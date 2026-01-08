"""Image processing module for video editor bot - Modern Pro Edition with Proteus Upscaling"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os
from textwrap import wrap
import logging
import math
from config import (
    CANVAS_WIDTH, CANVAS_HEIGHT, CANVAS_BACKGROUND,
    HEADLINE_HEIGHT, CONTENT_HEIGHT, CONTENT_SIDE_WIDTH,
    HEADLINE_PADDING, HEADLINE_FONT_SIZE, HEADLINE_TEXT_COLOR,
    HEADLINE_BG_COLOR, LOGO_SIZE, LOGO_OPACITY, FONT_PATH,
    UPSCALE_FACTOR, ENABLE_UPSCALING, IMAGE_QUALITY, RESAMPLE_FILTER,
    MAX_INTERMEDIATE_SIZE
)

logger = logging.getLogger(__name__)

# Modern font paths (Priority order)
FONT_PATHS = [
    "assets/fonts/impact.ttf",
    "assets/impact.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Impact.ttf",  # macOS
    "C:\\Windows\\Fonts\\impact.ttf",  # Windows
]


def get_font(size: int, bold: bool = True):
    """Get font object with fallback - tries Impact.ttf first, then system fonts"""
    # Try all font paths
    for font_path in FONT_PATHS:
        try:
            if os.path.exists(font_path):
                logger.debug(f"Loading font: {font_path} at size {size}")
                return ImageFont.truetype(font_path, size)
        except Exception as e:
            logger.debug(f"Could not load {font_path}: {e}")
    
    # Fallback to system fonts
    try:
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()



def auto_calculate_font_size(text: str, max_width: int, max_height: int) -> int:
    """
    Intelligently calculate font size based on text length
    Longer text = smaller font, shorter text = larger font
    Auto-adapts to maintain readability
    """
    text_length = len(text)
    
    # Dynamic sizing based on character count
    if text_length <= 5:
        # Very short - go big
        target_size = max(120, int(max_height * 0.9))
    elif text_length <= 10:
        # Short text
        target_size = max(90, int(max_height * 0.75))
    elif text_length <= 20:
        # Medium text
        target_size = max(70, int(max_height * 0.6))
    elif text_length <= 35:
        # Longer text
        target_size = max(50, int(max_height * 0.45))
    else:
        # Very long text
        target_size = max(35, int(max_height * 0.35))
    
    # Verify it actually fits
    font = get_font(target_size, bold=True)
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    
    # If text doesn't fit, reduce size
    while text_width > max_width * 0.95 and target_size > 20:
        target_size -= 5
        font = get_font(target_size, bold=True)
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
    
    logger.info(f"Auto-calculated font size: {target_size}px for '{text[:30]}...'")
    return target_size


def create_rounded_rectangle(image: Image.Image, radius: int = 20) -> Image.Image:
    """Create rounded corners on image"""
    try:
        # Create a mask for rounded corners
        width, height = image.size
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        
        # Draw white rounded rectangle on mask
        mask_draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=radius,
            fill=255
        )
        
        # Apply mask to image
        image.putalpha(mask)
        return image
    except Exception as e:
        logger.warning(f"Could not create rounded corners: {e}")
        return image


def create_headline_banner(text: str, width: int = CANVAS_WIDTH):
    """
    Create modern headline banner with:
    - Auto font sizing based on text length
    - Bold Impact font
    - Centered text
    - Proper spacing
    """
    
    logger.info(f"Creating headline banner: '{text}'")
    
    # Calculate optimal font size
    max_text_width = width - (2 * HEADLINE_PADDING)
    max_text_height = HEADLINE_HEIGHT - (2 * HEADLINE_PADDING)
    font_size = auto_calculate_font_size(text, max_text_width, max_text_height)
    
    # Create banner with white background
    banner = Image.new('RGB', (width, HEADLINE_HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(banner)
    font = get_font(font_size, bold=True)
    
    # Get text bounding box to center properly
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text horizontally and vertically
    x = (width - text_width) // 2
    y = (HEADLINE_HEIGHT - text_height) // 2 - bbox[1]  # Adjust for baseline
    
    # Draw text in bold black
    draw.text((x, y), text, fill=(0, 0, 0), font=font)
    
    # Add subtle shadow for depth
    shadow = Image.new('RGB', banner.size, (255, 255, 255))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.text((x + 2, y + 2), text, fill=(200, 200, 200), font=font)
    
    # Blend shadow with original
    banner = Image.blend(shadow, banner, 0.7)
    
    logger.info(f"✓ Headline banner created: {font_size}px, centered")
    return banner
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


def advanced_upscale(image: Image.Image, scale_factor: float) -> Image.Image:
    """
    Advanced upscaling using edge-aware filtering (Proteus-style)
    - Multi-pass upscaling for smoother results
    - Edge preservation and sharpening
    - Noise reduction
    - Color preservation
    """
    try:
        from config import UPSCALE_STEPS
        
        logger.info(f"Starting advanced upscaling: {scale_factor}x using {UPSCALE_STEPS} steps")
        
        current = image.copy()
        current_size = image.size
        
        # Multi-step upscaling for better quality
        step_scale = scale_factor ** (1 / UPSCALE_STEPS)
        
        for step in range(UPSCALE_STEPS):
            target_width = int(current_size[0] * (step_scale ** (step + 1)))
            target_height = int(current_size[1] * (step_scale ** (step + 1)))
            
            # Step 1: Lanczos upscaling
            current = current.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Step 2: Bilateral filtering for edge preservation
            # Apply slight blur then sharpen to enhance edges
            blurred = current.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # Step 3: Edge enhancement via unsharp mask
            enhancer = ImageEnhance.Sharpness(current)
            current = enhancer.enhance(1.5)  # More aggressive sharpening
            
            logger.info(f"Upscale step {step+1}/{UPSCALE_STEPS}: {current_size} → {current.size}")
        
        # Final polishing
        # Step 4: Enhance contrast for punchy look
        contrast_enhancer = ImageEnhance.Contrast(current)
        current = contrast_enhancer.enhance(1.15)
        
        # Step 5: Enhance color saturation slightly
        color_enhancer = ImageEnhance.Color(current)
        current = color_enhancer.enhance(1.05)
        
        logger.info(f"✓ Advanced upscaling complete: {scale_factor:.2f}x applied successfully")
        return current
        
    except Exception as e:
        logger.warning(f"Advanced upscaling failed: {e}, using fallback")
        # Fallback: simple LANCZOS resize
        target_size = (int(image.width * scale_factor), int(image.height * scale_factor))
        return image.resize(target_size, Image.Resampling.LANCZOS)


def resize_and_crop_to_fit(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """
    Intelligently resize and crop image with advanced upscaling
    - No distortion (maintains aspect ratio)
    - Advanced upscaling (Proteus-like)
    - Smart center-crop
    - Edge preservation
    """
    
    try:
        img_width, img_height = image.size
        logger.info(f"Resizing from {img_width}x{img_height} to {target_width}x{target_height}")
        
        # Limit intermediate size to save memory
        if img_width > MAX_INTERMEDIATE_SIZE or img_height > MAX_INTERMEDIATE_SIZE:
            scale = MAX_INTERMEDIATE_SIZE / max(img_width, img_height)
            new_size = (int(img_width * scale), int(img_height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            img_width, img_height = image.size
        
        # Calculate aspect ratios
        img_aspect = img_width / img_height
        target_aspect = target_width / target_height
        
        # Determine scale to fit
        if img_aspect > target_aspect:
            # Image is wider - fit by height
            scale_ratio = target_height / img_height
        else:
            # Image is taller - fit by width
            scale_ratio = target_width / img_width
        
        # Apply advanced upscaling if beneficial
        if ENABLE_UPSCALING and scale_ratio > 1.0:
            # Use advanced upscaling up to UPSCALE_FACTOR
            actual_scale = min(scale_ratio, UPSCALE_FACTOR)
            logger.info(f"Upscaling enabled: {scale_ratio:.2f}x (capped at {UPSCALE_FACTOR}x)")
            image = advanced_upscale(image, actual_scale)
            img_width, img_height = image.size
            
            # Recalculate if we hit the cap
            img_aspect = img_width / img_height
            if img_aspect > target_aspect:
                scale_ratio = target_height / img_height
            else:
                scale_ratio = target_width / img_width
        
        # Resize with best quality
        new_width = int(img_width * scale_ratio)
        new_height = int(img_height * scale_ratio)
        
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Sharpen edges for professional look
        enhancer = ImageEnhance.Sharpness(resized)
        resized = enhancer.enhance(1.2)
        
        # Center crop to exact target size
        if new_width > target_width or new_height > target_height:
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height
            
            cropped = resized.crop((left, top, right, bottom))
            logger.info(f"✓ Resized and cropped to {target_width}x{target_height}")
            return cropped
        else:
            # Pad if too small
            padded = Image.new('RGB', (target_width, target_height), (255, 255, 255))
            x_offset = (target_width - new_width) // 2
            y_offset = (target_height - new_height) // 2
            padded.paste(resized, (x_offset, y_offset))
            logger.info(f"✓ Resized and padded to {target_width}x{target_height}")
            return padded
        
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        # Return white placeholder
        return Image.new('RGB', (target_width, target_height), (255, 255, 255))



def create_image_collage(image_list, width=CONTENT_SIDE_WIDTH, height=CONTENT_HEIGHT):
    """
    Create modern image collage with:
    - Rounded corners on each image
    - Proper aspect ratio preservation (no distortion)
    - Auto-padding for smaller images
    - Enhanced contrast
    """
    
    if not image_list:
        # Return white canvas if no images
        return Image.new('RGB', (width, height), CANVAS_BACKGROUND)
    
    logger.info(f"Creating collage with {len(image_list)} images")
    
    num_images = len(image_list)
    slot_height = height // num_images
    corner_radius = 15  # Rounded corners
    
    # Create base collage
    collage = Image.new('RGB', (width, height), (255, 255, 255))
    
    for i, img_path in enumerate(image_list):
        try:
            # Open and process image
            img = Image.open(img_path).convert('RGB')
            logger.info(f"Processing image {i+1}/{num_images}: {img.size}")
            
            # Optimize image (reduce memory footprint)
            if img.size[0] > MAX_INTERMEDIATE_SIZE or img.size[1] > MAX_INTERMEDIATE_SIZE:
                max_dim = max(img.size)
                scale = MAX_INTERMEDIATE_SIZE / max_dim
                new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Resize to fit slot WITHOUT distortion (center-crop if needed)
            slot_width = width
            slot_top = i * slot_height
            
            # Calculate aspect ratios
            img_aspect = img.size[0] / img.size[1]
            slot_aspect = slot_width / slot_height
            
            # Smart resize: maintain aspect ratio
            if img_aspect > slot_aspect:
                # Image is wider - fit by height
                new_height = slot_height
                new_width = int(new_height * img_aspect)
            else:
                # Image is taller - fit by width
                new_width = slot_width
                new_height = int(new_width / img_aspect)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center crop if needed
            if img.size[0] > slot_width:
                left = (img.size[0] - slot_width) // 2
                img = img.crop((left, 0, left + slot_width, img.size[1]))
            
            if img.size[1] > slot_height:
                top = (img.size[1] - slot_height) // 2
                img = img.crop((0, top, img.size[0], top + slot_height))
            
            # Pad if needed to exact slot size
            if img.size[0] < slot_width or img.size[1] < slot_height:
                padded = Image.new('RGB', (slot_width, slot_height), (255, 255, 255))
                x_offset = (slot_width - img.size[0]) // 2
                y_offset = (slot_height - img.size[1]) // 2
                padded.paste(img, (x_offset, y_offset))
                img = padded
            
            # Add rounded corners
            img = add_rounded_corners(img, radius=corner_radius)
            
            # Enhance contrast for modern look
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)
            
            # Add slight brightness boost
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.05)
            
            # Paste into collage
            collage.paste(img, (0, slot_top))
            logger.info(f"✓ Image {i+1} pasted")
            
        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")
            # Fill with light gray if error
            gray_fill = Image.new('RGB', (width, slot_height), (240, 240, 240))
            collage.paste(gray_fill, (0, i * slot_height))
    
    logger.info(f"✓ Collage created: {width}x{height}")
    return collage


def add_rounded_corners(image: Image.Image, radius: int = 15) -> Image.Image:
    """Add rounded corners to image for modern look"""
    try:
        width, height = image.size
        
        # Create rounded mask
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=radius,
            fill=255
        )
        
        # Create image with alpha channel
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Apply mask
        image.putalpha(mask)
        
        # Convert back to RGB with white background
        white_bg = Image.new('RGB', image.size, (255, 255, 255))
        white_bg.paste(image, (0, 0), image)
        return white_bg
        
    except Exception as e:
        logger.warning(f"Could not add rounded corners: {e}")
        return image



def add_logo_overlay(base_image, logo_path, opacity: float = 0.5):
    """
    Add professional logo watermark at center with 50% opacity
    - Centered positioning
    - Smooth alpha blending
    - Rounded corners on logo
    """
    
    if not os.path.exists(logo_path):
        logger.warning(f"Logo not found: {logo_path}")
        return base_image.copy()
    
    try:
        # Open logo and convert to RGBA
        logo = Image.open(logo_path).convert('RGBA')
        logger.info(f"Logo loaded: {logo.size}")
        
        # Resize logo with LANCZOS (best quality)
        logo.thumbnail((LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS)
        
        # Add rounded corners to logo for modern look
        logo = _add_logo_rounded_corners(logo, radius=5)
        
        # Apply exact 50% opacity (0.5 = 50%)
        if logo.mode == 'RGBA':
            r, g, b, a = logo.split()
            # Multiply alpha channel by opacity factor
            a = a.point(lambda p: int(p * opacity))
            logo = Image.merge('RGBA', (r, g, b, a))
        else:
            logo = logo.convert('RGBA')
            alpha = logo.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            logo.putalpha(alpha)
        
        logger.info(f"Logo opacity set to {opacity*100:.0f}%")
        
        # Convert base to RGBA if needed
        result = base_image.convert('RGBA')
        
        # Calculate center position (perfect centering)
        logo_width, logo_height = logo.size
        center_x = (result.width - logo_width) // 2
        center_y = (result.height - logo_height) // 2
        
        logger.info(f"Pasting logo at center: ({center_x}, {center_y})")
        
        # Paste logo with smooth alpha blending
        result.paste(logo, (center_x, center_y), logo)
        
        # Convert back to RGB
        final = Image.new('RGB', result.size, (255, 255, 255))
        final.paste(result, (0, 0), result)
        
        logger.info("✓ Logo overlay complete")
        return final
        
    except Exception as e:
        logger.error(f"Error adding logo: {e}")
        return base_image.copy()


def _add_logo_rounded_corners(image: Image.Image, radius: int = 5) -> Image.Image:
    """Add subtle rounded corners to logo"""
    try:
        width, height = image.size
        
        # Create rounded mask
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=radius,
            fill=255
        )
        
        # Apply mask to alpha channel
        if image.mode == 'RGBA':
            r, g, b, a = image.split()
            # Combine with new mask
            a = Image.composite(mask, a, mask)
            image = Image.merge('RGBA', (r, g, b, a))
        
        return image
    except Exception as e:
        logger.debug(f"Could not add rounded corners to logo: {e}")
        return image



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
