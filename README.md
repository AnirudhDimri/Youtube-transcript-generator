# YouTube Transcript Generator

A simple Streamlit-based web application that generates transcripts for YouTube videos using the [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) and provides options for punctuation restoration and downloadable transcripts.

## Features

- Generate transcripts for YouTube videos with subtitles.
- Add punctuation to transcripts using the Deep Multilingual Punctuation Model.
- Capitalize sentences for a polished output.
- Save the transcript as a downloadable `.md` file.
- Retries fetching transcripts for increased reliability.
- Uses temporary storage for managing transcript files.

## Technologies Used

- **Python**: Backend scripting.
- **Streamlit**: Web application framework.
- **NLTK**: Natural Language Toolkit for sentence tokenization.
- **Deep Multilingual Punctuation**: Adds punctuation to transcripts.
- **YouTube Transcript API**: Fetches video transcripts.

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/AnirudhDimri/Youtube-transcript-generator.git
   cd Youtube-transcript-generator

2. Run the app locally:
   streamlit run app.py
