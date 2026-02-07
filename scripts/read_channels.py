#!/usr/bin/env python3
"""Read latest messages from YoniNews Telegram channels and check for duplicates."""

import asyncio
import base64
import struct
import ipaddress
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 2778634
API_HASH = "9801669edc41e1df08488eae0a8aaff6"

CHANNELS = {
    "Hebrew": -1002569095525,
    "English": -1002840315669,
    "Spanish": -1002822235445,
}

MESSAGE_LIMIT = int(os.environ.get("MSG_LIMIT", "40"))


def build_string_session(b64_data: str) -> str:
    """Extract auth key from base64-encoded SQLite session and build a StringSession."""
    missing = len(b64_data) % 4
    if missing:
        b64_data += '=' * (4 - missing)

    data = base64.b64decode(b64_data)
    ip_pos = data.find(b'149.154.167.91')
    if ip_pos < 0:
        raise ValueError("Could not find DC4 IP in session data")

    auth_key = data[ip_pos + 14 + 2: ip_pos + 14 + 2 + 256]
    ip = ipaddress.ip_address('149.154.167.91')
    packed = struct.pack('>B4sH256s', 4, ip.packed, 443, auth_key)
    return '1' + base64.urlsafe_b64encode(packed).decode('ascii')


async def main():
    # Read session data from file or environment
    session_file = os.environ.get("SESSION_FILE", "/tmp/yoni_news_session_b64.txt")
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            b64_data = f.read().strip()
    elif os.environ.get("TELEGRAM_SESSION_DATA"):
        b64_data = os.environ["TELEGRAM_SESSION_DATA"]
    else:
        print("ERROR: No session data found.")
        print("Set SESSION_FILE env var or TELEGRAM_SESSION_DATA env var.")
        sys.exit(1)

    session_str = build_string_session(b64_data)
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("ERROR: Not authorized")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"Connected as: {me.first_name}\n")

    # Load entity cache from dialogs
    print("Loading dialogs...")
    async for _ in client.iter_dialogs():
        pass
    print()

    for name, chat_id in CHANNELS.items():
        print(f"\n{'=' * 60}")
        print(f"CHANNEL: {name} ({chat_id})")
        print(f"{'=' * 60}")

        try:
            messages = await client.get_messages(chat_id, limit=MESSAGE_LIMIT)
            print(f"Got {len(messages)} messages\n")

            seen = {}
            dups = []
            for msg in reversed(messages):
                if msg.text:
                    ds = msg.date.strftime("%Y-%m-%d %H:%M")
                    fp = msg.text[:100].strip()
                    preview = msg.text[:200].replace('\n', ' | ')
                    marker = ""
                    if fp in seen:
                        pid, pd = seen[fp]
                        marker = f" ** DUP of id:{pid} ({pd}) **"
                        dups.append((msg.id, pid, ds, pd))
                    else:
                        seen[fp] = (msg.id, ds)
                    print(f"[{ds}] id:{msg.id}{marker}")
                    print(f"  {preview}")
                    print()

            if dups:
                print(f"\n--- {len(dups)} DUPLICATES FOUND ---")
                for d1, d2, t1, t2 in dups:
                    print(f"  msg {d1} ({t1}) duplicates msg {d2} ({t2})")
            else:
                print(f"\n--- No duplicates in last {len(messages)} messages ---")

        except Exception as e:
            print(f"  ERROR: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
