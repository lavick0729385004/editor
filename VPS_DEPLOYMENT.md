# Instagram Video Editor Bot - VPS Deployment Guide

## Quick Start

### 1. Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install -y python3.10 python3.10-venv python3-pip

# Install FFmpeg (critical)
sudo apt install -y ffmpeg ffprobe

# Verify FFmpeg
ffmpeg -version
ffprobe -version
```

### 2. Setup Project

```bash
# Create project directory
mkdir -p ~/instagram-video-editor
cd ~/instagram-video-editor

# Create virtual environment
python3.10 -m venv venv

# Activate environment
source venv/bin/activate

# Clone or copy project files
# (Copy all .py files and assets/ folder)

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install psutil  # For system monitoring

# Create assets directory with your logo
mkdir -p assets/fonts
# Place your transparent logo.png in assets/
cp /path/to/your/logo.png assets/logo.png
```

### 3. Configuration

Edit `config.py` for your VPS:

```python
# For VPS with limited resources:
VIDEO_PRESET = "faster"  # faster encoding
VIDEO_CRF = 20           # high quality (18-23 range)

# For more powerful VPS:
VIDEO_PRESET = "medium"  # better quality
VIDEO_CRF = 18
```

### 4. Run Bot

```bash
# Development
python3 bot.py

# Production (with logging)
python3 bot.py > bot.log 2>&1 &

# Or use systemd (recommended)
```

## Systemd Service (Recommended)

### Create service file

```bash
sudo nano /etc/systemd/system/telegram-video-bot.service
```

Add this content:

```ini
[Unit]
Description=Instagram Video Editor Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/instagram-video-editor
Environment="PATH=/home/ubuntu/instagram-video-editor/venv/bin"
ExecStart=/home/ubuntu/instagram-video-editor/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/instagram-video-editor/bot.log
StandardError=append:/home/ubuntu/instagram-video-editor/bot.log

[Install]
WantedBy=multi-user.target
```

### Enable and start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable telegram-video-bot.service

# Start service
sudo systemctl start telegram-video-bot.service

# Check status
sudo systemctl status telegram-video-bot.service

# View logs
sudo journalctl -u telegram-video-bot.service -f
```

## Performance Optimization

### For Low-Resource VPS (1-2 GB RAM)

```python
# In config.py:
VIDEO_PRESET = "ultrafast"
VIDEO_CRF = 23           # Slightly lower quality for speed
ENABLE_UPSCALING = False  # Disable upscaling
MAX_INTERMEDIATE_SIZE = 1080  # Reduce memory usage
```

### For Medium VPS (4-8 GB RAM)

```python
# In config.py (default settings)
VIDEO_PRESET = "faster"
VIDEO_CRF = 20
ENABLE_UPSCALING = True
```

### For High-Resource VPS (16+ GB RAM)

```python
# In config.py:
VIDEO_PRESET = "slow"
VIDEO_CRF = 18          # Very high quality
ENABLE_UPSCALING = True
MAX_INTERMEDIATE_SIZE = 4320  # Allow larger intermediates
```

## Monitoring

### Check bot status

```bash
# View logs
tail -f bot.log

# Check memory usage
free -h

# Check disk space
df -h

# Check FFmpeg availability
which ffmpeg ffprobe
```

### Auto-cleanup old files

Add to crontab:

```bash
crontab -e
```

Add this line:

```bash
# Clean temp files daily at 2 AM
0 2 * * * cd /home/ubuntu/instagram-video-editor && python3 -c "from utils import cleanup_old_sessions; cleanup_old_sessions()"
```

## Troubleshooting

### FFmpeg not found

```bash
# Check installation
which ffmpeg
which ffprobe

# If not found, reinstall
sudo apt remove ffmpeg
sudo apt install -y ffmpeg ffprobe

# Verify
ffmpeg -version
```

### Bot crashes on video processing

1. Check RAM availability:
   ```bash
   free -h
   ```

2. Check disk space:
   ```bash
   df -h
   ```

3. Reduce quality in config.py:
   ```python
   VIDEO_PRESET = "faster"
   VIDEO_CRF = 23
   ```

### Slow video processing

1. Check CPU usage:
   ```bash
   top
   ```

2. Reduce resolution:
   ```python
   MAX_INTERMEDIATE_SIZE = 1080
   ```

3. Use faster preset:
   ```python
   VIDEO_PRESET = "ultrafast"
   ```

### Out of disk space

```bash
# Clean old sessions
python3 -c "from utils import cleanup_old_sessions; cleanup_old_sessions(max_age_hours=6)"

# Or manually clean temp folder
rm -rf temp/*
```

## SSL/HTTPS (Optional - Better for Production)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Request certificate
sudo certbot certonly --standalone -d yourdomain.com
```

## Backup

```bash
# Backup bot logs and config
tar -czf bot_backup_$(date +%Y%m%d).tar.gz *.py config.py bot.log assets/

# Store in cloud or external storage
```

## Upgrade Dependencies

```bash
# Activate venv
source venv/bin/activate

# Upgrade packages
pip install --upgrade -r requirements.txt
```

## Performance Tips

1. **Use SSD** - Faster disk I/O
2. **Allocate at least 4GB RAM** - For smooth video processing
3. **FFmpeg hardware acceleration** - If supported:
   ```bash
   ffmpeg -hwaccels
   ```
4. **Monitor disk usage** - Keep 20% free space
5. **Regular cleanup** - Remove old temp files

## Environment Variables (Optional)

Create `.env` file:

```bash
BOT_TOKEN=your_token_here
TEMP_DIR=/tmp/video-editor
LOG_LEVEL=INFO
VIDEO_PRESET=faster
VIDEO_CRF=20
```

Then load in bot.py:

```python
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
```

## Advanced: Docker Deployment

```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "bot.py"]
```

```bash
# Build
docker build -t video-bot .

# Run
docker run -d --name video-bot video-bot
```

## Support

For issues:
1. Check `bot.log` for errors
2. Verify FFmpeg is installed
3. Check system resources
4. Review `config.py` settings
5. Check bot token is correct

## License & Credits

Instagram Video Editor Bot - VPS Optimized Version
Designed for high-performance Telegram video processing
