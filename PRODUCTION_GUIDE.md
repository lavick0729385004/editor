# Production Deployment Guide - Enterprise Edition

## Overview

This guide covers deploying the Instagram Video Editor Bot for large-scale production environments, designed to handle YouTubers with 2M+ subscribers.

## Architecture Components

### 1. Core Systems
- **Job Queue**: Async job processing with priority, retries, and metrics
- **Rate Limiting**: Per-user and global limits with premium tier support
- **Error Recovery**: Automatic error handling with graceful degradation
- **Monitoring**: Real-time health checks and performance metrics
- **Database**: SQLite persistence for job history and analytics

### 2. Quality Presets

```
FAST (⚡)
├─ CRF: 23 (lower quality)
├─ Preset: veryfast
├─ Duration: 30s max
├─ Bitrate: 1500k
└─ Use case: Quick edits, stories

BALANCED (🎯)
├─ CRF: 20 (good quality)
├─ Preset: faster
├─ Duration: 60s max
├─ Bitrate: 2500k
└─ Use case: YouTube Shorts, TikTok, Reels

QUALITY (🎬)
├─ CRF: 18 (high quality)
├─ Preset: fast
├─ Duration: 120s max
├─ Resolution: 1440x1800
├─ Bitrate: 4000k
└─ Use case: Featured content, HD video

ULTRA (🎞️)
├─ CRF: 16 (very high quality)
├─ Preset: medium
├─ Duration: 300s max (5 min)
├─ Resolution: 1440x1800
├─ Bitrate: 6000k
└─ Use case: Main YouTube videos, professional content
```

### 3. Rate Limiting (for 2M+ subscriber creators)

**Default Limits:**
- Global: 100 videos/hour
- Per User: 20 videos/hour
- Per User Daily: 200 videos/day
- Premium (2x multiplier): 40/hour, 400/day

**For Large Creators:**
```python
# Make user premium
await rate_limiter.add_premium_user(user_id)

# Or adjust limits per creator
# Contact: Configure custom limits in production_config.py
```

## Deployment Steps

### Prerequisites

```bash
# System requirements
- Ubuntu 20.04+
- 4GB+ RAM (8GB recommended)
- 20GB+ free disk space
- Python 3.10+
- FFmpeg with all codecs

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip ffmpeg git
```

### 1. Clone and Setup

```bash
cd /opt/video-editor
git clone https://github.com/lavick0729385004/editor.git
cd editor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Create data directory for SQLite
mkdir -p data logs

# Create .env file
cat > .env << EOF
BOT_TOKEN=your_bot_token_here
TEMP_DIR=temp
DEBUG_KEEP_TEMP=False
MAX_CONCURRENT_JOBS=5
EOF

chmod 600 .env
```

### 3. Database Initialization

```python
# python3
from database import init_database
import asyncio

async def init():
    db = await init_database('data/video_editor.db')
    print("✓ Database initialized")

asyncio.run(init())
```

### 4. Start the Bot

**Manual:**
```bash
source venv/bin/activate
python3 bot.py
```

**With Systemd (Recommended):**
```bash
sudo cp systemd/video-editor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable video-editor
sudo systemctl start video-editor

# Monitor
sudo journalctl -u video-editor -f
```

**With Docker (Recommended for scaling):**
```dockerfile
FROM python:3.10-slim

WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
```

```bash
docker build -t video-editor:latest .
docker run -e BOT_TOKEN=your_token \
           -v $(pwd)/data:/app/data \
           -v $(pwd)/logs:/app/logs \
           video-editor:latest
```

## Monitoring & Operations

### Health Check

```python
from monitoring import get_health_check

health = await get_health_check()
status = await health.check_system()

print(status)
# {
#   'status': 'healthy',
#   'system': {
#       'cpu_percent': 45.2,
#       'memory_percent': 62.1,
#       'disk_percent': 35.8
#   },
#   'warnings': []
# }
```

### Job Queue Status

```python
from job_queue import get_job_queue

queue = await get_job_queue()
metrics = queue.get_metrics()

print(f"Queue size: {metrics['queue_size']}")
print(f"Active jobs: {metrics['active_jobs']}")
print(f"Success rate: {metrics['success_rate']:.1f}%")
print(f"Avg time: {metrics['avg_processing_time']:.1f}s")
```

### Analytics

```python
from database import get_database

db = await get_database()
analytics = db.get_analytics(hours=24)

print(f"Jobs (24h): {analytics['total_jobs']}")
print(f"Success rate: {analytics['success_rate']}")
print(f"Unique users: {analytics['unique_users']}")
print(f"Avg duration: {analytics['avg_processing_seconds']}s")
```

### Performance Monitoring

```python
# Prometheus metrics endpoint (add to bot.py)
from monitoring import MetricsExporter

@app.get("/metrics")
async def prometheus_metrics():
    health = await get_health_check()
    status = await health.check_system()
    return MetricsExporter.to_prometheus_format(status)

# Scrape with Prometheus
# curl http://localhost:8000/metrics
```

## Scaling Guidelines

### Load Capacity

| Max Concurrent Jobs | Memory | CPU | Disk/hour |
|:---:|:---:|:---:|:---:|
| 3 | 2GB | 40% | 10GB |
| 5 | 4GB | 60% | 15GB |
| 10 | 8GB | 80% | 30GB |
| 20+ | 16GB+ | Need load balancer | 60GB+ |

### Horizontal Scaling (Multiple Servers)

```yaml
# Setup with shared database
Server 1: bot1.py (uses shared DB)
Server 2: bot2.py (uses shared DB)
Server 3: bot3.py (uses shared DB)

Shared Storage:
  - NFS mount: /data (SQLite + outputs)
  - S3 bucket: video outputs backup
```

### Using Telegram Bot API Webhook (More Scalable)

```python
# Instead of polling, use webhook
application.run_webhook(
    listen="0.0.0.0",
    port=443,
    url_path="bot",
    webhook_url=f"https://yourdomain.com/bot"
)
```

## Performance Tuning

### FFmpeg Optimization

```bash
# Use hardware encoding if available
export FFMPEG_CMD="ffmpeg -hwaccel cuda -hwaccel_device 0"

# Or VA-API for Intel
export FFMPEG_CMD="ffmpeg -hwaccel vaapi -hwaccel_device /dev/dri/renderD128"
```

### Database Optimization

```bash
# Tune SQLite for high concurrency
# In database.py, configure:

# PRAGMA journal_mode = WAL;  (Write-Ahead Logging)
# PRAGMA synchronous = NORMAL;
# PRAGMA cache_size = 10000;
# PRAGMA temp_store = MEMORY;
```

### Queue Optimization

```python
# Adjust for your server
queue = JobQueue(
    max_concurrent_jobs=5,      # Match your CPU cores
    max_queue_size=100,         # Prevent OOM
    worker_timeout=600          # 10 min timeout
)
```

## Troubleshooting

### High CPU Usage

```bash
# 1. Check active jobs
ps aux | grep python

# 2. Monitor system
watch -n 1 'top -b -n 1 | head -20'

# 3. Enable degradation
# System automatically reduces quality when CPU > 80%
```

### High Memory Usage

```bash
# Check memory
free -h

# Cleanup old jobs
from database import get_database
db = await get_database()
db.cleanup_old_data(days=7)

# Reduce max_concurrent_jobs
```

### FFmpeg Errors

```bash
# Test FFmpeg
ffmpeg -version
ffprobe -version

# Check codec support
ffmpeg -codecs | grep h264

# Verify file integrity
ffprobe video.mp4 -show_format
```

### Database Corruption

```bash
# Backup
cp data/video_editor.db data/video_editor.db.backup

# Repair
sqlite3 data/video_editor.db "PRAGMA integrity_check;"

# Or recreate
rm data/video_editor.db
# Will be recreated on startup
```

## Security Considerations

### Bot Token Security

```bash
# Store in environment variable
export BOT_TOKEN="your_token_here"

# Never commit to git
echo "BOT_TOKEN=" >> .env
# Add to .gitignore
```

### File Validation

```python
# Implemented in bot.py:
- File extension validation
- MIME type checking
- File size limits
- Corrupted file detection
```

### Rate Limiting

```python
# Prevents abuse
- Per-user hourly limits
- Global concurrency limits
- Automatic temp file cleanup
- Failed job cleanup
```

## Backup & Disaster Recovery

```bash
# Backup database daily
0 2 * * * cp /opt/video-editor/data/video_editor.db /backup/db_$(date +\%Y\%m\%d).db

# Backup output videos to S3
aws s3 sync /opt/video-editor/outputs/ s3://my-bucket/ --delete

# Restore from backup
cp /backup/db_20240101.db /opt/video-editor/data/video_editor.db
systemctl restart video-editor
```

## API Integration

### Get Job Status

```python
from job_queue import get_job_queue

queue = await get_job_queue()
job = await queue.get_job_status("job_id_here")

if job:
    print(f"Status: {job.status.value}")
    print(f"Progress: {job.progress}%")
    print(f"Message: {job.status_message}")
```

### Programmatic Video Creation

```python
from job_queue import JobQueue
from production_config import QualityPreset

queue = await get_job_queue()

job = await queue.submit_job(
    user_id=12345,
    session_data={
        'headline': 'My Video Title',
        'images': ['/path/to/image1.jpg'],
        'video': '/path/to/video.mp4',
    },
    priority=JobPriority.HIGH,
    max_retries=3
)

# Check status
while True:
    status = await queue.get_job_status(job.job_id)
    if status.status == JobStatus.COMPLETED:
        print(f"Output: {status.output_file}")
        break
    await asyncio.sleep(1)
```

## Support & Updates

```bash
# Check for updates
cd /opt/video-editor
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Restart bot
sudo systemctl restart video-editor
```

---

**Last Updated**: 2026-01-08
**Version**: 2.0 Production
**For Support**: GitHub Issues or Email
