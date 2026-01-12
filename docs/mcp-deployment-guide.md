# MCP Bridge Deployment Guide

Complete guide for deploying Thanos with MCP bridge infrastructure in production environments.

## Overview

This guide covers production deployment of Thanos with full MCP SDK integration, including:
- Environment configuration
- Docker containerization
- Production logging and monitoring
- Performance optimization
- Security best practices

## Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL (for WorkOS adapter)
- Node.js 18+ (for third-party MCP servers)

## Environment Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# API Keys
OURA_API_KEY=your_oura_api_key
CONTEXT7_API_KEY=your_context7_api_key  # For third-party MCP servers
MAGIC_API_KEY=your_magic_api_key

# MCP Configuration
MCP_CONFIG_PATH=/path/to/mcp_servers.json
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/var/log/thanos/mcp.log

# Optional: Circuit Breaker Configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Optional: Connection Pool Configuration
MAX_CONNECTIONS=10
CONNECTION_TIMEOUT=30
```

### Environment Templates

Create `.env.production`:

```bash
# Production Environment Configuration
NODE_ENV=production
PYTHONUNBUFFERED=1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/thanos/app.log

# MCP Bridge Configuration
MCP_ENABLED=true
MCP_AUTO_DISCOVER=true
MCP_CONFIG_PATH=/etc/thanos/mcp_servers.json

# Database (replace with actual values)
DATABASE_URL=postgresql://thanos:${DB_PASSWORD}@postgres:5432/thanos

# API Keys (replace with actual values)
OURA_API_KEY=${OURA_API_KEY}
CONTEXT7_API_KEY=${CONTEXT7_API_KEY}
MAGIC_API_KEY=${MAGIC_API_KEY}

# Performance Tuning
MAX_CONNECTIONS=20
CONNECTION_TIMEOUT=30
REQUEST_TIMEOUT=60
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
```

Create `.env.development`:

```bash
# Development Environment Configuration
NODE_ENV=development
PYTHONUNBUFFERED=1

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=standard
LOG_FILE=logs/development.log

# MCP Bridge Configuration
MCP_ENABLED=true
MCP_AUTO_DISCOVER=true
MCP_CONFIG_PATH=config/mcp_servers.json

# Database (local development)
DATABASE_URL=postgresql://thanos:thanos@localhost:5432/thanos_dev

# API Keys (development/testing)
OURA_API_KEY=dev_oura_key
CONTEXT7_API_KEY=dev_context7_key
MAGIC_API_KEY=dev_magic_key

# Performance Tuning (relaxed for development)
MAX_CONNECTIONS=5
CONNECTION_TIMEOUT=10
REQUEST_TIMEOUT=30
CIRCUIT_BREAKER_ENABLED=false
```

## Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile for Thanos with MCP Bridge Support
FROM python:3.11-slim

# Install Node.js for third-party MCP servers
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for logs and config
RUN mkdir -p /var/log/thanos /etc/thanos

# Install third-party MCP servers
RUN npm install -g @21st-dev/mcp-context7 mcp-server-workos

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_ENABLED=true
ENV MCP_CONFIG_PATH=/etc/thanos/mcp_servers.json

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import asyncio; from Tools.adapters import get_default_manager; \
    asyncio.run(get_default_manager().health_check())"

# Run application
CMD ["python", "-m", "Tools.thanos_cli"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  thanos:
    build: .
    container_name: thanos-app
    restart: unless-stopped
    env_file:
      - .env.production
    volumes:
      - ./config:/etc/thanos:ro
      - ./logs:/var/log/thanos
      - ./data:/app/data
    depends_on:
      - postgres
    networks:
      - thanos-network
    ports:
      - "8000:8000"

  postgres:
    image: postgres:15-alpine
    container_name: thanos-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: thanos
      POSTGRES_USER: thanos
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - thanos-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U thanos"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
    driver: local

networks:
  thanos-network:
    driver: bridge
```

### Docker Compose with Monitoring

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  thanos:
    extends:
      file: docker-compose.yml
      service: thanos

  postgres:
    extends:
      file: docker-compose.yml
      service: thanos

  prometheus:
    image: prom/prometheus:latest
    container_name: thanos-prometheus
    restart: unless-stopped
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - thanos-network
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: thanos-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_INSTALL_PLUGINS=grafana-clock-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - thanos-network
    ports:
      - "3000:3000"
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
```

## Production Logging Configuration

### Configure Production Logging

```python
# config/logging_config.py
import logging.config
from Tools.adapters.mcp_observability import configure_production_logging

def setup_production_logging():
    """Setup production logging with JSON formatting and rotation."""
    configure_production_logging(
        log_level="INFO",
        log_file="/var/log/thanos/mcp.log"
    )

# Call at application startup
setup_production_logging()
```

### Log Rotation

Create `/etc/logrotate.d/thanos`:

```
/var/log/thanos/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 thanos thanos
    sharedscripts
    postrotate
        systemctl reload thanos
    endscript
}
```

## MCP Server Configuration

### Production MCP Servers Configuration

Create `/etc/thanos/mcp_servers.json`:

```json
{
  "mcpServers": {
    "workos": {
      "command": "uvx",
      "args": ["mcp-server-workos"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      },
      "transport": "stdio",
      "tags": ["workos", "productivity", "core"],
      "enabled": true
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@21st-dev/mcp-context7"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      },
      "transport": "stdio",
      "tags": ["documentation", "research"],
      "enabled": true
    },
    "magic": {
      "command": "npx",
      "args": ["-y", "@magic/mcp-server"],
      "env": {
        "MAGIC_API_KEY": "${MAGIC_API_KEY}"
      },
      "transport": "stdio",
      "tags": ["ui", "generation"],
      "enabled": true
    }
  }
}
```

## Deployment Commands

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with MCP bridges enabled
python -m Tools.thanos_cli --enable-mcp

# Run tests
pytest tests/
```

### Docker Deployment

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f thanos

# Check health
docker-compose exec thanos python -c "
from Tools.adapters import get_default_manager
import asyncio
manager = asyncio.run(get_default_manager(enable_mcp_bridges=True))
print(asyncio.run(manager.health_check()))
"

# Stop services
docker-compose down
```

### Production Deployment

```bash
# Pull latest code
git pull origin main

# Build production image
docker-compose -f docker-compose.yml build

# Deploy with zero downtime
docker-compose -f docker-compose.yml up -d --no-deps --build thanos

# Verify deployment
docker-compose exec thanos python -c "
from Tools.adapters.mcp_observability import get_all_metrics
import json
print(json.dumps(get_all_metrics(), indent=2))
"
```

## Performance Optimization

### Connection Pooling

```python
# config/performance_config.py
from Tools.adapters.mcp_pool import ConnectionPool

# Configure connection pool
pool_config = {
    "min_connections": 2,
    "max_connections": 10,
    "max_idle_time": 300,  # 5 minutes
    "health_check_interval": 60  # 1 minute
}

# Apply to MCP bridges
pool = ConnectionPool(config=pool_config)
```

### Caching Strategy

```python
# config/cache_config.py
from Tools.adapters.mcp_cache import ResultCache

# Configure result caching
cache_config = {
    "enabled": True,
    "ttl": 3600,  # 1 hour
    "max_size": 1000,  # entries
    "eviction_policy": "lru"  # Least Recently Used
}

cache = ResultCache(config=cache_config)
```

## Monitoring and Alerting

### Health Check Endpoints

```python
# Implement health check endpoint
@app.get("/health")
async def health_check():
    manager = await get_default_manager(enable_mcp_bridges=True)
    health = await manager.health_check()
    return health.to_dict()

@app.get("/metrics")
async def metrics():
    from Tools.adapters.mcp_observability import get_all_metrics
    return get_all_metrics()
```

### Prometheus Metrics

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'thanos'
    static_configs:
      - targets: ['thanos:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Example metrics to monitor:
- Connection success rate
- Tool call latency (p50, p95, p99)
- Error rates by server
- Cache hit rates
- Active connections

## Security Best Practices

### 1. Environment Variable Management

```bash
# Use secret management tools
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id thanos/production

# HashiCorp Vault
vault kv get secret/thanos/production
```

### 2. Network Security

```yaml
# docker-compose.yml - restrict network access
services:
  thanos:
    networks:
      - thanos-network
    # Don't expose unnecessary ports
```

### 3. Input Validation

All MCP bridge inputs are validated via Pydantic schemas before execution.

### 4. Logging Security

- Never log sensitive data (API keys, passwords)
- Use structured logging with appropriate log levels
- Implement log sanitization for PII

## Troubleshooting

### Common Issues

**Issue**: MCP server fails to start
```bash
# Check server configuration
python -c "from Tools.adapters.mcp_discovery import discover_servers; print(discover_servers())"

# Test server manually
npx -y @21st-dev/mcp-context7
```

**Issue**: High error rates
```bash
# Check metrics
docker-compose exec thanos python -c "
from Tools.adapters.mcp_observability import get_all_metrics
import json
print(json.dumps(get_all_metrics(), indent=2))
"

# Review logs
docker-compose logs --tail=100 thanos
```

**Issue**: Connection pool exhaustion
```bash
# Check active connections
docker-compose exec thanos python -c "
from Tools.adapters.mcp_pool import get_pool_stats
print(get_pool_stats())
"
```

## Maintenance

### Regular Tasks

1. **Daily**: Monitor error rates and latency
2. **Weekly**: Review and rotate logs
3. **Monthly**: Update dependencies and MCP servers
4. **Quarterly**: Performance review and optimization

### Backup Strategy

```bash
# Backup database
docker-compose exec postgres pg_dump -U thanos thanos > backup.sql

# Backup configuration
tar -czf config-backup.tar.gz config/ .env.production
```

## Support and Resources

- MCP SDK Documentation: https://github.com/modelcontextprotocol/python-sdk
- Thanos Documentation: docs/
- Issue Tracker: [Your issue tracker URL]
