# AnimeUnity Downloader

> A Python-based tool to download anime series from AnimeUnity, tracking progress for each episode. It extracts video URLs and handles downloads efficiently.

![Screenshot](https://github.com/Lysagxra/AnimeUnityDownloader/blob/660079e23bc16e8b1996b463e213aecbb1a56294/misc/Screenshot.png)

## Features

- Downloads multiple episodes concurrently.
- Supports batch downloading via a list of URLs.
- Tracks download progress with a progress bar.
- Automatically creates a directory structure for organized storage.

## Directory Structure

```
project-root/
├── helpers/
│ ├── anime_utils.py      # Python script containing formatting utility for AnimeUnity
│ └── progress_utils.py   # Python script containing progress utility
├── anime_downloader.py   # Module to download the anime episodes
├── main.py               # Main Python script to run the downloader
└── URLs.txt              # Text file containing album URLs
```

## Dependencies

- Python 3
- `requests` - for HTTP requests
- `BeautifulSoup` (bs4) - for HTML parsing
- `rich` - for progress display in terminal

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Lysagxra/AnimeUnityDownloader.git

2. Navigate to the project directory:
   ```bash
   cd AnimeUnityDownloader

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

## Single Anime Download

To download a single anime, you can use the `anime_downloader.py` script.

### Usage

Run the script followed by the anime URL you want download:

```bash
python3 anime_downloader.py <anime_page_url>
```

Example

```bash
python3 anime_downloader.py https://www.animeunity.to/anime/1517-yuru-yuri
```

## Batch Download

### Usage

1. Create a `URLs.txt` file in the project root and list the anime URLs you want to download.

2. Run the main script via the command line:

```bash
python3 main.py
```

The downloaded files will be saved in the `Downloads` directory.
