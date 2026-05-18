# Discord Points Tracker Bot

A Discord bot that tracks points per channel. Users can add or subtract points with simple commands, and export transaction history to CSV.

## Features

- ➕ Add points with `+NUMBER` (e.g., `+50`)
- ➖ Subtract points with `-NUMBER` (e.g., `-100`)
- 📊 View current total with `!score` (per channel)
- 📁 Export all transactions to CSV with `!export`
- 👤 Track which user added/subtracted points
- 📅 Record timestamp and month/year for each transaction
- 🔄 Separate points total for each channel
- 💾 All data persists across bot restarts

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the bot name, click "Reset Token" and copy the token
5. Keep this token safe! Don't share it

### 2. Configure Bot Permissions

1. In Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`
3. Select permissions: `Send Messages`, `Read Messages/View Channels`
4. Copy the generated URL and open it to invite the bot to your server

### 3. Set Up Local Environment

1. Clone or download this project
2. Copy `.env.example` to `.env` and fill in your bot token:
   ```
   DISCORD_TOKEN=your_actual_bot_token_here
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 4. Run the Bot

```bash
python bot.py
```

You should see output like:
```
BotName#1234 is now running!
Current points: 0
```

## Usage

### Adding Points
Send a message with `+NUMBER` to add points. You can optionally include a description:
- Message: `+50`
  - Bot response: ➕ Added 50 points! Total: **50**
- Message: `+10 for cleaning`
  - Bot response: ➕ Added 10 points for cleaning! Total: **60**

### Subtracting Points
Send a message with `-NUMBER` to subtract points. You can optionally include a description:
- Message: `-20`
  - Bot response: ➖ Subtracted 20 points! Total: **40**
- Message: `-5 broke a rule`
  - Bot response: ➖ Subtracted 5 points broke a rule! Total: **35**

### Viewing Score
Use the `!score` command to see the current total for the current channel:
- Message: `!score`
- Bot response: 📊 Current points in **#channel-name**: **35**

**Note:** Each channel has its own separate points total. Running `!score` in different channels will show different totals.

### Viewing Channel Total
Use the `!total` command to see the overall points for the current channel:
- Message: `!total`
- Bot response: 💰 **#channel-name** channel total: **100** points

### Viewing Leaderboard
Use the `!leaderboard` command to see per-user points for the current month in this channel:
- Message: `!leaderboard`
- Bot response: Shows a ranked table of users and their points (current month only)
- Sorted: Highest to lowest
- Only includes: Transactions from the current month in the current channel

Example leaderboard:
```
Rank  User                 Points
1     alice                50
2     bob                  30
3     charlie              20
```
Use the `!export` command to download all transactions as a CSV file:
- Message: `!export`
- Bot response: Bot generates and uploads a CSV file with all transactions
- CSV columns: Channel, User, Amount, Month/Year

The exported CSV includes:
- Channel name (readable channel names, not IDs)
- Who made each change (username)
- The amount (positive or negative)
- Month and year when it was added

### Getting Help
Use the `!howtopoints` command to see all available commands and how to use them:
- Message: `!howtopoints`
- Bot response: Displays a quick reference guide with all commands and usage tips

## How It Works

- **Per-Channel Tracking**: Each channel maintains its own independent points total
- **User Tracking**: The bot records who added/subtracted points and when
- **Transaction History**: All point changes are logged with:
  - Channel ID
  - Username and User ID
  - Amount (positive or negative)
  - Description (if provided)
  - ISO timestamp and month/year
- **Data Storage**: All data is stored in `points.json` with a `channels` object and a `transactions` array
- **Commands**: Users can add/subtract points with `+50`, `-100`, `+10 for cleaning`, etc.
- **Invalid Formats**: Ignored (e.g., `+ 50`, `+abc`, just `50`)
- **CSV Export**: Run `!export` to download all transactions as a spreadsheet-ready CSV file

## Troubleshooting

**Bot doesn't respond to commands:**
- Make sure bot has permission to send messages in the channel
- Check that DISCORD_TOKEN is set correctly in `.env`
- Ensure the bot account is in your server

**"DISCORD_TOKEN not found" error:**
- Create a `.env` file in the `discord_bot` folder
- Add your token: `DISCORD_TOKEN=your_token_here`

**Points file not found:**
- Run the bot once to auto-create `points.json`
- Check file permissions in the `discord_bot` folder

## Files

- `bot.py` - Main bot code
- `requirements.txt` - Python dependencies
- `.env` - Your Discord bot token (keep private!)
- `points.json` - Persistent points storage
- `README.md` - This file

## Future Enhancements

Possible additions:
- Leaderboard command (top contributors)
- Admin-only modification controls
- Role-based access restrictions
- Point deduction history (detailed breakdown)
- Scheduled point resets per month/year

