import logging
import os
import uuid
from pathlib import Path
from PIL import Image
from lama_cleaner.model_manager import ModelManager

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class RemoveObjectHandler(NodeHandler):
    """Handler for removing objects from an image using lama-cleaner inpainting."""
    def process(self, inputs, config):
        try:
            image_path = inputs.get("image_path") or config.get("image_path")
            mask_path = inputs.get("mask_path") or config.get("mask_path")
            if not image_path or not os.path.exists(image_path):
                return {"status": "error", "error": "Input image not found."}
            if not mask_path or not os.path.exists(mask_path):
                return {"status": "error", "error": "Mask image not found."}
            img = Image.open(image_path).convert("RGB")
            mask = Image.open(mask_path).convert("L")  # grayscale mask
            # Optionally resize images to match
            if img.size != mask.size:
                mask = mask.resize(img.size, Image.Resampling.LANCZOS)
            model = ModelManager(name="lama", device="cpu")  # Use "cuda" for GPU if available
            result = model(img, mask)
            file_ext = Path(image_path).suffix or ".png"
            unique_filename = f"inpaint_{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, unique_filename)
            result.save(output_path)
            logger.info(f"Object removed and image saved to: {output_path}")
            return {"status": "success", "outputs": {"output_path": output_path}}
        except Exception as e:
            logger.exception(f"Error in RemoveObject node: {str(e)}")
            return {"status": "error", "error": f"Error processing node: {str(e)}"}

_handler = RemoveObjectHandler()

def process(inputs, config):
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Remove objects from an image using lama-cleaner inpainting.")
    parser.add_argument("--image_path", required=True, help="Path to the input image file")
    parser.add_argument("--mask_path", required=True, help="Path to the mask image file (white = remove, black = keep)")
    args = parser.parse_args()
    inputs = {
        "image_path": args.image_path,
        "mask_path": args.mask_path
    }
    config = {}
    result = process(inputs, config)
    print(result)