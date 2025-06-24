import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import requests

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class AutoCaptionImageHandler(NodeHandler):
    """Handler for generating an automatic descriptive caption for an image using Gemini API."""
    def process(self, inputs, config):
        try:
            image_path = inputs.get("image_path") or config.get("image_path")
            api_key = "AIzaSyBjYhKIpFTOf8yqFJGxJldd_sG4xOLX5gA"
            if not image_path or not os.path.exists(image_path):
                return {"status": "error", "error": "Input image not found."}
            # Read image as bytes
            with open(image_path, "rb") as img_file:
                img_bytes = img_file.read()
            # Gemini API endpoint for multimodal (text+image) tasks
            url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=" + api_key
            headers = {"Content-Type": "application/json"}
            import base64
            image_b64 = base64.b64encode(img_bytes).decode("utf-8")
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": "Describe this image in one detailed, descriptive caption."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
                        ]
                    }
                ]
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.text}")
                return {"status": "error", "error": f"Gemini API error: {response.text}"}
            data = response.json()
            caption = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not caption:
                logger.error("No caption generated.")
                return {"status": "error", "error": "No caption generated."}
            logger.info(f"Generated caption: {caption}")
            return {"status": "success", "outputs": {"caption": caption}}
        except Exception as e:
            logger.exception(f"Error in AutoCaptionImage node: {str(e)}")
            return {"status": "error", "error": f"Error processing node: {str(e)}"}

_handler = AutoCaptionImageHandler()

def process(inputs, config):
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a descriptive caption for an image using Gemini API.")
    parser.add_argument("--image_path", required=True, help="Path to the input image file")
    parser.add_argument("--api_key", default=None, help="Gemini API key (or set GEMINI_API_KEY env variable)")
    args = parser.parse_args()
    inputs = {"image_path": args.image_path, "api_key": args.api_key}
    config = {}
    result = process(inputs, config)
    print(result)
