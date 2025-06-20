import logging
import os
import uuid
from pathlib import Path
from rembg import remove
from PIL import Image

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class RemoveBGHandler(NodeHandler):
    """Handler for removing background from images."""
    def process(self, inputs, config):
        try:
            image_path = inputs.get("image_path") or config.get("image_path")
            if not image_path or not os.path.exists(image_path):
                logger.error(f"Input image file not found: {image_path}")
                return {"status": "error", "error": f"Input image not found: {image_path}"}
            file_ext = Path(image_path).suffix
            unique_filename = f"{uuid.uuid4()}.png"  # Always save output as PNG (for transparency)
            output_path = os.path.join(OUTPUT_FOLDER, f"nobg_{unique_filename}")
            input_image = Image.open(image_path)
            output_image = remove(input_image)
            output_image.save(output_path)
            logger.info(f"Successfully saved background-removed image: {output_path}")
            return {"status": "success", "outputs": {"output_path": output_path}}
        except Exception as e:
            logger.exception(f"Error in RemoveBG node: {str(e)}")
            return {"status": "error", "error": f"Error processing node: {str(e)}"}

_handler = RemoveBGHandler()

def process(inputs, config):
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Remove background from an image.")
    parser.add_argument("--image_path", required=True, help="Path to the input image file")
    args = parser.parse_args()
    inputs = {"image_path": args.image_path}
    config = {}
    result = process(inputs, config)
    print(result)
