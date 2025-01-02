"""
This module provides functions for extracting information from anime web pages
and constructing episode URLs for downloading. It utilizes BeautifulSoup for 
parsing HTML content and includes error handling for common extraction issues.
"""

import asyncio
from urllib.parse import urlparse

import httpx

from helpers.config import CRAWLER_WORKERS, prepare_headers
from .crawler_utils import fetch_with_retries

HEADERS = prepare_headers()

def extract_host_domain(url):
    """
    Extract the host/domain name from a given URL.

    Args:
        url (str): The URL from which the host/domain name will be extracted.

    Returns:
        str: The domain or host part of the URL.
    """
    parsed_url = urlparse(url)
    return parsed_url.netloc

def extract_anime_name(soup):
    """
    Extracts the anime name from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML of
                              the anime page.

    Returns:
        str: The name of the anime.

    Raises:
        ValueError: If the <h1> tag with class "title" is not found in the
                    HTML.
        AttributeError: If there is an issue accessing the text of the
                        <h1> tag.
    """
    try:
        title_container = soup.find('h1', {'class': "title"})
        if title_container is None:
            raise ValueError("Anime title tag not found.")

        return title_container.get_text().strip()

    except AttributeError as attr_err:
        return AttributeError(f"Error extracting anime name: {attr_err}")

def validate_episode_range(start, end, num_episodes):
    """
    Validates the episode range provided by the user.

    Args:
        start (int): The starting episode number.
        end (int): The ending episode number.
        num_episodes (int): The number of episodes available for download.

    Returns:
        tuple: A tuple containing the validated start and end episode numbers.

    Raises:
        ValueError: If the start episode is greater than the end episode, 
                    or if the episode range is outside the valid bounds.
    """
    if start:
        if start < 1 or start > num_episodes:
            raise ValueError(
                f"Start episode must be between 1 and {num_episodes}."
            )

    if start and end:
        if start > end:
            raise ValueError(
                "Start episode cannot be greater than end episode."
            )
        if end > num_episodes:
            raise ValueError(
                f"End episode must be between 1 and {num_episodes}."
            )

    return start, end

def get_num_episodes(url, timeout=10):
    """
    Retrieve total number of episodes for the selected media.
    
    Returns:
        int: Total episode count
    """
    api_url = url.replace("/anime/", "/info_api/")
    response = httpx.get(url=api_url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.json()["episodes_count"]

async def get_episode_info(url, episode_indx, semaphore):
    """
    Fetch the ID of the specified episode from an API.

    Args:
        url (str): The base URL of the anime page (e.g., "/anime/{anime_name}").
        episode_indx (int): The index of the episode to retrieve.
        semaphore (asyncio.Semaphore): Semaphore to control concurrent access.

    Returns:
        int or None: The ID of the last episode if available, or None if the 
                     request fails or no episode information is found.
    """
    api_url = url.replace("/anime/", "/info_api/")
    episode_api_url = f"{api_url}/{episode_indx}"

    params = {
        "start_range": episode_indx,
        "end_range": episode_indx + 1
    }

    response = await fetch_with_retries(
        episode_api_url, semaphore, headers=HEADERS, params=params
    )

    if response:
        episode_info = response.json().get("episodes", [])
        return episode_info[-1]["id"] if episode_info else None

    return None

async def get_episode_ids(url, start_episode=None, end_episode=None):
    """
    Retrieves a list of episode IDs from a given URL, optionally filtered by a
    specified episode range.

    Args:
        url (str): The URL of the page containing the episode information.
        start_episode (int, optional): The starting episode number. If None,
                                       starts from the first episode.
        end_episode (int, optional): The ending episode number. If None, goes
                                     up to the last episode.

    Returns:
        list: A list of episode IDs within the specified range, or the entire
              list of episode IDs if no range is provided.
    """
    num_episodes = get_num_episodes(url)
    start_episode, end_episode = validate_episode_range(
        start_episode, end_episode, num_episodes
    )

    start_index = start_episode - 1 if start_episode else 0
    end_index = end_episode if end_episode else num_episodes

    semaphore = asyncio.Semaphore(CRAWLER_WORKERS)
    tasks = []

    # Generate tasks for asynchronous fetching
    for episode_indx in range(start_index, end_index):
        tasks.append(get_episode_info(url, episode_indx, semaphore))

    # Run all tasks concurrently and collect results
    return await asyncio.gather(*tasks)

def generate_episode_embed_urls(host_domain, episode_ids):
    """
    Generate a list of embed URLs for a series of episodes based on the given
    host domain and episode IDs.

    Args:
        host_domain (str): The domain or host where the embed URLs will point
                           to.
        episode_ids (list of int): A list of episode IDs for which the embed
                                   URLs will be generated.

    Returns:
        list of str: A list of embed URLs for each episode.
    """
    # Generate embed URLs for each episode using the base URL and episode ID
    return [
        f"https://{host_domain}/embed-url/{episode_id}"
        for episode_id in episode_ids
    ]
