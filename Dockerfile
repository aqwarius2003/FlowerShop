FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Установка nano и других необходимых пакетов
RUN apt-get update && \
    apt-get install -y --no-install-recommends nano && \
    rm -rf /var/lib/apt/lists/*

# Копируем все файлы из локальной директории static в образ
# Копируем все файлы из локальной директории static в образ
COPY static /app/static

# Копируем остальные файлы проекта
COPY . /app

WORKDIR /app

ENV DJANGO_SETTINGS_MODULE=FlowerShop.settings
ENV PYTHONUNBUFFERED=1

# RUN python manage.py migrate

RUN [ -f /app/start.sh ] && chmod +x /app/start.sh || echo "File /app/start.sh not found"

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
