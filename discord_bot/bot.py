import discord
from discord.ext import commands
import json
import os
import re
import csv
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('C:\\Users\\Administrator\\Desktop\\.env')
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

def get_user_period_totals(channel_id, user_id):
    """Get a user's total points for current month and year in a channel."""
    channels, transactions = load_data()
    current_month_year = datetime.now().strftime("%B %Y")
    current_year = datetime.now().strftime("%Y")
    
    month_total = 0
    year_total = 0
    
    for trans in transactions:
        if trans['channel_id'] == str(channel_id) and str(trans['user_id']) == str(user_id):
            if trans['month_year'] == current_month_year:
                month_total += trans['amount']
            if trans['month_year'].endswith(current_year):
                year_total += trans['amount']
    
    return month_total, year_total

def update_channel_total(channel_id, new_total):
    """Update points total for a specific channel."""
    channels, transactions = load_data()
    channels[str(channel_id)] = new_total
    save_data(channels, transactions)

def add_transaction(channel_id, user_id, username, amount, description, timestamp=None, month_year=None):
    """Add a transaction record. If timestamp is provided, use it; otherwise use current time."""
    channels, transactions = load_data()
    
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    if month_year is None:
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
        
        # Calculate new total
        if operator == '+':
            new_total = current + amount
        else:  # operator == '-'
            new_total = current - amount
        
        # Update channel total and record transaction first
        update_channel_total(channel_id, new_total)
        add_transaction(channel_id, user_id, username, amount if operator == '+' else -amount, description or '')
        
        # Get user's period totals (this will include the transaction we just added)
        month_total, year_total = get_user_period_totals(channel_id, user_id)
        
        # Build response message
        if operator == '+':
            base_msg = f'➕ Added {amount} points'
        else:
            base_msg = f'➖ Subtracted {amount} points'
        
        if description:
            base_msg += f' {description}'
        
        base_msg += f'! Total: **{new_total}**\n'
        base_msg += f'Your month: **{month_total}** | Your year: **{year_total}**'
        
        # Send as reply but only visible to the user (delete after 10 seconds)
        try:
            response = await message.reply(base_msg)
            # Schedule message deletion after 10 seconds
            await response.delete(delay=10)
        except discord.Forbidden:
            # If reply fails, try sending as DM
            try:
                await message.author.send(base_msg)
            except:
                pass  # Silently fail if both options don't work
    
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
    """Display user leaderboard for current month and year in this channel."""
    channel_id = ctx.channel.id
    channels, transactions = load_data()
    current_month_year = datetime.now().strftime("%B %Y")
    current_year = datetime.now().strftime("%Y")
    
    # Filter transactions for this channel and current month
    month_user_totals = {}
    year_user_totals = {}
    
    for trans in transactions:
        if trans['channel_id'] == str(channel_id):
            username = trans['username']
            amount = trans['amount']
            
            # Check if transaction is from current month
            if trans['month_year'] == current_month_year:
                month_user_totals[username] = month_user_totals.get(username, 0) + amount
            
            # Check if transaction is from current year
            if trans['month_year'].endswith(current_year):
                year_user_totals[username] = year_user_totals.get(username, 0) + amount
    
    # Build month leaderboard
    month_text = f"📊 **{ctx.channel.name} Leaderboard** - {current_month_year}\n"
    month_text += "```\n"
    month_text += f"{'Rank':<6} {'User':<20} {'Points':<10}\n"
    month_text += "-" * 36 + "\n"
    
    if month_user_totals:
        sorted_month = sorted(month_user_totals.items(), key=lambda x: x[1], reverse=True)
        for rank, (username, total) in enumerate(sorted_month, 1):
            month_text += f"{rank:<6} {username:<20} {total:<10}\n"
    else:
        month_text += "No transactions this month\n"
    
    month_text += "```"
    
    # Build year leaderboard
    year_text = f"📊 **{ctx.channel.name} Leaderboard** - {current_year}\n"
    year_text += "```\n"
    year_text += f"{'Rank':<6} {'User':<20} {'Points':<10}\n"
    year_text += "-" * 36 + "\n"
    
    if year_user_totals:
        sorted_year = sorted(year_user_totals.items(), key=lambda x: x[1], reverse=True)
        for rank, (username, total) in enumerate(sorted_year, 1):
            year_text += f"{rank:<6} {username:<20} {total:<10}\n"
    else:
        year_text += "No transactions this year\n"
    
    year_text += "```"
    
    # Send both leaderboards
    await ctx.send(month_text)
    await ctx.send(year_text)

@bot.command(name='readhistory')
async def readhistory_command(ctx):
    """Read channel history and add matching point commands to score (one-time backfill)."""
    await ctx.send("📖 Reading channel history... this may take a moment...")
    
    channel_id = ctx.channel.id
    channel_id_str = str(channel_id)
    
    # Clear current point records for this channel
    channels, transactions = load_data()
    
    # Reset channel total to 0
    if channel_id_str in channels:
        del channels[channel_id_str]
    
    # Remove all transactions for this channel
    transactions = [t for t in transactions if t['channel_id'] != channel_id_str]
    save_data(channels, transactions)
    
    added_count = 0
    total_change = 0
    
    try:
        async for message in ctx.channel.history(limit=None, oldest_first=True):
            # Skip bot messages
            if message.author == bot.user:
                continue
            
            content = message.content.strip()
            
            # Pattern for +NUMBER or -NUMBER commands with optional description
            match = re.match(r'^([+-])(\d+)(?:\s+(.+))?$', content)
            
            if match:
                operator = match.group(1)
                amount = int(match.group(2))
                description = match.group(3) or ''
                
                # Get the message's timestamp and calculate month/year from it
                msg_timestamp = message.created_at.isoformat()
                msg_month_year = message.created_at.strftime("%B %Y")
                
                # Add transaction with the message's original timestamp
                add_transaction(channel_id, message.author.id, message.author.name, 
                              amount if operator == '+' else -amount, description,
                              timestamp=msg_timestamp, month_year=msg_month_year)
                added_count += 1
                total_change += amount if operator == '+' else -amount
        
        # Update channel total with the calculated total from history
        update_channel_total(channel_id, total_change)
        
        await ctx.send(f"✅ History read complete! Cleared old records and added {added_count} transaction(s) for a total of {total_change:+d} points.")
    
    except Exception as e:
        await ctx.send(f"❌ Error reading history: {e}")

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
