# Input parameters
words = ["This", "is", "a", "test", "overlay", "for", "the", "video"]
duration = 10  # Example video duration
font_path = "./some_path/some_font.ttf"  # Replace with the actual font path
font_size = 20

text_clips = []

try:
    # Try to load the font using BytesIO
    try:
        with open(font_path, "rb") as font_file:
            font_data = font_file.read()
        font = ImageFont.truetype(BytesIO(font_data), size=font_size)
    except OSError as e:
        print(f"Error loading font: {e}")
        font = None  # If font loading fails, font remains None

    if font is None:
        raise ValueError("Font could not be loaded. Please check the font path.")

    # Create text overlays
    for i in range(0, len(words), 2):
        text = " ".join(words[i:i + 2])
        start_time = i // 2
        if start_time >= duration:
            break

        try:
            text_clip = TextClip(
                text,
                font=BytesIO(font_data),  # Use BytesIO workaround for the font
                font_size=font_size,
                color="white"
            ).set_position(("center", "bottom")).set_start(start_time).set_duration(1)
            text_clips.append(text_clip)
        except Exception as e:
            print(f"Error creating text clip for text '{text}': {e}")

except Exception as e:
    print(f"An error occurred during text overlay creation: {e}")

# At this point, text_clips contains the successfully created text clips
