import logging
import os
import uuid
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips
from typing import List

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class MergeHandler(NodeHandler):
    """Handler for merging multiple video clips into one."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict (unused, for compatibility)
            config: Dict containing 'video_paths' (list of paths)
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"Merge - Processing with config: {config}")
            video_paths = config.get("video_paths")
            if not video_paths or not isinstance(video_paths, list) or len(video_paths) < 2:
                logger.error("At least two video paths must be provided for merging.")
                return {"status": "error", "error": "At least two video paths must be provided for merging."}
            for path in video_paths:
                if not os.path.exists(path):
                    logger.error(f"Input video file not found: {path}")
                    return {"status": "error", "error": f"Input video not found: {path}"}
                if not path.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                    logger.error(f"Invalid file format: {path}")
                    return {"status": "error", "error": f"Invalid file format: {path}"}
            file_ext = Path(video_paths[0]).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"merged_{unique_filename}")
            success = self.merge_videos(video_paths, output_path)
            if not success or not os.path.exists(output_path):
                logger.error("Failed to merge videos or output file not created")
                return {"status": "error", "error": "Failed to merge videos or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in Merge node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def merge_videos(self, video_paths: List[str], output_path: str):
        clips = []
        try:
            logger.info(f"Loading video clips: {video_paths}")
            for path in video_paths:
                clips.append(VideoFileClip(path))
            final_clip = concatenate_videoclips(clips, method="compose")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Writing merged video to: {output_path}")
            final_clip.write_videofile(
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
            logger.info(f"Successfully created merged video: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error merging videos: {str(e)}")
            return False
        finally:
            for clip in clips:
                try:
                    if hasattr(clip, 'close'):
                        clip.close()
                except Exception as e:
                    logger.warning(f"Warning: Error closing clip: {str(e)}")
            try:
                if 'final_clip' in locals() and final_clip is not None and hasattr(final_clip, 'close'):
                    final_clip.close()
            except Exception as e:
                logger.warning(f"Warning: Error during final cleanup: {str(e)}")

_handler = MergeHandler()

def process(inputs, config):
    """Top-level process function that delegates to the handler instance."""
    logger.info("Merge - Top-level process function called")
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Merge multiple video clips into one.")
    parser.add_argument("--video_paths", nargs='+', required=True, help="Paths to the input video files (at least two)")
    args = parser.parse_args()
    inputs = {}
    config = {
        "video_paths": args.video_paths
    }
    result = process(inputs, config)
    print(result)
