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
Based on the transcription provided by the user with start and end times, I want three highlights of less than 30 seconds each. 
Each highlight should be continuous, interesting, and non-overlapping. Provide the timestamps for the start and end of each clip.

If any end time is more than the length of the clip, adjust it to be one second less than the total length of the clip. 
If the clip is too short, distribute the highlights equally across the duration of the video.

Follow this format and return valid JSON SCHEMA:
[
  {
    "start": "Start time of the first clip in HH:MM:SS format",
    "highlight": "Highlight text for the first clip",
    "transcript": "What part of transcript was said between start and end of the first clip",
    "end": "End time of the first clip in HH:MM:SS format"
  },
  {
    "start": "Start time of the second clip in HH:MM:SS format",
    "highlight": "Highlight text for the second clip",
    "transcript": "What part of transcript was said between start and end of the second clip",
    "end": "End time of the second clip in HH:MM:SS format"
  },
  {
    "start": "Start time of the third clip in HH:MM:SS format",
    "highlight": "Highlight text for the third clip",
    "transcript": "What part of transcript was said between start and end of the third clip",
    "end": "End time of the third clip in HH:MM:SS format"
  }
]

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
            # start_time_int = int((parse_time(data_json[0]["start"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
            # end_time_int = int((parse_time(data_json[0]["end"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
            # print("Got the start and end time ✅")
            # print(f"Start Time: {start_time}")
            # print(f"End Time: {end_time}")
            # print(f"Start Time: {start_time_int}")
            # print(f"End Time: {end_time_int}")
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
        video_clips = []
        main_video = mp.VideoFileClip(video_file)
        # Process each highlight
        for i, highlight in enumerate(highlight_json):
            # Parse highlight JSON
            start_time = int((parse_time(highlight_json[i]["start"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
            end_time = int((parse_time(highlight_json[i]["end"]) - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
            print("Got the start and end time ✅")
            print(start_time)
            print(end_time)
            total_duration = main_video.duration
            if(start_time>=total_duration): 
                start_time=total_duration/3
                end_time=start_time+20
            if(end_time>=total_duration):
                start_time=total_duration/3
                end_time=start_time+20


            # Load video
            video = main_video.subclipped(start_time, end_time)
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
            transcript = highlight_json[i]["transcript"]
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
                    text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 4)
                    text_x = (frame.shape[1] - text_size[0]) // 2
                    text_y = height - 50
                    
                    # Overlay the text on the frame
                    cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 4)
                    
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
            video_clips.append(output_file)
        return video_clips
    
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

    if st.button('Generate YT Shorts'):
        with st.spinner('Processing video...'):
            audio_path = extract_audio_from_video(video_path)
            if audio_path:
                transcription_text = transcribe_audio(audio_path)
                st.session_state["transcription"] = transcription_text

                # Generate highlights based on the transcription
                highlights_json = generate_highlights(video_path, transcription_text)
                st.session_state["highlights"] = highlights_json

                # Process the video
                processed_video_paths = process_video(str(video_path), highlights_json)

                if processed_video_paths:
                    st.session_state["processed_videos"] = processed_video_paths  # Save paths in session state
                    st.success("Video processed successfully!")
                else:
                    st.error("Failed to process the video.")

# Display processed videos and download links
if "processed_videos" in st.session_state and st.session_state["processed_videos"]:
    for i, processed_video_path in enumerate(st.session_state["processed_videos"]):
        st.write(f"### YT Short {i + 1}")
        st.video(processed_video_path)

        # Generate a download link for the processed video
        with open(processed_video_path, "rb") as file:
            video_bytes = file.read()

        st.download_button(
            label=f"Download YT Short {i + 1}",
            data=video_bytes,
            file_name=f"yt_short_{i + 1}.mp4",
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