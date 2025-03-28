import os
import shutil
import tempfile
import argparse
import glob
import logging
from pathlib import Path
from moviepy import *
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to analyze image properties (size and mode: full or partial)
def extract_image_details(image_path):
    """Determines the mode (full or partial) of a GIF or animated image."""
    logging.info(f"Analyzing image: {image_path}")
    
    with Image.open(image_path) as im:
        image_info = {'size': im.size, 'mode': 'full'}
        
        try:
            while True:
                if im.tile:
                    tile = im.tile[0]
                    if tile[1][2:] != im.size:
                        image_info['mode'] = 'partial'
                        break
                im.seek(im.tell() + 1)
        except EOFError:
            pass
    
    logging.info(f"Image details: {image_info}")
    return image_info

# Function to extract frames from an image (handling GIFs and partial updates)
def generate_image_frames(image_path, temp_directory):
    """Extracts frames from a GIF or animated image and saves them as PNGs."""
    logging.info(f"Extracting frames from: {image_path}")
    
    frame_list = []
    mode = extract_image_details(image_path)['mode']
    
    with Image.open(image_path) as im:
        frame_index = 0
        palette = im.getpalette()
        last_frame = im.convert('RGBA')

        try:
            while True:
                frame_filename = Path(temp_directory) / f"{Path(image_path).stem}-{frame_index}.png"
                
                if im.format == "GIF" and not im.getpalette():
                    im.putpalette(palette)
                
                new_frame = Image.new('RGBA', im.size)
                if mode == 'partial':
                    new_frame.paste(last_frame)
                new_frame.paste(im, (0, 0), im.convert('RGBA'))
                new_frame.save(frame_filename, 'PNG')
                
                frame_list.append(str(frame_filename))
                
                frame_index += 1
                last_frame = new_frame
                im.seek(im.tell() + 1)
        except EOFError:
            pass
    
    logging.info(f"Extracted {len(frame_list)} frames from {image_path}")
    return frame_list

# Function to convert a WEBP image sequence into an MP4 video
def convert_webp_to_mp4(source_file, frame_rate=20, split_ratio=100, output_dir=None):
    """Converts WEBP animation to MP4, with optional splitting."""
    logging.info(f"Converting {source_file} to MP4...")

    temp_directory = tempfile.mkdtemp()
    output_files = []

    try:
        extracted_frames = generate_image_frames(source_file, temp_directory)
        if not extracted_frames:
            logging.warning(f"No frames extracted from {source_file}")
            return None
        
        split_index = int(len(extracted_frames) * (split_ratio / 100))
        first_segment_frames, second_segment_frames = extracted_frames[:split_index], extracted_frames[split_index:]
        
        base_filename = Path(source_file).stem
        output_dir = Path(output_dir) if output_dir else Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        first_output = output_dir / f"{base_filename}_part1.mp4"
        second_output = output_dir / f"{base_filename}_part2.mp4" if second_segment_frames else None

        # Generate first part of the video
        logging.info(f"Creating MP4: {first_output}")
        ImageSequenceClip(first_segment_frames, fps=frame_rate).write_videofile(str(first_output), codec="libx264", threads=4, preset="ultrafast")
        output_files.append(str(first_output))

        # Generate second part if necessary
        if second_segment_frames:
            logging.info(f"Creating second MP4: {second_output}")
            ImageSequenceClip(second_segment_frames, fps=frame_rate).write_videofile(str(second_output), codec="libx264", threads=4, preset="ultrafast")
            output_files.append(str(second_output))

        logging.info(f"Generated MP4 files: {output_files}")
        return output_files
    except Exception as e:
        logging.error(f"Error processing {source_file}: {e}")
    finally:
        shutil.rmtree(temp_directory, ignore_errors=True)
        logging.info(f"Cleaned up temporary files for {source_file}")

# Function to merge multiple MP4 video files into a single file
def merge_video_clips(video_files, final_output):
    """Merges multiple MP4 clips into a single video."""
    logging.info(f"Merging videos into: {final_output}")
    
    if not video_files:
        logging.warning("No MP4 files found to merge.")
        return

    try:
        video_clips = [VideoFileClip(f) for f in sorted(video_files, key=lambda x: Path(x).name.lower())]
        concatenate_videoclips(video_clips).write_videofile(final_output, codec="libx264", threads=4, preset="ultrafast")
        logging.info(f"Merged video saved as {final_output}")
    except Exception as e:
        logging.error(f"Error merging videos: {e}")

# Function to parse command-line arguments for the script
def get_script_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Convert WEBP files to MP4 and optionally merge them")
    parser.add_argument("input_files", nargs='*', help="Input file names (.webp)")
    parser.add_argument("--fps", type=int, default=20, help="Frames per second (default: 20)")
    parser.add_argument("--percent", type=int, default=100, help="Percentage of the video to process in the first file (default: 100%)")
    parser.add_argument("--output", help="Directory for output MP4 files (optional)")
    parser.add_argument("--combine", help="Filename for combined output video (optional)")
    return parser.parse_args()

# Main execution block
if __name__ == "__main__":
    logging.info("Script execution started...")
    
    args = get_script_arguments()
    logging.info(f"Command-line arguments received: {vars(args)}")

    input_files = args.input_files if args.input_files else glob.glob("*.webp")
    
    if not input_files:
        logging.warning("No WEBP files found in the current directory or provided as arguments.")
        exit()

    logging.info(f"Files detected for processing: {input_files}")
    processed_output_files = []

    for file in input_files:
        logging.info(f"Processing: {file} ({args.percent}% in first file, {100 - args.percent}% in second file)")
        output_files = convert_webp_to_mp4(file, args.fps, args.percent, args.output)
        if output_files:
            processed_output_files.extend(output_files)

    if args.combine and processed_output_files:
        merge_video_clips(processed_output_files, args.combine)

    logging.info("Script execution completed!")
