FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "-Q", "ai_pipeline,image_gen,tts_gen,video_render,cleanup", "--concurrency=2"]
