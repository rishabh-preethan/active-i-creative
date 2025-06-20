import logging
import os
import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageColor
from typing import Optional, Tuple

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

FONTS_DIR = "/usr/share/fonts/truetype/dejavu/"
DEFAULT_FONT = "DejaVuSans-Bold.ttf"

def get_font(font_name: Optional[str], font_size: int) -> ImageFont.FreeTypeFont:
    font_path = os.path.join(FONTS_DIR, font_name) if font_name else os.path.join(FONTS_DIR, DEFAULT_FONT)
    try:
        return ImageFont.truetype(font_path, font_size)
    except Exception:
        return ImageFont.load_default()

def parse_color(color_str: str):
    try:
        return ImageColor.getrgb(color_str)
    except Exception:
        return (255, 255, 255)

def get_position(img_size: Tuple[int, int], text_size: Tuple[int, int], position: str, offset: Tuple[int, int] = (0, 0)):
    W, H = img_size
    w, h = text_size
    x_off, y_off = offset
    pos_map = {
        "center": ((W - w) // 2, (H - h) // 2),
        "top_left": (0, 0),
        "top_right": (W - w, 0),
        "bottom_left": (0, H - h),
        "bottom_right": (W - w, H - h),
        "top_center": ((W - w) // 2, 0),
        "bottom_center": ((W - w) // 2, H - h),
        "middle_left": (0, (H - h) // 2),
        "middle_right": (W - w, (H - h) // 2),
    }
    base = pos_map.get(position, pos_map["center"])
    x = base[0] + x_off
    y = base[1] + y_off
    # Clamp so text stays fully within the image
    x = max(0, min(x, W - w))
    y = max(0, min(y, H - h))
    return (x, y)

class TextOverlayImageHandler(NodeHandler):
    """Handler for overlaying text on images with various parameters."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict containing 'image_path'
            config: Dict with 'text', 'font_size', 'font_name', 'color', 'position', 'offset', 'bg_color', 'opacity', etc.
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"TextOverlayImage - Processing with config: {config}")
            image_path = inputs.get("image_path") or config.get("image_path")
            text = config.get("text", "Sample Text")
            font_size = int(config.get("font_size", 40))
            font_name = config.get("font_name", DEFAULT_FONT)
            color = config.get("color", "white")
            position = config.get("position", "center")
            offset = config.get("offset", (0, 0))
            if isinstance(offset, str):
                offset = tuple(map(int, offset.strip("() ").split(",")))
            bg_color = config.get("bg_color", None)
            opacity = float(config.get("opacity", 1.0))
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Input image file not found: {image_path}")
                return {"status": "error", "error": f"Input image not found: {image_path}"}
            if not image_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff")):
                logger.error(f"Invalid image file format: {image_path}")
                return {"status": "error", "error": f"Invalid image file format: {image_path}"}
            file_ext = Path(image_path).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"overlay_{unique_filename}")
            success = self.overlay_text(image_path, output_path, text, font_size, font_name, color, position, offset, bg_color, opacity)
            if not success or not os.path.exists(output_path):
                logger.error("Failed to overlay text or output file not created")
                return {"status": "error", "error": "Failed to overlay text or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in TextOverlayImage node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def overlay_text(self, image_path: str, output_path: str, text: str, font_size: int, font_name: str, color: str, position: str, offset: Tuple[int, int], bg_color: Optional[str], opacity: float):
        img = None
        try:
            logger.info(f"Loading image from: {image_path}")
            img = Image.open(image_path).convert("RGBA")
            txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            font = get_font(font_name, font_size)
            text_color = parse_color(color) + (int(255 * opacity),)
            text_size = draw.textbbox((0, 0), text, font=font)
            w = text_size[2] - text_size[0]
            h = text_size[3] - text_size[1]
            pos = get_position(img.size, (w, h), position, offset)
            # Draw background box if specified
            if bg_color:
                bg_rgba = parse_color(bg_color) + (int(255 * opacity),)
                draw.rectangle([pos, (pos[0] + w, pos[1] + h)], fill=bg_rgba)
            draw.text(pos, text, font=font, fill=text_color)
            combined = Image.alpha_composite(img, txt_layer)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            combined = combined.convert("RGB")
            combined.save(output_path)
            logger.info(f"Successfully created overlay image: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error overlaying text: {str(e)}")
            return False
        finally:
            if img is not None:
                try:
                    img.close()
                except Exception as e:
                    logger.warning(f"Warning: Error closing image: {str(e)}")

_handler = TextOverlayImageHandler()

def process(inputs, config):
    """Top-level process function that delegates to the handler instance."""
    logger.info("TextOverlayImage - Top-level process function called")
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Overlay text on an image with various parameters.")
    parser.add_argument("--image_path", required=True, help="Path to the input image file")
    parser.add_argument("--text", required=True, help="Text to overlay")
    parser.add_argument("--font_size", type=int, default=40, help="Font size")
    parser.add_argument("--font_name", default=DEFAULT_FONT, help="Font name (must be in fonts directory)")
    parser.add_argument("--color", default="white", help="Text color (name or hex)")
    parser.add_argument("--position", default="center", help="Position: center, top_left, top_right, bottom_left, bottom_right, top_center, bottom_center, middle_left, middle_right")
    parser.add_argument("--offset", default="(0,0)", help="Offset as tuple, e.g., (10,20)")
    parser.add_argument("--bg_color", default=None, help="Background color for text box (optional)")
    parser.add_argument("--opacity", type=float, default=1.0, help="Text opacity (0.0 to 1.0)")
    args = parser.parse_args()
    inputs = {"image_path": args.image_path}
    config = {
        "text": args.text,
        "font_size": args.font_size,
        "font_name": args.font_name,
        "color": args.color,
        "position": args.position,
        "offset": args.offset,
        "bg_color": args.bg_color,
        "opacity": args.opacity,
    }
    result = process(inputs, config)
    print(result)
