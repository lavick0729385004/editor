#!/bin/bash

# Instagram Video Editor Bot - Quick Setup Script
# Run: bash setup.sh

set -e

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🎬 Instagram Video Editor Bot - VPS Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}→${NC} Checking Python version..."
python3 --version || (echo -e "${RED}✗${NC} Python 3 not found" && exit 1)
echo -e "${GREEN}✓${NC} Python found"

# Check FFmpeg
echo -e "${YELLOW}→${NC} Checking FFmpeg..."
ffmpeg -version > /dev/null 2>&1 || (echo -e "${RED}✗${NC} FFmpeg not found. Install with: sudo apt install -y ffmpeg ffprobe" && exit 1)
echo -e "${GREEN}✓${NC} FFmpeg found"

# Create virtual environment
echo -e "${YELLOW}→${NC} Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${GREEN}✓${NC} Virtual environment already exists"
fi

# Activate environment
echo -e "${YELLOW}→${NC} Activating environment..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} Environment activated"

# Install requirements
echo -e "${YELLOW}→${NC} Installing Python requirements..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
echo -e "${GREEN}✓${NC} Requirements installed"

# Create directories
echo -e "${YELLOW}→${NC} Creating directories..."
mkdir -p assets/fonts
mkdir -p temp
echo -e "${GREEN}✓${NC} Directories created"

# Check for logo
echo -e "${YELLOW}→${NC} Checking for logo..."
if [ -f "assets/logo.png" ]; then
    echo -e "${GREEN}✓${NC} Logo found: assets/logo.png"
else
    echo -e "${YELLOW}⚠${NC} No logo found. Please place your transparent PNG at: assets/logo.png"
fi

# Test FFmpeg with config
echo -e "${YELLOW}→${NC} Verifying FFmpeg and config..."
python3 -c "
from video_composer import check_ffmpeg_installed
from config import LOGO_PATH, TEMP_DIR
import os

if check_ffmpeg_installed():
    print('${GREEN}✓${NC} FFmpeg working')
else:
    print('${RED}✗${NC} FFmpeg check failed')
    exit(1)

if os.path.exists(LOGO_PATH):
    print('${GREEN}✓${NC} Logo path valid')
else:
    print('${YELLOW}⚠${NC} Logo not found at:', LOGO_PATH)

print('${GREEN}✓${NC} Config verified')
" || exit 1

# Summary
echo ""
echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Add your bot token to config.py (if not already done)"
echo "2. Place your transparent logo in: assets/logo.png"
echo "3. Optionally place Impact font in: assets/fonts/impact.ttf"
echo ""
echo "🚀 Start the bot:"
echo "   source venv/bin/activate"
echo "   python3 bot.py"
echo ""
echo "📚 For production deployment, see: VPS_DEPLOYMENT.md"
echo ""
