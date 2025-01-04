"""
This module provides functionality to crawl anime websites, retrieve episode
information, and collect video URLs for each episode. This module is used for
automating the process of scraping anime videos based on episode ranges.
"""

import re
import asyncio

import httpx

from helpers.config import (
    CRAWLER_WORKERS,
    prepare_headers
)

from .crawler_utils import (
    fetch_with_retries,
    extract_host_domain,
    validate_url,
    validate_episode_range
)

HEADERS = prepare_headers()

class Crawler:
    """
    A class responsible for crawling an anime website to extract episode IDs,
    generate embed URLs, and retrieve video URLs for a specified range of
    episodes.

    Attributes:
        host_domain (str): The domain of the anime website extracted from the
                           URL.
        api_url (str): The generated API URL for retrieving episode
                       information.
        num_episodes (int): The total number of episodes for the anime.
        start_episode (int): The starting episode number for the range to
                             crawl.
        end_episode (int): The ending episode number for the range to crawl.
        semaphore (asyncio.Semaphore): A semaphore used to limit concurrent
                                       HTTP requests.
    """

    def __init__(
        self, url, start_episode, end_episode,
        max_workers=CRAWLER_WORKERS
    ):
        self.host_domain = extract_host_domain(url)
        self.api_url = self._generate_api_url(url)
        self.num_episodes = self._get_num_episodes()
        self.start_episode = start_episode
        self.end_episode = end_episode
        self.semaphore = asyncio.Semaphore(max_workers)

    async def collect_video_urls(self):
        """
        Collects a list of video URLs by concurrently fetching each embed URL
        using a thread pool.
        """
        episode_ids = await self._collect_episode_ids()
        embed_urls = self._generate_episode_embed_urls(episode_ids)
        tasks = [self._get_video_url(embed_url) for embed_url in embed_urls]
        return await asyncio.gather(*tasks)

    # Static methods
    @staticmethod
    def extract_anime_name(soup):
        """Extracts the anime name from the provided BeautifulSoup object."""
        try:
            title_container = soup.find('h1', {'class': "title"})
            if title_container is None:
                raise ValueError("Anime title tag not found.")

            return title_container.get_text().strip()

        except AttributeError as attr_err:
            return AttributeError(f"Error extracting anime name: {attr_err}")

    # Private methods
    def _get_num_episodes(self, timeout=10):
        """Retrieve total number of episodes for the selected media."""
        response = httpx.get(
            url=self.api_url,
            headers=HEADERS,
            timeout=timeout
        )
        response.raise_for_status()
        response_json = response.json()
        return response_json["episodes_count"]

    def _generate_api_url(self, url):
        """Generate the API URL based on the provided base URL."""
        validated_url = validate_url(url)
        escaped_host_domain = re.escape(self.host_domain)
        match = re.match(
            rf"https://{escaped_host_domain}/anime/(\d+-[^/]+)",
            validated_url
        )

        if match:
            anime_id = match.group(1)
            return f"https://{self.host_domain}/info_api/{anime_id}"

        print("URL format is incorrect.")
        return None

    async def _get_episode_id(self, episode_indx):
        """Fetch the ID of the specified episode from an API."""
        episode_api_url = f"{self.api_url}/{episode_indx}"
        params = {
            "start_range": episode_indx,
            "end_range": episode_indx + 1
        }

        response = await fetch_with_retries(
            episode_api_url,
            self.semaphore,
            headers=HEADERS,
            params=params
        )
        if response:
            episode_info = response.json().get("episodes", [])
            return episode_info[-1]["id"] if episode_info else None

        return None

    async def _collect_episode_ids(self):
        """
        Retrieves a list of episode IDs from a given URL, optionally filtered
        by a specified episode range.
        """
        start_episode, end_episode = validate_episode_range(
            self.start_episode,
            self.end_episode,
            self.num_episodes
        )

        start_index = start_episode - 1 if start_episode else 0
        end_index = end_episode if end_episode else self.num_episodes

        tasks = [
            self._get_episode_id(episode_indx)
            for episode_indx in range(start_index, end_index)
        ]
        return await asyncio.gather(*tasks)

    def _generate_episode_embed_urls(self, episode_ids):
        """
        Generate a list of embed URLs for a series of episodes based on the
        given episode IDs.
        """
        return [
            f"https://{self.host_domain}/embed-url/{episode_id}"
            for episode_id in episode_ids
        ]

    async def _get_video_url(self, embed_url):
        """Fetch the video URL from an embed URL."""
        response = await fetch_with_retries(
            embed_url,
            self.semaphore,
            headers=HEADERS
        )
        if response:
            return response.text.strip()

        return None
