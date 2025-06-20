import logging
import os
import uuid
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from typing import Optional

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class EffectImageHandler(NodeHandler):
    """Handler for applying visual effects to images (grayscale, sepia, etc)."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict containing 'image_path'
            config: Dict with 'effect' (e.g., 'grayscale', 'sepia', 'invert', 'contrast', etc)
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"EffectImage - Processing with config: {config}")
            image_path = inputs.get("image_path") or config.get("image_path")
            effect = config.get("effect", "grayscale")
            intensity = float(config.get("intensity", 1.0))  # for effects like contrast/brightness
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Input image file not found: {image_path}")
                return {"status": "error", "error": f"Input image not found: {image_path}"}
            if not image_path.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff")):
                logger.error(f"Invalid image file format: {image_path}")
                return {"status": "error", "error": f"Invalid image file format: {image_path}"}
            file_ext = Path(image_path).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"effect_{effect}_{unique_filename}")
            success = self.apply_effect(image_path, output_path, effect, intensity)
            if not success or not os.path.exists(output_path):
                logger.error("Failed to apply effect or output file not created")
                return {"status": "error", "error": "Failed to apply effect or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in EffectImage node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def apply_effect(self, image_path: str, output_path: str, effect: str, intensity: float = 1.0):
        img = None
        try:
            logger.info(f"Loading image from: {image_path}")
            img = Image.open(image_path).convert("RGB")
            logger.info(f"Applying effect: {effect}")
            if effect == "grayscale":
                img = ImageOps.grayscale(img)
            elif effect == "sepia":
                sepia = []
                for i in range(255):
                    sepia.append((int(i * 240 / 255), int(i * 200 / 255), int(i * 145 / 255)))
                img = img.convert("L")
                img = img.convert("RGB")
                img.putpalette([v for t in sepia for v in t] * 86)  # crude palette
            elif effect == "invert":
                img = ImageOps.invert(img)
            elif effect == "contrast":
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(intensity)
            elif effect == "brightness":
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(intensity)
            else:
                logger.error(f"Unknown effect: {effect}")
                return False
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Saving effect image to: {output_path}")
            img.save(output_path)
            logger.info(f"Successfully created effect image: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error applying effect: {str(e)}")
            return False
        finally:
            if img is not None:
                try:
                    img.close()
                except Exception as e:
                    logger.warning(f"Warning: Error closing image: {str(e)}")

_handler = EffectImageHandler()

def process(inputs, config):
    """Top-level process function that delegates to the handler instance."""
    logger.info("EffectImage - Top-level process function called")
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Apply a visual effect to an image.")
    parser.add_argument("--image_path", required=True, help="Path to the input image file")
    parser.add_argument("--effect", required=True, choices=["grayscale", "sepia", "invert", "contrast", "brightness"], help="Effect to apply")
    parser.add_argument("--intensity", type=float, default=1.0, help="Intensity for contrast/brightness (default 1.0)")
    args = parser.parse_args()
    inputs = {"image_path": args.image_path}
    config = {
        "effect": args.effect,
        "intensity": args.intensity,
    }
    result = process(inputs, config)
    print(result)
