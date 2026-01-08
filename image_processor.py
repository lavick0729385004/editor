"""Image processing module - Professional Instagram Layout"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os
import logging
from textwrap import wrap
from config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, HEADLINE_HEIGHT, CONTENT_HEIGHT,
    CONTENT_SIDE_WIDTH, CONTENT_GAP, CORNER_RADIUS,
    HEADLINE_PADDING, HEADLINE_FONT_SIZE_MIN, HEADLINE_FONT_SIZE_MAX,
    HEADLINE_TEXT_COLOR, HEADLINE_BG_COLOR, HEADLINE_LINE_SPACING,
    LOGO_SIZE, LOGO_OPACITY, IMAGE_QUALITY, RESAMPLE_FILTER,
    MAX_INTERMEDIATE_SIZE, FONTS_DIR
)

logger = logging.getLogger(__name__)

FONT_PATHS = [
    "assets/fonts/impact.ttf",
    "assets/impact.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Impact.ttf",
    "C:\\Windows\\Fonts\\impact.ttf",
]


def get_font(size: int):
    """Get Impact/Arial Black bold font with fallback"""
    for font_path in FONT_PATHS:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except:
            pass
    return ImageFont.load_default()


def apply_rounded_corners(image: Image.Image, radius: int = CORNER_RADIUS, 
                         corners=['tl', 'tr', 'bl', 'br']) -> Image.Image:
    """Apply rounded corners to image using alpha channel
    
    Args:
        image: PIL Image
        radius: corner radius in pixels
        corners: list of corners to round ['tl', 'tr', 'bl', 'br']
    """
    # Convert to RGBA if needed
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create mask
    width, height = image.size
    mask = Image.new('L', (width, height), 255)
    mask_draw = ImageDraw.Draw(mask)
    
    # Draw corners
    if 'tl' in corners:
        mask_draw.ellipse([0, 0, radius*2, radius*2], fill=0)
    if 'tr' in corners:
        mask_draw.ellipse([width-radius*2, 0, width, radius*2], fill=0)
    if 'bl' in corners:
        mask_draw.ellipse([0, height-radius*2, radius*2, height], fill=0)
    if 'br' in corners:
        mask_draw.ellipse([width-radius*2, height-radius*2, width, height], fill=0)
    
    # Apply mask
    image.putalpha(mask)
    return image


def create_headline_banner(text: str) -> Image.Image:
    """Create professional headline with black text on white background
    
    - White background
    - Black bold Impact font
    - Center-aligned, multi-line
    - Auto-scaled font size
    """
    logger.info(f"Creating headline: '{text}'")
    
    # Calculate font size dynamically
    max_width = CANVAS_WIDTH - (2 * HEADLINE_PADDING)
    font_size = HEADLINE_FONT_SIZE_MAX
    font = get_font(font_size)
    
    # Find optimal font size
    while font_size > HEADLINE_FONT_SIZE_MIN:
        test_bbox = font.getbbox(text)
        test_width = test_bbox[2] - test_bbox[0]
        
        if test_width <= max_width:
            break
        
        font_size -= 2
        font = get_font(font_size)
    
    # Split into lines
    avg_char_width = font.getbbox('A')[2] - font.getbbox('A')[0]
    chars_per_line = max_width // avg_char_width
    lines = wrap(text, width=int(chars_per_line))
    
    # Calculate banner height based on lines
    line_height = int(font_size * HEADLINE_LINE_SPACING)
    actual_height = (len(lines) * line_height) + (2 * HEADLINE_PADDING)
    
    # Create banner
    banner = Image.new('RGB', (CANVAS_WIDTH, actual_height), HEADLINE_BG_COLOR)
    draw = ImageDraw.Draw(banner)
    
    # Draw text centered
    total_text_height = len(lines) * line_height
    y_start = (actual_height - total_text_height) // 2
    
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (CANVAS_WIDTH - line_width) // 2
        y = y_start + (i * line_height)
        
        draw.text((x, y), line, fill=HEADLINE_TEXT_COLOR, font=font)
    
    logger.info(f"✓ Headline created: {font_size}px, {len(lines)} lines, {actual_height}px height")
    return banner, actual_height


def create_image_collage(image_paths: list) -> Image.Image:
    """Create collage from images with rounded corners
    
    - 1 image: Full height, rounded all corners
    - 2 images: Stacked, top/bottom corners rounded
    - 3+ images: Equal split, rounded outer corners
    """
    logger.info(f"Creating collage with {len(image_paths)} images")
    
    # Load images
    images = []
    for path in image_paths:
        try:
            img = Image.open(path).convert('RGB')
            images.append(img)
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
    
    if not images:
        # Return white placeholder
        return Image.new('RGB', (CONTENT_SIDE_WIDTH, CONTENT_HEIGHT), (255, 255, 255))
    
    # Calculate dimensions per image
    num_images = len(images)
    if num_images == 1:
        img_height = CONTENT_HEIGHT
    else:
        img_height = (CONTENT_HEIGHT - ((num_images - 1) * CONTENT_GAP)) // num_images
    
    # Resize and crop images to fit
    processed = []
    for i, img in enumerate(images):
        # Center crop to fit slot
        img_w, img_h = img.size
        aspect = img_w / img_h
        target_aspect = CONTENT_SIDE_WIDTH / img_height
        
        if aspect > target_aspect:
            # Image is wider, crop sides
            new_w = int(img_h * target_aspect)
            crop_left = (img_w - new_w) // 2
            img = img.crop((crop_left, 0, crop_left + new_w, img_h))
        else:
            # Image is taller, crop top/bottom
            new_h = int(img_w / target_aspect)
            crop_top = (img_h - new_h) // 2
            img = img.crop((0, crop_top, img_w, crop_top + new_h))
        
        # Resize to exact dimensions
        img = img.resize((CONTENT_SIDE_WIDTH, img_height), Image.Resampling.LANCZOS)
        
        # Apply rounded corners (only outer corners)
        corners = []
        if i == 0:  # Top image
            corners.append('tl')
            if num_images == 1:  # Only image
                corners.extend(['tr', 'br'])
            corners.append('bl' if num_images > 1 else 'br')
        
        if num_images > 1 and i == num_images - 1:  # Bottom image
            corners.extend(['bl', 'br'])
        
        if num_images > 2 and 0 < i < num_images - 1:  # Middle images
            pass  # No rounded corners on middle images
        
        if num_images == 1:
            corners = ['tl', 'tr', 'bl', 'br']
        
        img = apply_rounded_corners(img, CORNER_RADIUS, corners)
        processed.append(img)
    
    # Stack images vertically
    collage = Image.new('RGBA', (CONTENT_SIDE_WIDTH, CONTENT_HEIGHT), (255, 255, 255, 0))
    y_offset = 0
    
    for img in processed:
        collage.paste(img, (0, y_offset), img if img.mode == 'RGBA' else None)
        y_offset += img.height + CONTENT_GAP
    
    # Convert back to RGB with white background
    result = Image.new('RGB', (CONTENT_SIDE_WIDTH, CONTENT_HEIGHT), (255, 255, 255))
    result.paste(collage, (0, 0), collage)
    
    logger.info(f"✓ Collage created: {CONTENT_SIDE_WIDTH}x{CONTENT_HEIGHT}")
    return result


def create_video_frame(video_path: str, width: int = CONTENT_SIDE_WIDTH, 
                      height: int = CONTENT_HEIGHT) -> Image.Image:
    """Create placeholder frame for video with rounded corners"""
    # For now, return dark placeholder with rounded corners
    frame = Image.new('RGB', (width, height), (50, 50, 50))
    frame = apply_rounded_corners(frame, CORNER_RADIUS, ['tr', 'br'])
    return frame


def create_final_layout(headline: Image.Image, headline_height: int,
                       collage: Image.Image, video_frame: Image.Image,
                       logo_path: str) -> Image.Image:
    """Combine all elements into final layout
    
    Structure:
    - Top: Headline (white bg, black text)
    - Bottom: Left=collage (rounded), Right=video (rounded), gap between
    - Overlay: Logo centered at 50% opacity
    """
    
    # Create base canvas
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
    
    # Paste headline (may be different height than expected)
    canvas.paste(headline, (0, 0))
    content_start_y = headline.height
    
    # Paste collage (left side)
    canvas.paste(collage, (0, content_start_y))
    
    # Paste video frame (right side)
    canvas.paste(video_frame, (CONTENT_SIDE_WIDTH + CONTENT_GAP, content_start_y))
    
    # Overlay logo at center with 50% opacity
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert('RGBA')
            
            # Resize logo
            logo_width = LOGO_SIZE
            aspect = logo.size[1] / logo.size[0]
            logo_height = int(logo_width * aspect)
            logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            
            # Adjust opacity
            logo.putalpha(int(255 * LOGO_OPACITY))
            
            # Center logo
            logo_x = (CANVAS_WIDTH - logo_width) // 2
            logo_y = (CANVAS_HEIGHT - logo_height) // 2
            
            canvas.paste(logo, (logo_x, logo_y), logo)
            logger.info(f"✓ Logo overlaid at ({logo_x}, {logo_y}) with {LOGO_OPACITY*100}% opacity")
        except Exception as e:
            logger.warning(f"Could not overlay logo: {e}")
    
    logger.info(f"✓ Final layout created: {CANVAS_WIDTH}x{CANVAS_HEIGHT}")
    return canvas
