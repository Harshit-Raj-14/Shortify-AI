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
Highlight it so that it's interesting and also keep the timestamps for the clip to start and end. Only select a continuous part of the video.

Follow this format and return valid JSON SCHEMA:
[{
  "start": "Start time of the clip",
  "content": "Highlight Text",
  "end": "End Time for the highlighted clip"
}]
It should be one continuous clip as it will then be cut from the video and uploaded as a TikTok video. So only have one start, end, and content.

Don't say anything else, just return proper JSON. No explanation.
'''

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
            start_time_int = int((datetime.strptime(data_json[0]["start"], "%H:%M:%S.%f") - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
            end_time_int = int((datetime.strptime(data_json[0]["end"], "%H:%M:%S.%f") - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
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


def process_video(video_file, highlight_json):
    try:
        # Parse highlight JSON
        start_time = int((datetime.strptime(highlight_json[0]["start"], "%H:%M:%S.%f") - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
        end_time = int((datetime.strptime(highlight_json[0]["end"], "%H:%M:%S.%f") - datetime.strptime("00:00:00.000", "%H:%M:%S.%f")).total_seconds())
        print("Got the start and end time ✅")
        print(start_time)
        print(end_time)
        # Load the video
        print("input video path:"+video_file)
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
        # Save the cropped video
        output_path = Path("yt_short.mp4")
        cropped_video.write_videofile(
            str(output_path), codec="libx264", audio_codec="aac"
        )
        print("Saved output video ✅")
        return output_path

    except Exception as e:
        st.error(f"Error processing video: {e}")
        return None


# Streamlit app interface
st.title('Video Transcriber and Highlighter')

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
                # Validate JSON format
                input_video_path = Path("video_talk.mp4")
                output_path = process_video(str(video_path), highlights_json)


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
