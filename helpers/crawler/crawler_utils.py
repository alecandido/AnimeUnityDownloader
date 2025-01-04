"""
This module provides functions to retrieve, extract, and process anime episode
video URLs from a web page.
"""

import re
import random
import asyncio
from urllib.parse import urlparse

import httpx

from helpers.config import prepare_headers

HEADERS = prepare_headers()

def validate_url(url):
    """
    Validates a URL by ensuring it does not have a trailing slash.

    Args:
        url (str): The URL to validate and normalize.

    Returns:
        str: The normalized URL without a trailing slash.
    """
    if url.endswith('/'):
        return url.rstrip('/')
    return url

def extract_host_domain(url):
    """
    Extracts the host/domain name from a given URL.

    Args:
        url (str): The URL from which the host/domain name will be extracted.

    Returns:
        str: The domain or host part of the URL.
    """
    parsed_url = urlparse(url)
    return parsed_url.netloc

def validate_episode_range(start_episode, end_episode, num_episodes):
    """
    Validates the episode range to ensure it is within acceptable bounds.

    Args:
        start_episode (int): The starting episode number.
        end_episode (int): The ending episode number.
        num_episodes (int): The total number of episodes available.

    Returns:
        tuple: A tuple containing the validated start and end episode numbers.
               If either start_episode or end_episode is `None`, it will be
               returned unchanged.

    Raises:
        ValueError: If the start episode is less than 1, greater than the total
                    number of episodes, or if the start episode is greater than
                    the end episode. Additionally, it raises an error if the
                    end episode exceeds the total number of episodes.
    """
    if start_episode:
        if start_episode < 1 or start_episode > num_episodes:
            raise ValueError(
                f"Start episode must be between 1 and {num_episodes}."
            )

    if start_episode and end_episode:
        if start_episode > end_episode:
            raise ValueError(
                "Start episode cannot be greater than end episode."
            )
        if end_episode > num_episodes:
            raise ValueError(
                f"End episode must be between 1 and {num_episodes}."
            )

    return start_episode, end_episode

async def fetch_with_retries(
    url, semaphore,
    headers=None, params=None,retries=4
):
    """
    Fetch data from a URL with retries on failure.

    Args:
        url (str): The URL to request.
        semaphore (asyncio.Semaphore): Semaphore to control concurrency.
        headers (dict, optional): Headers to send with the request.
        params (dict, optional): Parameters to send with the request.
        retries (int, optional): Number of retries in case of failure.

    Returns:
        dict or str: The response data, either JSON or text, depending on the
                     URL.
        None: If the request fails after retries.
    """
    async with semaphore:
        async with httpx.AsyncClient() as client:
            for attempt in range(retries):
                try:
                    response = await client.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=10
                    )
                    response.raise_for_status()
                    return response

                except httpx.HTTPStatusError:
                    if attempt < retries - 1:
                        delay = 2 ** attempt + random.uniform(0, 2)
                        await asyncio.sleep(delay)

                except httpx.RequestError as req_err:
                    print(f"Request failed for {url}: {req_err}")
                    return None

    return None

def extract_download_link(script_items, video_url):
    """
    Extracts the download URL from a list of script items.

    Args:
        script_items (list): A list of BeautifulSoup objects representing
                             `<script>` tags.
        video_url (str): The URL of the video page, used for logging purposes
                         if extraction fails.

    Returns:
        str: The extracted download URL if found.
        None: If the download URL is not found in any of the provided script
              items.
    """
    pattern = r"window\.downloadUrl\s*=\s*'(https?:\/\/[^\s']+)'"

    for item in script_items:
        match = re.search(pattern, item.text)
        if match:
            return match.group(1)

    # Return None if no download link is found
    print(f"Error extracting the download link for {video_url}")
    return None
