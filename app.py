import streamlit as st
import tempfile
import os
import google.generativeai as genai
from moviepy import VideoFileClip
import moviepy as mp
from dotenv import load_dotenv
import json
from pathlib import Path
from datetime import datetime
from io import BytesIO
import tempfile

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

transcribe_prompt = '''
Please transcribe the following audio and provide the transcription in JSON format. 
The JSON should include each segment of text with its corresponding start and end timestamps. 
Each entry in the JSON should have the following structure: I want only the json nothing else.
{ "text": "Transcribed text here", "start": "Start timestamp", "end": "End timestamp" }
Don't print anything else.
'''

highlight_system_prompt = '''
Based on the transcription provided by the user with start and end times, I want only one highlight of less than 1 minute that can be directly converted into a short. 
Highlight it so that it's interesting and also keep the timestamps for the clip to start and end. 
If the end time is more than length of clip make it one second less than the total length of clip. Only select a continuous part of the video.

Follow this format and return valid JSON SCHEMA:
[{
  "start": "Start time of the clip in format: HH:MM:SS, put values even if its 0",
  "content": "Highlight Text",
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

def generate_highlights(transcription):
    try:
        print("highlighting started...")
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
        response = model.generate_content("highlight_system_prompt="+highlight_system_prompt+" AND transcription="+transcription)
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

        # Load the video
        video = mp.VideoFileClip(video_file)
        # Trim video to highlight duration
        trimmed_video = video.subclipped(start_time, end_time)
        # Crop to 9:16 aspect ratio
        width, height = trimmed_video.size
        new_width = int(height * 9 / 16)
        x_center = width // 2
        cropped_video = trimmed_video.cropped(
            x1=x_center - new_width // 2, x2=x_center + new_width // 2
        )
        print("Cropped and trimmed ✅")

        # Save to a temporary file instead of BytesIO
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_file_path = temp_file.name
            cropped_video.write_videofile(temp_file_path, codec="libx264", audio_codec="aac")
            print(f"Saved processed video to {temp_file_path}")

        return temp_file_path

    except Exception as e:
        st.error(f"Error processing video: {e}")
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
                highlights_json = generate_highlights(transcription_text)
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
