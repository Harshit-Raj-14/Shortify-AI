import streamlit as st
import tempfile
import os
import google.generativeai as genai
from moviepy import VideoFileClip
from moviepy import *
import moviepy as mp
from dotenv import load_dotenv
import json
from pathlib import Path
from datetime import datetime
from io import BytesIO
import tempfile
import re
from PIL import ImageFont
import cv2
import whisper

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

transcribe_prompt = '''
Please transcribe the following audio and provide the transcription in JSON format. 
The JSON should include each segment of text with its corresponding start and end timestamps. 
The start and end time stamp should all be correct and always less than the total length of audio.[important] start and end time can enver exceed length of audio clip given to you.
Each entry in the JSON should have the following structure: I want only the json nothing else.
{ "text": "Transcribed text here", "start": "Start timestamp", "end": "End timestamp" }
Don't print anything else.
'''

highlight_system_prompt = '''
Based on the transcription provided by the user with start and end times, I want only one highlight of less than 30 seconds that can be directly converted into a short. 
Highlight it so that it's interesting and also keep the timestamps for the clip to start and end. 
If the end time is more than length of clip make it one second less than the total length of clip. Only select a continuous part of the video.

Follow this format and return valid JSON SCHEMA:
[{
  "start": "Start time of the clip in format: HH:MM:SS, put values even if its 0",
  "highlight": "Highlight Text",
  "transcript": "What part of trancript was said between start and end",
  "end": "End Time for the highlighted clip in format: HH:MM:SS, put values even if its 0"
}]
It should be one continuous clip as it will then be cut from the video and uploaded as a TikTok video. So only have one start, end, and content.

Don't say anything else, just return proper JSON. No explanation.
'''

def parse_time(time_str):
    formats = [
        "%H:%M:%S.%f",  # hours:minutes:seconds.milliseconds
        "%H:%M:%S",     # hours:minutes:seconds
        "%M:%S",         # minutes:seconds
        "%S.%f",         # seconds.milliseconds
        "%H:%M",         # hours:minutes
        "%M:%S.%f",      # minutes:seconds.milliseconds
        "%H:%M:%S,%f",   # hours:minutes:seconds,milliseconds (comma separated)
        "%H:%M,%f",      # hours:minutes,milliseconds (comma separated)
        "%M:%S,%f",      # minutes:seconds,milliseconds (comma separated)
        "%H:%M:%S.%f %p", # 12-hour format with AM/PM (example: 10:30:15.123 PM)
        "%I:%M:%S.%f %p", # 12-hour format with AM/PM and milliseconds (example: 10:30:15.123 PM)
        "%I:%M:%S %p",    # 12-hour format with AM/PM without milliseconds (example: 10:30:15 PM)
        "%I:%M %p",       # 12-hour format with AM/PM (example: 10:30 AM)
        "%H:%M:%S",       # for hours:minutes:seconds without milliseconds
        "%H:%M:%S.%f",    # for hours:minutes:seconds with milliseconds
        "%S",             # just seconds
        "%S.%f",          # seconds with milliseconds
        "%Y-%m-%dT%H:%M:%S.%fZ", # ISO 8601 format (example: 2024-12-30T15:30:00.123Z)
        "%Y-%m-%d %H:%M:%S",    # ISO 8601 without milliseconds (example: 2024-12-30 15:30:00)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Time string '{time_str}' does not match any known format.")


def save_uploaded_file(uploaded_file):
    """Save the uploaded file to a temporary directory and return the file path."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error handling uploaded file: {e}")
        return None

def extract_audio_from_video(video_file_path):
    try:
        video = VideoFileClip(video_file_path)
        audio_file_path = video_file_path.replace('.mp4', '.wav')
        video.audio.write_audiofile(audio_file_path)
        return audio_file_path
    except Exception as e:
        st.error(f"Error extracting audio from video: {e}")
        return None

def transcribe_audio(audio_file_path):
    try:
        print("Transcribing started...")
        st.write("Transcribing audio...")
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
        audio_file = genai.upload_file(path=audio_file_path)
        response = model.generate_content(
        [
            transcribe_prompt,
            audio_file
        ]
        )
        print("Transcribing Completed✅")
        return response.text
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return ""



def generate_highlights(video_file, transcription):
    try:
        print("highlighting started...")
        video = mp.VideoFileClip(video_file)
        duration = str(video.duration)
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
        response = model.generate_content("highlight_system_prompt="+highlight_system_prompt+" AND transcription="+transcription+"Also note that the start and end time should not exceed the total duration of video ="+duration+".If you only when it exceeds then take the middle 25 to 30s of the clip and put it as start and end time. Don't forget to do this.")
        highlight_response = response.text.strip()
        # print((type(highlight_response))) #-> list
        print(highlight_response)
        print("Highlighting Completed✅")
        if not highlight_response:
            print("Error: The json is empty.")
            return "none"
        try:
            # Parse the string as JSON
            print("parsing json...")
            print(highlight_response)
            # json_string = highlight_response.choices[0].message.content
            json_string = highlight_response.replace("json", "")
            json_string = json_string.replace("```", "")
            data_json = json.loads(json_string)
            print(data_json)
            print(type(data_json))
            # Extract start and end times as floats
            # start_time = float(data_json[0]["start"])
            # end_time = float(data_json[0]["end"])
            # Convert to integers
            start_time_int = int((parse_time(data_json[0]["start"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
            end_time_int = int((parse_time(data_json[0]["end"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
            print("Got the start and end time ✅")
            # print(f"Start Time: {start_time}")
            # print(f"End Time: {end_time}")
            print(f"Start Time: {start_time_int}")
            print(f"End Time: {end_time_int}")
            return data_json

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return "none"

    except Exception as e:
        print(f"Error generating highlights: {e}")
        return "none"


from io import BytesIO
import base64

def process_video(video_file, highlight_json):
    try:
        # Parse highlight JSON
        start_time = int((parse_time(highlight_json[0]["start"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
        end_time = int((parse_time(highlight_json[0]["end"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
        print("Got the start and end time ✅")
        print(start_time)
        print(end_time)

        # Load video
        video = VideoFileClip(video_file).subclipped(start_time, end_time)
        fps = int(video.fps)
        audio = video.audio
        cap = cv2.VideoCapture(video_file)
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        aspect_ratio = 9 / 16
        new_width = int(height * aspect_ratio)
        x_center = width // 2
        x1, x2 = x_center - new_width // 2, x_center + new_width // 2
        
        # Process transcript
        transcript = highlight_json[0]["transcript"]
        cleaned_transcript = re.sub(r"[^\w\s]", "", transcript)
        words = cleaned_transcript.split()
        
        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_file_path = temp_file.name
        out = cv2.VideoWriter(temp_file_path, fourcc, fps, (new_width, height))
        
        word_index = 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_time * fps)
        total_frames = int((end_time - start_time) * fps)
        
        frames_per_word = 30  # You can increase this value to make the words appear longer
        word_index = 0
        frame_idx = 0

        # Loop through each frame of the video
        for frame_idx in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            # Crop the frame to the desired aspect ratio
            frame = frame[:, x1:x2]
            
            # Show the current word if the frame index is within the time window for that word
            if word_index < len(words) and frame_idx // frames_per_word < word_index + 1:
                text = words[word_index]
                
                # Position the text in the center
                text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                text_x = (frame.shape[1] - text_size[0]) // 2
                text_y = height - 50
                
                # Overlay the text on the frame
                cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                # Increment word index after the word stays on screen for the designated number of frames
                if frame_idx % frames_per_word == 0:
                    word_index += 1

            # Write the frame to the video output
            out.write(frame)

        cap.release()
        out.release()
        
        # Add audio
        final_video = VideoFileClip(temp_file_path)
        # final_video = final_video.set_audio(audio)
        new_audioclip = CompositeAudioClip([audio])
        final_video.audio = new_audioclip
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        final_video.write_videofile(output_file, codec="libx264", audio_codec="aac")
        
        return output_file
    
    except Exception as e:
        print(f"Error processing video: {e}")
        return None




# Streamlit app interface
st.title('Shortify AI')

# Initialize session state for transcription and highlights
if "transcription" not in st.session_state:
    st.session_state["transcription"] = None
if "highlights" not in st.session_state:
    st.session_state["highlights"] = None

# File uploader
video_file = st.file_uploader("Upload Video File", type=['mp4'])
if video_file is not None:
    video_path = save_uploaded_file(video_file)  # Save the uploaded file and get the path
    st.video(video_path)

    if st.button('Process Video'):
        with st.spinner('Processing video...'):
            audio_path = extract_audio_from_video(video_path)
            if audio_path:
                transcription_text = transcribe_audio(audio_path)
                st.session_state["transcription"] = transcription_text

                # Generate highlights based on the transcription
                highlights_json = generate_highlights(video_path, transcription_text)
                st.session_state["highlights"] = highlights_json

                # Crop Video
                # input_video_path = Path("video_talk.mp4")
                # output_path = process_video(str(video_path), highlights_json)

                # Process the video
                processed_video_path = process_video(str(video_path), highlights_json)

                if processed_video_path:
                    st.success("Video processed successfully!")

                    # Generate a download link for the processed video
                    with open(processed_video_path, "rb") as file:
                        video_bytes = file.read()

                    st.download_button(
                        label="Download Video",
                        data=video_bytes,
                        file_name="yt_short.mp4",
                        mime="video/mp4"
                    )


# Display transcription and highlights side by side
if st.session_state["transcription"] and st.session_state["highlights"]:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Transcription")
        st.markdown(st.session_state["transcription"], unsafe_allow_html=True)

    with col2:
        st.subheader("Highlights")
        # st.write(type(highlights))
        st.markdown(st.session_state["highlights"], unsafe_allow_html=True)