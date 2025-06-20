from app.worker.node_handler import NodeHandler
import logging
import os
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.config import change_settings
from PIL import Image, ImageDraw, ImageFont
import tempfile

logger = logging.getLogger(__name__)

# Configure MoviePy to use ImageMagick if available
try:
    change_settings({"IMAGEMAGICK_BINARY": "convert"})
except Exception:
    pass

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

FONTS_DIR = "/usr/share/fonts/truetype/dejavu/"
DEFAULT_FONT = "DejaVuSans-Bold.ttf"

def get_available_fonts():
    try:
        return [f for f in os.listdir(FONTS_DIR) if f.endswith('.ttf')]
    except FileNotFoundError:
        return [DEFAULT_FONT]

def create_text_image(text, font_size=50, color='white', bg_color=(0, 0, 0, 0), size=None):
    try:
        font = ImageFont.truetype(DEFAULT_FONT, font_size)
    except IOError:
        try:
            font = ImageFont.truetype("Arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
    if size is None:
        temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        text_bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        size = (text_width + 20, text_height + 20)
    img = Image.new('RGBA', size, bg_color)
    draw = ImageDraw.Draw(img)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    draw.text((x, y), text, font=font, fill=color)
    return img

def create_text_clip(text: str, video_size: Tuple[int, int], start: float, end: float,
                     position: Tuple[str, str] = ("center", "bottom"),
                     font_size: int = 50, color: str = "white",
                     bg_color: str = "rgba(0, 0, 0, 0.7)", padding: int = 10):
    from moviepy.video.VideoClip import ImageClip
    import re
    # Convert bg_color from rgba string to tuple if needed
    if isinstance(bg_color, str) and bg_color.startswith("rgba"):
        match = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([0-9.]+)\)", bg_color)
        if match:
            r, g, b, a = match.groups()
            bg_color = (int(r), int(g), int(b), int(float(a) * 255))
        else:
            bg_color = (0, 0, 0, 180)
    img = create_text_image(text, font_size=font_size, color=color, bg_color=bg_color)
    img_clip = ImageClip(np.array(img)).set_start(start).set_end(end)
    pos_map = {
        "center": lambda dim, size: (dim - size) // 2,
        "left": lambda dim, size: 10,
        "right": lambda dim, size: dim - size - 10,
        "top": lambda dim, size: 10,
        "bottom": lambda dim, size: dim - size - 10,
    }
    x_pos, y_pos = position
    x = pos_map.get(x_pos, pos_map["center"])(video_size[0], img.size[0])
    y = pos_map.get(y_pos, pos_map["bottom"])(video_size[1], img.size[1])
    img_clip = img_clip.set_position((x, y))
    return img_clip

class WatermarkHandler(NodeHandler):
    """Handler for Watermark nodes. Adds watermark and subtitles to a video."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict containing 'video_path', etc.
            config: Dict with watermark/subtitle options
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"Watermark - Processing with config: {config}")
            video_path = inputs.get("video_path") or config.get("video_path")
            watermark_text = config.get("watermark_text", "")
            subtitles_json = config.get("subtitles_json", "[]")
            font = config.get("font", None)
            start_time = float(config.get("start_time", 0))
            end_time = config.get("end_time")
            if end_time is not None:
                end_time = float(end_time)
            # Validate input
            if not video_path or not os.path.exists(video_path):
                logger.error(f"Input video file not found: {video_path}")
                return {"status": "error", "error": f"Input video not found: {video_path}"}
            if not video_path.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                logger.error(f"Invalid file format: {video_path}")
                return {"status": "error", "error": f"Invalid file format: {video_path}"}
            file_ext = Path(video_path).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"watermarked_{unique_filename}")
            # Parse subtitles JSON
            subtitles_list = []
            if subtitles_json and subtitles_json != '[]':
                try:
                    if '\\"' in subtitles_json:
                        clean_subtitles = subtitles_json.replace('\\"', '"')
                    elif '\"' in subtitles_json:
                        clean_subtitles = subtitles_json.replace('\"', '"')
                    else:
                        clean_subtitles = subtitles_json
                    subtitles_list = json.loads(clean_subtitles)
                except json.JSONDecodeError as e:
                    try:
                        clean_subtitles = subtitles_json.replace('\\', '')
                        subtitles_list = json.loads(clean_subtitles)
                    except Exception:
                        subtitles_list = []
                except Exception:
                    subtitles_list = []
            # Add watermark and subtitles
            success = self.add_watermark(
                video_path=video_path,
                output_path=output_path,
                watermark_text=watermark_text,
                subtitles=subtitles_list,
                font=font,
                start_time=start_time,
                end_time=end_time
            )
            if not success or not os.path.exists(output_path):
                logger.error("Failed to add watermark to video or output file not created")
                return {"status": "error", "error": "Failed to add watermark to video or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in Watermark node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def add_watermark(self, video_path: str, output_path: str, watermark_text: str = "", subtitles: List[Dict] = None, font: str = None, start_time: float = 0, end_time: Optional[float] = None, font_size: int = 50, color: str = "white", opacity: float = 0.7, position: Tuple[str, str] = ("center", "bottom")):
        video = None
        final_video = None
        try:
            logger.info(f"Loading video from: {video_path}")
            if not os.path.exists(video_path):
                logger.error(f"Input video file not found: {video_path}")
                return False
            try:
                video = VideoFileClip(video_path, audio=True)
                if not hasattr(video, 'fps') or video.fps is None:
                    video.fps = 24
                logger.info(f"Video loaded. Duration: {video.duration:.2f}s, Size: {video.size}, FPS: {video.fps}")
                if video.audio is None:
                    logger.warning("No audio track found in the input video")
            except Exception as e:
                logger.error(f"Error loading video: {str(e)}")
                if 'video' in locals():
                    video.close()
                raise
            if end_time is None or end_time > video.duration:
                end_time = video.duration
            watermark_clip = None
            if watermark_text:
                logger.info(f"Creating watermark with text: {watermark_text}")
                watermark_clip = create_text_clip(
                    text=watermark_text,
                    video_size=(video.w, video.h),
                    start=start_time,
                    end=end_time if end_time else video.duration,
                    position=position,
                    font_size=font_size,
                    color=color,
                    bg_color=f"rgba(0, 0, 0, {opacity * 0.8})",
                    padding=10
                )
                if watermark_clip is None:
                    logger.warning("Failed to create watermark clip")
            subtitle_clips = []
            if subtitles and len(subtitles) > 0:
                logger.info(f"Processing {len(subtitles)} subtitles...")
                for i, sub in enumerate(subtitles):
                    try:
                        sub_clip = create_text_clip(
                            text=sub['text'],
                            video_size=(video.w, video.h),
                            start=sub['start'],
                            end=sub['end'],
                            position=sub.get('position', ('center', 'bottom')),
                            font_size=sub.get('font_size', 30),
                            color=sub.get('color', 'white'),
                            bg_color=sub.get('bg_color', 'rgba(0, 0, 0, 0.7)'),
                            padding=10
                        )
                        if sub_clip:
                            subtitle_clips.append(sub_clip)
                    except Exception as e:
                        logger.error(f"Error creating subtitle {i}: {str(e)}")
            logger.info("Creating final video composition...")
            try:
                clips = [video]
                if watermark_clip:
                    clips.append(watermark_clip)
                if subtitle_clips:
                    clips.extend(subtitle_clips)
                if len(clips) > 1:
                    final_video = CompositeVideoClip(clips)
                else:
                    logger.info("No overlays to add, using original video")
                    final_video = video
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                logger.info(f"Writing output to: {output_path}")
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    bitrate='2000k',
                    audio_bitrate='192k',
                    temp_audiofile=os.path.join(tempfile.gettempdir(), f"temp-audio-{uuid.uuid4()}.m4a"),
                    remove_temp=True,
                    threads=4,
                    preset='medium',
                    ffmpeg_params=[
                        '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart',
                        '-profile:v', 'high',
                        '-level', '4.0',
                        '-crf', '23',
                        '-tune', 'film'
                    ],
                    logger=None,
                    verbose=False
                )
                logger.info(f"Successfully created video: {output_path}")
                return True
            except Exception as e:
                logger.error(f"Error during video composition: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Error in add_watermark: {str(e)}")
            return False
        finally:
            try:
                if 'final_video' in locals() and final_video is not None and hasattr(final_video, 'close'):
                    final_video.close()
                if 'video' in locals() and video is not None and hasattr(video, 'close'):
                    video.close()
                if 'watermark_clip' in locals() and watermark_clip is not None and hasattr(watermark_clip, 'close'):
                    watermark_clip.close()
                if 'subtitle_clips' in locals():
                    for clip in subtitle_clips:
                        if hasattr(clip, 'close'):
                            clip.close()
            except Exception as e:
                logger.warning(f"Warning: Error during final cleanup: {str(e)}")

_handler = WatermarkHandler()

def process(inputs, config):
    """Top-level process function that delegates to the handler instance."""
    logger.info("Watermark - Top-level process function called")
    return _handler.process(inputs, config)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Add watermark and subtitles to a video.")
    parser.add_argument("--video_path", required=True, help="Path to the input video file")
    parser.add_argument("--watermark_text", default="", help="Text for the watermark")
    parser.add_argument("--subtitles_json", default="[]", help="Subtitles as JSON string")
    parser.add_argument("--font", default=None, help="Font to use")
    parser.add_argument("--start_time", type=float, default=0, help="Start time for watermark")
    parser.add_argument("--end_time", type=float, default=None, help="End time for watermark (optional)")

    args = parser.parse_args()

    inputs = {"video_path": args.video_path}
    config = {
        "watermark_text": args.watermark_text,
        "subtitles_json": args.subtitles_json,
        "font": args.font,
        "start_time": args.start_time,
        "end_time": args.end_time,
    }

    result = process(inputs, config)
    print(result)