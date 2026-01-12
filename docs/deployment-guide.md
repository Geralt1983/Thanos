# Thanos MCP Integration - Production Deployment Guide

Complete guide for deploying Thanos with MCP integration to production environments.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Security Best Practices](#security-best-practices)
- [Production Checklist](#production-checklist)
- [Deployment Procedures](#deployment-procedures)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

---

## Overview

Thanos uses the Model Context Protocol (MCP) to integrate with multiple services and tools. This guide covers production deployment of the MCP infrastructure.

### Architecture Overview

```
Thanos Orchestrator
    ↓
AdapterManager (unified interface)
    ├─ Direct Adapters (WorkOS, Oura, Neo4j, etc.)
    └─ MCP Bridges
        ├─ Local Servers (stdio transport)
        │   ├─ WorkOS MCP Server (Node.js)
        │   ├─ Sequential Thinking Server
        │   ├─ Filesystem Server
        │   └─ Playwright Server
        └─ Remote Servers (SSE/HTTP transport)
            └─ Context7 API
```

### Key Components

- **MCP Python SDK**: Protocol implementation
- **MCPBridge**: Adapter interface for MCP servers
- **Transport Layer**: stdio, SSE, and HTTP support
- **Configuration System**: .mcp.json and environment variables
- **Advanced Features**: Pooling, caching, health monitoring, load balancing

---

## Prerequisites

### Required Software

- **Python 3.9+** with pip and venv
- **Node.js 18+** with npm (for MCP servers)
- **Git** for version control
- **PostgreSQL** (for WorkOS - can use Neon.tech free tier)
- **Neo4j AuraDB** (for MemOS - free tier available)

### Required Accounts and API Keys

- **Anthropic API Key** (Claude AI)
- **OpenAI API Key** (embeddings)
- **Neo4j AuraDB** credentials
- **Neon PostgreSQL** database (for WorkOS)
- **Context7 API Key** (optional, for doc search)

### System Requirements

**Minimum:**
- 2 CPU cores
- 4 GB RAM
- 10 GB disk space

**Recommended:**
- 4+ CPU cores
- 8+ GB RAM
- 20+ GB disk space

---

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/Thanos.git
cd Thanos
```

### 2. Run Setup Script

```bash
./scripts/mcp-setup.sh
```

This script will:
- Check prerequisites
- Create Python virtual environment
- Install dependencies
- Setup configuration files
- Build WorkOS MCP server
- Validate configuration

### 3. Manual Setup (Alternative)

If the setup script fails or you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy configuration templates
cp .env.example .env
cp .mcp.json.example .mcp.json

# Edit configuration files
nano .env
nano .mcp.json

# Build WorkOS MCP server (if present)
cd mcp-servers/workos-mcp
npm install
npm run build
cd ../..

# Validate configuration
python scripts/validate-mcp-config.py
```

---

## Environment Variables

### Overview

Thanos uses environment variables for sensitive configuration. **Never commit the `.env` file to version control!**

### Configuration File

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
chmod 600 .env  # Secure permissions
```

### Core Thanos Variables

#### `ANTHROPIC_API_KEY` (Required)

Claude AI API key for Thanos orchestrator.

- **Format**: `sk-ant-api03-...`
- **Get it**: https://console.anthropic.com/
- **Usage**: Core AI functionality

```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

#### `OPENAI_API_KEY` (Required)

OpenAI API key for vector embeddings in MemOS.

- **Format**: `sk-proj-...`
- **Get it**: https://platform.openai.com/api-keys
- **Usage**: Embedding generation for memory system

```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

### MemOS (Neo4j) Variables

#### `NEO4J_URI` (Required)

Neo4j database connection URI.

- **Format**: `neo4j+s://xxxxx.databases.neo4j.io`
- **Get it**: https://neo4j.com/cloud/aura/ (free tier available)
- **Usage**: Graph-based memory storage

```bash
NEO4J_URI=neo4j+s://12345678.databases.neo4j.io
```

#### `NEO4J_USERNAME` (Required)

Neo4j database username (usually `neo4j`).

```bash
NEO4J_USERNAME=neo4j
```

#### `NEO4J_PASSWORD` (Required)

Neo4j database password from AuraDB console.

```bash
NEO4J_PASSWORD=your-secure-neo4j-password
```

### WorkOS MCP Server Variables

#### `WORKOS_DATABASE_URL` or `DATABASE_URL` (Required for WorkOS)

PostgreSQL database URL for WorkOS task management.

- **Format**: `postgresql://user:password@host:port/database`
- **Get it**: https://neon.tech (free tier available)
- **Usage**: Task and habit tracking

```bash
WORKOS_DATABASE_URL=postgresql://user:password@ep-cool-name.us-east-2.aws.neon.tech/neondb
DATABASE_URL=${WORKOS_DATABASE_URL}
```

#### `WORKOS_MCP_PATH` (Optional)

Custom path to WorkOS MCP server. Uses default if not set.

```bash
# Default: ~/Projects/Thanos/mcp-servers/workos-mcp/dist/index.js
WORKOS_MCP_PATH=/custom/path/to/workos-mcp/dist/index.js
```

#### `NODE_ENV` (Optional)

Node.js environment mode.

- **Values**: `development` or `production`
- **Default**: `production`

```bash
NODE_ENV=production
```

### Third-Party MCP Server Variables

#### `CONTEXT7_API_KEY` (Optional)

Context7 API key for documentation search.

- **Get it**: https://context7.ai
- **Usage**: Search library documentation

```bash
CONTEXT7_API_KEY=your-context7-api-key
```

#### `ALLOWED_DIRECTORY` (Optional, Security Critical!)

Directory allowed for filesystem server operations.

- **Default**: `/tmp`
- **Security**: Restricts file access to this directory only

```bash
ALLOWED_DIRECTORY=/path/to/safe/directory
```

#### `FILESYSTEM_ALLOW_WRITE` (Optional, Security Critical!)

Enable write operations in filesystem server.

- **Default**: `false`
- **Security**: Only enable if absolutely necessary

```bash
FILESYSTEM_ALLOW_WRITE=false
```

#### `PLAYWRIGHT_HEADLESS` (Optional)

Run Playwright in headless mode.

- **Default**: `true`
- **Usage**: Browser automation

```bash
PLAYWRIGHT_HEADLESS=true
```

#### `PLAYWRIGHT_TIMEOUT` (Optional)

Playwright operation timeout in milliseconds.

- **Default**: `30000` (30 seconds)

```bash
PLAYWRIGHT_TIMEOUT=30000
```

#### `FETCH_USER_AGENT` (Optional)

Custom user agent for web requests.

- **Default**: `Thanos/1.0`

```bash
FETCH_USER_AGENT=Thanos/1.0
```

### Advanced MCP Configuration

#### `DEBUG` (Optional)

Enable debug logging for MCP operations.

- **Default**: `false`
- **Impact**: Very verbose logging

```bash
DEBUG=false
```

#### `MCP_TIMEOUT` (Optional)

Connection timeout in seconds.

- **Default**: `30`

```bash
MCP_TIMEOUT=30
```

#### `MCP_MAX_RETRIES` (Optional)

Maximum retry attempts for failed operations.

- **Default**: `3`

```bash
MCP_MAX_RETRIES=3
```

#### `MCP_CACHE_TTL` (Optional)

Cache time-to-live in seconds.

- **Default**: `300` (5 minutes)

```bash
MCP_CACHE_TTL=300
```

#### `MCP_HEALTH_CHECK_INTERVAL` (Optional)

Health check interval in seconds.

- **Default**: `60`

```bash
MCP_HEALTH_CHECK_INTERVAL=60
```

#### `MCP_POOL_MIN_CONNECTIONS` (Optional)

Minimum connection pool size.

- **Default**: `1`

```bash
MCP_POOL_MIN_CONNECTIONS=1
```

#### `MCP_POOL_MAX_CONNECTIONS` (Optional)

Maximum connection pool size.

- **Default**: `10`

```bash
MCP_POOL_MAX_CONNECTIONS=10
```

### Security and Logging

#### `MCP_ALLOW_REMOTE_SERVERS` (Optional)

Allow connections to remote MCP servers.

- **Default**: `true`

```bash
MCP_ALLOW_REMOTE_SERVERS=true
```

#### `MCP_VALIDATE_SSL` (Optional, Security Critical!)

Validate SSL certificates for remote servers.

- **Default**: `true`
- **Security**: Never disable in production!

```bash
MCP_VALIDATE_SSL=true
```

#### `MCP_SANITIZE_LOGS` (Optional, Security Critical!)

Sanitize sensitive data in logs.

- **Default**: `true`
- **Security**: Prevents credential leaks

```bash
MCP_SANITIZE_LOGS=true
```

#### `LOG_LEVEL` (Optional)

Logging level.

- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Default**: `INFO`

```bash
LOG_LEVEL=INFO
```

#### `MCP_DEBUG_PROTOCOL` (Optional)

Enable protocol-level debug logging.

- **Default**: `false`
- **Impact**: Extremely verbose, only for debugging

```bash
MCP_DEBUG_PROTOCOL=false
```

### Testing and Development

#### `TEST_MODE` (Development Only)

Enable test mode with mock servers.

- **Default**: `false`
- **Usage**: Development and testing only

```bash
TEST_MODE=false
```

#### `SKIP_SSL_VERIFICATION` (Development Only, NEVER in Production!)

Skip SSL verification for development.

- **Default**: `false`
- **Security**: **NEVER** use in production!

```bash
# SKIP_SSL_VERIFICATION=false  # Keep commented in production!
```

---

## Configuration Files

### .mcp.json

Main MCP server configuration file.

**Location**: Project root (`.mcp.json`) or home directory (`~/.claude.json`)

**Precedence**: Project `.mcp.json` overrides global `~/.claude.json`

#### Basic Structure

```json
{
  "mcpServers": {
    "server-name": {
      "name": "server-name",
      "description": "Server description",
      "type": "stdio",
      "command": "node",
      "args": ["path/to/server.js"],
      "env": {
        "KEY": "${ENV_VAR}"
      },
      "tags": ["tag1", "tag2"],
      "enabled": true
    }
  },
  "config": {
    "discovery": { ... },
    "defaults": { ... },
    "security": { ... },
    "performance": { ... },
    "logging": { ... }
  }
}
```

#### Transport Types

1. **stdio** (Local Subprocess)
   ```json
   {
     "type": "stdio",
     "command": "node",
     "args": ["dist/index.js"],
     "env": {"KEY": "value"}
   }
   ```

2. **SSE** (Remote Server-Sent Events)
   ```json
   {
     "type": "sse",
     "url": "https://api.example.com/mcp",
     "api_key": "${API_KEY}",
     "headers": {"User-Agent": "Thanos/1.0"},
     "timeout": 30
   }
   ```

3. **HTTP** (Remote HTTP - Planned)
   ```json
   {
     "type": "http",
     "url": "https://api.example.com/mcp",
     "api_key": "${API_KEY}"
   }
   ```

#### Environment Variable Interpolation

Use `${VAR}` or `$VAR` syntax:

```json
{
  "args": ["${WORKOS_MCP_PATH:-/default/path}"],
  "env": {
    "DATABASE_URL": "${DATABASE_URL}",
    "NODE_ENV": "${NODE_ENV:-production}"
  }
}
```

Default values supported: `${VAR:-default}`

#### Server Tags

Tags for filtering and organization:

```json
{
  "tags": ["workos", "productivity", "tasks", "habits"]
}
```

Use tags to enable/disable groups of servers:

```python
# Enable only productivity servers
servers = discovery.discover_servers(tags=["productivity"])
```

### Global Configuration Section

#### Discovery Settings

```json
{
  "config": {
    "discovery": {
      "enabled": true,
      "search_parent_directories": true,
      "max_depth": 5
    }
  }
}
```

#### Default Settings

```json
{
  "config": {
    "defaults": {
      "timeout": 30,
      "retry_attempts": 3,
      "enable_caching": true,
      "cache_ttl": 300,
      "enable_health_checks": true,
      "health_check_interval": 60
    }
  }
}
```

#### Security Settings

```json
{
  "config": {
    "security": {
      "allow_remote_servers": true,
      "validate_ssl": true,
      "allowed_domains": [],
      "blocked_domains": []
    }
  }
}
```

#### Performance Settings

```json
{
  "config": {
    "performance": {
      "enable_connection_pooling": true,
      "pool_min_connections": 1,
      "pool_max_connections": 10,
      "enable_load_balancing": false
    }
  }
}
```

#### Logging Settings

```json
{
  "config": {
    "logging": {
      "level": "INFO",
      "enable_debug_protocol": false,
      "sanitize_sensitive_data": true
    }
  }
}
```

---

## Security Best Practices

### Credentials Management

#### ✅ DO:

- **Use environment variables** for all sensitive data
- **Encrypt secrets** at rest (e.g., with AWS Secrets Manager, Vault)
- **Rotate credentials** regularly (at least quarterly)
- **Use unique credentials** per environment (dev, staging, prod)
- **Enable MFA** on all service accounts
- **Audit credential access** regularly

#### ❌ DON'T:

- **Never commit** `.env` file to version control
- **Never hardcode** credentials in code or config files
- **Never share** credentials via email or chat
- **Never use** production credentials in development
- **Never log** credentials (sanitization should prevent this)

### .gitignore Configuration

Ensure `.gitignore` includes:

```gitignore
# Sensitive files
.env
.env.local
.env.*.local

# MCP configuration with secrets
.mcp.json

# Logs
*.log
logs/

# Local development
.venv/
venv/
__pycache__/
*.pyc
```

### File Permissions

Secure permissions on sensitive files:

```bash
# .env file (read/write for owner only)
chmod 600 .env

# Configuration files
chmod 644 .mcp.json

# Scripts
chmod 755 scripts/*.sh
```

### Network Security

#### SSL/TLS

- **Always validate SSL** certificates in production
- Use `MCP_VALIDATE_SSL=true` (default)
- Never set `SKIP_SSL_VERIFICATION=true` in production

#### Remote Servers

- **Verify server identity** before enabling
- **Review server source code** when possible
- **Use HTTPS** for all remote connections
- **Whitelist allowed domains** if possible

### Filesystem Server Security

#### Critical Configuration

```json
{
  "name": "filesystem",
  "args": ["/home/thanos/safe-directory"],  // Restrict to safe path!
  "env": {
    "ALLOW_WRITE": "false"  // Read-only by default
  }
}
```

#### Security Checklist

- ✅ **Restrict access** to safe directories only
- ✅ **Disable write operations** unless necessary
- ✅ **Avoid symbolic links** in allowed directories
- ✅ **Monitor file operations** in logs
- ✅ **Use separate user** with limited permissions

### Database Security

#### PostgreSQL (WorkOS)

- Use SSL connections (`sslmode=require`)
- Create dedicated database user for WorkOS
- Grant minimal required permissions
- Enable connection pooling
- Set connection limits
- Enable query logging for audit

#### Neo4j (MemOS)

- Use encrypted connections (`neo4j+s://`)
- Create dedicated database user
- Enable authentication
- Restrict network access
- Enable audit logging

### API Key Security

- **Store keys in environment variables**
- **Rotate keys quarterly**
- **Use key management service** (AWS KMS, Azure Key Vault, etc.)
- **Monitor API usage** for anomalies
- **Set usage limits** where possible
- **Enable alerts** for unusual activity

### Logging and Monitoring

#### Safe Logging Practices

- **Enable sanitization**: `MCP_SANITIZE_LOGS=true`
- **Review logs regularly** for leaked secrets
- **Secure log storage** (encrypted, access-controlled)
- **Set log retention** policies
- **Redact sensitive patterns**: passwords, API keys, tokens

#### Monitoring Alerts

Set up alerts for:
- Failed authentication attempts
- Unusual API usage patterns
- High error rates
- Slow response times
- Health check failures
- Resource exhaustion

### Incident Response

#### Security Incident Checklist

1. **Detect**: Monitor for security events
2. **Contain**: Disable compromised credentials immediately
3. **Investigate**: Review logs and access patterns
4. **Rotate**: Generate new credentials
5. **Update**: Update all configurations
6. **Notify**: Inform affected parties if required
7. **Review**: Post-mortem and process improvements

#### Credential Rotation Procedure

```bash
# 1. Generate new credentials
# (via service provider console)

# 2. Update .env file
nano .env

# 3. Restart services
sudo systemctl restart thanos

# 4. Verify functionality
./scripts/validate-mcp-config.py

# 5. Revoke old credentials
# (via service provider console)

# 6. Document rotation in log
echo "$(date): Rotated ANTHROPIC_API_KEY" >> credential-rotation.log
```

---

## Production Checklist

### Pre-Deployment

- [ ] All required environment variables set
- [ ] No placeholder values in `.env`
- [ ] `.env` file not committed to git
- [ ] `.gitignore` includes `.env` and sensitive files
- [ ] Configuration validation passed
- [ ] All dependencies installed
- [ ] WorkOS MCP server built
- [ ] Database connections tested
- [ ] API keys validated
- [ ] SSL certificates valid
- [ ] Secure file permissions set
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] Backup procedures documented
- [ ] Rollback procedures tested

### Post-Deployment

- [ ] Services started successfully
- [ ] Health checks passing
- [ ] Logs show no errors
- [ ] All MCP servers accessible
- [ ] Tool calls working
- [ ] Performance metrics normal
- [ ] No credential leaks in logs
- [ ] Monitoring dashboards functional
- [ ] Alerts configured and tested
- [ ] Documentation updated
- [ ] Team notified

---

## Deployment Procedures

### Single Server Deployment

```bash
# 1. Update code
cd /opt/thanos
git pull origin main

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Build MCP servers
cd mcp-servers/workos-mcp
npm install
npm run build
cd ../..

# 5. Validate configuration
python scripts/validate-mcp-config.py

# 6. Run tests (optional)
pytest tests/ -v

# 7. Restart service
sudo systemctl restart thanos

# 8. Verify health
python -c "
from Tools.adapters import get_default_manager
import asyncio

async def check():
    manager = await get_default_manager(enable_mcp=True)
    tools = await manager.list_tools()
    print(f'Available tools: {len(tools)}')

asyncio.run(check())
"

# 9. Monitor logs
tail -f logs/thanos.log
```

### Systemd Service

Create `/etc/systemd/system/thanos.service`:

```ini
[Unit]
Description=Thanos AI Orchestrator
After=network.target

[Service]
Type=simple
User=thanos
Group=thanos
WorkingDirectory=/opt/thanos
Environment="PATH=/opt/thanos/.venv/bin"
EnvironmentFile=/opt/thanos/.env
ExecStart=/opt/thanos/.venv/bin/python -m Tools.thanos_orchestrator
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/thanos/logs

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable thanos
sudo systemctl start thanos
sudo systemctl status thanos
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install Node.js
RUN apt-get update && apt-get install -y \
    nodejs npm git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Build MCP servers
RUN cd mcp-servers/workos-mcp && \
    npm install && \
    npm run build

# Create user
RUN useradd -m -u 1000 thanos && \
    chown -R thanos:thanos /app

USER thanos

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from Tools.adapters import get_default_manager; import asyncio; asyncio.run(get_default_manager())"

# Run application
CMD ["python", "-m", "Tools.thanos_orchestrator"]
```

Build and run:

```bash
# Build image
docker build -t thanos:latest .

# Run container
docker run -d \
    --name thanos \
    --env-file .env \
    -v $(pwd)/logs:/app/logs \
    -p 8000:8000 \
    thanos:latest

# View logs
docker logs -f thanos
```

### Kubernetes Deployment

See separate Kubernetes documentation for production-grade orchestration.

---

## Monitoring and Maintenance

### Health Checks

#### Manual Health Check

```bash
python -c "
from Tools.adapters import get_default_manager
import asyncio

async def health_check():
    try:
        manager = await get_default_manager(enable_mcp=True)

        # List all tools
        tools = await manager.list_tools()
        print(f'✓ Available tools: {len(tools)}')

        # Test MCP bridge health
        for name, adapter in manager._adapters.items():
            if hasattr(adapter, 'health_check'):
                health = await adapter.health_check()
                status = '✓' if health else '✗'
                print(f'{status} {name}: {\"healthy\" if health else \"unhealthy\"}')'

        return True
    except Exception as e:
        print(f'✗ Health check failed: {e}')
        return False

result = asyncio.run(health_check())
exit(0 if result else 1)
"
```

#### Automated Health Checks

Add to cron:

```bash
# Health check every 5 minutes
*/5 * * * * /opt/thanos/.venv/bin/python /opt/thanos/scripts/health-check.py >> /opt/thanos/logs/health.log 2>&1
```

### Log Monitoring

#### Log Locations

- **Application logs**: `logs/thanos.log`
- **MCP protocol logs**: `logs/mcp-protocol.log`
- **Error logs**: `logs/error.log`
- **Health check logs**: `logs/health.log`

#### Log Rotation

Configure with `logrotate`:

```bash
# /etc/logrotate.d/thanos
/opt/thanos/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
}
```

### Performance Monitoring

#### Metrics to Track

- Tool call latency (p50, p95, p99)
- Success/failure rates
- Connection pool utilization
- Health check results
- Error rates by type
- Cache hit rates
- CPU and memory usage

#### Prometheus Integration

Expose metrics endpoint:

```python
from Tools.adapters.mcp_metrics import get_global_metrics_collector
from flask import Flask, Response

app = Flask(__name__)

@app.route('/metrics')
def metrics():
    collector = get_global_metrics_collector()
    return Response(collector.to_prometheus(), mimetype='text/plain')
```

### Backup Procedures

#### Configuration Backup

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/thanos/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup configuration (without secrets)
cp .mcp.json "$BACKUP_DIR/"
# Note: .env is NOT backed up (contains secrets)

# Backup database credentials reference
echo "Database credentials stored in: 1Password/Thanos" > "$BACKUP_DIR/credentials.txt"

# Backup MCP server code
tar -czf "$BACKUP_DIR/mcp-servers.tar.gz" mcp-servers/
```

#### Database Backup

```bash
# PostgreSQL (WorkOS)
pg_dump "$WORKOS_DATABASE_URL" > backup-workos-$(date +%Y%m%d).sql

# Neo4j (MemOS)
# Use Neo4j backup tools or AuraDB automatic backups
```

### Maintenance Windows

#### Weekly Maintenance

- Review logs for errors
- Check disk space
- Review performance metrics
- Test backups
- Update dependencies (if security patches)

#### Monthly Maintenance

- Rotate API keys and credentials
- Review and update documentation
- Performance optimization review
- Capacity planning review
- Security audit

#### Quarterly Maintenance

- Major version updates
- Architecture review
- Disaster recovery test
- Security penetration test
- Team training updates

---

## Troubleshooting

### Common Issues

#### 1. MCP Server Won't Start

**Symptoms:**
- "Connection refused" errors
- "Server not found" errors

**Solutions:**
```bash
# Check server path
echo $WORKOS_MCP_PATH
ls -la $WORKOS_MCP_PATH

# Rebuild server
cd mcp-servers/workos-mcp
npm install
npm run build

# Check Node.js
node --version
npx --version

# Test server directly
node dist/index.js
```

#### 2. Database Connection Fails

**Symptoms:**
- "Connection refused"
- "Authentication failed"

**Solutions:**
```bash
# Check environment variables
echo $WORKOS_DATABASE_URL
echo $NEO4J_URI

# Test PostgreSQL connection
psql "$WORKOS_DATABASE_URL" -c "SELECT version();"

# Test Neo4j connection
python -c "
from neo4j import GraphDatabase
uri = '$NEO4J_URI'
user = '$NEO4J_USERNAME'
password = '$NEO4J_PASSWORD'
driver = GraphDatabase.driver(uri, auth=(user, password))
driver.verify_connectivity()
print('Connected!')
"
```

#### 3. SSL Certificate Errors

**Symptoms:**
- "SSL certificate verify failed"
- "CERTIFICATE_VERIFY_FAILED"

**Solutions:**
```bash
# Update certificates
pip install --upgrade certifi

# Check SSL validation setting
grep MCP_VALIDATE_SSL .env

# Test remote server
curl -v https://api.context7.ai/mcp
```

#### 4. Tool Call Timeouts

**Symptoms:**
- "Operation timed out"
- Slow responses

**Solutions:**
```bash
# Increase timeout
export MCP_TIMEOUT=60

# Check network latency
ping api.example.com

# Review performance metrics
# Check connection pool settings
# Enable caching
```

#### 5. Memory Leaks

**Symptoms:**
- Increasing memory usage
- Out of memory errors

**Solutions:**
```bash
# Monitor memory
while true; do
    ps aux | grep thanos | grep -v grep
    sleep 60
done

# Check connection pool
# Review cache settings
# Restart service
sudo systemctl restart thanos
```

### Debug Mode

Enable debug logging:

```bash
# Set in .env
DEBUG=true
LOG_LEVEL=DEBUG
MCP_DEBUG_PROTOCOL=true

# Restart service
sudo systemctl restart thanos

# Watch logs
tail -f logs/thanos.log | grep DEBUG
```

### Getting Help

1. **Check Documentation**
   - `docs/mcp-integration-guide.md`
   - `docs/troubleshooting.md`
   - `docs/third-party-mcp-servers.md`

2. **Review Logs**
   - Application logs: `logs/thanos.log`
   - Error logs: `logs/error.log`
   - MCP protocol logs: `logs/mcp-protocol.log`

3. **Run Validation**
   ```bash
   python scripts/validate-mcp-config.py --verbose
   ```

4. **Test Components Individually**
   ```bash
   # Test MCP SDK
   python -c "import mcp; print(mcp.__version__)"

   # Test server connection
   python -c "
   from Tools.adapters.workos_mcp_bridge import create_workos_mcp_bridge
   import asyncio
   async def test():
       bridge = await create_workos_mcp_bridge()
       tools = await bridge.list_tools()
       print(f'Tools: {len(tools)}')
   asyncio.run(test())
   "
   ```

5. **Community Support**
   - GitHub Issues
   - Discord/Slack community
   - Stack Overflow

---

## Rollback Procedures

### Quick Rollback

```bash
# 1. Stop service
sudo systemctl stop thanos

# 2. Restore previous version
cd /opt/thanos
git checkout <previous-commit>

# 3. Restore virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Restore configuration
cp /backup/thanos/latest/.mcp.json .

# 5. Restart service
sudo systemctl start thanos

# 6. Verify
sudo systemctl status thanos
tail -f logs/thanos.log
```

### Database Rollback

```bash
# PostgreSQL
psql "$WORKOS_DATABASE_URL" < backup-workos-20260111.sql

# Neo4j
# Contact support for AuraDB restoration
```

### Emergency Procedures

#### Complete System Failure

1. **Notify stakeholders**
2. **Switch to backup system** (if available)
3. **Investigate root cause**
4. **Restore from known good state**
5. **Test thoroughly**
6. **Document incident**

#### Data Loss

1. **Stop all services immediately**
2. **Do not write any data**
3. **Restore from most recent backup**
4. **Validate data integrity**
5. **Resume operations**
6. **Review backup procedures**

---

## Conclusion

This deployment guide provides comprehensive instructions for production deployment of Thanos with MCP integration. Follow security best practices, monitor systems proactively, and maintain regular backups.

### Key Takeaways

- ✅ **Security first**: Never commit secrets, always validate SSL
- ✅ **Monitor everything**: Logs, metrics, health checks
- ✅ **Automate**: Setup scripts, health checks, backups
- ✅ **Document**: Changes, incidents, procedures
- ✅ **Test**: Configuration, connections, rollbacks

### Additional Resources

- [MCP Integration Guide](./mcp-integration-guide.md)
- [MCP Server Development Guide](./mcp-server-development.md)
- [Third-Party MCP Servers](./third-party-mcp-servers.md)
- [Architecture Documentation](./architecture.md)
- [API Reference](./api-reference.md)

---

**Last Updated**: 2026-01-11
**Version**: 1.0.0
**Maintainer**: Thanos Development Team
