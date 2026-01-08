"""Video composition module using FFmpeg - Optimized for VPS"""

import os
import subprocess
import json
from PIL import Image
import logging
from config import (
    CANVAS_WIDTH, CONTENT_SIDE_WIDTH, CANVAS_HEIGHT, HEADLINE_HEIGHT,
    CONTENT_HEIGHT, TEMP_DIR, VIDEO_PRESET, VIDEO_CRF, VIDEO_BITRATE,
    AUDIO_BITRATE, FFMPEG_TIMEOUT
)

logger = logging.getLogger(__name__)


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1:novalue=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        duration = float(result.stdout.strip())
        logger.info(f"Video duration: {duration:.2f}s")
        return duration
    except subprocess.TimeoutExpired:
        logger.error("ffprobe timeout getting video duration")
        return 0
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
        return 0


def compose_final_video(headline_img, collage_img, video_path, logo_path, output_path):
    """
    Compose final video with high quality and fast encoding:
    - Headline and collage on left side
    - Video on right side
    - Logo at center with 50% opacity
    - Same duration as input video
    - Optimized for VPS performance
    """
    
    try:
        # Get video duration
        duration = get_video_duration(video_path)
        if duration == 0:
            raise Exception("Could not determine video duration")
        
        logger.info(f"Creating final video with {duration:.2f}s duration")
        
        # Create static image frame (headline + collage)
        static_frame = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
        static_frame.paste(headline_img, (0, 0))
        static_frame.paste(collage_img, (0, HEADLINE_HEIGHT))
        
        # Save static frame temporarily
        static_frame_path = os.path.join(TEMP_DIR, 'static_frame.png')
        static_frame.save(static_frame_path, quality=95)
        logger.info(f"Saved static frame: {static_frame_path}")
        
        right_side_x = CONTENT_SIDE_WIDTH
        right_side_y = HEADLINE_HEIGHT
        
        # Build optimized FFmpeg command for VPS
        # Using faster preset and CRF for quality
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite
            '-hide_banner',
            '-loglevel', 'error',
            '-loop', '1',
            '-i', static_frame_path,  # Static frame
            '-i', video_path,  # Video input
        ]
        
        # Add logo if exists
        if os.path.exists(logo_path):
            cmd.extend(['-i', logo_path])
            has_logo = True
        else:
            has_logo = False
        
        # Build filter complex
        if has_logo:
            filter_complex = (
                f"[0]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}[base];"
                f"[1]scale={CONTENT_SIDE_WIDTH}:{CONTENT_HEIGHT}[v];"
                f"[base][v]overlay={right_side_x}:{right_side_y}[with_video];"
                f"[2]scale=100:100[logo];"
                f"[with_video][logo]overlay="
                f"(main_w-overlay_w)/2:(main_h-overlay_h)/2:alpha=0.5[out]"
            )
            output_map = '[out]'
        else:
            filter_complex = (
                f"[0]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}[base];"
                f"[1]scale={CONTENT_SIDE_WIDTH}:{CONTENT_HEIGHT}[v];"
                f"[base][v]overlay={right_side_x}:{right_side_y}[out]"
            )
            output_map = '[out]'
        
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', output_map,
            '-map', '1:a',  # Audio from video
            '-c:v', 'libx264',
            '-preset', VIDEO_PRESET,  # fast/faster for VPS
            '-crf', str(VIDEO_CRF),  # Quality: 20 = high quality
            '-c:a', 'aac',
            '-b:a', AUDIO_BITRATE,
            '-shortest',
            '-t', str(duration),
            '-movflags', 'faststart',  # Stream-friendly
            output_path
        ])
        
        logger.info(f"Running FFmpeg with preset={VIDEO_PRESET}, crf={VIDEO_CRF}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
        
        if not os.path.exists(output_path):
            logger.error("Output file was not created")
            return False
        
        logger.info(f"Video created successfully: {output_path}")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout after {FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"Error composing video: {e}")
        return False


def compose_video_simple(headline_img, collage_img, video_path, output_path, duration):
    """
    Simpler video composition if complex filter fails
    Creates side-by-side layout without logo
    """
    
    try:
        logger.info("Using simplified video composition (fallback)")
        
        # Create static frame
        static_frame = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
        static_frame.paste(headline_img, (0, 0))
        static_frame.paste(collage_img, (0, HEADLINE_HEIGHT))
        
        static_path = os.path.join(TEMP_DIR, 'static_simple.png')
        static_frame.save(static_path, quality=95)
        
        # Simple overlay: video on right side
        right_side_x = CONTENT_SIDE_WIDTH
        right_side_y = HEADLINE_HEIGHT
        
        cmd = [
            'ffmpeg',
            '-y',
            '-hide_banner',
            '-loglevel', 'error',
            '-loop', '1',
            '-i', static_path,
            '-i', video_path,
            '-filter_complex', (
                f"[0:v]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}[base];"
                f"[1:v]scale={CONTENT_SIDE_WIDTH}:{CONTENT_HEIGHT}[v];"
                f"[base][v]overlay={right_side_x}:{right_side_y}"
            ),
            '-map', '[v]',
            '-map', '1:a',
            '-c:v', 'libx264',
            '-preset', VIDEO_PRESET,
            '-crf', str(VIDEO_CRF),
            '-c:a', 'aac',
            '-b:a', AUDIO_BITRATE,
            '-shortest',
            '-t', str(duration),
            '-movflags', 'faststart',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
        
        success = result.returncode == 0
        if not success:
            logger.error(f"Simplified composition failed: {result.stderr}")
        else:
            logger.info("Simplified composition succeeded")
        
        return success
        
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout after {FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"Error in simple video composition: {e}")
        return False


def check_ffmpeg_installed():
    """Check if FFmpeg is installed and accessible"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=5)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True, timeout=5)
        logger.info("FFmpeg and ffprobe are available")
        return True
    except Exception as e:
        logger.error(f"FFmpeg check failed: {e}")
        return False
