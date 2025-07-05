from telethon import TelegramClient
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH

# Using a file-based session to avoid logging in every time.
# The .session file will be created automatically in your project root.
client = TelegramClient('anon', TELEGRAM_API_ID, TELEGRAM_API_HASH)

async def fetch_telegram_messages(channel_username, limit=5):
    """
    Fetches the latest text messages from a public Telegram channel.
    """
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("Warning: Telegram API_ID or API_HASH not configured. Skipping Telegram fetching.")
        return []
    
    messages_to_return = []
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Telethon client not authorized. Please run interactively first to log in.")
            # In a real-world scenario, you would handle the login flow here,
            # but for this script, we assume the user logs in via a separate process or one-time run.
            await client.disconnect()
            return []

        async for message in client.iter_messages(channel_username, limit=limit):
            # We are only interested in text messages for now.
            if message.text:
                # We construct a dictionary that looks like our RSS article objects for consistency.
                messages_to_return.append({
                    'title': '', # We don't use a title for telegram messages to keep them clean
                    'summary': message.text,
                    'link': f"https://t.me/{channel_username}/{message.id}",
                    'id': f"https://t.me/{channel_username}/{message.id}"
                })
        await client.disconnect()
    except Exception as e:
        print(f"Error fetching messages from Telegram channel '{channel_username}': {e}")
        # Ensure client is disconnected on error
        if client.is_connected():
            await client.disconnect()

    return messages_to_return

if __name__ == '__main__':
    import asyncio

    async def test_fetch():
        # Replace 'telegram' with a public channel you want to test
        channel = 'telegram' 
        print(f"Fetching latest messages from '{channel}'...")
        messages = await fetch_telegram_messages(channel)
        if messages:
            print(f"Fetched {len(messages)} messages.")
            for msg in messages:
                print("\\n---")
                print(f"Title: {msg['title']}")
                print(f"Link: {msg['link']}")
                print(f"Summary: {msg['summary'][:100]}...") # Print first 100 chars
                print("---")
        else:
            print("No messages fetched.")

    asyncio.run(test_fetch()) 