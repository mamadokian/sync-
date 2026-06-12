FROM alpine:3.18

RUN apk add --no-cache git bash

WORKDIR /app

COPY sync.sh /app/sync.sh
RUN chmod +x /app/sync.sh

CMD ["/app/sync.sh"]
