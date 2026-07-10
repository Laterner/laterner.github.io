# 1. Базовый образ
FROM python:3.13-slim

# 2. Рабочая директория
WORKDIR /bot

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Копируем зависимости и ставим их (кэширование слоев!)
COPY requirements.txt requirements.txt

RUN pip install uv

RUN pip install --no-cache-dir -r requirements.txt

# 4. Копируем сам код
COPY . .

# 5. Команда запуска
CMD ["python", "bot.py"]