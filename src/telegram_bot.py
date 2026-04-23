import requests

class TelegramBot:
    def __init__(self, token=None, chat_id=None):
        # Bạn hãy điền Token và Chat ID của bạn vào đây
        self.token = token or "YOUR_BOT_TOKEN"
        self.chat_id = chat_id or "YOUR_CHAT_ID"
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, text):
        if self.token == "YOUR_BOT_TOKEN":
            print(f"DEBUG (Telegram): {text}")
            return
            
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(self.base_url, json=payload)
            return response.json()
        except Exception as e:
            print(f"Lỗi gửi Telegram: {e}")
            return None

    def send_signal_alert(self, details):
        emoji = "🚀" if "BUY" in details['type'] else "🔥"
        msg = (
            f"{emoji} *[GOLD SIGNAL ALERT]* {emoji}\n"
            f"---------------------------\n"
            f"🎯 *Loại:* {details['type']}\n"
            f"⏱️ *Thời gian:* {details['time']}\n"
            f"💵 *Giá vào (Entry):* `{details['entry']}`\n"
            f"🛑 *Cắt lỗ (SL):* `{details['sl']}`\n"
            f"🎯 *Chốt lời (TP):* `{details['tp']}`\n"
            f"⚖️ *Tỉ lệ R:R:* `{details['rr']}`\n"
            f"---------------------------\n"
            f"📊 *H1 Context:* {details['h1_status']}\n"
            f"📈 *M5/M15 Sign:* {details['m5_status']}\n"
            f"🔊 *Volume:* {details['vol_status']}\n"
            f"---------------------------\n"
            f"💡 *Hành động:* {details['action']}\n"
            f"📊 *Xác suất lịch sử:* `{details['prob']}`"
        )
        return self.send_message(msg)
