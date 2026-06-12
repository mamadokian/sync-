FROM alpine:3.18

# Install git and cron
RUN apk add --no-cache git dcron bash

# Copy sync script
COPY sync.sh /app/sync.sh
RUN chmod +x /app/sync.sh

# Create mirror directory
RUN mkdir -p /app/repo-mirror.git

# Add cron job (every 2 hours)
RUN echo "0 */2 * * * /app/sync.sh >> /app/sync.log 2>&1" > /etc/crontabs/root

# Start cron in foreground
CMD ["crond", "-f", "-l", "2"]
