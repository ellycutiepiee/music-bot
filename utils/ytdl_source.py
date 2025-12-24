import discord
import yt_dlp
import asyncio
import requests
from bs4 import BeautifulSoup

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda *args, **kwargs: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    # Use cookies if available
    'cookiefile': 'cookies.txt', 
}

ffmpeg_options = {
    'options': '-vn',
    # Improved options for stability and buffering + FORCE START AT 00:00:00
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M -ss 00:00:00' 
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        
        # Check for Spotify
        if "open.spotify.com" in url:
            try:
                # Basic scraping to get title
                # We need a User-Agent, otherwise Spotify might block or return limited info
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        # Title usually looks like "Song Name - Song by Artist | Spotify"
                        page_title = title_tag.get_text()
                        # Clean up a bit to get a good search query
                        search_query = page_title.replace(" | Spotify", "")
                        # Force a youtube search
                        url = f"ytsearch:{search_query}"
            except Exception as e:
                print(f"Spotify extraction failed: {e}")
                # Fallback: let yt-dlp try or fail

        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
