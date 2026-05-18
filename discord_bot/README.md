# Discord Points Tracker Bot

A simple Discord bot that tracks a shared points total in a channel. Users can add or subtract points with simple commands, and view the current total.

## Features

- ➕ Add points with `+NUMBER` (e.g., `+50`)
- ➖ Subtract points with `-NUMBER` (e.g., `-100`)
- 📊 View current total with `!score`
- 💾 Points persist across bot restarts (saved to JSON file)

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
Use the `!score` command:
- Message: `!score`
- Bot response: 📊 Current points: **35**

## How It Works

- Points are stored in `points.json` as a single total
- All users can add or subtract points
- Commands support optional descriptions: `+50`, `+50 for completing task`, etc.
- The bot responds to patterns like `+50`, `-100`, `+10 for cleaning`, etc.
- Invalid formats are ignored (e.g., `+ 50`, `+abc`, just `50`)
- Points persist even after restarting the bot

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
- Per-user point tracking
- Point history/leaderboard
- Admin-only modification controls
- Custom point increment values
- Role-based access restrictions
