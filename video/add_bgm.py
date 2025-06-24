import logging
import os
import uuid
from pathlib import Path
from moviepy.editor import VideoFileClip, AudioFileClip
from moviepy.audio.AudioClip import CompositeAudioClip
from typing import Optional

# Standalone base class for testing; replace with real import if integrating
class NodeHandler:
    pass

logger = logging.getLogger(__name__)

OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class AddBGMHandler(NodeHandler):
    """Handler for adding background music to a video."""
    def process(self, inputs, config):
        """Process the node.
        Args:
            inputs: Dict containing 'video_path', 'music_path', and optionally 'music_volume', 'video_volume'
            config: Dict (not used here, but for compatibility)
        Returns:
            A dictionary with the execution result
        """
        try:
            logger.info(f"AddBGM - Processing with config: {config}")
            video_path = config.get("video_path")
            music_path = config.get("music_path")
            music_volume = float(config.get("music_volume", 0.5))
            video_volume = float(config.get("video_volume", 1.0))
            if not video_path or not os.path.exists(video_path):
                logger.error(f"Input video file not found: {video_path}")
                return {"status": "error", "error": f"Input video not found: {video_path}"}
            if not music_path or not os.path.exists(music_path):
                logger.error(f"Music file not found: {music_path}")
                return {"status": "error", "error": f"Music file not found: {music_path}"}
            if not video_path.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                logger.error(f"Invalid video file format: {video_path}")
                return {"status": "error", "error": f"Invalid video file format: {video_path}"}
            if not music_path.lower().endswith((".mp3", ".wav", ".aac", ".ogg", ".m4a")):
                logger.error(f"Invalid music file format: {music_path}")
                return {"status": "error", "error": f"Invalid music file format: {music_path}"}
            file_ext = Path(video_path).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            output_path = os.path.join(OUTPUT_FOLDER, f"bgm_{unique_filename}")
            success = self.add_bgm(video_path, music_path, output_path, music_volume, video_volume)
            if not success or not os.path.exists(output_path):
                logger.error("Failed to add background music or output file not created")
                return {"status": "error", "error": "Failed to add background music or output file not created"}
            return {
                "status": "success",
                "outputs": {
                    "output_path": output_path
                }
            }
        except Exception as e:
            logger.exception(f"Error in AddBGM node: {str(e)}")
            return {
                "status": "error",
                "error": f"Error processing node: {str(e)}"
            }
    def add_bgm(self, video_path: str, music_path: str, output_path: str, music_volume: float = 0.5, video_volume: float = 1.0):
        video = None
        music = None
        final_video = None
        try:
            logger.info(f"Loading video from: {video_path}")
            video = VideoFileClip(video_path)
            logger.info(f"Loading music from: {music_path}")
            music = AudioFileClip(music_path)
            # Adjust volumes
            if video.audio is not None:
                video_audio = video.audio.volumex(video_volume)
                music = music.volumex(music_volume)
                # Loop music if shorter than video
                if music.duration < video.duration:
                    music = music.fx(lambda c: c.audio_loop(duration=video.duration))
                composite_audio = CompositeAudioClip([video_audio, music.set_duration(video.duration)])
            else:
                # No original audio
                if music.duration < video.duration:
                    music = music.fx(lambda c: c.audio_loop(duration=video.duration))
                composite_audio = music.set_duration(video.duration)
            final_video = video.set_audio(composite_audio)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Writing video with background music to: {output_path}")
            final_video.write_videofile(
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
            logger.info(f"Successfully created video with background music: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error adding background music: {str(e)}")
            return False
        finally:
            try:
                if final_video is not None and hasattr(final_video, 'close'):
                    final_video.close()
                if video is not None and hasattr(video, 'close'):
                    video.close()
                if music is not None and hasattr(music, 'close'):
                    music.close()
            except Exception as e:
                logger.warning(f"Warning: Error during final cleanup: {str(e)}")

_handler = AddBGMHandler()

def process(inputs, config):
    """Top-level process function that delegates to the handler instance."""
    logger.info("AddBGM - Top-level process function called")
    return _handler.process(inputs, config)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Add background music to a video.")
    parser.add_argument("--video_path", required=True, help="Path to the input video file")
    parser.add_argument("--music_path", required=True, help="Path to the music file (mp3, wav, aac, ogg, m4a)")
    parser.add_argument("--music_volume", type=float, default=0.5, help="Music volume (0.0 to 1.0)")
    parser.add_argument("--video_volume", type=float, default=1.0, help="Original video volume (0.0 to 1.0)")
    args = parser.parse_args()
    inputs = {}
    config = {
        "video_path": args.video_path,
        "music_path": args.music_path,
        "music_volume": args.music_volume,
        "video_volume": args.video_volume,
    }
    result = process(inputs, config)
    print(result)
