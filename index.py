import os
import argparse
import logging
import re
import math
import warnings
import subprocess
import platform
import tempfile
import time

import nltk

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled



def open_file(filename):
    # Open the file using the default application
    logging.info(f'Opening "{filename}"...')
    try:
        if platform.system() == "Darwin":       # macOS
            subprocess.call(('open', filename))
        elif platform.system() == "Windows":    # Windows
            os.startfile(filename)
        else:                                   # linux variants
            subprocess.call(('xdg-open', filename))
    except Exception as e:
        logging.error(f'Error: {e}')

def clean_for_filename(title):
    # Define a regular expression to keep only alphanumeric characters, spaces, dots, hyphens, and various parentheses
    cleaned_title = re.sub(r'[^\w\s\.\-\(\)\[\]]', '', title)

    # Remove leading and trailing spaces
    return cleaned_title.strip()

def remove_tags(text):
    # Remove any text inside [] like [music]
    updated_text = re.sub(r'\[.*?\]', '', text)
    return updated_text

def remove_period_after_hashes(text):
    # Remove . after # or ##, considering newline characters
    return re.sub(r'(#\.||##\.)', lambda match: match.group(1)[:-1], text)

def remove_escape_sequences(text):
    # Remove escape sequences like \n, \r\n, \t, \b, \r
    return re.sub(r'\\[nrtb]|\\r\n', '', text)

def remove_double_greater_than(text):
    # Replace occurrences of ">>" with an empty string
    cleaned_text = re.sub(r'>>', '', text)
    return cleaned_text


def capitalize_sentences(sentences):
    # Capitalize the first letter of each sentence in a batch
    capitalized_sentences = [sentence[0].upper() + sentence[1:] for sentence in sentences]
    return capitalized_sentences

def parse_youtube_url(url):
    video_id_match = re.search(r'(?:youtube\.com\/.*?[?&]v=|youtu\.be\/)([^"&?\/\s]{11})', url)
    if video_id_match:
        return video_id_match.group(1)
    else:
        raise ValueError('Invalid YouTube URL')

def get_transcript(video_id, language, verbose=True):
    ytt_api = YouTubeTranscriptApi()

    try:
        fetched = ytt_api.fetch(video_id, languages=[language])
    except NoTranscriptFound:
        raise ValueError(f"Transcript not available in language '{language}'.")
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except Exception as e:
        logging.exception("Transcript failure:")
        raise RuntimeError(str(e))



    transcript_list = fetched.to_raw_data()
    transcript = ''

    for i, line in enumerate(transcript_list):
        line['text'] = remove_tags(line['text'])
        line['text'] = remove_escape_sequences(line['text'])
        line['text'] = remove_double_greater_than(line['text'])

        if line['text']:
            transcript += line['text'].strip() + ' '

        if verbose and i % 100 == 0:
            logging.info(f"Processed {i} lines out of {len(transcript_list)}")

    return transcript

def process_and_save_transcript(video_id, language, output_dir, filename, verbose):
    try:
        logging.info('Getting transcript...')
        raw_transcript = get_transcript(video_id, language, verbose)

        sentences = nltk.sent_tokenize(raw_transcript)

        # Capitalize sentences without batching
        capitalized_sentences = capitalize_sentences(sentences)

        double_linesep = os.linesep + os.linesep
        capitalized_transcript = double_linesep.join(capitalized_sentences)

        # Ensure file creation
        temp_file_path = os.path.join(output_dir, f"{filename}.md")
        with open(temp_file_path, "w", encoding="utf-8") as temp_file:
            temp_file.write(capitalized_transcript)

        if os.path.exists(temp_file_path):
            logging.info(f'Transcript successfully saved to "{temp_file_path}"')
            return temp_file_path
        else:
            raise FileNotFoundError(f"File {temp_file_path} could not be created.")

    except Exception as e:
        logging.error(f'Error: {e}')
        raise

def main():
    parser = argparse.ArgumentParser(
        description='Process YouTube video transcript and save it.')
    parser.add_argument('url', type=str, help='YouTube video URL')
    parser.add_argument('-l', '--language', type=str, default='en',
                        help='Language for the transcript (default: en)')
    parser.add_argument('-p', '--punctuated', action='store_true',
                        help='Generate punctuated transcript (default: False)')
    parser.add_argument('-o', '--output_dir', type=str, default=tempfile.gettempdir(),
                        help='Output directory for saving the transcript (default: system temp directory)')
    parser.add_argument('-f', '--filename', type=str, default='',
                        help='Filename for saving the transcript (default: Video Id)')
    parser.add_argument('-m', '--punctuation_model', type=str, default='',
                        help='Path to the punctuation model (default: None)')
    parser.add_argument('-a', '--auto-open', action='store_true',
                        help='Automatically open the generated file in the default application (default: False)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print verbose output (default: False)')

    args = parser.parse_args()

    # Install NLTK punkt if not already installed
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        logging.error('NLTK punkt not found.')
        logging.info('Downloading punkt...')
        try:
            nltk.download('punkt')
        except Exception as e:
            logging.error(f'Error: {e}')
            exit(1)

    # if verbose is false, set logging level to error
    if not args.verbose:
        logging.getLogger().setLevel(logging.ERROR)

    video_id = parse_youtube_url(args.url)
    filename = args.filename or clean_for_filename(video_id)

    process_and_save_transcript(video_id, args.language, args.punctuated,
                                args.output_dir, filename, args.verbose, args.punctuation_model)

if __name__ == "__main__":
    main()

