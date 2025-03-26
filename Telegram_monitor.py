import json
import regex
import os
import asyncio
import logging
import traceback
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events

# --- START OF FILE Telegram_monitor.py ---

# Load configuration from credentials.json
CREDENTIALS_FILE = '/root/Telegram_monitor/credentials.json'

if not os.path.exists(CREDENTIALS_FILE):
    # File {CREDENTIALS_FILE} not found! Specify API ID, HASH, and TOKEN.
    raise FileNotFoundError(f"File {CREDENTIALS_FILE} not found! Specify API ID, HASH, and TOKEN.")

with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as file:
    credentials = json.load(file)

TELEGRAM_API_ID = int(credentials["api_id"])
TELEGRAM_API_HASH = credentials["api_hash"]
TELEGRAM_PHONE = credentials["phone"]
BOT_TOKEN = credentials["bot_token"]
PRIVATE_CHANNEL_LINK = credentials.get("channel_id", None)

# Configuration files
KEYWORDS_FILE = 'keywords.txt'
CHANNELS_FILE = 'channels.txt'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

def load_entries_from_file(file_path):
    """Loads lines from a file, removing empty ones"""
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} not found.")
        return []
    with open(file_path, 'r', encoding='utf-8') as file:
        entries = [x.strip() for x in file.read().splitlines() if x.strip()]
    return entries

def load_patterns():
    """Creates regex patterns for keywords"""
    keywords = load_entries_from_file(KEYWORDS_FILE)
    word_patterns = {}

    for word in keywords:
        # Using \b for word boundaries and (?i) for case-insensitivity
        pattern = rf'\b(?i){regex.escape(word)}\b'
        try:
            compiled = regex.compile(pattern)
            word_patterns[word] = compiled
        except regex.error as e:
            logging.error(f'Regex error for "{word}": {e}')
    return word_patterns

async def check_recent_messages(client, private_channel, channels, word_patterns):
    """Checks messages from the last 12 hours"""
    twelve_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)

    for channel in channels:
        try:
            entity = await client.get_entity(channel)
            # Fetch a reasonable number of recent messages (e.g., 100)
            messages = await client.get_messages(entity, limit=100)

            for message in messages:
                # Skip messages older than 12 hours
                if message.date.replace(tzinfo=timezone.utc) < twelve_hours_ago:
                    continue # Optimization: if we hit an old message, likely the rest are too

                message_content = message.message or ""
                word_counts = {}

                # Check each keyword pattern against the message content
                for word, pattern in word_patterns.items():
                    matches = list(pattern.finditer(message_content))
                    if matches:
                        word_counts[word] = len(matches)

                # If any keywords were found, format and send the notification
                if word_counts:
                    # Format matched words, showing count if > 1
                    matched_words_str = ', '.join(f"{word} ({count})" if count > 1 else word for word, count in word_counts.items())

                    message_text = (
                        # Found keywords in {entity.title}: {matched_words_str}
                        f"🔎 Found keywords in {entity.title}: {matched_words_str}\n"
                        # Message:
                        f"📝 Message:\n{message_content[:1000]}..." # Truncate long messages
                    )
                    await client.send_message(private_channel, message_text, link_preview=False)
                    # Sent message from {entity.title}
                    logging.info(f"Sent message from {entity.title}")

        except Exception as e:
            # Error processing recent messages from {channel}: {e}
            logging.error(f"Error processing recent messages from {channel}: {e}")

async def main():
    try:
        client = TelegramClient('user_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        await client.start(phone=TELEGRAM_PHONE)
        # Client started successfully.
        logging.info("Client started successfully.")

        if not PRIVATE_CHANNEL_LINK:
            # Error: channel_id is missing in credentials.json!
            raise ValueError("Error: channel_id is missing in credentials.json!")

        private_channel = await client.get_entity(PRIVATE_CHANNEL_LINK)
        # Fetched private channel: {private_channel.title} (ID: {private_channel.id})
        logging.info(f"Fetched private channel: {private_channel.title} (ID: {private_channel.id})")

        word_patterns = load_patterns()
        channels = load_entries_from_file(CHANNELS_FILE)

        # Send a startup message to the private channel
        await client.send_message(private_channel, f"📡 Bot started. Monitoring channels: {', '.join(channels)}")
        # Sent startup message to the private channel.
        logging.info("Sent startup message to the private channel.")

        # Check recent messages upon startup
        await check_recent_messages(client, private_channel, channels, word_patterns)

        # Define the event handler for new messages in the monitored channels
        @client.on(events.NewMessage(chats=channels))
        async def handler(event):
            try:
                message_content = event.message.message or ""
                word_counts = {}

                # Check each keyword pattern against the new message content
                for word, pattern in word_patterns.items():
                    matches = list(pattern.finditer(message_content))
                    if matches:
                        word_counts[word] = len(matches)

                # If any keywords were found, format and send the notification
                if word_counts:
                    # Format matched words, showing count if > 1
                    matched_words_str = ', '.join(f"{word} ({count})" if count > 1 else word for word, count in word_counts.items())

                    message_text = (
                        # Match found in {event.chat.title}: {matched_words_str}
                        f"📢 Match found in {event.chat.title}: {matched_words_str}\n"
                        # Message:
                        f"📝 Message:\n{message_content[:1000]}..." # Truncate long messages
                    )
                    await client.send_message(private_channel, message_text, link_preview=False)
                    # Sent message from {event.chat.title}
                    logging.info(f"Sent message from {event.chat.title}")

            except Exception as e:
                # Error processing message: {e}
                logging.error(f"Error processing message: {e}")
                logging.error(traceback.format_exc()) # Log full traceback for debugging

        # Keep the client running until disconnected
        await client.run_until_disconnected()

    except Exception as e:
        # Error in main: {e}
        logging.error(f"Error in main: {e}")
        logging.error(traceback.format_exc()) # Log full traceback for debugging

if __name__ == '__main__':
    asyncio.run(main())
# --- END OF FILE Telegram_monitor.py ---