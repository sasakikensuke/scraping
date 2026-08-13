FROM python:3.10-slim

# Set the time zone to Japan Standard Time (JST)
ENV TZ=Asia/Tokyo

RUN apt-get update && \
    apt-get install -y cron dos2unix procps && \
    rm -rf /var/lib/apt/lists/*

# Link the system’s local time to Tokyo
RUN ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && \
    echo "Asia/Tokyo" > /etc/timezone

WORKDIR /app

COPY config.yaml /app
COPY secret.yaml /app
COPY handler_daily.py /app
COPY cron.d /app/cron.d
COPY handler_historical.py /app
COPY shared /app/shared

RUN pip install --no-cache-dir -r /app/shared/requirements.txt

# Convert cron file to LF
RUN dos2unix /app/cron.d/daily \
 && crontab /app/cron.d/daily \
 && mkdir -p /app/record

CMD ["sleep", "infinity"]