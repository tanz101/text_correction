import discord
from discord.ext import commands
import json
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
POINTS_FILE = 'discord_bot/points.json'

# Create bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Helper functions for points management
def load_points():
    """Load points total from JSON file."""
    try:
        with open(POINTS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('total', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

def save_points(total):
    """Save points total to JSON file."""
    try:
        with open(POINTS_FILE, 'w') as f:
            json.dump({'total': total}, f)
    except Exception as e:
        print(f"Error saving points: {e}")

@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    print(f'{bot.user} is now running!')
    print(f'Current points: {load_points()}')

@bot.event
async def on_message(message):
    """Process messages for point commands."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    content = message.content.strip()
    
    # Pattern for +NUMBER or -NUMBER commands with optional description
    # Examples: "+10", "+10 for cleaning", "-50 lost points"
    match = re.match(r'^([+-])(\d+)(?:\s+(.+))?$', content)
    
    if match:
        operator = match.group(1)
        amount = int(match.group(2))
        description = match.group(3)  # Optional description
        
        current = load_points()
        
        if operator == '+':
            new_total = current + amount
            if description:
                await message.reply(f'➕ Added {amount} points {description}! Total: **{new_total}**')
            else:
                await message.reply(f'➕ Added {amount} points! Total: **{new_total}**')
        else:  # operator == '-'
            new_total = current - amount
            if description:
                await message.reply(f'➖ Subtracted {amount} points {description}! Total: **{new_total}**')
            else:
                await message.reply(f'➖ Subtracted {amount} points! Total: **{new_total}**')
        
        save_points(new_total)
    
    # Process bot commands (like !score)
    await bot.process_commands(message)

@bot.command(name='score')
async def score(ctx):
    """Display the current points total."""
    current = load_points()
    await ctx.send(f'📊 Current points: **{current}**')

# Run the bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: DISCORD_TOKEN not found in .env file!")
    print("Please set up your .env file with your bot token.")
