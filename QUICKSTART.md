# 🚀 Quick Start Guide

## For VPS Users

### 1️⃣ One-Command Setup

```bash
# SSH into your VPS and run:
cd /home/ubuntu  # or your user directory
git clone <your-repo> instagram-video-editor
cd instagram-video-editor
bash setup.sh
```

### 2️⃣ Add Your Logo

```bash
# Copy your transparent PNG logo to:
cp your_logo.png assets/logo.png

# Verify
ls -la assets/logo.png
```

### 3️⃣ Verify Bot Token

Open `config.py` and confirm:
```python
BOT_TOKEN = "8145841033:AAEK1LsjRBQfGeMj9GC918oXoSJ6oc10kwM"
```

✅ Already set!

### 4️⃣ Start Bot

**Quick test:**
```bash
source venv/bin/activate
python3 bot.py
```

**Production (background):**
```bash
# Using systemd (recommended)
sudo cp telegram-video-bot.service /etc/systemd/system/
sudo systemctl enable telegram-video-bot
sudo systemctl start telegram-video-bot
sudo systemctl status telegram-video-bot

# Or simple background
python3 bot.py > bot.log 2>&1 &
```

### 5️⃣ Test the Bot

1. Find your bot on Telegram
2. Send `/start`
3. Follow the prompts
4. Test with sample image and video

## ⚙️ Optimize for Your VPS

### Check Your VPS Specs

```bash
# CPU cores
nproc

# RAM
free -h

# Disk
df -h
```

### Adjust config.py

**Low-end VPS (512MB - 2GB RAM):**
```python
VIDEO_PRESET = "ultrafast"
VIDEO_CRF = 23
ENABLE_UPSCALING = False
MAX_INTERMEDIATE_SIZE = 720
```

**Medium VPS (4-8GB RAM):**
```python
VIDEO_PRESET = "faster"     # Default
VIDEO_CRF = 20
ENABLE_UPSCALING = True
MAX_INTERMEDIATE_SIZE = 1080
```

**High-end VPS (16GB+ RAM):**
```python
VIDEO_PRESET = "slow"
VIDEO_CRF = 18
ENABLE_UPSCALING = True
MAX_INTERMEDIATE_SIZE = 4320
```

## 🛠️ Troubleshooting

### Bot won't start

```bash
# Check Python
python3 --version

# Check FFmpeg
ffmpeg -version
ffprobe -version

# Check if port is available
netstat -tuln | grep 8080

# Check for error logs
tail -f bot.log
```

### FFmpeg not found

```bash
# Install FFmpeg
sudo apt update
sudo apt install -y ffmpeg ffprobe

# Verify
which ffmpeg
which ffprobe
```

### Out of memory

```bash
# Check usage
free -h
top

# Solution:
# 1. Reduce VIDEO_CRF to 22-24
# 2. Set ENABLE_UPSCALING = False
# 3. Restart bot
```

### Video processing fails

1. Check disk space: `df -h`
2. Check RAM: `free -h`
3. Review logs: `tail -f bot.log`
4. Try uploading smaller video
5. Reduce VIDEO_CRF value

## 📊 Monitor Your Bot

```bash
# View logs
tail -f bot.log

# Monitor resources while processing
watch -n 1 'free -h && echo "---" && df -h'

# Check bot process
ps aux | grep bot.py

# Restart bot
pkill -f "python3 bot.py"
python3 bot.py > bot.log 2>&1 &
```

## 🚀 Performance Tips

1. **Keep 20% disk free** - Prevents slowdown
2. **Monitor RAM** - Kill other services if needed
3. **Use SSD** - Much faster than HDD
4. **Regular cleanup** - `rm -rf temp/*`
5. **Update packages** - `pip install --upgrade -r requirements.txt`

## 📝 File Checklist

```
✓ bot.py                  # Main bot
✓ image_processor.py      # Image processing
✓ video_composer.py       # Video creation
✓ config.py              # Configuration
✓ utils.py               # Utilities
✓ requirements.txt       # Dependencies
✓ assets/logo.png        # Your logo ⭐
✓ assets/fonts/          # (optional fonts)
✓ temp/                  # Auto-created
✓ bot.log                # Auto-created
```

## 🎯 Expected Performance

**With default settings (faster preset, CRF 20):**

| Video Length | Images | Est. Time |
|------------|--------|-----------|
| 15 seconds | 1      | 30 sec    |
| 30 seconds | 2      | 60 sec    |
| 60 seconds | 3      | 2 min     |
| 120 seconds| 4      | 4 min     |

## 🔒 Security Notes

- Keep bot token secret (don't commit to git)
- Use systemd for auto-restart
- Monitor disk usage
- Clean old temp files regularly
- Use firewall rules if needed

## 📚 Documentation

- **Full setup:** See [VPS_DEPLOYMENT.md](VPS_DEPLOYMENT.md)
- **Features:** See [README.md](README.md)
- **Config options:** Edit `config.py`
- **Logs:** Check `bot.log`

## ✨ Features Included

✅ Auto-scaling headline text
✅ Smart image collage (1-N images)
✅ Video integration (right side)
✅ Logo watermark (centered, 50% opacity)
✅ High-quality output (CRF 20)
✅ Upscaling support
✅ Fast processing (faster preset)
✅ Error recovery
✅ Progress tracking
✅ Auto cleanup

## 🤝 Need Help?

1. Check `bot.log` - most issues are logged
2. Run `bash setup.sh` again - verifies everything
3. Test FFmpeg: `ffmpeg -version`
4. Check resources: `free -h` and `df -h`
5. Review [VPS_DEPLOYMENT.md](VPS_DEPLOYMENT.md)

---

**Your Instagram video editor is ready! 🎬**

Send `/start` to your bot and start creating videos! 🚀
