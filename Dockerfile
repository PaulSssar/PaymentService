FROM python:3.12-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаём непривилегированного пользователя
RUN useradd --create-home appuser

# Копируем зависимости и устанавливаем их (только production)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

# Копируем исходный код
COPY --chown=appuser . .

# Переключаемся на непривилегированного пользователя
USER appuser

# Порт для FastAPI
EXPOSE 8000

# Команда запуска (переопределяется в docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
