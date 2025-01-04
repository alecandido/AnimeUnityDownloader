"""
This module provides functions to retrieve, extract, and process anime episode
video URLs from a web page.
"""

import random
import asyncio

import httpx

from helpers.config import CRAWLER_WORKERS, prepare_headers

HEADERS = prepare_headers()

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
        timeout (int, optional): Timeout for the request.
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

async def get_video_url(embed_url, semaphore):
    """
    Fetch the video URL from an embed URL.

    Args:
        embed_url (str): The URL to retrieve the video from.
        semaphore (asyncio.Semaphore): Semaphore to control concurrent access.

    Returns:
        str or None: The video URL as a string if the request is successful, 
                     or None if the request fails or no URL is found.
    """
    response = await fetch_with_retries(embed_url, semaphore, headers=HEADERS)
    if response:
        return response.text.strip()

    return None

async def collect_video_urls(embed_urls):
    """
    Collects a list of video URLs by concurrently fetching each embed URL using
    a thread pool.

    Args:
        embed_urls (list): A list of embed URLs to fetch video URLs from.

    Returns:
        list: A list of video URLs obtained from the provided embed URLs.
    """
    semaphore = asyncio.Semaphore(CRAWLER_WORKERS)
    tasks = []

    # Generate tasks for asynchronous fetching
    for embed_url in embed_urls:
        tasks.append(get_video_url(embed_url, semaphore))

    # Run all tasks concurrently and collect results
    return await asyncio.gather(*tasks)

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
