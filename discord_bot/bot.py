import discord
from discord.ext import commands
import json
import os
import re
import csv
from datetime import datetime
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
def load_data():
    """Load points data from JSON file. Returns channels dict and transactions list."""
    try:
        with open(POINTS_FILE, 'r') as f:
            data = json.load(f)
            # Check if it's old format (has 'total' key) and migrate
            if 'total' in data and 'channels' not in data:
                data = migrate_old_format(data)
            return data.get('channels', {}), data.get('transactions', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, []

def migrate_old_format(old_data):
    """Migrate old format with single 'total' to new format with channels and transactions."""
    new_data = {
        'channels': {},
        'transactions': []
    }
    # Preserve the old total in a default channel (ID 0)
    if 'total' in old_data:
        new_data['channels']['0'] = old_data['total']
    return new_data

def save_data(channels, transactions):
    """Save points data to JSON file."""
    try:
        data = {
            'channels': channels,
            'transactions': transactions
        }
        with open(POINTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving points: {e}")

def get_channel_total(channel_id):
    """Get points total for a specific channel."""
    channels, _ = load_data()
    return channels.get(str(channel_id), 0)

def update_channel_total(channel_id, new_total):
    """Update points total for a specific channel."""
    channels, transactions = load_data()
    channels[str(channel_id)] = new_total
    save_data(channels, transactions)

def add_transaction(channel_id, user_id, username, amount, description):
    """Add a transaction record."""
    channels, transactions = load_data()
    timestamp = datetime.now().isoformat()
    month_year = datetime.now().strftime("%B %Y")
    
    transaction = {
        'channel_id': str(channel_id),
        'user_id': str(user_id),
        'username': username,
        'amount': amount,
        'description': description or '',
        'timestamp': timestamp,
        'month_year': month_year
    }
    transactions.append(transaction)
    save_data(channels, transactions)

def export_to_csv():
    """Export all transactions to a CSV file. Returns filename."""
    channels, transactions = load_data()
    
    filename = f'points_export_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
    filepath = os.path.join('discord_bot', filename)
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Channel', 'User', 'Amount', 'Month/Year']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for trans in transactions:
                # Get channel name from ID
                channel_id = int(trans['channel_id'])
                channel = bot.get_channel(channel_id)
                channel_name = channel.name if channel else f"Unknown ({trans['channel_id']})"
                
                writer.writerow({
                    'Channel': channel_name,
                    'User': trans['username'],
                    'Amount': trans['amount'],
                    'Month/Year': trans['month_year']
                })
        
        return filepath
    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return None

@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    print(f'{bot.user} is now running!')
    channels, transactions = load_data()
    print(f'Tracking {len(channels)} channel(s) with {len(transactions)} transaction(s)')

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
        
        channel_id = message.channel.id
        user_id = message.author.id
        username = message.author.name
        
        current = get_channel_total(channel_id)
        
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
        
        # Update channel total and record transaction
        update_channel_total(channel_id, new_total)
        add_transaction(channel_id, user_id, username, amount if operator == '+' else -amount, description or '')
    
    # Process bot commands (like !score)
    await bot.process_commands(message)

@bot.command(name='score')
async def score(ctx):
    """Display the current points total for this channel."""
    channel_id = ctx.channel.id
    current = get_channel_total(channel_id)
    await ctx.send(f'📊 Current points in **{ctx.channel.name}**: **{current}**')

@bot.command(name='export')
async def export_command(ctx):
    """Export all point transactions to a CSV file."""
    await ctx.send("📁 Generating export... please wait...")
    
    filepath = export_to_csv()
    
    if filepath and os.path.exists(filepath):
        channels, transactions = load_data()
        try:
            with open(filepath, 'rb') as f:
                file = discord.File(f, filename=os.path.basename(filepath))
                await ctx.send(
                    f"✅ Export complete! ({len(transactions)} transactions)",
                    file=file
                )
        except Exception as e:
            await ctx.send(f"❌ Error uploading file: {e}")
        finally:
            # Clean up the file after upload
            try:
                os.remove(filepath)
            except:
                pass
    else:
        await ctx.send("❌ Error generating export file.")

@bot.command(name='total')
async def total_command(ctx):
    """Display the total points for this channel."""
    channel_id = ctx.channel.id
    total = get_channel_total(channel_id)
    await ctx.send(f'💰 **{ctx.channel.name}** channel total: **{total}** points')

@bot.command(name='leaderboard')
async def leaderboard_command(ctx):
    """Display user leaderboard for current month in this channel."""
    channel_id = ctx.channel.id
    channels, transactions = load_data()
    current_month_year = datetime.now().strftime("%B %Y")
    
    # Filter transactions for this channel and current month
    user_totals = {}
    for trans in transactions:
        if trans['channel_id'] == str(channel_id) and trans['month_year'] == current_month_year:
            username = trans['username']
            amount = trans['amount']
            user_totals[username] = user_totals.get(username, 0) + amount
    
    if not user_totals:
        await ctx.send(f"📊 No transactions in **{ctx.channel.name}** for **{current_month_year}**")
        return
    
    # Sort by amount descending
    sorted_users = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)
    
    # Build leaderboard message
    leaderboard_text = f"📊 **Leaderboard for {ctx.channel.name}** - {current_month_year}\n"
    leaderboard_text += "```\n"
    leaderboard_text += f"{'Rank':<6} {'User':<20} {'Points':<10}\n"
    leaderboard_text += "-" * 36 + "\n"
    
    for rank, (username, total) in enumerate(sorted_users, 1):
        leaderboard_text += f"{rank:<6} {username:<20} {total:<10}\n"
    
    leaderboard_text += "```"
    
    await ctx.send(leaderboard_text)

@bot.command(name='howtopoints')
async def howtopoints_command(ctx):
    """Display help information and available commands."""
    help_text = """
**📖 Points Tracker Bot - How to Use**

**Point Commands** (No prefix needed, just type in the channel):
  `+NUMBER` - Add points
  `-NUMBER` - Subtract points

**Info Commands** (Use these with `!`):
  `!score` - Show current channel points
  `!total` - Show total points in channel (all-time)
  `!leaderboard` - Show top users this month in this channel
  `!export` - Download all transactions as CSV file
  `!howtopoints` - Show this help message

**Tips:**
  • Each channel has its own separate points total
  • Leaderboard only shows current month's transactions
  • CSV export includes all channels and all-time data
  • Point Commands will also work with typing descriptions after the points
"""
    await ctx.send(help_text)
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: DISCORD_TOKEN not found in .env file!")
    print("Please set up your .env file with your bot token.")
