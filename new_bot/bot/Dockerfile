# 1. Базовый образ
FROM python:3.11-slim

# 2. Рабочая директория
WORKDIR /bot

# 3. Копируем зависимости и ставим их (кэширование слоев!)
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. Копируем сам код
COPY . .

# 5. Команда запуска
CMD ["python", "bot.py"]