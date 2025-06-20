import logging
import os
import uuid
from pathlib import Path
from PIL import Image
from typing import Optional, Tuple

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_position(img_size: Tuple[int, int], logo_size: Tuple[int, int], position: str, offset: Tuple[int, int] = (0, 0)):
    W, H = img_size
    w, h = logo_size
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
    base = pos_map.get(position, pos_map["bottom_right"])
    x = base[0] + x_off
    y = base[1] + y_off
    # Clamp so logo stays fully within the image
    x = max(0, min(x, W - w))
    y = max(0, min(y, H - h))
    return (x, y)

class LogoOverlayImageHandler(NodeHandler):
    """Handler for overlaying a logo on images with various parameters."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict containing 'image_path', 'logo_path'
            config: Dict with 'position', 'offset', 'logo_scale', 'opacity', etc.
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"LogoOverlayImage - Processing with config: {config}")
            image_path = inputs.get("image_path") or config.get("image_path")
            logo_path = inputs.get("logo_path") or config.get("logo_path")
            position = config.get("position", "bottom_right")
            offset = config.get("offset", (0, 0))
            if isinstance(offset, str):
                offset = tuple(map(int, offset.strip("() ").split(",")))
            logo_scale = float(config.get("logo_scale", 1.0))
            opacity = float(config.get("opacity", 1.0))
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Input image file not found: {image_path}")
                return {"status": "error", "error": f"Input image not found: {image_path}"}
            if not logo_path or not os.path.exists(logo_path):
                logger.error(f"Logo image file not found: {logo_path}")
                return {"status": "error", "error": f"Logo image not found: {logo_path}"}
            if not image_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff")):
                logger.error(f"Invalid image file format: {image_path}")
                return {"status": "error", "error": f"Invalid image file format: {image_path}"}
            if not logo_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff")):
                logger.error(f"Invalid logo file format: {logo_path}")
                return {"status": "error", "error": f"Invalid logo file format: {logo_path}"}
            file_ext = Path(image_path).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"logo_{unique_filename}")
            success = self.overlay_logo(image_path, logo_path, output_path, position, offset, logo_scale, opacity)
            if not success or not os.path.exists(output_path):
                logger.error("Failed to overlay logo or output file not created")
                return {"status": "error", "error": "Failed to overlay logo or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in LogoOverlayImage node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def overlay_logo(self, image_path: str, logo_path: str, output_path: str, position: str, offset: Tuple[int, int], logo_scale: float, opacity: float):
        img = None
        logo = None
        try:
            logger.info(f"Loading main image from: {image_path}")
            img = Image.open(image_path).convert("RGBA")
            logger.info(f"Loading logo image from: {logo_path}")
            logo = Image.open(logo_path).convert("RGBA")
            # Scale logo
            logo_w, logo_h = logo.size
            new_w = int(logo_w * logo_scale)
            new_h = int(logo_h * logo_scale)
            logo = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Adjust logo opacity
            if opacity < 1.0:
                alpha = logo.split()[3]
                alpha = alpha.point(lambda p: int(p * opacity))
                logo.putalpha(alpha)
            pos = get_position(img.size, logo.size, position, offset)
            # Overlay
            combined = Image.new("RGBA", img.size)
            combined.paste(img, (0, 0))
            combined.paste(logo, pos, mask=logo)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            combined = combined.convert("RGB")
            combined.save(output_path)
            logger.info(f"Successfully created logo overlay image: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error overlaying logo: {str(e)}")
            return False
        finally:
            if img is not None:
                try:
                    img.close()
                except Exception as e:
                    logger.warning(f"Warning: Error closing image: {str(e)}")
            if logo is not None:
                try:
                    logo.close()
                except Exception as e:
                    logger.warning(f"Warning: Error closing logo: {str(e)}")

_handler = LogoOverlayImageHandler()

def process(inputs, config):
    logger.info("LogoOverlayImage - Top-level process function called")
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Overlay a brand logo on an image.")
    parser.add_argument("--image_path", required=True, help="Path to the input image file")
    parser.add_argument("--logo_path", required=True, help="Path to the logo image file (PNG recommended)")
    parser.add_argument("--position", default="bottom_right", help="Logo position: center, top_left, top_right, bottom_left, bottom_right, top_center, bottom_center, middle_left, middle_right")
    parser.add_argument("--offset", default="(0,0)", help="Offset as tuple, e.g., (10,20)")
    parser.add_argument("--logo_scale", type=float, default=1.0, help="Scale factor for logo size (e.g., 0.5 for half size)")
    parser.add_argument("--opacity", type=float, default=1.0, help="Logo opacity (0.0 to 1.0)")
    args = parser.parse_args()
    inputs = {"image_path": args.image_path, "logo_path": args.logo_path}
    config = {
        "position": args.position,
        "offset": args.offset,
        "logo_scale": args.logo_scale,
        "opacity": args.opacity,
    }
    result = process(inputs, config)
    print(result)
