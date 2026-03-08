# Deployment Guide

This guide covers deployment options for the Personal AI Employee system, from local development to production cloud deployments.

## Table of Contents

- [Local Deployment](#local-deployment)
- [Cloud VM Deployment](#cloud-vm-deployment)
- [Docker Deployment](#docker-deployment)
- [Security Hardening](#security-hardening)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Local Deployment

### Prerequisites

- Python 3.11+
- Git
- Obsidian (optional, for vault viewing)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/muhammadhamza718/Hackathon-0.git
   cd Hackathon-0
   ```

2. **Create vault directories**
   ```bash
   mkdir -p Inbox Needs_Action Done Pending_Approval Approved Rejected Plans Logs Briefings
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your paths and credentials
   ```

4. **Install dependencies**
   ```bash
   cd sentinel
   uv sync
   ```

5. **Run the system**
   ```bash
   uv run python -m sentinel
   ```

### Local Development Tips

- Use `pytest tests/ -v` to run tests
- Enable debug logging in `.env`
- Monitor `/Logs/` for audit trails

---

## Cloud VM Deployment

### Oracle Cloud (Free Tier)

1. **Create VM instance**
   - Shape: VM.Standard.A1.Flex (free tier eligible)
   - OS: Ubuntu 22.04 LTS
   - Storage: 50GB+

2. **Configure firewall**
   ```bash
   # Only allow SSH (port 22)
   # No public HTTP/HTTPS needed for vault-only operation
   ```

3. **Install dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3.11-venv git
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

4. **Deploy application**
   ```bash
   git clone https://github.com/muhammadhamza718/Hackathon-0.git
   cd Hackathon-0/sentinel
   uv sync
   ```

5. **Configure systemd service**
   ```ini
   # /etc/systemd/system/ai-employee.service
   [Unit]
   Description=AI Employee Sentinel
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/Hackathon-0/sentinel
   Environment=PATH=/home/ubuntu/.local/bin:%H
   ExecStart=/home/ubuntu/.local/bin/uv run python -m sentinel
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

6. **Enable and start**
   ```bash
   sudo systemctl enable ai-employee
   sudo systemctl start ai-employee
   sudo systemctl status ai-employee
   ```

### AWS EC2 Deployment

Similar to Oracle Cloud, with these adjustments:

1. **Instance type**: t3.micro (free tier eligible)
2. **Security group**: Allow only SSH
3. **IAM role**: Attach if using AWS services

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy and install dependencies
COPY pyproject.toml .
RUN uv pip install -r pyproject.toml

# Copy application
COPY . .

# Create vault directories
RUN mkdir -p /vault/Inbox /vault/Needs_Action /vault/Done \
    /vault/Pending_Approval /vault/Approved /vault/Rejected \
    /vault/Plans /vault/Logs

# Run sentinel
CMD ["python", "-m", "sentinel"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  ai-employee:
    build: .
    volumes:
      - ./vault:/vault
      - ./.env:/app/.env:ro
    restart: unless-stopped
    environment:
      - VAULT_ROOT=/vault
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### Run with Docker

```bash
docker-compose up -d
docker-compose logs -f
```

---

## Security Hardening

### Environment Variables

Never commit `.env` files. Use:

```bash
# Set restrictive permissions
chmod 600 .env
```

### File Permissions

```bash
# Vault directories
chmod 700 Inbox Needs_Action Done Pending_Approval Approved Rejected Plans Logs

# Application files
chmod 755 sentinel/
chmod 644 sentinel/**/*.py
```

### Network Security

1. **Firewall rules**: Only allow necessary ports
2. **SSH hardening**:
   ```bash
   # /etc/ssh/sshd_config
   PermitRootLogin no
   PasswordAuthentication no
   PubkeyAuthentication yes
   ```

3. **Fail2ban**:
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

### Secrets Management

- Use environment variables for secrets
- Consider HashiCorp Vault for production
- Rotate API keys regularly
- Never log credentials

---

## Monitoring and Maintenance

### Log Monitoring

```bash
# Watch audit logs
tail -f Logs/*.json

# Check for errors
grep -r "error" Logs/ | tail -20
```

### Health Checks

```bash
# Check systemd service
systemctl status ai-employee

# Check process
ps aux | grep sentinel

# Check disk space
df -h
```

### Backup Strategy

1. **Vault backup** (daily)
   ```bash
   tar -czf vault-backup-$(date +%Y%m%d).tar.gz /path/to/vault
   ```

2. **Configuration backup**
   ```bash
   cp .env .env.backup.$(date +%Y%m%d)
   ```

3. **Offsite storage**
   - Use cloud storage (S3, GCS)
   - Encrypt backups before upload

### Updates

```bash
# Pull latest changes
git pull origin main

# Update dependencies
uv sync --upgrade

# Restart service
sudo systemctl restart ai-employee
```

---

## Troubleshooting

### Common Issues

**Service won't start**
```bash
journalctl -u ai-employee -n 50
```

**Permission errors**
```bash
chown -R ubuntu:ubuntu /path/to/vault
```

**Memory issues**
```bash
# Check memory usage
free -h
# Consider adding swap if needed
```

### Support

- Check logs in `/Logs/`
- Review audit trail for failed actions
- Open GitHub issue for bugs
