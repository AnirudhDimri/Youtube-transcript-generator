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
import googleapiclient.discovery
import googleapiclient.errors
from deepmultilingualpunctuation import PunctuationModel
from youtube_transcript_api import YouTubeTranscriptApi

logging.basicConfig(level=logging.INFO, force=True)
# stop any warnings
warnings.filterwarnings("ignore")


def open_file(filename):
    # Open the file using the default application
    logging.info(f'Opening \'{filename}\'...')
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
    # Some old videos contain escape sequences like \n in their subtitle
    # Remove \n, \r\n, \t, \b, \r
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
    capitalized_sentences = [sentence[0].upper() + sentence[1:]
                             for sentence in sentences]
    return capitalized_sentences


def parse_youtube_url(url):
    video_id_match = re.search(
        r'(?:youtube\.com\/.*?[?&]v=|youtu\.be\/)([^"&?\/\s]{11})', url)
    if video_id_match:
        return video_id_match.group(1)
    else:
        raise ValueError('Invalid YouTube URL')


def parse_chapters(description):
    lines = description.split("\n")
    regex = re.compile(r"(\d{0,2}:?\d{1,2}:\d{2})")
    chapters = []

    for line in lines:
        matches = regex.findall(line)
        if matches:
            ts = matches[0]
            title = line.replace(ts, "").strip()

            # Check if the title contains another timestamp and remove it
            title = re.sub(r'\d{0,2}:?\d{1,2}:\d{2}', '', title).strip().strip(
                '-').strip().strip('-').strip()

            chapters.append({
                "timestamp": ts,
                "title": title,
            })

    return chapters


def get_transcript(video_id, language, video_info, verbose=True):
    transcript_list = YouTubeTranscriptApi.get_transcript(
        video_id, languages=[language])

    if video_info["title"] != "":
        transcript = f'# {video_info["title"]}\n\n'
    else:
        transcript = ''
    current_chapter_index = 0
    chapters = video_info["chapters"]
    logging.info(f"""Transcript List Length: {
                 len(transcript_list)}, Chapter Length: {len(chapters)}""")

    for i, line in enumerate(transcript_list):
        # Floor and convert to integer
        start_time = int(math.floor(line['start']))

        # Check if current_chapter_index is within the valid range
        if 0 <= current_chapter_index < len(chapters):
            chapter_time = chapters[current_chapter_index]['timestamp']

            try:
                # Extract start time from the chapter timestamp
                chapter_start = chapter_time.strip()
                chapter_start_seconds = sum(
                    int(x) * 60 ** i for i, x in enumerate(reversed(chapter_start.split(':'))))
                chapters[current_chapter_index]["title"] = chapters[current_chapter_index]["title"].strip()
                buffer_time = 2

                if start_time >= chapter_start_seconds - buffer_time:
                    # If the start time is within the buffer time, add the chapter title
                    transcript += f'\n\n## {chapters[current_chapter_index]["title"]}\n\n'
                    current_chapter_index += 1
            except Exception as e:
                logging.error(
                    f"Error processing chapter timestamp: {chapter_time}")
                logging.error(f"Error details: {e}")

        line['text'] = remove_tags(line['text'])
        line['text'] = remove_escape_sequences(line['text'])
        line['text'] = remove_double_greater_than(line['text'])
        if line['text']:
            transcript += line['text'].strip() + ' '

        # Log progress information
        if verbose and i % 100 == 0:  # Adjust the log frequency as needed
            logging.info(f"Processed {i} lines out of {len(transcript_list)}")

    return transcript


def process_and_save_transcript(video_id, video_info, language, generate_punctuated, output_dir, filename, verbose, punctuation_model):
    try:
        logging.info('Getting transcript...')
        raw_transcript = get_transcript(
            video_id, language, video_info, verbose)

        if generate_punctuated:
            logging.info('Generating punctuated transcript...')
            with_punctuation = add_punctuation(
                raw_transcript, punctuation_model)
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

        # set log level to info to print the output path
        logging.getLogger().setLevel(logging.INFO)
        if generate_punctuated:
            logging.info(f'Punctuated transcript saved to \'{output_path}\'')
        else:
            logging.info(f'Raw transcript saved to \'{output_path}\'')

    except Exception as e:
        logging.error(f'Error: {e}')


def getVideoInfo(video_id):
    try:
        # Set up Google API credentials using API key
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if api_key is None:
            raise Exception(
                "No API key found, please set the YOUTUBE_API_KEY environment variable. \n Example: export YOUTUBE_API_KEY=your_api_key"
            )
        logging.info('Getting video info...')
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(part="id,snippet",
                                        id=video_id
                                        )
        response = request.execute()
        title = response['items'][0]['snippet']['title']
        description = response['items'][0]['snippet']['description']
        data = {"title": title, "chapters": parse_chapters(description)}
        return data
    except Exception as e:
        logging.error(f'Error: {e}')
        return {"title": "", "chapters": []}


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
                        help='Filename for saving the transcript (default: Video Title or Video Id)')
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

            # Check if the Errno 60 error is thrown and suggest using a proxy/vpn
            if 'Errno 60' in str(e):
                logging.error(
                    'Error downloading punkt. Try using a proxy or a VPN.')
            else:
                logging.error('Error downloading punkt. Exiting.')
            exit(1)

    # if verbose is false, set logging level to error
    if not args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    video_id = parse_youtube_url(args.url)
    video_info = getVideoInfo(video_id)
    filename = args.filename or clean_for_filename(
        video_info["title"]) or clean_for_filename(video_id)

    process_and_save_transcript(video_id, video_info, args.language, args.punctuated,
                                args.output_dir, filename, args.verbose, args.punctuation_model)

    if args.auto_open:
        output_path = os.path.join(args.output_dir, f'{filename}.md')
        open_file(output_path)


if __name__ == "__main__":
    main()
