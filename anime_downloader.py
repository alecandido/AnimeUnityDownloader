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
import time
import argparse
import asyncio
import random

import requests
from rich.live import Live

from helpers.crawler.crawler import Crawler
from helpers.crawler.crawler_utils import extract_download_link

from helpers.config import prepare_headers
from helpers.progress_utils import (
    create_progress_bar,
    create_progress_table
)
from helpers.general_utils import (
    fetch_page,
    create_download_directory,
    clear_terminal
)
from helpers.download_utils import (
    get_episode_filename,
    save_file_with_progress,
    run_in_parallel
)

HEADERS = prepare_headers()

def download_episode(download_link, download_path, task_info, retries=4):
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
            response = requests.get(
                download_link,
                stream=True,
                headers=HEADERS,
                timeout=10
            )
            response.raise_for_status()

            filename = get_episode_filename(download_link)
            final_path = os.path.join(download_path, filename)
            save_file_with_progress(response, final_path, task_info)
            break

        except requests.RequestException:
            if attempt < retries - 1:
#                print(
#                    f"HTTP request failed: {req_err}. "
#                    f"Retrying in a moment... ({attempt + 1}/{retries})"
#                )
                delay = 10 * (attempt + 1) + random.uniform(0, 2)
                time.sleep(delay)

def process_video_url(video_url, download_path, task_info):
    """
    Processes an embed URL to extract episode download links and initiate their
    download.

    Args:
        video_url (str): The embed URL to process.
        download_path (str): The path to save the downloaded episodes.
        task_info (tuple): A tuple containing progress tracking information.
    """
    soup = fetch_page(video_url)
    script_items = soup.find_all('script')
    download_link = extract_download_link(script_items, video_url)
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
            process_video_url,
            video_urls, job_progress, download_path
        )

async def process_anime_download(url, start_episode=None, end_episode=None):
    """
    Processes the download of an anime from the specified URL.

    Args:
        url (str): The URL of the anime page to process.
        start_episode (int, optional): The starting episode number. Defaults to
                                       None.
        end_episode (int, optional): The ending episode number. Defaults to
                                     None.

    Raises:
        ValueError: If there is an issue with extracting data from 
                    the anime page.
    """
    soup = fetch_page(url)
    crawler = Crawler(
        url=url,
        start_episode=start_episode,
        end_episode=end_episode
    )
    video_urls = await crawler.collect_video_urls()

    try:
        anime_name = crawler.extract_anime_name(soup)
        download_path = create_download_directory(anime_name)
        download_anime(anime_name, video_urls, download_path)

    except ValueError as val_err:
        print(f"Value error: {val_err}")

def setup_parser():
    """
    Set up the argument parser for the anime download script.

    Returns:
        argparse.ArgumentParser: The configured argument parser instance.
    """
    parser = argparse.ArgumentParser(
        description="Download anime episodes from a given URL."
    )
    parser.add_argument('url', help="The URL of the Anime series to download.")
    parser.add_argument(
        '--start', type=int, default=None, help="The starting episode number."
    )
    parser.add_argument(
        '--end', type=int, default=None, help="The ending episode number."
    )
    return parser

async def main():
    """
    Main function to download anime episodes from a given AnimeUnity URL.

    Command-line Arguments:
        <anime_url> (str): The URL of the anime page to download episodes from.
    """
    clear_terminal()
    parser = setup_parser()
    args = parser.parse_args()
    await process_anime_download(
        args.url,
        start_episode=args.start,
        end_episode=args.end
    )

if __name__ == '__main__':
    asyncio.run(main())
