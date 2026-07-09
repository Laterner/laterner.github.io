FROM python:3.13-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Установка Python зависимостей
RUN uv pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание непривилегированного пользователя
RUN adduser --disabled-password --no-create-home appuser
USER appuser

# Запуск приложения
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
CMD ["python", "main.py"]