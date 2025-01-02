"""
This module provides functionality to read URLs from a file, process
them for downloading Anime content, and write results back to the file.

Usage:
    To use this module, ensure that 'URLs.txt' is present in the same
    directory as this script. Execute the script to read URLs, download
    content, and clear the URL list upon completion.
"""

import asyncio

from helpers.file_utils import read_file, write_file
from helpers.general_utils import clear_terminal
from helpers.config import FILE

from anime_downloader import process_anime_download

async def process_urls(urls):
    """
    Validates and downloads items for a list of URLs.

    Args:
        urls (list): A list of URLs to process.
    """
    for url in urls:
        await process_anime_download(url)

async def main():
    """
    Main function to execute the script.

    Reads URLs from a file, processes them, and clears the file at the end.
    """
    clear_terminal()
    urls = read_file(FILE)
    await process_urls(urls)
    write_file(FILE)

if __name__ == '__main__':
    asyncio.run(main())
