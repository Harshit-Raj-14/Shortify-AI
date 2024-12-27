import streamlit as st
import tempfile
import os
import google.generativeai as genai
from moviepy import VideoFileClip
from dotenv import load_dotenv
import json

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

transcribe_prompt = '''
Please transcribe the following audio and provide the transcription in JSON format. 
The JSON should include each segment of text with its corresponding start and end timestamps. 
Each entry in the JSON should have the following structure:
{
  "text": "Transcribed text here",
  "start": "Start timestamp",
  "end": "End timestamp"
}
Don't print anything else.
'''

highlight_system_prompt = '''
Based on the transcription provided by the user with start and end times, highlight the main parts in less than 1 minute that can be directly converted into a short. 
Highlight it so that it's interesting and also keep the timestamps for the clip to start and end. Only select a continuous part of the video.

Follow this format and return valid JSON:
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
        st.write("Transcribing audio...")
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
        audio_file = genai.upload_file(path=audio_file_path)
        response = model.generate_content(
        [
            transcribe_prompt,
            audio_file
        ]
        )
        return response.text
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return ""

def generate_highlights(transcription):
    try:
        model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
        response = model.generate_content("highlight_system_prompt="+highlight_system_prompt+" AND transcription="+transcription)
        highlight_response = response.text.strip()
        return highlight_response
    #     return json.loads(highlight_response)
    # except json.JSONDecodeError:
    #     st.error("Failed to parse highlights. Please try again.")
    #     return []
    except Exception as e:
        st.error(f"Error generating highlights: {e}")
        return "np"

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
                highlights = generate_highlights(transcription_text)
                st.session_state["highlights"] = highlights

# Display transcription and highlights side by side
if st.session_state["transcription"] and st.session_state["highlights"]:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Transcription")
        st.markdown(st.session_state["transcription"], unsafe_allow_html=True)

    with col2:
        st.subheader("Highlights")
        st.markdown(st.session_state["highlights"], unsafe_allow_html=True)
