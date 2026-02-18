FROM python:3.12-slim

# Install ffmpeg via apt — lands at /usr/bin/ffmpeg, always on PATH
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads outputs

CMD ["python", "run.py"]
