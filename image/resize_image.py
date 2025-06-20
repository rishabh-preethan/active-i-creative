import logging
import os
import uuid
from pathlib import Path
from PIL import Image
from typing import Optional

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class ResizeImageHandler(NodeHandler):
    """Handler for resizing images to specified dimensions."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict containing 'image_path'
            config: Dict with 'width' and 'height' (integers)
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"ResizeImage - Processing with config: {config}")
            image_path = inputs.get("image_path") or config.get("image_path")
            width = config.get("width")
            height = config.get("height")
            if width is None or height is None:
                logger.error("Both width and height must be specified.")
                return {"status": "error", "error": "Both width and height must be specified."}
            width = int(width)
            height = int(height)
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Input image file not found: {image_path}")
                return {"status": "error", "error": f"Input image not found: {image_path}"}
            if not image_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff")):
                logger.error(f"Invalid image file format: {image_path}")
                return {"status": "error", "error": f"Invalid image file format: {image_path}"}
            file_ext = Path(image_path).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"resized_{unique_filename}")
            success = self.resize_image(image_path, output_path, width, height)
            if not success or not os.path.exists(output_path):
                logger.error("Failed to resize image or output file not created")
                return {"status": "error", "error": "Failed to resize image or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in ResizeImage node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def resize_image(self, image_path: str, output_path: str, width: int, height: int):
        img = None
        try:
            logger.info(f"Loading image from: {image_path}")
            img = Image.open(image_path)
            logger.info(f"Resizing image to {width}x{height}")
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Saving resized image to: {output_path}")
            resized.save(output_path)
            logger.info(f"Successfully created resized image: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            return False
        finally:
            if img is not None:
                try:
                    img.close()
                except Exception as e:
                    logger.warning(f"Warning: Error closing image: {str(e)}")

_handler = ResizeImageHandler()

def process(inputs, config):
    """Top-level process function that delegates to the handler instance."""
    logger.info("ResizeImage - Top-level process function called")
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Resize an image to specified width and height.")
    parser.add_argument("--image_path", required=True, help="Path to the input image file")
    parser.add_argument("--width", type=int, required=True, help="Target width in pixels")
    parser.add_argument("--height", type=int, required=True, help="Target height in pixels")
    args = parser.parse_args()
    inputs = {"image_path": args.image_path}
    config = {
        "width": args.width,
        "height": args.height,
    }
    result = process(inputs, config)
    print(result)
