import streamlit as st
import tempfile
import os
import google.generativeai as genai
from moviepy import VideoFileClip
from dotenv import load_dotenv

load_dotenv()

# Configure Google API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def transcribe_audio(audio_file_path):
    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
    audio_file = genai.upload_file(path=audio_file_path)
    response = model.generate_content(
        [
            "Transcribe audio with proper time stamping.",
            audio_file
        ]
    )
    return response.text

def save_uploaded_file(uploaded_file):
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

# Streamlit app interface
st.title('Video Transcriber')

# Initialize session state for transcription
if "transcription" not in st.session_state:
    st.session_state["transcription"] = None

video_file = st.file_uploader("Upload Video File", type=['mp4'])
if video_file is not None:
    video_path = save_uploaded_file(video_file)  # Save the uploaded file and get the path
    st.video(video_path)

    if st.button('Transcribe Video'):
        with st.spinner('Processing video...'):
            audio_path = extract_audio_from_video(video_path)
            if audio_path:
                st.session_state["transcription"] = transcribe_audio(audio_path)

# Display transcription if available
if st.session_state["transcription"]:
    st.subheader("Transcription")
    st.markdown(st.session_state["transcription"], unsafe_allow_html=True)
