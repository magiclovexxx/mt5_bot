# 📈 TỔNG HỢP CHIẾN LƯỢC GOLD BB BREAKOUT (CHỜ XÁC NHẬN)
**Cập nhật:** Tháng 4/2026
**Dữ liệu backtest:** 1 năm gần nhất (XAUUSD)
**Chỉ báo:** Bollinger Bands (20, 2)

---

## 🎯 1. PHƯƠNG PHÁP ĐÃ CHỐT (Khuyến nghị Thực Chiến)

> [!IMPORTANT]
> Phương pháp này yêu cầu chờ **nến breakout đóng cửa** hoàn toàn mới đặt lệnh chờ (Pending Order) tại đỉnh/đáy của nến đó. Tuyệt đối **không** dùng Limit Order cản đầu giá đang chạy.

* **Entry:** Lệnh Limit đặt tại **High (nếu SELL)** hoặc **Low (nếu BUY)** của nến vừa phá vỡ (breakout) dải BB.
* **Stop Loss (SL):** Dùng *Structural N=1* (Đỉnh/Đáy của 1 nến ngay sau nến breakout). Trung bình SL chỉ rơi vào khoảng `3 - 6 giá`.
* **Take Profit (TP):** `R:R = 1:5` (TP = Khoảng cách SL × 5).

---

## 📊 2. KẾT QUẢ TỔNG QUAN (RR 1:5)

| Khung | Hướng | Số tín hiệu | Tỷ lệ TP | Tỷ lệ SL | EV / Lệnh | Đánh giá |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **M15** | SELL | 3,366 | 51.84% | 48.16% | **+2.11 R** | ✅ Tốt |
| **M15** | BUY | 3,288 | 57.91% | 42.09% | **+2.47 R** | 🏆 Rất Tốt |
| **H1** | SELL | 831 | 50.66% | 49.34% | **+2.04 R** | ✅ Tốt |
| **H1** | BUY | 698 | 63.04% | 36.96% | **+2.78 R** | 💎 **Tuyệt Vời** |

> [!TIP]
> **H1 BUY** (Bắt đáy ở khung H1) là setup mạnh nhất của Cậu Vàng. Với EV lên tới gần 2.8R, mỗi lệnh rủi ro 1% tài khoản sẽ mang về trung bình +2.8% lợi nhuận trong dài hạn.

---

## 🟢 3. CHI TIẾT SETUP BẮT ĐÁY (BUY)

Vàng luôn có xu hướng phục hồi mạnh mẽ sau những cú sập nhanh. Đây là mỏ vàng của chiến lược này.

### A. Khung H1 BUY (Kỳ vọng: 2.78R)
* **Ngưỡng phá vỡ BB% tốt nhất:**
  * Từ `0.2% - 0.3%`: Tỷ lệ thắng **72.3%** (EV +3.34R)
  * Lớn hơn `1.0%`: Tỷ lệ thắng **72.5%** (EV +3.35R)
* **Độ rộng Band (BB Width):** Tuyệt vời nhất khi Width từ `1.15% - 1.61%` (band đang mở vừa phải, chưa quá hỗn loạn).
* **Khung giờ vàng (Giờ VN):**
  * `00:00 - 01:00` sáng: Winrate 83%
  * `03:00 - 04:00` sáng: Winrate 78%
  * `01:00 - 02:00` sáng: Winrate 73%
  *(Thanh khoản mỏng phiên Á sớm giúp nến xác nhận có SL cực nhỏ)*

### B. Khung M15 BUY (Kỳ vọng: 2.47R)
* **Ngưỡng phá vỡ BB% tốt nhất:** 
  * Lớn hơn `1.0%`: Tỷ lệ thắng **64%** (EV +2.84R). Lực xả càng mạnh, giá bật hồi càng gắt.
  * Từ `0.15% - 0.5%`: Winrate đều trên 60%.
* **Khung giờ vàng (Giờ VN):**
  * `00:00 - 01:00`: Winrate 66.8%
  * `20:00 - 21:00`: Winrate 65.8% (Đầu phiên Mỹ)

---

## 🔴 4. CHI TIẾT SETUP BẮT ĐỈNH (SELL)

Bắt đỉnh rủi ro cao hơn bắt đáy, đòi hỏi phải tuân thủ bộ lọc chặt chẽ hơn.

### A. Khung H1 SELL (Kỳ vọng: 2.04R)
* **Ngưỡng phá vỡ BB% tốt nhất:**
  * Từ `0.5% - 1.0%`: Tỷ lệ thắng **60.4%** (EV +2.62R)
  * Phá vỡ nhẹ `0% - 0.05%`: Winrate 54.5% (EV +2.27R)
* **Khung giờ vàng (Giờ VN):**
  * `19:00 - 20:00`: Winrate 70.8% (Chuẩn bị vào phiên Mỹ)
  * `10:00 - 12:00`: Winrate 62-63% (Giữa phiên Á)
* **Giờ CẤM:** Không đánh SELL H1 lúc `06:00 - 07:00` (Thắng 5%, Lỗ sấp mặt).

### B. Khung M15 SELL (Kỳ vọng: 2.11R)
* **Ngưỡng phá vỡ BB% tốt nhất:**
  * Từ `0.2% - 0.3%`: Tỷ lệ thắng **58.3%** (EV +2.5R)
* **Khung giờ vàng (Giờ VN):**
  * `18:00 - 19:00`: Winrate 59.4%
  * `19:00 - 20:00`: Winrate 58.6%

---

## ⚙️ 5. VÍ DỤ TÍNH TOÁN THỰC CHIẾN

**Bắt đáy BUY H1 tại mốc phá vỡ 0.25%, Giá Vàng 2300:**

1. Nến `[0]` đóng cửa, tạo râu xuyên qua BB_Lower. Low của nến này là **2295**.
2. Nến `[1]` xuất hiện. Chờ nến `[1]` đóng cửa, ta lấy mức Low của nó làm điểm Stop Loss. Giả sử Low nến `[1]` là **2292**.
3. **Tính Risk:** $2295 - 2292 = 3$ giá (30 pip).
4. **Tính TP:** Khoảng cách TP = $3 \times 5 = 15$ giá. Mức chốt lời là $2295 + 15 = 2310$.
5. **Vào lệnh:** Treo lệnh **BUY LIMIT** ngay tại **2295**. Nếu giá rớt xuống khớp 2295, ta sẽ có 1 lệnh với:
   * SL = 2292
   * TP = 2310

---

## 📌 TỔNG KẾT
Chiến lược **chờ đóng nến xác nhận** cho tỷ lệ thắng và EV ấn tượng vì nó bắt buộc thị trường phải có dấu hiệu dừng lại (tạo đỉnh/đáy) mới cho phép chúng ta tham gia. Kết hợp với việc tính SL theo Cấu trúc N=1 giúp cắt giảm tối đa khoảng cách cắt lỗ, qua đó dễ dàng đạt mức R:R 1:5. 

> Khuyến nghị: Tập trung đánh **BUY (Bắt đáy)** ở cả H1 và M15, và ưu tiên các khung giờ giao phiên (Tối muộn phiên Mỹ sang Á, hoặc đầu phiên Âu).
