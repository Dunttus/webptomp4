import os
import re
import shutil
import tempfile
import argparse
import glob
import logging
from pathlib import Path
from typing import List, Dict, Optional
from moviepy import *
from PIL import Image, ImageSequence

def configure_logging(log_to_file: bool = False):
    """Configure logging with optional file output."""
    handlers = [logging.StreamHandler()]
    if log_to_file:
        handlers.append(logging.FileHandler("webp_converter.log"))
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers
    )

class ImageAnalyzer:
    """Handles analysis of animated image properties and frame extraction."""
    
    @staticmethod
    def analyze_image(image_path: str) -> Dict:
        """
        Analyzes an animated image to determine its properties.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing image properties:
            - size: (width, height) tuple
            - mode: 'full' or 'partial' (full frame vs partial updates)
            - frame_count: Total number of frames
            - duration: Total duration in milliseconds (if available)
            - format: Image format (GIF, WEBP, etc.)
        """
        logging.info(f"Analyzing image: {image_path}")
        
        with Image.open(image_path) as img:
            image_info = {
                'size': img.size,
                'mode': 'full',
                'frame_count': 1,
                'duration': 0,
                'format': img.format
            }
            
            # Check if image is animated
            if not getattr(img, 'is_animated', False):
                return image_info
                
            image_info['frame_count'] = img.n_frames if hasattr(img, 'n_frames') else 0
            
            try:
                durations = []
                for frame in ImageSequence.Iterator(img):
                    durations.append(frame.info.get('duration', 0))
                    
                    # Check for partial updates
                    if frame.tile:
                        tile = frame.tile[0]
                        if tile[1][2:] != img.size:
                            image_info['mode'] = 'partial'
                            break
                
                image_info['duration'] = sum(durations)
                if image_info['frame_count'] == 0:
                    image_info['frame_count'] = len(durations)
                    
            except Exception as e:
                logging.warning(f"Error analyzing image frames: {e}")
                
        logging.debug(f"Image analysis results: {image_info}")
        return image_info

class FrameExtractor:
    """Handles efficient extraction of frames from animated images."""
    
    @staticmethod
    def extract_frames(image_path: str, output_dir: str) -> List[str]:
        """
        Extracts all frames from an animated image and saves them as PNGs.
        
        Args:
            image_path: Path to the source image
            output_dir: Directory to save extracted frames
            
        Returns:
            List of paths to extracted frame files
        """
        logging.info(f"Extracting frames from: {image_path}")
        
        image_info = ImageAnalyzer.analyze_image(image_path)
        if image_info['frame_count'] <= 1:
            logging.warning("Image is not animated or contains only one frame")
            return []
            
        frame_paths = []
        temp_dir = Path(output_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with Image.open(image_path) as img:
                palette = img.getpalette()
                last_frame = img.convert('RGBA')
                
                for frame_index, frame in enumerate(ImageSequence.Iterator(img)):
                    frame_filename = temp_dir / f"{Path(image_path).stem}-{frame_index:04d}.png"
                    
                    # Handle palette for GIFs
                    if img.format == "GIF" and palette and not frame.getpalette():
                        frame.putpalette(palette)
                    
                    # Handle partial frame updates
                    if image_info['mode'] == 'partial':
                        new_frame = last_frame.copy()
                        new_frame.paste(frame, (0, 0), frame.convert('RGBA'))
                    else:
                        new_frame = frame.convert('RGBA')
                    
                    new_frame.save(frame_filename, 'PNG')
                    frame_paths.append(str(frame_filename))
                    last_frame = new_frame
                    
        except Exception as e:
            logging.error(f"Error extracting frames: {e}")
            # Clean up partially extracted frames
            for frame in frame_paths:
                try:
                    os.remove(frame)
                except:
                    pass
            return []
            
        logging.info(f"Successfully extracted {len(frame_paths)} frames")
        return frame_paths

class VideoConverter:
    """Handles conversion of image sequences to video formats."""
    
    @staticmethod
    def convert_to_mp4(
        source_file: str,
        frame_rate: int = 20,
        split_ratio: int = 100,
        output_dir: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        Converts an animated image to MP4 video(s).
        
        Args:
            source_file: Path to source image
            frame_rate: Frames per second for output video
            split_ratio: Percentage to split video (100 = no split)
            output_dir: Directory for output files (None = current dir)
            
        Returns:
            List of output file paths or None if conversion failed
        """
        logging.info(f"Starting conversion of {source_file}")
        
        temp_dir = tempfile.mkdtemp()
        output_files = []
        
        try:
            # Extract frames
            frames = FrameExtractor.extract_frames(source_file, temp_dir)
            if not frames:
                logging.error("No frames extracted - conversion aborted")
                return None
                
            # Calculate split points
            split_index = int(len(frames) * (split_ratio / 100))
            segments = [frames[:split_index]]
            if split_index < len(frames):
                segments.append(frames[split_index:])
                
            # Prepare output directory
            output_dir = Path(output_dir) if output_dir else Path.cwd()
            output_dir.mkdir(parents=True, exist_ok=True)
            base_name = Path(source_file).stem
            
            # Process each segment
            for i, segment in enumerate(segments, 1):
                output_path = output_dir / f"{base_name}_part{i}.mp4"
                
                logging.info(f"Creating video segment {i} with {len(segment)} frames")
                clip = ImageSequenceClip(segment, fps=frame_rate)
                
                # Optimize video writing
                clip.write_videofile(
                    str(output_path),
                    codec="libx264",
                    threads=4,
                    preset="ultrafast",
                    ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p"],
                    logger=None  # Disable moviepy progress bars
                )
                output_files.append(str(output_path))
                
        except Exception as e:
            logging.error(f"Conversion failed: {e}")
            output_files = None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        return output_files
    
    @staticmethod
    def merge_videos(
        video_files: List[str],
        output_path: str,
        frame_rate: int = 20
    ) -> bool:
        """
        Merges multiple video files into one.
        
        Args:
            video_files: List of video files to merge
            output_path: Path for merged output
            frame_rate: Target frame rate
            
        Returns:
            True if merge succeeded, False otherwise
        """
        if not video_files:
            logging.warning("No video files provided for merging")
            return False
            
        try:
            # Natural sorting for numbered sequences
            def natural_sort_key(s):
                return [
                    int(text) if text.isdigit() else text.lower()
                    for text in re.split('([0-9]+)', str(s))
                ]
            
            video_files = sorted(video_files, key=natural_sort_key)
            
            clips = []
            for file in video_files:
                try:
                    logging.info(f"Loading clip: {file}")
                    clip = VideoFileClip(file)
                    
                    # Ensure consistent frame rate and resolution
                    if clip.fps != frame_rate:
                        clip = clip.set_fps(frame_rate)
                    
                    clips.append(clip)
                except Exception as e:
                    logging.error(f"Error loading {file}: {e}")
                    continue
                    
            if not clips:
                logging.error("No valid video clips to merge")
                return False
                
            logging.info(f"Merging {len(clips)} clips into {output_path}")
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Write final merged video
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                threads=4,
                preset="medium",
                ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p"],
                logger=None  # Disable moviepy progress bars
            )
            
            # Close all clips to release resources
            for clip in clips:
                clip.close()
            final_clip.close()
            
            return True
            
        except Exception as e:
            logging.error(f"Video merging failed: {e}")
            return False
        finally:
            # Ensure all clips are closed
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass

def main():
    """Main entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Convert animated WEBP/GIF files to MP4 videos with optional splitting and merging",
        epilog="Example: python webp_converter.py anim1.webp anim2.webp --fps 24 --percent 50 --output videos --log"
    )
    parser.add_argument(
        "input_files",
        nargs='*',
        help="Input file names (.webp, .gif)"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=20,
        help="Frames per second for output video (default: 20)"
    )
    parser.add_argument(
        "--percent",
        type=int,
        default=100,
        choices=range(1, 100),
        metavar="[1-99]",
        help="Percentage to split first video segment (default: 100 - no split)"
    )
    parser.add_argument(
        "--output",
        help="Directory for output MP4 files (default: current directory)"
    )
    parser.add_argument(
        "--combine",
        help="Filename for combined output video (requires --output if specified)"
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable logging to webp_converter.log file"
    )
    
    args = parser.parse_args()
    configure_logging(args.log)
    logging.info(f"Starting conversion with parameters: {vars(args)}")
    
    # Find input files if not specified
    input_files = args.input_files if args.input_files else glob.glob("*.[wW][eE][bB][pP]") + glob.glob("*.[gG][iI][fF]")
    if not input_files:
        logging.error("No input files found")
        return
        
    # Process each file
    processed_files = []
    for file in input_files:
        if not Path(file).exists():
            logging.warning(f"File not found: {file}")
            continue
            
        result = VideoConverter.convert_to_mp4(
            file,
            frame_rate=args.fps,
            split_ratio=args.percent,
            output_dir=args.output
        )
        
        if result:
            processed_files.extend(result)
            
    # Merge if requested
    if args.combine and processed_files:
        output_path = Path(args.combine)
        if args.output and not output_path.is_absolute():
            output_path = Path(args.output) / output_path
            
        if not VideoConverter.merge_videos(processed_files, str(output_path), args.fps):
            logging.error("Failed to merge videos")
            
    logging.info("Processing complete")

if __name__ == "__main__":
    main()
