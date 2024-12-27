import os
import streamlit as st
from faster_whisper import WhisperModel
import torch

# Function to transcribe audio using Faster Whisper
def transcribe_audio(audio_path):
    try:
        st.write("Transcribing audio...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = WhisperModel("base.en", device=device)
        st.write(f"Model loaded on {device}")
        
        segments, info = model.transcribe(
            audio=audio_path,
            beam_size=5,
            language="en",
            max_new_tokens=128,
            condition_on_previous_text=False
        )
        
        extracted_texts = [[segment.text, segment.start, segment.end] for segment in segments]
        return extracted_texts
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return []

# Streamlit UI
st.title("Audio Transcription with Faster Whisper")
st.write("Upload an audio file to see its transcription.")

# File uploader
uploaded_file = st.file_uploader("Upload Audio File", type=["wav", "mp3", "m4a"])

if uploaded_file is not None:
    # Save the uploaded file temporarily
    audio_path = f"temp_{uploaded_file.name}"
    with open(audio_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.audio(audio_path, format="audio/wav")
    
    # Transcription button
    if st.button("Transcribe"):
        transcriptions = transcribe_audio(audio_path)
        
        if transcriptions:
            # Display transcription in Streamlit
            st.markdown("## Transcription Output:")
            transcription_text = ""
            
            for text, start, end in transcriptions:
                transcription_text += f"{start:.2f} - {end:.2f}: {text}\n"
            
            st.text_area("Transcription", transcription_text, height=300)
        else:
            st.error("No transcription could be generated.")
    
    # Clean up temporary file
    os.remove(audio_path)
