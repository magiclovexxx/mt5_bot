# MT5 Analyzer

Dự án này là một công cụ giúp tự động lấy dữ liệu nến (rates) từ MetaTrader 5 (MT5), tính toán các chỉ báo kỹ thuật (Bollinger Bands, RSI, EMA, ATR) và phân tích các điểm đảo chiều tiềm năng.

## Yêu cầu hệ thống

1. Đã cài đặt phần mềm **MetaTrader 5 (MT5)** trên máy tính và đã đăng nhập vào tài khoản giao dịch.
2. Đã cài đặt **Python 3.12** trở lên.

## Cài đặt và thiết lập môi trường

Dự án này sử dụng môi trường ảo (virtual environment) để quản lý các thư viện.

**Bước 1: Mở Terminal (PowerShell hoặc Command Prompt) tại thư mục dự án (`mt5_analyzer`).**

**Bước 2: Kích hoạt môi trường ảo (venv):**

```powershell
.\venv\Scripts\activate
```
*(Nếu bạn thấy `(venv)` xuất hiện ở đầu dòng lệnh nghĩa là đã thành công. Nếu bạn chưa có thư mục `venv`, hãy chạy lệnh `py -3.12 -m venv venv` để tạo mới).*

**Bước 3: Cài đặt các thư viện cần thiết (nếu chưa cài):**

```powershell
pip install -r requirements.txt
```

## Cấu hình

Trước khi chạy, bạn có thể thiết lập các cặp tiền và khung thời gian mà bạn muốn phân tích bằng cách mở file `main.py` và tìm đoạn cấu hình:

```python
    # 1. Configuration
    symbols = ["EURUSD", "XAUUSD"] # Danh sách các cặp tiền cần lấy dữ liệu
    timeframes = ["M1", "M15", "H1"] # Danh sách các khung thời gian
```

Bạn có thể thêm bớt các symbol (vd: `"GBPUSD"`, `"USDJPY"`) hoặc thay đổi khung thời gian (vd: `"M5"`, `"H4"`, `"D1"`).
*Lưu ý:* Cần phải mở phần mềm MT5 và đăng nhập thành công trước khi chạy script thì mới lấy được dữ liệu.

## Hướng dẫn chạy dự án

Đảm bảo MT5 đang mở, sau đó trong Terminal (đã kích hoạt `venv`), bạn chạy lệnh sau:

```powershell
python main.py
```

## Giải thích luồng xử lý

Khi chạy `main.py`, chương trình sẽ thực hiện các bước sau:
1. **Fetch Data:** Kết nối với MT5 và tải về dữ liệu giá lịch sử của các `symbols` và `timeframes` đã cấu hình. Dữ liệu thô sẽ được lưu ở định dạng CSV trong thư mục `data/`.
2. **Apply Indicators:** Tính toán và thêm các chỉ báo như BB (Bollinger Bands), RSI, EMA, ATR vào dữ liệu giá.
3. **Analyze:** Tìm các điểm có độ biến động cao (Volatility) và các điểm đảo chiều xu hướng dựa trên các điều kiện về kỹ thuật.
4. **Save Results:** Các điểm đảo chiều tiềm năng sẽ được tổng hợp và xuất ra file CSV, lưu tại thư mục `results/`.
