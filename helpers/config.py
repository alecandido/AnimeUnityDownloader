"""
Centralized configuration module for managing constants and settings used
across the project. These configurations aim to improve modularity and
readability by consolidating settings into a single location.
"""

from fake_useragent import UserAgent

DOWNLOAD_FOLDER = "Downloads"  # The folder where downloaded files will be
                               # stored
FILE = "URLs.txt"              # The name of the file containing URLs

TASK_COLOR = "cyan"            # The color to be used for task-related messages
CRAWLER_WORKERS = 8            # The maximum number of worker threads for
                               # crawling tasks
DOWNLOAD_WORKERS = 3           # The maximum number of worker threads for
                               # downloading tasks

# Creating a user-agent rotator
USER_AGENT_ROTATOR = UserAgent(use_external_data=True)

def prepare_headers():
    """
    Prepare a random HTTP headers with a user-agent string for making requests.

    Returns:
        dict: A dictionary containing the `User-Agent` header.
    """
#    user_agent = str(USER_AGENT_ROTATOR.chrome)
    user_agent = str(USER_AGENT_ROTATOR.firefox)
    return {"User-Agent": user_agent}
