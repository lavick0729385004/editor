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
    """Get video duration in seconds using ffprobe with fallback methods"""
    
    # Method 1: Try modern ffprobe format query
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1:novalue=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            try:
                duration = float(result.stdout.strip())
                if duration > 0:
                    logger.info(f"✓ Video duration (method 1): {duration:.2f}s")
                    return duration
            except ValueError:
                logger.warning(f"Could not parse duration from output: {result.stdout}")
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe method 1 timeout")
    except Exception as e:
        logger.warning(f"ffprobe method 1 failed: {e}")
    
    # Method 2: Try JSON output format
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_format',
            '-print_format', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                duration = float(data.get('format', {}).get('duration', 0))
                if duration > 0:
                    logger.info(f"✓ Video duration (method 2): {duration:.2f}s")
                    return duration
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning(f"Could not parse JSON format: {e}")
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe method 2 timeout")
    except Exception as e:
        logger.warning(f"ffprobe method 2 failed: {e}")
    
    # Method 3: Get duration from video stream
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1:novalue=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            try:
                duration = float(result.stdout.strip())
                if duration > 0:
                    logger.info(f"✓ Video duration (method 3 - stream): {duration:.2f}s")
                    return duration
            except ValueError:
                logger.warning(f"Could not parse stream duration: {result.stdout}")
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe method 3 timeout")
    except Exception as e:
        logger.warning(f"ffprobe method 3 failed: {e}")
    
    # Method 4: Use ffmpeg to get duration (last resort)
    try:
        cmd = ['ffmpeg', '-i', video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Parse duration from ffmpeg stderr output: "Duration: HH:MM:SS.ms"
        for line in result.stderr.split('\n'):
            if 'Duration:' in line:
                # Extract duration string
                duration_str = line.split('Duration:')[1].split(',')[0].strip()
                # Parse HH:MM:SS.ms format
                parts = duration_str.split(':')
                if len(parts) == 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    duration = hours * 3600 + minutes * 60 + seconds
                    if duration > 0:
                        logger.info(f"✓ Video duration (method 4 - ffmpeg): {duration:.2f}s")
                        return duration
    except Exception as e:
        logger.warning(f"ffmpeg method 4 failed: {e}")
    
    # Fallback: Return default short duration (will create short video)
    logger.warning("⚠️ Could not determine video duration, using default 5 seconds")
    return 5.0  # Safer default than 0





def compose_final_video(headline_img, collage_img, video_path, logo_path, output_path):
    """
    Compose final video with hardware acceleration and optimized encoding:
    - Headline and collage on left side
    - Video on right side
    - Logo at center with 50% opacity
    - Same duration as input video
    - GPU-accelerated encoding when available
    - Fast turnaround with high quality
    """
    
    try:
        from config import ENABLE_GPU_ENCODING, GPU_DEVICE_ID, VIDEO_PRESET, VIDEO_CRF, AUDIO_BITRATE, FFMPEG_TIMEOUT, ENABLE_VIDEO_UPSCALING, VIDEO_UPSCALE_FACTOR
        
        # Get video duration (will use fallback methods if needed)
        duration = get_video_duration(video_path)
        
        if duration < 1:
            logger.warning(f"⚠️ Video duration {duration}s is very short, using minimum 5s")
            duration = 5.0
        
        logger.info(f"Creating final UHD 4K video with {duration:.2f}s duration")
        
        # Create static image frame (headline + collage)
        static_frame = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
        static_frame.paste(headline_img, (0, 0))
        static_frame.paste(collage_img, (0, HEADLINE_HEIGHT))
        
        # Save static frame temporarily with highest quality
        static_frame_path = os.path.join(TEMP_DIR, 'static_frame.png')
        static_frame.save(static_frame_path, quality=98, optimize=False)
        logger.info(f"Saved 4K static frame: {static_frame_path} ({CANVAS_WIDTH}x{CANVAS_HEIGHT})")
        
        right_side_x = CONTENT_SIDE_WIDTH
        right_side_y = HEADLINE_HEIGHT
        
        # Build optimized FFmpeg command with video upscaling
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
        
        # Build filter complex with video upscaling
        if has_logo:
            if ENABLE_VIDEO_UPSCALING:
                # Upscale video input for better quality
                filter_complex = (
                    f"[0]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}[base];"
                    f"[1]scale={int(CONTENT_SIDE_WIDTH * VIDEO_UPSCALE_FACTOR)}:{int(CONTENT_HEIGHT * VIDEO_UPSCALE_FACTOR)},scale={CONTENT_SIDE_WIDTH}:{CONTENT_HEIGHT}[v];"
                    f"[base][v]overlay={right_side_x}:{right_side_y}[with_video];"
                    f"[2]scale=100:100[logo];"
                    f"[with_video][logo]overlay="
                    f"(main_w-overlay_w)/2:(main_h-overlay_h)/2:alpha=0.5[out]"
                )
            else:
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
            if ENABLE_VIDEO_UPSCALING:
                filter_complex = (
                    f"[0]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}[base];"
                    f"[1]scale={int(CONTENT_SIDE_WIDTH * VIDEO_UPSCALE_FACTOR)}:{int(CONTENT_HEIGHT * VIDEO_UPSCALE_FACTOR)},scale={CONTENT_SIDE_WIDTH}:{CONTENT_HEIGHT}[v];"
                    f"[base][v]overlay={right_side_x}:{right_side_y}[out]"
                )
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
        ])
        
        # Try GPU encoding first, fall back to CPU if it fails
        use_gpu = False
        if ENABLE_GPU_ENCODING:
            result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=5)
            if 'h264_nvenc' in result.stdout or 'hevc_nvenc' in result.stdout:
                use_gpu = True
                logger.info("⚡ GPU encoder detected, attempting GPU encoding...")
        
        if use_gpu:
            gpu_cmd = cmd.copy()
            gpu_cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'fast',
                '-rc', 'vbr',
                '-cq', str(VIDEO_CRF),
                '-b:v', '0',
                '-c:a', 'aac',
                '-b:a', AUDIO_BITRATE,
                '-shortest',
                '-t', str(int(duration) + 1),
                '-movflags', 'faststart',
                '-pix_fmt', 'yuv420p',
                output_path
            ])
            
            logger.info("Running FFmpeg with GPU (h264_nvenc)...")
            result = subprocess.run(gpu_cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
            
            if result.returncode != 0:
                logger.warning(f"GPU encoding failed: {result.stderr[:200]}")
                logger.warning("Falling back to CPU encoding...")
                # Remove output file if partially created
                if os.path.exists(output_path):
                    os.remove(output_path)
                use_gpu = False
            else:
                logger.info("✓ GPU encoding successful!")
                return True
        
        # CPU fallback encoding
        if not use_gpu:
            cpu_cmd = cmd.copy()
            cpu_cmd.extend([
                '-c:v', 'libx264',
                '-preset', VIDEO_PRESET,
                '-crf', str(VIDEO_CRF),
                '-tune', 'film',
                '-profile:v', 'high',
                '-level:v', '4.2',
                '-c:a', 'aac',
                '-b:a', AUDIO_BITRATE,
                '-shortest',
                '-t', str(int(duration) + 1),
                '-movflags', 'faststart',
                '-pix_fmt', 'yuv420p',
                output_path
            ])
            
            logger.info(f"Running FFmpeg with CPU (libx264) preset={VIDEO_PRESET}, crf={VIDEO_CRF}...")
            result = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
        
        if not os.path.exists(output_path):
            logger.error("Output file was not created")
            return False
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"✓ Video created successfully: {output_path} ({file_size:.1f}MB)")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout after {FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"Error composing video: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
