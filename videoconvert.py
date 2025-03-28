import os
import shutil
import tempfile
import argparse
import glob
from moviepy import *
import PIL.Image

# Function to analyze image properties (size and mode: full or partial)
def extract_image_details(image_path):
    print(f"Analyzing image: {image_path}")  # Debugging
    with PIL.Image.open(image_path) as im:
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
    print(f"Image details: {image_info}")  # Debugging
    return image_info

# Function to extract frames from an image (handling GIFs and partial updates)
def generate_image_frames(image_path, temp_directory):
    print(f"Extracting frames from: {image_path}")  # Debugging
    frame_list = []
    mode = extract_image_details(image_path)['mode']
    with PIL.Image.open(image_path) as im:
        frame_index = 0
        palette = im.getpalette()
        last_frame = im.convert('RGBA')
        
        try:
            while True:
                frame_filename = os.path.join(temp_directory, f'{os.path.splitext(os.path.basename(image_path))[0]}-{frame_index}.png')
                if '.gif' in image_path and not im.getpalette():
                    im.putpalette(palette)
                new_frame = PIL.Image.new('RGBA', im.size)
                if mode == 'partial':
                    new_frame.paste(last_frame)
                new_frame.paste(im, (0, 0), im.convert('RGBA'))
                new_frame.save(frame_filename, 'PNG')
                frame_list.append(frame_filename)
                
                frame_index += 1
                last_frame = new_frame
                im.seek(im.tell() + 1)
        except EOFError:
            pass
    
    print(f"Extracted {len(frame_list)} frames from {image_path}")  # Debugging
    return frame_list

# Function to convert a WEBP image sequence into an MP4 video with optional splitting
def convert_webp_to_mp4(source_file, frame_rate=20, split_ratio=100, output_dir=None):
    print(f"Converting {source_file} to MP4...")  # Debugging
    temp_directory = tempfile.mkdtemp()
    try:
        extracted_frames = generate_image_frames(source_file, temp_directory)
        if not extracted_frames:
            print(f"No frames extracted from {source_file}")
            return None
        
        split_index = int(len(extracted_frames) * (split_ratio / 100))
        first_segment_frames, second_segment_frames = extracted_frames[:split_index], extracted_frames[split_index:]
        base_filename = os.path.splitext(os.path.basename(source_file))[0]
        
        # Output filenames will be based on the specified output directory or current working directory
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            first_output = os.path.join(output_dir, f'{base_filename}_part1.mp4')
            second_output = os.path.join(output_dir, f'{base_filename}_part2.mp4') if second_segment_frames else None
        else:
            first_output = f'{base_filename}_part1.mp4'
            second_output = f'{base_filename}_part2.mp4' if second_segment_frames else None
        
        # Generate first part of the video
        print(f"Creating MP4: {first_output}")  # Debugging
        ImageSequenceClip(first_segment_frames, fps=frame_rate).write_videofile(first_output, codec="libx264", threads=4, preset="ultrafast")
        output_files = [first_output]
        
        if second_segment_frames:
            print(f"Creating second MP4: {second_output}")  # Debugging
            ImageSequenceClip(second_segment_frames, fps=frame_rate).write_videofile(second_output, codec="libx264", threads=4, preset="ultrafast")
            output_files.append(second_output)
        
        print(f"Generated MP4 files: {output_files}")  # Debugging
        return output_files
    finally:
        shutil.rmtree(temp_directory)
        print(f"Cleaned up temporary files for {source_file}")  # Debugging

# Function to merge multiple MP4 video files into a single file
def merge_video_clips(video_files, final_output):
    print(f"Merging videos into: {final_output}")  # Debugging
    if not video_files:
        print("No MP4 files found to merge.")
        return
    
    video_clips = [VideoFileClip(f) for f in sorted(video_files, key=lambda x: os.path.basename(x).lower())]
    concatenate_videoclips(video_clips).write_videofile(final_output, codec="libx264", threads=4, preset="ultrafast")
    print(f"Merged video saved as {final_output}")

# Function to parse command-line arguments for the script
def get_script_arguments():
    parser = argparse.ArgumentParser(description="Convert WEBP files to MP4 and optionally merge them")
    parser.add_argument("input_files", nargs='*', help="Input file names (.webp)")
    parser.add_argument("--fps", type=int, default=20, help="Frames per second (default: 20)")
    parser.add_argument("--percent", type=int, default=100, help="Percentage of the video to process in the first file (default: 100%)")
    parser.add_argument("--output", help="Directory for output MP4 files (optional)")
    parser.add_argument("--combine", help="Filename for combined output video (optional)")
    return parser.parse_args()

# Main execution block
if __name__ == "__main__":
    print("Script execution started...")  # Debugging
    args = get_script_arguments()
    
    print("Command-line arguments received:", vars(args))  # Debugging
    
    input_files = args.input_files if args.input_files else glob.glob("*.webp")
    
    if not input_files:
        print("No WEBP files found in the current directory or provided as arguments.")
        exit()
    
    print(f"Files detected for processing: {input_files}")  # Debugging
    
    processed_output_files = []
    
    for file in input_files:
        print(f"Processing: {file} ({args.percent}% in first file, {100 - args.percent}% in second file)")
        output_files = convert_webp_to_mp4(file, args.fps, args.percent, args.output)
        if output_files:
            processed_output_files.extend(output_files)
    
    if args.combine and processed_output_files:
        final_output = args.combine
        merge_video_clips(processed_output_files, final_output)
    
    print("Script execution completed!")  # Debugging
