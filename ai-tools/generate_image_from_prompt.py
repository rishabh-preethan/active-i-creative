import logging
import os
import uuid
from pathlib import Path
import requests

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class GenerateImageHandler(NodeHandler):
    """Handler for generating an image from a text prompt using OpenAI DALL·E API."""
    def process(self, inputs, config):
        try:
            prompt = inputs.get("prompt") or config.get("prompt")
            api_key = inputs.get("api_key") or config.get("api_key") or os.getenv("OPENAI_API_KEY", "")
            if not prompt:
                logger.error("Prompt is required.")
                return {"status": "error", "error": "Prompt is required."}
            if not api_key:
                logger.error("OpenAI API key is required.")
                return {"status": "error", "error": "OpenAI API key is required."}
            import openai
            openai.api_key = api_key
            response = openai.Image.create(
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            image_url = response['data'][0]['url']
            # Download the image
            img_response = requests.get(image_url)
            file_ext = ".png"
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"gen_{unique_filename}")
            with open(output_path, "wb") as f:
                f.write(img_response.content)
            logger.info(f"Image generated and saved to: {output_path}")
            return {"status": "success", "outputs": {"output_path": output_path, "image_url": image_url}}
        except Exception as e:
            logger.exception(f"Error in GenerateImage node: {str(e)}")
            return {"status": "error", "error": f"Error processing node: {str(e)}"}

_handler = GenerateImageHandler()

def process(inputs, config):
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate an image from a text prompt using OpenAI DALL·E API.")
    parser.add_argument("--prompt", required=True, help="Text prompt to generate the image")
    parser.add_argument("--api_key", default=None, help="OpenAI API key (or set OPENAI_API_KEY env variable)")
    args = parser.parse_args()
    inputs = {"prompt": args.prompt, "api_key": args.api_key}
    config = {}
    result = process(inputs, config)
    print(result)