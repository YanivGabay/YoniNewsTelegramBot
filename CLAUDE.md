# YoniNews Telegram Bot

A Telegram bot that aggregates news from RSS feeds and PikudHaOref alerts, translates them to 3 languages, and posts to separate Telegram channels.

## Architecture

- **RSS News**: Fetches from Ynet, Fox News, NYT → AI filters/rates → summarizes → translates → posts to 3 channels
- **PikudHaOref Alerts**: Telethon listens to `PikudHaOref_all` channel → translates → posts emergency alerts to 3 channels
- **Deployment**: DigitalOcean App Platform (Worker component)

## Credentials (CRITICAL - Correct Values)

```
TELEGRAM_API_ID=27728634        # 8 digits! NOT 2778634
TELEGRAM_API_HASH=9801669edc41e1df08488eae0a8aaff6
TELEGRAM_BOT_TOKEN=<get from DO env vars or .env>
```

**Note**: Never commit bot tokens to git. Get from DigitalOcean env vars or local .env file.

## Channel IDs

| Channel | Chat ID | Invite Link |
|---------|---------|-------------|
| Hebrew | -1002569095525 | https://t.me/yoninewoficial |
| English | -1002840315669 | https://t.me/+OfHivOlj6ioyNTRk |
| Spanish | -1002822235445 | https://t.me/+k2DXLoE-VOJjOTZk |

## DigitalOcean Deployment

- **App ID**: `d3cf5115-3e06-428f-9338-d394a1aff0e4`
- **Check logs**: `doctl apps logs d3cf5115-3e06-428f-9338-d394a1aff0e4 --type=run`
- **Get app info**: `doctl apps get d3cf5115-3e06-428f-9338-d394a1aff0e4`

## Common Issues & Fixes

### "database disk image is malformed"
Session data corrupted. Fix:
```bash
python scripts/create_session.py  # Creates new session locally
# Then update TELEGRAM_SESSION_DATA env var in DO with the base64 output
```

### "ApiIdInvalidError"
Using wrong API_ID. Must be `27728634` (8 digits, not 7).

### "Could not find the input entity for PeerChannel"
Entity cache not populated. The bot code already handles this by calling `iter_dialogs()` before setting up event handlers.

### PikudHaOref alerts not received
1. Check Telethon client is authorized: look for "✅ Telethon client authorized" in logs
2. Check entity cache populated: "✅ Entity cache populated"
3. Check alert channel found: "✅ Found alert channel: פיקוד העורף"
4. Check listener started: "🚨 Real-time alert listener started"

## Key Files

- `src/main.py` - Main entry point, RSS processing, message formatting
- `src/bot.py` - Telethon client setup, PikudHaOref alert handling
- `src/llm_handler.py` - AI summarization and translation
- `src/prompts.py` - AI prompt templates
- `scripts/create_session.py` - Create new Telethon session

## Session Management

The Telethon session is stored as base64-encoded SQLite in `TELEGRAM_SESSION_DATA` env var.

To create a new session:
```bash
cd /home/yaniv/repos/yoni-news-telegram-bot
python scripts/create_session.py
# Follow prompts to log in with phone number (+972...)
# Copy the base64 output to DO env var
```

## Dev Mode

```bash
python -m src.main --dev  # Console output only, no Telegram sends
```
