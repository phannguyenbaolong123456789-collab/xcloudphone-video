# XCloudPhone Video Maker

Tool Python tự động tạo **video ngắn dọc 9:16 (1080×1920)** quảng bá và khen ngợi dịch vụ **XCloudPhone**
(mượt mà, giao diện đẹp, thao tác tiện lợi, hiệu năng mạnh mẽ) — dùng được ngay cho TikTok, Reels, YouTube Shorts.

## Tính năng

- **Kịch bản tiếng Việt** 5 câu ngắn, cuốn hút (sửa thoải mái trong `main.py` hoặc dùng file `.txt` riêng).
- **Giọng đọc tự nhiên** bằng [`edge-tts`](https://github.com/rany2/edge-tts): `vi-VN-HoaiMyNeural` (nữ) hoặc `vi-VN-NamMinhNeural` (nam). Mỗi câu một file audio, thời lượng đo chính xác để làm mốc dựng.
- **Nền linh hoạt**: đọc ảnh/video trong `assets/`; nếu trống sẽ tự tạo nền **gradient hiện đại** (kèm hình điện thoại + đám mây).
- **Zoom nhẹ (Ken Burns)** cho nền, xen kẽ zoom-in / zoom-out giữa các cảnh.
- **Phụ đề kiểu TikTok/Reels**: chữ to có viền, nền bo góc mờ, tự căn giữa, **chia dòng cân đối** (không tràn lề), tự thu nhỏ chữ nếu câu quá dài, từ khoá (*mượt, đẹp, mạnh mẽ…*) tô vàng, hiệu ứng "pop" khi xuất hiện.
- Phụ đề **khớp từng câu theo đúng thời lượng audio**; ghép bằng `moviepy`, xuất `output_xcloudphone.mp4` (H.264 + AAC, tương thích mọi nền tảng).

## Yêu cầu

- Python **3.9+**
- Kết nối Internet (edge-tts gọi dịch vụ đọc của Microsoft Edge; lần đầu còn tải font)
- Không cần cài ffmpeg riêng: `moviepy` đã kéo theo `imageio-ffmpeg`.

## Cài đặt

```bash
git clone <url-repo-cua-ban> xcloudphone-video
cd xcloudphone-video

python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt
```

> Tool dùng **moviepy 2.x**. Nếu bạn từng cài moviepy 1.x, hãy chạy `pip install -U -r requirements.txt`.

## Font chữ

Mặc định tool dùng **Be Vietnam Pro Bold** (hỗ trợ tiếng Việt rất tốt, giấy phép SIL OFL). Có 3 cách:

1. **Tự động (khuyên dùng):** cứ chạy `python main.py`, nếu chưa có font tool sẽ tự tải vào `fonts/`.
   Hoặc tải trước bằng lệnh:
   ```bash
   python main.py --download-font
   ```
2. **Tải thủ công:** vào [Google Fonts – Be Vietnam Pro](https://fonts.google.com/specimen/Be+Vietnam+Pro) → *Get font* → giải nén → copy `BeVietnamPro-Bold.ttf` vào thư mục `fonts/`.
   Hoặc dùng `curl`:
   ```bash
   curl -L -o fonts/BeVietnamPro-Bold.ttf \
     https://github.com/google/fonts/raw/main/ofl/bevietnampro/BeVietnamPro-Bold.ttf
   ```
3. **Dùng font khác** (Montserrat, Roboto…): đặt file `.ttf` vào `fonts/` hoặc chỉ định trực tiếp:
   ```bash
   python main.py --font "duong/dan/toi/font.ttf"
   ```
   Nhớ chọn font có hỗ trợ tiếng Việt (có đủ dấu: ạ ệ ữ ợ đ…).

Thứ tự tool tìm font: `--font` → file trong `fonts/` → tự tải → font hệ thống (Segoe UI/Arial/DejaVu…).

## Ảnh / video nền (tuỳ chọn)

Bỏ ảnh hoặc video vào thư mục `assets/`:

- Ảnh: `.jpg .jpeg .png .webp .bmp`
- Video: `.mp4 .mov .mkv .webm .avi .m4v` (video nền sẽ bị tắt tiếng)

Các file được sắp xếp theo tên rồi gán lần lượt cho từng câu (câu 1 → file 1, câu 2 → file 2…; hết file thì quay vòng). Ảnh/video ngang sẽ được cắt tự động theo khổ dọc 9:16, nên tốt nhất dùng ảnh dọc. Thư mục trống → tự dùng gradient.

## Chạy

```bash
python main.py
```

Kết quả: `output_xcloudphone.mp4` ngay trong thư mục dự án (khoảng 20–25 giây).

### Tuỳ chọn

| Tuỳ chọn | Ý nghĩa | Ví dụ |
|---|---|---|
| `--voice` | Giọng đọc | `--voice vi-VN-NamMinhNeural` |
| `--rate` | Tốc độ đọc | `--rate "+15%"` / `--rate "-5%"` |
| `--script` | File kịch bản riêng (mỗi dòng 1 câu, dòng bắt đầu bằng `#` bị bỏ qua) | `--script kichban.txt` |
| `--assets` | Thư mục nền khác | `--assets D:/anh-nen` |
| `--font` | Font `.ttf` riêng | `--font fonts/Roboto-Bold.ttf` |
| `--output`, `-o` | Tên file xuất | `-o video_tet.mp4` |
| `--fps` | Số khung hình/giây (mặc định 30) | `--fps 24` |
| `--keep-temp` | Giữ file audio từng câu trong `build/audio/` | |
| `--download-font` | Chỉ tải font rồi thoát | |

## Tuỳ biến nhanh trong `main.py`

Các hằng số ở đầu file:

- `SCRIPT` – kịch bản mặc định (nên 4–5 câu, mỗi câu dưới ~70 ký tự để phụ đề gọn).
- `PRONUNCIATION` – cách giọng đọc phát âm tên thương hiệu. Mặc định `XCloudPhone` → "Ích Clao Phôn" (chỉ ảnh hưởng giọng đọc, phụ đề vẫn là *XCloudPhone*). Nghe chưa vừa tai thì sửa chuỗi này, hoặc đặt `PRONUNCIATION = {}` để tắt.
- `HIGHLIGHT_WORDS`, `ACCENT` – từ khoá và màu tô nhấn trong phụ đề.
- `PALETTES` – bảng màu gradient.
- `ZOOM_AMOUNT`, `SENTENCE_GAP`, `LEAD_IN`, `END_PADDING` – mức zoom và nhịp nghỉ giữa các câu.
- `SUB_FONT_MAX`, `SUB_CENTER_Y`, `SUB_MAX_LINES` – cỡ chữ và vị trí phụ đề (mặc định nằm ở ~66% chiều cao, tránh vùng nút/mô tả của app).

## Cấu trúc dự án

```
xcloudphone-video/
├── main.py             # toàn bộ logic: TTS, nền, phụ đề, ghép video
├── requirements.txt
├── README.md
├── .gitignore
├── assets/             # ảnh/video nền của bạn (tuỳ chọn)
├── fonts/              # font .ttf (tự tải hoặc tự đặt vào)
└── build/              # file tạm khi chạy (tự xoá, đã .gitignore)
```

## Xử lý lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `edge-tts thất bại sau 3 lần thử` | Kiểm tra Internet/VPN/proxy; thử chạy lại. |
| `Không có font hỗ trợ tiếng Việt` | Tải font thủ công theo mục **Font chữ** ở trên. |
| Chữ tiếng Việt bị ô vuông `□` | Font đang dùng thiếu dấu tiếng Việt → dùng Be Vietnam Pro / Montserrat / Roboto. |
| `ImportError: cannot import name ... from 'moviepy'` | Đang dùng moviepy 1.x → `pip install -U -r requirements.txt`. |
| Dựng chậm | Bình thường với 1080×1920; giảm `--fps 24` hoặc dùng ảnh nền thay vì video. |
| Giọng đọc đọc sai tên thương hiệu | Chỉnh `PRONUNCIATION` trong `main.py`. |

## Đẩy lên GitHub

```bash
git init
git add .
git commit -m "XCloudPhone video maker"
git branch -M main
git remote add origin https://github.com/<ten-ban>/xcloudphone-video.git
git push -u origin main
```

`.gitignore` đã loại trừ video xuất ra, file tạm, font tải về và ảnh/video nền cá nhân.

## Giấy phép & lưu ý

- Font Be Vietnam Pro, Montserrat: SIL Open Font License.
- `edge-tts` dùng dịch vụ đọc văn bản trực tuyến của Microsoft Edge (không chính thức); hãy kiểm tra điều khoản sử dụng nếu dùng cho mục đích thương mại.
- Nội dung quảng cáo nên bảo đảm đúng với tính năng thực tế của dịch vụ.
