import json
import regex
import os
import asyncio
import logging
import traceback
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.errors import UsernameInvalidError, FloodWaitError

# Path settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
KEYWORDS_FILE = os.path.join(BASE_DIR, 'keywords.txt')
CHANNELS_FILE = os.path.join(BASE_DIR, 'channels.txt')
SESSION_NAME = os.path.join(BASE_DIR, 'user_session')
SENT_FILE = os.path.join(BASE_DIR, 'sent_messages.txt')
MAX_SENT_MESSAGES = 10000

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "bot.log")),
        logging.StreamHandler()
    ]
)

# Load credentials
if not os.path.exists(CREDENTIALS_FILE):
    raise FileNotFoundError(f"File {CREDENTIALS_FILE} not found!")

with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as file:
    credentials = json.load(file)

TELEGRAM_API_ID = int(credentials["api_id"])
TELEGRAM_API_HASH = credentials["api_hash"]
TELEGRAM_PHONE = credentials["phone"]
PRIVATE_CHANNEL_LINK = credentials.get("channel_id", None)

# File operations
def load_entries_from_file(file_path):
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} not found.")
        return []
    with open(file_path, 'r', encoding='utf-8') as file:
        return [x.strip() for x in file.read().splitlines() if x.strip()]

def load_patterns():
    keywords = load_entries_from_file(KEYWORDS_FILE)
    word_patterns = {}
    for word in keywords:
        pattern = rf'\b(?i){regex.escape(word)}\b'
        try:
            word_patterns[word] = regex.compile(pattern)
        except regex.error as e:
            logging.error(f'Regex error for "{word}": {e}')
    return word_patterns

def load_sent():
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
        if len(lines) > MAX_SENT_MESSAGES:
            logging.warning(f"📦 sent_messages.txt exceeds {MAX_SENT_MESSAGES} lines, clearing...")
            os.remove(SENT_FILE)
            return set()
        return set(lines)

def save_sent(sent_ids):
    if len(sent_ids) > MAX_SENT_MESSAGES:
        logging.warning(f"📦 Sent message count exceeded {MAX_SENT_MESSAGES}, clearing...")
        sent_ids.clear()
        if os.path.exists(SENT_FILE):
            os.remove(SENT_FILE)
    else:
        with open(SENT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sent_ids))

# Safe message sending with FloodWait handling
async def safe_send_message(client, target, text):
    try:
        await client.send_message(target, text, link_preview=False)
    except FloodWaitError as e:
        logging.warning(f"⏳ FloodWait: sleeping for {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)
        await client.send_message(target, text, link_preview=False)
    except Exception as e:
        logging.error(f"❌ Error while sending message: {e}")
        logging.error(traceback.format_exc())

# Processing recent messages
async def check_recent_messages(client, private_channel, channels, word_patterns):
    twelve_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)
    sent = load_sent()

    for channel in channels:
        try:
            entity = await client.get_entity(channel)
            messages = await client.get_messages(entity, limit=100)

            for message in messages:
                if message.date.replace(tzinfo=timezone.utc) < twelve_hours_ago:
                    continue

                msg_key = f"{entity.id}:{message.id}"
                if msg_key in sent:
                    continue

                message_content = message.message or ""
                word_counts = {}

                for word, pattern in word_patterns.items():
                    matches = list(pattern.finditer(message_content))
                    if matches:
                        word_counts[word] = len(matches)

                if word_counts:
                    matched_words_str = ', '.join(
                        f"{word} ({count})" if count > 1 else word
                        for word, count in word_counts.items()
                    )
                    msg_text = (
                        f"🔎 Keywords found in {entity.title}: {matched_words_str}\n"
                        f"📝 Message:\n{message_content[:1000]}..."
                    )
                    await safe_send_message(client, private_channel, msg_text)
                    logging.info(f"Message sent from {entity.title}")
                    sent.add(msg_key)
                    save_sent(sent)
                    await asyncio.sleep(1)

        except UsernameInvalidError:
            logging.warning(f"⚠️ Invalid or non-existent channel: {channel}")
        except Exception as e:
            logging.error(f"Error while processing channel {channel}: {e}")
            logging.error(traceback.format_exc())

# Main logic
async def main():
    try:
        client = TelegramClient(SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)
        await client.start(phone=TELEGRAM_PHONE)
        logging.info("Client started successfully.")

        if not PRIVATE_CHANNEL_LINK:
            raise ValueError("Error: channel_id is missing in credentials.json!")

        private_channel = await client.get_entity(PRIVATE_CHANNEL_LINK)
        logging.info(f"Private channel obtained: {private_channel.title} (ID: {private_channel.id})")

        word_patterns = load_patterns()
        channels = load_entries_from_file(CHANNELS_FILE)

        await safe_send_message(client, private_channel, f"📡 Bot started. Monitoring channels: {', '.join(channels)}")
        logging.info("Startup message sent to private channel.")

        await check_recent_messages(client, private_channel, channels, word_patterns)

        sent = load_sent()

        @client.on(events.NewMessage(chats=channels))
        async def handler(event):
            try:
                message_content = event.message.message or ""
                word_counts = {}

                for word, pattern in word_patterns.items():
                    matches = list(pattern.finditer(message_content))
                    if matches:
                        word_counts[word] = len(matches)

                if word_counts:
                    msg_key = f"{event.chat_id}:{event.message.id}"
                    if msg_key in sent:
                        return
                    matched_words_str = ', '.join(
                        f"{word} ({count})" if count > 1 else word
                        for word, count in word_counts.items()
                    )
                    msg_text = (
                        f"📢 Match found in {event.chat.title}: {matched_words_str}\n"
                        f"📝 Message:\n{message_content[:1000]}..."
                    )
                    await safe_send_message(client, private_channel, msg_text)
                    logging.info(f"Message sent from {event.chat.title}")
                    sent.add(msg_key)
                    save_sent(sent)

            except Exception as e:
                logging.error(f"Error while processing incoming message: {e}")
                logging.error(traceback.format_exc())

        await client.run_until_disconnected()

    except Exception as e:
        logging.error(f"Error in main: {e}")
        logging.error(traceback.format_exc())

if __name__ == '__main__':
    asyncio.run(main())
