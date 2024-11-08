"""
This script downloads anime episodes from a given AnimeUnity URL.

It extracts the anime ID, formats the anime name, retrieves episode IDs and
URLs, and downloads episodes concurrently.

Usage:
    - Run the script with the URL of the anime page as a command-line argument.
    - It will create a directory structure in the 'Downloads' folder based on
      the anime name where each episode will be downloaded.
"""

import os
import sys
import time

import requests
from bs4 import BeautifulSoup
from rich.live import Live

from helpers.progress_utils import create_progress_bar, create_progress_table
from helpers.download_utils import (
    get_episode_filename, save_file_with_progress, run_in_parallel
)
from helpers.anime_utils import (
    extract_anime_name, get_episode_ids, generate_episode_urls
)

SCRIPT_NAME = os.path.basename(__file__)
DOWNLOAD_FOLDER = "Downloads"
TIMEOUT = 10

def get_embed_url(episode_url, tag, attribute):
    """
    Retrieves the embed URL from the given episode URL.

    Args:
        episode_url (str): The URL of the episode page.
        tag (str): The HTML tag to search for.
        attribute (str): The attribute of the tag containing the embed URL.

    Returns:
        str: The retrieved embed URL.

    Raises:
        requests.RequestException: If there is an issue with the HTTP request.
        AttributeError: If there is an issue accessing the attribute of the tag.
        KeyError: If the expected attribute is not found in the tag.
    """
    try:
        response = requests.get(episode_url, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        element = soup.find(tag)

        if element is None:
            raise AttributeError(f"Tag '{tag}' not found")

        embed_url = element.get(attribute)

        if embed_url is None:
            raise KeyError(f"Attribute '{attribute}' not found in tag '{tag}'")

        return embed_url

    except requests.RequestException as req_err:
        return print(f"HTTP request error: {req_err}")

    except AttributeError as attr_err:
        return AttributeError(f"Error accessing tag attributes: {attr_err}")

    except KeyError as key_err:
        return KeyError(f"Expected attribute not found: {key_err}")

def get_embed_urls(episodes_urls):
    """
    Constructs a list of embed URLs for a given list of episode URLs.

    Args:
        episodes_urls (list of str): A list of episode URLs.

    Returns:
        list of str: A list of embed URLs extracted from the episode URLs.
    """
    def extract_embed_url(episode_url):
        return get_embed_url(episode_url, 'video-player', 'embed_url')

    return list(map(extract_embed_url, episodes_urls))

def download_episode(download_link, download_path, task_info, retries=3):
    """
    Downloads an episode from the specified link and provides real-time
    progress updates.

    Args:
        download_link (str): The URL from which to download the episode.
        download_path (str): The directory path where the episode file will
                             be saved.
        task_info (tuple): A tuple containing progress tracking information:
            - job_progress: The progress bar object.
            - task: The specific task being tracked.
            - overall_task: The overall progress task being updated.
        retries (int, optional): The number of retry attempts in case of a
                                 download failure. Defaults to 3 retries.

    Raises:
        requests.RequestException: If there is an error with the HTTP request,
                                   such as connectivity issues or invalid URLs.
    """
    for attempt in range(retries):
        try:
            response = requests.get(download_link, stream=True, timeout=TIMEOUT)
            response.raise_for_status()

            filename = get_episode_filename(download_link)
            final_path = os.path.join(download_path, filename)
            save_file_with_progress(response, final_path, task_info)
            break

        except requests.RequestException as req_err:
            print(
                f"HTTP request failed: {req_err}\n"
                f"Retrying in a moment... ({attempt + 1}/{retries})"
            )
            time.sleep(20)

def process_embed_url(embed_url, download_path, task_info):
    """
    Processes an embed URL to extract episode download links and initiate their
    download.

    Args:
        embed_url (str): The embed URL to process.
        download_path (str): The path to save the downloaded episodes.
        task_info (tuple): A tuple containing progress tracking information.
    """
    def extract_download_link(text, match="window.downloadUrl = "):
        """
    Extracts a download link from a JavaScript text by searching for a specific
    match pattern.

    Args:
        text (str): The text to search for the download URL.
        match (str, optional): The pattern to search for in the text.
                               Defaults to `window.downloadUrl = `.

    Returns:
        str: The extracted download URL if the pattern is found;
             otherwise, `None`.

    Raises:
        IndexError: If the expected format of the text does not match the
                    pattern or the URL cannot be extracted.
    """
        if match in text:
            try:
                return text.split("'")[-2]

            except IndexError as indx_err:
                raise IndexError(
                    'Error extracting the download link'
                ) from indx_err

        return None

    response = requests.get(embed_url, timeout=TIMEOUT)
    soup = BeautifulSoup(response.text, 'html.parser')

    script_items = soup.find_all('script')
    texts = [item.text for item in script_items]

    for text in texts:
        download_link = extract_download_link(text)
        if download_link:
            download_episode(download_link, download_path, task_info)

def download_anime(anime_name, video_urls, download_path):
    """
    Concurrently downloads episodes of a specified anime from provided video
    URLs and tracks the download progress in real-time.

    Args:
        anime_name (str): The name of the anime being downloaded.
        video_urls (list): A list of URLs corresponding to each episode to be
                           downloaded.
        download_path (str): The local directory path where the downloaded
                             episodes will be saved.
    """
    job_progress = create_progress_bar()
    progress_table = create_progress_table(anime_name, job_progress)

    with Live(progress_table, refresh_per_second=10):
        run_in_parallel(
            process_embed_url, video_urls, job_progress, download_path
        )

def create_download_directory(anime_name):
    """
    Creates a directory for downloads if it doesn't exist.

    Args:
        anime_name (str): The name of the anime used to create the download 
                          directory.

    Returns:
        str: The path to the created download directory.

    Raises:
        OSError: If there is an error creating the directory.
    """
    download_path = os.path.join(DOWNLOAD_FOLDER, anime_name)

    try:
        os.makedirs(download_path, exist_ok=True)
        return download_path

    except OSError as os_err:
        print(f"Error creating directory: {os_err}")
        sys.exit(1)

def fetch_anime_page(url):
    """
    Fetches the anime page and returns its BeautifulSoup object.

    Args:
        url (str): The URL of the anime page.

    Returns:
        BeautifulSoup: The BeautifulSoup object containing the HTML.

    Raises:
        requests.RequestException: If there is an error with the HTTP request.
    """
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')

    except requests.RequestException as req_err:
        print(f"Error fetching the anime page: {req_err}")
        sys.exit(1)

def process_anime_download(url):
    """
    Processes the download of an anime from the specified URL.

    Args:
        url (str): The URL of the anime page to process.

    Raises:
        ValueError: If there is an issue with extracting data from 
                    the anime page.
    """
    soup = fetch_anime_page(url)

    try:
        anime_name = extract_anime_name(soup)
        download_path = create_download_directory(anime_name)

        episodes_ids = get_episode_ids(soup)
        episodes_urls = generate_episode_urls(url, episodes_ids)

        embed_urls = get_embed_urls(episodes_urls)
        download_anime(anime_name, embed_urls, download_path)

    except ValueError as val_err:
        print(f"Value error: {val_err}")

def clear_terminal():
    """
    Clears the terminal screen based on the operating system.
    """
    commands = {
        'nt': 'cls',      # Windows
        'posix': 'clear'  # macOS and Linux
    }

    command = commands.get(os.name)
    if command:
        os.system(command)

def main():
    """
    Main function to download anime episodes from a given AnimeUnity URL.

    Command-line Arguments:
        <anime_url> (str): The URL of the anime page to download episodes from.
    """
    if len(sys.argv) != 2:
        print(f"Usage: python3 {SCRIPT_NAME} <anime_url>")
        sys.exit(1)

    clear_terminal()
    url = sys.argv[1]
    process_anime_download(url)

if __name__ == '__main__':
    main()
