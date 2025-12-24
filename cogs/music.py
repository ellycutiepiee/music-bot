import discord
from discord.ext import commands
from discord.ui import Button, View
from utils.ytdl_source import YTDLSource
import asyncio

# --- 🎨 CUSTOM EMOJI CONFIGURATION ---
# We use the specific unicode symbols requested by the user.
# "↻ ♡ ⏹ ⏭ ⏸ ▶ "
# We will use them as LABELS to ensure they render as text (white/monochrome) and have consistent sizing.

EMOJI_PLAY = "▶" 
EMOJI_PAUSE = "⏸" 
EMOJI_SKIP = "⏭"
EMOJI_STOP = "⏹"
EMOJI_LOOP = "↻" 
EMOJI_LIKE = "♡"
EMOJI_LIKED = "💚" 

class MusicControlView(View):
    def __init__(self, ctx, music_cog):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.music_cog = music_cog
        self.update_buttons()

    def update_buttons(self):
        # Update Loop button color/state
        loop_btn = [x for x in self.children if x.custom_id == 'loop'][0]
        guild_id = self.ctx.guild.id
        if self.music_cog.loops.get(guild_id, False):
            loop_btn.style = discord.ButtonStyle.success # Green for enabled
        else:
            loop_btn.style = discord.ButtonStyle.secondary # Grey for disabled

        # Update Play/Pause button based on voice state? 
        pass

    @discord.ui.button(label=EMOJI_PAUSE, style=discord.ButtonStyle.success, custom_id='pause_resume') # Green Play/Pause button (Spotify style)
    async def pause_resume(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.voice or not interaction.guild.voice_client:
             return await interaction.response.send_message("You need to be in a voice channel!", ephemeral=True)
        
        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.pause()
            # Update button to Play icon
            button.label = EMOJI_PLAY
            await interaction.response.edit_message(view=self)
        elif vc.is_paused():
            vc.resume()
            button.label = EMOJI_PAUSE
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Nothing is playing!", ephemeral=True)

    @discord.ui.button(label=EMOJI_SKIP, style=discord.ButtonStyle.secondary, custom_id='skip')
    async def skip(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.voice or not interaction.guild.voice_client:
             return await interaction.response.send_message("You need to be in a voice channel!", ephemeral=True)
        
        vc = interaction.guild.voice_client
        if vc.is_playing() or vc.is_paused():
            vc.stop() # This triggers the after_playing callback which plays the next song
            await interaction.response.send_message(f"Skipped {EMOJI_SKIP}", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing!", ephemeral=True)

    @discord.ui.button(label=EMOJI_STOP, style=discord.ButtonStyle.secondary, custom_id='stop')
    async def stop(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.voice or not interaction.guild.voice_client:
             return await interaction.response.send_message("You need to be in a voice channel!", ephemeral=True)
        
        # Clear queue and stop
        self.music_cog.queues[interaction.guild.id] = []
        interaction.guild.voice_client.stop()
        await interaction.response.send_message(f"Stopped {EMOJI_STOP}", ephemeral=True)

    @discord.ui.button(label=EMOJI_LOOP, style=discord.ButtonStyle.secondary, custom_id='loop')
    async def loop(self, interaction: discord.Interaction, button: Button):
        guild_id = interaction.guild.id
        if guild_id not in self.music_cog.loops:
            self.music_cog.loops[guild_id] = False
        
        # Toggle
        self.music_cog.loops[guild_id] = not self.music_cog.loops[guild_id]
        
        # Update button style
        if self.music_cog.loops[guild_id]:
            button.style = discord.ButtonStyle.success
        else:
            button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label=EMOJI_LIKE, style=discord.ButtonStyle.secondary, custom_id='like') # Use label for Heart to get white outline
    async def like(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"{EMOJI_LIKED} **Added to your Liked Songs**", ephemeral=True)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {} # guild_id -> list of YTDLSource objects
        self.loops = {} # guild_id -> bool

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def play_next(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        if len(queue) > 0:
            player = queue.pop(0)
            
            # Modern Dark Theme Embed
            # Color: Dark Violet (0x8A2BE2)
            embed = discord.Embed(
                title="Now Playing",
                description=f"[{player.title}]({player.data.get('webpage_url', '')})\n{player.data.get('uploader', 'Unknown Artist')}", 
                color=0x8A2BE2 
            )
            
            # Thumbnail: show song/video artwork (Right side small image)
            if 'thumbnail' in player.data:
                embed.set_thumbnail(url=player.data['thumbnail'])
            
            # Fields: Duration, Volume
            if 'duration' in player.data:
                duration = int(player.data['duration']) # Ensure duration is an integer
                minutes = duration // 60
                seconds = duration % 60
                embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)
            
            # Volume (Default 50% from YTDLSource init)
            current_vol = int(player.volume * 100) if hasattr(player, 'volume') else 100
            embed.add_field(name="Volume", value=f"{current_vol}%", inline=True)
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

            # Create the view with buttons
            view = MusicControlView(ctx, self)
            
            await ctx.send(embed=embed, view=view)
            
            ctx.voice_client.play(player, after=lambda e: self.bot.loop.create_task(self.after_playing(ctx, e)))
        else:
            # Queue finished
            pass

    async def after_playing(self, ctx, error):
        if error:
            print(f"Player error: {error}")
        await self.play_next(ctx)

    @commands.command(name="join", help="Joins your voice channel")
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("You are not connected to a voice channel.")
        
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect(self_deaf=True)
        
        await ctx.send(f"Joined {channel.name}")

    @commands.command(name="leave", help="Disconnects from the voice channel")
    async def leave(self, ctx):
        if ctx.voice_client:
            self.queues[ctx.guild.id] = [] # Clear queue
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected.")
        else:
            await ctx.send("I am not in a voice channel.")

    @commands.command(name="play", help="Plays a song from a link or search query")
    async def play(self, ctx, *, query):
        if not ctx.author.voice:
            return await ctx.send("You are not connected to a voice channel.")

        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect(self_deaf=True)
        
        if ctx.voice_client.channel != ctx.author.voice.channel:
             return await ctx.send("You must be in the same voice channel as me to play music.")

        await ctx.send("🔍 Searching...", delete_after=5)
        
        async with ctx.typing():
            try:
                player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
                
                queue = self.get_queue(ctx.guild.id)
                queue.append(player)
                
                if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                    await self.play_next(ctx)
                else:
                    # Added to queue message - Match theme
                    embed = discord.Embed(title="Added to Queue", description=f"**{player.title}**", color=0x8A2BE2)
                    if 'thumbnail' in player.data:
                        embed.set_thumbnail(url=player.data['thumbnail'])
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                await ctx.send(f'An error occurred: {str(e)}')

    @commands.command(name="pause", help="Pauses the current track")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused playback.")
        else:
            await ctx.send("Nothing is playing right now.")

    @commands.command(name="resume", help="Resumes playback")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed playback.")
        else:
            await ctx.send("Nothing is paused right now.")

    @commands.command(name="stop", help="Stops playback and clears the current audio")
    async def stop(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            self.queues[ctx.guild.id] = []
            ctx.voice_client.stop()
            await ctx.send("Stopped playback.")
        else:
            await ctx.send("Nothing is playing right now.")
            
    @commands.command(name="skip", help="Skips the current song")
    async def skip(self, ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            await ctx.send("Skipped.")
        else:
            await ctx.send("Nothing is playing right now.")

    @commands.command(name="help", help="Shows this help message")
    async def help(self, ctx):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are the available commands:",
            color=0x8A2BE2 # Dark Violet
        )
        
        embed.add_field(name="!play <query/url>", value="Plays a song from YouTube, Spotify, or SoundCloud.", inline=False)
        embed.add_field(name="!pause", value="Pauses the current song.", inline=True)
        embed.add_field(name="!resume", value="Resumes the paused song.", inline=True)
        embed.add_field(name="!skip", value="Skips the current song.", inline=True)
        embed.add_field(name="!stop", value="Stops playback and clears the queue.", inline=True)
        embed.add_field(name="!join", value="Joins your voice channel.", inline=True)
        embed.add_field(name="!leave", value="Leaves the voice channel.", inline=True)
        embed.add_field(name="!help", value="Shows this message.", inline=True)
        
        embed.set_footer(text="Created with Trae • Music Bot")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))
