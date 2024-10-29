"""
This script downloads anime episodes from a given AnimeUnity URL.

It extracts the anime ID, formats the anime name, retrieves episode IDs and
URLs, and downloads episodes concurrently.

Dependencies:
    - requests: For making HTTP requests.
    - bs4 (BeautifulSoup): For parsing HTML content.

Usage:
    - Run the script with the URL of the anime page as a command-line argument.
    - It will create a directory structure in the 'Downloads' folder based on
      the anime name where each episode will be downloaded.
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
from rich.live import Live

from helpers.progress_utils import create_progress_bar, create_progress_table
from helpers.anime_utils import (
    extract_anime_name, get_episode_ids, generate_episode_urls
)

SCRIPT_NAME = os.path.basename(__file__)
DOWNLOAD_FOLDER = "Downloads"
WINDOW_STR = "window.downloadUrl = "

MAX_WORKERS = 3
CHUNK_SIZE = 8192
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

def get_episode_file_name(download_link):
    """
    Extract the file name from the provided episode download link.

    Args:
        download_link (str): The download link for the episode.

    Returns:
        str: The extracted file name, or None if the link is None or empty.
    """
    if download_link:
        try:
            return download_link.split('=')[-1]

        except IndexError as indx_err:
            print(f"Error while extracting the file name: {indx_err}")

    return None

def download_episode(download_link, download_path, task_info):
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

    Prints:
        Progress messages during the download process, updating the user on the
        completion percentage of the episode download.

    Raises:
        requests.RequestException: If there is an error with the HTTP request,
                                   such as connectivity issues or invalid URLs.
        OSError: If there is an error with file operations, such as writing to
                 disk or permission issues.
    """
    def save_file_with_progress(response, final_path, file_size, task_info):
        (job_progress, task, overall_task) = task_info
        total_downloaded = 0

        with open(final_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    file.write(chunk)
                    total_downloaded += len(chunk)
                    progress_percentage = (total_downloaded / file_size) * 100
                    job_progress.update(task, completed=progress_percentage)

        job_progress.update(task, completed=100, visible=False)
        job_progress.advance(overall_task)

    try:
        response = requests.get(download_link, stream=True, timeout=TIMEOUT)
        response.raise_for_status()

        file_name = get_episode_file_name(download_link)
        final_path = os.path.join(download_path, file_name)
        file_size = int(response.headers.get('content-length', -1))
        save_file_with_progress(response, final_path, file_size, task_info)

    except requests.RequestException as req_error:
        print(f"HTTP request failed: {req_error}")

    except OSError as os_error:
        print(f"File operation failed: {os_error}")

def process_embed_url(embed_url, download_path, task_info):
    """
    Processes an embed URL to find and download episode URLs.

    Args:
        embed_url (str): The embed URL to process.
        download_path (str): The path to save the downloaded episodes.
        task_info (tuple): A tuple containing progress tracking information.
    """
    def extract_download_link(text, match=WINDOW_STR):
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

        if not download_link:
            continue

        download_episode(download_link, download_path, task_info)

def download_anime(anime_name, video_urls, download_path):
    """
    Downloads anime episodes from provided video URLs.

    Args:
        anime_name (str): The name of the anime to download.
        video_urls (list): List of video URLs for the anime episodes.
        download_path (str): The directory path to save the downloaded episodes.

    Prints:
        Information about the anime being downloaded and completion message
        after all downloads are finished.
    """
    def manage_running_tasks(futures):
        while futures:
            for future in list(futures.keys()):
                if future.running():
                    task = futures.pop(future)
                    job_progress.update(task, visible=True)

    job_progress = create_progress_bar()
    progress_table = create_progress_table(anime_name, job_progress)
    num_episodes = len(video_urls)

    with Live(progress_table, refresh_per_second=10):
        futures = {}

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            overall_task = job_progress.add_task(
                "[cyan]Progress", total=num_episodes, visible=True
            )

            for (indx, episode_url) in enumerate(video_urls):
                task = job_progress.add_task(
                    f"[cyan]Episode {indx + 1}/{num_episodes}",
                    total=100, visible=False
                )
                future = executor.submit(
                    process_embed_url, episode_url, download_path,
                    (job_progress, task, overall_task)
                )
                futures[future] = task
                manage_running_tasks(futures)

def create_download_directory(download_path):
    """
    Creates a directory for downloads if it doesn't exist.

    Args:
        download_path (str): The path to create the download directory.

    Raises:
        OSError: If there is an error creating the directory.
    """
    try:
        os.makedirs(download_path, exist_ok=True)

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

        download_path = os.path.join(os.getcwd(), DOWNLOAD_FOLDER, anime_name)
        create_download_directory(download_path)

        episodes_ids = get_episode_ids(soup)
        episodes_urls = generate_episode_urls(url, episodes_ids)

        embed_urls = get_embed_urls(episodes_urls)

        download_anime(anime_name, embed_urls, download_path)

    except ValueError as val_err:
        print(f"Value error: {val_err}")

def main():
    """
    Main function to download anime episodes from a given AnimeUnity URL.

    Command-line Arguments:
        <anime_url> (str): The URL of the anime page to download episodes from.

    Prints:
        Usage information, progress messages, and error details.
    """
    if len(sys.argv) != 2:
        print(f"Usage: python3 {SCRIPT_NAME} <anime_url>")
        sys.exit(1)

    url = sys.argv[1]
    process_anime_download(url)

if __name__ == '__main__':
    main()
