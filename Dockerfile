# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libespeak-ng-dev \
    libespeak-ng1 \
    espeak-ng-data \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .
COPY piper1-gpl/ ./piper1-gpl/

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt && \
    cd piper1-gpl && \
    pip install --no-cache-dir -e . && \
    cd ..

# Копируем остальные файлы проекта
COPY voice_generator.py .
COPY vk_bot.py .

# Создаем директорию для временных файлов
RUN mkdir -p /app/temp && chmod 777 /app/temp

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Запускаем бота
CMD ["python", "vk_bot.py"]



