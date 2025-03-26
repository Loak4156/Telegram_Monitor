
# Telegram Monitor

A Python-based monitoring bot that listens to public Telegram channels and forwards messages containing specific keywords to a private channel.

---

## ✨ Features

- Listens to any number of public channels defined in `channels.txt`
- Supports regex matching for precise keyword detection via `keywords.txt`
- Scans last 12 hours of messages on startup
- Real-time forwarding of matching messages
- Clean output with keyword hit count
- All settings and credentials stored in external files
- Compatible with both user accounts and bots (via Telethon)

---

## 📁 File Structure

```
telegram-monitor/
├── Telegram_monitor.py                 # Main monitoring script
├── credentials.json                    # API keys and target channel config
├── keywords.txt                        # List of keywords to match
├── channels.txt                        # List of Telegram channels to monitor
├── bot.log                             # Log file (auto-generated)
├── README.md                           # Project documentation
```

---

## ⚙️ Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/Loak4156/telegram-monitor.git
cd telegram-monitor
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create `credentials.json`
```json
{
  "api_id": "your_api_id",
  "api_hash": "your_api_hash",
  "phone": "your_phone_number",
  "bot_token": "123456:ABC-DEF...", 
  "channel_id": "@your_private_channel"
}
```

### 4. Add keywords
```
# keywords.txt
hacked
leak
data breach
usa
```

### 5. Add monitored channels
```
# channels.txt
@some_channel
@another_channel
```

---

## 🚀 Running the Bot

```bash
python3 Telegram_monitor.py
```

The bot will:
- Analyze messages from the last 12 hours
- Monitor incoming messages in real time
- Forward any matches to your private channel

---

## 🛡 Requirements

- Python 3.8+
- Telethon
- regex

Install via:
```bash
pip install telethon regex
```

---

## 🧠 Why?
This tool helps cyber threat intelligence teams monitor public Telegram sources for any relevant leaks or discussions in real-time.

---


