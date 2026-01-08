"""Image processing module for video editor bot - AI Enhanced"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os
from textwrap import wrap
import logging
from config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, CANVAS_BACKGROUND,
    HEADLINE_HEIGHT, CONTENT_HEIGHT, CONTENT_SIDE_WIDTH,
    HEADLINE_PADDING, HEADLINE_FONT_SIZE, HEADLINE_TEXT_COLOR,
    HEADLINE_BG_COLOR, LOGO_SIZE, LOGO_OPACITY, FONT_PATH,
    UPSCALE_FACTOR, ENABLE_UPSCALING, IMAGE_QUALITY, RESAMPLE_FILTER,
    MAX_INTERMEDIATE_SIZE
)

logger = logging.getLogger(__name__)


def get_font(size):
    """Get font object with fallback to default if TTF not available"""
    try:
        if os.path.exists(FONT_PATH):
            return ImageFont.truetype(FONT_PATH, size)
    except Exception as e:
        logger.debug(f"Could not load TTF font: {e}")
    
    # Fallback to default font
    return ImageFont.load_default()


def wrap_text(text, max_width, font):
    """Wrap text to fit within max_width"""
    lines = text.split('\n')
    wrapped_lines = []
    
    for line in lines:
        # Estimate characters per line
        char_width = max_width / 20  # Rough estimate
        chars_per_line = int(max_width / char_width)
        
        if chars_per_line > 0:
            wrapped = wrap(line, width=chars_per_line)
            wrapped_lines.extend(wrapped)
        else:
            wrapped_lines.append(line)
    
    return wrapped_lines


def calculate_font_size(text, max_width, max_height, initial_size=HEADLINE_FONT_SIZE):
    """Calculate optimal font size to fit text within bounds"""
    size = initial_size
    
    while size > 10:
        font = get_font(size)
        lines = wrap_text(text, max_width, font)
        
        # Calculate total height needed
        line_height = size + 10  # Add spacing between lines
        total_height = len(lines) * line_height
        
        if total_height <= max_height:
            return size, lines
        
        size -= 2
    
    return size, wrap_text(text, max_width, get_font(size))


def create_headline_banner(text, width=CANVAS_WIDTH, font_path=FONT_PATH):
    """Create headline banner with auto-wrapping and font scaling"""
    
    # Calculate font size and wrap text
    max_text_width = width - (2 * HEADLINE_PADDING)
    max_text_height = HEADLINE_HEIGHT - (2 * HEADLINE_PADDING)
    font_size, lines = calculate_font_size(text, max_text_width, max_text_height)
    
    # Create image
    banner = Image.new('RGB', (width, HEADLINE_HEIGHT), HEADLINE_BG_COLOR)
    draw = ImageDraw.Draw(banner)
    font = get_font(font_size)
    
    # Calculate total text height
    line_height = font_size + 10
    total_text_height = len(lines) * line_height
    
    # Center text vertically and horizontally
    y_start = (HEADLINE_HEIGHT - total_text_height) // 2
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        y = y_start + (i * line_height)
        
        draw.text((x, y), line, fill=HEADLINE_TEXT_COLOR, font=font)
    
    return banner


def resize_and_crop_to_fit(image, target_width, target_height):
    """Resize and center-crop image to fit target dimensions while maintaining aspect ratio"""
    
    try:
        img_width, img_height = image.size
        
        # Limit intermediate size to save memory
        if img_width > MAX_INTERMEDIATE_SIZE or img_height > MAX_INTERMEDIATE_SIZE:
            scale = MAX_INTERMEDIATE_SIZE / max(img_width, img_height)
            new_size = (int(img_width * scale), int(img_height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            img_width, img_height = image.size
        
        # Calculate scale ratio
        width_ratio = target_width / img_width
        height_ratio = target_height / img_height
        
        # Scale up to fit the larger dimension
        scale_ratio = max(width_ratio, height_ratio)
        
        # Apply upscaling if enabled and beneficial
        if ENABLE_UPSCALING and scale_ratio > 1.0:
            scale_ratio = min(scale_ratio, UPSCALE_FACTOR)  # Cap upscaling
        
        new_width = int(img_width * scale_ratio)
        new_height = int(img_height * scale_ratio)
        
        # Use best resampling filter
        resample = [Image.Resampling.NEAREST, Image.Resampling.LANCZOS, 
                   Image.Resampling.BILINEAR, Image.Resampling.BICUBIC][RESAMPLE_FILTER]
        
        # Resize image
        resized = image.resize((new_width, new_height), resample)
        
        # Sharpen slightly for better quality
        enhancer = ImageEnhance.Sharpness(resized)
        resized = enhancer.enhance(1.1)  # Slight sharpening
        
        # Center crop to exact target size
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        cropped = resized.crop((left, top, right, bottom))
        
        return cropped
    
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        # Return white placeholder
        return Image.new('RGB', (target_width, target_height), (255, 255, 255))


def create_image_collage(image_list, width=CONTENT_SIDE_WIDTH, height=CONTENT_HEIGHT):
    """Create image collage by stacking images vertically with quality optimization"""
    
    if not image_list:
        # Return white canvas if no images
        return Image.new('RGB', (width, height), CANVAS_BACKGROUND)
    
    num_images = len(image_list)
    slot_height = height // num_images
    
    # Create base collage
    collage = Image.new('RGB', (width, height), CANVAS_BACKGROUND)
    
    for i, img_path in enumerate(image_list):
        try:
            # Open and process image
            img = Image.open(img_path).convert('RGB')
            
            # Optimize image (reduce memory footprint)
            if img.size[0] > MAX_INTERMEDIATE_SIZE or img.size[1] > MAX_INTERMEDIATE_SIZE:
                max_dim = max(img.size)
                scale = MAX_INTERMEDIATE_SIZE / max_dim
                new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Resize and crop to fit slot
            slot_width = width
            slot_top = i * slot_height
            
            processed = resize_and_crop_to_fit(img, slot_width, slot_height)
            
            # Enhance contrast slightly for better quality
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.05)
            
            # Paste into collage
            collage.paste(processed, (0, slot_top))
            
        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")
            # Fill with white if error
            white_fill = Image.new('RGB', (width, slot_height), (255, 255, 255))
            collage.paste(white_fill, (0, i * slot_height))
    
    return collage


def add_logo_overlay(base_image, logo_path, opacity=LOGO_OPACITY):
    """Add logo watermark at center with specified opacity - High quality"""
    
    if not os.path.exists(logo_path):
        logger.warning(f"Logo not found: {logo_path}")
        return base_image.copy()
    
    try:
        # Open logo and convert to RGBA
        logo = Image.open(logo_path).convert('RGBA')
        
        # Resize logo with high quality
        logo.thumbnail((LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS)
        
        # Apply opacity via alpha channel
        alpha = logo.split()[3]  # Get alpha channel
        alpha = alpha.point(lambda p: int(p * opacity))
        logo.putalpha(alpha)
        
        # Convert base to RGBA if needed
        result = base_image.convert('RGBA')
        
        # Calculate center position
        logo_width, logo_height = logo.size
        center_x = (result.width - logo_width) // 2
        center_y = (result.height - logo_height) // 2
        
        # Paste logo with alpha blending
        result.paste(logo, (center_x, center_y), logo)
        
        # Convert back to RGB with quality optimization
        return result.convert('RGB')
        
    except Exception as e:
        logger.error(f"Error adding logo: {e}")
        return base_image.copy()


def create_static_frame(headline_img, collage_img, logo_path):
    """Combine headline, collage, and logo into single frame for video"""
    
    # Create base canvas
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), CANVAS_BACKGROUND)
    
    # Paste headline at top
    canvas.paste(headline_img, (0, 0))
    
    # Paste collage on left side
    content_start_y = HEADLINE_HEIGHT
    canvas.paste(collage_img, (0, content_start_y))
    
    # Add logo overlay on top of everything
    canvas = add_logo_overlay(canvas, logo_path)
    
    return canvas
