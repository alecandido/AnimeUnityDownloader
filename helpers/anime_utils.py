"""
This module provides functions for extracting information from anime web pages
and constructing episode URLs for downloading. It utilizes BeautifulSoup for 
parsing HTML content and includes error handling for common extraction issues.
"""

import json

def extract_anime_name(soup):
    """
    Extracts the anime name from the provided BeautifulSoup object.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object containing the HTML of
                              the anime page.

    Returns:
        str: The name of the anime.

    Raises:
        ValueError: If the <h1> tag with class "title" is not found in the HTML.
        AttributeError: If there is an issue accessing the text of the <h1> tag.
    """
    try:
        title_tag = soup.find('h1', {'class': "title"})

        if title_tag is None:
            raise ValueError("Anime title tag not found.")

        return title_tag.get_text().strip()

    except AttributeError as attr_err:
        return AttributeError(f"Error extracting anime name: {attr_err}")

def get_episode_ids(soup):
    """
    Extracts episode IDs from HTML soup.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object containing HTML.

    Returns:
        list: A list of extracted episode IDs.

    Raises:
        AttributeError: If there is an issue accessing the attribute of the
                        tags.
        KeyError: If the expected attribute is not found in the tag.
        IndexError: If the expected structure of the string is not found.
    """
    try:
        episodes_data = soup.find('video-player')['episodes']
        episodes = json.loads(episodes_data)
        return [episode['id'] for episode in episodes]

#        episodes_list = [
#            link['episodes'] for link in soup.find_all('video-player')
#        ]
#        all_episodes = ''.join(episodes_list)
#        id_parts = all_episodes.split('"id":')[1:]
#        return list(map(lambda item: item.split(',')[0], id_parts))

    except AttributeError as attr_err:
        return AttributeError(f"Error accessing tag attributes: {attr_err}")

    except KeyError as key_err:
        return KeyError(f"Expected attribute not found: {key_err}")

    except IndexError as indx_err:
        return IndexError(f"Error processing string structure: {indx_err}")

def generate_episode_urls(url, episodes_ids):
    """
    Constructs a list of episode URLs given a base URL and a list of episode
    IDs.

    Args:
        url (str): The base URL for the episodes.
        episodes_ids (list of str): A list of episode IDs.

    Returns:
        list of str: A list of complete episode URLs.
    """
    return [f"{url}/{episode_id}" for episode_id in episodes_ids]
