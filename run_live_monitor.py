import time
import MetaTrader5 as mt5
from src.fetch_data import initialize_mt5
from src.signal_engine import SignalEngine
from src.telegram_bot import TelegramBot
from datetime import datetime

def main():
    print("====================================================")
    print("   GOLD SIGNAL SENTINEL - HỆ THỐNG CẢNH BÁO LIVE")
    print("====================================================")
    
    symbol = "GOLD"
    initialize_mt5()
    
    # Khởi tạo Engine và Bot
    # LƯU Ý: Bạn cần điền Token và Chat ID vào trong src/telegram_bot.py 
    # hoặc truyền trực tiếp vào đây: TelegramBot(token="...", chat_id="...")
    engine = SignalEngine(symbol)
    bot = TelegramBot()
    
    print(f"Đang theo dõi {symbol}... Quét mỗi 60 giây.")
    print("Nhấn Ctrl+C để dừng.")
    
    last_signal_time = None
    
    try:
        while True:
            current_time = datetime.now()
            
            # Quét tín hiệu
            signal = engine.scan_for_signals()
            
            if signal:
                # Tránh gửi tin nhắn liên tục cho cùng một tín hiệu trong vòng 15 phút
                if last_signal_time is None or (current_time - last_signal_time).total_seconds() > 900:
                    print(f"[{current_time.strftime('%H:%M:%S')}] PHÁT HIỆN TÍN HIỆU: {signal['type']}")
                    bot.send_signal_alert(signal)
                    last_signal_time = current_time
                else:
                    print(f"[{current_time.strftime('%H:%M:%S')}] Tín hiệu duy trì: {signal['type']} (Đã gửi thông báo)")
            else:
                if current_time.second < 2: # Chỉ in log mỗi phút một lần
                    print(f"[{current_time.strftime('%H:%M:%S')}] Đang quét thị trường... Chưa có tín hiệu hội tụ.")
            
            # Đợi 1 phút (quét theo nến M1)
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\nĐang dừng hệ thống...")
    finally:
        mt5.shutdown()
        print("Đã tắt kết nối MT5.")

if __name__ == "__main__":
    main()
