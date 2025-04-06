import os
import sys
import subprocess
import openai
from dotenv import load_dotenv
import tempfile
import json

def process_video(video_path):
    print(f"Processing video: {video_path}")
    
    # Create a temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract audio using FFmpeg
        print("Extracting audio...")
        audio_path = os.path.join(temp_dir, "audio.mp3")
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'libmp3lame',  # Use MP3 codec
            '-q:a', '2',  # High quality
            '-y',  # Overwrite output file if it exists
            audio_path
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Error extracting audio: {e.stderr.decode()}")
            return None
        
        # Transcribe audio
        print("Transcribing audio...")
        with open(audio_path, "rb") as audio_file:
            transcript_obj = openai.Audio.transcribe("whisper-1", audio_file)
            transcript_text = transcript_obj.text
        
        # Generate summary
        print("Generating summary...")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates meeting summaries."},
                {"role": "user", "content": f"Please create a summary of this meeting transcript with bullet points for key decisions, action items, timeline, and budget:\n\n{transcript_text}"}
            ]
        )
        
        summary = response.choices[0].message.content
        
        return {
            "transcript": transcript_text,
            "summary": summary
        }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_file.py <video_file_path>")
        sys.exit(1)
    
    # Load environment variables
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    # Process the video
    result = process_video(sys.argv[1])
    
    if result:
        # Print results
        print("\nTranscript:")
        print(result["transcript"])
        print("\nSummary:")
        print(result["summary"])
        
        # Save results to files
        with open("transcript.txt", "w") as f:
            f.write(result["transcript"])
        
        with open("summary.txt", "w") as f:
            f.write(result["summary"])
        
        print("\nResults saved to transcript.txt and summary.txt")
    else:
        print("Failed to process video.") 