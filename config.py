"""Configuration for Telegram Video Editor Bot - VPS Optimized"""

# Telegram Bot Token
BOT_TOKEN = "8145841033:AAEK1LsjRBQfGeMj9GC918oXoSJ6oc10kwM"

# ============ CANVAS SETTINGS ============
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
CANVAS_BACKGROUND = (255, 255, 255)  # White

# Section dimensions
HEADLINE_HEIGHT = 200
CONTENT_HEIGHT = CANVAS_HEIGHT - HEADLINE_HEIGHT
CONTENT_SIDE_WIDTH = CANVAS_WIDTH // 2

# ============ HEADLINE SETTINGS ============
HEADLINE_PADDING = 25
HEADLINE_FONT_SIZE = 45
HEADLINE_TEXT_COLOR = (0, 0, 0)  # Black
HEADLINE_BG_COLOR = (255, 255, 255)  # White

# ============ LOGO SETTINGS ============
LOGO_SIZE = 100
LOGO_OPACITY = 0.5

# ============ IMAGE UPSCALING SETTINGS ============
# Upscale factor for low-res images (1.0 = no upscale, 2.0 = 2x upscale like Topaz Proteus)
UPSCALE_FACTOR = 1.8  # Advanced upscaling like Topaz Proteus
ENABLE_UPSCALING = True
# Image quality: 1=poor, 95=excellent (higher = slower)
IMAGE_QUALITY = 95  # Maximum quality for Instagram
# Resampling filter: 0=NEAREST, 1=LANCZOS (best), 2=BILINEAR, 3=BICUBIC
RESAMPLE_FILTER = 1  # LANCZOS (best quality)
# Use advanced upscaling algorithm (like Proteus/professional upscalers)
ADVANCED_UPSCALING_ENABLED = True
# Number of upscaling steps for multi-pass upscaling
UPSCALE_STEPS = 3

# ============ VIDEO ENCODING SETTINGS ============
# Preset: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
# faster = less quality but quick | slow = better quality but slower
VIDEO_PRESET = "fast"  # Faster encoding for quick turnaround
# CRF (quality): 0-51, lower=better. 23 is default, 18-23 is high quality
VIDEO_CRF = 18  # Very high quality for Instagram
# Bitrate (kbps) - None = use CRF, or specify like "8000k"
VIDEO_BITRATE = None
# Audio bitrate
AUDIO_BITRATE = "256k"  # Higher audio quality

# ============ HARDWARE ACCELERATION ============
# Enable hardware-accelerated encoding if available (CUDA/NVENC for NVIDIA)
ENABLE_GPU_ENCODING = True
# GPU device to use (-1 = auto, 0 = first GPU)
GPU_DEVICE_ID = -1

# ============ FILE PATHS ============
ASSETS_DIR = "assets"
FONTS_DIR = "assets/fonts"
TEMP_DIR = "temp"
LOGO_PATH = f"{ASSETS_DIR}/logo.png"
FONT_PATH = f"{FONTS_DIR}/impact.ttf"

# ============ FILE SIZE LIMITS ============
MAX_IMAGE_SIZE = 100  # MB (increased for VPS)
MAX_VIDEO_SIZE = 1000  # MB (increased for VPS)
MAX_TOTAL_SESSION = 1500  # Total MB per session

# ============ SUPPORTED FORMATS ============
SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
# All common video formats - bot accepts ANY video type
SUPPORTED_VIDEO_FORMATS = {
    '.mp4', '.mov', '.avi', '.mkv', '.mkv', '.webm', '.flv', '.wmv',  # Common
    '.3gp', '.3g2', '.m4v', '.ts', '.mts', '.m2ts',  # Mobile/Streaming
    '.mpeg', '.mpg', '.mpeg2', '.ogv', '.ogg',  # Legacy/Open
    '.mxf', '.vob', '.asf', '.rm', '.rmvb',  # Professional/Legacy
    '.f4v', '.hevc', '.h265', '.vp8', '.vp9',  # Modern codecs
}  # FFmpeg will handle any format

# ============ PROCESSING SETTINGS ============
# Enable parallel processing
ENABLE_PARALLEL_PROCESSING = True
# Threads for parallel operations
WORKER_THREADS = 4
# Timeout for FFmpeg operations (seconds)
FFMPEG_TIMEOUT = 600
# Keep temp files for debugging (set to False in production)
DEBUG_KEEP_TEMP = False

# ============ OPTIMIZATION ============
# Use faster image loading (reduced color depth if needed)
FAST_IMAGE_MODE = False
# Resize images before processing to reduce memory
MAX_INTERMEDIATE_SIZE = 2160  # pixels (1920x1080 = 2K)
# Enable frame caching
ENABLE_CACHE = True
