# webptomp4
**Webp to mp4 video converter**
Didint find any good webp to mp4 offline converter so i made simple one with Python3. Tested with WSL ubuntu 22.04.5LTS and Windows 11.
# Requirement:
Any OS that supports python3
1. Python3 Pillow
2. Python3 Moviepy
3. Python3 Argparse
4. Python3 Glob2
# Install for Ubuntu bash
`sudo apt-get update`\
`sudo apt-get install python3`\
`pip3 install moviepy pillow argparse glob2`
# Install for Windows cmd
`winget install python3`\
`pip3 install moviepy pillow argparse glob2`
# Usage:
Copy videoconvert.py in same folder as video files. Test commands (no user inputs default setting is 20framespersecond, set new fps with --fps number): \
`videoconvert.py --fps 16`\
`python3 videoconvert.py --fps 16` \
`python3 videoconvert.py a1_video.webp a2_video.webp --fps 16 --percent 50 --output videos --combine final.mp4 --log`

### Convert all webp files in same folder
Run test code: `python3 videoconvert.py --fps 16`\
\
![percentage](./images/image_normal.png)
### Convert percentage parts of video into 2 videos
Run test code: `python3 videoconvert.py --percent 80`\
\
![percentage](./images/image_prosent.png)

### Convert all videos and extra video file that combined all videos (videos sorted by filename a-z and 1-9), (combining videos may fail if the videos are incompatible with each other, such as having different resolutions)
Run test code: `python3 videoconvert.py --fps 16 --combine fullvideo.mp4`\
\
![combine](./images/image_combine.png)

### Save local logs in text file with --log (for debugging)
Run test code: `python3 videoconvert.py --log --fps 16 --combine fullvideo.mp4`\
\
![log](./images/image_log.png)
