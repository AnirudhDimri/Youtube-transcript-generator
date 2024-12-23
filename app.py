import os
import logging
import tempfile
import streamlit as st
import nltk
from youtube_transcript_api import YouTubeTranscriptApi
from deepmultilingualpunctuation import PunctuationModel
from index import (  # Import functions from your existing index.py
    parse_youtube_url,
    getVideoInfo,
    clean_for_filename,
    process_and_save_transcript,
    remove_period_after_hashes,
    add_punctuation,
)
import time  # Added for file existence check

# Ensure NLTK punkt tokenizer is available
nltk.download('punkt')

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


def run_streamlit_app():
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
                # Create a secure temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Parse video details
                    video_id = parse_youtube_url(video_url)
                    video_info = getVideoInfo(video_id)
                    final_filename = filename or clean_for_filename(video_info["title"]) or clean_for_filename(video_id)
                    final_output_path = os.path.join(temp_dir, f"{final_filename}.md")

                    # Generate transcript
                    st.info("Generating transcript... Please wait.")
                    process_and_save_transcript(
                        video_id=video_id,
                        video_info=video_info,
                        language=language,
                        generate_punctuated=generate_punctuated,
                        output_dir=temp_dir,
                        filename=final_filename,
                        verbose=False,
                        punctuation_model=""
                    )

                    # Wait for the file to be created
                    retries = 5
                    while not os.path.exists(final_output_path) and retries > 0:
                        time.sleep(0.5)  # Wait for 500ms
                        retries -= 1

                    # Check if the file exists
                    if not os.path.exists(final_output_path):
                        st.error("Error: Transcript file could not be created.")
                        return

                    # Display and download transcript
                    with open(final_output_path, "r", encoding="utf-8") as file:
                        transcript_content = file.read()
                        st.success("Transcript generated successfully!")
                        st.text_area("Generated Transcript", transcript_content, height=300)
                        st.download_button(
                            label="Download Transcript",
                            data=transcript_content,
                            file_name=f"{final_filename}.md",
                            mime="text/markdown"
                        )
            except Exception as e:
                st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    run_streamlit_app()

