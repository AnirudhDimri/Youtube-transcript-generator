import os
import argparse
import logging
import re
import math
import warnings
import subprocess
import platform

import nltk
nltk.download('punkt')
from deepmultilingualpunctuation import PunctuationModel
from youtube_transcript_api import YouTubeTranscriptApi

logging.basicConfig(level=logging.INFO, force=True)
# stop any warnings
warnings.filterwarnings("ignore")

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
    return re.sub(r'(#\.|##\.)', lambda match: match.group(1)[:-1], text)

def remove_escape_sequences(text):
    # Remove escape sequences like \n, \r\n, \t, \b, \r
    return re.sub(r'\\[nrtb]|\\r\n', '', text)

def remove_double_greater_than(text):
    # Replace occurrences of ">>" with an empty string
    cleaned_text = re.sub(r'>>', '', text)
    return cleaned_text

def add_punctuation(text, punctuation_model):
    if punctuation_model != "":
        model = PunctuationModel(model=punctuation_model)
    else:
        model = PunctuationModel()

    punctuated_text = model.restore_punctuation(text)
    return punctuated_text

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
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
    transcript = ''
    for i, line in enumerate(transcript_list):
        # Floor and convert to integer
        line['text'] = remove_tags(line['text'])
        line['text'] = remove_escape_sequences(line['text'])
        line['text'] = remove_double_greater_than(line['text'])
        if line['text']:
            transcript += line['text'].strip() + ' '
        # Log progress information
        if verbose and i % 100 == 0:  # Adjust the log frequency as needed
            logging.info(f"Processed {i} lines out of {len(transcript_list)}")

    return transcript

def process_and_save_transcript(video_id, language, generate_punctuated, output_dir, filename, verbose, punctuation_model):
    try:
        logging.info('Getting transcript...')
        raw_transcript = get_transcript(video_id, language, verbose)

        if generate_punctuated:
            logging.info('Generating punctuated transcript...')
            with_punctuation = add_punctuation(raw_transcript, punctuation_model)
            with_punctuation = remove_period_after_hashes(with_punctuation)
            logging.info('Capitalizing sentences...')
            sentences = nltk.sent_tokenize(with_punctuation)
        else:
            sentences = nltk.sent_tokenize(raw_transcript)

        # Capitalize sentences without batching
        capitalized_sentences = capitalize_sentences(sentences)

        double_linesep = os.linesep + os.linesep
        capitalized_transcript = double_linesep.join(capitalized_sentences)
        output_path = os.path.join(output_dir, f'{filename}.md')

        logging.info(f'Saving transcript to {output_path}...')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(capitalized_transcript)

        # Confirm file creation
        if os.path.exists(output_path):
            logging.info(f'Transcript successfully saved to "{output_path}"')
        else:
            raise FileNotFoundError(f"File {output_path} could not be created.")

        if generate_punctuated:
            logging.info(f'Punctuated transcript saved to "{output_path}"')
        else:
            logging.info(f'Raw transcript saved to "{output_path}"')

    except Exception as e:
        logging.error(f'Error: {e}')

def main():
    parser = argparse.ArgumentParser(
        description='Process YouTube video transcript and save it.')
    parser.add_argument('url', type=str, help='YouTube video URL')
    parser.add_argument('-l', '--language', type=str, default='en',
                        help='Language for the transcript (default: en)')
    parser.add_argument('-p', '--punctuated', action='store_true',
                        help='Generate punctuated transcript (default: False)')
    parser.add_argument('-o', '--output_dir', type=str, default='.',
                        help='Output directory for saving the transcript (default: .)')
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

    if args.auto_open:
        output_path = os.path.join(args.output_dir, f'{filename}.md')
        open_file(output_path)

if __name__ == "__main__":
    main()

