import logging
import os
import uuid
from pathlib import Path
from moviepy.editor import VideoFileClip
from typing import Optional

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class TrimHandler(NodeHandler):
    """Handler for trimming videos between given timestamps."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict containing 'video_path'
            config: Dict with 'start_time' and 'end_time' (in seconds)
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"Trim - Processing with config: {config}")
            video_path = inputs.get("video_path") or config.get("video_path")
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
            output_path = os.path.join(OUTPUT_FOLDER, f"trimmed_{unique_filename}")
            # Trim the video
            success = self.trim_video(video_path, output_path, start_time, end_time)
            if not success or not os.path.exists(output_path):
                logger.error("Failed to trim video or output file not created")
                return {"status": "error", "error": "Failed to trim video or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in Trim node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def trim_video(self, video_path: str, output_path: str, start_time: float = 0, end_time: Optional[float] = None):
        video = None
        trimmed = None
        try:
            logger.info(f"Loading video from: {video_path}")
            video = VideoFileClip(video_path)
            if end_time is None or end_time > video.duration:
                end_time = video.duration
            if start_time < 0 or start_time >= end_time:
                logger.error(f"Invalid start_time: {start_time} or end_time: {end_time}")
                return False
            trimmed = video.subclip(start_time, end_time)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Writing trimmed video to: {output_path}")
            trimmed.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=os.path.join("/tmp", f"temp-audio-{uuid.uuid4()}.m4a"),
                remove_temp=True,
                threads=2,
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
            logger.info(f"Successfully created trimmed video: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error trimming video: {str(e)}")
            return False
        finally:
            try:
                if trimmed is not None and hasattr(trimmed, 'close'):
                    trimmed.close()
                if video is not None and hasattr(video, 'close'):
                    video.close()
            except Exception as e:
                logger.warning(f"Warning: Error during final cleanup: {str(e)}")

_handler = TrimHandler()

def process(inputs, config):
    """Top-level process function that delegates to the handler instance."""
    logger.info("Trim - Top-level process function called")
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trim a video between start and end timestamps.")
    parser.add_argument("--video_path", required=True, help="Path to the input video file")
    parser.add_argument("--start_time", type=float, required=True, help="Start time in seconds")
    parser.add_argument("--end_time", type=float, required=True, help="End time in seconds")
    args = parser.parse_args()
    inputs = {"video_path": args.video_path}
    config = {
        "start_time": args.start_time,
        "end_time": args.end_time,
    }
    result = process(inputs, config)
    print(result)
