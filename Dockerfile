FROM alpine:3.18

RUN apk add --no-cache git python3

WORKDIR /app

COPY sync.py /app/sync.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
