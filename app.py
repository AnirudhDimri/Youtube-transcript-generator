import os
import tempfile
import logging
import streamlit as st
import nltk
from index import (  # Import functions from the updated index.py
    parse_youtube_url,
    clean_for_filename,
    process_and_save_transcript,
)

# Ensure NLTK punkt tokenizer is available
nltk.download('punkt')

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def run_streamlit_app():
    # Use tempfile for output directory
    output_dir = tempfile.gettempdir()

    # App title and description
    st.title("YouTube Video Transcript Generator")
    st.write("Generate and download transcripts for YouTube videos.")

    # Input Fields
    video_url = st.text_input("YouTube Video URL", placeholder="Enter a valid YouTube URL")
    language = st.selectbox("Select Language", ["en", "es", "fr", "de"], index=0)
    generate_punctuated = st.checkbox("Generate Punctuated Transcript", value=True)
    filename = st.text_input("Custom Filename (Optional)", placeholder="Leave blank for default naming")

    # Button to generate transcript
    if st.button("Generate Transcript"):
        if not video_url:
            st.error("Please enter a valid YouTube URL.")
        else:
            try:
                # Parse video details
                video_id = parse_youtube_url(video_url)
                final_filename = filename or clean_for_filename(video_id)
                final_output_path = os.path.join(output_dir, f"{final_filename}.md")

                # Generate transcript
                st.info("Generating transcript... Please wait.")
                process_and_save_transcript(
                    video_id=video_id,
                    language=language,
                    generate_punctuated=generate_punctuated,
                    output_dir=output_dir,
                    filename=final_filename,
                    verbose=False,
                    punctuation_model="",
                )

                # Display and download transcript
                with open(final_output_path, "r", encoding="utf-8") as file:
                    transcript_content = file.read()
                    st.success("Transcript generated successfully!")
                    st.text_area("Generated Transcript", transcript_content, height=300)
                    st.download_button(
                        label="Download Transcript",
                        data=transcript_content,
                        file_name=f"{final_filename}.md",
                        mime="text/markdown",
                    )
            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    run_streamlit_app()
