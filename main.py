#!/usr/bin/env python3
"""
XCloudPhone Video Maker
=======================
Tự động tạo video ngắn dọc 9:16 (1080x1920) quảng bá dịch vụ XCloudPhone:

  1. Kịch bản tiếng Việt (4-5 câu ngắn)  ->  2. edge-tts tạo giọng đọc từng câu
  3. Đo thời lượng từng file audio       ->  4. Dựng nền (ảnh/video/gradient) + zoom
  5. Phụ đề kiểu TikTok/Reels khớp từng câu  ->  6. moviepy xuất output_xcloudphone.mp4

Chạy nhanh:   python main.py
Xem tuỳ chọn: python main.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import random
import re
import sys
import unicodedata
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError as exc:  # pragma: no cover
    sys.exit(f"Thiếu thư viện '{exc.name}'. Hãy chạy: pip install -r requirements.txt")

# edge-tts và moviepy được import muộn (trong hàm) để file này vẫn import/kiểm thử
# được khi chưa cài đủ thư viện. Xem hàm require_runtime_libs().

# ----------------------------------------------------------------------------
# CẤU HÌNH
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = BASE_DIR / "fonts"
BUILD_DIR = BASE_DIR / "build"
OUTPUT_FILE = BASE_DIR / "output_xcloudphone.mp4"

WIDTH, HEIGHT = 1080, 1920          # tỉ lệ dọc 9:16
FPS = 30

DEFAULT_VOICE = "vi-VN-HoaiMyNeural"  # hoặc "vi-VN-NamMinhNeural"
DEFAULT_RATE = "+8%"                  # tốc độ đọc: "-10%" chậm hơn, "+15%" nhanh hơn
VOICES = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"]

LEAD_IN = 0.15        # giây im lặng đầu mỗi câu (để phụ đề hiện trước giọng đọc một nhịp)
SENTENCE_GAP = 0.35   # giây nghỉ sau mỗi câu
END_PADDING = 0.80    # giây nghỉ sau câu cuối cùng

ZOOM_AMOUNT = 0.12    # mức zoom nhẹ cho nền (12%)
POP_TIME = 0.30       # thời gian hiệu ứng "pop" của phụ đề (giây)

# Kịch bản mặc định (4-5 câu). Có thể thay bằng file riêng: python main.py --script kichban.txt
SCRIPT = [
    "Bạn có tin điện thoại chạy mượt như lụa ngay trên đám mây?",
    "XCloudPhone có giao diện đẹp, hiện đại, nhìn là mê ngay!",
    "Thao tác tiện lợi, chạm đâu mượt đó, không giật, không khựng.",
    "Hiệu năng mạnh mẽ, chơi game hay làm việc đều dư sức.",
    "XCloudPhone, đỉnh cao điện thoại đám mây. Thử ngay hôm nay!",
]

# Giúp giọng đọc phát âm tên thương hiệu tự nhiên hơn (chỉ áp dụng cho TTS, phụ đề vẫn hiện
# đúng "XCloudPhone"). Muốn tắt: để PRONUNCIATION = {}. Có thể chỉnh lại cho vừa tai.
PRONUNCIATION = {
    "XCloudPhone": "Ích Clao Phôn",
}

# Từ khoá được tô màu nhấn trong phụ đề (so khớp không phân biệt hoa/thường, bỏ dấu câu)
HIGHLIGHT_WORDS = {"xcloudphone", "mượt", "đẹp", "mạnh", "mẽ", "tiện", "lợi", "đỉnh", "cao"}
ACCENT = (255, 214, 10, 255)  # vàng

# Bảng màu gradient hiện đại (dùng khi thư mục assets/ trống)
PALETTES = [
    ("#6C5CE7", "#A66CFF", "#00D2FF"),   # tím -> xanh ngọc
    ("#FF512F", "#DD2476", "#6A11CB"),   # cam -> hồng -> tím
    ("#00C6FF", "#0072FF", "#7F00FF"),   # xanh dương -> tím
    ("#F953C6", "#B91D73", "#FF9A44"),   # hồng -> cam
    ("#11998E", "#38EF7D", "#0072FF"),   # xanh lá -> xanh dương
]

# Phụ đề
SUB_FONT_MAX = 86
SUB_FONT_MIN = 44
SUB_MAX_LINES = 4
SUB_MARGIN_X = 60          # lề trái/phải của khung phụ đề so với mép video
SUB_PAD_X, SUB_PAD_Y = 44, 34
SUB_RADIUS = 52
SUB_CENTER_Y = int(HEIGHT * 0.66)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

# Font: ưu tiên Be Vietnam Pro (hỗ trợ tiếng Việt rất tốt), dự phòng Montserrat.
# Tải từ repo google/fonts (giấy phép SIL OFL – được dùng/phân phối tự do).
FONT_SOURCES = [
    ("BeVietnamPro-Bold.ttf",
     "https://github.com/google/fonts/raw/main/ofl/bevietnampro/BeVietnamPro-Bold.ttf"),
    ("Montserrat-Variable.ttf",
     "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"),
]
LOCAL_FONT_PRIORITY = [
    "BeVietnamPro-Bold.ttf", "BeVietnamPro-ExtraBold.ttf", "BeVietnamPro-SemiBold.ttf",
    "Montserrat-Bold.ttf", "Montserrat-ExtraBold.ttf", "Montserrat-Variable.ttf",
    "Roboto-Bold.ttf", "Roboto-Variable.ttf",
]
SYSTEM_FONT_FALLBACKS = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


# ----------------------------------------------------------------------------
# TIỆN ÍCH CHUNG
# ----------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def ease_in_out(p: float) -> float:
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def normalize_word(word: str) -> str:
    word = unicodedata.normalize("NFC", word).lower()
    return re.sub(r"[^\w]", "", word)


def is_highlight(word: str) -> bool:
    return normalize_word(word) in {unicodedata.normalize("NFC", w) for w in HIGHLIGHT_WORDS}


def require_runtime_libs():
    """Import edge-tts + moviepy và trả về các đối tượng cần dùng."""
    try:
        import edge_tts
        from moviepy import (
            AudioFileClip,
            CompositeAudioClip,
            VideoClip,
            VideoFileClip,
            concatenate_videoclips,
        )
    except ImportError as exc:
        sys.exit(
            f"Thiếu thư viện '{exc.name}' hoặc moviepy phiên bản cũ (<2.0).\n"
            "Hãy chạy: pip install -r requirements.txt"
        )
    return edge_tts, AudioFileClip, CompositeAudioClip, VideoClip, VideoFileClip, concatenate_videoclips


# ----------------------------------------------------------------------------
# FONT
# ----------------------------------------------------------------------------
def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (xcloudphone-video)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        log(f"   ! Không tải được {url}\n     ({exc})")
        return False
    # Kiểm tra đúng là file font (tránh lưu nhầm trang lỗi HTML)
    if len(data) < 20_000 or data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"):
        log(f"   ! Dữ liệu tải về từ {url} không phải file font hợp lệ.")
        return False
    dest.write_bytes(data)
    return True


def download_fonts() -> Path | None:
    """Tải font vào thư mục fonts/. Trả về đường dẫn font đầu tiên tải được."""
    FONTS_DIR.mkdir(exist_ok=True)
    for name, url in FONT_SOURCES:
        dest = FONTS_DIR / name
        if dest.exists():
            return dest
        log(f"-> Đang tải font {name} ...")
        if _download(url, dest):
            log(f"   Đã lưu: {dest}")
            return dest
    return None


def resolve_font_path(custom: str | None = None) -> Path:
    if custom:
        p = Path(custom)
        if not p.exists():
            sys.exit(f"Không tìm thấy font: {p}")
        return p

    for name in LOCAL_FONT_PRIORITY:
        p = FONTS_DIR / name
        if p.exists():
            return p

    downloaded = download_fonts()
    if downloaded:
        return downloaded

    for candidate in SYSTEM_FONT_FALLBACKS:
        if Path(candidate).exists():
            log(f"-> Dùng font hệ thống dự phòng: {candidate}")
            return Path(candidate)

    others = sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf"))
    if others:
        return others[0]

    sys.exit(
        "Không có font hỗ trợ tiếng Việt. Hãy tải 'Be Vietnam Pro' (Google Fonts), "
        "đặt file BeVietnamPro-Bold.ttf vào thư mục fonts/ rồi chạy lại. Xem README.md."
    )


@lru_cache(maxsize=64)
def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(path, size)
    try:  # font biến thiên (Montserrat/Roboto variable) -> chọn kiểu Bold
        font.set_variation_by_name("Bold")
    except Exception:  # noqa: BLE001  (font tĩnh sẽ báo lỗi -> bỏ qua)
        pass
    return font


# ----------------------------------------------------------------------------
# NỀN: ẢNH / VIDEO / GRADIENT
# ----------------------------------------------------------------------------
def draw_phone_mockup(img: Image.Image) -> None:
    """Vẽ mô phỏng điện thoại + biểu tượng đám mây lên nền gradient (cho đỡ trống)."""
    s = 2  # supersampling cho nét mượt
    pw, ph = 350, 700
    canvas = Image.new("RGBA", (pw * s, ph * s), (255, 255, 255, 0))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle(
        (8 * s, 8 * s, (pw - 8) * s, (ph - 8) * s), radius=64 * s,
        fill=(255, 255, 255, 34), outline=(255, 255, 255, 150), width=6 * s,
    )
    cx = pw * s // 2
    d.rounded_rectangle((cx - 46 * s, 28 * s, cx + 46 * s, 46 * s), radius=9 * s,
                        fill=(255, 255, 255, 120))
    cy = (ph // 2 - 50) * s  # đám mây
    for dx, dy, rr in [(-60, 0, 46), (0, -34, 72), (66, 2, 42)]:
        d.ellipse((cx + (dx - rr) * s, cy + (dy - rr) * s,
                   cx + (dx + rr) * s, cy + (dy + rr) * s), fill=(255, 255, 255, 215))
    d.rounded_rectangle((cx - 130 * s, cy + 10 * s, cx + 130 * s, cy + 70 * s),
                        radius=30 * s, fill=(255, 255, 255, 215))
    for row in range(2):  # lưới "app"
        for col in range(3):
            x0 = cx + (-135 + col * 100) * s
            y0 = cy + (130 + row * 100) * s
            d.rounded_rectangle((x0, y0, x0 + 70 * s, y0 + 70 * s), radius=20 * s,
                                fill=(255, 255, 255, 90))
    canvas = canvas.resize((pw, ph), Image.Resampling.LANCZOS)
    img.paste(canvas, ((WIDTH - pw) // 2, 285), canvas)


def make_gradient_background(index: int) -> Image.Image:
    w, h = WIDTH, HEIGHT
    colors = np.array([hex_to_rgb(c) for c in PALETTES[index % len(PALETTES)]], dtype=np.float32)
    angle = math.radians(62 + 18 * (index % 3))
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    proj = xs * math.cos(angle) + ys * math.sin(angle)
    proj = (proj - proj.min()) / (proj.max() - proj.min())
    n = len(colors) - 1
    pos = proj * n
    idx = np.clip(pos.astype(np.int32), 0, n - 1)
    frac = (pos - idx)[..., None]
    arr = colors[idx] * (1 - frac) + colors[idx + 1] * frac
    img = Image.fromarray(arr.astype(np.uint8))

    # Các đốm sáng mờ (bokeh) cho nền bớt phẳng
    sw, sh = w // 4, h // 4
    glow = Image.new("RGBA", (sw, sh), (255, 255, 255, 0))
    gd = ImageDraw.Draw(glow)
    rng = random.Random(1000 + index)
    for _ in range(7):
        r = rng.randint(sw // 6, sw // 2)
        cx, cy = rng.randint(0, sw), rng.randint(0, sh)
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, rng.randint(22, 55)))
    glow = glow.filter(ImageFilter.GaussianBlur(22)).resize((w, h), Image.Resampling.BICUBIC)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    draw_phone_mockup(img)
    return img


def zoom_crop(src: Image.Image, zoom: float) -> Image.Image:
    """Cắt kiểu 'cover' về đúng 1080x1920 và phóng to theo hệ số zoom (>=1) quanh tâm."""
    sw, sh = src.size
    scale = max(WIDTH / sw, HEIGHT / sh)
    vw, vh = WIDTH / scale / zoom, HEIGHT / scale / zoom
    cx, cy = sw / 2, sh / 2
    box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
    return src.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR, box=box)


class Background:
    """Nguồn nền cho một câu thoại: ảnh, video hoặc gradient tự tạo."""

    def __init__(self, index: int, path: Path | None, video_cls):
        self.video = None
        self.image: Image.Image | None = None
        self.path = path
        try:
            if path is not None and path.suffix.lower() in VIDEO_EXT:
                self.video = video_cls(str(path), audio=False)
            elif path is not None:
                img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
                img.thumbnail((HEIGHT * 2, HEIGHT * 2), Image.Resampling.LANCZOS)  # tránh ảnh quá lớn
                self.image = img
        except Exception as exc:  # noqa: BLE001
            log(f"   ! Không đọc được {path.name if path else ''}: {exc} -> dùng gradient thay thế")
            self.video, self.image = None, None
        if self.video is None and self.image is None:
            self.image = make_gradient_background(index)

    def get(self, t: float, zoom: float) -> Image.Image:
        if self.video is not None:
            dur = max(float(self.video.duration or 0.1) - 0.05, 0.1)
            src = Image.fromarray(self.video.get_frame(t % dur))
        else:
            src = self.image
        return zoom_crop(src, zoom)

    def close(self) -> None:
        if self.video is not None:
            self.video.close()


def discover_assets(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_EXT | VIDEO_EXT)


# ----------------------------------------------------------------------------
# PHỤ ĐỀ KIỂU TIKTOK / REELS
# ----------------------------------------------------------------------------
def wrap_words(words: list[str], font: ImageFont.FreeTypeFont, max_width: float) -> list[list[str]]:
    lines: list[list[str]] = []
    cur: list[str] = []
    for w in words:
        if cur and font.getlength(" ".join(cur + [w])) > max_width:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def balanced_wrap(words: list[str], font: ImageFont.FreeTypeFont, max_width: float) -> list[list[str]]:
    """Chia dòng thông minh: giữ nguyên số dòng nhưng làm các dòng dài đều nhau."""
    best = wrap_words(words, font, max_width)
    n = len(best)
    if n <= 1:
        return best
    lo, hi = max(font.getlength(w) for w in words), max_width
    for _ in range(14):
        mid = (lo + hi) / 2
        cand = wrap_words(words, font, mid)
        if len(cand) <= n:
            best, hi = cand, mid
        else:
            lo = mid
    return best


def render_subtitle(text: str, font_path: Path) -> Image.Image:
    """Vẽ phụ đề thành ảnh RGBA: chữ to, viền đen, nền bo góc mờ, từ khoá tô vàng."""
    words = text.split()
    max_text_w = WIDTH - 2 * SUB_MARGIN_X - 2 * SUB_PAD_X
    size = SUB_FONT_MAX
    while True:
        font = load_font(str(font_path), size)
        lines = balanced_wrap(words, font, max_text_w)
        longest_fits = max(font.getlength(w) for w in words) <= max_text_w
        if (longest_fits and len(lines) <= SUB_MAX_LINES) or size <= SUB_FONT_MIN:
            break
        size -= 4

    asc, desc = font.getmetrics()
    line_h = int(size * 1.32)
    stroke = max(3, size // 14)
    line_widths = [font.getlength(" ".join(line)) for line in lines]
    box_w = int(max(line_widths)) + 2 * SUB_PAD_X
    box_h = line_h * len(lines) + 2 * SUB_PAD_Y

    img = Image.new("RGBA", (box_w, box_h), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, box_w - 1, box_h - 1), radius=SUB_RADIUS,
                        fill=(10, 10, 28, 165), outline=(255, 255, 255, 45), width=2)
    for i, line in enumerate(lines):
        x0 = (box_w - line_widths[i]) / 2
        baseline = SUB_PAD_Y + i * line_h + (line_h - (asc + desc)) / 2 + asc
        for j, word in enumerate(line):
            prefix = " ".join(line[:j]) + (" " if j else "")
            color = ACCENT if is_highlight(word) else (255, 255, 255, 255)
            d.text((x0 + font.getlength(prefix), baseline), word, font=font, fill=color,
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 255), anchor="ls")
    return img


def make_vignette() -> Image.Image:
    """Lớp tối dần ở mép trên/dưới để chữ luôn dễ đọc, kể cả khi nền là ảnh sáng."""
    ys = np.arange(HEIGHT, dtype=np.float32)
    top = np.clip(1 - ys / 520, 0, 1) ** 1.5 * 150
    bottom = np.clip((ys - 1250) / 670, 0, 1) ** 1.3 * 190
    alpha = np.maximum(top, bottom).astype(np.uint8)
    arr = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    arr[..., 3] = alpha[:, None]
    return Image.fromarray(arr)


def make_overlay(index: int, total: int, font_path: Path, vignette: Image.Image) -> Image.Image:
    """Lớp phủ tĩnh cho mỗi câu: vignette + huy hiệu thương hiệu + chấm tiến trình."""
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 0))
    d = ImageDraw.Draw(layer)

    font = load_font(str(font_path), 44)
    asc, desc = font.getmetrics()
    brand = "XCloudPhone"
    pad_x, pad_y = 38, 18
    pill_w = font.getlength(brand) + 2 * pad_x
    pill_h = asc + desc + 2 * pad_y
    left, top = (WIDTH - pill_w) / 2, 150
    d.rounded_rectangle((left, top, left + pill_w, top + pill_h), radius=pill_h / 2,
                        fill=(255, 255, 255, 48), outline=(255, 255, 255, 120), width=2)
    d.text((left + pad_x, top + pad_y), "X", font=font, fill=ACCENT)
    d.text((left + pad_x + font.getlength("X"), top + pad_y), "CloudPhone", font=font,
           fill=(255, 255, 255, 255))

    if total > 1:
        widths = [56 if i == index else 16 for i in range(total)]
        gap = 16
        x = (WIDTH - (sum(widths) + gap * (total - 1))) / 2
        y = 1610
        for i, wdt in enumerate(widths):
            fill = ACCENT if i == index else (255, 255, 255, 120)
            d.rounded_rectangle((x, y, x + wdt, y + 16), radius=8, fill=fill)
            x += wdt + gap

    return Image.alpha_composite(vignette, layer)


# ----------------------------------------------------------------------------
# TTS (edge-tts)
# ----------------------------------------------------------------------------
@dataclass
class Segment:
    index: int
    text: str
    audio_path: Path
    audio_duration: float
    start: float = 0.0
    total: float = 0.0


def apply_pronunciation(text: str) -> str:
    for src, dst in PRONUNCIATION.items():
        text = re.sub(re.escape(src), dst, text, flags=re.IGNORECASE)
    return text


async def synthesize(edge_tts, text: str, voice: str, rate: str, out_path: Path, retries: int = 3) -> None:
    for attempt in range(1, retries + 1):
        try:
            await edge_tts.Communicate(apply_pronunciation(text), voice, rate=rate).save(str(out_path))
            if out_path.exists() and out_path.stat().st_size > 0:
                return
            raise RuntimeError("File audio rỗng")
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                raise RuntimeError(
                    f"edge-tts thất bại sau {retries} lần thử (kiểm tra kết nối Internet): {exc}"
                ) from exc
            await asyncio.sleep(1.5 * attempt)


def measure_audio(path: Path, audio_clip_cls) -> float:
    """Lấy thời lượng (giây) chính xác của file mp3."""
    try:
        from mutagen.mp3 import MP3
        return float(MP3(str(path)).info.length)
    except Exception:  # noqa: BLE001  -> dự phòng bằng moviepy/ffmpeg
        clip = audio_clip_cls(str(path))
        try:
            return float(clip.duration)
        finally:
            clip.close()


async def build_audio(edge_tts, audio_clip_cls, sentences: list[str], voice: str, rate: str,
                      audio_dir: Path) -> list[Segment]:
    audio_dir.mkdir(parents=True, exist_ok=True)
    segments: list[Segment] = []
    for i, text in enumerate(sentences):
        path = audio_dir / f"sentence_{i + 1:02d}.mp3"
        log(f"-> TTS câu {i + 1}/{len(sentences)}: {text}")
        await synthesize(edge_tts, text, voice, rate, path)
        dur = measure_audio(path, audio_clip_cls)
        log(f"   {dur:.2f}s")
        segments.append(Segment(i, text, path, dur))
    return segments


def plan_timeline(segments: list[Segment]) -> float:
    t = 0.0
    for i, seg in enumerate(segments):
        tail = END_PADDING if i == len(segments) - 1 else SENTENCE_GAP
        seg.start = t
        seg.total = LEAD_IN + seg.audio_duration + tail
        t += seg.total
    return t


# ----------------------------------------------------------------------------
# DỰNG VIDEO
# ----------------------------------------------------------------------------
def build_segment_clip(seg: Segment, bg: Background, overlay: Image.Image, subtitle: Image.Image,
                       zoom_in: bool, video_clip_cls):
    dur = seg.total

    def make_frame(t: float):
        e = ease_in_out(t / dur)
        zoom = 1.0 + ZOOM_AMOUNT * (e if zoom_in else 1.0 - e)
        frame = bg.get(seg.start + t, zoom)
        frame.paste(overlay, (0, 0), overlay)

        sub = subtitle
        a = t / POP_TIME
        if a < 1.0:  # hiệu ứng pop: phóng nhẹ + hiện dần
            k = 1 - (1 - max(a, 0.0)) ** 3
            scale = 0.88 + 0.12 * k
            sub = subtitle.resize((max(1, int(subtitle.width * scale)),
                                   max(1, int(subtitle.height * scale))), Image.Resampling.BILINEAR)
            sub.putalpha(sub.getchannel("A").point(lambda v, k=k: int(v * k)))
        frame.paste(sub, ((WIDTH - sub.width) // 2, SUB_CENTER_Y - sub.height // 2), sub)
        return np.asarray(frame)

    return video_clip_cls(make_frame, duration=dur)


def render_video(segments: list[Segment], sources: list[Path], font_path: Path, output: Path,
                 fps: int, libs) -> None:
    _, audio_clip_cls, composite_audio_cls, video_clip_cls, video_file_cls, concat = libs
    total_duration = plan_timeline(segments)
    log(f"-> Tổng thời lượng video: {total_duration:.2f}s ({len(segments)} câu)")

    vignette = make_vignette()
    backgrounds: list[Background] = []
    clips = []
    audio_clips = []
    try:
        for seg in segments:
            path = sources[seg.index % len(sources)] if sources else None
            log(f"-> Dựng cảnh {seg.index + 1}/{len(segments)} "
                f"(nền: {path.name if path else 'gradient tự tạo'})")
            bg = Background(seg.index, path, video_file_cls)
            backgrounds.append(bg)
            overlay = make_overlay(seg.index, len(segments), font_path, vignette)
            subtitle = render_subtitle(seg.text, font_path)
            clips.append(build_segment_clip(seg, bg, overlay, subtitle,
                                            zoom_in=(seg.index % 2 == 0), video_clip_cls=video_clip_cls))
            audio_clips.append(audio_clip_cls(str(seg.audio_path)).with_start(seg.start + LEAD_IN))

        video = concat(clips, method="chain")
        audio = composite_audio_cls(audio_clips).with_duration(total_duration)
        video = video.with_audio(audio)

        log(f"-> Đang xuất {output.name} ...")
        video.write_videofile(
            str(output), fps=fps, codec="libx264", audio_codec="aac", audio_bitrate="192k",
            preset="medium", threads=os.cpu_count() or 4,
            ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart"],
        )
    finally:
        for c in audio_clips:
            c.close()
        for b in backgrounds:
            b.close()


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def load_script(path: str | None) -> list[str]:
    if not path:
        return SCRIPT
    p = Path(path)
    if not p.exists():
        sys.exit(f"Không tìm thấy file kịch bản: {p}")
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("#")]
    if not lines:
        sys.exit("File kịch bản trống.")
    return lines


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Tạo video ngắn 9:16 quảng bá XCloudPhone.")
    ap.add_argument("--output", "-o", default=str(OUTPUT_FILE), help="File video xuất ra")
    ap.add_argument("--assets", default=str(ASSETS_DIR), help="Thư mục ảnh/video nền")
    ap.add_argument("--voice", default=DEFAULT_VOICE, choices=VOICES, help="Giọng đọc tiếng Việt")
    ap.add_argument("--rate", default=DEFAULT_RATE, help='Tốc độ đọc, ví dụ "+0%%", "+10%%", "-5%%"')
    ap.add_argument("--script", help="File .txt kịch bản (mỗi dòng một câu, dòng bắt đầu bằng # bị bỏ qua)")
    ap.add_argument("--font", help="Đường dẫn font .ttf riêng (hỗ trợ tiếng Việt)")
    ap.add_argument("--fps", type=int, default=FPS, help="Số khung hình/giây")
    ap.add_argument("--download-font", action="store_true", help="Chỉ tải font vào fonts/ rồi thoát")
    ap.add_argument("--keep-temp", action="store_true", help="Giữ thư mục build/ (file audio từng câu)")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    if args.download_font:
        path = download_fonts()
        sys.exit(0 if path else "Tải font thất bại. Xem hướng dẫn tải thủ công trong README.md.")

    if sys.platform == "win32":  # tránh lỗi 'Event loop is closed' của aiohttp trên Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    libs = require_runtime_libs()
    edge_tts, audio_clip_cls = libs[0], libs[1]

    font_path = resolve_font_path(args.font)
    log(f"-> Font: {font_path.name}")

    sentences = load_script(args.script)
    sources = discover_assets(Path(args.assets))
    log(f"-> Nền: {len(sources)} file trong '{args.assets}'" if sources
        else "-> assets/ trống: dùng nền gradient tự tạo")

    segments = asyncio.run(build_audio(edge_tts, audio_clip_cls, sentences, args.voice, args.rate,
                                       BUILD_DIR / "audio"))
    output = Path(args.output)
    render_video(segments, sources, font_path, output, args.fps, libs)

    if not args.keep_temp:
        for seg in segments:
            seg.audio_path.unlink(missing_ok=True)
        try:
            (BUILD_DIR / "audio").rmdir()
            BUILD_DIR.rmdir()
        except OSError:
            pass
    log(f"\nXong! Video: {output.resolve()}")


if __name__ == "__main__":
    main()
