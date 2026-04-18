FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir python-telegram-bot flask psutil requests yt-dlp docker
WORKDIR /aio_bot
COPY . .
CMD ["python", "main.py"]
