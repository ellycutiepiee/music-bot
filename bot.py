import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Add FFmpeg to PATH temporarily for this session
ffmpeg_path = r"C:\Users\ellyc\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
if os.path.exists(ffmpeg_path):
    os.environ["PATH"] += os.pathsep + ffmpeg_path

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class MusicBot(commands.Bot):
    def __init__(self):
        # We need voice states intent for the bot to know about voice channels
        intents = discord.Intents.default()
        intents.message_content = True
        # Disable default help command to use our custom one
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=intents, help_command=None)

    async def setup_hook(self):
        # Load the music cog
        await self.load_extension('cogs.music')
        # Syncing commands globally
        # We clear the tree first to ensure no slash commands are registered
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        print("Slash commands cleared/disabled. Only prefix commands are available.")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

bot = MusicBot()

if __name__ == '__main__':
    if not TOKEN or TOKEN == "your_token_here":
        print("Error: DISCORD_TOKEN not found in .env file or it is set to default.")
        print("Please set your bot token in the .env file.")
    else:
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("Failed to login: Invalid token.")
