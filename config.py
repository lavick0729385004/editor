"""Configuration for Telegram Video Editor Bot - Instagram Native Resolution"""

# Telegram Bot Token
BOT_TOKEN = "8145841033:AAEK1LsjRBQfGeMj9GC918oXoSJ6oc10kwM"

# ============ CANVAS SETTINGS (Instagram Native) ============
CANVAS_WIDTH = 1080  # Instagram native width
CANVAS_HEIGHT = 1350  # Instagram 4:5 aspect ratio
CANVAS_BACKGROUND = (255, 255, 255)  # White

# Section dimensions
HEADLINE_HEIGHT = 200  # Flexible, based on text
CONTENT_HEIGHT = CANVAS_HEIGHT - HEADLINE_HEIGHT
CONTENT_SIDE_WIDTH = CANVAS_WIDTH // 2  # 540px per side

# Layout
CONTENT_GAP = 4  # Gap between left/right content
CORNER_RADIUS = 15  # Rounded corners on images/video

# ============ HEADLINE SETTINGS ============
HEADLINE_PADDING = 40  # Left/right padding
HEADLINE_FONT_SIZE_MIN = 36  # Minimum font size
HEADLINE_FONT_SIZE_MAX = 56  # Maximum font size
HEADLINE_TEXT_COLOR = (0, 0, 0)  # Pure black
HEADLINE_BG_COLOR = (255, 255, 255)  # Pure white
HEADLINE_LINE_SPACING = 1.2  # Line height multiplier

# ============ LOGO SETTINGS ============
LOGO_SIZE = 90
LOGO_OPACITY = 0.5

# ============ IMAGE SETTINGS ============
# Image quality: 85-95 is good for Instagram
IMAGE_QUALITY = 95
# Resampling filter: 1=LANCZOS (best quality)
RESAMPLE_FILTER = 1
# Enable upscaling for small images
ENABLE_UPSCALING = False  # Keep native resolution
UPSCALE_FACTOR = 1.0

# ============ VIDEO ENCODING SETTINGS ============
# Preset: fast, medium, slow (not ultrafast or veryslow)
VIDEO_PRESET = "medium"
# CRF (quality): 18-20 recommended for Instagram
VIDEO_CRF = 18
# Bitrate: None to use CRF
VIDEO_BITRATE = None
# Audio bitrate
AUDIO_BITRATE = "192k"

# ============ HARDWARE ACCELERATION ============
ENABLE_GPU_ENCODING = True
GPU_DEVICE_ID = -1

# ============ FILE PATHS ============
ASSETS_DIR = "assets"
FONTS_DIR = "assets/fonts"
TEMP_DIR = "temp"
LOGO_PATH = f"{ASSETS_DIR}/logo.png"
FONT_PATH = f"{FONTS_DIR}/impact.ttf"

# ============ FILE SIZE LIMITS ============
MAX_IMAGE_SIZE = 100  # MB
MAX_VIDEO_SIZE = 1000  # MB
MAX_TOTAL_SESSION = 1500  # Total MB per session

# ============ SUPPORTED FORMATS ============
SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
SUPPORTED_VIDEO_FORMATS = {
    '.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv',
    '.3gp', '.3g2', '.m4v', '.ts', '.mts', '.m2ts',
    '.mpeg', '.mpg', '.mpeg2', '.ogv', '.ogg',
    '.mxf', '.vob', '.asf', '.rm', '.rmvb',
    '.f4v', '.hevc', '.h265', '.vp8', '.vp9',
}

# ============ PROCESSING SETTINGS ============
ENABLE_PARALLEL_PROCESSING = True
WORKER_THREADS = 4
FFMPEG_TIMEOUT = 600
DEBUG_KEEP_TEMP = False

# ============ OPTIMIZATION ============
FAST_IMAGE_MODE = False
MAX_INTERMEDIATE_SIZE = 1080
ENABLE_CACHE = True
