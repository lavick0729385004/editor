"""Video composition - Instagram Native Resolution (1080x1350)"""

import os
import subprocess
import json
import logging
from PIL import Image
from config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, CONTENT_SIDE_WIDTH, CONTENT_HEIGHT,
    CONTENT_GAP, CORNER_RADIUS, TEMP_DIR, VIDEO_PRESET, VIDEO_CRF,
    VIDEO_BITRATE, AUDIO_BITRATE, FFMPEG_TIMEOUT, ENABLE_GPU_ENCODING
)

logger = logging.getLogger(__name__)


def check_ffmpeg_installed():
    """Check if FFmpeg and ffprobe are available"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=5, check=True)
        logger.info("✓ FFmpeg and ffprobe are available")
        return True
    except:
        logger.error("❌ FFmpeg not installed")
        return False


def get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_format',
            '-print_format', 'json', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data.get('format', {}).get('duration', 0))
            if duration > 0:
                logger.info(f"✓ Video duration: {duration:.2f}s")
                return duration
    except:
        pass
    
    logger.warning("Could not determine duration, using 5s default")
    return 5.0


def compose_final_video(headline_img, collage_img, video_path, logo_path, output_path):
    """Compose video - Instagram native 1080x1350
    
    Layout:
    - Headline at top (variable height, white bg, black text)
    - Content below: Left=collage (rounded), Right=video (rounded), gap between
    - Logo centered at 50% opacity
    """
    
    try:
        logger.info("🎬 Starting video composition...")
        
        # Get video duration
        duration = get_video_duration(video_path)
        if duration < 1:
            duration = 5.0
        
        logger.info(f"Creating {CANVAS_WIDTH}x{CANVAS_HEIGHT} Instagram video ({duration:.1f}s)")
        
        # Create static frame from headline + collage
        # Headline height may vary based on text
        headline_h = headline_img.height
        content_start_y = headline_h
        content_h = CANVAS_HEIGHT - headline_h
        
        static_frame = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
        static_frame.paste(headline_img, (0, 0))
        static_frame.paste(collage_img, (0, content_start_y))
        
        # Save frame temporarily
        static_frame_path = os.path.join(TEMP_DIR, 'static_frame.png')
        static_frame.save(static_frame_path, quality=95)
        logger.info(f"✓ Static frame saved")
        
        # Build FFmpeg command for composition
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-loop', '1', '-i', static_frame_path,  # Static frame
            '-i', video_path,  # Input video
        ]
        
        # Add logo if exists
        has_logo = os.path.exists(logo_path)
        if has_logo:
            cmd.extend(['-i', logo_path])
        
        # Filter graph: overlay video on right side
        if has_logo:
            filter_complex = (
                f"[0]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}[base];"
                f"[1]scale={CONTENT_SIDE_WIDTH}:{content_h}[v];"
                f"[base][v]overlay={CONTENT_SIDE_WIDTH + CONTENT_GAP}:{content_start_y}[with_video];"
                f"[2]scale={int(CANVAS_WIDTH*0.08)}:{int(CANVAS_WIDTH*0.08)}[logo];"
                f"[with_video][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:alpha=0.5[out]"
            )
            output_map = '[out]'
        else:
            filter_complex = (
                f"[0]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}[base];"
                f"[1]scale={CONTENT_SIDE_WIDTH}:{content_h}[v];"
                f"[base][v]overlay={CONTENT_SIDE_WIDTH + CONTENT_GAP}:{content_start_y}[out]"
            )
            output_map = '[out]'
        
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', output_map,
            '-map', '1:a',  # Audio from video
        ])
        
        # Try GPU encoding first, fallback to CPU
        use_gpu = False
        if ENABLE_GPU_ENCODING:
            result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=5)
            if 'h264_nvenc' in result.stdout:
                use_gpu = True
                logger.info("⚡ Using GPU acceleration (h264_nvenc)")
                cmd.extend([
                    '-c:v', 'h264_nvenc',
                    '-preset', 'fast',
                    '-rc', 'vbr',
                    '-cq', str(VIDEO_CRF),
                ])
        
        if not use_gpu:
            logger.info("Using CPU encoding (libx264)")
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', VIDEO_PRESET,
                '-crf', str(VIDEO_CRF),
                '-profile:v', 'high',
            ])
        
        cmd.extend([
            '-c:a', 'aac',
            '-b:a', AUDIO_BITRATE,
            '-shortest',
            '-t', str(int(duration) + 1),
            '-movflags', 'faststart',
            '-pix_fmt', 'yuv420p',
            output_path
        ])
        
        logger.info(f"Running FFmpeg: {VIDEO_PRESET} preset, CRF {VIDEO_CRF}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr[:500]}")
            return False
        
        if not os.path.exists(output_path):
            logger.error("Output file not created")
            return False
        
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"✓ Video created: {size_mb:.1f}MB")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout after {FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"Error composing video: {e}")
        return False
