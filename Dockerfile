FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    ffmpeg build-essential python3-dev gcc make \
    wget \
    curl \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --upgrade pip setuptools wheel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /tmp/mediainfo
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "bot"]
