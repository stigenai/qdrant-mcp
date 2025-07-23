FROM qdrant/qdrant:latest

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create directories
WORKDIR /app
RUN mkdir -p /var/log/supervisor

# Copy Python requirements
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Expose ports
EXPOSE 8000 8001 6333

# Use startup script as entrypoint
ENTRYPOINT ["/app/startup.sh"]