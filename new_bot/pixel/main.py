# server.py
from quart import Quart, render_template, websocket, send_from_directory
import asyncio
import json
import os

app = Quart(__name__)
app.secret_key = 'your-secret-key-change-in-production'


# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Состояние сетки: 100 элементов, каждый 0..5 (0 - белый)
GRID_SIZE = 50
TOTAL_PIXELS = GRID_SIZE * GRID_SIZE
grid_state = [0] * TOTAL_PIXELS

# Хранилище активных WebSocket соединений
connected_websockets = set()

# Блокировка для потокобезопасного доступа к grid_state (для Quart/async)
grid_lock = asyncio.Lock()

async def broadcast(message, exclude=None):
    """Отправить сообщение всем подключенным клиентам, кроме exclude."""
    if not connected_websockets:
        return
    data = json.dumps(message)
    tasks = []
    for ws in list(connected_websockets):
        if ws is exclude:
            continue
        tasks.append(asyncio.create_task(ws.send(data)))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

@app.route('/')
async def index():
    """Отдать HTML-страницу."""
    return await render_template('index.html')

@app.route('/static/<path:filename>')
async def static_files(filename):
    """Раздача статики (если понадобится)."""
    return await send_from_directory('static', filename)

@app.websocket('/ws')
async def ws_endpoint():
    """WebSocket эндпоинт для обмена данными."""
    ws = websocket._get_current_object()  # для корректного использования в broadcast
    connected_websockets.add(ws)
    try:
        # Отправляем текущее состояние при подключении
        await ws.send(json.dumps({
            'type': 'init',
            'data': grid_state
        }))

        # Основной цикл обработки сообщений
        while True:
            raw = await ws.receive()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue  # игнорируем невалидный JSON

            msg_type = data.get('type')
            if msg_type == 'paint':
                index = data.get('index')
                color = data.get('color')
                if index is None or color is None:
                    continue
                if not (0 <= index < TOTAL_PIXELS and 0 <= color <= 5):
                    continue
                async with grid_lock:
                    if grid_state[index] != color:
                        grid_state[index] = color
                        # Отправляем обновление всем, включая отправителя (чтобы синхронизировать)
                        await broadcast({
                            'type': 'update',
                            'index': index,
                            'color': color
                        })
            elif msg_type == 'reset':
                async with grid_lock:
                    # Сброс на белый (0)
                    for i in range(TOTAL_PIXELS):
                        grid_state[i] = 0
                    await broadcast({
                        'type': 'reset',
                        'data': grid_state
                    })
            else:
                # Неизвестный тип сообщения
                pass

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connected_websockets.discard(ws)
        try:
            await ws.close()
        except:
            pass

if __name__ == '__main__':
    # Запуск сервера на всех интерфейсах, порт 5000
    app.run(host='0.0.0.0', port=8000, debug=False)