from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psutil
import numpy as np

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}

from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QElapsedTimer, QMimeData, QObject, QPoint, QPointF,
    QRectF, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal, QPropertyAnimation, QEvent,
)
from PyQt6.QtGui import (
    QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent, QFont,
    QFontDatabase, QImage, QKeySequence, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient, QShortcut, QMouseEvent, QTextCursor,
)

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    _MEDIA_OK = True
except Exception:
    QAudioOutput = QMediaPlayer = QVideoWidget = None
    _MEDIA_OK = False

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    _WEB_OK = True
except Exception:
    QWebEngineView = QWebEnginePage = QWebEngineSettings = None
    _WEB_OK = False

from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QStackedWidget, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QProgressBar, QSlider,
    QListWidget, QListWidgetItem, QGridLayout, QGraphicsOpacityEffect, QInputDialog,
    QAbstractItemView,
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

# ==================== LOGO ADJUSTMENTS (edit these) ====================
# Everything visual about the J.A.R.V.I.S. reactor logo lives here.
# Change a value, save, and restart the app to see it.
LOGO_TITLE        = "JARVIS"  # center wordmark text
LOGO_RING_RADIUS  = 108.0     # main cyan ring radius (design units)
LOGO_TEXT_SIZE    = 28        # title lettering size (design units)
LOGO_GLOW         = 1.3       # ring bloom brightness (0.7 softer, 1.3 brighter)
LOGO_PARTICLES    = 0        # no floating particle dots; keep the logo clean
LOGO_PARTICLE_GLOW = 1.4      # particle visibility (0.6 faint, 1.4 brighter)
LOGO_SPEED        = 2.0       # base animation rate (0.5 slower, 1.5 faster)
LOGO_CLICK_SWELL  = 0.015     # click swell amount (keep small and subtle)
LOGO_CLICK_TIME   = 0.76      # click-effect duration in seconds
LOGO_DOT_RINGS    = True      # True = white sweeps drawn as dots, False = solid lines
LOGO_DOT_SIZE     = 0.8       # dot size multiplier for the white sweeps
LOGO_DOT_GAP      = 0.3       # spacing between sweep dots (0.6 = more dots, 1.8 = fewer)
LOGO_DOT_COUNT    = 14           # exactly 8 dots on the main logo sweep
LOGO_STARTUP_ANIM = True      # False = skip the ease-in, show logo instantly
# ======================================================================

# Modular UI settings/layout helpers.
from ui_settings import load as _ui_load, save as _ui_save, SettingsWindow
from ui_layout import clamp_size as _clamp_size, LayoutEditorDialog, load_layout as _load_layout_file, save_layout as _save_layout_file
from ui_theme import (
    button_css as _theme_button_css, primary_button_css as _theme_primary_css,
    field_css as _theme_field_css, card_css as _theme_card_css,
    header_css as _theme_header_css, chip_css as _theme_chip_css,
    section_css as _theme_section_css, title_css as _theme_title_css,
    subtitle_css as _theme_subtitle_css, scrollbar_css as _theme_scrollbar_css,
    hidden_scrollbar_css as _theme_hidden_scrollbar_css, tab_css as _theme_tab_css,
    slider_css as _theme_slider_css, checkbox_css as _theme_checkbox_css,
    status_color as _theme_status_color, meter_color as _theme_meter_color,
    icon_font_css as _theme_icon_font_css,
)


def _read_full_config() -> dict:
    """Read api_keys.json config dict. Returns {} on any error."""
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 148
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class C:
    BG        = "#00060a"
    PANEL     = "#010d14"
    PANEL2    = "#010f18"
    BORDER    = "#0d3347"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0f4060"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001f2e"
    ACC       = "#ff6b00"
    ACC2      = "#ffcc00"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    RED       = "#ff3355"
    MUTED_C   = "#ff3366"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#3a8a9a"
    TEXT_MED  = "#5ab8cc"
    WHITE     = "#d8f8ff"
    DARK      = "#000d14"
    BAR_BG    = "#011520"


class FuturisticBackdrop(QFrame):
    """Paint a subtle sci-fi grid, glow and circuit geometry behind a panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if parent is not None:
            parent.installEventFilter(self)
            self.setGeometry(parent.rect())
            self.lower()

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.setGeometry(obj.rect())
            self.lower()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            r = self.rect()
            w, h = max(1, r.width()), max(1, r.height())
            bounds = QRectF(1.5, 1.5, w - 3.0, h - 3.0)
            cut = max(10, min(16, min(w, h) * 0.045))
            path = QPainterPath()
            path.moveTo(QPointF(bounds.left() + cut, bounds.top()))
            path.lineTo(QPointF(bounds.right() - cut, bounds.top()))
            path.lineTo(QPointF(bounds.right(), bounds.top() + cut))
            path.lineTo(QPointF(bounds.right(), bounds.bottom() - cut))
            path.lineTo(QPointF(bounds.right() - cut, bounds.bottom()))
            path.lineTo(QPointF(bounds.left() + cut, bounds.bottom()))
            path.lineTo(QPointF(bounds.left(), bounds.bottom() - cut))
            path.lineTo(QPointF(bounds.left(), bounds.top() + cut))
            path.closeSubpath()
            p.setClipPath(path)

            base = QLinearGradient(0, 0, w, h)
            base.setColorAt(0.0, QColor(0, 42, 62, 235))
            base.setColorAt(0.42, QColor(1, 8, 20, 245))
            base.setColorAt(1.0, QColor(0, 54, 66, 230))
            p.fillPath(path, QBrush(base))

            glow = QRadialGradient(QPointF(w * 0.72, h * 0.18), max(w, h) * 0.72)
            glow.setColorAt(0.0, QColor(0, 190, 230, 52))
            glow.setColorAt(0.55, QColor(0, 65, 100, 20))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillPath(path, QBrush(glow))

            p.setPen(QPen(QColor(0, 170, 210, 28), 1))
            step = 24
            for x in range(0, w + step, step):
                p.drawLine(x, 0, x, h)
            for y in range(0, h + step, step):
                p.drawLine(0, y, w, y)

            p.setPen(QPen(QColor(0, 212, 255, 70), 1))
            p.drawLine(int(w * 0.08), int(h * 0.76), int(w * 0.92), int(h * 0.12))
            p.drawLine(int(w * 0.02), int(h * 0.28), int(w * 0.72), int(h * 0.98))
            ring = min(w, h) * 0.42
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(0, 212, 255, 48), 1))
            p.drawEllipse(QPointF(w * 0.78, h * 0.76), ring, ring)
            p.setPen(QPen(QColor(255, 107, 0, 48), 1))
            p.drawArc(QRectF(w * 0.58, h * 0.48, ring * 2, ring * 2), 25 * 16, 92 * 16)

            p.setClipping(False)
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Minimal backdrop outline: keep the panel clean and let interactive
            # controls provide the angular HUD accents. No bright corner fragments.
            p.setPen(QPen(QColor(C.BORDER_B), 0.8))
            p.drawPath(path)
        except Exception:
            pass
        p.end()


# Ana renge (accent) bağlı anahtarlar — durum renkleri (ACC, GREEN, RED…) sabit kalır
_HUE_LINKED = (
    "BG", "PANEL", "PANEL2", "BORDER", "BORDER_B", "BORDER_A",
    "PRI", "PRI_DIM", "PRI_GHO", "TEXT", "TEXT_DIM", "TEXT_MED",
    "WHITE", "DARK", "BAR_BG",
)
_PALETTE_DEFAULTS: dict[str, str] = {k: getattr(C, k) for k in _HUE_LINKED}

DEFAULT_UI_COLOR = _PALETTE_DEFAULTS["PRI"]


def apply_ui_accent(accent_hex: str) -> bool:
    """
    Seçilen accent rengine göre tüm turkuaz-ailesi paleti yeniden türetir
    (hue kaydırma — parlaklık/doygunluk oranları korunur, tasarım bozulmaz).
    Boyanan öğeler (HUD, dalga formu, metrikler) bir sonraki karede yeni
    rengi alır; stylesheet tabanlı paneller yeniden kurulduklarında alır.
    """
    import colorsys

    accent_hex = (accent_hex or "").strip().lower()
    if not (accent_hex.startswith("#") and len(accent_hex) == 7):
        return False
    try:
        int(accent_hex[1:], 16)
    except ValueError:
        return False

    def _hsv(h: str) -> tuple[float, float, float]:
        r = int(h[1:3], 16) / 255
        g = int(h[3:5], 16) / 255
        b = int(h[5:7], 16) / 255
        return colorsys.rgb_to_hsv(r, g, b)

    base_h            = _hsv(_PALETTE_DEFAULTS["PRI"])[0]
    acc_h, acc_s, _av = _hsv(accent_hex)
    dh   = acc_h - base_h
    grey = acc_s < 0.08   # griye yakın accent → tüm tema desaturize edilir

    for key, hex0 in _PALETTE_DEFAULTS.items():
        h, s, v = _hsv(hex0)
        if grey:
            s *= 0.15
        r, g, b = colorsys.hsv_to_rgb((h + dh) % 1.0, s, v)
        setattr(C, key, "#{:02x}{:02x}{:02x}".format(
            int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5)))
    return True


def current_palette() -> dict[str, str]:
    """C sınıfındaki accent'e bağlı renklerin anlık kopyası."""
    return {k: getattr(C, k) for k in _HUE_LINKED}


def retheme_all_widgets(old: dict[str, str], new: dict[str, str]) -> None:
    """
    CANLI tam tema değişimi. Uygulamadaki HER widget'ın stylesheet'inde eski
    palet renklerini yenileriyle değiştirir ve yeniden çizdirir. Böylece renk
    değişimi yalnızca boyanan öğelerde değil, panel/buton/kenarlık dahil tüm
    arayüzde ANINDA uygulanır — yeniden başlatma gerekmez.
    """
    mapping = {old[k].lower(): new[k].lower()
               for k in old if old[k].lower() != new.get(k, old[k]).lower()}
    if not mapping:
        return
    app = QApplication.instance()
    if app is None:
        return
    for w in app.allWidgets():
        try:
            ss = w.styleSheet()
            if ss:
                s2 = ss
                for o, n in mapping.items():
                    if o in s2:
                        s2 = s2.replace(o, n)
                if s2 != ss:
                    w.setStyleSheet(s2)
            w.update()
        except Exception:
            pass


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c


def _sfx(name: str) -> None:
    """Play a futuristic UI sound. Silent no-op when SFX disabled/unavailable."""
    try:
        from core import sfx as _sfx_mod
        fn = getattr(_sfx_mod, name, None)
        if callable(fn):
            fn()
    except Exception:
        pass


def _sfx_enabled(host=None) -> bool:
    try:
        feats = getattr(host, '_features', {}) if host is not None else {}
        if isinstance(feats, dict) and 'enable_sfx' in feats:
            return bool(feats['enable_sfx'])
        cfg = _ui_load(API_FILE)
        return bool((cfg.get('features', {}) or {}).get('enable_sfx', True))
    except Exception:
        return True


# ── Windows GPU via NVML DLL (no subprocess, no console window) ──────────────
_nvml_lib: object = None   # cached ctypes DLL
_nvml_ok:  object = None   # None=untested, True=works, False=unavailable


def _nvml_gpu_windows() -> float:
    """Return NVIDIA GPU utilisation % using nvml.dll directly — zero subprocess."""
    global _nvml_lib, _nvml_ok
    if _nvml_ok is False:
        return -1.0
    try:
        import ctypes

        class _Util(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

        if _nvml_lib is None:
            for dll_name in ("nvml", r"C:\Windows\System32\nvml.dll"):
                try:
                    lib = ctypes.WinDLL(dll_name)
                    lib.nvmlInit_v2()
                    _nvml_lib = lib
                    break
                except Exception:
                    continue

        if _nvml_lib is None:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            _nvml_ok = True
            return float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)

        dev = ctypes.c_void_p()
        _nvml_lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        util = _Util()
        _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(util))
        _nvml_ok = True
        return float(util.gpu)
    except Exception:
        _nvml_ok = False
        return -1.0


class _SysMetrics:
    def __init__(self):
        self.cpu  = 0.0
        self.mem  = 0.0
        self.net  = 0.0
        self.gpu  = -1.0
        self.tmp  = -1.0
        self.disk = 0.0
        self.batt = -1.0
        self.plugged = False
        self.uptime  = 0
        self.procs   = 0
        self._lock = threading.Lock()
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _update(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            sent = (nc.bytes_sent - self._last_net.bytes_sent) / dt
            recv = (nc.bytes_recv - self._last_net.bytes_recv) / dt
            net  = (sent + recv) / (1024 * 1024)
        else:
            net = 0.0
        self._last_net   = nc
        self._last_net_t = now

        gpu = self._get_gpu()

        tmp = self._get_temp()

        try:
            disk = float(psutil.disk_usage('C:\\' if _OS == 'Windows' else '/').percent)
        except Exception:
            disk = 0.0
        try:
            batt_info = psutil.sensors_battery()
            batt = float(batt_info.percent) if batt_info else -1.0
            plugged = bool(batt_info.power_plugged) if batt_info else False
        except Exception:
            batt, plugged = -1.0, False
        try:
            uptime = int(time.time() - psutil.boot_time())
        except Exception:
            uptime = 0
        try:
            procs = len(psutil.pids())
        except Exception:
            procs = 0

        with self._lock:
            self.cpu = cpu
            self.mem = mem
            self.net = net
            self.gpu = gpu
            self.tmp = tmp
            self.disk = disk
            self.batt = batt
            self.plugged = plugged
            self.uptime = uptime
            self.procs = procs

    def _get_gpu(self) -> float:
        # pynvml — subprocess-free, works on all platforms if installed
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            return float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
        except Exception:
            pass

        # Windows: nvml.dll via ctypes (already cached in _nvml_gpu_windows)
        if _OS == "Windows":
            return _nvml_gpu_windows()

        # Linux / macOS: libnvidia-ml shared lib via ctypes
        try:
            import ctypes
            _lib = "libnvidia-ml.so.1" if _OS == "Linux" else "libnvidia-ml.dylib"

            class _Util(ctypes.Structure):
                _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

            nv = ctypes.CDLL(_lib)
            nv.nvmlInit_v2()
            dev = ctypes.c_void_p()
            nv.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
            u = _Util()
            nv.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u))
            return float(u.gpu)
        except Exception:
            pass

        return -1.0   # N/A — zero subprocess on all platforms

    def _get_temp(self) -> float:
        # psutil — works on Linux; occasionally Windows with driver support
        try:
            temps = psutil.sensors_temperatures()
            for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                         "cpu-thermal", "zenpower", "it8688"]:
                if name in temps and temps[name]:
                    return temps[name][0].current
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass

        # Windows: wmi module (pure Python COM, zero subprocess)
        if _OS == "Windows":
            try:
                import wmi  # type: ignore
                w = wmi.WMI(namespace="root/wmi")
                tz = w.MSAcpi_ThermalZoneTemperature()
                if tz:
                    return (tz[0].CurrentTemperature / 10.0) - 273.15
            except Exception:
                pass

        return -1.0   # N/A — zero subprocess on all platforms

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "mem": self.mem,
                "net": self.net,
                "gpu": self.gpu,
                "tmp": self.tmp,
                "disk": self.disk,
                "batt": self.batt,
                "plugged": self.plugged,
                "uptime": self.uptime,
                "procs": self.procs,
            }


def _fmt_uptime(seconds) -> str:
    try:
        seconds = max(0, int(seconds))
    except Exception:
        return "--"
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, _s = divmod(rem, 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


_metrics = _SysMetrics()

class HudCanvas(QWidget):
    def __init__(self, face_path: str, assistant_name: str = "J.A.R.V.I.S", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"
        self._assistant_name = assistant_name

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 55.0
        self._tgt_halo   = 55.0
        self._last_t     = time.time()
        self._scan       = 0.0
        self._scan2      = 180.0
        self._rings      = [0.0, 120.0, 240.0]
        self._pulses: list[float] = [0.0, 50.0, 100.0]
        self._blink      = True
        self._blink_tick = 0
        self._particles: list[list[float]] = []
        self._face_px: QPixmap | None = None
        self._load_face(face_path)

        # Live audio reactivity: _live_amp is written from the audio threads
        # (0.0–1.0), _amp_disp is the smoothed value the paint code reads.
        self._live_amp  = 0.0
        self._amp_disp  = 0.0
        self._base_scale = 1.0    # slow "breathing" target; amp is added per-frame
        self._base_halo  = 55.0

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def set_audio_level(self, level: float) -> None:
        """Thread-safe entry point for the audio threads. Stores the louder of
        the incoming level and the current value so brief gaps between chunks
        don't make the waveform stutter; _step() decays it back down."""
        try:
            lv = float(level)
        except (TypeError, ValueError):
            return
        if lv < 0.0:
            lv = 0.0
        elif lv > 1.0:
            lv = 1.0
        if lv > self._live_amp:
            self._live_amp = lv

    @property
    def assistant_name(self) -> str:
        return self._assistant_name

    @assistant_name.setter
    def assistant_name(self, value: str) -> None:
        self._assistant_name = str(value).strip() or "J.A.R.V.I.S"

    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz  = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mk  = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mk)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None

    def _step(self):
        self._tick += 1
        now = time.time()

        # ── Live audio reactivity ────────────────────────────────────────────
        # Audio threads push peaks into _live_amp; decay it toward silence so
        # gaps between chunks fade out instead of freezing, then smooth it.
        self._live_amp *= 0.86
        self._amp_disp += (self._live_amp - self._amp_disp) * 0.45
        amp = self._amp_disp

        # Slow "breathing" base target (random shimmer), refreshed on a timer.
        if now - self._last_t > (0.12 if self.speaking else 0.5):
            if self.speaking:
                self._base_scale = 1.03
                self._base_halo  = 122.0
            elif self.muted:
                self._base_scale = random.uniform(0.998, 1.002)
                self._base_halo  = random.uniform(15, 28)
            else:
                self._base_scale = random.uniform(1.001, 1.008)
                self._base_halo  = random.uniform(48, 68)
            self._last_t = now

        # Every frame, the live audio level lifts the target on top of the base
        # — this is what makes the core visibly pulse to the actual voice.
        if self.muted:
            self._tgt_scale, self._tgt_halo = self._base_scale, self._base_halo
        elif self.speaking:
            self._tgt_scale = self._base_scale + amp * 0.13
            self._tgt_halo  = self._base_halo  + amp * 95.0
        else:
            self._tgt_scale = self._base_scale + amp * 0.06
            self._tgt_halo  = self._base_halo  + amp * 75.0

        sp = 0.38 if self.speaking else (0.30 if amp > 0.02 else 0.15)
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo  += (self._tgt_halo  - self._halo)  * sp

        # Rings/scanners spin faster while speaking, reacting to loudness.
        boost  = 1.0 + amp * 1.6
        speeds = ([1.3, -0.9, 2.0] if self.speaking else [0.55, -0.35, 0.9])
        for i, spd in enumerate(speeds):
            self._rings[i] = (self._rings[i] + spd * boost) % 360

        self._scan  = (self._scan  + (3.0 if self.speaking else 1.3) * boost) % 360
        self._scan2 = (self._scan2 + (-2.0 if self.speaking else -0.75) * boost) % 360

        fw  = min(self.width(), self.height())
        lim = fw * 0.74
        spd = 4.2 if self.speaking else 2.0
        self._pulses = [r + spd for r in self._pulses if r + spd < lim]
        if len(self._pulses) < 3 and random.random() < (0.07 if self.speaking else 0.025):
            self._pulses.append(0.0)

        if self.speaking and random.random() < 0.28:
            cx, cy = self.width() / 2, self.height() / 2
            ang = random.uniform(0, 2 * math.pi)
            r_s = fw * 0.28
            self._particles.append([
                cx + math.cos(ang) * r_s, cy + math.sin(ang) * r_s,
                math.cos(ang) * random.uniform(0.9, 2.4),
                math.sin(ang) * random.uniform(0.9, 2.4) - 0.4, 1.0,
            ])
        self._particles = [
            [p[0]+p[2], p[1]+p[3], p[2]*0.97, p[3]*0.97, p[4]-0.028]
            for p in self._particles if p[4] > 0
        ]

        self._blink_tick += 1
        if self._blink_tick >= 38:
            self._blink = not self._blink
            self._blink_tick = 0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        if not p.isActive():      # device not ready (e.g. 0-size during layout) — skip cleanly
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(C.BG, 128))

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)

        # grid dots
        p.setPen(QPen(qcol(C.PRI_GHO), 1))
        for x in range(0, W, 48):
            for y in range(0, H, 48):
                p.drawPoint(x, y)

        r_face = fw * 0.31

        # halo glow
        for i in range(10):
            r   = r_face * (1.8 - i * 0.08)
            frc = 1.0 - i / 10
            a   = max(0, min(255, int(self._halo * 0.085 * frc)))
            col = qcol(C.MUTED_C if self.muted else C.PRI, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # pulse rings
        for pr in self._pulses:
            a   = max(0, int(230 * (1.0 - pr / (fw * 0.74))))
            col = qcol(C.MUTED_C if self.muted else C.PRI, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))

        # spinning arc rings
        for idx, (r_frac, w_r, arc_l, gap) in enumerate(
            [(0.48, 3, 115, 78), (0.40, 2, 78, 55), (0.32, 1, 56, 40)]
        ):
            ring_r = fw * r_frac
            base   = self._rings[idx]
            a_val  = max(0, min(255, int(self._halo * (1.0 - idx * 0.18))))
            col    = qcol(C.MUTED_C if self.muted else C.PRI, a_val)
            p.setPen(QPen(col, w_r)); p.setBrush(Qt.BrushStyle.NoBrush)
            angle = base
            rect  = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            while angle < base + 360:
                p.drawArc(rect, int(angle * 16), int(arc_l * 16))
                angle += arc_l + gap

        # scanners
        sr = fw * 0.50
        sa = min(255, int(self._halo * 1.5))
        ex = 75 if self.speaking else 44
        p.setPen(QPen(qcol(C.MUTED_C if self.muted else C.PRI, sa), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
        p.drawArc(srect, int(self._scan * 16), int(ex * 16))
        p.setPen(QPen(qcol(C.ACC, sa // 2), 1.5))
        p.drawArc(srect, int(self._scan2 * 16), int(ex * 16))

        # tick marks
        t_out, t_in = fw * 0.497, fw * 0.474
        p.setPen(QPen(qcol(C.PRI, 140), 1))
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inn = t_in if deg % 30 == 0 else t_in + 6
            p.drawLine(
                QPointF(cx + t_out * math.cos(rad), cy - t_out * math.sin(rad)),
                QPointF(cx + inn  * math.cos(rad), cy - inn  * math.sin(rad)),
            )

        # crosshair
        ch_r, gap_h = fw * 0.51, fw * 0.16
        p.setPen(QPen(qcol(C.PRI, int(self._halo * 0.5)), 1))
        p.drawLine(QPointF(cx - ch_r, cy), QPointF(cx - gap_h, cy))
        p.drawLine(QPointF(cx + gap_h, cy), QPointF(cx + ch_r, cy))
        p.drawLine(QPointF(cx, cy - ch_r), QPointF(cx, cy - gap_h))
        p.drawLine(QPointF(cx, cy + gap_h), QPointF(cx, cy + ch_r))

        # corner brackets
        bl = 24
        bc = qcol(C.PRI, 210)
        hl, hr = cx - fw // 2, cx + fw // 2
        ht, hb = cy - fw // 2, cy + fw // 2
        p.setPen(QPen(bc, 2))
        for bx, by, dx, dy in [(hl,ht,1,1),(hr,ht,-1,1),(hl,hb,1,-1),(hr,hb,-1,-1)]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

        # face
        if self._face_px:
            fsz    = int(fw * 0.62 * self._scale)
            scaled = self._face_px.scaled(
                fsz, fsz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
        else:
            orb_r = int(fw * 0.27 * self._scale)
            oc    = (200, 0, 50) if self.muted else (0, 60, 110)
            for i in range(8, 0, -1):
                r2  = int(orb_r * i / 8)
                frc = i / 8
                a   = max(0, min(255, int(self._halo * 1.1 * frc)))
                p.setBrush(QBrush(QColor(int(oc[0]*frc), int(oc[1]*frc), int(oc[2]*frc), a)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))
            p.setPen(QPen(qcol(C.PRI, min(255, int(self._halo * 2))), 1))
            p.setFont(QFont("Exo 2", 13, QFont.Weight.Bold))
            p.drawText(QRectF(cx - 80, cy - 14, 160, 28),
                       Qt.AlignmentFlag.AlignCenter, self._assistant_name)

        # particles
        for pt in self._particles:
            a = max(0, min(255, int(pt[4] * 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        # status text
        sy = cy + fw * 0.40
        if self.muted:
            txt, col = "⊘  MUTED",     qcol(C.MUTED_C)
        elif self.speaking:
            txt, col = "●  SPEAKING",  qcol(C.ACC)
        elif self.state == "THINKING":
            sym = "◈" if self._blink else "◇"
            txt, col = f"{sym}  THINKING",   qcol(C.ACC2)
        elif self.state == "PROCESSING":
            sym = "▷" if self._blink else "▶"
            txt, col = f"{sym}  PROCESSING", qcol(C.ACC2)
        elif self.state == "LISTENING":
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  LISTENING",  qcol(C.GREEN)
        else:
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  {self.state}", qcol(C.PRI)

        p.setPen(QPen(col, 1))
        p.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        p.drawText(QRectF(0, sy, W, 26), Qt.AlignmentFlag.AlignCenter, txt)

        # waveform — reacts to the real audio level (mic while listening,
        # JARVIS's own voice while speaking). Falls back to a gentle idle
        # ripple when there's no sound. _amp_disp is the smoothed 0–1 level.
        wy = sy + 30
        N, bw = 36, 8
        wx0 = (W - N * bw) / 2
        amp = self._amp_disp
        mid = (N - 1) / 2.0
        for i in range(N):
            if self.muted:
                hgt, cl = 2, qcol(C.MUTED_C)
            else:
                env     = (1.0 - abs(i - mid) / mid) ** 0.7      # center-weighted hump
                shimmer = 0.55 + 0.45 * math.sin(self._tick * 0.18 + i * 0.7)
                idle    = 3.0 + 2.0 * math.sin(self._tick * 0.09 + i * 0.6)
                hgt     = int(max(2, min(24, idle + amp * 22.0 * env * shimmer)))
                if amp > 0.05:
                    cl = qcol(C.PRI) if hgt > 12 else qcol(C.PRI_DIM)
                else:
                    cl = qcol(C.BORDER_B)
            p.fillRect(QRectF(wx0 + i * bw, wy + 20 - hgt, bw - 1, hgt), cl)

        p.end()   # end deterministically so the backing store never flushes an active painter

class MetricBar(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0       # 0–100
        self._text  = "--"
        self.setFixedHeight(38)
        self.setMinimumWidth(80)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setBrush(QBrush(qcol(C.PANEL2)))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 4, 4)

        bar_h   = 4
        bar_y   = H - bar_h - 5
        bar_w   = W - 12
        bar_x   = 6
        fill_w  = int(bar_w * self._value / 100)

        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        if self._value > 85:
            bar_col = qcol(C.RED)
        elif self._value > 65:
            bar_col = qcol(C.ACC)
        else:
            bar_col = qcol(self._color)

        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        p.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont("Orbitron", 9, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 4, W - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)

        p.end()

class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Share Tech Mono", 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 6px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: transparent;
                border: none;
                min-height: 20px;
            }}
            QScrollBar:horizontal {{ background: transparent; height: 0px; border: none; }}
            QScrollBar::handle:horizontal {{ background: transparent; border: none; }}
        """)
        # Chatlog scrollbar hidden — wheel / touch scrolling still works,
        # auto-scroll is driven in code after every append.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._queue: list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._ai_name_lc = "jarvis"   # updated when assistant name changes
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text   = self._queue.pop(0)
        self._pos    = 0
        tl = self._text.lower()
        _ai_pfx = f"{self._ai_name_lc}:"
        if   tl.startswith("you:"):                              self._tag = "you"
        elif tl.startswith(_ai_pfx) or tl.startswith("jarvis:"): self._tag = "ai"
        elif tl.startswith("file:"):                             self._tag = "file"
        elif "err" in tl:                                        self._tag = "err"
        else:                                                    self._tag = "sys"
        self._tmr.start(6)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = {
                "you":  qcol(C.WHITE),
                "ai":   qcol(C.PRI),
                "err":  qcol(C.RED),
                "file": qcol(C.GREEN),
                "sys":  qcol(C.ACC2),
            }.get(self._tag, qcol(C.TEXT))
            fmt.setForeground(QBrush(col))
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._next)

_FILE_ICONS = {
    "image":   ("🖼", "#00d4ff"), "video":   ("🎬", "#ff6b00"),
    "audio":   ("🎵", "#cc44ff"), "pdf":     ("📄", "#ff4444"),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", "#44bb44"),
    "code":    ("💻", "#ffcc00"), "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", "#88ddff"), "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],         "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],        "audio"),
    **dict.fromkeys(["pdf"],                                                     "pdf"),
    **dict.fromkeys(["doc","docx"],                                              "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                        "excel"),
    **dict.fromkeys(["ppt","pptx"],                                              "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],   "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                   "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                    "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                  "data"),
}

def _file_category(path: Path) -> str:
    return _EXT_TO_CAT.get(path.suffix.lower().lstrip("."), "unknown")

def _fmt_size(size: int) -> str:
    if   size < 1024:    return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    else:                return f"{size/1024**3:.1f} GB"


class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        self._dash_offset = 0.0
        self._anim_tmr = QTimer(self)
        self._anim_tmr.timeout.connect(self._animate)
        self._anim_tmr.start(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _DropCanvas(self)
        layout.addWidget(self._canvas)

    def _animate(self):
        self._dash_offset = (self._dash_offset + 0.8) % 20
        self._canvas.update()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a file for JARVIS", str(Path.home()),
            "All Files (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)",
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z    = self._z
        W, H = self.width(), self.height()
        pad  = 6
        rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)

        bg_col = qcol("#001a24" if z._drag_over else ("#001218" if z._hovering else C.PANEL))
        p.setBrush(QBrush(bg_col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   border_col = qcol(C.GREEN, 200)
        elif z._drag_over:    border_col = qcol(C.PRI, 230)
        elif z._hovering:     border_col = qcol(C.BORDER_B, 200)
        else:                 border_col = qcol(C.BORDER, 160)

        pen = QPen(border_col, 1.5, Qt.PenStyle.DashLine)
        pen.setDashOffset(z._dash_offset)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   self._paint_file(p, W, H)
        elif z._drag_over:    self._paint_drag_over(p, W, H)
        else:                 self._paint_idle(p, W, H, z._hovering)

        p.end()

    def _paint_idle(self, p, W, H, hover):
        cx, cy = W / 2, H / 2
        col = qcol(C.PRI_DIM if not hover else C.PRI)
        p.setPen(QPen(col, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(cx, cy - 14), QPointF(cx, cy + 4))
        p.drawLine(QPointF(cx - 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx + 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx - 14, cy + 4), QPointF(cx + 14, cy + 4))
        p.setFont(QFont("Exo 2", 8))
        p.setPen(QPen(qcol(C.PRI_DIM if not hover else C.TEXT), 1))
        p.drawText(QRectF(0, cy + 8, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "Drop file here  or  Click to Browse")
        p.setFont(QFont("Exo 2", 7))
        p.setPen(QPen(qcol("#1a4a5a"), 1))
        p.drawText(QRectF(0, cy + 24, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "Images · Video · Audio · PDF · Docs · Code · Data")

    def _paint_drag_over(self, p, W, H):
        cx, cy = W / 2, H / 2
        p.setFont(QFont("Exo 2", 20))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy - 24, W, 32), Qt.AlignmentFlag.AlignCenter, "⬇")
        p.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy + 12, W, 16), Qt.AlignmentFlag.AlignCenter, "Release to load")

    def _paint_file(self, p, W, H):
        path = Path(self._z._current_file)
        cat  = _file_category(path)
        icon, icon_col = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size)
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        p.setFont(QFont("Segoe UI Emoji", 22) if _OS == "Windows" else QFont("Arial", 22))
        p.setPen(QPen(qcol(icon_col), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 6
        tw = W - tx - 38

        p.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 34 else path.name[:31] + "..."
        p.drawText(QRectF(tx, H * 0.18, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        p.setFont(QFont("Exo 2", 7))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(tx, H * 0.18 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")

        p.setFont(QFont("Exo 2", 6))
        p.setPen(QPen(qcol("#1e5c6a"), 1))
        par = str(path.parent)
        if len(par) > 42: par = "…" + par[-41:]
        p.drawText(QRectF(tx, H * 0.18 + 34, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)

        p.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.RED, 180), 1))
        p.drawText(QRectF(W - 34, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, e):
        z = self._z
        if z._current_file and e.pos().x() > self.width() - 34:
            z.clear_file()
        else:
            z.mousePressEvent(e)


_face_cascade = None


def _detect_faces(jpg_bytes: bytes) -> list[tuple[float, float, float, float]]:
    """Detect faces with OpenCV Haar cascade. Returns relative (x, y, w, h) rects."""
    global _face_cascade
    try:
        import cv2
        import numpy as np
    except Exception:
        return []
    try:
        if _face_cascade is None:
            _face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            if _face_cascade.empty():
                _face_cascade = None
                return []
        arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []
        h, w = img.shape[:2]
        scale = 320.0 / max(1, w)
        small = cv2.resize(img, (max(80, int(w * scale)), max(60, int(h * scale))))
        faces = _face_cascade.detectMultiScale(small, scaleFactor=1.15, minNeighbors=4, minSize=(36, 36))
        sw = w / small.shape[1]
        return [(float(x * sw / w), float(y * sw / h),
                 float(fw * sw / w), float(fh * sw / h)) for (x, y, fw, fh) in faces]
    except Exception:
        return []


class _ScanOverlay(QWidget):
    """Horizontal glowing blue scan line sweeping top → bottom."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._pos = 0.0
        self._single = False
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self.hide()

    def start(self, single: bool = False) -> None:
        try:
            self.setGeometry(self.parentWidget().rect())
        except Exception:
            pass
        self._pos = 0.0
        self._single = single
        self.show()
        self.raise_()
        if not self._tmr.isActive():
            self._tmr.start(30)

    def stop(self) -> None:
        try:
            self._tmr.stop()
        except Exception:
            pass
        self.hide()

    def _step(self):
        try:
            if self.parentWidget() is not None and self.geometry() != self.parentWidget().rect():
                self.setGeometry(self.parentWidget().rect())
        except Exception:
            pass
        self._pos += 0.028
        if self._pos >= 1.0:
            if self._single:
                self.stop()
                return
            self._pos = 0.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        if not p.isActive():
            return
        W, H = self.width(), self.height()
        y = self._pos * H
        # soft blue glow band + bright white core line
        for dy, alpha, color in ((-9, 40, C.PRI), (-5, 90, C.PRI), (-2, 170, C.PRI)):
            p.fillRect(QRectF(0, y + dy, W, 5 if dy == -2 else 4), qcol(color, alpha))
        p.fillRect(QRectF(0, y - 1, W, 2), qcol(C.WHITE, 235))
        p.end()


class _FeatheredCamView(QWidget):
    """Borderless webcam-only window: video with feathered (fading) edges,
    face brackets and a horizontal scan sweep. No panels, no background."""

    def __init__(self, parent=None):
        super().__init__(None)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self._img = QImage()
        self._faces: list[tuple[float, float, float, float]] = []
        self._obj_boxes: list[tuple] = []
        self._gest_boxes: list[tuple] = []
        self._labels: list[tuple] = []
        self._frame_n = 0
        self._had_faces = False
        self._feather = 34
        self._scan = _ScanOverlay(self)
        self.resize(480, 360)
        self.setMinimumSize(240, 180)

    def set_frame(self, px: QPixmap) -> None:
        if px.isNull():
            return
        try:
            target = self.size()
            if target.width() < 8 or target.height() < 8:
                return
            scaled = px.scaled(target, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               Qt.TransformationMode.SmoothTransformation)
            x = max(0, (scaled.width() - target.width()) // 2)
            y = max(0, (scaled.height() - target.height()) // 2)
            self._img = scaled.copy(x, y, target.width(), target.height()).toImage().convertToFormat(
                QImage.Format.Format_ARGB32_Premultiplied)
            self.update()
        except Exception:
            pass

    def set_faces(self, rects) -> None:
        try:
            self._faces = [(float(a), float(b), float(c), float(d)) for (a, b, c, d) in (rects or [])]
            self.update()
        except Exception:
            pass

    def set_scan(self, on: bool, single: bool = False) -> None:
        try:
            if on:
                self._scan.start(single=single)
            else:
                self._scan.stop()
        except Exception:
            pass

    def set_overlay(self, boxes, kind: str = "obj", scan: bool = True) -> None:
        """Add vision detection brackets to the live webcam view.
        boxes: list of (x, y, w, h) normalised rects; kind in {obj, face, hand}."""
        try:
            rects = [(float(a), float(b), float(c), float(d)) for (a, b, c, d) in (boxes or [])]
            if kind == "face":
                self._faces = rects
            else:
                self._objs = rects
            self._overlay_kind = kind
            if scan:
                self.set_scan(True, single=True)
            self.update()
        except Exception:
            pass

    def paintEvent(self, _):
        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self._img.isNull():
            p.drawImage(0, 0, self._img)
        # thin blue glowing stroke (small accent border — no vignette).
        # Glow: a few layered rounded strokes that fade outward.
        W, H = self.width(), self.height()
        r = QRectF(2.0, 2.0, W - 4.0, H - 4.0)
        rad = 16.0
        p.setPen(QPen(QColor(0, 212, 255, 34), 9.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), rad, rad)
        p.setPen(QPen(QColor(0, 212, 255, 90), 5.0))
        p.drawRoundedRect(r, rad, rad)
        p.setPen(QPen(QColor(150, 235, 255, 255), 2.0))
        p.drawRoundedRect(r, rad, rad)
        # thin face brackets (corner marks only — no boxes, no text)
        for (fx, fy, fw, fh) in self._faces:
            x, y, w, h = fx * W, fy * H, fw * W, fh * H
            L = max(10, min(w, h) * 0.28)
            p.setPen(QPen(qcol(C.PRI, 220), 2.0))
            for cx0, cy0, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1),
                                     (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
                p.drawLine(QPointF(cx0, cy0), QPointF(cx0 + dx * L, cy0))
                p.drawLine(QPointF(cx0, cy0), QPointF(cx0, cy0 + dy * L))
        p.end()

    def mousePressEvent(self, e):
        # Right-click closes the webcam view; left-drag is handled by the host.
        if e.button() == Qt.MouseButton.RightButton:
            self.hide()
            e.accept()
            return
        super().mousePressEvent(e)


class _CameraPreview(QWidget):
    """Floating overlay that briefly shows what the camera captured."""

    _W, _H = 244, 188

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            _CameraPreview {{
                background: rgba(0, 6, 10, 242);
                border: 1px solid {C.PRI};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._W)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 5, 6, 6)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        title = QLabel("◈  VISUAL INPUT")
        title.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setFont(QFont("Exo 2", 8))
        close_btn.setStyleSheet(
            f"color: {C.TEXT_DIM}; background: transparent; border: none;"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        self._img_lbl = QLabel()
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(self._img_lbl)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        self._drag_pos = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self.hide()

    # -- draggable: click-drag anywhere on the panel (buttons keep working,
    #    since they consume their own press events before this ever fires) --
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.position().toPoint()
            e.accept(); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + (e.position().toPoint() - self._drag_pos))
            e.accept(); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def show_frame(self, img_bytes: bytes) -> None:
        px = QPixmap()
        px.loadFromData(img_bytes)
        if not px.isNull():
            max_w = self._W - 12
            scaled = px.scaled(
                max_w, 160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._img_lbl.setPixmap(scaled)
            self._img_lbl.setFixedSize(scaled.width(), scaled.height())
            self.adjustSize()
        self.show()
        self.raise_()
        # one blue scan sweep across the capture, then settle
        try:
            if getattr(self, '_scan', None) is None:
                self._scan = _ScanOverlay(self._img_lbl)
            self._scan.start(single=True)
        except Exception:
            pass
        self._timer.start(6_000)   # auto-dismiss after 6 s


class SetupOverlay(QWidget):
    done = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)

        detected = {"darwin": "mac", "windows": "windows"}.get(
            _OS.lower(), "linux"
        )
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(8)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Exo 2", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  INITIALISATION REQUIRED", 13, True))
        layout.addWidget(_lbl("Configure J.A.R.V.I.S. before first boot.", 9, color=C.PRI_DIM))
        layout.addSpacing(6)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont("Exo 2", 10))
        self._key_input.setFixedHeight(32)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(12)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep2)
        layout.addSpacing(4)

        layout.addWidget(_lbl("OPERATING SYSTEM", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        det_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected]
        layout.addWidget(_lbl(f"Auto-detected: {det_name}", 8, color=C.ACC2,
                               align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout(); os_row.setSpacing(6)
        self._os_btns: dict[str, QPushButton] = {}
        for key, label in [("windows","⊞  Windows"),("mac","  macOS"),("linux","🐧  Linux")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        init_btn.setFixedHeight(36)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; border: 1px solid {C.PRI};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _sel(self, key: str):
        self._sel_os = key
        pal = {"windows":(C.PRI,"#001a22"),"mac":(C.ACC2,"#1a1400"),"linux":(C.GREEN,"#001a0d")}
        for k, btn in self._os_btns.items():
            if k == key:
                fg, bg = pal[k]
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {fg}; color: {bg};
                        border: none; border-radius: 3px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #000d12; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 3px;
                    }}
                    QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
                """)

    def _submit(self):
        key = self._key_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(key, self._sel_os)

    # -- draggable: click-drag anywhere on the setup panel background --
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.position().toPoint()
            e.accept(); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if getattr(self, "_drag_pos", None) is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + (e.position().toPoint() - self._drag_pos))
            e.accept(); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)


class HueWheel(QWidget):
    """
    Dairesel renk seçici. Kullanıcı tutamacı (küçük beyaz daire) çarkın
    çevresinde sürükleyerek TÜM renk tonları arasından seçim yapar.
    Merkezdeki dolu daire seçilen rengin canlı önizlemesidir.
    """

    hue_picked    = pyqtSignal(str)   # sürükleme sırasında (canlı)
    hue_committed = pyqtSignal(str)   # tutamaç bırakıldığında

    _RING = 16   # halka kalınlığı (px)

    def __init__(self, initial_hex: str = DEFAULT_UI_COLOR, parent=None):
        super().__init__(parent)
        self.setFixedSize(148, 148)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hue  = 0.53
        self._drag = False
        self.set_color(initial_hex)

    # ── API ──────────────────────────────────────────────────────────────────
    def color(self) -> str:
        return QColor.fromHsvF(self._hue, 1.0, 1.0).name()

    def set_color(self, hex_str: str):
        c = QColor((hex_str or "").strip())
        if c.isValid() and c.hsvHueF() >= 0:
            self._hue = c.hsvHueF()
            self.update()

    # ── geometri yardımcıları ────────────────────────────────────────────────
    def _ring_rect(self) -> QRectF:
        m = self._RING / 2 + 3
        return QRectF(self.rect()).adjusted(m, m, -m, -m)

    def _hue_from_pos(self, pos: QPointF) -> float:
        c  = QRectF(self.rect()).center()
        dx = pos.x() - c.x()
        dy = c.y() - pos.y()          # ekran y'si aşağı — matematiksel eksene çevir
        ang = math.atan2(dy, dx)      # [-π, π], saat yönünün tersi
        return (ang / (2 * math.pi)) % 1.0

    # ── çizim ────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect   = self._ring_rect()
        center = rect.center()

        grad = QConicalGradient(center, 0)
        for i in range(0, 361, 20):
            grad.setColorAt(i / 360.0, QColor.fromHsvF((i % 360) / 360.0, 1.0, 1.0))
        p.setPen(QPen(QBrush(grad), self._RING))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # merkez önizleme dairesi
        preview = QColor.fromHsvF(self._hue, 1.0, 1.0)
        inner   = rect.adjusted(30, 30, -30, -30)
        p.setPen(QPen(qcol(C.BORDER_B), 1))
        p.setBrush(QBrush(preview))
        p.drawEllipse(inner)

        # sürüklenen tutamaç
        r   = rect.width() / 2
        ang = self._hue * 2 * math.pi
        hx  = center.x() + r * math.cos(ang)
        hy  = center.y() - r * math.sin(ang)
        p.setPen(QPen(QColor("#00060a"), 2))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(QPointF(hx, hy), 7.5, 7.5)
        p.end()

    # ── fare ─────────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        self._drag = True
        self._hue  = self._hue_from_pos(e.position())
        self.update()
        self.hue_picked.emit(self.color())

    def mouseMoveEvent(self, e):
        if self._drag:
            self._hue = self._hue_from_pos(e.position())
            self.update()
            self.hue_picked.emit(self.color())

    def mouseReleaseEvent(self, e):
        if self._drag:
            self._drag = False
            self.hue_committed.emit(self.color())


class CustomizeOverlay(QWidget):
    """Floating overlay — change assistant name, user name, UI colour and voice."""

    saved = pyqtSignal(str, str, str, str)   # assistant_name, user_name, ui_color, voice
    _OW, _OH = 400, 588

    def __init__(self, assistant_name="JARVIS", user_name="",
                 ui_color=DEFAULT_UI_COLOR, voice="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            CustomizeOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(8)

        def _lbl(txt, fs=9, bold=False, color=C.PRI, align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt); w.setAlignment(align)
            w.setFont(QFont("Exo 2", fs,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        _fs = (f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
               f"border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px; }}"
               f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}")

        lay.addWidget(_lbl("⚙  CUSTOMISE ASSISTANT", 12, True))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)

        lay.addWidget(_lbl("ASSISTANT NAME", 8, color=C.TEXT_DIM,
                            align=Qt.AlignmentFlag.AlignLeft))
        self._name_input = QLineEdit(assistant_name)
        self._name_input.setFont(QFont("Exo 2", 10))
        self._name_input.setFixedHeight(32)
        self._name_input.setStyleSheet(_fs)
        lay.addWidget(self._name_input)

        lay.addSpacing(4)
        lay.addWidget(_lbl("YOUR NAME  (leave blank for default sir / efendim)", 8,
                            color=C.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
        self._user_input = QLineEdit(user_name)
        self._user_input.setPlaceholderText("e.g.  Tony   (leave blank for auto)")
        self._user_input.setFont(QFont("Exo 2", 10))
        self._user_input.setFixedHeight(32)
        self._user_input.setStyleSheet(_fs)
        lay.addWidget(self._user_input)

        # ── Assistant voice — Gemini prebuilt voices ─────────────────────────
        # Names are language-neutral proper nouns, so the row reads the same in
        # every locale. Selecting one and applying rebuilds the Live session.
        from memory.config_manager import AVAILABLE_VOICES, DEFAULT_VOICE
        lay.addSpacing(4)
        lay.addWidget(_lbl("ASSISTANT VOICE", 8, color=C.TEXT_DIM,
                            align=Qt.AlignmentFlag.AlignLeft))
        self._sel_voice   = (voice or DEFAULT_VOICE)
        if self._sel_voice not in AVAILABLE_VOICES:
            self._sel_voice = DEFAULT_VOICE
        self._voice_btns: dict[str, QPushButton] = {}
        voice_row = QHBoxLayout(); voice_row.setSpacing(4)
        for _v in AVAILABLE_VOICES:
            b = QPushButton(_v)
            b.setCheckable(True)
            b.setFixedHeight(28)
            b.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, name=_v: self._on_voice_pick(name))
            self._voice_btns[_v] = b
            voice_row.addWidget(b)
        lay.addLayout(voice_row)
        self._refresh_voice_btns()

        # ── UI colour — renk çarkı ───────────────────────────────────────────
        lay.addSpacing(4)
        clr_hdr = QHBoxLayout()
        clr_hdr.addWidget(_lbl("UI COLOUR  —  drag the handle", 8,
                               color=C.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
        clr_hdr.addStretch()
        df_btn = QPushButton("DEFAULT")
        df_btn.setFixedSize(64, 20)
        df_btn.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        df_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        df_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        df_btn.clicked.connect(lambda: self._set_color(DEFAULT_UI_COLOR))
        clr_hdr.addWidget(df_btn)
        lay.addLayout(clr_hdr)

        self._initial_color = (ui_color or DEFAULT_UI_COLOR).strip().lower()
        self._sel_color     = self._initial_color
        self.on_preview     = None   # callable(hex) — canlı önizleme; MainWindow bağlar

        self._wheel = HueWheel(self._sel_color)
        wheel_row = QHBoxLayout()
        wheel_row.addStretch(); wheel_row.addWidget(self._wheel); wheel_row.addStretch()
        lay.addLayout(wheel_row)
        self._wheel.hue_picked.connect(self._on_wheel_pick)
        self._wheel.hue_committed.connect(self._on_wheel_commit)

        self._hex_input = QLineEdit(self._sel_color)
        self._hex_input.setPlaceholderText("#00d4ff   (custom hex colour)")
        self._hex_input.setFont(QFont("Exo 2", 10))
        self._hex_input.setFixedHeight(28)
        self._hex_input.setStyleSheet(_fs)
        self._hex_input.textEdited.connect(self._on_hex_edited)
        lay.addWidget(self._hex_input)

        lay.addSpacing(6)
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)

        save_btn = QPushButton("▸  APPLY CHANGES")
        save_btn.setFixedHeight(34)
        save_btn.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFont(QFont("Exo 2", 9))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

    # ── ses seçimi ───────────────────────────────────────────────────────────
    def _on_voice_pick(self, name: str):
        self._sel_voice = name
        self._refresh_voice_btns()

    def _refresh_voice_btns(self):
        """Highlight the selected voice pill; dim the rest."""
        for name, b in self._voice_btns.items():
            on = (name == self._sel_voice)
            b.setChecked(on)
            if on:
                b.setStyleSheet(f"""
                    QPushButton {{ background: {C.PRI_GHO}; color: {C.PRI};
                        border: 1px solid {C.PRI}; border-radius: 3px; }}
                """)
            else:
                b.setStyleSheet(f"""
                    QPushButton {{ background: transparent; color: {C.TEXT_MED};
                        border: 1px solid {C.BORDER}; border-radius: 3px; }}
                    QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
                """)

    # ── renk akışı ───────────────────────────────────────────────────────────
    def _set_color(self, hx: str, update_wheel: bool = True, preview: bool = True):
        """Seçili rengi günceller; hex kutusu + çark senkron kalır, tema canlı önizlenir."""
        self._sel_color = hx.strip().lower()
        self._hex_input.blockSignals(True)
        self._hex_input.setText(self._sel_color)
        self._hex_input.blockSignals(False)
        if update_wheel:
            self._wheel.set_color(self._sel_color)
        if preview and self.on_preview:
            self.on_preview(self._sel_color)

    def _on_wheel_pick(self, hx: str):
        # Sürükleme sırasında: hex kutusunu güncelle, temayı henüz uygulama
        self._sel_color = hx
        self._hex_input.blockSignals(True)
        self._hex_input.setText(hx)
        self._hex_input.blockSignals(False)

    def _on_wheel_commit(self, hx: str):
        # Tutamaç bırakıldı → tüm arayüzü canlı önizle
        self._set_color(hx, update_wheel=False)

    def _on_hex_edited(self, text: str):
        t = text.strip().lower()
        if t.startswith("#") and len(t) == 7:
            try:
                int(t[1:], 16)
            except ValueError:
                return
            self._set_color(t, update_wheel=True, preview=True)

    def _cancel(self):
        # Önizleme uygulandıysa açılıştaki renge geri dön
        if self.on_preview and self._sel_color != self._initial_color:
            self.on_preview(self._initial_color)
        self.hide()

    def _save(self):
        name = self._name_input.text().strip() or "JARVIS"
        user = self._user_input.text().strip()
        self.saved.emit(name, user, self._sel_color or DEFAULT_UI_COLOR, self._sel_voice)
        self.hide()


class PluginManagerOverlay(QWidget):
    """Floating overlay — lists discovered plugins with per-plugin ON/OFF toggles."""

    _OW = 420

    def __init__(self, plugins: list[dict], parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            PluginManagerOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._OW)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(6)

        hdr = QLabel("🧩  PLUGIN MANAGER")
        hdr.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        lay.addWidget(hdr)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)

        if not plugins:
            empty = QLabel("No plugins found in /plugins.")
            empty.setFont(QFont("Exo 2", 8))
            empty.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
            lay.addWidget(empty)

        for p in plugins:
            lay.addLayout(self._build_row(p))

        lay.addSpacing(4)
        close_btn = QPushButton("CLOSE")
        close_btn.setFixedHeight(30)
        close_btn.setFont(QFont("Exo 2", 9))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        close_btn.clicked.connect(self.hide)
        lay.addWidget(close_btn)
        self.adjustSize()

    def _build_row(self, p: dict) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(6)

        label_text = p["name"] if p["valid"] else f"{p['name']}  (⚠ {p['file']})"
        lbl = QLabel(label_text)
        lbl.setFont(QFont("Exo 2", 8))
        lbl.setStyleSheet(f"color: {C.TEXT if p['valid'] else C.TEXT_DIM}; background: transparent;")
        lbl.setToolTip(p["description"] if p["valid"] else p["error"])
        lbl.setWordWrap(False)
        row.addWidget(lbl, stretch=1)

        btn = QPushButton()
        btn.setFixedSize(72, 24)
        btn.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        if not p["valid"]:
            btn.setText("BROKEN")
            btn.setEnabled(False)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.TEXT_DIM};
                    border: 1px solid {C.BORDER}; border-radius: 3px;
                }}
            """)
        else:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._style_toggle(btn, p["enabled"])
            btn.clicked.connect(lambda _, name=p["name"], b=btn: self._toggle(name, b))
        row.addWidget(btn)
        return row

    def _style_toggle(self, btn: QPushButton, enabled: bool):
        if enabled:
            btn.setText("ON")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #001a08; color: {C.GREEN};
                    border: 1px solid {C.GREEN_D}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #002010; }}
            """)
        else:
            btn.setText("OFF")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.TEXT_DIM};
                    border: 1px solid {C.BORDER}; border-radius: 3px;
                }}
                QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
            """)

    def _toggle(self, name: str, btn: QPushButton):
        from memory.config_manager import get_plugin_enabled, save_plugin_enabled
        new_val = not get_plugin_enabled(name)
        save_plugin_enabled(name, new_val)
        self._style_toggle(btn, new_val)


class _HudOverlay(QWidget):
    """Base for the floating panels placed by hand over the HUD.

    They are children of the central widget but sit in no layout, so Qt never
    invalidates the region they occupy when they hide or shrink: the HUD keeps
    painting around them and their last frame stays on screen as a ghost. Any
    overlay positioned with _centre_overlay needs this."""

    def hideEvent(self, e):
        p = self.parentWidget()
        if p is not None:
            # Repaint exactly what we were covering, before we stop covering it.
            p.update(self.geometry())
        super().hideEvent(e)

    def closeEvent(self, e):
        p = self.parentWidget()
        if p is not None:
            p.update(self.geometry())
        super().closeEvent(e)


class ConfirmBanner(_HudOverlay):
    """The gate in front of an action that cannot be taken back.

    The old confirmation was a tool parameter the model filled in itself, which
    means it confirmed its own shutdown requests. This is the interface asking,
    and the answer travels from a human finger to core/confirm.py without the
    model in the loop. Nothing blocks while it is up: the assistant keeps
    talking, so this costs no latency — unlike the old gate, which spent two
    tool round trips on every power command."""

    answered = pyqtSignal(bool)
    _OW = 430

    def __init__(self, title: str, detail: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ConfirmBanner {{
                background: rgba(14, 3, 0, 250);
                border: 1px solid {C.ACC};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._OW)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)

        hdr = QLabel("⚠  CONFIRM")
        hdr.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.ACC}; background: transparent;")
        lay.addWidget(hdr)

        ttl = QLabel(title)
        ttl.setWordWrap(True)
        ttl.setFont(QFont("Exo 2", 10, QFont.Weight.Bold))
        ttl.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
        lay.addWidget(ttl)

        if detail:
            dtl = QLabel(detail)
            dtl.setWordWrap(True)
            dtl.setFont(QFont("Exo 2", 8))
            dtl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            lay.addWidget(dtl)

        row = QHBoxLayout(); row.setSpacing(8)

        yes = QPushButton("▸  CONFIRM")
        yes.setFixedHeight(32)
        yes.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        yes.setCursor(Qt.CursorShape.PointingHandCursor)
        yes.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.ACC};
                border: 1px solid {C.ACC}; border-radius: 3px; }}
            QPushButton:hover {{ background: rgba(255,107,0,40); }}
        """)
        yes.clicked.connect(lambda: self.answered.emit(True))
        row.addWidget(yes)

        no = QPushButton("CANCEL")
        no.setFixedHeight(32)
        no.setFont(QFont("Exo 2", 9))
        no.setCursor(Qt.CursorShape.PointingHandCursor)
        no.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px; }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        no.clicked.connect(lambda: self.answered.emit(False))
        row.addWidget(no)
        lay.addLayout(row)

        # Default focus on CANCEL: if someone hits Enter without reading, the
        # safe answer wins.
        no.setDefault(True)
        no.setFocus()


class AudioDeviceOverlay(_HudOverlay):
    """Choose which microphone JARVIS listens to and which speakers it uses.

    Both audio streams used to open with no `device=` at all, so they always
    took the OS default — which on Windows moves by itself the moment a headset
    is plugged in. 'JARVIS can't hear me' is usually 'JARVIS is listening to the
    webcam'."""

    picked = pyqtSignal()      # emitted after Apply, when something changed
    _OW = 460

    def __init__(self, parent=None):
        super().__init__(parent)
        from core.audio_devices import list_devices, DEFAULT_LABEL
        from memory.config_manager import get_input_device, get_output_device

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            AudioDeviceOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._OW)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(6)

        hdr = QLabel("🎧  AUDIO DEVICES")
        hdr.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        lay.addWidget(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)

        _combo_css = (
            f"QComboBox {{ background: #000d12; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px; }}"
            f"QComboBox:hover {{ border-color: {C.BORDER_B}; }}"
            f"QComboBox QAbstractItemView {{ background: #000d12; color: {C.TEXT}; "
            f"selection-background-color: {C.PRI_GHO}; border: 1px solid {C.BORDER}; }}"
        )

        def _row(label: str, kind: str, current: str) -> QComboBox:
            cap = QLabel(label)
            cap.setFont(QFont("Exo 2", 8))
            cap.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
            lay.addWidget(cap)

            box = QComboBox()
            box.setFont(QFont("Exo 2", 9))
            box.setFixedHeight(30)
            box.setStyleSheet(_combo_css)
            # The list is served from a cache warmed on a background thread at
            # startup, so opening this panel never blocks the Qt thread on the
            # host audio API.
            box.addItem(DEFAULT_LABEL, "")
            for name in list_devices(kind):
                box.addItem(name, name)
            idx = box.findData(current) if current else 0
            box.setCurrentIndex(idx if idx >= 0 else 0)
            if current and idx < 0:
                # Saved device is not plugged in right now. Show it rather than
                # silently resetting the user's choice to default.
                box.addItem(f"{current}  (not connected)", current)
                box.setCurrentIndex(box.count() - 1)
            lay.addWidget(box)
            return box

        self._in_box  = _row("MICROPHONE — what JARVIS hears you with",
                             "input", get_input_device())
        lay.addSpacing(4)
        self._out_box = _row("SPEAKERS — what JARVIS talks through",
                             "output", get_output_device())

        note = QLabel("Applying reconnects the session. Your conversation is kept.")
        note.setWordWrap(True)
        note.setFont(QFont("Exo 2", 7))
        note.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        lay.addSpacing(6)
        lay.addWidget(note)

        row = QHBoxLayout(); row.setSpacing(8)
        ok = QPushButton("▸  APPLY")
        ok.setFixedHeight(32)
        ok.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        ok.setCursor(Qt.CursorShape.PointingHandCursor)
        ok.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px; }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border-color: {C.PRI}; }}
        """)
        ok.clicked.connect(self._apply)
        row.addWidget(ok)

        cancel = QPushButton("CLOSE")
        cancel.setFixedHeight(32)
        cancel.setFont(QFont("Exo 2", 9))
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px; }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        cancel.clicked.connect(self.hide)
        row.addWidget(cancel)
        lay.addLayout(row)

    def _apply(self):
        from memory.config_manager import (
            get_input_device, get_output_device,
            save_input_device, save_output_device,
        )
        new_in  = self._in_box.currentData()  or ""
        new_out = self._out_box.currentData() or ""
        changed = (new_in != get_input_device()) or (new_out != get_output_device())
        save_input_device(new_in)
        save_output_device(new_out)
        self.hide()
        # Only rebuild the session if something actually moved — a no-op Apply
        # should not cost a reconnect.
        if changed:
            self.picked.emit()


class MemoryOverlay(_HudOverlay):
    """Everything JARVIS has stored about you, and when it learned it.

    Memory used to be a 2200-character store that deleted its oldest entries
    when full and mentioned it only on stdout. The cap is gone; this panel is
    the other half of that change — a memory you cannot inspect is a memory you
    cannot trust, and 'delete' has to be something the person can do."""

    _OW = 520

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            MemoryOverlay {{
                background: rgba(0, 6, 10, 246);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._OW)

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(20, 16, 20, 16)
        self._lay.setSpacing(5)
        self._rebuild()

    def _clear_layout(self):
        """Take every item out of the layout and detach it from the widget tree
        in this call.

        deleteLater() on its own is not enough: it queues destruction for the
        next event-loop pass, and until then the old rows are still children of
        this widget and still paint — which is what drew half of the previous
        panel over the new one. setParent(None) removes them from the tree now;
        deleteLater() then frees them safely."""
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                # hide() stops it painting in this frame; deleteLater() frees it
                # safely afterwards. setParent(None) would also stop the paint,
                # but it turns the widget into a top-level window for the moment
                # between the two calls, which is not something to leave lying
                # around inside a click handler.
                w.hide()
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                while sub.count():
                    si = sub.takeAt(0)
                    sw = si.widget()
                    if sw is not None:
                        sw.hide()
                        sw.deleteLater()
                sub.deleteLater()

    def _settle(self, before):
        """Size the panel to its content, re-centre it, and repaint what the old
        size covered.

        The re-size has to happen here rather than at the end of _rebuild
        because Qt has not polished the freshly-created children at that point,
        so the size hint it would read is the empty-layout one. Measured: a
        first adjustSize() returned 32 px for a panel whose content needed 155,
        and a second call — after the same widgets had been through the event
        loop — returned 155. So this runs twice: once now, once on the next
        turn, from _rebuild.

        The re-centre and the repaint are needed because the overlay is placed
        by hand and is in no layout: shrinking it leaves it off-centre and
        leaves its former pixels on screen, since nothing tells the parent that
        region changed. The repaint has to cover the union of the old and new
        rectangles."""
        self._lay.invalidate()
        self._lay.activate()
        self.updateGeometry()
        self.adjustSize()

        p = self.parentWidget()
        if p is None:
            self.update()
            return
        self.move(max(0, (p.width()  - self.width())  // 2),
                  max(0, (p.height() - self.height()) // 2))
        p.update(before.united(self.geometry()))
        self.update()

    def _rebuild(self):
        before = self.geometry()
        self._clear_layout()

        from memory.memory_manager import all_entries_for_ui

        hdr = QLabel("🧠  WHAT JARVIS REMEMBERS")
        hdr.setFont(QFont("Exo 2", 12, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._lay.addWidget(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        self._lay.addWidget(sep)

        rows = all_entries_for_ui()

        cap = QLabel(f"{len(rows)} stored facts — newest first. "
                     f"Nothing here is sent anywhere; it lives in "
                     f"memory/long_term.json on this machine.")
        cap.setWordWrap(True)
        cap.setFont(QFont("Exo 2", 7))
        cap.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._lay.addWidget(cap)

        if not rows:
            empty = QLabel("Nothing stored yet.")
            empty.setFont(QFont("Exo 2", 9))
            empty.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            self._lay.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFixedHeight(min(420, 34 * len(rows) + 10))
            scroll.setStyleSheet(
                f"QScrollArea {{ border: 1px solid {C.BORDER}; border-radius: 3px; "
                f"background: transparent; }}"
            )
            inner = QWidget()
            ilay  = QVBoxLayout(inner)
            ilay.setContentsMargins(6, 6, 6, 6)
            ilay.setSpacing(3)

            for r in rows:
                line = QHBoxLayout(); line.setSpacing(6)
                txt = QLabel(f"<b>{r['key'].replace('_', ' ')}</b> "
                             f"<span style='color:{C.TEXT_MED}'>— {r['value']}</span>")
                txt.setWordWrap(True)
                txt.setFont(QFont("Exo 2", 8))
                txt.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
                line.addWidget(txt, 1)

                meta = QLabel(f"{r['category'][:4]} · {r['updated'] or '—'}")
                meta.setFont(QFont("Exo 2", 7))
                meta.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
                line.addWidget(meta)

                rm = QPushButton("✕")
                rm.setFixedSize(20, 20)
                rm.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
                rm.setCursor(Qt.CursorShape.PointingHandCursor)
                rm.setToolTip("Forget this")
                rm.setStyleSheet(f"""
                    QPushButton {{ background: transparent; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 3px; }}
                    QPushButton:hover {{ color: {C.RED}; border-color: {C.RED}; }}
                """)
                rm.clicked.connect(
                    lambda _=False, c=r["category"], k=r["key"]: self._forget(c, k))
                line.addWidget(rm)

                holder = QWidget()
                holder.setLayout(line)
                ilay.addWidget(holder)

            ilay.addStretch()
            scroll.setWidget(inner)
            self._lay.addWidget(scroll)

        close = QPushButton("CLOSE")
        close.setFixedHeight(30)
        close.setFont(QFont("Exo 2", 9))
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px; }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        close.clicked.connect(self.hide)
        self._lay.addWidget(close)

        self._settle(before)
        # …and again once Qt has polished the new children, because the size
        # hint is not final until then. Harmless when the first pass already
        # got it right: _settle is idempotent.
        QTimer.singleShot(0, lambda g=before: self._settle(g))

    def _forget(self, category: str, key: str):
        from memory.memory_manager import forget
        forget(key, category)
        # Rebuild on the NEXT event-loop turn, not inside this click handler.
        # The rebuild destroys the very ✕ button that emitted this signal, and
        # Qt is entitled to touch the sender after a slot returns; tearing it
        # down mid-emission is how a widget ends up half-alive on screen.
        QTimer.singleShot(0, self._rebuild)


class ClipboardPanel(QWidget):
    """Floating panel shown when text is copied — offers quick Jarvis actions."""

    action_requested = pyqtSignal(str)
    _W, _H = 326, 112

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ClipboardPanel {{
                background: rgba(0, 8, 14, 248);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._W)
        self._clip_text = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 7)
        lay.setSpacing(4)

        hdr = QHBoxLayout(); hdr.setSpacing(4)
        icon_lbl = QLabel("◈  CLIPBOARD DETECTED")
        icon_lbl.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        icon_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent;")
        hdr.addWidget(icon_lbl); hdr.addStretch()
        x_btn = QPushButton("✕")
        x_btn.setFixedSize(16, 16)
        x_btn.setFont(QFont("Exo 2", 8))
        x_btn.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        x_btn.clicked.connect(self.hide)
        hdr.addWidget(x_btn)
        lay.addLayout(hdr)

        self._preview = QLabel()
        self._preview.setFont(QFont("Exo 2", 8))
        self._preview.setStyleSheet(f"""
            color: {C.TEXT}; background: {C.PANEL2};
            border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 6px;
        """)
        self._preview.setWordWrap(False)
        self._preview.setFixedHeight(28)
        lay.addWidget(self._preview)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        _bs = (f"QPushButton {{ background: {C.PANEL2}; color: {C.TEXT_MED}; "
               f"border: 1px solid {C.BORDER}; border-radius: 2px; }}"
               f"QPushButton:hover {{ color: {C.PRI}; border-color: {C.BORDER_B}; }}")
        for label, cmd_fmt in [
            ("TRANSLATE", "Translate this text to English: {text}"),
            ("SUMMARISE", "Summarise this: {text}"),
            ("EXPLAIN",   "Explain this: {text}"),
            ("FIX",       "Fix grammar and spelling: {text}"),
        ]:
            b = QPushButton(label)
            b.setFixedHeight(22)
            b.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(_bs)
            b.clicked.connect(lambda _, c=cmd_fmt: self._trigger(c))
            btn_row.addWidget(b)
        lay.addLayout(btn_row)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.hide)
        self._drag_pos = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.hide()

    # -- draggable: click-drag anywhere on the panel background --
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.position().toPoint()
            e.accept(); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + (e.position().toPoint() - self._drag_pos))
            e.accept(); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def _trigger(self, cmd_fmt: str):
        if self._clip_text:
            self.action_requested.emit(cmd_fmt.format(text=self._clip_text[:800]))
        self.hide()

    def show_clipboard(self, text: str):
        self._clip_text = text
        preview = text[:58].replace('\n', ' ')
        if len(text) > 58:
            preview += "…"
        self._preview.setText(f'"{preview}"')
        self.show(); self.raise_()
        self._dismiss_timer.start(8000)


class RemoteKeyOverlay(QWidget):
    """Floating overlay — QR code for instant phone pairing + manual key fallback."""

    closed = pyqtSignal()

    _OW, _OH = 400, 465

    def __init__(self, url: str, key: str, auto_login_url: str = "",
                 manual_url: str = "", expiry_secs: int = 600, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            RemoteKeyOverlay {{
                background: rgba(0, 4, 12, 0.95);
                border: 1px solid {C.BORDER_B};
                border-radius: 3px;
            }}
        """)
        self._expiry          = time.time() + expiry_secs
        self._on_new_key      = None
        self._auto_login_url  = auto_login_url
        self._manual_url      = manual_url or url

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(5)

        def _lbl(txt, fs=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Exo 2", fs,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            w.setWordWrap(True)
            return w

        lay.addWidget(_lbl("◈  REMOTE ACCESS", 12, True))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 1px 0;")
        lay.addWidget(sep)

        # ── QR code ───────────────────────────────────────────────────────────
        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setFixedSize(176, 176)
        self._qr_label.setStyleSheet(
            "background: white; border-radius: 3px; padding: 4px;"
        )
        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(self._qr_label)
        qr_row.addStretch()
        lay.addLayout(qr_row)

        self._update_qr(auto_login_url)

        lay.addWidget(_lbl("Scan with phone camera to connect instantly", 8, color=C.TEXT_DIM))

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER}; margin: 1px 0;")
        lay.addWidget(sep2)

        lay.addWidget(_lbl("Or enter manually:", 7, color=C.TEXT_DIM,
                           align=Qt.AlignmentFlag.AlignLeft))

        self._url_lbl = QLabel(self._manual_url)
        self._url_lbl.setFont(QFont("Exo 2", 8))
        self._url_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        self._url_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._url_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self._url_lbl)

        self._key_lbl = QLabel(key)
        self._key_lbl.setFont(QFont("Orbitron", 28, QFont.Weight.Bold))
        self._key_lbl.setStyleSheet(f"""
            color: {C.ACC};
            background: {C.PANEL2};
            border: 1px solid {C.BORDER_B};
            border-radius: 2px;
            padding: 6px 4px;
            letter-spacing: 10px;
        """)
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._key_lbl)

        self._timer_lbl = QLabel()
        self._timer_lbl.setFont(QFont("Exo 2", 8))
        self._timer_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._timer_lbl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        new_btn = QPushButton("NEW KEY")
        new_btn.setFixedHeight(32)
        new_btn.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 5px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        new_btn.clicked.connect(self._refresh_key)
        btn_row.addWidget(new_btn)

        close_btn = QPushButton("DISMISS")
        close_btn.setFixedHeight(32)
        close_btn.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 5px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
        """)
        close_btn.clicked.connect(self._do_close)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        self._ctimer = QTimer(self)
        self._ctimer.timeout.connect(self._tick)
        self._ctimer.start(1000)
        self._tick()

    def set_new_key_callback(self, fn) -> None:
        self._on_new_key = fn

    def _update_qr(self, url: str) -> None:
        if not url:
            self._qr_label.setText("—")
            return
        try:
            import qrcode as _qrmod
            from io import BytesIO
            qr = _qrmod.QRCode(
                box_size=5, border=2,
                error_correction=_qrmod.constants.ERROR_CORRECT_M,
            )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap()
            px.loadFromData(buf.getvalue())
            self._qr_label.setPixmap(
                px.scaled(170, 170,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
            )
        except ImportError:
            self._qr_label.setText("pip install\nqrcode[pil]")
            self._qr_label.setFont(QFont("Exo 2", 8))
            self._qr_label.setStyleSheet(
                "color: #888; background: white; border-radius: 3px; padding: 4px;"
            )
        except Exception:
            self._qr_label.setText(url[:28])
            self._qr_label.setFont(QFont("Exo 2", 7))
            self._qr_label.setStyleSheet(
                f"color: {C.PRI}; background: white; border-radius: 3px; padding: 4px;"
            )

    def _tick(self):
        remaining = max(0, int(self._expiry - time.time()))
        m, s = divmod(remaining, 60)
        self._timer_lbl.setText(f"Key expires in  {m:02d}:{s:02d}")
        if remaining == 0:
            self._do_close()

    def mark_connected(self) -> None:
        """Call from any thread when a phone successfully connects."""
        self._ctimer.stop()
        self._key_lbl.setText("CONNECTED")
        self._key_lbl.setStyleSheet(f"""
            color: {C.GREEN};
            background: rgba(34,197,94,0.08);
            border: 2px solid rgba(34,197,94,0.4);
            border-radius: 2px;
            padding: 6px 4px;
            letter-spacing: 4px;
        """)
        self._qr_label.setText("✓")
        self._qr_label.setFont(QFont("Orbitron", 54, QFont.Weight.Bold))
        self._qr_label.setStyleSheet(
            "color: #00ff88; background: #001a0d; border-radius: 3px;"
        )
        self._timer_lbl.setText("Phone connected — JARVIS ready")
        self._timer_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")

    def _refresh_key(self):
        if self._on_new_key:
            result = self._on_new_key()
            if result:
                url    = result[0]
                key    = result[1]
                auto   = result[2] if len(result) >= 3 else ""
                manual = result[3] if len(result) >= 4 else url
                self._manual_url     = manual or url
                self._url_lbl.setText(self._manual_url)
                self._key_lbl.setText(key)
                self._auto_login_url = auto
                self._update_qr(auto or url)
                self._expiry = time.time() + 600
                self._key_lbl.setStyleSheet(f"""
                    color: {C.ACC};
                    background: {C.PANEL2};
                    border: 1px solid {C.BORDER_B};
                    border-radius: 2px;
                    padding: 6px 4px;
                    letter-spacing: 10px;
                """)
                self._timer_lbl.setStyleSheet(
                    f"color: {C.TEXT_MED}; background: transparent;"
                )
                self._ctimer.start(1000)
                self._tick()

    def _do_close(self):
        self._ctimer.stop()
        self.hide()
        self.closed.emit()


class LegacyMainWindow(QMainWindow):
    _log_sig        = pyqtSignal(str)
    _state_sig      = pyqtSignal(str)
    _content_sig    = pyqtSignal(str, str)   # (title, text) — thread-safe content display
    _reconfig_sig   = pyqtSignal()           # trigger setup overlay from any thread
    _camera_sig     = pyqtSignal(bytes)      # show camera frame preview (small overlay)
    _cam_stream_sig = pyqtSignal(bool)       # True=start live stream, False=stop
    _cam_frame_sig  = pyqtSignal(bytes)      # live camera frame → HUD area
    _clipboard_sig  = pyqtSignal(str)        # clipboard text changed (thread-safe)
    _confirm_sig    = pyqtSignal(str, str)   # (title, detail) — irreversible-action gate
    _confirm_hide_sig = pyqtSignal()

    def __init__(self, face_path: str):
        super().__init__()
        self._face_path = face_path

        # Load customization from config
        _cfg = _read_full_config()
        self._assistant_name: str = (_cfg.get("assistant_name") or "JARVIS").strip()
        _display = self._assistant_name.upper()

        # Kayıtlı UI rengini panel/stylesheet'ler kurulmadan ÖNCE uygula
        _ui_color = (_cfg.get("ui_color") or "").strip()
        if _ui_color and _ui_color.lower() != DEFAULT_UI_COLOR:
            apply_ui_accent(_ui_color)

        self.setWindowTitle(f"{_display} — MARK LII")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self.on_text_command   = None
        self.on_remote_clicked = None   # callable: () -> (url, key) | None
        self.on_interrupt      = None   # callable: () -> None — stop JARVIS mid-speech
        self.on_voice_change   = None   # callable: () -> None — rebuild session with new voice
        self.on_audio_device_change = None  # callable: () -> None — reopen audio streams
        self._confirm_overlay  = None   # live ConfirmBanner, if one is on screen
        self.get_plugins       = None   # callable: () -> list[dict], set by JarvisLive
        self._muted            = False
        self._current_file: str | None = None
        self._remote_overlay: RemoteKeyOverlay | None = None
        self._customize_overlay: CustomizeOverlay | None = None

        central = QWidget()
        central.setStyleSheet("background: rgba(0, 6, 10, 128);")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._left_panel = self._build_left_panel()
        body.addWidget(self._left_panel, stretch=0)

        # Center column: HUD + resizable content panel via QSplitter
        self.hud = HudCanvas(face_path, _display)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._content_panel = self._build_content_panel()

        # Live camera container — replaces HUD when camera stream is active
        _cam_cont = QWidget()
        _cam_cont.setStyleSheet("background: #000308;")
        _cam_v = QVBoxLayout(_cam_cont)
        _cam_v.setContentsMargins(0, 0, 0, 0)
        _cam_v.setSpacing(0)
        _cam_hdr = QHBoxLayout()
        _cam_hdr.setContentsMargins(8, 5, 8, 5)
        _cam_title = QLabel("◈  CAMERA FEED")
        _cam_title.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        _cam_title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        _cam_hdr.addWidget(_cam_title)
        _cam_hdr.addStretch()
        _cam_x = QPushButton("✕  CLOSE")
        _cam_x.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        _cam_x.setCursor(Qt.CursorShape.PointingHandCursor)
        _cam_x.setStyleSheet(f"""
            QPushButton {{
                color: {C.TEXT_DIM}; background: transparent;
                border: none; padding: 2px 6px;
            }}
            QPushButton:hover {{ color: {C.PRI}; }}
        """)
        _cam_x.clicked.connect(self.stop_camera_stream)
        _cam_hdr.addWidget(_cam_x)
        _cam_v.addLayout(_cam_hdr)
        self._cam_live_lbl = QLabel()
        self._cam_live_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_live_lbl.setStyleSheet("background: transparent;")
        self._cam_live_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        _cam_v.addWidget(self._cam_live_lbl, stretch=1)

        # Stack: 0 = animated HUD, 1 = live camera
        self._hud_cam_stack = QStackedWidget()
        self._hud_cam_stack.addWidget(self.hud)
        self._hud_cam_stack.addWidget(_cam_cont)

        self._center_split = QSplitter(Qt.Orientation.Vertical)
        self._center_split.setStyleSheet(f"""
            QSplitter::handle {{
                background: {C.BORDER};
                height: 4px;
            }}
            QSplitter::handle:hover {{
                background: {C.PRI_DIM};
            }}
        """)
        self._center_split.addWidget(self._hud_cam_stack)
        self._center_split.addWidget(self._content_panel)
        self._center_split.setStretchFactor(0, 3)
        self._center_split.setStretchFactor(1, 1)
        self._center_split.setCollapsible(0, False)
        body.addWidget(self._center_split, stretch=5)

        self._right_panel = self._build_right_panel()
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())

        # Quick-access drawer (floating overlay, built after central widget layout is done)
        self._quick_drawer = self._build_quick_drawer()
        self._update_autostart_btn(self._check_autostart())
        from memory.config_manager import get_brief_enabled as _gbe
        self._update_brief_btn(_gbe())

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        # Metrik güncelleme timer'ı
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._content_sig.connect(self._show_content)
        self._reconfig_sig.connect(self._show_setup)
        self._camera_sig.connect(self._show_camera_frame)
        self._confirm_sig.connect(self._show_confirm_banner)
        self._confirm_hide_sig.connect(self._hide_confirm_banner)
        self._cam_stream_sig.connect(self._on_cam_stream)
        self._cam_frame_sig.connect(self._on_cam_frame)
        self._clipboard_sig.connect(self._show_clipboard_panel)
        self._cam_stop = threading.Event()

        # Camera preview overlay (child of central widget, positioned in resizeEvent)
        self._cam_preview = _CameraPreview(self.centralWidget())

        # Clipboard panel (child of central widget, bottom-center)
        self._clipboard_panel = ClipboardPanel(self.centralWidget())
        self._clipboard_panel.action_requested.connect(self._on_clipboard_action)
        QApplication.clipboard().dataChanged.connect(self._on_clipboard_changed)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_intr = QShortcut(QKeySequence("Escape"), self)
        sc_intr.activated.connect(self._do_interrupt)

    def _show_camera_frame(self, img_bytes: bytes):
        """Slot — display camera preview overlay (main thread)."""
        self._cam_preview.show_frame(img_bytes)
        cw = self.centralWidget()
        pw = _CameraPreview._W
        ph = self._cam_preview.height()
        self._cam_preview.setGeometry(
            cw.width() - _RIGHT_W - pw - 12,
            cw.height() - ph - 28,
            pw, ph,
        )

    # --- Live camera stream in HUD area ------------------------------------
    def _on_cam_stream(self, start: bool) -> None:
        if start:
            self._hud_cam_stack.setCurrentIndex(1)
        else:
            self._hud_cam_stack.setCurrentIndex(0)
            self._cam_live_lbl.clear()

    def _on_cam_frame(self, data: bytes) -> None:
        px = QPixmap()
        px.loadFromData(data)
        if not px.isNull():
            w, h = self._cam_live_lbl.width(), self._cam_live_lbl.height()
            if w > 1 and h > 1:
                self._cam_live_lbl.setPixmap(
                    px.scaled(w, h,
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
                )

    def start_camera_stream(self) -> None:
        self._cam_stop.clear()
        self._cam_stream_sig.emit(True)
        t = threading.Thread(target=self._cam_loop, daemon=True, name="cam-stream")
        t.start()

    def _cam_loop(self) -> None:
        try:
            import cv2
            # Reuse camera index detected by screen_processor (cached in api_keys.json)
            cam_idx = 0
            try:
                import json as _j
                cfg = _j.loads((CONFIG_DIR / "api_keys.json").read_text())
                cam_idx = int(cfg.get("camera_index", 0))
            except Exception:
                pass
            try:
                backend = cv2.CAP_DSHOW if _OS == "Windows" else cv2.CAP_ANY
            except AttributeError:
                backend = 0
            cap = cv2.VideoCapture(cam_idx, backend)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return
            # warm-up frames
            for _ in range(5):
                cap.read()
            while not self._cam_stop.wait(0.033) and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
                    self._cam_frame_sig.emit(buf.tobytes())
            cap.release()
        except Exception as e:
            print(f"[Camera] Stream error: {e}")
        finally:
            self._cam_stream_sig.emit(False)

    def stop_camera_stream(self) -> None:
        self._cam_stop.set()

    # ------------------------------------------------------------------
    # Icon generation — arc-reactor style, rendered with Pillow
    # ------------------------------------------------------------------
    @staticmethod
    def _build_jarvis_icon(out_path: Path) -> bool:
        """
        Render a JARVIS arc-reactor icon at 4× resolution and downsample
        for crisp results at all sizes. Saves a multi-res .ico to out_path.
        Returns True on success.
        """
        try:
            import math
            import PIL.Image
            import PIL.ImageDraw
            import PIL.ImageFilter
        except ImportError:
            return False

        CYAN   = (0, 212, 255)
        DIM    = (0, 100, 140)
        DARK   = (0, 6, 10)
        GLOW   = (0, 160, 200)
        WHITE  = (220, 240, 255)

        def _render(sz: int) -> PIL.Image.Image:
            S  = sz * 4                     # draw at 4× then downscale
            img = PIL.Image.new("RGBA", (S, S), (0, 0, 0, 0))
            d   = PIL.ImageDraw.Draw(img)
            cx = cy = S // 2

            # ── filled background circle ──────────────────────────────────
            R = S // 2 - 2
            d.ellipse([cx-R, cy-R, cx+R, cy+R], fill=(*DARK, 255))

            # ── outer border ring ─────────────────────────────────────────
            lw = max(2, S // 40)
            d.ellipse([cx-R, cy-R, cx+R, cy+R],
                      outline=(*CYAN, 220), width=lw)

            # ── mid decorative ring ───────────────────────────────────────
            R2 = int(R * 0.72)
            d.ellipse([cx-R2, cy-R2, cx+R2, cy+R2],
                      outline=(*DIM, 180), width=max(1, lw // 2))

            # ── 6 radial spokes (hex bolt) ────────────────────────────────
            R_inner = int(R * 0.30)
            R_outer = int(R * 0.62)
            spoke_w = max(1, S // 80)
            for i in range(6):
                angle = math.radians(i * 60 - 30)
                x1 = cx + int(R_inner * math.cos(angle))
                y1 = cy + int(R_inner * math.sin(angle))
                x2 = cx + int(R_outer * math.cos(angle))
                y2 = cy + int(R_outer * math.sin(angle))
                d.line([x1, y1, x2, y2], fill=(*GLOW, 200), width=spoke_w)

            # ── 6 tick marks on outer ring ────────────────────────────────
            for i in range(6):
                angle = math.radians(i * 60)
                for dr in range(lw * 2):
                    rx = (R - lw - dr)
                    d.point(
                        [cx + int(rx * math.cos(angle)),
                         cy + int(rx * math.sin(angle))],
                        fill=(*WHITE, 220),
                    )

            # ── inner glowing ring ────────────────────────────────────────
            Ri = int(R * 0.26)
            d.ellipse([cx-Ri, cy-Ri, cx+Ri, cy+Ri],
                      outline=(*CYAN, 255), width=max(2, lw))

            # ── bright glow soft blur applied before core ─────────────────
            # (draw a slightly larger cyan circle on a separate layer)
            glow_layer = PIL.Image.new("RGBA", (S, S), (0, 0, 0, 0))
            gd = PIL.ImageDraw.Draw(glow_layer)
            Rc = int(R * 0.13)
            gd.ellipse([cx-Rc*2, cy-Rc*2, cx+Rc*2, cy+Rc*2],
                       fill=(*CYAN, 110))
            glow_layer = glow_layer.filter(PIL.ImageFilter.GaussianBlur(S // 14))
            img = PIL.Image.alpha_composite(img, glow_layer)
            d   = PIL.ImageDraw.Draw(img)

            # ── core dot ──────────────────────────────────────────────────
            d.ellipse([cx-Rc, cy-Rc, cx+Rc, cy+Rc], fill=(*WHITE, 255))

            # ── downscale to target size ──────────────────────────────────
            return img.resize((sz, sz), PIL.Image.LANCZOS)

        try:
            sizes  = [256, 128, 64, 48, 32, 16]
            frames = [_render(s) for s in sizes]
            frames[0].save(
                out_path,
                format="ICO",
                append_images=frames[1:],
                sizes=[(s, s) for s in sizes],
            )
            return True
        except Exception as e:
            print(f"[Shortcut] ⚠️  Icon generation failed: {e}")
            return False

    @staticmethod
    def _create_lnk_windows(lnk: str, target: str, args: str,
                             work_dir: str, icon_loc: str) -> None:
        """
        Create a Windows .lnk shortcut WITHOUT launching PowerShell or cmd.
        Tries win32com (pywin32) first; falls back to wscript.exe + VBScript.
        wscript.exe is a GUI-mode host — it never opens a console window.
        """
        # ── Option 1: pywin32 (pure Python COM, zero subprocess) ──────────
        try:
            from win32com.client import Dispatch   # type: ignore
            sh = Dispatch("WScript.Shell")
            sc = sh.CreateShortCut(lnk)
            sc.TargetPath       = target
            sc.Arguments        = f'"{args}"'
            sc.WorkingDirectory = work_dir
            sc.Description      = "J.A.R.V.I.S AI Assistant"
            sc.IconLocation     = icon_loc
            sc.save()
            return
        except ImportError:
            pass

        # ── Option 2: wscript.exe + VBScript (always available on Windows,
        #    GUI-mode executable — never opens a console window) ────────────
        vbs = "\n".join([
            'Set ws = CreateObject("WScript.Shell")',
            f'Set sc = ws.CreateShortcut("{lnk}")',
            f'sc.TargetPath = "{target}"',
            f'sc.Arguments = Chr(34) & "{args}" & Chr(34)',
            f'sc.WorkingDirectory = "{work_dir}"',
            'sc.Description = "J.A.R.V.I.S AI Assistant"',
            f'sc.IconLocation = "{icon_loc}"',
            'sc.Save',
        ])
        import tempfile
        fd, tmp = tempfile.mkstemp(suffix=".vbs")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(vbs)
            proc = subprocess.Popen(
                ["wscript.exe", "/nologo", tmp],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            )
            proc.wait(timeout=10)
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass

    @staticmethod
    def _get_desktop_dir() -> Path:
        """
        Resolve the user's REAL desktop directory instead of assuming
        ~/Desktop, which breaks when:
          • OneDrive "Known Folder Move" relocates the desktop
            (C:/Users/x/OneDrive/Desktop) — very common on Win 10/11;
          • the XDG desktop is localized on Linux (~/Masaüstü,
            ~/Schreibtisch, ~/Bureau, …).
        Falls back to ~/Desktop only as a last resort.
        """
        home = Path.home()
        _os = platform.system()

        if _os == "Windows":
            # ── 1) SHGetKnownFolderPath(FOLDERID_Desktop) — the canonical
            #       answer; follows OneDrive redirection. No dependencies. ──
            try:
                import ctypes
                from ctypes import wintypes

                class _GUID(ctypes.Structure):
                    _fields_ = [("Data1", wintypes.DWORD),
                                ("Data2", wintypes.WORD),
                                ("Data3", wintypes.WORD),
                                ("Data4", ctypes.c_ubyte * 8)]

                # FOLDERID_Desktop {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
                fid = _GUID(0xB4BFCC3A, 0xDB2C, 0x424C,
                            (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9,
                                                 0x9A, 0x87, 0xC6, 0x41))
                buf = ctypes.c_wchar_p()
                if ctypes.windll.shell32.SHGetKnownFolderPath(
                        ctypes.byref(fid), 0, None, ctypes.byref(buf)) == 0:
                    p = Path(buf.value)
                    ctypes.windll.ole32.CoTaskMemFree(buf)
                    if p.is_dir():
                        return p
            except Exception:
                pass

            # ── 2) Registry: User Shell Folders (may contain %VARS%) ──────
            try:
                import winreg
                with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion"
                        r"\Explorer\User Shell Folders") as key:
                    val, _t = winreg.QueryValueEx(key, "Desktop")
                p = Path(os.path.expandvars(val))
                if p.is_dir():
                    return p
            except Exception:
                pass

        elif _os == "Linux":
            # ── xdg-user-dir honours localized names (~/Masaüstü, …) ──────
            try:
                out = subprocess.run(["xdg-user-dir", "DESKTOP"],
                                     capture_output=True, text=True, timeout=5)
                p = Path(out.stdout.strip())
                if out.stdout.strip() and p != home and p.is_dir():
                    return p
            except Exception:
                pass
            try:
                cfg = home / ".config" / "user-dirs.dirs"
                for line in cfg.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("XDG_DESKTOP_DIR"):
                        val = line.split("=", 1)[1].strip().strip('"')
                        p = Path(val.replace("$HOME", str(home)))
                        if p != home and p.is_dir():
                            return p
            except Exception:
                pass

        # macOS: ~/Desktop is always the real path (localization is
        # display-only). Everything else lands here as a last resort.
        return home / "Desktop"

    def _create_desktop_shortcut(self):
        """
        Create a desktop shortcut on Windows / macOS / Linux.
        Never opens a terminal, console, or PowerShell window on any platform.
        """
        import stat as _stat
        script  = Path(__file__).resolve().parent / "main.py"
        python  = Path(sys.executable)
        desktop = self._get_desktop_dir()

        # Arc-reactor icon (.ico — also exported as .png for Linux/macOS)
        ico_path = Path(__file__).resolve().parent / "config" / "jarvis.ico"
        if not ico_path.exists():
            self._build_jarvis_icon(ico_path)

        try:
            _os = platform.system()

            # ── Windows ───────────────────────────────────────────────────────
            if _os == "Windows":
                pythonw  = python.parent / "pythonw.exe"
                target   = str(pythonw if pythonw.exists() else python)
                lnk      = str(desktop / "J.A.R.V.I.S.lnk")
                icon_loc = str(ico_path) if ico_path.exists() else f"{target},0"
                self._create_lnk_windows(lnk, target, str(script),
                                         str(script.parent), icon_loc)

            # ── macOS — proper .app bundle (no Terminal window) ───────────────
            elif _os == "Darwin":
                app     = desktop / "J.A.R.V.I.S.app"
                mac_dir = app / "Contents" / "MacOS"
                res_dir = app / "Contents" / "Resources"
                mac_dir.mkdir(parents=True, exist_ok=True)
                res_dir.mkdir(exist_ok=True)

                # Launcher executable (bash — runs as background process,
                # macOS does NOT open Terminal for executables inside .app bundles)
                launcher = mac_dir / "JARVIS"
                launcher.write_text(
                    "#!/usr/bin/env bash\n"
                    f'cd "{script.parent}"\n'
                    f'exec "{python}" "{script}"\n'
                )
                launcher.chmod(launcher.stat().st_mode
                               | _stat.S_IEXEC | _stat.S_IXGRP | _stat.S_IXOTH)

                # Minimal Info.plist (required for .app recognition)
                (app / "Contents" / "Info.plist").write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0"><dict>\n'
                    '  <key>CFBundleExecutable</key><string>JARVIS</string>\n'
                    '  <key>CFBundleIdentifier</key>'
                    '<string>com.jarvis.assistant</string>\n'
                    '  <key>CFBundleName</key><string>J.A.R.V.I.S</string>\n'
                    '  <key>CFBundlePackageType</key><string>APPL</string>\n'
                    '  <key>CFBundleVersion</key><string>1.0</string>\n'
                    '</dict></plist>\n'
                )

                # Optional: copy icon as .icns (skip silently if Pillow is missing)
                try:
                    import PIL.Image
                    icns = res_dir / "AppIcon.icns"
                    PIL.Image.open(ico_path).save(icns, format="ICNS")
                    # Inject icon reference into plist
                    plist = app / "Contents" / "Info.plist"
                    txt = plist.read_text()
                    plist.write_text(
                        txt.replace(
                            '</dict></plist>',
                            '  <key>CFBundleIconFile</key>'
                            '<string>AppIcon</string>\n</dict></plist>\n',
                        )
                    )
                except Exception:
                    pass  # icon is optional

            # ── Linux — .desktop file (Terminal=false, no console) ────────────
            else:
                # Export .ico → .png for better desktop integration
                png_path = ico_path.with_suffix(".png")
                if not png_path.exists() and ico_path.exists():
                    try:
                        import PIL.Image
                        PIL.Image.open(ico_path).resize(
                            (256, 256), PIL.Image.LANCZOS
                        ).save(png_path, format="PNG")
                    except Exception:
                        png_path = ico_path  # fallback to .ico

                icon_line = f"Icon={png_path}\n" if png_path.exists() else ""
                desk = desktop / "J.A.R.V.I.S.desktop"
                desk.write_text(
                    "[Desktop Entry]\n"
                    "Name=J.A.R.V.I.S\n"
                    f"Exec={python} {script}\n"
                    f"Path={script.parent}\n"
                    "Type=Application\n"
                    "Terminal=false\n"
                    "Categories=Utility;\n"
                    + icon_line
                )
                desk.chmod(desk.stat().st_mode | 0o755)

            self._log.append_log("SYS: Desktop shortcut created.")
        except Exception as e:
            self._log.append_log(f"ERR: Shortcut failed — {e}")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_quick_backdrop()
        cw = self.centralWidget()
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 390
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        if self._remote_overlay and self._remote_overlay.isVisible():
            ow, oh = RemoteKeyOverlay._OW, RemoteKeyOverlay._OH
            self._remote_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        if self._customize_overlay and self._customize_overlay.isVisible():
            ow, oh = CustomizeOverlay._OW, CustomizeOverlay._OH
            self._customize_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        # Camera preview — bottom-right corner of the center/HUD area
        pw = _CameraPreview._W
        ph = self._cam_preview.height() or _CameraPreview._H
        self._cam_preview.setGeometry(
            cw.width() - _RIGHT_W - pw - 12,
            cw.height() - ph - 28,
            pw, ph,
        )
        # Clipboard panel — bottom-center
        if hasattr(self, '_clipboard_panel') and self._clipboard_panel.isVisible():
            self._position_clipboard_panel()
        # Quick drawer — reposition if open
        if hasattr(self, '_quick_drawer') and self._quick_drawer.isVisible():
            self._position_quick_drawer()

    def _update_metrics(self):
        snap = _metrics.snapshot()

        # CPU
        cpu = snap["cpu"]
        self._bar_cpu.set_value(cpu, f"{cpu:.0f}%")

        # MEM
        mem = snap["mem"]
        self._bar_mem.set_value(mem, f"{mem:.0f}%")

        # NET
        net = snap["net"]
        if net < 1.0:
            net_str = f"{net*1024:.0f}KB/s"
        else:
            net_str = f"{net:.1f}MB/s"
        net_pct = min(100, net * 10)  # 10 MB/s = %100
        self._bar_net.set_value(net_pct, net_str)

        # GPU
        gpu = snap["gpu"]
        if gpu >= 0:
            self._bar_gpu.set_value(gpu, f"{gpu:.0f}%")
        else:
            self._bar_gpu.set_value(0, "N/A")

        # TMP
        tmp = snap["tmp"]
        if tmp >= 0:
            tmp_pct = min(100, (tmp / 100) * 100)
            self._bar_tmp.set_value(tmp_pct, f"{tmp:.0f}°C")
        else:
            self._bar_tmp.set_value(0, "N/A")

        try:
            boot_t  = psutil.boot_time()
            elapsed = time.time() - boot_t
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")


    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(54)
        w.setStyleSheet(f"background: {C.DARK}; border-bottom: 1px solid {C.BORDER_B};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        def _badge(txt, color=C.TEXT_MED):
            l = QLabel(txt)
            l.setFont(QFont("Exo 2", 8))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        lay.addWidget(_badge("MARK LII", C.PRI_DIM))
        lay.addSpacing(8)
        self._drawer_btn = QPushButton("⚙")
        self._drawer_btn.setFixedSize(26, 26)
        self._drawer_btn.setFont(QFont("Exo 2", 11))
        self._drawer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._drawer_btn.setToolTip("Settings & Controls")
        self._drawer_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER}; border-radius: 4px;
            }}
            QPushButton:hover {{ color: {C.PRI}; border-color: {C.PRI_DIM}; }}
            QPushButton:checked {{ color: {C.PRI}; border-color: {C.PRI}; background: {C.PRI_GHO}; }}
        """)
        self._drawer_btn.setCheckable(True)
        self._drawer_btn.clicked.connect(self._toggle_drawer)
        lay.addWidget(self._drawer_btn)
        lay.addStretch()

        mid = QVBoxLayout(); mid.setSpacing(1)
        _disp = self._assistant_name.upper()
        self._title_lbl = QLabel(_disp)
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setFont(QFont("Exo 2", 17, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        mid.addWidget(self._title_lbl)
        _sub_text = ("Just A Rather Very Intelligent System"
                     if _disp in ("JARVIS", "J.A.R.V.I.S")
                     else "Personal AI Assistant")
        self._sub_lbl = QLabel(_sub_text)
        self._sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_lbl.setFont(QFont("Exo 2", 7))
        self._sub_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        mid.addWidget(self._sub_lbl)
        lay.addLayout(mid)
        lay.addStretch()

        right_col = QVBoxLayout(); right_col.setSpacing(2)
        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setFont(QFont("Orbitron", 14, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._clock_lbl)
        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Exo 2", 7))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)
        lay.addLayout(right_col)
        return w

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y"))

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_LEFT_W)
        w.setStyleSheet(f"background: {C.DARK}; border-right: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(6)

        hdr = QLabel("◈ SYS MONITOR")
        hdr.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                          f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(hdr)
        lay.addSpacing(2)

        self._bar_cpu = MetricBar("CPU", C.PRI)
        self._bar_mem = MetricBar("MEM", C.ACC2)
        self._bar_net = MetricBar("NET", C.GREEN)
        self._bar_gpu = MetricBar("GPU", C.ACC)
        self._bar_tmp = MetricBar("TMP", "#ff6688")

        for bar in [self._bar_cpu, self._bar_mem, self._bar_net,
                    self._bar_gpu, self._bar_tmp]:
            lay.addWidget(bar)

        lay.addSpacing(4)

        info_panel = QWidget()
        info_panel.setStyleSheet(
            f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;"
        )
        ip_lay = QVBoxLayout(info_panel)
        ip_lay.setContentsMargins(6, 5, 6, 5)
        ip_lay.setSpacing(3)

        self._uptime_lbl = QLabel("UP  --:--")
        self._uptime_lbl.setFont(QFont("Orbitron", 8, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        ip_lay.addWidget(self._uptime_lbl)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont("Exo 2", 8))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        ip_lay.addWidget(self._proc_lbl)

        os_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        os_lbl = QLabel(f"OS  {os_name}")
        os_lbl.setFont(QFont("Exo 2", 8))
        os_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")
        ip_lay.addWidget(os_lbl)

        lay.addWidget(info_panel)
        lay.addSpacing(4)

        lay.addStretch()

        for txt, col in [
            ("AI CORE\nACTIVE",  C.GREEN),
            ("SEC\nCLEARED",     C.PRI),
            ("PROTOCOL\nXLIX",   C.TEXT_DIM),
        ]:
            lbl = QLabel(txt)
            lbl.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {col}; background: {C.PANEL2};"
                f"border: 1px solid {C.BORDER_A}; border-radius: 3px; padding: 4px;"
            )
            lay.addWidget(lbl)

        return w
    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_RIGHT_W)
        w.setStyleSheet(f"background: {C.DARK}; border-left: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        def _sec(txt):
            l = QLabel(f"▸ {txt}")
            l.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            return l

        lay.addWidget(_sec("ACTIVITY LOG"))
        self._log = LogWidget()
        lay.addWidget(self._log, stretch=1)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)

        lay.addWidget(_sec("FILE UPLOAD"))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        lay.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded — drop or click above to upload")
        self._file_hint.setFont(QFont("Exo 2", 7))
        self._file_hint.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._file_hint.setWordWrap(True)
        lay.addWidget(self._file_hint)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep2)

        lay.addWidget(_sec("COMMAND INPUT"))
        lay.addLayout(self._build_input_row())

        self._interrupt_btn = QPushButton("✋  INTERRUPT  [ESC]")
        self._interrupt_btn.setFixedHeight(34)
        self._interrupt_btn.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        self._interrupt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._interrupt_btn.setStyleSheet(f"""
            QPushButton {{
                background: #140008; color: {C.MUTED_C};
                border: 1px solid {C.MUTED_C}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: #200010; border: 1px solid #ff6688;
            }}
            QPushButton:pressed {{
                background: #300018;
            }}
        """)
        self._interrupt_btn.clicked.connect(self._do_interrupt)
        lay.addWidget(self._interrupt_btn)

        self._mute_btn = QPushButton("🎙  MICROPHONE ACTIVE")
        self._mute_btn.setFixedHeight(30)
        self._mute_btn.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        lay.addWidget(self._mute_btn)

        return w

    def _build_quick_drawer(self) -> QWidget:
        """Floating overlay panel shown when the ⚙ header button is toggled."""
        _BTN_STYLE_PRI = f"""
            QPushButton {{
                background: #00091a; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
                text-align: left; padding: 0 8px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border-color: {C.PRI}; }}
        """
        _BTN_STYLE_DIM = f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
                text-align: left; padding: 0 8px;
            }}
            QPushButton:hover {{ color: {C.PRI}; border-color: {C.BORDER_B}; }}
        """

        w = QWidget(self.centralWidget())
        w.setObjectName("QuickDrawer")
        w.setStyleSheet(f"""
            QWidget#QuickDrawer {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 20, 34, 232),
                    stop:0.5 rgba(0, 9, 22, 214),
                    stop:1 rgba(0, 35, 48, 226));
                border: 1px solid {C.PRI_DIM};
                border-top: none;
                border-radius: 0 0 6px 6px;
            }}
        """)
        w.hide()

        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(5)

        hdr = QLabel("◈ CONTROLS")
        hdr.setFont(QFont("Exo 2", 7, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent; "
                          f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(hdr)

        remote_btn = QPushButton("◉  REMOTE CONTROL")
        remote_btn.setFixedHeight(30)
        remote_btn.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        remote_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remote_btn.setStyleSheet(_BTN_STYLE_PRI)
        remote_btn.clicked.connect(self._open_remote)
        lay.addWidget(remote_btn)

        fs_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fs_btn.setFixedHeight(26)
        fs_btn.setFont(QFont("Exo 2", 7))
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.setStyleSheet(_BTN_STYLE_DIM)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        lay.addWidget(fs_btn)

        sc_btn = QPushButton("⊞  CREATE DESKTOP SHORTCUT")
        sc_btn.setFixedHeight(26)
        sc_btn.setFont(QFont("Exo 2", 7))
        sc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sc_btn.setStyleSheet(_BTN_STYLE_DIM)
        sc_btn.clicked.connect(self._create_desktop_shortcut)
        lay.addWidget(sc_btn)

        self._autostart_btn = QPushButton("◉  AUTO-START: OFF")
        self._autostart_btn.setFixedHeight(26)
        self._autostart_btn.setFont(QFont("Exo 2", 7))
        self._autostart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._autostart_btn.clicked.connect(self._toggle_autostart)
        lay.addWidget(self._autostart_btn)

        cust_btn = QPushButton("⚙  CUSTOMISE ASSISTANT")
        cust_btn.setFixedHeight(26)
        cust_btn.setFont(QFont("Exo 2", 7))
        cust_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cust_btn.setStyleSheet(_BTN_STYLE_DIM)
        cust_btn.clicked.connect(self._open_customize)
        lay.addWidget(cust_btn)

        self._brief_btn = QPushButton()
        self._brief_btn.setFixedHeight(26)
        self._brief_btn.setFont(QFont("Exo 2", 7))
        self._brief_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._brief_btn.clicked.connect(self._toggle_brief)
        lay.addWidget(self._brief_btn)

        audio_btn = QPushButton("🎧  AUDIO DEVICES")
        audio_btn.setFixedHeight(26)
        audio_btn.setFont(QFont("Exo 2", 7))
        audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        audio_btn.setStyleSheet(_BTN_STYLE_DIM)
        audio_btn.clicked.connect(self._open_audio_devices)
        lay.addWidget(audio_btn)

        mem_btn = QPushButton("🧠  MEMORY")
        mem_btn.setFixedHeight(26)
        mem_btn.setFont(QFont("Exo 2", 7))
        mem_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mem_btn.setStyleSheet(_BTN_STYLE_DIM)
        mem_btn.clicked.connect(self._open_memory_panel)
        lay.addWidget(mem_btn)

        plugin_btn = QPushButton("🧩  PLUGINS")
        plugin_btn.setFixedHeight(26)
        plugin_btn.setFont(QFont("Exo 2", 7))
        plugin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plugin_btn.setStyleSheet(_BTN_STYLE_DIM)
        plugin_btn.clicked.connect(self._open_plugin_manager)
        lay.addWidget(plugin_btn)

        w.adjustSize()
        return w

    def _toggle_drawer(self, checked: bool):
        if checked:
            self._position_quick_drawer()
            self._quick_drawer.show()
            self._quick_drawer.raise_()
        else:
            self._quick_drawer.hide()

    def _position_quick_drawer(self):
        if not hasattr(self, '_quick_drawer'):
            return
        _W = 220
        self._quick_drawer.setFixedWidth(_W)
        self._quick_drawer.adjustSize()
        self._quick_drawer.setGeometry(12, 54, _W, self._quick_drawer.sizeHint().height())

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(5)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont("Exo 2", 9))
        self._input.setFixedHeight(30)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d14; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 3px 7px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton("▸")
        send.setFixedSize(30, 30)
        send.setFont(QFont("Exo 2", 11, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        send.clicked.connect(self._send)
        row.addWidget(send)
        return row

    def _build_content_panel(self) -> QWidget:
        """
        Collapsible panel below the HUD — shows search results, news, briefings.
        Hidden by default; appears when show_content() is called.
        """
        w = QWidget()
        w.setObjectName("ContentPanel")
        w.setStyleSheet(f"""
            QWidget#ContentPanel {{
                background: {C.PANEL};
                border-top: 1px solid {C.BORDER_B};
            }}
        """)
        w.hide()

        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 7, 12, 8)
        lay.setSpacing(5)

        # ── header row ───────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(6)

        dot = QLabel("◈")
        dot.setFont(QFont("Exo 2", 9, QFont.Weight.Bold))
        dot.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        hdr.addWidget(dot)

        self._content_title_lbl = QLabel("BRIEFING")
        self._content_title_lbl.setFont(QFont("Exo 2", 8, QFont.Weight.Bold))
        self._content_title_lbl.setStyleSheet(
            f"color: {C.PRI}; background: transparent; letter-spacing: 1px;"
        )
        hdr.addWidget(self._content_title_lbl)
        hdr.addStretch()

        self._content_ts_lbl = QLabel("")
        self._content_ts_lbl.setFont(QFont("Exo 2", 7))
        self._content_ts_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        hdr.addWidget(self._content_ts_lbl)

        dismiss = QPushButton("DISMISS  ✕")
        dismiss.setFont(QFont("Exo 2", 7))
        dismiss.setFixedHeight(18)
        dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER}; border-radius: 2px; padding: 0 5px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        dismiss.clicked.connect(w.hide)
        hdr.addWidget(dismiss)
        lay.addLayout(hdr)

        # ── separator ─────────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); lay.addWidget(sep)

        # ── text display ──────────────────────────────────────────────────────
        self._content_display = QTextEdit()
        self._content_display.setReadOnly(True)
        self._content_display.setFont(QFont("Exo 2", 8))
        self._content_display.setMinimumHeight(60)
        self._content_display.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._content_display.setStyleSheet(f"""
            QTextEdit {{
                background: {C.DARK};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                padding: 6px 8px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: rgba(0, 6, 10, 128); width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B}; border-radius: 3px; min-height: 16px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0; border: none;
            }}
        """)
        lay.addWidget(self._content_display)

        return w

    def _show_content(self, title: str, text: str):
        """Slot — runs on Qt main thread. Updates and shows the content panel."""
        import time as _time
        self._content_title_lbl.setText(title.upper()[:48])
        self._content_ts_lbl.setText(_time.strftime("%H:%M:%S"))
        self._content_display.setPlainText(text)
        self._content_display.moveCursor(
            self._content_display.textCursor().MoveOperation.Start
        )
        first_show = not self._content_panel.isVisible()
        self._content_panel.show()
        if first_show:
            total = self._center_split.height()
            self._center_split.setSizes([max(total - 220, 120), 220])

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(22)
        w.setStyleSheet(f"background: {C.DARK}; border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w); lay.setContentsMargins(14, 0, 14, 0)

        def _fl(txt, color=C.TEXT_MED):
            l = QLabel(txt); l.setFont(QFont("Exo 2", 7))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        lay.addWidget(_fl("[F4] Mute  ·  [F11] Fullscreen"))
        lay.addStretch()
        lay.addWidget(_fl("By FatihMakes", C.PRI_DIM))
        return w

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell {self._assistant_name} what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def notify_phone_connected(self) -> None:
        if self._remote_overlay and self._remote_overlay.isVisible():
            self._remote_overlay.mark_connected()

    def _open_remote(self):
        if not self.on_remote_clicked:
            self._log.append_log("SYS: Dashboard not running — remote unavailable.")
            return
        result = self.on_remote_clicked()
        if not result:
            self._log.append_log("SYS: Could not generate remote key.")
            return
        url    = result[0]
        key    = result[1]
        auto   = result[2] if len(result) >= 3 else ""
        manual = result[3] if len(result) >= 4 else url
        if self._remote_overlay:
            self._remote_overlay._do_close()
        cw  = self.centralWidget()
        ow, oh = RemoteKeyOverlay._OW, RemoteKeyOverlay._OH
        ov  = RemoteKeyOverlay(url, key, auto_login_url=auto, manual_url=manual,
                               expiry_secs=600, parent=cw)
        ov.set_new_key_callback(self.on_remote_clicked)
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.closed.connect(lambda: setattr(self, '_remote_overlay', None))
        ov.show()
        self._remote_overlay = ov
        self._log.append_log(f"SYS: Remote key generated — manual: {manual or url}")

    # ── Auto-start ──────────────────────────────────────────────────────────────

    def _check_autostart(self) -> bool:
        """Returns True if auto-start is currently registered on this OS."""
        try:
            if _OS == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                try:
                    winreg.QueryValueEx(key, "JARVIS_AI")
                    return True
                except FileNotFoundError:
                    return False
                finally:
                    winreg.CloseKey(key)
            elif _OS == "Darwin":
                return (Path.home() / "Library" / "LaunchAgents"
                        / "com.jarvis.assistant.plist").exists()
            else:
                return (Path.home() / ".config" / "autostart" / "jarvis.desktop").exists()
        except Exception:
            return False

    def _toggle_autostart(self):
        currently_on = self._check_autostart()
        try:
            script = str(Path(__file__).resolve().parent / "main.py")
            if _OS == "Windows":
                import winreg
                reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
                if currently_on:
                    winreg.DeleteValue(reg, "JARVIS_AI")
                else:
                    pythonw = Path(sys.executable).parent / "pythonw.exe"
                    exe = str(pythonw if pythonw.exists() else sys.executable)
                    winreg.SetValueEx(reg, "JARVIS_AI", 0, winreg.REG_SZ,
                                      f'"{exe}" "{script}"')
                winreg.CloseKey(reg)
            elif _OS == "Darwin":
                plist_dir = Path.home() / "Library" / "LaunchAgents"
                plist_dir.mkdir(parents=True, exist_ok=True)
                plist = plist_dir / "com.jarvis.assistant.plist"
                if currently_on:
                    plist.unlink(missing_ok=True)
                else:
                    plist.write_text(
                        '<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                        '<plist version="1.0"><dict>\n'
                        '  <key>Label</key><string>com.jarvis.assistant</string>\n'
                        '  <key>ProgramArguments</key><array>\n'
                        f'    <string>{sys.executable}</string>\n'
                        f'    <string>{script}</string>\n'
                        '  </array>\n'
                        '  <key>RunAtLoad</key><true/>\n'
                        '</dict></plist>\n'
                    )
            else:
                desk_dir = Path.home() / ".config" / "autostart"
                desk_dir.mkdir(parents=True, exist_ok=True)
                desk = desk_dir / "jarvis.desktop"
                if currently_on:
                    desk.unlink(missing_ok=True)
                else:
                    desk.write_text(
                        "[Desktop Entry]\n"
                        f"Name={self._assistant_name}\n"
                        f"Exec={sys.executable} {script}\n"
                        "Type=Application\nTerminal=false\n"
                        "X-GNOME-Autostart-enabled=true\n"
                    )
            enabled = not currently_on
            self._update_autostart_btn(enabled)
            self._log.append_log(
                f"SYS: Auto-start {'enabled' if enabled else 'disabled'}.")
        except Exception as e:
            self._log.append_log(f"ERR: Auto-start failed — {e}")

    def _update_autostart_btn(self, enabled: bool):
        if not hasattr(self, '_autostart_btn'):
            return
        if enabled:
            self._autostart_btn.setText("◉  AUTO-START: ON")
            self._autostart_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #001a08; color: {C.GREEN};
                    border: 1px solid {C.GREEN_D}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #002010; }}
            """)
        else:
            self._autostart_btn.setText("◉  AUTO-START: OFF")
            self._autostart_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.TEXT_DIM};
                    border: 1px solid {C.BORDER}; border-radius: 3px;
                }}
                QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
            """)

    def _toggle_brief(self):
        from memory.config_manager import get_brief_enabled, save_brief_enabled
        new_val = not get_brief_enabled()
        save_brief_enabled(new_val)
        self._update_brief_btn(new_val)

    def _update_brief_btn(self, enabled: bool):
        if not hasattr(self, '_brief_btn'):
            return
        if enabled:
            self._brief_btn.setText("☀  MORNING BRIEF: ON")
            self._brief_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #001a08; color: {C.GREEN};
                    border: 1px solid {C.GREEN_D}; border-radius: 3px;
                    text-align: left; padding: 0 8px;
                }}
                QPushButton:hover {{ background: #002010; }}
            """)
        else:
            self._brief_btn.setText("☀  MORNING BRIEF: OFF")
            self._brief_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.TEXT_DIM};
                    border: 1px solid {C.BORDER}; border-radius: 3px;
                    text-align: left; padding: 0 8px;
                }}
                QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
            """)

    # ── Customization ────────────────────────────────────────────────────────────

    def _open_customize(self):
        cfg = _read_full_config()
        if self._customize_overlay:
            self._customize_overlay.hide()
        cw = self.centralWidget()
        ov = CustomizeOverlay(
            cfg.get("assistant_name", "JARVIS") or "JARVIS",
            cfg.get("user_name", ""),
            cfg.get("ui_color", "") or DEFAULT_UI_COLOR,
            cfg.get("voice_name", ""),
            parent=cw,
        )
        ow, oh = CustomizeOverlay._OW, CustomizeOverlay._OH
        oh = min(oh, cw.height() - 16)
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.on_preview = self._preview_ui_color
        ov.saved.connect(self._apply_name_update)
        ov.show()
        self._customize_overlay = ov

    def _preview_ui_color(self, hex_color: str):
        """Canlı önizleme — tüm arayüzü yeni renge boyar (config'e YAZMAZ)."""
        old = current_palette()
        if apply_ui_accent(hex_color):
            retheme_all_widgets(old, current_palette())

    def _apply_name_update(self, name: str, user_name: str, ui_color: str = "",
                           voice: str = ""):
        """Update all name/theme-dependent UI elements and persist to config."""
        self._assistant_name = name.strip() or "JARVIS"
        display = self._assistant_name.upper()
        self.setWindowTitle(f"{display} — MARK LII")
        self._title_lbl.setText(display)
        if display in ("JARVIS", "J.A.R.V.I.S"):
            self._sub_lbl.setText("Just A Rather Very Intelligent System")
        else:
            self._sub_lbl.setText("Personal AI Assistant")
        self._log._ai_name_lc = self._assistant_name.lower()
        self.hud._assistant_name = display

        color_changed = False
        if ui_color:
            old = current_palette()
            if apply_ui_accent(ui_color):
                # Tüm arayüzü (paneller, butonlar, kenarlıklar, HUD) canlı boya
                retheme_all_widgets(old, current_palette())
                color_changed = old["PRI"] != C.PRI

        # Voice change → persist and, if it actually changed, rebuild the Live
        # session so the new voice takes effect (it's fixed at connect time).
        voice_changed = False
        if voice:
            from memory.config_manager import get_voice, save_voice
            if voice != get_voice():
                save_voice(voice)
                voice_changed = True

        try:
            data = _read_full_config()
            data["assistant_name"] = self._assistant_name
            data["user_name"] = user_name.strip()
            if ui_color:
                data["ui_color"] = ui_color.strip().lower()
            API_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
            self._log.append_log(f"SYS: Identity updated — {display}")
            if color_changed:
                self._log.append_log(f"SYS: UI colour applied — {ui_color}")
            if voice_changed:
                self._log.append_log(f"SYS: Voice set — {voice}")
        except Exception as e:
            self._log.append_log(f"ERR: Config save failed — {e}")

        if voice_changed and self.on_voice_change:
            self.on_voice_change()

    def _centre_overlay(self, ov) -> None:
        """Place a floating overlay in the middle of the HUD and show it."""
        cw = self.centralWidget()
        ov.adjustSize()
        ov.setGeometry(
            max(0, (cw.width()  - ov.width())  // 2),
            max(0, (cw.height() - ov.height()) // 2),
            ov.width(), ov.height(),
        )
        ov.show()
        ov.raise_()

    # ── Audio devices ────────────────────────────────────────────────────────

    def _open_audio_devices(self):
        ov = AudioDeviceOverlay(parent=self.centralWidget())
        ov.picked.connect(self._on_audio_devices_applied)
        self._centre_overlay(ov)
        self._audio_overlay = ov            # keep a reference so it isn't GC'd

    def _on_audio_devices_applied(self):
        self._log.append_log("SYS: Audio devices updated.")
        if self.on_audio_device_change:
            self.on_audio_device_change()

    # ── Memory panel ─────────────────────────────────────────────────────────

    def _open_memory_panel(self):
        ov = MemoryOverlay(parent=self.centralWidget())
        self._centre_overlay(ov)
        self._memory_overlay = ov

    # ── Irreversible-action confirmation ─────────────────────────────────────

    def _show_confirm_banner(self, title: str, detail: str):
        self._hide_confirm_banner()
        ov = ConfirmBanner(title, detail, parent=self.centralWidget())
        ov.answered.connect(self._on_confirm_answered)
        self._centre_overlay(ov)
        self._confirm_overlay = ov

    def _hide_confirm_banner(self):
        ov = getattr(self, "_confirm_overlay", None)
        if ov is not None:
            ov.hide()
            ov.deleteLater()
            self._confirm_overlay = None

    def _on_confirm_answered(self, accepted: bool):
        # Tear the banner down first: core.confirm.resolve() may be about to
        # shut the machine down, and a live widget mid-callback is not where you
        # want to be when that happens.
        self._hide_confirm_banner()
        try:
            from core.confirm import resolve
            resolve(bool(accepted))
        except Exception as e:
            self._log.append_log(f"ERR: Confirmation failed — {e}")

    def _open_plugin_manager(self):
        plugins = self.get_plugins() if self.get_plugins else []
        cw = self.centralWidget()
        ov = PluginManagerOverlay(plugins, parent=cw)
        ov.adjustSize()
        ov.setGeometry(
            (cw.width()  - ov.width())  // 2,
            (cw.height() - ov.height()) // 2,
            ov.width(), ov.height(),
        )
        ov.show()
        ov.raise_()
        self._plugin_manager_overlay = ov   # keep a reference so it isn't GC'd

    # ── Clipboard intelligence ───────────────────────────────────────────────────

    def _on_clipboard_changed(self):
        try:
            text = QApplication.clipboard().text().strip()
            if len(text) >= 10:
                self._clipboard_sig.emit(text)
        except Exception:
            pass

    def _show_clipboard_panel(self, text: str):
        self._clipboard_panel.show_clipboard(text)
        self._position_clipboard_panel()

    def _position_clipboard_panel(self):
        cw = self.centralWidget()
        pw = ClipboardPanel._W
        ph = self._clipboard_panel.sizeHint().height() or ClipboardPanel._H
        x = (cw.width() - pw) // 2
        y = cw.height() - ph - 6
        self._clipboard_panel.setGeometry(x, y, pw, ph)
        self._clipboard_panel.raise_()

    def _on_clipboard_action(self, cmd: str):
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(cmd,), daemon=True).start()

    # ────────────────────────────────────────────────────────────────────────────

    def _do_interrupt(self):
        if self.on_interrupt:
            self.on_interrupt()

    def set_audio_level(self, level):
        try: lv=max(0.0,min(1.0,float(level)))
        except Exception: return
        self.hud.set_audio_level(lv); self._header_logo.set_audio_level(lv)

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _toggle_push_to_talk(self):
        self._voice_input_enabled = not self._voice_input_enabled
        if self._voice_input_enabled:
            self._log.append_log("SYS: Push-to-talk microphone active.")
            self._apply_state("LISTENING")
        else:
            self._log.append_log("SYS: Push-to-talk microphone paused.")
            self._apply_state("MUTED")

    @property
    def voice_input_enabled(self):
        return self._voice_input_enabled and not self._muted

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("🔇  MICROPHONE MUTED")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #140006; color: {C.MUTED_C};
                    border: 1px solid {C.MUTED_C}; border-radius: 3px;
                }}
            """)
        else:
            self._mute_btn.setText("🎙  MICROPHONE ACTIVE")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #00140a; color: {C.GREEN};
                    border: 1px solid {C.GREEN}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #001f10; }}
            """)

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key")) and bool(d.get("os_system"))
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 390
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    def _on_setup_done(self, key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({"gemini_api_key": key, "os_system": os_name}, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._assistant_name = _read_full_config().get("assistant_name", "JARVIS") or "JARVIS"
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. {self._assistant_name} online.")

class _ArcLogo(QWidget):
    """Glowing blue JARVIS ring reactor (matches the reference look).

    Transparent background; dark core disc, bright blue outer ring, thin
    white inner ring, slow white sweep arcs, a faint outer orbit ring with
    tick marks, and twinkling satellite dots. Always fully visible — no
    hover gating. Speaking scales the rings with the voice level.
    """
    def __init__(self, parent=None, size=220):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        # Slow independent sweep phases (degrees).
        self._sweep_a = 200.0
        self._sweep_b = 40.0
        self._orbit = 0.0
        self._twinkle = 0.0
        self._live_amp = 0.0
        self._amp_disp = 0.0
        self._pulse = 0.0
        # Deterministic satellite dots: (base_angle, radius_frac, speed, size, phase).
        try:
            _rng = random.Random(7)
            self._dots = [
                (_rng.uniform(0, 360), _rng.uniform(0.40, 0.485),
                 _rng.uniform(-6, 6) or 2.0, _rng.uniform(1.0, 2.1),
                 _rng.uniform(0, 6.28))
                for _ in range(26)
            ]
            self._stars = [
                (_rng.uniform(0, 360), _rng.uniform(0.30, 0.49),
                 _rng.uniform(0.8, 1.6), _rng.uniform(0, 6.28))
                for _ in range(46)
            ]
        except Exception:
            self._dots, self._stars = [], []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(20)
        # Always-visible graphic; window around it stays fully transparent.
        self._graphic_opacity = 1.0
        self._stroke_opacity = 1.0
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(self._graphic_opacity)
        self.setGraphicsEffect(self._opacity_effect)

    def set_logo_size(self, size: int) -> None:
        self.setFixedSize(max(120, int(size)), max(120, int(size)))
        self.update()

    def set_graphic_opacity(self, percent: int) -> None:
        # Direct mapping — the reactor is always visible, no hover gating.
        self._graphic_opacity = max(0.0, min(1.0, int(percent) / 100.0))
        if hasattr(self, "_opacity_effect"):
            self._opacity_effect.setOpacity(self._graphic_opacity)
        self.update()

    def set_stroke_opacity(self, percent: int) -> None:
        """Controls line/stroke alpha independently from the whole reactor opacity."""
        self._stroke_opacity = max(0.0, min(1.0, int(percent) / 100.0))
        self.update()

    @property
    def stroke_opacity(self) -> int:
        return int(round(self._stroke_opacity * 100))

    @property
    def graphic_opacity(self) -> int:
        return int(round(self._graphic_opacity * 100))

    def set_audio_level(self, level: float) -> None:
        try:
            lv = max(0.0, min(1.0, float(level)))
        except Exception:
            return
        self._live_amp = max(self._live_amp, min(1.0, (lv ** 0.62) * 1.85))

    def _tick(self):
        # Slow elegant motion; sweeps accelerate while speaking.
        speed = max(0.25, float(getattr(self, '_animation_speed', 1.0)))
        boost = 1.0 + self._amp_disp * 2.2
        self._sweep_a = (self._sweep_a + 0.55 * speed * boost) % 360.0
        self._sweep_b = (self._sweep_b - 0.38 * speed * boost) % 360.0
        self._orbit = (self._orbit + 0.12 * speed) % 360.0
        self._twinkle = (self._twinkle + 0.05 * speed) % (math.pi * 2.0)
        self._pulse = (self._pulse + 0.075 * speed) % (math.pi * 2.0)
        self._live_amp *= 0.94
        self._amp_disp += (self._live_amp - self._amp_disp) * 0.42
        self.update()

    def enterEvent(self, e):
        # No hover gating — cursor feedback only.
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().enterEvent(e)

    def leaveEvent(self, e):
        super().leaveEvent(e)

    def _line(self, p, cx, cy, ang_deg, r1, r2, pen):
        a = math.radians(ang_deg)
        p.setPen(pen)
        p.drawLine(QPointF(cx + math.cos(a) * r1, cy + math.sin(a) * r1),
                   QPointF(cx + math.cos(a) * r2, cy + math.sin(a) * r2))

    def paintEvent(self, _):
        # Reference look: dark core disc, glowing blue ring, thin white
        # inner ring, slow white sweep arcs, faint orbit ring with tick
        # marks, twinkling satellite dots. Transparent outside the disc.
        # Speaking scales the rings with the voice level.
        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        W, H = self.width(), self.height()
        cx, cy = W * 0.5, H * 0.5
        b = float(min(W, H))
        amp = self._amp_disp
        so = self._stroke_opacity
        Rs = 1.0 + amp * 0.07  # speak scaling
        R = b * 0.335 * Rs

        # ---- dark core disc ----
        core = QRadialGradient(QPointF(cx, cy), R)
        core.setColorAt(0.0, qcol("#04070c", int(225 * so)))
        core.setColorAt(0.82, qcol("#04070c", int(215 * so)))
        core.setColorAt(1.0, qcol("#04070c", 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(core))
        p.drawEllipse(QPointF(cx, cy), R, R)

        # ---- blue aura glow ----
        p.setBrush(Qt.BrushStyle.NoBrush)
        for rr, aa in ((0.40, 26), (0.435, 16), (0.465, 9)):
            a = int(min(255, aa * (0.75 + amp * 1.1)) * so)
            if a > 0:
                p.setPen(QPen(qcol(C.PRI, a), max(1.0, b * 0.006)))
                r = b * rr * (1.0 + amp * 0.03)
                p.drawEllipse(QPointF(cx, cy), r, r)

        # ---- main glowing blue ring ----
        ring_rect = QRectF(cx - R, cy - R, R * 2, R * 2)
        for w, a in ((max(2.2, b * 0.016), 90), (max(1.0, b * 0.006), 235)):
            p.setPen(QPen(qcol(C.PRI, int(min(255, a * (0.8 + amp * 0.5)) * so)), w))
            p.drawEllipse(ring_rect)

        # ---- thin white inner ring ----
        p.setPen(QPen(qcol(C.WHITE, int(225 * so)), max(1.0, b * 0.0045)))
        r_in = R * 0.90
        p.drawEllipse(QPointF(cx, cy), r_in, r_in)

        # ---- slow white sweep arcs ----
        for phase, span, frac, alpha, w in (
            (self._sweep_a, 52, 1.06, 245, 2.4),
            (self._sweep_b, 34, 1.13, 170, 1.8),
            (self._sweep_a * 0.5 + 140, 22, 0.97, 130, 1.4),
        ):
            rr = R * frac
            p.setPen(QPen(qcol(C.WHITE, int(alpha * so)), max(1.0, b * 0.004 * w / 2)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx - rr, cy - rr, rr * 2, rr * 2),
                      int(phase * 16), int(span * 16))

        # ---- faint outer orbit ring with double tick marks ----
        orb_r = b * 0.455
        p.setPen(QPen(qcol(C.PRI, int(70 * so)), 1.0))
        p.drawEllipse(QPointF(cx, cy), orb_r, orb_r)
        for k in range(8):
            deg = k * 45.0 + self._orbit
            rad = math.radians(deg)
            # double-tick like the reference (two short parallel dashes)
            for off in (-0.012, 0.012):
                a2 = rad + off
                p.setPen(QPen(qcol(C.WHITE, int(150 * so)), max(1.0, b * 0.004)))
                p.drawLine(
                    QPointF(cx + math.cos(a2) * orb_r, cy + math.sin(a2) * orb_r),
                    QPointF(cx + math.cos(a2) * (orb_r - b * 0.028),
                            cy + math.sin(a2) * (orb_r - b * 0.028)))
        # small bright node riding the orbit ring
        nd = math.radians(self._sweep_b * 1.7)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(C.WHITE, int(230 * so))))
        p.drawEllipse(QPointF(cx + math.cos(nd) * orb_r, cy + math.sin(nd) * orb_r),
                      max(1.4, b * 0.006), max(1.4, b * 0.006))

        # ---- satellite dots (slow orbit + twinkle) ----
        for ang0, frac, spd, sz, ph in getattr(self, '_dots', []):
            ang = math.radians(ang0 + self._orbit * spd)
            tw = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(self._twinkle * 2.0 + ph))
            a = int(min(255, 200 * tw) * so)
            if a <= 0:
                continue
            rr = b * frac
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.WHITE, a)))
            d = max(1.0, b * 0.0032 * sz)
            p.drawEllipse(QPointF(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr), d, d)
        # faint static starfield
        for ang0, frac, sz, ph in getattr(self, '_stars', []):
            tw = 0.30 + 0.40 * (0.5 + 0.5 * math.sin(self._twinkle + ph))
            a = int(min(255, 150 * tw) * so)
            if a <= 0:
                continue
            ang = math.radians(ang0)
            rr = b * frac
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI, a)))
            d = max(1.0, b * 0.0022 * sz)
            p.drawEllipse(QPointF(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr), d, d)

        # ---- center title, exactly like the reference ----
        font = QFont('Rajdhani', max(9, int(b * 0.072)), QFont.Weight.Bold)
        try:
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 135)
        except Exception:
            pass
        p.setFont(font)
        p.setPen(QPen(qcol(C.WHITE, int(248 * so)), 1))
        p.drawText(QRectF(cx - b * 0.44, cy - b * 0.06, b * 0.88, b * 0.12),
                   Qt.AlignmentFlag.AlignCenter, 'JARVIS')

        p.end()


class VideoPreview(QFrame):
    'Clean floating video preview with top controls, seek bar and time.'
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('VideoPreview')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(f"QFrame#VideoPreview{{background:transparent;border:none;}}")
        self._player = None
        self._audio = None
        self._video = None
        self._duration = 0
        self._drag_target = self.window()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(7)

        self._controls = QWidget(self)
        self._controls.setStyleSheet("background:rgba(3,20,30,140);border:1px solid rgba(74,196,239,120);border-radius:9px;")
        cr = QHBoxLayout(self._controls); cr.setContentsMargins(8,6,8,6); cr.setSpacing(6)
        self._title = QLabel('VIDEO PREVIEW · NO FILE')
        self._title.setStyleSheet("color:#9ae8ff;font:700 8pt 'Exo 2';background:transparent;")
        cr.addWidget(self._title,1)
        open_btn = _GlowButton('OPEN','＋',compact=True); open_btn.clicked.connect(self._choose_file); cr.addWidget(open_btn)
        self._play_btn = _GlowButton('PLAY','▶',compact=True); self._play_btn.clicked.connect(self.toggle_play); cr.addWidget(self._play_btn)
        stop_btn = _GlowButton('STOP','■',compact=True); stop_btn.clicked.connect(self.stop); cr.addWidget(stop_btn)
        browser_btn = _GlowButton('BROWSER','🌐',compact=True); browser_btn.setToolTip('Open current file in system browser (codec fallback)'); browser_btn.clicked.connect(self.open_in_browser); cr.addWidget(browser_btn)
        layout.addWidget(self._controls)
        self._controls.setCursor(Qt.CursorShape.SizeAllCursor)
        self._controls.installEventFilter(self)

        self._label = QLabel('No video loaded')
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setMinimumHeight(210)
        self._label.setStyleSheet(_theme_card_css() + "color:#5796ad;")
        layout.addWidget(self._label, 1)

        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0,0); self._seek.setSingleStep(1000); self._seek.setPageStep(5000); self._seek.setTracking(True)
        self._seek.setStyleSheet(_theme_slider_css())
        layout.addWidget(self._seek)

        time_row = QHBoxLayout(); time_row.setSpacing(8)
        self._time = QLabel('00:00 / 00:00'); self._time.setMinimumWidth(110)
        self._time.setStyleSheet(_theme_chip_css() + "font:8pt 'Orbitron';")
        time_row.addWidget(self._time); time_row.addStretch(1)
        back = _GlowButton('−5s','◀',compact=True); back.clicked.connect(lambda:self._seek_by(-5000)); time_row.addWidget(back)
        fwd = _GlowButton('+5s','▶',compact=True); fwd.clicked.connect(lambda:self._seek_by(5000)); time_row.addWidget(fwd)
        layout.addLayout(time_row)

        self._seek.sliderMoved.connect(self._on_slider_moved)
        self._seek.sliderReleased.connect(self._on_slider_released)

    @staticmethod
    def _fmt(ms: int) -> str:
        secs=max(0,int(ms//1000)); h,rem=divmod(secs,3600); m,s=divmod(rem,60)
        return f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

    def eventFilter(self,obj,event):
        if obj is getattr(self,'_controls',None):
            if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                self._drag_origin=event.globalPosition().toPoint(); self._window_origin=self.window().frameGeometry().topLeft(); return False
            if event.type()==QEvent.Type.MouseMove and getattr(self,'_drag_origin',None) is not None and event.buttons() & Qt.MouseButton.LeftButton:
                self.window().move(self._window_origin + (event.globalPosition().toPoint()-self._drag_origin)); return True
            if event.type()==QEvent.Type.MouseButtonRelease: self._drag_origin=None; return False
        return super().eventFilter(obj,event)

    _AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac'}

    def _ensure_player(self):
        if self._player is not None: return True
        if QMediaPlayer is None or QAudioOutput is None:
            self._label.show()
            self._label.setText('Qt Multimedia is unavailable — install PyQt6 + system codecs, or use OPEN IN BROWSER.')
            return False
        try:
            self._audio = QAudioOutput(self)
            try:
                self._audio.setVolume(0.9)
            except Exception:
                pass
            self._player = QMediaPlayer(self)
            self._player.setAudioOutput(self._audio)
            self._player.positionChanged.connect(self._position_changed)
            self._player.durationChanged.connect(self._duration_changed)
            self._player.playbackStateChanged.connect(self._playback_state_changed)
            self._player.errorOccurred.connect(self._on_player_error)
            try:
                self._player.mediaStatusChanged.connect(self._on_media_status)
            except Exception:
                pass
            return True
        except Exception as exc:
            self._show_error(f'Player init failed: {exc}')
            return False

    def _ensure_video_surface(self):
        """Create the QVideoWidget lazily — audio files never need one."""
        if getattr(self, '_video', None) is not None:
            return
        if QVideoWidget is None:
            return
        try:
            self._video = QVideoWidget(self)
            self._video.setStyleSheet(_theme_card_css())
            idx = self.layout().indexOf(self._label)
            self._label.hide()
            self.layout().insertWidget(idx, self._video, 1)
            if self._player is not None:
                self._player.setVideoOutput(self._video)
        except Exception:
            pass

    def _on_player_error(self, _err, msg):
        # Friendly in-panel message with fallback — the tool layer reports
        # success (panel opened) so the assistant never apologises; the user
        # sees the real cause + one-click alternatives here instead.
        detail = str(msg or '').strip() or 'unsupported codec or file'
        self._show_error(
            f'Cannot decode with system codecs: {detail}\n'
            'Try OPEN IN BROWSER below, or convert to H.264 MP4.'
        )
        try:
            from core import sfx as _sfx
            _sfx.error()
        except Exception:
            pass

    def _on_media_status(self, status):
        try:
            from PyQt6.QtMultimedia import QMediaPlayer as _MP
            if status == _MP.MediaStatus.InvalidMedia:
                self._on_player_error(None, 'invalid or corrupt media')
            elif status == _MP.MediaStatus.LoadedMedia and self._duration <= 0:
                # Loaded but no duration yet (audio / stream) — show playing state.
                self._time.setText('LIVE / AUDIO')
        except Exception:
            pass

    def _show_error(self, msg):
        self._label.show()
        self._label.setText(str(msg))
        try:
            self._title.setText('VIDEO PREVIEW · PLAYBACK ISSUE')
        except Exception:
            pass

    def open_in_browser(self):
        try:
            import webbrowser
            p = getattr(self, '_current_path', None)
            if p:
                webbrowser.open(Path(p).as_uri())
        except Exception as exc:
            self._show_error(f'Browser fallback failed: {exc}')

    def load_file(self, path):
        try:
            p = Path(str(path)).expanduser()
        except Exception:
            self._show_error('Invalid file path.')
            return False
        if not p.exists() or not p.is_file():
            self._show_error(f'File not found: {p.name}')
            return False
        if not self._ensure_player():
            return False
        is_audio = p.suffix.lower() in self._AUDIO_EXTS
        try:
            self._current_path = str(p)
            if is_audio:
                # Audio: keep the status label visible as a now-playing card.
                try:
                    if getattr(self, '_video', None) is not None:
                        self._video.hide()
                except Exception:
                    pass
                self._label.show()
                self._label.setText(f'♪  {p.name}\nAudio preview — video surface not needed.')
            else:
                self._ensure_video_surface()
                try:
                    if getattr(self, '_video', None) is not None:
                        self._video.show()
                        self._label.hide()
                    else:
                        self._label.show()
                        self._label.setText('Loading…')
                except Exception:
                    pass
            self._player.stop()
            self._player.setSource(QUrl.fromLocalFile(str(p)))
            self._seek.setValue(0)
            self._seek.setRange(0, 0)
            self._duration = 0
            self._time.setText('00:00 / 00:00')
            self._title.setText(f'{"AUDIO" if is_audio else "VIDEO"} PREVIEW · {p.name.upper()[:60]}')
            self._player.play()
            # If nothing loads within 9 s (missing codec), surface the fallback hint.
            QTimer.singleShot(9000, self._check_stalled_load)
            return True
        except Exception as exc:
            self._show_error(f'Playback failed: {exc}')
            return False

    def _check_stalled_load(self):
        try:
            if self._player is None:
                return
            from PyQt6.QtMultimedia import QMediaPlayer as _MP
            stalled = self._duration <= 0 and self._player.playbackState() != _MP.PlaybackState.PlayingState
            if stalled and getattr(self, '_current_path', None):
                self._show_error(
                    'Still loading — the system codec pack may not support this file.\n'
                    'Try OPEN IN BROWSER below, or convert to H.264 MP4.'
                )
        except Exception:
            pass

    def _choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Open video',str(Path.home()),'Video (*.mp4 *.avi *.mkv *.mov *.webm *.wmv *.m4v)')
        if path: self.load_file(path)

    def _position_changed(self,pos):
        if not self._seek.isSliderDown(): self._seek.setValue(int(pos))
        self._time.setText(f'{self._fmt(pos)} / {self._fmt(self._duration)}')

    def _duration_changed(self,dur):
        self._duration=max(0,int(dur)); self._seek.setRange(0,self._duration)
        self._time.setText(f'{self._fmt(self._player.position() if self._player else 0)} / {self._fmt(self._duration)}')

    def _on_slider_moved(self,value): self._time.setText(f'{self._fmt(value)} / {self._fmt(self._duration)}')
    def _on_slider_released(self):
        if self._player is not None: self._player.setPosition(self._seek.value())
    def _seek_by(self,delta):
        if self._player is not None: self._player.setPosition(max(0,min(self._duration,self._player.position()+int(delta))))

    def toggle_play(self):
        if self._player is None:
            self._choose_file(); return
        try:
            if self._player.playbackState()==QMediaPlayer.PlaybackState.PlayingState: self._player.pause()
            else: self._player.play()
        except Exception as exc: self._show_error(str(exc))

    def _playback_state_changed(self,state):
        self._play_btn.setText('PAUSE' if state==QMediaPlayer.PlaybackState.PlayingState else 'PLAY')

    def stop(self):
        if self._player is not None: self._player.stop()
        self._seek.setValue(0); self._time.setText(f'00:00 / {self._fmt(self._duration)}')

    def close_player(self): self.stop()


class Model3DView(QFrame):
    def __init__(self,parent=None,transparent=False):
        super().__init__(parent); self.setMouseTracking(True); self.setMinimumSize(280,240)
        self._vertices=self._faces=self._edges=None; self._path=None; self._yaw=35.0; self._pitch=-18.0; self._zoom=1.0
        self._pan_x=self._pan_y=0.0; self._wireframe=False; self._drag_pos=None; self._window_drag_offset=None; self._rotate_mode=False; self._transparent=bool(transparent)
        self._status='3D display ready · double-click to rotate · wheel to zoom'
        self.setStyleSheet('background:transparent;border:none;') if transparent else self.setStyleSheet(f'background:rgba(0,6,10,120);border:1px solid {C.BORDER};border-radius:8px;')
    def load_model(self,path):
        self._path=str(path)
        try:
            import trimesh; loaded=trimesh.load(self._path,force='scene',process=False); meshes=list(loaded.geometry.values()) if hasattr(loaded,'geometry') else [loaded]; verts=[]; faces=[]; off=0
            for m in meshes:
                if m is None or not hasattr(m,'vertices') or not hasattr(m,'faces'): continue
                v=np.asarray(m.vertices,dtype=np.float32); f=np.asarray(m.faces,dtype=np.int32)
                if len(v) and len(f): verts.append(v); faces.append(f+off); off+=len(v)
            if not verts: raise ValueError('No renderable mesh geometry found')
            self._vertices=np.vstack(verts); self._faces=np.vstack(faces); center=(self._vertices.min(0)+self._vertices.max(0))*0.5; self._vertices-=center; radius=float(np.max(np.linalg.norm(self._vertices,axis=1))) or 1.0; self._vertices/=radius; self.reset_view(); self._status=f'{Path(path).name} · drag to move · double-click rotate · wheel zoom · right-click close'
        except Exception as e:
            self._vertices=self._faces=self._edges=None; self._status=f'3D load failed: {e}'
        self.update()
    def reset_view(self): self._yaw,self._pitch,self._zoom=35.0,-18.0,1.0; self._pan_x=self._pan_y=0.0; self.update()
    def toggle_wireframe(self): self._wireframe=not self._wireframe; self.update()
    def wheelEvent(self,e): self._zoom=max(0.22,min(5.0,self._zoom*(1.13**(e.angleDelta().y()/120.0)))); self.update(); e.accept()
    def mouseDoubleClickEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self._rotate_mode=not self._rotate_mode; self.setCursor(Qt.CursorShape.OpenHandCursor if self._rotate_mode else Qt.CursorShape.SizeAllCursor); e.accept(); return
        super().mouseDoubleClickEvent(e)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.RightButton: self.window().close(); e.accept(); return
        if e.button()==Qt.MouseButton.LeftButton:
            self._drag_pos=e.position(); self._window_drag_offset=(e.globalPosition().toPoint()-self.window().frameGeometry().topLeft()) if e.modifiers() & Qt.KeyboardModifier.AltModifier else None; e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            if self._window_drag_offset is not None: self.window().move(e.globalPosition().toPoint()-self._window_drag_offset)
            else:
                d=e.position()-self._drag_pos; base=max(1.0,min(self.width(),self.height()))
                if self._rotate_mode:
                    self._yaw+=d.x()*0.65; self._pitch=max(-89.0,min(89.0,self._pitch+d.y()*0.65))
                else:
                    self._pan_x+=d.x()/base*2.0; self._pan_y+=d.y()/base*2.0
                self._drag_pos=e.position(); self.update()
            e.accept(); return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton: self._drag_pos=None; self._window_drag_offset=None; e.accept(); return
        super().mouseReleaseEvent(e)
    def paintEvent(self,_):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._transparent: p.fillRect(self.rect(),qcol(C.BG,105))
        W,H=self.width(),self.height()
        if self._vertices is None or self._faces is None:
            if not self._transparent: p.setPen(qcol(C.TEXT_DIM)); p.setFont(QFont('Exo 2',9)); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,self._status)
            p.end(); return
        yaw,pitch=math.radians(self._yaw),math.radians(self._pitch); cy,sy=math.cos(yaw),math.sin(yaw); cx,sx=math.cos(pitch),math.sin(pitch); v=self._vertices; x=v[:,0]*cy-v[:,2]*sy; z=v[:,0]*sy+v[:,2]*cy; y=v[:,1]*cx-z*sx; z2=v[:,1]*sx+z*cx; scale=min(W,H)*0.40*self._zoom; sxp=W*0.5+self._pan_x*scale+x*scale; syp=H*0.47+self._pan_y*scale-y*scale
        tris=[]
        for face in self._faces:
            if len(face)>=3:
                a,b,c=face[:3]; tris.append((float((z2[a]+z2[b]+z2[c])/3.0),a,b,c))
        tris.sort(reverse=True)
        for depth,a,b,c in tris:
            light=max(0.15,min(1.0,0.58+0.32*(depth+1.0)/2.0)); col=qcol(C.PRI,int(115+125*light)); path=QPainterPath(); path.moveTo(float(sxp[a]),float(syp[a])); path.lineTo(float(sxp[b]),float(syp[b])); path.lineTo(float(sxp[c]),float(syp[c])); path.closeSubpath(); p.setBrush(Qt.BrushStyle.NoBrush if self._wireframe else QBrush(col)); p.setPen(QPen(col,1.0) if self._wireframe else QPen(qcol(C.PRI,90),0.5)); p.drawPath(path)
        if not self._transparent: p.setPen(qcol(C.TEXT_DIM,190)); p.setFont(QFont('Exo 2',7)); p.drawText(8,H-9,self._status[:110])
        p.end()


class _3DDisplayWindow(QWidget):
    """Borderless transparent 3D-only window."""
    def __init__(self, parent=None):
        super().__init__(None)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(680,680)
        self.viewer=Model3DView(self, transparent=True)
        self._drag_origin = None
        self.viewer.installEventFilter(self)
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(self.viewer)
    def load_model(self,path): self.viewer.load_model(path)
    def eventFilter(self, obj, event):
        if obj is self.viewer:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.grabMouse()
                return False
            if event.type() == QEvent.Type.MouseMove and self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_origin)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._drag_origin = None
                self.releaseMouse()
                try:
                    if getattr(self._three_d_display, '_jarvis_floating_panel', False):
                        self._remember_panel_position(self._three_d_display)
                except Exception:
                    pass
        return super().eventFilter(obj, event)


class _ArcLogoButton(_ArcLogo):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_start = None
        self._moved = False

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint()
            self._moved = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        win = self.window()
        if not getattr(win, '_drag_reactor_enabled', True):
            super().mouseMoveEvent(e); return
        if self._drag_start is not None and e.buttons() & Qt.MouseButton.LeftButton:
            delta = e.globalPosition().toPoint() - self._drag_start
            if delta.manhattanLength() >= QApplication.startDragDistance():
                self._moved = True
                win = self.window()
                if win:
                    win.move(win.pos() + delta)
                    if hasattr(win, '_save_window_position'):
                        win._save_window_position()
                self._drag_start = e.globalPosition().toPoint()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not self._moved:
            self.clicked.emit()
        self._drag_start = None
        super().mouseReleaseEvent(e)


class _MiniWaveform(QWidget):
    """Real-time audio-reactive waveform strip (reference: voice waveform)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self._amp = 0.0
        self._live = 0.0
        self._tick = 0
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(33)

    def set_audio_level(self, level: float) -> None:
        try:
            lv = max(0.0, min(1.0, float(level)))
        except Exception:
            return
        if lv > self._live:
            self._live = lv

    def _step(self):
        self._tick += 1
        self._live *= 0.88
        self._amp += (self._live - self._amp) * 0.45
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        W, H = self.width(), self.height()
        N, bw = 48, 7
        wx0 = (W - N * bw) / 2
        mid = (N - 1) / 2.0
        for i in range(N):
            env = (1.0 - abs(i - mid) / mid) ** 0.7
            shimmer = 0.55 + 0.45 * math.sin(self._tick * 0.18 + i * 0.7)
            idle = 2.5 + 1.8 * math.sin(self._tick * 0.09 + i * 0.6)
            hgt = int(max(2, min(H - 6, idle + self._amp * (H - 8) * env * shimmer)))
            cl = qcol(C.PRI) if hgt > H * 0.45 else (qcol(C.PRI_DIM) if self._amp > 0.04 else qcol(C.BORDER_B))
            p.fillRect(QRectF(wx0 + i * bw, (H - hgt) / 2, bw - 1.5, hgt), cl)
        p.end()


class _CommandWindow(QFrame):
    """New 4:5 J.A.R.V.I.S. Command Interface (reference design).

    Frameless angular HUD: custom draggable header, tab bar
    (CHAT/ACTIVITY/TOOLS/WEB/MEMORY/SYSTEM/SETTINGS), particle globe,
    voice waveform, LISTENING status, scrollable conversation log,
    metric chips and mic/send input row.
    """

    closed = pyqtSignal()

    def __init__(self, host):
        super().__init__(None)
        self._host = host  # MainWindow
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setProperty('_jarvis_floating_panel', True)
        self.setProperty('_jarvis_panel_kind', 'command')
        self.setProperty('_jarvis_panel_key', 'command_window')
        self.setMinimumSize(420, 525)
        self.setMaximumSize(520, 650)
        self.resize(470, 600)
        self._drag_pos = None
        self._build()

    # -- layout ---------------------------------------------------------
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(7)
        # Same grid-and-glow backdrop as the Control Center.
        try:
            backdrop = FuturisticBackdrop(self)
            backdrop.lower()
            self._futuristic_backdrop = backdrop
        except Exception:
            pass

        # Header (draggable): centered title + ONLINE + close (X quits JARVIS).
        hdr = QFrame(self)
        hdr.setObjectName('CmdHeader')
        hdr.setFixedHeight(40)
        hdr.setStyleSheet(
            f'QFrame#CmdHeader {{ background: transparent; '
            f'border: none; border-radius: 3px; }}'
        )
        hb = QHBoxLayout(hdr)
        hb.setContentsMargins(10, 4, 6, 4)
        hb.setSpacing(6)
        hb.addStretch(1)
        brand = QLabel('J.A.R.V.I.S.')
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet(f'color:{C.PRI};font:800 11pt "Exo 2";background:transparent;letter-spacing:4px;')
        hb.addWidget(brand)
        self._online = QLabel('●  ONLINE')
        self._online.setStyleSheet(f'color:{C.GREEN};font:700 7pt "Exo 2";background:transparent;border:none;padding:0px;')
        hb.addWidget(self._online)
        hb.addStretch(1)
        close_btn = QPushButton('×')
        close_btn.setToolTip('Close J.A.R.V.I.S. completely')
        close_btn.setFixedSize(26, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f'QPushButton {{ background:transparent;color:{C.TEXT_MED};border:none;font-size:14px; }}'
            f'QPushButton:hover {{ color:{C.RED};background:rgba(60,8,16,160); }}'
        )
        close_btn.clicked.connect(self._close_jarvis)
        hb.addWidget(close_btn)
        lay.addWidget(hdr)
        hdr.mousePressEvent = self._hdr_press
        hdr.mouseMoveEvent = self._hdr_move
        hdr.mouseReleaseEvent = self._hdr_release

        # Tab bar
        tabs = QHBoxLayout()
        tabs.setSpacing(3)
        self._tab_btns: list[QPushButton] = []
        for i, label in enumerate(('CHAT', 'ACTIVITY', 'TOOLS', 'WEB', 'MEMORY', 'SYSTEM', 'SETTINGS')):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(34)
            b.setStyleSheet(
                f'QPushButton {{ color:{C.TEXT_DIM};background:transparent;'
                f'border:none;border-radius:2px;font:700 7pt "Exo 2";padding:4px 2px; }}'
                f'QPushButton:hover {{ color:{C.WHITE};border-color:{C.PRI}; }}'
                f'QPushButton:checked {{ color:{C.WHITE};background:{C.PRI_GHO};border-color:{C.PRI}; }}'
            )
            b.clicked.connect(lambda _=False, idx=i: self._on_tab(idx))
            tabs.addWidget(b, 1)
            self._tab_btns.append(b)
        # Dedicated webcam button: opens the live webcam overlay directly.
        cam_b = QPushButton('WEBCAM')
        cam_b.setCheckable(False)
        cam_b.setCursor(Qt.CursorShape.PointingHandCursor)
        cam_b.setMinimumHeight(34)
        cam_b.setStyleSheet(
            f'QPushButton {{ color:{C.PRI};background:{C.PRI_GHO};'
            f'border:1px solid {C.PRI};border-radius:2px;font:700 7pt "Exo 2";padding:4px 6px; }}'
            f'QPushButton:hover {{ color:{C.WHITE};border-color:{C.PRI}; }}'
        )
        cam_b.clicked.connect(lambda _=False: self._host.start_camera_stream())
        tabs.addWidget(cam_b, stretch=0)
        self._webcam_btn = cam_b
        self._tab_btns[0].setChecked(True)
        lay.addLayout(tabs)

        # Core: particle globe + soundwave (same reactor as the startup button).
        core = QFrame(self)
        core.setStyleSheet('background:transparent;border:none;')
        cl = QVBoxLayout(core)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)
        self.globe = _ArcLogo(self, size=200)
        self.globe.setMinimumHeight(190)
        self.globe.setMaximumHeight(230)
        cl.addWidget(self.globe, 0, Qt.AlignmentFlag.AlignCenter)
        self.wave = _MiniWaveform(self)
        cl.addWidget(self.wave)
        lay.addWidget(core)

        # Conversation log (scrollable) + metric chips
        self.chat = QTextEdit(self)
        self.chat.setReadOnly(True)
        self.chat.setMinimumHeight(120)
        self.chat.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat.setStyleSheet(
            f'QTextEdit {{ background:rgba(0,12,20,130);color:{C.TEXT};'
            f'border:1px solid {C.BORDER_B};border-radius:3px;padding:7px;font:8pt "Exo 2"; }}'
            f'QScrollBar:vertical {{ background:transparent;width:0px;border:none; }}'
            f'QScrollBar::handle:vertical {{ background:transparent;border:none; }}'
            f'QScrollBar:horizontal {{ background:transparent;height:0px;border:none; }}'
            f'QScrollBar::handle:horizontal {{ background:transparent;border:none; }}'
        )
        self.chat.setHtml(
            f'<p><b style="color:{C.WHITE}">You</b> '
            f'<span style="color:{C.TEXT_DIM}">11:32 AM</span><br/>What\'s the status of my system?</p>'
            f'<p><b style="color:{C.PRI}">J.A.R.V.I.S.</b> '
            f'<span style="color:{C.TEXT_DIM}">11:32 AM</span><br/>Everything appears to be in order, sir.</p>'
        )
        lay.addWidget(self.chat, 1)
        self.chips = QLabel('CPU 24%  |  RAM 41%  |  GPU 18%  |  TEMP 42°C')
        self.chips.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chips.setStyleSheet(
            f'color:{C.PRI};font:700 8pt "Exo 2";background:rgba(0,24,36,140);'
            f'border:1px solid {C.BORDER_B};border-radius:8px;padding:5px;'
        )
        lay.addWidget(self.chips)

        # Input row with microphone + send
        row = QHBoxLayout()
        row.setSpacing(6)
        self.input = QLineEdit(self)
        self.input.setPlaceholderText('Type a message or speak...')
        self.input.setFixedHeight(36)
        self.input.setStyleSheet(
            f'QLineEdit {{ background:rgba(0,12,20,130);color:{C.WHITE};'
            f'border:1px solid {C.BORDER_B};border-radius:14px;padding:4px 12px; }}'
            f'QLineEdit:focus {{ border-color:{C.PRI}; }}'
        )
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, 1)
        self.mic_btn = QPushButton('🎙')
        self.mic_btn.setToolTip('Mute / unmute (F4)')
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setStyleSheet(
            f'QPushButton {{ background:rgba(0,30,50,160);color:{C.PRI};'
            f'border:1px solid {C.PRI};border-radius:18px;font-size:15px; }}'
            f'QPushButton:hover {{ background:{C.PRI_GHO}; }}'
        )
        self.mic_btn.clicked.connect(self._toggle_mute)
        row.addWidget(self.mic_btn)
        send = QPushButton('➤')
        send.setFixedSize(36, 36)
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(
            f'QPushButton {{ background:rgba(0,30,50,160);color:{C.PRI};'
            f'border:1px solid {C.BORDER_B};border-radius:18px;font-size:14px; }}'
            f'QPushButton:hover {{ border-color:{C.PRI};background:{C.PRI_GHO}; }}'
        )
        send.clicked.connect(self._send)
        row.addWidget(send)
        lay.addLayout(row)

    # -- behavior -------------------------------------------------------
    def _hdr_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def _hdr_move(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def _hdr_release(self, e):
        self._drag_pos = None
        try:
            self._host._remember_panel_position(self)
        except Exception:
            pass

    def hideEvent(self, e):
        try:
            self.closed.emit()
        except Exception:
            pass
        super().hideEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = self.rect().adjusted(1, 1, -1, -1)
        cut = 14
        path = QPainterPath()
        path.moveTo(r.left() + cut, r.top())
        path.lineTo(r.right() - cut, r.top())
        path.lineTo(r.right(), r.top() + cut)
        path.lineTo(r.right(), r.bottom() - cut)
        path.lineTo(r.right() - cut, r.bottom())
        path.lineTo(r.left() + cut, r.bottom())
        path.lineTo(r.left(), r.bottom() - cut)
        path.lineTo(r.left(), r.top() + cut)
        path.closeSubpath()
        p.fillPath(path, QBrush(QColor(1, 10, 20, 232)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol(C.BORDER_B), 1.2))
        p.drawPath(path)
        p.end()
        super().paintEvent(e)

    def _close_jarvis(self):
        """X quits J.A.R.V.I.S. completely (all windows, then the app)."""
        try:
            if _sfx_enabled(getattr(self, '_host', None)):
                _sfx('close')
            self._host._close_all_ui()
        except Exception:
            try:
                self.hide()
            except Exception:
                pass

    def _toggle_mute(self):
        try:
            self._host._toggle_mute()
        except Exception:
            pass

    def _on_tab(self, idx: int):
        if _sfx_enabled(getattr(self, '_host', None)):
            _sfx('click')
        for i, b in enumerate(self._tab_btns):
            b.setChecked(i == idx)
        try:
            h = self._host
            if idx == 1:
                h._open_activity_panel()
            elif idx == 2:
                h._open_web_task_panel()
            elif idx == 3:
                h._open_webview_panel()
            elif idx == 4:
                h._open_memory_panel()
            elif idx == 5:
                h._open_world_monitor()
            elif idx == 6:
                h._open_full_settings()
            else:
                self.input.setFocus()
        except Exception:
            pass

    def _send(self):
        txt = self.input.text().strip()
        if not txt:
            return
        if _sfx_enabled(getattr(self, '_host', None)):
            _sfx('send')
        self.input.clear()
        self.append_msg('You', txt, you=True)
        try:
            self._host._send_backend_command(txt, log=False)
            self._host._activity_add(f'YOU: {txt}')
        except Exception:
            pass
        self._show_typing_dots()
        self.input.setFocus()

    def append_msg(self, who: str, text: str, you: bool = False):
        safe = str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        col = C.WHITE if you else C.PRI
        try:
            self._stop_typing_dots()
            self._clear_trailing_dots()
            if you:
                self.chat.append(f'<b style="color:{col}">{who}</b><br/>{safe}')
                sb = self.chat.verticalScrollBar()
                sb.setValue(sb.maximum())
                return
            if self._tw_enabled():
                self._tw_who = str(who)
                self._tw_col = col
                self._tw_text = safe
                self._tw_i = 0
                self._start_tw_timer()
            else:
                self.chat.append(f'<b style="color:{col}">{who}</b><br/>{safe}')
                sb = self.chat.verticalScrollBar()
                sb.setValue(sb.maximum())
        except Exception:
            pass

    def _tw_enabled(self) -> bool:
        try:
            cfg = _read_full_config()
            feats = cfg.get('features', {}) if isinstance(cfg.get('features', {}), dict) else {}
            return bool(feats.get('typewriter_effect', True))
        except Exception:
            return True

    # ── typewriter + 3-dot loading effect ─────────────────────────────────
    def _start_tw_timer(self):
        try:
            self._stop_tw_timer()
            cur = self.chat.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            cur.insertHtml(f'<b style="color:{self._tw_col}">{self._tw_who}</b><br/>')
            self._tw_cur = cur
            self._tw_timer = QTimer(self)
            self._tw_timer.timeout.connect(self._tw_tick)
            self._tw_timer.start(12)
            self._tw_tick()
        except Exception:
            self._tw_timer = None
            self.chat.append(f'<b style="color:{self._tw_col}">{self._tw_who}</b><br/>{self._tw_text}')
            self._autoscroll_chat()

    def _tw_tick(self):
        try:
            if getattr(self, '_tw_timer', None) is None:
                return
            nxt = self._tw_i + 2  # 2 chars per tick → fast, visible reveal
            part = self._tw_text[self._tw_i:nxt]
            self._tw_i = nxt
            if part:
                self._tw_cur.insertText(part)
                self._autoscroll_chat()
            if self._tw_i >= len(self._tw_text):
                self._stop_tw_timer()
                self._autoscroll_chat()
        except Exception:
            self._stop_tw_timer()

    def _stop_tw_timer(self):
        try:
            t = getattr(self, '_tw_timer', None)
            if t is not None:
                t.stop()
                t.deleteLater()
            self._tw_timer = None
        except Exception:
            self._tw_timer = None

    def _autoscroll_chat(self):
        try:
            sb = self.chat.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception:
            pass

    def _show_typing_dots(self):
        """Animated "thinking…" 3-dot indicator while JARVIS works."""
        try:
            self._stop_typing_dots()
            self._clear_trailing_dots()
            cur = self.chat.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            self._dots_active = True
            self._dots_n = 0
            cur.insertHtml('<b style="color:{C.PRI}">J.A.R.V.I.S.</b>  '.replace('{C.PRI}', str(C.PRI)))
            self._dots_cur = self.chat.textCursor()
            self._dots_cur.movePosition(QTextCursor.MoveOperation.End)
            self._dots_cur.insertText('· · ·')
            self._dots_timer = QTimer(self)
            self._dots_timer.timeout.connect(self._dots_tick)
            self._dots_timer.start(320)
            self._autoscroll_chat()
        except Exception:
            self._dots_timer = None

    def _dots_tick(self):
        try:
            if getattr(self, '_dots_timer', None) is None:
                return
            c = QTextCursor(self.chat.document().lastBlock())
            c.select(QTextCursor.SelectionType.BlockUnderCursor)
            c.removeSelectedText()
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.MoveAnchor)
            c.insertHtml('<b style="color:{C.PRI}">J.A.R.V.I.S.</b>  '.replace('{C.PRI}', str(C.PRI)))
            c.insertText('· · ·' if self._dots_n < 2 else '· ·')
            self._dots_n = (self._dots_n + 1) % 3
            self._autoscroll_chat()
        except Exception:
            pass

    def _clear_trailing_dots(self):
        """Remove an animated dots block left at the end of the chat."""
        try:
            if not getattr(self, '_dots_active', False):
                return
            doc = self.chat.document()
            blk = doc.lastBlock()
            c = QTextCursor(blk)
            c.select(QTextCursor.SelectionType.BlockUnderCursor)
            c.removeSelectedText()
            c.insertBlock()
            c.deletePreviousChar()
            self._dots_active = False
        except Exception:
            pass

    def _stop_typing_dots(self):
        try:
            d = getattr(self, '_dots_timer', None)
            if d is not None:
                d.stop()
                d.deleteLater()
            self._dots_timer = None
        except Exception:
            self._dots_timer = None

    def set_audio_level(self, level: float):
        try:
            self.wave.set_audio_level(level)
        except Exception:
            pass
        try:
            self.globe.set_audio_level(level)
        except Exception:
            pass

    def set_status(self, state: str):
        # No status text in the clean layout — the globe + waveform react
        # to the audio level instead. Mute state is shown on the ONLINE chip.
        s = str(state or '').upper()
        try:
            online = getattr(self, '_online', None)
            if online is not None:
                if s == 'MUTED':
                    online.setText('○  MUTED')
                    online.setStyleSheet(f'color:{C.MUTED_C};font:700 7pt "Exo 2";background:transparent;padding:3px 4px;{_theme_icon_font_css()}')
                else:
                    online.setText('●  ONLINE')
                    online.setStyleSheet(f'color:{C.GREEN};font:700 7pt "Exo 2";background:transparent;padding:3px 4px;{_theme_icon_font_css()}')
        except Exception:
            pass
        # Drive the reactor state machine (smooth-blended visuals).
        try:
            globe = getattr(self, 'globe', None)
            if globe is not None and hasattr(globe, 'set_state'):
                globe.set_state(s)
        except Exception:
            pass

    def set_metrics_text(self, text: str):
        try:
            self.chips.setText(text)
        except Exception:
            pass


DISPLAY_FONT = "Segoe UI"

# Display families (must match the loaded files in assets/fonts/).
FONT_UI = "Rajdhani"            # main UI text
FONT_HEAD = "Orbitron"          # headings
FONT_LOG = "Share Tech Mono"    # system logs
FONT_NUM = "Orbitron"           # numbers / metrics
FONT_SMALL = "Exo 2"            # small labels


def _register_redesign_font() -> str:
    """Load the bundled Nasalization display font when available (no install needed)."""
    try:
        font_path = Path(__file__).resolve().parent / "assets" / "Nasalization Rg.otf"
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            if families:
                return families[0]
    except Exception:
        pass
    return "Segoe UI"


def _register_app_fonts() -> None:
    """Load the bundled UI font files (Rajdhani/Orbitron/ShareTechMono/Exo2)."""
    try:
        base = Path(__file__).resolve().parent / "assets" / "fonts"
        for filename in ("Rajdhani-Bold.ttf", "Orbitron-Bold.ttf",
                         "ShareTechMono-Regular.ttf", "Exo2-Bold.ttf"):
            try:
                path = base / filename
                if path.exists():
                    QFontDatabase.addApplicationFont(str(path))
            except Exception:
                pass
    except Exception:
        pass


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


class RefinedArcLogo(QFrame):
    """Transparent animated J.A.R.V.I.S. logo: layered cyan ring, orbit arcs,
    twinkling particles and typed title, with a smoothly-blending reactor
    state machine (IDLE/LISTENING/THINKING/EXECUTING/SPEAKING/ERROR)."""

    # Visuals come from the LOGO_* block at the very top of this file.
    LOGO_RADIUS = LOGO_RING_RADIUS
    TEXT_SIZE = LOGO_TEXT_SIZE
    GLOW_STRENGTH = LOGO_GLOW
    PARTICLE_COUNT = LOGO_PARTICLES
    PARTICLE_BRIGHTNESS = LOGO_PARTICLE_GLOW
    ANIMATION_SPEED = LOGO_SPEED
    ACTIVATION_GROWTH = LOGO_CLICK_SWELL
    ACTIVATION_DURATION = LOGO_CLICK_TIME

    def __init__(self, parent=None, size: int = 220):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self._animation_speed = 1.0
        self._stroke_opacity = 1.0
        self._live_amp = 0.0
        self._amp_display = 0.0
        self._activation_at = -10.0
        # --- reactor state machine: targets blend smoothly every tick ---
        # energy: motion speed · glow: bloom boost · tint: ring RGB ·
        # spread: particle radius · sweep: arc speed · dim: master alpha
        self._STATE_TARGETS = {
            'IDLE':      {'energy': 0.55, 'glow': 0.50, 'tint': (36, 174, 239),  'spread': 1.00, 'sweep': 1.0, 'dim': 1.00},
            'LISTENING': {'energy': 1.40, 'glow': 0.90, 'tint': (120, 226, 255), 'spread': 1.06, 'sweep': 1.8, 'dim': 1.00},
            'THINKING':  {'energy': 2.20, 'glow': 0.80, 'tint': (150, 210, 255), 'spread': 1.00, 'sweep': 3.0, 'dim': 1.00},
            'EXECUTING': {'energy': 2.60, 'glow': 1.20, 'tint': (255, 200, 120), 'spread': 1.10, 'sweep': 3.4, 'dim': 1.00},
            'SPEAKING':  {'energy': 1.20, 'glow': 1.00, 'tint': (140, 230, 255), 'spread': 1.00, 'sweep': 1.4, 'dim': 1.00},
            'ERROR':     {'energy': 0.80, 'glow': 0.90, 'tint': (255, 90, 110),  'spread': 1.00, 'sweep': 0.8, 'dim': 1.00},
            'SLEEPING':  {'energy': 0.30, 'glow': 0.25, 'tint': (60, 120, 150),  'spread': 0.97, 'sweep': 0.5, 'dim': 0.50},
        }
        self._STATE_ALIASES = {'PROCESSING': 'THINKING', 'THINK': 'THINKING', 'MUTED': 'SLEEPING',
                               'SLEEP': 'SLEEPING', 'TALKING': 'SPEAKING', 'LISTEN': 'LISTENING'}
        self._state = 'IDLE'
        self._blend = dict(self._STATE_TARGETS['IDLE'], tint=list(self._STATE_TARGETS['IDLE']['tint']))
        self._target = dict(self._STATE_TARGETS['IDLE'])
        self._clock = QElapsedTimer()
        self._clock.start()
        rng = random.Random(17)  # Stable placement; only the motion changes.
        self._particles = [
            (rng.uniform(0.0, math.tau),
             rng.uniform(126.0, 171.0),
             rng.uniform(-0.05, 0.05),
             rng.uniform(2.0, 7.0),
             rng.uniform(0.0, math.tau),
             rng.choice((1.8, 2.2, 2.7)))
            for _ in range(self.PARTICLE_COUNT)
        ]
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._frame_counter = 0
        self._timer.start(16)

    def seconds(self) -> float:
        return self._clock.elapsed() / 1000.0

    def set_logo_size(self, size: int) -> None:
        size = max(120, int(size))
        self.setFixedSize(size, size)
        self.update()

    def set_graphic_opacity(self, percent: int) -> None:
        self._opacity_effect.setOpacity(max(0.0, min(1.0, int(percent) / 100.0)))

    def set_stroke_opacity(self, percent: int) -> None:
        self._stroke_opacity = max(0.0, min(1.0, int(percent) / 100.0))
        self.update()

    @property
    def graphic_opacity(self) -> int:
        return int(round(self._opacity_effect.opacity() * 100))

    @property
    def stroke_opacity(self) -> int:
        return int(round(self._stroke_opacity * 100))

    def set_audio_level(self, level: float) -> None:
        try:
            level = max(0.0, min(1.0, float(level)))
        except (TypeError, ValueError):
            return
        self._live_amp = max(self._live_amp, level)

    def trigger_activation(self) -> None:
        self._activation_at = self._clock.elapsed() / 1000.0
        self.update()

    def set_state(self, state) -> None:
        """Retarget the reactor state; visuals blend toward it smoothly."""
        try:
            s = str(state or 'IDLE').upper().strip()
        except Exception:
            s = 'IDLE'
        s = self._STATE_ALIASES.get(s, s)
        if s not in self._STATE_TARGETS:
            s = 'IDLE'
        self._state = s
        self._target = dict(self._STATE_TARGETS[s])

    @property
    def state(self) -> str:
        return getattr(self, '_state', 'IDLE')

    def _tick(self) -> None:
        # The animation clock is elapsed-time based, so ring rotation continues
        # from the correct phase even when a frame is late. Keep the timer alive
        # even if a transient paint/state value is malformed.
        self._frame_counter += 1
        try:
            self._live_amp *= 0.93
            self._amp_display += (self._live_amp - self._amp_display) * 0.14
        except Exception:
            self._live_amp = 0.0
        # smooth-blend every visual parameter toward the state target
        try:
            k = 0.10
            tgt = self._target
            bld = self._blend
            for key in ('energy', 'glow', 'spread', 'sweep', 'dim'):
                bld[key] += (float(tgt[key]) - float(bld[key])) * k
            tr, tg, tb = tgt['tint']
            cr, cg, cb = bld['tint']
            bld['tint'] = [cr + (tr - cr) * k, cg + (tg - cg) * k, cb + (tb - cb) * k]
        except Exception:
            pass
        # Explicit repaint request every frame keeps the rotating layers alive.
        self.update()

    @staticmethod
    def _pen(color: QColor, width: float) -> QPen:
        pen = QPen(color)
        pen.setWidthF(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        return pen

    def _tint(self, mult=1.0, alpha=255):
        """Current blended state tint as a QColor."""
        try:
            r, g, b = self._blend['tint']
        except Exception:
            r, g, b = (36, 174, 239)
        r = max(0, min(255, int(r * mult)))
        g = max(0, min(255, int(g * mult)))
        b = max(0, min(255, int(b * mult)))
        return QColor(r, g, b, max(0, min(255, int(alpha))))

    @staticmethod
    def _startup(t: float):
        """Glow, rings, inner ring and text opacities for the ease-in."""
        return (
            _ease((t - 0.18) / 0.42),
            _ease((t - 0.46) / 0.42),
            _ease((t - 0.76) / 0.30),
            _ease((t - 0.96) / 0.28),
        )

    def _draw_particles(self, p: QPainter, t: float, startup: float, activation: float,
                        spread: float, stroke_alpha: float) -> None:
        for angle0, radius0, speed, drift, phase, size in self._particles:
            radius = (radius0 + math.sin(t * 0.65 + phase) * drift) * spread + activation * 11
            angle = angle0 + speed * t
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            alpha = int((70 + 78 * (0.5 + 0.5 * math.sin(t * 0.85 + phase)))
                        * startup * self.PARTICLE_BRIGHTNESS)
            if alpha <= 0:
                continue
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(113, 205, 250, int(alpha * 0.18 * stroke_alpha)))
            p.drawEllipse(QPointF(x, y), size * 2.6, size * 2.6)
            p.setBrush(QColor(232, 248, 255, int(alpha * stroke_alpha)))
            p.drawEllipse(QPointF(x, y), size, size)

    def _draw_dotted_orbit(self, p: QPainter, t: float, radius: float, count: int,
                           speed: float, dot: float, color: QColor, opacity: float,
                           twinkle: bool = True) -> None:
        """A full ring of small dots rotating together (no gaps, no dashes)."""
        if count <= 0 or opacity <= 0.004:
            return
        base = t * speed
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(count):
            ang = math.radians(base + i * (360.0 / count))
            a = opacity
            if twinkle:
                a *= 0.72 + 0.28 * (0.5 + 0.5 * math.sin(t * 0.9 + i * 2.39996))
            ai = int(a)
            if ai <= 0:
                continue
            c = QColor(color)
            c.setAlpha(min(255, ai))
            p.setBrush(c)
            d = dot * LOGO_DOT_SIZE * (0.85 + 0.3 * ((i * 37 % 10) / 10.0))
            # bright core so each dot reads at small sizes
            p.drawEllipse(QPointF(math.cos(ang) * radius, math.sin(ang) * radius), d * 1.9, d * 1.9)
            cw = QColor(235, 250, 255, min(255, ai))
            p.setBrush(cw)
            p.drawEllipse(QPointF(math.cos(ang) * radius, math.sin(ang) * radius), d, d)
        p.setBrush(Qt.BrushStyle.NoBrush)

    def _draw_dotted_arc(self, p: QPainter, radius: float, start_deg: float,
                           span_deg: float, step_deg: float, dot: float,
                           color: QColor) -> None:
        """White circular line rendered as rotating dots (centered origin).

        When LOGO_DOT_COUNT > 0 the main sweep gets exactly that many dots
        and shorter arcs get proportionally fewer; otherwise spacing comes
        from LOGO_DOT_GAP."""
        try:
            want = int(LOGO_DOT_COUNT)
        except Exception:
            want = 0
        if want > 0:
            n = max(2, int(round(want * span_deg / 67.0)))
            step_deg = span_deg / (n - 1)
        else:
            step_deg = max(1.0, step_deg * LOGO_DOT_GAP)
        if color.alpha() <= 0 or span_deg <= 0 or step_deg <= 0:
            return
        dot = max(0.4, dot * LOGO_DOT_SIZE)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        a = start_deg
        end = start_deg + span_deg
        while a <= end + 0.001:
            r = math.radians(a)
            p.drawEllipse(QPointF(math.cos(r) * radius, math.sin(r) * radius), dot, dot)
            a += step_deg
        p.setBrush(Qt.BrushStyle.NoBrush)

    def _draw_secondary_rings(self, p: QPainter, t: float, opacity: float, sweep: float) -> None:
        for radius, start, span, speed, alpha in (
            (119, 18, 92, 3.0, 72),
            (124, 168, 72, -2.2, 55),
            (129, 252, 52, 1.45, 42),
            (115, 108, 38, -1.8, 46),
        ):
            rect = QRectF(-radius, -radius, radius * 2, radius * 2)
            p.setPen(self._pen(QColor(92, 191, 241, int(alpha * opacity)), 0.85))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(rect, int((start + t * speed * sweep) * 16), int(span * 16))

        # A dim, incomplete fine orbit gives depth but never becomes a HUD panel.
        radius = 136
        p.setPen(self._pen(QColor(130, 210, 249, int(25 * opacity)), 0.65))
        p.drawArc(QRectF(-radius, -radius, radius * 2, radius * 2), int((215 - t * 1.1 * sweep) * 16), 74 * 16)

        # The quiet pale orbit underneath the ring adds the layered, machined feel
        # seen in the reference without turning the component into a full HUD.
        radius = 129
        p.setPen(self._pen(QColor(206, 240, 255, int(54 * opacity)), 0.9))
        p.drawArc(QRectF(-radius, -radius, radius * 2, radius * 2), int((224 + t * 0.65 * sweep) * 16), 57 * 16)
        p.setPen(self._pen(QColor(100, 197, 240, int(42 * opacity)), 0.75))
        p.drawArc(QRectF(-radius, -radius, radius * 2, radius * 2), int((48 - t * 0.8 * sweep) * 16), 44 * 16)

    def _draw_radial_marks(self, p: QPainter, t: float, opacity: float) -> None:
        """A few tiny instrumentation marks, much quieter than a HUD."""
        for angle, radius, length, alpha in (
            (-2, 143, 9, 105),
            (92, 147, 5, 60),
            (178, 144, 8, 86),
            (270, 146, 5, 52),
            (42, 149, 4, 48),
        ):
            flicker = 0.82 + 0.18 * math.sin(t * 0.62 + angle)
            p.save()
            p.rotate(angle)
            p.setPen(self._pen(QColor(227, 247, 255, int(alpha * opacity * flicker)), 1.15))
            p.drawLine(QPointF(0, -radius), QPointF(0, -radius - length))
            p.restore()

    def _draw_main_ring(self, p: QPainter, t: float, glow: float, inner: float,
                        pulse: float, blink: float, sweep: float, amp: float, state: str) -> None:
        glow = min(1.0, glow * self.GLOW_STRENGTH)
        radius = self.LOGO_RADIUS
        rect = QRectF(-radius, -radius, radius * 2, radius * 2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for width, alpha in ((23, 6), (16, 10), (10, 19), (6, 42)):
            p.setPen(self._pen(self._tint(0.55, alpha * glow * pulse * blink), width))
            p.drawEllipse(rect)
        p.setPen(self._pen(self._tint(1.0, 205 * glow * pulse * blink), 2.3))
        p.drawEllipse(rect)
        p.setPen(self._pen(self._tint(1.5, 100 * glow * blink), 1.1))
        p.drawEllipse(QRectF(-radius - 3, -radius - 3, (radius + 3) * 2, (radius + 3) * 2))
        # White spectral sweeps: dots or solid lines (see LOGO_DOT_RINGS).
        if LOGO_DOT_RINGS:
            # Main spectral sweep: exactly 8 visible circular dots.
            self._draw_dotted_arc(p, radius, 32 + t * 3.2 * sweep, 67, 5.5, 1.6,
                                  QColor(189, 238, 255, int(150 * glow)))
            # Secondary sweep stays a subtle solid arc so it does not add extra dots.
            p.setPen(self._pen(QColor(228, 249, 255, int(104 * glow * pulse)), 0.85))
            p.drawArc(rect, int((224 - t * 1.8 * sweep) * 16), 26 * 16)
        else:
            p.setPen(self._pen(QColor(189, 238, 255, int(150 * glow)), 1.5))
            p.drawArc(rect, int((32 + t * 3.2 * sweep) * 16), 67 * 16)
            p.setPen(self._pen(QColor(228, 249, 255, int(104 * glow * pulse)), 0.85))
            p.drawArc(rect, int((224 - t * 1.8 * sweep) * 16), 26 * 16)
        inner_radius = radius - 8
        breathe = 1.0 + (amp * 0.05 if state == 'SPEAKING' else 0.0)
        ir = inner_radius * breathe
        irect = QRectF(-ir, -ir, ir * 2, ir * 2)
        p.setPen(self._pen(self._tint(1.1, 52 * inner), 6.0))
        p.drawEllipse(irect)
        p.setPen(self._pen(QColor(247, 252, 255, int(min(255, 238 * inner + amp * 60 * inner))), 2.1))
        p.drawEllipse(irect)
        # THINKING: fast counter-rotating dotted ring around the glass edge.
        if state == 'THINKING':
            self._draw_dotted_orbit(p, t, (radius - 8) * 1.04, 8, -26.0, 1.7,
                                    self._tint(1.2, 255), 175 * inner)

    def _draw_left_arc(self, p: QPainter, t: float, opacity: float,
                       activation: float, sweep: float) -> None:
        radius = 127
        rect = QRectF(-radius, -radius, radius * 2, radius * 2)
        start = 161 + t * 1.15 * sweep
        arc_alpha = int((180 + 75 * activation) * opacity)
        p.setPen(self._pen(QColor(102, 209, 255, int(38 * opacity)), 8.0))
        p.drawArc(rect, int(start * 16), 35 * 16)
        # White left arc: dots or solid lines (see LOGO_DOT_RINGS).
        if LOGO_DOT_RINGS:
            # Keep the side arc clean; the logo's only circular dot set is the 8-dot main sweep.
            p.setPen(self._pen(QColor(250, 253, 255, arc_alpha), 2.0))
            p.drawArc(rect, int(start * 16), 22 * 16)
            p.setPen(self._pen(QColor(250, 253, 255, int(arc_alpha * 0.78)), 1.4))
            p.drawArc(rect, int((start + 27) * 16), 8 * 16)
        else:
            p.setPen(self._pen(QColor(250, 253, 255, arc_alpha), 2.7))
            p.drawArc(rect, int(start * 16), 22 * 16)
            p.setPen(self._pen(QColor(250, 253, 255, int(arc_alpha * 0.78)), 1.8))
            p.drawArc(rect, int((start + 27) * 16), 8 * 16)

    def _draw_text(self, p: QPainter, t: float, opacity: float, activation: float) -> None:
        font = QFont(DISPLAY_FONT)
        font.setPixelSize(self.TEXT_SIZE)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        p.setFont(font)
        text = LOGO_TITLE
        metrics = p.fontMetrics()
        tracking = 4.2
        widths = [metrics.horizontalAdvance(letter) for letter in text]
        total_width = sum(widths) + tracking * (len(text) - 1)
        baseline = (metrics.ascent() - metrics.descent()) / 2.0

        # The title begins typing at one second; individual alpha fades prevent a hard pop.
        typed = len(text) if not LOGO_STARTUP_ANIM else _ease((t - 1.0) / 0.62) * len(text)
        x = -total_width / 2.0
        for index, (letter, width) in enumerate(zip(text, widths)):
            letter_opacity = max(0.0, min(1.0, typed - index)) * opacity
            if letter_opacity:
                p.setPen(QColor(92, 207, 255, int((34 + 30 * activation) * letter_opacity)))
                p.drawText(QPointF(x + 1.2, baseline + 1.2), letter)
                p.setPen(QColor(249, 252, 255, int((222 + 33 * activation) * letter_opacity)))
                p.drawText(QPointF(x, baseline), letter)
            x += width + tracking

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        box = float(min(self.width(), self.height()))
        if box < 2:
            p.end()
            return
        try:
            bld = self._blend
            energy, glow = float(bld['energy']), float(bld['glow'])
            spread, sweep = float(bld['spread']), float(bld['sweep'])
            dim = float(bld['dim'])
        except Exception:
            energy, glow, spread, sweep, dim = 0.55, 0.5, 1.0, 1.0, 1.0
        state = getattr(self, '_state', 'IDLE')
        t = self.seconds()
        motion_t = t * self.ANIMATION_SPEED * max(0.15, energy) * max(0.25, float(self._animation_speed))
        if LOGO_STARTUP_ANIM:
            startup_glow, startup_rings, startup_inner, startup_text = self._startup(t)
        else:
            startup_glow = startup_rings = startup_inner = startup_text = 1.0
        stroke_alpha = max(0.0, min(1.0, self._stroke_opacity)) * dim
        glow_o = startup_glow * stroke_alpha
        rings_o = startup_rings * stroke_alpha
        inner_o = startup_inner * stroke_alpha
        text_o = startup_text * stroke_alpha
        act_prog = max(0.0, min(1.0, (t - self._activation_at) / self.ACTIVATION_DURATION))
        activation = math.sin(math.pi * act_prog) ** 2
        speak_boost = 1.5 if state == 'SPEAKING' else 1.0
        amp = self._amp_display
        pulse = (0.80 + 0.20 * math.sin(t * 1.45) ** 2 + 0.33 * activation) * (0.7 + 0.6 * glow)
        if state == 'ERROR':
            blink = 0.55 + 0.45 * math.sin(t * math.pi * 2.0 * 1.6)
        else:
            blink = 1.0
        c = QPointF(self.width() / 2.0, self.height() / 2.0)
        s = box / 300.0
        # Voice swell rides on top of the restrained click swell.
        expansion = 1.0 + self.ACTIVATION_GROWTH * activation + amp * 0.05 * speak_boost

        p.translate(c)
        p.scale(s * expansion, s * expansion)

        # The center is deliberately almost transparent: it reads over any desktop.
        p.setBrush(QColor(2, 12, 22, int(30 * inner_o)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(), self.LOGO_RADIUS - 7, self.LOGO_RADIUS - 7)

        self._draw_particles(p, motion_t, glow_o, activation, spread, stroke_alpha)
        self._draw_secondary_rings(p, motion_t, rings_o, sweep)
        self._draw_radial_marks(p, motion_t, rings_o)
        self._draw_main_ring(p, motion_t, glow_o, inner_o, pulse, blink, sweep, amp, state)
        self._draw_left_arc(p, motion_t, rings_o, activation, sweep)

        # LISTENING: fast dotted energy ring outside the orbits.
        if state == 'LISTENING' and rings_o > 0.01:
            self._draw_dotted_orbit(p, motion_t, 140.0, 8, 14.0, 1.7,
                                    self._tint(1.15, 255), 150 * rings_o)

        # EXECUTING: expanding ripple rings radiating from the core.
        if state == 'EXECUTING' and rings_o > 0.01:
            p.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(2):
                ph = (t * 0.9 + i * 0.5) % 1.0
                rr = self.LOGO_RADIUS * (0.9 + ph * 0.65)
                p.setPen(self._pen(self._tint(1.1, (1.0 - ph) * 130 * rings_o), 1.5))
                p.drawEllipse(QPointF(), rr, rr)

        # Subtle continuous instrumentation sweep: adds motion even while idle.
        if rings_o > 0.01:
            scan_a = (t * 34.0 * max(0.55, sweep)) % 360.0
            sr = self.LOGO_RADIUS + 12
            p.setPen(self._pen(QColor(225, 250, 255, int(68 * rings_o)), 1.15))
            p.drawArc(QRectF(-sr, -sr, sr * 2, sr * 2), int(scan_a * 16), 16 * 16)
            pulse_r = self.LOGO_RADIUS + 17 + 3.0 * math.sin(t * 2.2)
            p.setPen(self._pen(self._tint(1.08, int(28 * rings_o)), 0.8))
            p.drawEllipse(QPointF(), pulse_r, pulse_r)

        self._draw_text(p, t, text_o, activation)
        p.end()

    def enterEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().enterEvent(event)


class RefinedArcLogoButton(RefinedArcLogo):
    """Logo button that supports click activation and window dragging."""

    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._drag_start = None
        self._moved = False

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._moved = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        window = self.window()
        if getattr(window, "_drag_reactor_enabled", True) and self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_start
            if delta.manhattanLength() >= QApplication.startDragDistance():
                self._moved = True
                window.move(window.pos() + delta)
                if hasattr(window, "_save_window_position"):
                    window._save_window_position()
                self._drag_start = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._moved:
            self.trigger_activation()
            self.clicked.emit()
        self._drag_start = None
        super().mouseReleaseEvent(event)



class _AngularFrameMixin:
    """Shared cut-corner HUD painter for lightweight controls."""
    def _angular_path(self, rect, cut=8):
        cut = max(4.0, min(float(cut), min(rect.width(), rect.height()) * 0.28))
        path = QPainterPath()
        path.moveTo(QPointF(rect.left() + cut, rect.top()))
        path.lineTo(QPointF(rect.right() - cut, rect.top()))
        path.lineTo(QPointF(rect.right(), rect.top() + cut))
        path.lineTo(QPointF(rect.right(), rect.bottom() - cut))
        path.lineTo(QPointF(rect.right() - cut, rect.bottom()))
        path.lineTo(QPointF(rect.left() + cut, rect.bottom()))
        path.lineTo(QPointF(rect.left(), rect.bottom() - cut))
        path.lineTo(QPointF(rect.left(), rect.top() + cut))
        path.closeSubpath()
        return path


class _AngularButton(QPushButton, _AngularFrameMixin):
    """Flat glass button using the same bright-corner language as Settings tabs."""
    def __init__(self, text='', parent=None, accent=False, compact=False):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumHeight(32 if compact else 38)
        self._hover = False
        self._accent = accent
        self.setMouseTracking(True)
        self.setStyleSheet('background:transparent;border:none;padding:0;')

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = self._angular_path(r, 7)
        active = self.isChecked() or self.hasFocus() or self._hover
        if self.isDown():
            fill = QColor(0, 120, 157, 185)
        elif self.isChecked():
            fill = QColor(0, 92, 124, 150)
        elif self._hover:
            fill = QColor(0, 72, 98, 125)
        else:
            fill = QColor(1, 16, 25, 135)
        p.fillPath(path, QBrush(fill))
        p.setBrush(Qt.BrushStyle.NoBrush)
        border = QColor(66, 199, 239, 240) if active else QColor(67, 151, 185, 92)
        p.setPen(QPen(border, 1.2))
        p.drawPath(path)
        # Keep the button clean: no extra top-left / bottom-right corner lines.
        p.setPen(QColor(233, 252, 255, 255) if active else QColor(168, 239, 255, 235))
        f = QFont('Exo 2', 7, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(r.adjusted(7, 0, -7, 0), Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()


class _AngularLineEdit(QLineEdit, _AngularFrameMixin):
    """Command field with tab-like cut corners and a clean interior."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("QLineEdit{background:transparent;color:#f0fcff;border:none;padding:5px 12px;font:9pt 'Rajdhani';}")
        self._focus = False

    def focusInEvent(self, e):
        self._focus = True
        self.update()
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        self._focus = False
        self.update()
        super().focusOutEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = self._angular_path(r, 8)
        p.fillPath(path, QBrush(QColor(1, 15, 26, 205)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(74, 196, 239, 210) if self._focus else QColor(67,151,185,105), 1.2))
        p.drawPath(path)
        p.setPen(QPen(QColor(118,230,252,170 if self._focus else 70), 1.4))
        p.drawLine(QPointF(r.left()+2, r.top()+9), QPointF(r.left()+2, r.top()+2))
        p.drawLine(QPointF(r.left()+2, r.top()+2), QPointF(r.left()+15, r.top()+2))
        p.drawLine(QPointF(r.right()-15, r.bottom()-2), QPointF(r.right()-2, r.bottom()-2))
        p.drawLine(QPointF(r.right()-2, r.bottom()-2), QPointF(r.right()-2, r.bottom()-9))
        p.end()
        super().paintEvent(e)


class _AngularTextEdit(QTextEdit, _AngularFrameMixin):
    """Conversation surface with restrained cut-corner HUD framing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("QTextEdit{background:transparent;color:#b9efff;border:none;padding:9px;font:9pt 'Rajdhani';}QScrollBar:vertical{background:transparent;width:0px;border:none;}QScrollBar:horizontal{background:transparent;height:0px;border:none;}")
        self._focus = False

    def focusInEvent(self, e):
        self._focus = True; self.update(); super().focusInEvent(e)

    def focusOutEvent(self, e):
        self._focus = False; self.update(); super().focusOutEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = self._angular_path(r, 10)
        p.fillPath(path, QBrush(QColor(1, 13, 23, 185)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(74,196,239,205) if self._focus else QColor(67,151,185,105), 1.2))
        p.drawPath(path)
        p.setPen(QPen(QColor(118,230,252,150 if self._focus else 60), 1.4))
        p.drawLine(QPointF(r.left()+2, r.top()+10), QPointF(r.left()+2, r.top()+2))
        p.drawLine(QPointF(r.left()+2, r.top()+2), QPointF(r.left()+18, r.top()+2))
        p.drawLine(QPointF(r.right()-18, r.bottom()-2), QPointF(r.right()-2, r.bottom()-2))
        p.drawLine(QPointF(r.right()-2, r.bottom()-2), QPointF(r.right()-2, r.bottom()-10))
        p.end()
        super().paintEvent(e)


class RefinedCommandWindow(_CommandWindow):
    """A calmer command deck retaining the original message and panel hooks."""

    def _build(self) -> None:
        self.setMinimumSize(440, 580)
        self.setMaximumSize(560, 700)
        self.resize(484, 630)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        header = QFrame(self)
        header.setFixedHeight(46)
        # Keep the title/status area visually clean: no box or stroke behind ONLINE.
        header.setStyleSheet("QFrame { background: transparent; border: none; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(13, 4, 7, 4)
        identity = QVBoxLayout()
        identity.setSpacing(0)
        title = QLabel("J.A.R.V.I.S")
        title.setStyleSheet("color:#dff8ff; font: 700 10pt 'Orbitron'; letter-spacing:4px; background:transparent; border:none;")
        identity.addWidget(title)
        header_layout.addLayout(identity)
        header_layout.addStretch(1)
        self._online = QLabel("●  ONLINE")
        self._online.setStyleSheet("color:#7affc3; font:700 7pt 'Exo 2'; background:transparent; border:none; padding:0px; margin:0px;" + _theme_icon_font_css())
        header_layout.addWidget(self._online)
        close = QPushButton("×")
        close.setFixedSize(27, 27)
        close.setToolTip("Close J.A.R.V.I.S.")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet("QPushButton { color:#7ab7c9; background:transparent; border:none; font-size:16px; } QPushButton:hover { color:#ff7892; }")
        close.clicked.connect(self._close_jarvis)
        header_layout.addWidget(close)
        header.mousePressEvent = self._hdr_press
        header.mouseMoveEvent = self._hdr_move
        header.mouseReleaseEvent = self._hdr_release
        layout.addWidget(header)

        nav = QHBoxLayout()
        nav.setSpacing(5)
        self._tab_btns = []
        for index, title in enumerate(("CHAT", "ACTIVITY", "TOOLS", "WEB", "MEMORY", "SYSTEM", "SETTINGS")):
            button = _AngularButton(title, self, compact=True)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(29)
            button.setStyleSheet(
                "QPushButton { color:#659fb1; background:rgba(1,17,27,150); border:1px solid rgba(67,151,185,100); border-radius:7px; font:700 7pt 'Exo 2'; }"
                "QPushButton:hover { color:#e3fbff; border-color:#42c7ef; }"
                "QPushButton:checked { color:#e9fcff; background:rgba(0,103,143,105); border-color:#42c7ef; }"
            )
            button.clicked.connect(lambda _=False, i=index: self._on_tab(i))
            nav.addWidget(button, 1)
            self._tab_btns.append(button)

        # Vision sits directly beside CHAT and toggles the existing live webcam overlay.
        vision = _AngularButton("VISION", self, compact=True)
        vision.setCheckable(True)
        vision.setCursor(Qt.CursorShape.PointingHandCursor)
        vision.setFixedHeight(29)
        vision.setToolTip("Toggle live webcam vision overlay")
        vision.setStyleSheet(
            "QPushButton { color:#63d8f6; background:rgba(0,38,52,170); border:1px solid rgba(66,199,239,150); border-radius:7px; font:700 7pt 'Exo 2'; }"
            "QPushButton:hover { color:#ffffff; border-color:#8be8ff; background:rgba(0,72,94,190); }"
            "QPushButton:checked { color:#ffffff; background:rgba(0,122,156,150); border-color:#8be8ff; }"
        )
        vision.toggled.connect(self._on_vision_toggled)
        nav.insertWidget(1, vision, 1)
        self._vision_btn = vision

        self._tab_btns[0].setChecked(True)
        layout.addLayout(nav)

        core = QFrame(self)
        core.setFixedHeight(228)
        core.setStyleSheet("QFrame { background:rgba(0, 12, 22, 72); border:1px solid rgba(41, 135, 170, 85); border-radius:14px; }")
        core_layout = QVBoxLayout(core)
        core_layout.setContentsMargins(6, 4, 6, 4)
        self.globe = RefinedArcLogo(core, size=190)
        core_layout.addWidget(self.globe, 1, Qt.AlignmentFlag.AlignCenter)
        self.wave = _MiniWaveform(core)
        self.wave.setFixedHeight(34)
        core_layout.addWidget(self.wave)
        layout.addWidget(core)

        self.chat = _AngularTextEdit(self)
        self.chat.setReadOnly(True)
        self.chat.setMinimumHeight(115)
        self.chat.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat.setPlaceholderText("Command history will appear here.")
        self.chat.setHtml("<span style='color:#5c95a8'>SYSTEM</span>  Secure channel ready.  Enter a command to begin.")
        layout.addWidget(self.chat, 1)

        self.chips = QLabel("CPU  --%    ·    RAM  --%    ·    GPU  --%")
        self.chips.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chips.setStyleSheet("color:#9ae8ff; background:rgba(0,83,116,82); border:1px solid rgba(86,190,225,110); border-radius:8px; padding:6px; font:700 7.5pt 'Orbitron';")
        layout.addWidget(self.chips)

        input_row = QHBoxLayout()
        input_row.setSpacing(7)
        self.input = _AngularLineEdit(self)
        self.input.setPlaceholderText("Ask JARVIS anything…")
        self.input.setFixedHeight(38)
        self.input.returnPressed.connect(self._send)
        input_row.addWidget(self.input, 1)
        self.mic_btn = _AngularButton("MIC", self, compact=True)
        self.mic_btn.setFixedSize(58, 38)
        self.mic_btn.setToolTip("Mute / unmute (F4)")
        self.mic_btn.clicked.connect(self._toggle_mute)
        input_row.addWidget(self.mic_btn)
        send = _AngularButton("SEND", self, accent=True, compact=True)
        send.setFixedSize(62, 38)
        send.clicked.connect(self._send)
        input_row.addWidget(send)
        layout.addLayout(input_row)

    def _on_vision_toggled(self, checked: bool) -> None:
        """Toggle the host's existing live webcam overlay from the Vision button."""
        try:
            _sfx('click')
        except Exception:
            pass
        host = self._host
        try:
            if checked:
                host.toggle_camera_overlay(True)
            else:
                host.toggle_camera_overlay(False)
        except Exception as exc:
            try:
                self._vision_btn.blockSignals(True)
                self._vision_btn.setChecked(not checked)
            finally:
                self._vision_btn.blockSignals(False)
            try:
                host.write_log(f'ERR: Vision — {exc}')
            except Exception:
                pass

    def _on_tab(self, index: int) -> None:
        try:
            _sfx('click')
        except Exception:
            pass
        for tab_index, button in enumerate(self._tab_btns):
            button.setChecked(tab_index == index)
        try:
            h = self._host
            if index == 0:
                self.input.setFocus()
            elif index == 1:
                h._open_activity_panel()
            elif index == 2:
                h._open_tools_panel()
            elif index == 3:
                h._open_webview_panel()
            elif index == 4:
                h._open_memory_panel()
            elif index == 5:
                h._open_world_monitor()
            elif index == 6:
                h._open_full_settings()
        except Exception:
            pass

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        cut = 18
        path.moveTo(rect.left() + cut, rect.top())
        path.lineTo(rect.right() - cut, rect.top())
        path.lineTo(rect.right(), rect.top() + cut)
        path.lineTo(rect.right(), rect.bottom() - cut)
        path.lineTo(rect.right() - cut, rect.bottom())
        path.lineTo(rect.left() + cut, rect.bottom())
        path.lineTo(rect.left(), rect.bottom() - cut)
        path.lineTo(rect.left(), rect.top() + cut)
        path.closeSubpath()
        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0.0, QColor(1, 17, 29, 242))
        fill.setColorAt(0.55, QColor(1, 8, 18, 248))
        fill.setColorAt(1.0, QColor(0, 35, 51, 238))
        painter.fillPath(path, QBrush(fill))
        bloom = QRadialGradient(QPointF(rect.width() * 0.82, rect.height() * 0.10), rect.width() * 0.70)
        bloom.setColorAt(0.0, QColor(0, 195, 242, 36))
        bloom.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillPath(path, QBrush(bloom))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(70, 188, 223, 165), 1.2))
        painter.drawPath(path)
        painter.setPen(QPen(QColor(121, 228, 250, 185), 1.6))
        painter.drawLine(QPointF(rect.left() + cut, rect.top() + 1), QPointF(rect.left() + cut + 42, rect.top() + 1))
        painter.drawLine(QPointF(rect.right() - cut - 42, rect.bottom() - 1), QPointF(rect.right() - cut, rect.bottom() - 1))
        painter.end()


# Preview redesign becomes the production default. The original implementations
# remain in the file for backend compatibility and as a fallback reference.
_ArcLogo = RefinedArcLogo
_ArcLogoButton = RefinedArcLogoButton
_CommandWindow = RefinedCommandWindow


class _HudPanel(QFrame):
    """Reference-style angular glass HUD panel used by floating previews/actions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self._resize_origin = None
        self._resize_geom = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setObjectName('HudPanel')

    def _in_resize_zone(self, pos):
        r = self.rect()
        return pos.x() >= r.width() - 18 and pos.y() >= r.height() - 18

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._in_resize_zone(e.position()):
            self._resize_origin = e.globalPosition().toPoint()
            self._resize_geom = self.geometry()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resize_origin is not None and e.buttons() & Qt.MouseButton.LeftButton:
            delta = e.globalPosition().toPoint() - self._resize_origin
            g = self._resize_geom
            self.resize(max(260, g.width() + delta.x()), max(180, g.height() + delta.y()))
            e.accept()
            return
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if self._in_resize_zone(e.position()) else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._resize_origin = None
            self._resize_geom = None
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        # Unified refined shell: gradient fill + bloom + rounded border,
        # matching the main command window.
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = 14.0
        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0.0, QColor(1, 17, 29, 242))
        fill.setColorAt(0.55, QColor(1, 8, 18, 248))
        fill.setColorAt(1.0, QColor(0, 35, 51, 238))
        p.setBrush(QBrush(fill))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, radius, radius)
        bloom = QRadialGradient(QPointF(rect.width() * 0.82, rect.height() * 0.10), rect.width() * 0.70)
        bloom.setColorAt(0.0, QColor(0, 195, 242, 30))
        bloom.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(bloom))
        p.drawRoundedRect(rect, radius, radius)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(70, 188, 223, 200 if self._hover else 165), 1.2))
        p.drawRoundedRect(rect, radius, radius)
        p.setPen(QPen(QColor(121, 228, 250, 185), 1.6))
        p.drawLine(QPointF(rect.left() + 18, rect.top() + 1), QPointF(rect.left() + 60, rect.top() + 1))
        p.drawLine(QPointF(rect.right() - 60, rect.bottom() - 1), QPointF(rect.right() - 18, rect.bottom() - 1))
        # resize grip hint (QPointF: raw QRectF floats hang drawLine overloads)
        p.setPen(QPen(QColor(66, 199, 239, 150), 1.4))
        p.drawLine(QPointF(rect.right()-16, rect.bottom()-4), QPointF(rect.right()-4, rect.bottom()-16))
        p.drawLine(QPointF(rect.right()-11, rect.bottom()-4), QPointF(rect.right()-4, rect.bottom()-11))
        p.end()
        super().paintEvent(e)


class _GlowButton(QPushButton):
    """Reference-style angular HUD button with transparent glass fill."""
    def __init__(self, text='', icon_text='', compact=False, parent=None):
        label = f'{icon_text}  {text}' if icon_text else text
        super().__init__(label, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(34 if compact else 40)
        self._hover = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def enterEvent(self, e):
        self._hover = True; self.update(); super().enterEvent(e)
        # Hover.mp3 asset; _sfx() self-gates on the enable switch.
        try:
            _sfx('hover')
        except Exception:
            pass

    def leaveEvent(self, e):
        self._hover = False; self.update(); super().leaveEvent(e)

    def paintEvent(self, e):
        # Unified refined button: rounded card, hover glow, pressed depth.
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = 7.0
        if self.isDown():
            fill = QBrush(QColor(0, 154, 199, 180))
        elif self._hover:
            fill = QBrush(QColor(0, 125, 165, 120))
        else:
            fill = QBrush(QColor(1, 17, 27, 150))
        p.setBrush(fill)
        p.setPen(QPen(QColor(66, 199, 239, 255) if (self._hover or self.hasFocus()) else QColor(67, 151, 185, 100), 1.2))
        p.drawRoundedRect(r, radius, radius)
        # top sheen line for depth
        p.setPen(QPen(QColor(233, 252, 255, 46 if self._hover else 26), 1.0))
        p.drawLine(QPointF(r.left() + radius + 2, r.top() + 2.5), QPointF(r.right() - radius - 2, r.top() + 2.5))
        p.setPen(QPen(QColor(227, 251, 255, 255) if self._hover else QColor(168, 239, 255, 255), 1))
        p.setFont(self.font())
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()


class _GlowSquareButton(QPushButton):
    """Cut-corner square chrome matching the C-button language."""
    def __init__(self, text='×', parent=None, size=26):
        super().__init__(text, parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True; self.update(); super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False; self.update(); super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = 7.0
        p.setBrush(QBrush(QColor(0, 125, 165, 120) if self._hover else QColor(1, 17, 27, 150)))
        p.setPen(QPen(QColor(66, 199, 239, 255) if self._hover else QColor(67, 151, 185, 100), 1.2))
        p.drawRoundedRect(r, radius, radius)
        p.setPen(QPen(QColor(255, 120, 146, 255) if (self._hover and self.text().strip() in ('×', '✕')) else (QColor(227, 251, 255, 255) if self._hover else QColor(168, 239, 255, 255)), 1))
        p.setFont(QFont('Rajdhani', 11, QFont.Weight.Bold))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()


def _hud_field_css():
    # Centralized: every input/list in the app shares the theme fields.
    return _theme_field_css()


class RefinedMeter(QFrame):
    """Live metric bar: label, animated QProgressBar and value readout.
    Bar color follows healthy / warning / critical thresholds."""
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background:rgba(1,17,27,120);"
            " border:1px solid rgba(67,151,185,70); border-radius:8px; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(5)
        top = QHBoxLayout()
        top.setSpacing(6)
        self._label = QLabel(label.upper())
        self._label.setStyleSheet("color:#5796ad;font:700 7pt 'Exo 2';background:transparent;")
        top.addWidget(self._label, 1)
        self._value = QLabel('--')
        self._value.setStyleSheet("color:#9ae8ff;font:700 8pt 'Orbitron';background:transparent;")
        top.addWidget(self._value)
        lay.addLayout(top)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(7)
        self._apply_bar_style('#42c7ef')
        lay.addWidget(self._bar)
        self._anim = None

    def _apply_bar_style(self, color: str) -> None:
        self._bar.setStyleSheet(
            "QProgressBar { background:rgba(0,20,30,180); border:none; border-radius:3px; }"
            f"QProgressBar::chunk {{ background:{color}; border-radius:3px; }}"
        )

    def set_value(self, pct: float, text: str = '') -> None:
        try:
            pct = max(0.0, min(100.0, float(pct)))
        except Exception:
            pct = 0.0
        self._apply_bar_style(_theme_meter_color(pct))
        if text:
            self._value.setText(str(text))
        try:
            if self._anim is not None:
                self._anim.stop()
        except Exception:
            pass
        try:
            self._anim = QPropertyAnimation(self._bar, b'value', self)
            self._anim.setDuration(600)
            self._anim.setStartValue(self._bar.value())
            self._anim.setEndValue(int(round(pct)))
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        except Exception:
            try:
                self._bar.setValue(int(round(pct)))
            except Exception:
                pass


class WebViewPane(QFrame):
    """Minimal JARVIS web console: search field + check button only.
    Engine selection lives in Settings → Web; errors surface as a
    single floating line, otherwise the pane stays text-free."""
    def __init__(self, parent=None, home='https://www.google.com', use_engine=True):
        super().__init__(parent)
        self.setStyleSheet('background:transparent;border:none;')
        self._home = home or 'https://www.google.com'
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        bar = QHBoxLayout(); bar.setSpacing(6)
        self._url = QLineEdit(self._home)
        self._url.setPlaceholderText('Search or type a URL…')
        self._url.setStyleSheet(_hud_field_css())
        self._url.setMinimumHeight(36)
        self._url.returnPressed.connect(self.navigate)
        bar.addWidget(self._url, 1)
        go = _GlowButton('✓', '', compact=True)
        go.setMinimumHeight(36); go.setMinimumWidth(44)
        go.setToolTip('Go')
        go.clicked.connect(self.navigate)
        bar.addWidget(go)
        lay.addLayout(bar)
        # Engine switch lives in Settings → Web; kept hidden here so the
        # engine_enabled property and external callers keep working.
        self._engine_toggle = QCheckBox('INTERNAL ENGINE')
        self._engine_toggle.setChecked(bool(use_engine))
        self._engine_toggle.setVisible(False)
        self._engine_toggle.toggled.connect(self._on_engine_toggle)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(5)
        self._progress.setStyleSheet(
            "QProgressBar { background:rgba(0,20,30,180); border:none; border-radius:2px; }"
            "QProgressBar::chunk { background:#42c7ef; border-radius:2px; }"
        )
        self._progress.hide()
        lay.addWidget(self._progress)
        self._status = QLabel('')
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color:#ff7892;font:700 7pt 'Exo 2';background:transparent;" + _theme_icon_font_css())
        self._status.hide()
        lay.addWidget(self._status)
        self._engine = None
        self._fallback = QTextEdit(self)
        self._fallback.setReadOnly(True)
        self._fallback.setStyleSheet(_hud_field_css())
        self._fallback.setHtml(
            '<p style="color:#5ab8cc">Embedded WebView is unavailable or disabled. '
            'Use GO to open the URL in your system browser, or install PyQt6-WebEngine.</p>'
        )
        if _WEB_OK and QWebEngineView is not None:
            self._engine = QWebEngineView(self)
            try:
                self._engine.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                # Let voice commands start media without requiring an extra manual click.
                try:
                    self._engine.settings().setAttribute(
                        QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False
                    )
                except Exception:
                    pass
            except Exception:
                pass
            self._engine.urlChanged.connect(self._on_url_changed)
            self._engine.titleChanged.connect(lambda t: self._status.setText(f'● {t[:64]}'))
            self._engine.loadStarted.connect(self._on_load_started)
            self._engine.loadProgress.connect(self._on_load_progress)
            self._engine.loadFinished.connect(self._on_load_finished)
            lay.addWidget(self._engine, 1)
        lay.addWidget(self._fallback, 1)
        self._set_engine_enabled(self._engine_toggle.isChecked())
        QTimer.singleShot(0, self.go_home)

    def _on_engine_toggle(self, enabled):
        self._set_engine_enabled(enabled)
        # Persist the user's choice so the engine mode survives JARVIS restarts.
        try:
            cfg = _ui_load(API_FILE)
            feats = dict(cfg.get('features', {})) if isinstance(cfg.get('features', {}), dict) else {}
            feats['webview_engine'] = bool(enabled)
            _ui_save(API_FILE, features=feats)
        except Exception:
            pass

    def _set_engine_enabled(self, enabled):
        enabled = bool(enabled) and getattr(self, '_engine', None) is not None
        if getattr(self, '_engine', None) is not None:
            self._engine.setVisible(enabled)
        self._fallback.setVisible(not enabled)
        if self._engine_toggle.isChecked() and self._engine is None:
            self._engine_toggle.setToolTip('Install PyQt6-WebEngine to enable the embedded browser.')
            self._status.setText('WEBVIEW · ENGINE UNAVAILABLE')

    @property
    def engine_enabled(self):
        return bool(self._engine is not None and self._engine_toggle.isChecked())

    def _normalize(self, raw: str) -> str:
        raw = (raw or '').strip()
        if not raw:
            return self._home
        if ' ' in raw and '://' not in raw:
            from urllib.parse import quote_plus
            return 'https://www.google.com/search?q=' + quote_plus(raw)
        if not raw.startswith(('http://', 'https://')):
            raw = 'https://' + raw
        return raw

    def _on_url_changed(self, u) -> None:
        try:
            txt = u.toString()
            self._url.setText(txt)
            host = QUrl(txt).host() or '—'
            self._source.setText(f'SOURCE · {host[:40]}')
        except Exception:
            pass

    def _on_load_started(self) -> None:
        try:
            self._progress.setValue(0)
            self._progress.show()
            self._status.setText('◌ LOADING…')
        except Exception:
            pass

    def _on_load_progress(self, pct: int) -> None:
        try:
            self._progress.setValue(max(0, min(100, int(pct))))
            self._status.setText(f'◌ LOADING… {int(pct)}%')
        except Exception:
            pass

    def _on_load_finished(self, ok: bool) -> None:
        try:
            self._progress.hide()
        except Exception:
            pass
        self._status.setText('● READY' if ok else '✕ LOAD ERROR')
        try:
            self._status.setStyleSheet(
                "color:#7affc3;font:700 7pt 'Exo 2';background:transparent;"
                if ok else "color:#ff7892;font:700 7pt 'Exo 2';background:transparent;")
        except Exception:
            pass

    def navigate(self):
        url = self._normalize(self._url.text())
        self._url.setText(url)
        if self.engine_enabled:
            self._on_load_started()
            self._engine.setUrl(QUrl(url))
        else:
            try:
                import webbrowser; webbrowser.open(url)
                self._status.setText(f'OPENED SYSTEM BROWSER · {url[:48]}')
            except Exception as exc:
                self._status.setText(f'WEBVIEW ERROR · {exc}')

    def back(self):
        if self.engine_enabled:
            self._engine.back()

    def forward(self):
        if self.engine_enabled:
            try:
                self._engine.forward()
            except Exception:
                pass

    def reload(self):
        if self.engine_enabled:
            self._on_load_started()
            self._engine.reload()
        else:
            self.navigate()

    def go_home(self):
        self._url.setText(self._home); self.navigate()


class WebTaskPane(QFrame):
    """Queue and run web research / browse tasks from a dedicated window."""
    task_run = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('background:transparent;border:none;')
        self._tasks = []
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(7)
        intro = QLabel('WEB TASK QUEUE  //  SEARCH · NEWS · RESEARCH · BROWSE')
        intro.setStyleSheet(f'color:{C.PRI};font:800 8pt "Exo 2";background:transparent;')
        lay.addWidget(intro)
        form = QGridLayout(); form.setHorizontalSpacing(7); form.setVerticalSpacing(6)
        self._kind = QComboBox(); self._kind.addItems(['search', 'news', 'research', 'price', 'browse']); self._kind.setStyleSheet(_hud_field_css())
        self._query = QLineEdit(); self._query.setPlaceholderText('Query, URL, or research brief…'); self._query.setStyleSheet(_hud_field_css())
        self._query.returnPressed.connect(self.add_task)
        form.addWidget(QLabel('MODE'), 0, 0); form.addWidget(self._kind, 0, 1)
        form.addWidget(QLabel('INPUT'), 1, 0); form.addWidget(self._query, 1, 1)
        lay.addLayout(form)
        row = QHBoxLayout(); row.setSpacing(6)
        add = _GlowButton('ADD TASK', '＋', compact=True); add.clicked.connect(self.add_task); row.addWidget(add)
        run = _GlowButton('RUN SELECTED', '▸', compact=True); run.clicked.connect(self.run_selected); row.addWidget(run)
        run_all = _GlowButton('RUN ALL', '▶', compact=True); run_all.clicked.connect(self.run_all); row.addWidget(run_all)
        clear = _GlowButton('CLEAR', '×', compact=True); clear.clicked.connect(self.clear_done); row.addWidget(clear)
        lay.addLayout(row)
        self._list = QListWidget(); self._list.setStyleSheet(_hud_field_css()); self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        lay.addWidget(self._list, 1)
        self._log = QLabel('0 queued · idle')
        self._log.setStyleSheet(f'color:{C.TEXT_MED};font:700 7pt "Exo 2";background:transparent;')
        lay.addWidget(self._log)

    def add_task(self):
        q = self._query.text().strip()
        if not q:
            return
        kind = self._kind.currentText()
        item = {'kind': kind, 'query': q, 'state': 'QUEUED'}
        self._tasks.append(item)
        self._query.clear()
        self._refresh()

    def _refresh(self):
        self._list.clear()
        for i, t in enumerate(self._tasks):
            self._list.addItem(f'{i+1:02d}  [{t["state"]}]  {t["kind"].upper()}  ·  {t["query"][:80]}')
        queued = sum(1 for t in self._tasks if t['state'] == 'QUEUED')
        self._log.setText(f'{len(self._tasks)} tasks · {queued} queued')

    def _command_for(self, task):
        k, q = task['kind'], task['query']
        if k == 'browse':
            return f'Open this URL and summarize the page: {q}'
        if k == 'news':
            return f'Search the latest news about: {q}'
        if k == 'research':
            return f'Research this topic in depth and report sources: {q}'
        if k == 'price':
            return f'Find current prices and compare options for: {q}'
        return f'Search the web for: {q}'

    def run_selected(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._tasks):
            if self._tasks:
                row = 0
            else:
                self.add_task(); row = len(self._tasks) - 1
                if row < 0:
                    return
        self._run_index(row)

    def run_all(self):
        if self._query.text().strip():
            self.add_task()
        for i, t in enumerate(self._tasks):
            if t['state'] == 'QUEUED':
                self._run_index(i)

    def _run_index(self, i):
        task = self._tasks[i]
        task['state'] = 'RUNNING'
        self._refresh()
        cmd = self._command_for(task)
        self.task_run.emit(cmd)
        if task['kind'] == 'browse':
            self.task_run.emit('__webview__:' + task['query'])
        task['state'] = 'SENT'
        self._refresh()

    def clear_done(self):
        self._tasks = [t for t in self._tasks if t['state'] == 'QUEUED']
        self._refresh()


class WorldMonitorPane(QFrame):
    """Global clocks, telemetry, and world headlines in a dedicated HUD."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('background:transparent;border:none;')
        self._headlines = ['Scanning world feeds…']
        self._city = 'Local'
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(7)
        hdr = QLabel('SYSTEM  //  LIVE TELEMETRY')
        hdr.setStyleSheet(_theme_section_css())
        lay.addWidget(hdr)
        clocks = QGridLayout(); clocks.setHorizontalSpacing(10); clocks.setVerticalSpacing(4)
        self._clock_labels = {}
        zones = [('LOCAL', None), ('UTC', 0), ('LONDON', 0), ('NEW YORK', -4), ('TOKYO', 9), ('MANILA', 8)]
        for i, (name, offset) in enumerate(zones):
            cap = QLabel(name); cap.setStyleSheet("color:#5796ad;font:700 7pt 'Exo 2';background:transparent;")
            val = QLabel('--:--:--'); val.setStyleSheet("color:#9ae8ff;font:800 11pt 'Orbitron';background:transparent;")
            clocks.addWidget(cap, 0, i); clocks.addWidget(val, 1, i); self._clock_labels[name] = (val, offset)
        lay.addLayout(clocks)
        meters = QGridLayout(); meters.setHorizontalSpacing(8); meters.setVerticalSpacing(8)
        self._meter_cpu = RefinedMeter('CPU'); self._meter_ram = RefinedMeter('RAM')
        self._meter_gpu = RefinedMeter('GPU'); self._meter_disk = RefinedMeter('DISK')
        meters.addWidget(self._meter_cpu, 0, 0); meters.addWidget(self._meter_ram, 0, 1)
        meters.addWidget(self._meter_gpu, 1, 0); meters.addWidget(self._meter_disk, 1, 1)
        lay.addLayout(meters)
        chips = QHBoxLayout(); chips.setSpacing(6)
        self._m_temp = QLabel('TEMP --'); self._m_net = QLabel('NET --'); self._m_batt = QLabel('BATT --')
        self._m_up = QLabel('UP --'); self._m_procs = QLabel('PROCS --')
        for w in (self._m_temp, self._m_net, self._m_batt, self._m_up, self._m_procs):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setStyleSheet(_theme_chip_css() + "font:700 7pt 'Exo 2';")
            chips.addWidget(w, 1)
        lay.addLayout(chips)
        feeds_lbl = QLabel('WORLD FEEDS  //  LIVE HEADLINES')
        feeds_lbl.setStyleSheet(_theme_section_css())
        lay.addWidget(feeds_lbl)
        self._globe = QLabel()
        self._globe.setMinimumHeight(118)
        self._globe.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._globe.setStyleSheet(_theme_card_css() + "color:#9ae8ff;")
        lay.addWidget(self._globe)
        self._news = QListWidget(); self._news.setStyleSheet(_hud_field_css()); self._news.setMinimumHeight(140)
        lay.addWidget(self._news, 1)
        row = QHBoxLayout(); row.setSpacing(6)
        refresh = _GlowButton('REFRESH FEEDS', '↻', compact=True); refresh.clicked.connect(self.refresh_feeds); row.addWidget(refresh)
        self._status = QLabel('● MONITOR ONLINE'); self._status.setStyleSheet("color:#7affc3;font:700 7pt 'Exo 2';background:transparent;" + _theme_icon_font_css())
        row.addWidget(self._status, 1); lay.addLayout(row)
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick); self._timer.start(1000)
        self._tick(); QTimer.singleShot(400, self.refresh_feeds)

    def _tick(self):
        now = datetime.now()
        utc = datetime.now(timezone.utc)
        for name, (lab, offset) in self._clock_labels.items():
            if offset is None:
                lab.setText(now.strftime('%H:%M:%S'))
            else:
                lab.setText((utc + timedelta(hours=offset)).strftime('%H:%M:%S'))
        try:
            s = _metrics.snapshot()
            gpu_v = float(s.get('gpu', -1))
            gpu_t = f'{gpu_v:.0f}%' if gpu_v >= 0 else 'N/A'
            self._meter_cpu.set_value(s.get('cpu', 0), f"{s.get('cpu', 0):.0f}%")
            self._meter_ram.set_value(s.get('mem', 0), f"{s.get('mem', 0):.0f}%")
            self._meter_gpu.set_value(gpu_v if gpu_v >= 0 else 0, gpu_t)
            self._meter_disk.set_value(s.get('disk', 0), f"{s.get('disk', 0):.0f}%")
            tmp_v = s.get('tmp', -1)
            self._m_temp.setText(f"TEMP {tmp_v:.0f}°C" if isinstance(tmp_v, (int, float)) and tmp_v >= 0 else 'TEMP --')
            net_v = s.get('net', 0)
            self._m_net.setText(f'NET {net_v:.0f} KB/s' if isinstance(net_v, (int, float)) else 'NET --')
            batt_v = s.get('batt', -1)
            if isinstance(batt_v, (int, float)) and batt_v >= 0:
                plug = '⚡' if s.get('plugged') else ''
                self._m_batt.setText(f'BATT {batt_v:.0f}%{plug}')
            else:
                self._m_batt.setText('BATT --')
            self._m_up.setText(f"UP {_fmt_uptime(s.get('uptime', 0))}")
            self._m_procs.setText(f"PROCS {int(s.get('procs', 0) or 0)}")
        except Exception:
            pass
        self._paint_globe()

    def _paint_globe(self):
        w, h = max(320, self._globe.width()), max(110, self._globe.height())
        px = QPixmap(w, h); px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx, cy, rad = w * 0.22, h * 0.5, min(w, h) * 0.38
        p.setPen(QPen(qcol(C.PRI, 80), 1)); p.setBrush(QBrush(qcol(C.PRI_GHO, 90))); p.drawEllipse(QPointF(cx, cy), rad, rad)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for k in (0.45, 0.72, 1.0):
            p.drawEllipse(QPointF(cx, cy), rad * k, rad * k)
        p.drawLine(QPointF(cx - rad, cy), QPointF(cx + rad, cy))
        p.drawLine(QPointF(cx, cy - rad), QPointF(cx, cy + rad))
        pulse = (time.time() % 4.0) / 4.0
        p.setPen(QPen(qcol(C.ACC, 180), 2)); p.drawEllipse(QPointF(cx + rad * 0.35, cy - rad * 0.18), 3 + pulse * 4, 3 + pulse * 4)
        p.setPen(qcol(C.TEXT)); p.setFont(QFont('Exo 2', 8, QFont.Weight.Bold))
        p.drawText(QRectF(w * 0.46, 10, w * 0.52, h - 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f'WORLD GRID ACTIVE\nLAT/LON SWEEP  {pulse*360:.0f}°\nFEEDS  {len(self._headlines)}\nNODE  {self._city}')
        p.end(); self._globe.setPixmap(px)

    def refresh_feeds(self):
        self._status.setText('SCANNING FEEDS…')
        threading.Thread(target=self._fetch_feeds, daemon=True).start()

    def _fetch_feeds(self):
        headlines = []
        try:
            req = urllib.request.Request(
                'https://feeds.bbci.co.uk/news/world/rss.xml',
                headers={'User-Agent': 'JARVIS-WorldMonitor/1.0'},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml = resp.read().decode('utf-8', errors='ignore')
            import re
            headlines = [re.sub(r'<[^>]+>', '', t).strip() for t in re.findall(r'<title>(.*?)</title>', xml, re.I | re.S)][1:12]
        except Exception as exc:
            headlines = [f'Feed offline — {exc}', 'Using local telemetry only.']
        if not headlines:
            headlines = ['No headlines returned.']
        self._headlines = headlines
        QTimer.singleShot(0, self._apply_feeds)

    def _apply_feeds(self):
        self._news.clear()
        for h in self._headlines:
            self._news.addItem('▸  ' + h)
        self._status.setText(f'{len(self._headlines)} HEADLINES · LIVE')


class MemoryMonitorPane(QFrame):
    """Refined memory core: stats, sections, search, save, edit, delete."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('background:transparent;border:none;')
        self._rows = []
        self._cat_filter = 'All'
        self._clear_armed = False
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(7)
        title = QLabel('MEMORY CORE  //  RECENT · LONG-TERM · PREFERENCES')
        title.setStyleSheet(_theme_section_css())
        lay.addWidget(title)
        stats = QHBoxLayout(); stats.setSpacing(6)
        self._stat_total = QLabel('FACTS --'); self._stat_cats = QLabel('AREAS --'); self._stat_new = QLabel('NEWEST --')
        for w in (self._stat_total, self._stat_cats, self._stat_new):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setStyleSheet(_theme_chip_css() + "font:700 7pt 'Exo 2';")
            stats.addWidget(w, 1)
        lay.addLayout(stats)
        self._cap = QLabel('Loading memory…')
        self._cap.setWordWrap(True)
        self._cap.setStyleSheet("color:#5796ad;font:7pt 'Exo 2';background:transparent;")
        lay.addWidget(self._cap)
        search_row = QHBoxLayout(); search_row.setSpacing(6)
        self._search = QLineEdit(); self._search.setPlaceholderText('Search facts…'); self._search.setStyleSheet(_hud_field_css())
        self._search.setMinimumHeight(30)
        self._search.textChanged.connect(self._render)
        search_row.addWidget(self._search, 1)
        self._catbox = QComboBox(); self._catbox.addItem('All'); self._catbox.setStyleSheet(_hud_field_css())
        self._catbox.setMinimumHeight(30)
        self._catbox.currentTextChanged.connect(self._on_cat_filter)
        search_row.addWidget(self._catbox)
        reload_b = _GlowButton('RELOAD', '↻', compact=True); reload_b.clicked.connect(self.reload); search_row.addWidget(reload_b)
        lay.addLayout(search_row)
        self._list = QListWidget(); self._list.setStyleSheet(_hud_field_css()); lay.addWidget(self._list, 1)
        add = QGridLayout(); add.setHorizontalSpacing(6); add.setVerticalSpacing(5)
        self._cat = QComboBox(); self._cat.addItems(['notes', 'identity', 'preferences', 'projects', 'relationships', 'wishes']); self._cat.setStyleSheet(_hud_field_css())
        self._key = QLineEdit(); self._key.setPlaceholderText('key'); self._key.setStyleSheet(_hud_field_css())
        self._val = QLineEdit(); self._val.setPlaceholderText('value to remember'); self._val.setStyleSheet(_hud_field_css())
        self._val.returnPressed.connect(self.add_fact)
        add.addWidget(self._cat, 0, 0); add.addWidget(self._key, 0, 1); add.addWidget(self._val, 0, 2)
        lay.addLayout(add)
        row = QHBoxLayout(); row.setSpacing(6)
        save = _GlowButton('REMEMBER', '◆', compact=True); save.clicked.connect(self.add_fact); row.addWidget(save)
        forget = _GlowButton('FORGET SELECTED', '✕', compact=True); forget.clicked.connect(self.forget_selected); row.addWidget(forget)
        self._clear_btn = _GlowButton('CLEAR ALL', '⚠', compact=True); self._clear_btn.clicked.connect(self.clear_all); row.addWidget(self._clear_btn)
        lay.addLayout(row)
        self.reload()

    def _on_cat_filter(self, text: str) -> None:
        self._cat_filter = text
        self._render()

    def reload(self):
        try:
            from memory.memory_manager import all_entries_for_ui
            self._rows = all_entries_for_ui()
        except Exception as exc:
            self._rows = []
            self._cap.setText(f'Memory load failed: {exc}')
            return
        cats = sorted({str(r.get('category', '')) for r in self._rows if r.get('category')})
        try:
            keep = self._catbox.currentText()
            self._catbox.blockSignals(True)
            self._catbox.clear()
            self._catbox.addItem('All')
            self._catbox.addItems(cats)
            if keep in (['All'] + cats):
                self._catbox.setCurrentText(keep)
                self._cat_filter = keep
            self._catbox.blockSignals(False)
        except Exception:
            pass
        try:
            newest = self._rows[0]['updated'] if self._rows else '—'
            self._stat_total.setText(f'FACTS {len(self._rows)}')
            self._stat_cats.setText(f'AREAS {len(cats)}')
            self._stat_new.setText(f'NEWEST {str(newest)[:10]}')
        except Exception:
            pass
        self._cap.setText(f'{len(self._rows)} stored facts in memory/long_term.json — newest first.')
        self._disarm_clear()
        self._render()

    def _render(self):
        q = self._search.text().strip().lower()
        self._list.clear()
        for r in self._rows:
            line = f"{r['category']}/{r['key']} — {r['value']}   [{r['updated'] or '—'}]"
            if self._cat_filter != 'All' and str(r.get('category', '')) != self._cat_filter:
                continue
            if q and q not in line.lower():
                continue
            item = QListWidgetItem(line)
            item.setData(Qt.ItemDataRole.UserRole, (r['category'], r['key']))
            self._list.addItem(item)
        if self._list.count() == 0:
            self._list.addItem('Nothing stored yet. Add a fact below.')

    def _disarm_clear(self) -> None:
        self._clear_armed = False
        try:
            self._clear_btn.setText('CLEAR ALL')
        except Exception:
            pass

    def clear_all(self):
        """Two-press arm/disarm wipe of every stored fact (no surprises)."""
        if not self._clear_armed:
            self._clear_armed = True
            try:
                self._clear_btn.setText('SURE?')
            except Exception:
                pass
            self._cap.setText('Press CLEAR ALL again within 4 seconds to forget everything.')
            QTimer.singleShot(4000, self._disarm_clear)
            return
        self._disarm_clear()
        try:
            from memory.memory_manager import forget as _forget
            n = 0
            for r in list(self._rows):
                try:
                    _forget(r['key'], r['category'])
                    n += 1
                except Exception:
                    pass
            self.reload()
            self._cap.setText(f'Forgot {n} facts. Memory is clear.')
        except Exception as exc:
            self._cap.setText(f'Clear failed: {exc}')

    def add_fact(self):
        key = self._key.text().strip().replace(' ', '_')
        val = self._val.text().strip()
        if not key or not val:
            self._cap.setText('Enter both a key and a value to remember.')
            return
        try:
            from memory.memory_manager import remember
            remember(key, val, self._cat.currentText())
            self._key.clear(); self._val.clear()
            self.reload()
            self._cap.setText(f'Remembered {self._cat.currentText()}/{key}.')
        except Exception as exc:
            self._cap.setText(f'Remember failed: {exc}')

    def forget_selected(self):
        item = self._list.currentItem()
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        try:
            from memory.memory_manager import forget
            forget(data[1], data[0])
            self.reload()
        except Exception as exc:
            self._cap.setText(f'Forget failed: {exc}')


class _ActivityTimeline(QFrame):
    """Refined JARVIS activity timeline: categorized cards with timestamps,
    status dots, text filter and smooth fade-in on every new entry."""
    MAX_ENTRIES = 60

    _CATS = (
        (('you:', 'voice:', 'mic:'),            'VOICE', '#e9fcff'),
        (('jarvis:', 'j.a.r.v.i.s', 'ai:'),     'AI',    '#9ae8ff'),
        (('err', 'fail', 'exception', 'trace'), 'ERROR', '#ff7892'),
        (('ok', 'done', 'complete', 'sent'),    'OK',    '#7affc3'),
        (('file:',),                            'FILE',  '#7affc3'),
        (('tool', 'exec', 'run:'),              'TOOL',  '#ffcc66'),
        (('web', 'search', 'fetch'),            'WEB',   '#42c7ef'),
        (('warn',),                             'WARN',  '#ffcc66'),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('background:transparent;border:none;')
        self._entries: list[dict] = []
        self._filter = 'ALL'
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet('QScrollArea{background:transparent;border:none;}' + _theme_scrollbar_css(5))
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._cl = QVBoxLayout(self._container)
        self._cl.setContentsMargins(2, 2, 2, 2)
        self._cl.setSpacing(6)
        self._cl.addStretch(1)
        self._scroll.setWidget(self._container)
        lay.addWidget(self._scroll, 1)

    @classmethod
    def _categorize(cls, text: str):
        tl = text.strip().lower()
        for prefixes, tag, color in cls._CATS:
            if tl.startswith(prefixes) or f' {prefixes[0]}' in tl[:14]:
                return tag, color
        if tl.startswith('sys:'):
            return 'SYS', '#659fb1'
        return 'SYS', '#659fb1'

    def set_filter(self, tag: str) -> None:
        self._filter = str(tag or 'ALL').upper()
        self._render()

    def count(self) -> int:
        return len(self._entries)

    def lines(self, n: int = 80) -> list[str]:
        try:
            return [f"[{e['time']}] [{e['tag']}] {e['text']}" for e in self._entries[:max(1, int(n))]]
        except Exception:
            return []

    def add_entry(self, text: str) -> None:
        text = str(text or '').strip()
        if not text:
            return
        try:
            stamp = time.strftime('%H:%M:%S')
        except Exception:
            stamp = '--:--:--'
        tag, color = self._categorize(text)
        self._entries.insert(0, {'time': stamp, 'tag': tag, 'color': color, 'text': text[:280]})
        del self._entries[self.MAX_ENTRIES:]
        self._render(new_first=(not self._filter or self._filter == 'ALL' or self._filter == tag))

    def _render(self, new_first: bool = False) -> None:
        # rebuild visible cards (cheap: <= 60 small widgets)
        while self._cl.count() > 1:
            item = self._cl.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        shown = 0
        for i, e in enumerate(self._entries):
            if self._filter != 'ALL' and e['tag'] != self._filter:
                continue
            card = self._make_card(e)
            self._cl.insertWidget(shown, card)
            shown += 1
            if new_first and i == 0:
                self._fade_in(card)
        try:
            self._scroll.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def _make_card(self, e: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:rgba(1,17,27,120);"
            " border:1px solid rgba(67,151,185,70); border-radius:8px; }"
        )
        hl = QHBoxLayout(card)
        hl.setContentsMargins(9, 6, 9, 6)
        hl.setSpacing(8)
        dot = QLabel('●')
        dot.setStyleSheet(f"color:{e['color']};font-size:9px;background:transparent;{_theme_icon_font_css()}")
        dot.setFixedWidth(12)
        hl.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
        vb = QVBoxLayout()
        vb.setSpacing(2)
        vb.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        head.setSpacing(8)
        tag = QLabel(e['tag'])
        tag.setStyleSheet(f"color:{e['color']};font:700 7pt 'Exo 2';background:transparent;")
        head.addWidget(tag)
        head.addStretch(1)
        ts = QLabel(e['time'])
        ts.setStyleSheet("color:#3a6a7a;font:700 7pt 'Exo 2';background:transparent;")
        head.addWidget(ts)
        vb.addLayout(head)
        body = QLabel(e['text'])
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet("color:#b9efff;font:8pt 'Share Tech Mono';background:transparent;")
        vb.addWidget(body)
        hl.addLayout(vb, 1)
        return card

    def _fade_in(self, card: QFrame) -> None:
        try:
            eff = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(eff)
            eff.setOpacity(0.0)
            anim = QPropertyAnimation(eff, b'opacity', card)
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda: card.setGraphicsEffect(None))
            anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        except Exception:
            pass


class ToolsPane(QFrame):
    """Refined tools deck: every JARVIS capability as a categorized card
    with status and a RUN action wired to the existing backend."""
    CATEGORIES = ('All', 'Computer Control', 'Browser', 'Files', 'Screen',
                  'Media', 'System', 'Automation', 'Coding', 'Memory', 'Plugins')

    def __init__(self, host=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet('background:transparent;border:none;')
        self._host = host
        self._entries: list[dict] = []
        self._filter = 'All'
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(7)
        top = QHBoxLayout()
        top.setSpacing(6)
        self._search = QLineEdit()
        self._search.setPlaceholderText('Search tools…')
        self._search.setStyleSheet(_hud_field_css())
        self._search.setMinimumHeight(30)
        self._search.textChanged.connect(self._render)
        top.addWidget(self._search, 1)
        self._cat = QComboBox()
        self._cat.addItems(list(self.CATEGORIES))
        self._cat.setStyleSheet(_hud_field_css())
        self._cat.setMinimumHeight(30)
        self._cat.currentTextChanged.connect(self._on_cat)
        top.addWidget(self._cat)
        lay.addLayout(top)
        self._count = QLabel('')
        self._count.setStyleSheet("color:#5796ad;font:700 7pt 'Exo 2';background:transparent;")
        lay.addWidget(self._count)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet('QScrollArea{background:transparent;border:none;}' + _theme_scrollbar_css(5))
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._cl = QVBoxLayout(self._container)
        self._cl.setContentsMargins(2, 2, 2, 2)
        self._cl.setSpacing(7)
        self._cl.addStretch(1)
        self._scroll.setWidget(self._container)
        lay.addWidget(self._scroll, 1)

    def _on_cat(self, text: str) -> None:
        self._filter = text
        self._render()

    def reload(self) -> None:
        try:
            host = self._host() if callable(self._host) else self._host
            if host is not None and hasattr(host, 'get_tool_entries'):
                self._entries = list(host.get_tool_entries() or [])
        except Exception:
            pass
        self._render()

    def _render(self) -> None:
        q = self._search.text().strip().lower() if hasattr(self, '_search') else ''
        while self._cl.count() > 1:
            item = self._cl.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        shown = 0
        for e in self._entries:
            if self._filter != 'All' and e.get('category') != self._filter:
                continue
            hay = f"{e.get('name','')} {e.get('desc','')}".lower()
            if q and q not in hay:
                continue
            self._cl.insertWidget(shown, self._make_card(e))
            shown += 1
        try:
            self._count.setText(f'{shown} of {len(self._entries)} tools ready')
        except Exception:
            pass

    def _make_card(self, e: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:rgba(1,17,27,120);"
            " border:1px solid rgba(67,151,185,70); border-radius:8px; }"
        )
        hl = QHBoxLayout(card)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(9)
        icon = QLabel(e.get('icon', '▣'))
        icon.setStyleSheet("color:#42c7ef;font-size:15px;background:transparent;" + _theme_icon_font_css())
        icon.setFixedWidth(22)
        hl.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        vb = QVBoxLayout()
        vb.setSpacing(3)
        vb.setContentsMargins(0, 0, 0, 0)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        name = QLabel(str(e.get('name', 'tool')).upper())
        name.setStyleSheet("color:#dff8ff;font:700 8pt 'Orbitron';letter-spacing:1px;background:transparent;border:none;")
        title_row.addWidget(name, 1)
        avail = bool(e.get('available', True))
        dot = QLabel('● READY' if avail else '○ OFF')
        dot.setStyleSheet(f"color:{'#7affc3' if avail else '#5796ad'};font:700 7pt 'Exo 2';background:transparent;")
        title_row.addWidget(dot)
        vb.addLayout(title_row)
        cat = QLabel(str(e.get('category', '')))
        cat.setStyleSheet("color:#5796ad;font:600 7pt 'Exo 2';background:transparent;")
        vb.addWidget(cat)
        desc = QLabel(str(e.get('desc', '')))
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#9ae8ff;font:8pt 'Rajdhani';background:transparent;")
        vb.addWidget(desc)
        hl.addLayout(vb, 1)
        run = QPushButton('RUN')
        run.setFixedSize(56, 32)
        run.setCursor(Qt.CursorShape.PointingHandCursor)
        run.setStyleSheet(
            "QPushButton { color:#edfcff; background:rgba(0,111,151,170);"
            " border:1px solid #75e2fa; border-radius:7px; font:700 7pt 'Exo 2'; }"
            "QPushButton:hover { background:rgba(0,154,199,210); }"
            "QPushButton:disabled { color:#3a6a7a; border-color:rgba(67,151,185,40);"
            " background:rgba(1,17,27,80); }"
        )
        run.setEnabled(avail)
        run.setToolTip(str(e.get('desc', 'Run this tool')))
        run.clicked.connect(lambda _=False, entry=dict(e): self._run_entry(entry))
        hl.addWidget(run, 0, Qt.AlignmentFlag.AlignVCenter)
        return card

    def _run_entry(self, entry: dict) -> None:
        try:
            _sfx('click')
        except Exception:
            pass
        try:
            host = self._host() if callable(self._host) else self._host
            if host is None:
                return
            action = entry.get('action')
            if action == 'open_web_task' and hasattr(host, '_open_web_task_panel'):
                host._open_web_task_panel()
                return
            if action == 'open_window' and hasattr(host, 'control_jarvis_window'):
                host.control_jarvis_window(entry.get('window', 'webview'), 'open')
                return
            run_text = (entry.get('run') or '').strip()
            if run_text and hasattr(host, '_send_backend_command'):
                try:
                    host._activity_add(f"YOU: {run_text}")
                except Exception:
                    pass
                host._send_backend_command(run_text)
        except Exception:
            pass


class WorkspaceWindowPane(QFrame):
    """Generic HUD workspace window the user can title and annotate."""
    def __init__(self, parent=None, title='WORKSPACE'):
        super().__init__(parent)
        self.setStyleSheet('background:transparent;border:none;')
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        self._title = QLineEdit(title); self._title.setStyleSheet(_hud_field_css())
        lay.addWidget(self._title)
        self._notes = QTextEdit(); self._notes.setPlaceholderText('Drop notes, links, or live status for this window…')
        self._notes.setStyleSheet(_hud_field_css()); lay.addWidget(self._notes, 1)
        row = QHBoxLayout(); row.setSpacing(6)
        pin = QLabel('DRAGGABLE HUD WINDOW  ·  EDIT TITLE  ·  RESIZE FROM CORNER')
        pin.setStyleSheet(f'color:{C.TEXT_DIM};font:700 7pt "Exo 2";background:transparent;')
        row.addWidget(pin, 1); lay.addLayout(row)


class _LayoutElementWidget(QWidget):
    """Simple draggable widget used by the UI Layout Editor."""
    def __init__(self, kind: str, text: str, color: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._text = text
        self._color = color
        self._drag_start = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._label = None
        if kind == 'Text':
            self._label = QLabel(text, self)
            self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._label.setStyleSheet(f'background:transparent;color:{color};font:700 13px "Rajdhani";')
        elif kind == 'Button':
            self._label = QPushButton(text, self)
            self._label.setStyleSheet(f'QPushButton{{background:rgba(0,24,36,190);color:{color};border:1px solid {color};border-radius:8px;padding:6px 10px;}}')
            self._label.setGeometry(self.rect())
            self._label.setEnabled(False)
        elif kind in ('Panel', 'Window', 'Monitor', 'WebView'):
            self.setStyleSheet(f'background:rgba(0,14,24,110);border:1px solid {color};border-radius:10px;')
        elif kind == 'Separator':
            self.setStyleSheet(f'background:{color};border:none;')

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._label is not None:
            self._label.setGeometry(self.rect())

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            e.accept(); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_start is not None and e.buttons() & Qt.MouseButton.LeftButton:
            d = e.globalPosition().toPoint() - self._drag_start
            self.move(self.pos() + d)
            self._drag_start = e.globalPosition().toPoint()
            e.accept(); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if hasattr(self.window(), '_save_layout_elements'):
                self.window()._save_layout_elements()
            e.accept(); return
        super().mouseReleaseEvent(e)


class MainWindow(QMainWindow):
    """Responsive frameless glass HUD. Backend callbacks remain compatible with main.py."""
    _state_sig = pyqtSignal(str)
    _log_sig = pyqtSignal(str)
    _content_sig = pyqtSignal(str, str)
    _reconfig_sig = pyqtSignal()
    _camera_sig = pyqtSignal(bytes)
    _cam_stream_sig = pyqtSignal(bool)
    _cam_frame_sig = pyqtSignal(bytes)
    _confirm_sig = pyqtSignal(str, str)
    _confirm_hide_sig = pyqtSignal()
    _image_bytes_sig = pyqtSignal(bytes, str)
    _gui_exec_sig = pyqtSignal(object)

    EXPANDED_SIZE = QSize(1380, 840)
    COLLAPSED_SIZE = QSize(136, 136)

    def __init__(self, face_path: str):
        super().__init__()
        cfg = _ui_load(API_FILE)
        global DISPLAY_FONT
        DISPLAY_FONT = _register_redesign_font()
        _register_app_fonts()
        self._face_path = face_path
        self._assistant_name = (cfg.get('assistant_name') or 'JARVIS').strip() or 'JARVIS'
        self._muted = False
        self._voice_input_enabled = True
        self._current_file = None
        self._ready = self._check_config()
        self.get_plugins = None
        self.request_say = None
        self.on_text_command = None
        self.on_remote_clicked = None
        self.on_interrupt = None
        self.on_voice_change = None
        self.on_audio_device_change = None
        self._confirm_overlay = None
        self._customize_overlay = None
        self._overlay = None
        self._collapsed = True
        self._panel_alpha = int(cfg.get('ui_opacity', 82) or 82)
        self._font_family = cfg.get('ui_font') or 'Rajdhani'
        self._drag_pos = None
        self._cam_stop = threading.Event()
        self._panel_animations = {}
        self._quick_popup = None
        self._command_window = None
        self._chat_history = []
        self._custom_quick_actions = list(cfg.get("quick_actions", [])) if isinstance(cfg.get("quick_actions", []), list) else []
        self._layout_editor = None
        self._layout_elements = {}
        self._layout_widgets = {}
        self._reactor_opacity = int(cfg.get('reactor_opacity', 60) or 60)
        self._reactor_stroke_opacity = int(cfg.get('reactor_stroke_opacity', 100) or 100)
        self._features = dict(cfg.get('features', {})) if isinstance(cfg.get('features', {}), dict) else {}
        self._drag_reactor_enabled = bool(self._features.get('drag_reactor', True))
        self._music_webview_enabled = bool(self._features.get('webview_music', True))
        self._reactor_speed = float(cfg.get('reactor_animation_speed', 1.0) or 1.0)
        self._eq_sensitivity = float(cfg.get('equalizer_sensitivity', 1.0) or 1.0)
        # Startup choreography: show the large reactor at screen center first.
        # Movement to the remembered position is intentionally deferred until
        # JARVIS has actually spoken once, so startup feels like a real boot sequence.
        self._startup_waiting_for_voice = False
        self._startup_voice_seen = False
        self._startup_position_animated = False
        self._startup_target_pos = None
        self._startup_transitioning = False
        self._compact_alpha = 0
        self._compact_size = max(150, min(500, int(cfg.get("compact_size", 150) or 150)))

        _ui_color = (cfg.get('ui_color') or '').strip()
        if _ui_color:
            apply_ui_accent(_ui_color)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        # Keep the minimum at collapsed size so the window can freely switch
        # between the compact reactor and full HUD. The previous implementation
        # set the minimum to the expanded size before resizing, which caused
        # inconsistent geometry and 'only a circle' layouts.
        self.setMinimumSize(QSize(self._compact_size, self._compact_size))
        self.setMaximumSize(QSize(self._compact_size, self._compact_size))
        self.resize(QSize(self._compact_size, self._compact_size))
        self.setFont(QFont(self._font_family, 10))
        self.setWindowTitle('J.A.R.V.I.S')

        self._build_ui()
        self._wire_signals()
        self._apply_initial_visibility()
        self._load_layout_elements()
        self._header_logo.set_graphic_opacity(self._reactor_opacity)
        self._header_logo.set_stroke_opacity(self._reactor_stroke_opacity)
        self._header_logo._animation_speed = self._reactor_speed
        self._hide_taskbar_button = bool(self._features.get('hide_taskbar_button', self._features.get('hide_taskbar', False)))
        self._set_taskbar_button_hidden(self._hide_taskbar_button)
        try:
            from core import sfx as _sfx_mod
            _sfx_mod.configure(
                enabled=bool(self._features.get('enable_sfx', True)),
                volume=float(cfg.get('voice_volume', 1.0) or 1.0) * 0.35,
            )
        except Exception:
            pass
        if not self._ready:
            QTimer.singleShot(120, self._show_setup)
        else:
            self._restore_window_position(animate=True)

    def _surface_style(self):
        opaque = max(40, min(245, int(255*self._panel_alpha/100)))
        return f"""QFrame#Surface {{
            background: rgba(1, 8, 16, {opaque});
            border: none;
            border-radius: 3px;
        }}"""

    def _build_ui(self):
        root = QWidget(); root.setObjectName('Root'); root.setStyleSheet('background: transparent;')
        self.setCentralWidget(root)
        root_l = QVBoxLayout(root); root_l.setContentsMargins(0,0,0,0); root_l.setSpacing(0); self._root_layout = root_l

        self.surface = QFrame(); self.surface.setObjectName('Surface'); self.surface.setStyleSheet(self._surface_style())
        root_l.addWidget(self.surface)
        sl = QVBoxLayout(self.surface); sl.setContentsMargins(18,14,18,16); sl.setSpacing(10)

        self._topbar = QFrame(); self._topbar.setStyleSheet('background: transparent;')
        hb = QHBoxLayout(self._topbar); hb.setContentsMargins(2,0,2,0); hb.setSpacing(7); self._header_layout = hb
        self._header_logo = _ArcLogoButton(size=max(112, self._compact_size - 8)); self._header_logo.clicked.connect(self._toggle_command_window)
        hb.addWidget(self._header_logo)
        self._brand = QLabel('J.A.R.V.I.S'); self._brand.setStyleSheet(f'color:{C.PRI};font-size:17px;font-weight:800;letter-spacing:3px;background:transparent;')
        hb.addWidget(self._brand)
        self._status = QLabel('VOICE LINK · ONLINE'); self._status.setStyleSheet(f'color:{C.TEXT_MED};font-size:9px;background:transparent;')
        hb.addWidget(self._status)
        hb.addStretch(1)
        self._top_metrics = QLabel('CPU --%   RAM --%   GPU --%'); self._top_metrics.setStyleSheet(f'color:{C.TEXT_DIM};font-size:8px;background:transparent;')
        hb.addWidget(self._top_metrics)
        self._settings_btn = self._mini_button('⚙', 'Settings')
        self._min_btn = self._mini_button('—', 'Minimize')
        self._close_btn = self._mini_button('×', 'Close')
        sl.addWidget(self._topbar)

        self._main_row = QWidget(); mr = QHBoxLayout(self._main_row); mr.setContentsMargins(0,0,0,0); mr.setSpacing(12)
        self.hud = HudCanvas(self._face_path, self._assistant_name.upper())
        mr.addWidget(self.hud, 1)
        self.quick_panel = self._build_quick_panel()
        self.quick_panel.hide()
        sl.addWidget(self._main_row, 1)

        self._statusbar = QLabel('LISTENING · F4 MUTE · F11 FULLSCREEN · ESC INTERRUPT')
        self._statusbar.setStyleSheet(f'color:{C.TEXT_DIM};font-size:8px;background:transparent;padding:2px 4px;')
        sl.addWidget(self._statusbar)

        self._panel_launcher = None # legacy launcher intentionally removed
        self._video_preview_widget = VideoPreview()
        self._video_panel = self._build_floating_panel(self._video_preview_widget, 'video')
        self._hide_video_title(self._video_panel)
        self._activity_panel = self._build_activity_panel()
        self._image_panel = self._build_image_panel()
        self._content_panel = self._build_content_panel()
        self._model_panel = self._build_model_panel()
        home = str((_ui_load(API_FILE) or {}).get('web_homepage') or 'https://www.google.com')
        web_features = self._features
        self._webview_pane = WebViewPane(
            home=home,
            use_engine=bool(web_features.get('webview_engine', True)),
        )
        self._webview_panel = self._build_floating_panel(self._webview_pane, 'web')
        self._web_task_pane = WebTaskPane()
        self._web_task_pane.task_run.connect(self._on_web_task)
        self._web_task_panel = self._build_floating_panel(self._web_task_pane, 'task')
        self._world_monitor_pane = WorldMonitorPane()
        self._world_monitor_panel = self._build_floating_panel(self._world_monitor_pane, 'world')
        self._memory_pane = MemoryMonitorPane()
        self._memory_panel = self._build_floating_panel(self._memory_pane, 'memory')
        self._tools_pane = ToolsPane(self)
        self._tools_panel = self._build_floating_panel(self._tools_pane, 'tools')
        self._workspace_windows = []
        self._system_layout_widgets = {
            'Video Preview': self._video_panel,
            'Image Preview': self._image_panel,
            'Activity Log': self._activity_panel,
            'Content Surface': self._content_panel,
            '3D Display': self._model_panel,
            'Webview': self._webview_panel,
            'Web Task': self._web_task_panel,
            'World Monitor': self._world_monitor_panel,
            'Memory Core': self._memory_panel,
            'Tools Deck': self._tools_panel,
        }

        for panel in (self._video_panel, self._activity_panel, self._image_panel, self._content_panel, self._model_panel,
                      self._webview_panel, self._web_task_panel, self._world_monitor_panel, self._memory_panel,
                      self._tools_panel):
            panel.hide(); panel.raise_()

        self._clock_timer = QTimer(self); self._clock_timer.timeout.connect(self._update_clock); self._clock_timer.start(1000)
        self._metrics_timer = QTimer(self); self._metrics_timer.timeout.connect(self._update_metrics); self._metrics_timer.start(1500)
        self._update_clock(); self._update_metrics()

        self._cam_preview = _CameraPreview(None); self._cam_preview.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint); self._cam_preview.hide()
        # Webcam-only window: feathered video, no panels, no background.
        self._cam_live_lbl = _FeatheredCamView(None); self._cam_live_lbl.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint); self._cam_live_lbl.hide()
        # draggable: reuse the same popup-drag plumbing as the Quick Actions window
        self._cam_live_lbl.setProperty('_jarvis_popup_drag', True)
        self._cam_live_lbl.installEventFilter(self)
        self._cam_live_lbl.setCursor(Qt.CursorShape.SizeAllCursor)

    def _wire_signals(self):
        self._state_sig.connect(self._apply_state)
        self._log_sig.connect(self._log_from_backend)
        self._content_sig.connect(self.show_content)
        self._reconfig_sig.connect(self._show_setup)
        self._camera_sig.connect(self._show_camera_frame)
        self._cam_stream_sig.connect(self._on_cam_stream)
        self._cam_frame_sig.connect(self._on_cam_frame)
        self._confirm_sig.connect(self._show_confirm_banner)
        self._confirm_hide_sig.connect(self._hide_confirm_banner)
        self._image_bytes_sig.connect(self._show_image_bytes)
        self._gui_exec_sig.connect(self._run_gui_task)
        QShortcut(QKeySequence('F4'), self).activated.connect(self._toggle_mute)
        QShortcut(QKeySequence('F11'), self).activated.connect(self._toggle_fullscreen)
        QShortcut(QKeySequence('Escape'), self).activated.connect(self._do_interrupt)
        QShortcut(QKeySequence('Ctrl+Shift+Space'), self).activated.connect(self.toggle_panels)
        QShortcut(QKeySequence('F6'), self).activated.connect(self._toggle_push_to_talk)
        close_shortcut = QShortcut(QKeySequence('Shift+Home'), self)
        close_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        close_shortcut.activated.connect(self._close_all_ui)
        # Settings always opens the standalone tabbed Control Center.
        self._settings_btn.clicked.connect(self._open_full_settings)
        self._topbar.installEventFilter(self)

    def _mini_button(self, text, tip):
        b = QPushButton(text); b.setToolTip(tip); b.setFixedSize(30,30); b.setCursor(Qt.CursorShape.PointingHandCursor)
        radius = 0 if text == '×' else 7
        b.setStyleSheet(f"""QPushButton{{background:rgba(0,18,28,180);color:{C.TEXT_MED};border:1px solid {C.BORDER};border-radius:{radius}px;font-size:13px;}}
                           QPushButton:hover{{color:{C.PRI};border:1px solid {C.PRI};background:{C.PRI_GHO};}}""")
        return b

    def _panel_base(self):
        f = _HudPanel(None)
        f.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        f.setMinimumSize(260, 180)
        # Unified redesign shell used by video/image/web/system/world/memory/etc.
        f.setStyleSheet(
            "QFrame { background: rgba(1, 10, 20, 238); border: none; border-radius: 14px; }"
            "QLabel { background: transparent; }"
        )
        # Every floating JARVIS panel is a real independent window.  Give it a
        # stable drag identity so movement can be saved/restored.
        f.setProperty('_jarvis_floating_panel', True)
        f.setMouseTracking(True)
        return f

    def _panel_header(self, parent, icon='✦', close_cb=None, title='', subtitle=''):
        bar = QFrame(parent)
        bar.setFixedHeight(40)
        bar.setStyleSheet(_theme_header_css())
        row = QHBoxLayout(bar); row.setContentsMargins(12, 4, 6, 4); row.setSpacing(8)
        icon_l = QLabel(icon, bar); icon_l.setStyleSheet(f'color:{C.PRI};font-size:14px;background:transparent;{_theme_icon_font_css()}'); row.addWidget(icon_l)
        title_box = QVBoxLayout(); title_box.setSpacing(0); title_box.setContentsMargins(0, 0, 0, 0)
        title_l = QLabel(title or 'HUD WINDOW', bar)
        title_l.setStyleSheet("color:#dff8ff;font:700 9pt 'Orbitron';letter-spacing:2px;background:transparent;border:none;")
        title_box.addWidget(title_l)
        if subtitle:
            sub_l = QLabel(subtitle, bar)
            sub_l.setStyleSheet("color:#5796ad;font:600 6.5pt 'Exo 2';letter-spacing:1px;background:transparent;border:none;")
            title_box.addWidget(sub_l)
        row.addLayout(title_box, 1)
        x = _GlowSquareButton('×', bar, 26)
        x.setToolTip('Close window')
        if close_cb: x.clicked.connect(close_cb)
        row.addWidget(x)
        parent.layout().insertWidget(0, bar)
        bar.setProperty('_jarvis_panel_drag', True)
        icon_l.setProperty('_jarvis_panel_drag', True)
        title_l.setProperty('_jarvis_panel_drag', True)
        bar.installEventFilter(self); icon_l.installEventFilter(self); title_l.installEventFilter(self)
        bar.setCursor(Qt.CursorShape.SizeAllCursor); icon_l.setCursor(Qt.CursorShape.SizeAllCursor); title_l.setCursor(Qt.CursorShape.SizeAllCursor)
        return x

    def _build_quick_panel(self):
        f = self._panel_base(); f.setFixedWidth(318)
        l = QVBoxLayout(f); l.setContentsMargins(10,10,10,10); l.setSpacing(8)
        self._panel_header(f, '✦', lambda: self._set_panel_visible(f, False), 'QUICK LINK')
        self._panel_command_input = QLineEdit(); self._panel_command_input.setPlaceholderText('Type a command…'); self._panel_command_input.returnPressed.connect(lambda:self._send_backend_command(self._panel_command_input.text())); self._panel_command_input.setStyleSheet(f'QLineEdit{{background:rgba(0,0,0,80);color:{C.WHITE};border:1px solid {C.BORDER};border-radius:6px;padding:5px;}}'); l.addWidget(self._panel_command_input)
        hint = QLabel('QUICK LINK'); hint.setStyleSheet(f'color:{C.TEXT_DIM};font-size:8px;letter-spacing:2px;background:transparent;padding:0 4px;'); l.addWidget(hint)
        grid = QGridLayout(); grid.setSpacing(8)
        actions = [
            ('SETTINGS', self._open_full_settings),
            ('VIDEO PREVIEW', self._open_video_panel),
            ('IMAGE PREVIEW', self._open_image_panel),
            ('3D DISPLAY', self._open_3d_display),
            ('WEBVIEW', self._open_webview_panel),
            ('WEB TASK', self._open_web_task_panel),
            ('VISION', self._open_vision_preview),
            ('WORLD MONITOR', self._open_world_monitor),
            ('MEMORY', self._open_memory_panel),
        ]
        for i,(txt,cb) in enumerate(actions):
            b = _GlowButton(txt, '', compact=True); b.setMinimumHeight(46); b.clicked.connect(cb); grid.addWidget(b,i//2,i%2)
        l.addLayout(grid); l.addStretch(1)
        mic = QLabel('VOICE ONLY  ·  SAY COMMANDS TO J.A.R.V.I.S'); mic.setAlignment(Qt.AlignmentFlag.AlignCenter); mic.setWordWrap(True)
        mic.setStyleSheet(f'color:{C.TEXT_MED};font-size:8px;background:rgba(0,25,35,120);border:1px solid {C.BORDER};border-radius:9px;padding:8px;'); l.addWidget(mic)
        return f

    def _build_floating_panel(self, widget, kind):
        f=self._panel_base(); f.setProperty('_jarvis_panel_kind', str(kind))
        l=QVBoxLayout(f); l.setContentsMargins(8,8,8,8); l.setSpacing(6)
        titles={'video':'VIDEO PREVIEW','model':'3D DISPLAY','web':'WEBVIEW','task':'WEB TASK','world':'SYSTEM MONITOR','memory':'MEMORY CORE','window':'WINDOW','tools':'TOOLS DECK'}
        icons={'video':'▶','model':'◇','web':'🌐','task':'⌁','world':'◎','memory':'🧠','window':'▣','tools':'▣'}
        subtitles={'video':'LOCAL MEDIA','model':'HOLOGRAM','web':'WEB CONSOLE','task':'RESEARCH QUEUE','world':'LIVE TELEMETRY','memory':'LONG-TERM STORE','window':'WORKSPACE','tools':'COMMAND DECK'}
        self._panel_header(f, icons.get(kind,'✦'), lambda:self._set_panel_visible(f,False), titles.get(kind,'HUD WINDOW'), subtitles.get(kind,''))
        l.addWidget(widget,1)
        self._install_panel_drag_surface(f)
        return f

    def _install_panel_drag_surface(self, panel):
        """Make the complete floating-panel chrome draggable without stealing controls."""
        if panel is None:
            return
        panel.setProperty('_jarvis_floating_panel', True)
        panel.setCursor(Qt.CursorShape.ArrowCursor)
        # Observe the actual top-level panel so manual resizing is persisted automatically.
        panel.installEventFilter(self)
        panel_kind = str(panel.property('_jarvis_panel_kind') or 'panel')
        panel.setObjectName(f'JarvisPanel_{panel_kind}')
        # Header/title already use _jarvis_panel_drag.  Add a dedicated,
        # transparent grab strip just above the content so there is always an
        # obvious area to press-and-hold, even when the content is a WebView.
        bar = panel.findChild(QWidget, 'JarvisPanelDragStrip')
        if bar is None:
            bar = QWidget(panel)
            bar.setObjectName('JarvisPanelDragStrip')
            bar.setFixedHeight(4)
            bar.setStyleSheet('background:transparent;')
            bar.setProperty('_jarvis_panel_drag', True)
            bar.installEventFilter(self)
            bar.setCursor(Qt.CursorShape.SizeAllCursor)
        try:
            bar.raise_()
            bar.setGeometry(8, 34, max(40, panel.width()-16), 4)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            strip = self.findChild(QWidget, 'JarvisPanelDragStrip')
            if strip is not None:
                strip.setGeometry(8, 34, max(40, self.width() - 16), 6)
        except Exception:
            pass

    def _remember_panel_position(self, panel):
        try:
            if panel is None or not panel.isWindow():
                return
            key = str(panel.property('_jarvis_panel_key') or panel.property('_jarvis_panel_kind') or panel.objectName() or '')
            if not key:
                return
            positions = self._features.get('panel_positions') if isinstance(self._features, dict) else None
            if not isinstance(positions, dict):
                positions = {}
            positions[key] = {
                'x': int(panel.x()),
                'y': int(panel.y()),
                'w': int(panel.width()),
                'h': int(panel.height()),
            }
            self._features['panel_positions'] = positions
            _ui_save(API_FILE, features=self._features)
        except Exception:
            pass

    def _schedule_panel_autosave(self, panel):
        """Debounced live save for floating panel geometry (move + resize)."""
        try:
            if panel is None or not panel.isWindow():
                return
            if not hasattr(self, '_panel_save_timers'):
                self._panel_save_timers = {}
            old = self._panel_save_timers.pop(panel, None)
            if old is not None:
                try: old.stop()
                except Exception: pass
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda p=panel, t=timer: (self._remember_panel_position(p), self._panel_save_timers.pop(p, None)))
            self._panel_save_timers[panel] = timer
            timer.start(220)
        except Exception:
            pass

    def _restore_panel_position(self, panel):
        try:
            positions = self._features.get('panel_positions', {}) if isinstance(self._features, dict) else {}
            key = str(panel.property('_jarvis_panel_key') or panel.property('_jarvis_panel_kind') or panel.objectName() or '')
            pos = positions.get(key) if isinstance(positions, dict) else None
            if isinstance(pos, dict):
                x = int(pos.get('x', panel.x()))
                y = int(pos.get('y', panel.y()))
                w = int(pos.get('w', 0) or 0)
                h = int(pos.get('h', 0) or 0)
                if w > 0 and h > 0:
                    panel.resize(max(panel.minimumWidth(), w), max(panel.minimumHeight(), h))
                panel.move(x, y)
                return True
        except Exception:
            pass
        return False

    def _build_model_panel(self):
        f = self._panel_base(); f.setMinimumSize(460, 380)
        l = QVBoxLayout(f); l.setContentsMargins(7,7,7,7); l.setSpacing(6)
        self._panel_header(f, '◇', lambda: self._set_panel_visible(f, False), '3D DISPLAY', 'HOLOGRAM')
        self._model_view = Model3DView()
        l.addWidget(self._model_view, 1)
        self._model_status = QLabel('No 3D model loaded')
        self._model_status.setStyleSheet(f'color:{C.TEXT_DIM};font:8pt "Exo 2";background:transparent;')
        l.addWidget(self._model_status)
        row = QHBoxLayout()
        open_btn = _GlowButton('OPEN MODEL', '＋', compact=True); open_btn.clicked.connect(self._open_model); row.addWidget(open_btn)
        reset = _GlowButton('RESET', '↻', compact=True); reset.clicked.connect(self._model_view.reset_view); row.addWidget(reset)
        wire = _GlowButton('WIREFRAME', '◇', compact=True); wire.clicked.connect(self._model_view.toggle_wireframe); row.addWidget(wire)
        row.addStretch(1); l.addLayout(row)
        return f

    def _open_3d_panel(self):
        self._open_3d_display()

    def _open_3d_display(self):
        path,_=QFileDialog.getOpenFileName(self,'Open 3D object',str(Path.home()),'3D Models (*.obj *.stl *.ply *.off *.glb *.gltf *.dae *.3ds *.fbx);;All Files (*.*)')
        if not path: return
        try:
            if getattr(self,'_three_d_display',None) is None:
                self._three_d_display=_3DDisplayWindow(self)
                self._three_d_display.setProperty('_jarvis_floating_panel', True)
                self._three_d_display.setProperty('_jarvis_panel_kind', '3d_hologram')
                self._three_d_display.setProperty('_jarvis_panel_key', '3d_hologram')
            self._three_d_display.load_model(path)
            sg=QApplication.primaryScreen().availableGeometry() if QApplication.primaryScreen() else None
            if sg:
                w,h=self._three_d_display.width(),self._three_d_display.height()
                self._three_d_display.move(sg.left()+(sg.width()-w)//2,sg.top()+(sg.height()-h)//2)
            self._three_d_display.show(); self._three_d_display.raise_(); self._three_d_display.activateWindow()
        except Exception as exc:
            self.write_log(f'ERR: 3D display — {exc}')

    def control_jarvis_window(self, window: str, action: str = "open", query: str = ""):
        """Open/control one of JARVIS's built-in floating HUD windows.

        This is the backend-facing command used by voice/tool calls so the assistant
        can target its own panels instead of opening unrelated external windows.
        """
        w = str(window or "webview").strip().lower().replace(" ", "_").replace("-", "_")
        a = str(action or "open").strip().lower()
        aliases = {
            "web": "webview", "browser": "webview", "search": "webview",
            "images": "image", "image_preview": "image", "imageviewer": "image",
            "world": "world_monitor", "worldmonitor": "world_monitor",
            "video_preview": "video", "player": "video",
            "task": "web_task", "webtask": "web_task",
            "tools": "tools", "toolbox": "tools", "tool": "tools",
            "system": "world_monitor", "telemetry": "world_monitor",
            "sysmon": "world_monitor", "performance": "world_monitor",
            "memory_core": "memory", "memorycore": "memory",
            "activity_log": "activity", "log": "activity",
            "content_surface": "content", "research": "content",
            "model": "3d", "3d_display": "3d", "hologram": "3d",
        }
        w = aliases.get(w, w)
        panels = {
            "video": self._video_panel, "image": self._image_panel,
            "activity": self._activity_panel, "content": self._content_panel,
            "3d": self._model_panel, "webview": self._webview_panel,
            "web_task": self._web_task_panel, "world_monitor": self._world_monitor_panel,
            "memory": self._memory_panel, "tools": self._tools_panel,
        }
        if w not in panels:
            return "Unknown JARVIS window. Available: Tools, WebView, Image, System Monitor, Video, Web Task, Memory, Activity, Content, and 3D."
        panel = panels[w]

        if a == "close":
            self._set_panel_visible(panel, False)
            return f"Closed the {w.replace('_', ' ')} window."

        if w == "webview":
            if a in ("search", "find"):
                q = query.strip()
                if not q:
                    return "Please provide something to search for."
                self._open_webview_panel()
                self._webview_pane._url.setText(q)
                self._webview_pane.navigate()
                return f"Searching for {q} inside the JARVIS WebView."
            if a in ("refresh", "reload"):
                self._open_webview_panel(); self._webview_pane.reload()
                return "Refreshed the JARVIS WebView."
            self._open_webview_panel(query if query else None)
            return "Opened the JARVIS WebView."

        if w == "world_monitor":
            self._open_world_monitor()
            if a == "refresh":
                try: self._world_monitor_pane.refresh_feeds()
                except Exception: pass
                return "Refreshed the JARVIS World Monitor."
            return "Opened the JARVIS World Monitor."

        if w == "image":
            self._open_image_panel()
            if a == "search" and query:
                # Search through the normal research pipeline and keep the answer on the HUD.
                try:
                    from urllib.parse import quote_plus
                    self._open_webview_panel('https://www.google.com/search?tbm=isch&q=' + quote_plus(query))
                    return f"Opened image search for {query} inside the JARVIS WebView."
                except Exception as exc:
                    return f"Could not open image search: {exc}"
            return "Opened the JARVIS Image Preview."

        if w == "video":
            self._open_video_panel()
            return "Opened the JARVIS Video Preview."
        if w == "web_task":
            self._open_web_task_panel()
            return "Opened the JARVIS Web Task window."
        if w == "tools":
            self._open_tools_panel()
            return "Opened the JARVIS Tools Deck."
        if w == "memory":
            self._open_memory_panel()
            return "Opened the JARVIS Memory Core."
        if w == "activity":
            self._open_activity_panel()
            return "Opened the JARVIS Activity Log."
        if w == "content":
            self._set_panel_visible(self._content_panel, True)
            return "Opened the JARVIS Content Surface."
        if w == "3d":
            # Show the embedded 3D panel directly — never pop a file dialog
            # from a voice/tool request (it would block the whole UI).
            self._set_panel_visible(self._model_panel, True)
            return "Opened the JARVIS 3D Display. Use OPEN MODEL inside it to load a file."
        return "Done."

    def _open_video_panel(self):
        self._set_panel_visible(self._video_panel, True)

    def _open_image_panel(self):
        self._set_panel_visible(self._image_panel, True)

    def play_web_music(self, query: str):
        """Search YouTube inside the internal WebView and try to start the first result."""
        from urllib.parse import quote_plus
        q = str(query or '').strip()
        if not q:
            q = 'music'
        if not getattr(self, '_music_webview_enabled', True):
            return 'WebView music is disabled. Enable "Play music inside the internal WebView" in Control Center → Web.'
        pane = getattr(self, '_webview_pane', None)
        panel = getattr(self, '_webview_panel', None)
        if pane is None or panel is None:
            return 'The internal WebView panel is unavailable.'
        if not getattr(pane, 'engine_enabled', False):
            return 'Internal WebView is disabled. Enable it in Control Center → Web to play music inside JARVIS.'
        url = 'https://www.youtube.com/results?search_query=' + quote_plus(q)
        try:
            self._set_panel_visible(panel, True)
            pane._url.setText(url)
            engine = getattr(pane, '_engine', None)
            if engine is None:
                return 'The embedded WebView engine is unavailable.'
            def _after_load(ok):
                if not ok:
                    return
                js = r"""
                    (() => {
                      const pick = () => {
                        const selectors = [
                          'a#video-title',
                          'a#video-title-link',
                          'ytd-video-renderer a#video-title',
                          'a[href*="watch?v="]'
                        ];
                        for (const sel of selectors) {
                          const el = [...document.querySelectorAll(sel)].find(x => x && x.offsetParent !== null);
                          if (el) { el.click(); return true; }
                        }
                        return false;
                      };
                      if (pick()) return;
                      let n = 0;
                      const timer = setInterval(() => {
                        if (pick() || ++n > 12) clearInterval(timer);
                      }, 700);
                    })();
                """
                try: engine.page().runJavaScript(js)
                except Exception: pass
            old = getattr(pane, '_music_load_hook', None)
            if old is not None:
                try: engine.loadFinished.disconnect(old)
                except Exception: pass
            pane._music_load_hook = _after_load
            engine.loadFinished.connect(_after_load)
            engine.setUrl(QUrl(url))
            pane._status.setText(f'MUSIC · SEARCHING {q[:52]}')
            return f"Opened music for {q} inside the JARVIS WebView."
        except Exception as exc:
            return f"Music WebView error: {exc}"

    def _open_webview_panel(self, url=None):
        if url:
            try:
                self._webview_pane._url.setText(str(url))
                self._webview_pane.navigate()
            except Exception:
                pass
        self._set_panel_visible(self._webview_panel, True)

    def _open_web_task_panel(self):
        self._set_panel_visible(self._web_task_panel, True)

    def _open_tools_panel(self):
        try:
            self._tools_pane.reload()
        except Exception:
            pass
        self._set_panel_visible(self._tools_panel, True)

    def get_tool_entries(self) -> list:
        """All executable capabilities for the Tools deck: core tools with
        categories plus installed plugins. RUN routes through the backend."""
        feats = self._features if isinstance(getattr(self, '_features', None), dict) else {}
        def _on(*keys, default=True):
            try:
                return bool(feats.get(keys[0], default)) if len(keys) == 1 else any(bool(feats.get(k, default)) for k in keys)
            except Exception:
                return True
        web_ok  = _on('webview', 'webview_engine')
        comp_ok = _on('computer_control')
        core = [
            # Computer Control
            ('open_app', 'Computer Control', '▣', 'Open any application by name.', 'Open the calculator app.', comp_ok),
            ('computer_settings', 'Computer Control', '◐', 'Volume, brightness, windows, power and shortcuts.', 'Turn the volume up slightly.', comp_ok),
            ('computer_control', 'Computer Control', '⌖', 'See and control the screen, mouse and keyboard.', 'Take a screenshot of my screen.', comp_ok),
            ('desktop_control', 'Computer Control', '⊞', 'Wallpaper, icons, desktop organization and stats.', 'Organize my desktop.', comp_ok),
            # Browser
            ('browser_control', 'Browser', '🌐', 'Drive the web browser: open, click, fill, scroll.', 'Open example.com in the browser.', web_ok),
            ('web_search', 'Browser', '⌕', 'Search, news, research, prices and comparisons.', 'Search the web for quantum computing news.', web_ok),
            ('youtube_video', 'Browser', '▶', 'Play, summarize and inspect YouTube videos.', 'Play a relaxing jazz video.', web_ok),
            ('play_music', 'Browser', '♫', 'Play music inside the JARVIS WebView.', 'Play some lofi music.', web_ok and _on('webview_music')),
            ('flight_finder', 'Browser', '✈', 'Find flights with live options and prices.', 'Find flights from London to Tokyo.', web_ok),
            # Files
            ('file_controller', 'Files', '🗀', 'List, create, move, copy, rename and inspect files.', 'List the files on my desktop.', _on('file_control')),
            ('file_processor', 'Files', '⬣', 'Summarize, convert and analyze documents and media.', 'Summarize the selected file.', _on('file_control')),
            ('desktop_control', 'Files', '🗄', 'Desktop-level file organization helpers.', 'Show my disk usage.', _on('file_control')),
            # Screen
            ('screen_process', 'Screen', '◉', 'Capture and understand screen or webcam.', 'Look at my screen and tell me what you see.', _on('screen_understanding')),
            ('close_camera', 'Screen', '◌', 'Close the live camera view.', 'Close the camera.', True),
            # Media
            ('play_local_video', 'Media', '🎬', 'Play a local video/audio file in the media panel.', 'Play my video file.', True),
            ('generate_image', 'Media', '◈', 'Generate AI imagery from a description.', 'Generate an image of a futuristic city.', True),
            # System
            ('system_status', 'System', '⬢', 'Live CPU, RAM, GPU, temperature and uptime.', 'What is the status of my system?', _on('desktop_awareness')),
            ('reminder', 'System', '⏰', 'Set timed reminders via the task scheduler.', 'Remind me in 10 minutes to stretch.', True),
            ('manage_monitor', 'System', '◎', 'Track topics and get daily briefings.', 'What topics are being monitored?', True),
            ('game_updater', 'System', '🎮', 'Update and manage Steam / Epic games.', 'Check for game updates.', True),
            ('shutdown_jarvis', 'System', '⏻', 'End the session and shut JARVIS down.', 'Goodbye.', True),
            # Automation
            ('jarvis_window', 'Automation', '▤', 'Open JARVIS windows: web, memory, activity, 3D.', 'Open the webview window.', True),
            ('send_message', 'Automation', '✉', 'Send WhatsApp / Telegram messages.', 'Send a message.', True),
            ('file_processor', 'Automation', '⚙', 'Batch-process the selected file.', 'Process the selected file.', _on('file_control')),
            # Coding
            ('code_helper', 'Coding', '⌨', 'Write, explain, run and fix code.', 'Write a Python hello world script.', True),
            ('dev_agent', 'Coding', '⛭', 'Build complete multi-file projects.', 'Build me a Pomodoro timer app.', True),
            # Memory
            ('save_memory', 'Memory', '◆', 'Remember a fact about the user.', 'Remember that I like espresso.', True),
            ('recall_memory', 'Memory', '◇', 'Recall stored facts on demand.', 'What do you remember about me?', True),
            ('undo', 'Memory', '↩', 'Undo the last change JARVIS made.', 'Undo that.', True),
        ]
        entries = []
        for name, cat, icon, desc, run, avail in core:
            entries.append({'name': name, 'category': cat, 'icon': icon,
                            'desc': desc, 'run': run, 'available': bool(avail)})
        entries.append({'name': 'web_task_queue', 'category': 'Automation', 'icon': '☰',
                        'desc': 'Queue search, news and research jobs.', 'run': '',
                        'available': _on('web_task'), 'action': 'open_web_task'})
        # Installed plugins extend the deck.
        try:
            plugins = self.get_plugins() if getattr(self, 'get_plugins', None) else []
        except Exception:
            plugins = []
        for p in plugins or []:
            try:
                pname = str(p.get('name', 'plugin'))
                entries.append({'name': pname, 'category': 'Plugins', 'icon': '⬢',
                                'desc': str(p.get('description', 'Community plugin.'))[:140],
                                'run': f'Use the {pname} plugin.',
                                'available': bool(p.get('enabled', True) and p.get('valid', True))})
            except Exception:
                pass
        return entries

    def _open_vision_preview(self):
        """VISION quick tile → open the live webcam overlay (shared camera,
        feathered edges, live detection brackets). Thread-safe."""
        try:
            self.start_camera_stream()
        except Exception as exc:
            self.write_log(f'ERR: Vision preview — {exc}')

    def _open_world_monitor(self):
        self._set_panel_visible(self._world_monitor_panel, True)
        try:
            self._world_monitor_pane.refresh_feeds()
        except Exception:
            pass

    def _open_memory_panel(self):
        try:
            self._memory_pane.reload()
        except Exception:
            pass
        self._set_panel_visible(self._memory_panel, True)

    def _open_activity_panel(self):
        self._set_panel_visible(self._activity_panel, True)

    def _spawn_workspace_window(self):
        pane = WorkspaceWindowPane(title=f'WINDOW {len(self._workspace_windows)+1:02d}')
        win = self._build_floating_panel(pane, 'window')
        win.setProperty('_jarvis_panel_key', f'new_window_{len(self._workspace_windows)+1:02d}')
        self._workspace_windows.append(win)
        self._set_panel_visible(win, True)

    def _on_web_task(self, payload: str):
        text = str(payload or '')
        if text.startswith('__webview__:'):
            self._open_webview_panel(text.split(':', 1)[-1].strip())
            return
        self._send_backend_command(text)

    def _build_activity_panel(self):
        f=self._panel_base(); f.setMinimumSize(400,320); l=QVBoxLayout(f); l.setContentsMargins(12,10,12,10); l.setSpacing(8)
        self._panel_header(f,'◉',lambda:self._set_panel_visible(f,False),'ACTIVITY','LIVE TIMELINE')
        filt_row=QHBoxLayout(); filt_row.setSpacing(6)
        filt_lbl=QLabel('SHOW'); filt_lbl.setStyleSheet("color:#5796ad;font:700 7pt 'Exo 2';background:transparent;")
        filt_row.addWidget(filt_lbl)
        self._activity_filter=QComboBox(); self._activity_filter.addItems(['ALL','VOICE','AI','TOOL','WEB','FILE','OK','WARN','ERROR','SYS'])
        self._activity_filter.setStyleSheet(_hud_field_css()); self._activity_filter.setMinimumHeight(28)
        self._activity_filter.currentTextChanged.connect(lambda t: self._activity.set_filter(t))
        filt_row.addWidget(self._activity_filter,1)
        l.addLayout(filt_row)
        self._activity=_ActivityTimeline(); l.addWidget(self._activity,1); self._activity_add('SYS: UI online'); return f

    def _build_image_panel(self):
        f=self._panel_base(); f.setMinimumSize(500,420)
        l=QVBoxLayout(f); l.setContentsMargins(8,8,8,8); l.setSpacing(7)
        self._panel_header(f,'▧',lambda:self._set_panel_visible(f,False),'IMAGE PREVIEW', 'STILLS & ANALYSIS')
        top=QWidget(f); top.setStyleSheet("background:rgba(3,20,30,140);border:1px solid rgba(74,196,239,120);border-radius:9px;")
        tr=QHBoxLayout(top); tr.setContentsMargins(8,6,8,6); tr.setSpacing(6)
        self._image_status=QLabel('IMAGE PREVIEW · NO FILE'); self._image_status.setWordWrap(False); self._image_status.setStyleSheet("color:#9ae8ff;font:700 8pt 'Exo 2';background:transparent;"); tr.addWidget(self._image_status,1)
        open_btn=_GlowButton('OPEN','＋',compact=True); open_btn.clicked.connect(self._open_image_file); tr.addWidget(open_btn)
        clear_btn=_GlowButton('CLEAR','×',compact=True); clear_btn.clicked.connect(lambda:self._image_label.clear()); tr.addWidget(clear_btn)
        top.setCursor(Qt.CursorShape.SizeAllCursor); top.installEventFilter(self); top.setProperty('_jarvis_panel_drag',True); l.addWidget(top)
        self._image_label=QLabel(); self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self._image_label.setMinimumHeight(300); self._image_label.setStyleSheet(_theme_card_css() + "color:#5796ad;"); self._image_label.setScaledContents(False); l.addWidget(self._image_label,1)
        return f

    def _open_image_file(self):
        p,_=QFileDialog.getOpenFileName(self,'Open image',str(Path.home()),'Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tif *.tiff)')
        if p: self.show_image_path(p,'Loaded image')

    def _build_content_panel(self):
        f=self._panel_base(); f.setMinimumSize(560,360); l=QVBoxLayout(f); l.setContentsMargins(7,7,7,7); l.setSpacing(5)
        self._panel_header(f,'⌕',lambda:self._set_panel_visible(f,False),'CONTENT SURFACE', 'RESEARCH & DOCS')
        self._content_title=QLabel(''); self._content_title.setStyleSheet("color:#dff8ff;font:700 10pt 'Orbitron';letter-spacing:2px;background:transparent;border:none;padding:2px 7px;"); l.addWidget(self._content_title)
        self._content_text=QTextEdit(); self._content_text.setReadOnly(True); self._content_text.setStyleSheet(_hud_field_css() + "QTextEdit{padding:10px;}"); l.addWidget(self._content_text,1); return f

    def _open_full_settings(self):
        """Open the standalone tabbed settings center without changing the main HUD."""
        try:
            win = getattr(self, "_full_settings_window", None)
            try:
                if win is not None:
                    win.windowTitle()
            except RuntimeError:
                win = None
            if win is None:
                # Keep the Control Center independent from the compact HUD.
                # Parenting it as a Tool window can hide/close the frameless reactor.
                win = SettingsWindow(config_path=API_FILE, parent=None)
                try:
                    win.setProperty('_jarvis_floating_panel', True)
                    win.setProperty('_jarvis_panel_kind', 'control_center')
                    win.setProperty('_jarvis_panel_key', 'control_center')
                except Exception:
                    pass
                self._full_settings_window = win
                win.settings_saved.connect(self._apply_full_settings)
                win.voice_test_requested.connect(self._send_backend_command)
                # Backend providers for the Plugins + Diagnostics tabs.
                try:
                    win.get_plugins = self.get_plugins
                    from memory.config_manager import save_plugin_enabled as _save_plug
                    win.set_plugin_enabled = _save_plug
                    win.get_activity_log = self.get_activity_lines
                except Exception:
                    pass
            win.show()
            win.raise_()
            win.activateWindow()
            if not getattr(win, "_jarvis_positioned", False):
                sg = QApplication.primaryScreen().availableGeometry()
                win.move(sg.left() + (sg.width() - win.width()) // 2,
                         sg.top() + (sg.height() - win.height()) // 2)
                win._jarvis_positioned = True
        except Exception as exc:
            self.write_log(f"ERR: Settings window — {exc}")

    def _apply_full_settings(self, data):
        try:
            self._font_family = str(data.get('ui_font', self._font_family))
            self._panel_alpha = max(0, min(100, int(data.get('ui_opacity', self._panel_alpha))))
            self._compact_size = max(150, min(500, int(data.get('compact_size', self._compact_size))))
            self._reactor_opacity = max(0, min(100, int(data.get('reactor_opacity', self._reactor_opacity))))
            self._reactor_stroke_opacity = max(0, min(100, int(data.get('reactor_stroke_opacity', self._reactor_stroke_opacity))))
            self._reactor_speed = max(0.25, min(2.5, float(data.get('reactor_animation_speed', self._reactor_speed))))
            self._eq_sensitivity = max(0.1, min(3.0, float(data.get('equalizer_sensitivity', self._eq_sensitivity))))
            feats = data.get('features')
            if isinstance(feats, dict):
                self._features.update(feats)
            # Personality: assistant + user names.
            try:
                new_name = str(data.get('assistant_name', '') or '').strip()
                new_user = str(data.get('user_name', '') or '').strip()
                if new_name and (new_name != getattr(self, '_assistant_name', '') or
                                 new_user != _read_full_config().get('user_name', '')):
                    self._apply_name_update(new_name, new_user)
            except Exception as exc:
                self.write_log(f'ERR: Identity update — {exc}')
            # Permissions: revoked mic forces mute immediately.
            try:
                if not bool(self._features.get('mic_access', True)) and not self._muted:
                    self._toggle_mute()
            except Exception:
                pass
            voice_changed = False
            voice_name = str(data.get('voice_name', '') or '').strip()
            if voice_name:
                from memory.config_manager import get_voice, save_voice
                if voice_name != get_voice():
                    save_voice(voice_name)
                    voice_changed = True
            self._drag_reactor_enabled = bool(self._features.get('drag_reactor', True))
            self._music_webview_enabled = bool(self._features.get('webview_music', True))
            app = QApplication.instance()
            if app:
                app.setFont(QFont(self._font_family, 10))
            color = str(data.get('ui_color', '') or '')
            if color:
                old = current_palette()
                if apply_ui_accent(color):
                    retheme_all_widgets(old, current_palette())
            # Compact reactor must stay fully transparent (no panel background
            # or border). The opaque HUD surface style only applies expanded.
            if getattr(self, '_collapsed', True):
                self.setMinimumSize(QSize(self._compact_size, self._compact_size))
                self.setMaximumSize(QSize(self._compact_size, self._compact_size))
                self.resize(self._compact_size, self._compact_size)
                self._apply_compact_style()
                self._header_logo.set_logo_size(max(96, self._compact_size - 8))
                self._header_logo.setGeometry(
                    max(0, (self._compact_size - self._header_logo.width()) // 2),
                    max(0, (self._compact_size - self._header_logo.height()) // 2),
                    self._header_logo.width(), self._header_logo.height())
                self._header_logo.raise_()
            else:
                self.surface.setStyleSheet(self._surface_style())
            self._header_logo.set_graphic_opacity(self._reactor_opacity)
            self._header_logo.set_stroke_opacity(self._reactor_stroke_opacity)
            self._header_logo._animation_speed = self._reactor_speed
            home = str(data.get('web_homepage') or '')
            if home and getattr(self, '_webview_pane', None) is not None:
                self._webview_pane._home = home
            if getattr(self, '_webview_pane', None) is not None and isinstance(feats, dict):
                self._webview_pane._engine_toggle.setChecked(bool(feats.get('webview_engine', True)))
            self._hide_taskbar_button = bool(self._features.get('hide_taskbar_button', self._features.get('hide_taskbar', False)))
            self._set_taskbar_button_hidden(self._hide_taskbar_button)
            try:
                from core import sfx as _sfx_mod
                _sfx_mod.configure(
                    enabled=bool(self._features.get('enable_sfx', True)),
                    volume=float(data.get('voice_volume', 1.0) or 1.0) * 0.35,
                )
            except Exception:
                pass
            self._save_window_position()
            if voice_changed and self.on_voice_change:
                self.write_log(f'SYS: Voice set — {voice_name}; reconnecting voice session')
                self.on_voice_change()
        except Exception as e:
            self.write_log(f'ERR: Applying settings — {e}')

    def _open_layout_editor(self):
        try:
            if self._layout_editor is None:
                self._layout_editor=LayoutEditorDialog(self)
            self._layout_editor.show()
        except Exception as e: self.write_log(f'ERR: Layout editor — {e}')

    def _hide_video_title(self, panel):
        for label in panel.findChildren(QLabel):
            if label.text().strip().upper() == 'VIDEO PREVIEW': label.hide()

    def _load_layout_elements(self):
        try:
            path=CONFIG_DIR/'ui_layout.json'; data=_load_layout_file(path); elems=data.get('elements',[]) if isinstance(data,dict) else []
            self._layout_elements={}
            for e in elems:
                if isinstance(e,dict) and e.get('name'):
                    self._layout_elements[str(e['name'])]=dict(e)
            self._apply_layout_elements()
        except Exception as e:
            self.write_log(f'ERR: Layout load — {e}')

    def _save_layout_elements(self):
        try:
            # Capture positions of draggable custom elements.
            for name,w in self._layout_widgets.items():
                e=self._layout_elements.get(name)
                if e is not None:
                    g=w.geometry(); e.update({'x':g.x(),'y':g.y(),'w':g.width(),'h':g.height(),'visible':w.isVisible()})
            _save_layout_file(CONFIG_DIR/'ui_layout.json', {'elements':list(self._layout_elements.values())})
        except Exception as e:
            self.write_log(f'ERR: Layout save — {e}')

    def _apply_layout_elements(self):
        if not hasattr(self,'_layout_widgets'): return
        for name,w in list(self._layout_widgets.items()):
            if name not in self._layout_elements:
                w.deleteLater(); self._layout_widgets.pop(name,None)
        parent=self.centralWidget()
        for name,e in self._layout_elements.items():
            kind=str(e.get('kind','Text')); text=str(e.get('text',name)); color=str(e.get('color',C.PRI))
            w=self._layout_widgets.get(name)
            if w is None:
                w=_LayoutElementWidget(kind,text,color,parent); self._layout_widgets[name]=w
            w.kind=kind; w._text=text; w._color=color; w.setGeometry(int(e.get('x',60)),int(e.get('y',60)),int(e.get('w',220)),int(e.get('h',50))); w.setVisible(bool(e.get('visible',True))); w.raise_()
            if w._label is not None and kind in ('Text','Button'): w._label.setStyleSheet((f'background:transparent;color:{color};font:700 13px "Rajdhani";' if kind=='Text' else f'QPushButton{{background:rgba(0,24,36,190);color:{color};border:1px solid {color};border-radius:8px;padding:6px 10px;font:700 9pt "Rajdhani";}}'))
            elif kind in ('Panel','Window','Monitor','WebView'): w.setStyleSheet(f'background:rgba(0,14,24,110);border:1px solid {color};border-radius:10px;')
            elif kind=='Separator': w.setStyleSheet(f'background:{color};border:none;')

    def _apply_initial_visibility(self):
        self._topbar.hide(); self._main_row.hide(); self._statusbar.hide()
        self._apply_compact_style()
        if hasattr(self, '_root_layout'):
            self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._header_logo.setParent(self.surface)
        self._header_logo.set_logo_size(max(96, self._compact_size - 8))
        self._header_logo.setGeometry(max(0, (self._compact_size-self._header_logo.width())//2),
                                      max(0, (self._compact_size-self._header_logo.height())//2),
                                      self._header_logo.width(), self._header_logo.height())
        self._header_logo.raise_()
        # Position is restored by __init__; keep the reactor exactly centered in its window.
        self._center_logo()

    def _center_logo(self):
        try:
            logo = self._header_logo
            logo.setGeometry(
                max(0, (self.width() - logo.width()) // 2),
                max(0, (self.height() - logo.height()) // 2),
                logo.width(), logo.height(),
            )
        except Exception:
            pass

    def _apply_compact_style(self):
        self._compact_alpha = 0
        radius = max(20, self._compact_size // 2)
        self.surface.setStyleSheet(
            f'QFrame#Surface{{background:transparent;border:none;border-radius:{radius}px;}}'
        )

    def _set_taskbar_button_hidden(self, hidden: bool):
        """Hide/show only J.A.R.V.I.S's taskbar button; never hide the Windows taskbar."""
        if _OS != 'Windows':
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            if not hwnd:
                return
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOACTIVATE = 0x0010
            SWP_FRAMECHANGED = 0x0020
            if hasattr(user32, 'GetWindowLongPtrW'):
                get_style = user32.GetWindowLongPtrW
                set_style = user32.SetWindowLongPtrW
            else:
                get_style = user32.GetWindowLongW
                set_style = user32.SetWindowLongW
            get_style.restype = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
            set_style.restype = get_style.restype
            exstyle = int(get_style(hwnd, GWL_EXSTYLE))
            if hidden:
                exstyle = (exstyle & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
            else:
                exstyle = (exstyle & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            set_style(hwnd, GWL_EXSTYLE, exstyle)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_FRAMECHANGED)
        except Exception:
            pass

    def _clamp_position_to_screen(self, pos: QPoint, size: int | None = None) -> QPoint:
        """Keep the reactor completely inside the monitor work area.

        Qt's ``availableGeometry()`` is the OS work area, so Windows taskbars
        (bottom/top/left/right) are excluded. This also works correctly when
        the user moves the reactor between multiple monitors.
        """
        try:
            w = max(1, int(size or self.width()))
            h = max(1, int(size or self.height()))
            center = pos + QPoint(w // 2, h // 2)
            screen = QApplication.screenAt(center)
            if screen is None:
                screen = QApplication.primaryScreen()
            if screen is None:
                return pos

            # availableGeometry() excludes the Windows taskbar/work-reserved
            # edges, unlike geometry(), which is the full physical monitor.
            g = screen.availableGeometry()
            max_x = g.right() - w + 1
            max_y = g.bottom() - h + 1
            x = max(g.left(), min(int(pos.x()), max_x))
            y = max(g.top(), min(int(pos.y()), max_y))
            return QPoint(x, y)
        except Exception:
            return pos

    def _move_clamped(self, pos: QPoint, size: int | None = None):
        """Move the reactor without ever allowing it to cross a screen edge."""
        target = self._clamp_position_to_screen(pos, size)
        self.move(target)
        return target

    def _save_window_position(self):
        try:
            feats = self._features if isinstance(getattr(self, '_features', None), dict) else {}
            if feats.get('remember_position', True):
                safe = self._clamp_position_to_screen(self.pos(), min(self.width(), self.height()))
                if safe != self.pos():
                    self.move(safe)
                _ui_save(API_FILE, ui_x=self.x(), ui_y=self.y())
        except Exception:
            pass

    def _save_compact_settings(self):
        try:
            _ui_save(API_FILE, compact_opacity=self._compact_alpha, compact_size=self._compact_size)
        except Exception: pass

    def toggle_panels(self):
        # Reactor click opens the new 4:5 Command Window (reference design).
        # The window background around the reactor stays fully transparent.
        self._toggle_command_window()

    def _toggle_command_window(self):
        """Show/hide the new Command Interface when the reactor is clicked."""
        try:
            win = getattr(self, '_command_window', None)
            try:
                if win is not None:
                    win.windowTitle()
            except RuntimeError:
                win = None
                self._command_window = None
            if win is not None and win.isVisible():
                if self._smooth():
                    self._fade_panel(win, False)
                else:
                    win.hide()
                if _sfx_enabled(self):
                    _sfx('close')
                return
            if win is None:
                win = _CommandWindow(self)
                self._command_window = win
                # Replay recent chat so the new window opens with context.
                for entry in getattr(self, '_chat_history', [])[-20:]:
                    try:
                        plain = entry.replace('<b style="color:', '').replace('</b>', '')
                        win.chat.append(entry)
                    except Exception:
                        pass
            # Always auto-place the command window relative to the reactor.
            # Do not restore the command window at the reactor's saved coordinates;
            # that caused the two windows to overlap when the logo was clicked.
            screen = QApplication.primaryScreen()
            sg = screen.availableGeometry() if screen is not None else None
            g = self.frameGeometry()
            if sg is not None:
                gap = 14
                w, h = win.width(), win.height()
                # Prefer the right side of the reactor. If there is not enough room,
                # use the left side. Finally fall back to a centered/clamped placement.
                right_x = g.right() + gap
                left_x = g.left() - w - gap
                centered_y = g.top() + (g.height() - h) // 2
                if right_x + w <= sg.right():
                    x = right_x
                    y = centered_y
                elif left_x >= sg.left():
                    x = left_x
                    y = centered_y
                else:
                    x = sg.left() + (sg.width() - w) // 2
                    y = g.bottom() + gap
                    if y + h > sg.bottom():
                        y = g.top() - h - gap
                x = max(sg.left() + 8, min(x, sg.right() - w - 8))
                y = max(sg.top() + 8, min(y, sg.bottom() - h - 8))
                win.move(x, y)
            else:
                win.move(self.pos() + QPoint(self.width() + 14, 0))
            win.show()
            win.raise_()
            win.activateWindow()
            if self._smooth():
                self._fade_panel(win, True)
            if _sfx_enabled(self):
                _sfx('open')
        except Exception as exc:
            self.write_log(f'ERR: Command window — {exc}')

    def _toggle_quick_popup(self):
        if self._quick_popup is not None and self._quick_popup.isVisible():
            self._animate_quick_popup(False)
            return
        if self._quick_popup is None:
            self._quick_popup = self._build_quick_popup()
        self._quick_popup.adjustSize()
        g = self.frameGeometry()
        screen = QApplication.primaryScreen().availableGeometry()
        x = g.right() + 12
        if x + self._quick_popup.width() > screen.right():
            x = g.left() - self._quick_popup.width() - 12
        y = g.top() + max(0, (g.height() - self._quick_popup.sizeHint().height()) // 2)
        y = min(max(screen.top()+8, y), screen.bottom() - self._quick_popup.height() - 8)
        target = QRectF(x, y, self._quick_popup.width(), self._quick_popup.height()).toRect()
        self._animate_quick_popup(True, target)

    def _animate_quick_popup(self, show: bool, target=None):
        if not self._quick_popup:
            return
        panel = self._quick_popup
        panel.adjustSize()
        target = target or panel.geometry()
        if show:
            sw, sh = max(200, int(target.width()*0.84)), max(120, int(target.height()*0.84))
            start = target.__class__(0, 0, sw, sh); start.moveCenter(target.center())
            panel.setGeometry(start); panel.show(); panel.raise_(); panel.activateWindow()
            eff = QGraphicsOpacityEffect(panel); panel.setGraphicsEffect(eff); eff.setOpacity(0.0)
            opacity = QPropertyAnimation(eff, b'opacity', panel); opacity.setDuration(220); opacity.setStartValue(0.0); opacity.setEndValue(1.0); opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
            geom = QPropertyAnimation(panel, b'geometry', panel); geom.setDuration(220); geom.setStartValue(start); geom.setEndValue(target); geom.setEasingCurve(QEasingCurve.Type.OutCubic)
            opacity.start(); geom.start(); self._quick_anim = (opacity, geom)
        else:
            start = panel.geometry(); ew, eh = max(180, int(start.width()*0.84)), max(110, int(start.height()*0.84))
            end = start.__class__(0,0,ew,eh); end.moveCenter(start.center())
            eff = panel.graphicsEffect() if isinstance(panel.graphicsEffect(), QGraphicsOpacityEffect) else QGraphicsOpacityEffect(panel); panel.setGraphicsEffect(eff); eff.setOpacity(1.0)
            opacity = QPropertyAnimation(eff,b'opacity',panel); opacity.setDuration(170); opacity.setStartValue(1.0); opacity.setEndValue(0.0); opacity.setEasingCurve(QEasingCurve.Type.InCubic)
            geom = QPropertyAnimation(panel,b'geometry',panel); geom.setDuration(170); geom.setStartValue(start); geom.setEndValue(end); geom.setEasingCurve(QEasingCurve.Type.InCubic)
            opacity.finished.connect(panel.hide); opacity.start(); geom.start(); self._quick_anim=(opacity,geom)

    def _build_quick_popup(self):
        w = QFrame(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        w.setObjectName('QuickPopup')
        w.setProperty('_jarvis_floating_panel', True)
        w.setProperty('_jarvis_panel_kind', 'command_deck')
        w.setProperty('_jarvis_panel_key', 'command_deck')
        w.setWindowTitle('JARVIS Quick Actions')
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        w.setStyleSheet(f'''
            QFrame#QuickPopup {{ background: transparent; border: none; }}
            QFrame#DashboardHeader {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0,62,78,180), stop:0.55 rgba(0,18,32,145), stop:1 rgba(0,52,66,180)); border: 1px solid {C.BORDER_B}; border-radius: 3px; }}
            QLabel#DashboardTitle {{ color: {C.PRI}; font: 800 9pt "Orbitron"; background: transparent; padding: 5px 8px; letter-spacing: 1px; }}
            QLabel#DashboardSubtitle {{ color: {C.TEXT_DIM}; font: 700 6pt "Exo 2"; background: transparent; padding-left: 8px; }}
            QFrame#DashboardPanel {{ background: rgba(0,20,32,155); border: 1px solid {C.BORDER_B}; border-radius: 5px; }}
            QLabel#DashboardEyebrow {{ color: {C.TEXT_DIM}; font: 700 7pt "Exo 2"; letter-spacing: 1px; background: transparent; }}
            QLabel#DashboardMetric {{ color: {C.PRI}; font: 700 9pt "Orbitron"; background: transparent; }}
            QPushButton#DashboardNav {{ color: {C.TEXT_MED}; background: rgba(0,18,29,210); border: 1px solid {C.BORDER}; border-radius: 1px; padding: 4px 7px; font: 700 7pt "Exo 2"; }}
            QPushButton#DashboardNav:hover, QPushButton#DashboardNav:checked {{ color: {C.WHITE}; border-color: {C.PRI}; background: {C.PRI_GHO}; }}
            QScrollBar:vertical {{ background: transparent; width: 7px; }}
            QScrollBar::handle:vertical {{ background: {C.BORDER_B}; border-radius: 3px; min-height: 18px; }}
        ''')
        backdrop = FuturisticBackdrop(w)
        backdrop.lower()
        w._futuristic_backdrop = backdrop
        w.resize(448, 430)
        backdrop.setGeometry(w.rect())
        lay = QVBoxLayout(w); lay.setContentsMargins(8,8,8,8); lay.setSpacing(5)
        header_frame = QFrame(); header_frame.setObjectName('DashboardHeader')
        header_frame.setProperty('_jarvis_popup_drag', True); header_frame.installEventFilter(self)
        header = QHBoxLayout(header_frame); header.setContentsMargins(5, 3, 5, 3); header.setSpacing(5)
        title_box = QVBoxLayout(); title_box.setSpacing(0)
        hdr = QLabel('◈  J.A.R.V.I.S  //  COMMAND DECK  //  HUD v2'); hdr.setObjectName('DashboardTitle')
        hdr.setProperty('_jarvis_popup_drag', True); hdr.installEventFilter(self)
        title_box.addWidget(hdr)
        subtitle = QLabel('TACTICAL INTERFACE  //  SYSTEM LINK ACTIVE'); subtitle.setObjectName('DashboardSubtitle')
        subtitle.setProperty('_jarvis_popup_drag', True); subtitle.installEventFilter(self)
        header_frame.setProperty('_jarvis_floating_panel', True)
        title_box.addWidget(subtitle); header.addLayout(title_box); header.addStretch(1)
        self._dashboard_link = QLabel('SECURE  ●'); self._dashboard_link.setStyleSheet(f'color:{C.GREEN};font:700 7pt "Exo 2";background:transparent;'); header.addWidget(self._dashboard_link)
        close = _GlowSquareButton('×'); close.setToolTip('Close command deck and all JARVIS windows')
        close.clicked.connect(self._close_all_ui); header.addWidget(close)
        lay.addWidget(header_frame)
        telemetry = QFrame(); telemetry.setObjectName('DashboardPanel'); tl = QHBoxLayout(telemetry); tl.setContentsMargins(8,5,8,5); tl.setSpacing(12)
        for label, attr in (('CPU', 'cpu'), ('RAM', 'mem'), ('GPU', 'gpu')):
            col = QVBoxLayout(); eyebrow = QLabel(label + ' // TELEMETRY'); eyebrow.setObjectName('DashboardEyebrow'); col.addWidget(eyebrow)
            value = QLabel('--%'); value.setObjectName('DashboardMetric'); setattr(self, '_dashboard_' + attr, value); col.addWidget(value); tl.addLayout(col)
        tl.addStretch(1); mode = QLabel('AUTO'); mode.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); mode.setStyleSheet(f'color:{C.ACC2};font:700 7pt "Exo 2";background:transparent;'); tl.addWidget(mode)
        lay.addWidget(telemetry)
        nav = QHBoxLayout(); nav.setSpacing(3)
        self._dashboard_pages = QStackedWidget(); self._dashboard_pages.setStyleSheet('background:transparent;')
        for i, label in enumerate(('CORE', 'MEDIA', 'WEB', 'COMPUTER', 'MONITOR', 'SYSTEM')):
            b = QPushButton(f'{i+1:02d}  {label}'); b.setObjectName('DashboardNav'); b.setCheckable(True); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda checked=False, page=i: self._switch_dashboard_page(page)); nav.addWidget(b)
            if i == 0: self._dashboard_nav_first = b
        lay.addLayout(nav)
        self._dashboard_nav = nav
        pages = [
            [('CHAT LINK', 'Send commands through the secure voice/text bridge.', self._focus_quick_input),
             ('MEMORY CORE', 'Inspect, add, and forget stored facts.', self._open_memory_panel),
             ('ACTIVITY LOG', 'Open the live system activity window.', self._open_activity_panel)],
            [('VIDEO FEED', 'Open live media preview and camera telemetry.', self._open_video_panel),
             ('IMAGE ANALYSIS', 'Inspect generated or uploaded imagery.', self._open_image_panel),
             ('3D HOLOGRAM', 'Launch the interactive model display surface.', self._open_3d_display)],
            [('WEBVIEW', 'Open a dedicated in-HUD browser window.', self._open_webview_panel),
             ('WEB TASK', 'Queue search, news, research, and browse jobs.', self._open_web_task_panel),
             ('NEW WINDOW', 'Spawn another editable HUD workspace window.', self._spawn_workspace_window)],
            [('SCREEN CAPTURE', 'Capture and understand the current screen.', lambda: self._send_backend_command('Capture and understand my screen.')),
             ('DESKTOP CONTROL', 'Control applications, windows, mouse, keyboard, files, and terminal.', lambda: self._send_backend_command('Help me control my computer desktop.'))],
            [('WORLD MONITOR', 'Global clocks, telemetry, and world headlines.', self._open_world_monitor),
             ('REFRESH WORLD', 'Rescan world news feeds now.', lambda: self._open_world_monitor())],
            [('CONTROL CENTER', 'Configure identity, audio, theme, and runtime.', self._open_full_settings),
             ('LAYOUT EDITOR', 'Move, resize, and create HUD elements.', self._open_layout_editor)],
        ]
        for entries in pages:
            page = QFrame(); page.setObjectName('DashboardPanel'); pl = QVBoxLayout(page); pl.setContentsMargins(8,8,8,8); pl.setSpacing(5)
            for title, detail, callback in entries:
                btn = _GlowButton(title, '▸', compact=True); btn.setMinimumHeight(30); btn.setToolTip(detail); btn.clicked.connect(callback); pl.addWidget(btn)
            pl.addStretch(1); self._dashboard_pages.addWidget(page)
        lay.addWidget(self._dashboard_pages, 1)
        self._chat_log = QTextEdit(); self._chat_log.setReadOnly(True); self._chat_log.setFixedHeight(52); self._chat_log.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self._chat_log.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self._chat_log.setStyleSheet(f'QTextEdit{{background:rgba(0,12,20,110);color:{C.TEXT};border:1px solid {C.BORDER_B};border-radius:2px;padding:5px;font:8pt "Exo 2";}} QTextEdit:focus{{border:1px solid {C.PRI};}} QScrollBar:vertical{{background:transparent;width:0px;border:none;}} QScrollBar::handle:vertical{{background:transparent;border:none;}} QScrollBar:horizontal{{background:transparent;height:0px;border:none;}} QScrollBar::handle:horizontal{{background:transparent;border:none;}}'); self._chat_log.setPlaceholderText('Chat log…'); lay.addWidget(self._chat_log)
        for entry in getattr(self, '_chat_history', []): self._chat_log.append(entry)
        row = QHBoxLayout(); row.setSpacing(6)
        self._quick_input = QLineEdit(); self._quick_input.setPlaceholderText('Type a command…'); self._quick_input.setMinimumWidth(180); self._quick_input.setFixedHeight(29); self._quick_input.returnPressed.connect(self._send_quick_input); self._quick_input.setStyleSheet(f'QLineEdit{{background:rgba(0,12,20,115);color:{C.WHITE};border:1px solid {C.BORDER_B};border-radius:2px;padding:4px 7px;}} QLineEdit:focus{{border-color:{C.PRI};}}'); row.addWidget(self._quick_input,1)
        send = _GlowButton('SEND','▸',compact=True); send.clicked.connect(self._send_quick_input); row.addWidget(send); lay.addLayout(row)
        self._custom_quick_buttons_layout = QGridLayout(); self._custom_quick_buttons_layout.setSpacing(6); lay.addLayout(self._custom_quick_buttons_layout); self._rebuild_custom_quick_buttons()
        self._dashboard_nav_first.setChecked(True)
        self._dashboard_pages.setCurrentIndex(0)
        return w

    def _resize_quick_backdrop(self):
        if self._quick_popup is not None:
            backdrop = getattr(self._quick_popup, '_futuristic_backdrop', None)
            if backdrop is not None:
                backdrop.setGeometry(self._quick_popup.rect())

    def _switch_dashboard_page(self, index):
        """Switch the HUD command-deck category without touching backend callbacks."""
        if not hasattr(self, '_dashboard_pages'):
            return
        self._dashboard_pages.setCurrentIndex(index)
        for i in range(self._dashboard_nav.count()):
            item = self._dashboard_nav.itemAt(i)
            if item and item.widget():
                item.widget().setChecked(i == index)

    def _focus_quick_input(self):
        if hasattr(self, '_quick_input'):
            self._quick_input.setFocus()

    def _close_all_ui(self):
        """Close every JARVIS window, including the compact reactor."""
        windows = (
            '_quick_popup', '_command_window', '_full_settings_window', '_three_d_display',
            '_video_panel', '_image_panel', '_content_panel', '_activity_panel',
            '_model_panel', '_webview_panel', '_web_task_panel', '_world_monitor_panel',
            '_memory_panel', '_tools_panel', '_cam_preview', '_cam_live_lbl', '_overlay',
            '_confirm_overlay', '_customize_overlay', '_audio_overlay',
            '_memory_overlay', '_plugin_manager_overlay',
        )
        for name in windows:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.close()
        for win in getattr(self, '_workspace_windows', []):
            try:
                win.close()
            except Exception:
                pass
        self.close()
        QApplication.quit()

    # -- GUI-thread marshaling -------------------------------------------
    # The voice backend runs on the `jarvis-backend` thread while Qt owns the
    # main thread. Widgets, animations and effects MUST be touched on the GUI
    # thread — doing it from a worker leaves windows invisible (fade timers
    # never tick, opacity stuck at 0). Every backend entry point below goes
    # through run_on_ui / call_on_ui.
    def _on_gui_thread(self) -> bool:
        try:
            app = QApplication.instance()
            return app is not None and QThread.currentThread() == app.thread()
        except Exception:
            return False

    def _run_gui_task(self, fn) -> None:
        try:
            fn()
        except Exception as exc:
            try:
                self.write_log(f'ERR: UI task — {exc}')
            except Exception:
                pass

    def run_on_ui(self, fn) -> None:
        """Fire-and-forget `fn()` on the GUI thread (runs inline if already there)."""
        try:
            if self._on_gui_thread():
                self._run_gui_task(fn)
                return
            self._gui_exec_sig.emit(fn)
        except Exception:
            try:
                self._run_gui_task(fn)
            except Exception:
                pass

    def call_on_ui(self, fn, timeout: float = 15.0):
        """Blocking GUI-thread call with a return value. Deadlock-free: runs
        inline when already on the GUI thread, otherwise waits (max `timeout`
        seconds) for the queued slot."""
        if self._on_gui_thread():
            return fn()
        box: dict = {}
        done = threading.Event()

        def _run():
            try:
                box['value'] = fn()
            except Exception as exc:
                box['error'] = exc
            finally:
                done.set()

        try:
            self._gui_exec_sig.emit(_run)
        except Exception as exc:
            raise RuntimeError(f'UI call failed: {exc}')
        if not done.wait(timeout):
            raise RuntimeError('UI call timed out — the interface may be busy.')
        if 'error' in box:
            raise box['error']
        return box.get('value')

    def show_video(self, url):
        """Open a video URL inside the built-in WebView (thread-safe)."""
        self.run_on_ui(lambda: self._open_webview_panel(url))


    def _rebuild_custom_quick_buttons(self):
        layout = getattr(self, '_custom_quick_buttons_layout', None)
        if layout is None: return
        while layout.count():
            item=layout.takeAt(0)
            if item and item.widget(): item.widget().deleteLater()
        for i,action in enumerate(self._custom_quick_actions):
            label=str(action.get('label','ACTION')).strip() or 'ACTION'; cmd=str(action.get('command','')).strip(); b=_GlowButton(label,'✦',compact=True); b.setMinimumHeight(36); b.clicked.connect(lambda _=False, command=cmd: self._send_backend_command(command)); layout.addWidget(b,i//2,i%2)
        add=_GlowButton('ADD QUICK BUTTON','＋',compact=True); add.clicked.connect(self._add_quick_action); layout.addWidget((len(self._custom_quick_actions))//2+1,0,1,2) if False else None
        layout.addWidget(add, (len(self._custom_quick_actions))//2 + 1, 0, 1, 2)

    def _send_quick_input(self):
        if not hasattr(self,'_quick_input'): return
        txt=self._quick_input.text().strip()
        if not txt: return
        self._quick_input.clear()
        self._append_chat(f'<b style="color:{C.WHITE}">YOU</b>  {txt}')
        self._send_backend_command(txt, log=False)
        self._quick_input.setFocus()

    def _add_quick_action(self):
        label,ok=QInputDialog.getText(self,'Add Quick Action','Button name:')
        if not ok or not label.strip(): return
        command,ok=QInputDialog.getText(self,'Add Quick Action','Command to send to JARVIS:')
        if not ok or not command.strip(): return
        self._custom_quick_actions.append({'label':label.strip(),'command':command.strip()})
        cfg=_read_full_config(); cfg['quick_actions']=self._custom_quick_actions; API_FILE.parent.mkdir(parents=True,exist_ok=True); API_FILE.write_text(json.dumps(cfg,indent=4),encoding='utf-8')
        self._rebuild_custom_quick_buttons()
        if self._quick_popup: self._quick_popup.adjustSize()

    def _expand(self, animated=True):
        # Legacy callers may still request expansion. Never show the old large HUD.
        self._collapsed = True
        self.setMinimumSize(QSize(self._compact_size, self._compact_size))
        self.setMaximumSize(QSize(self._compact_size, self._compact_size))
        self.resize(self._compact_size, self._compact_size)
        self._topbar.hide()
        self._main_row.hide()
        self._statusbar.hide()
        self._apply_compact_style()
        self._header_logo.setParent(self.surface)
        self._header_logo.set_logo_size(max(96, self._compact_size - 8))
        self._header_logo.setGeometry(max(0, (self._compact_size-self._header_logo.width())//2),
                                      max(0, (self._compact_size-self._header_logo.height())//2),
                                      self._header_logo.width(), self._header_logo.height())
        self._header_logo.raise_()

    def _collapse(self, animated=True):
        # Compatibility method: the root window always remains the small reactor.
        self._collapsed = True
        for panel in (self.quick_panel, self._video_panel, self._activity_panel, self._image_panel, self._content_panel,
                      getattr(self, '_webview_panel', None), getattr(self, '_web_task_panel', None),
                      getattr(self, '_world_monitor_panel', None), getattr(self, '_memory_panel', None)):
            if panel is not None:
                panel.hide()
        self._topbar.hide(); self._main_row.hide(); self._statusbar.hide(); self._apply_compact_style()
        self.setMinimumSize(QSize(self._compact_size, self._compact_size)); self.setMaximumSize(QSize(self._compact_size, self._compact_size)); self.resize(self._compact_size, self._compact_size)
        if hasattr(self, '_root_layout'): self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._header_logo.setParent(self.surface); self._header_logo.set_logo_size(max(96, self._compact_size - 8)); self._header_logo.setGeometry(max(0,(self._compact_size-self._header_logo.width())//2),max(0,(self._compact_size-self._header_logo.height())//2),self._header_logo.width(),self._header_logo.height()); self._header_logo.raise_()

    def _prepare_startup_presentation(self):
        """Put the large reactor at the exact center of the primary screen.

        Nothing moves toward the remembered position yet. The transition is
        deliberately waiting for the first real JARVIS voice event.
        """
        try:
            screen = QApplication.primaryScreen()
            sg = screen.availableGeometry() if screen is not None else None
            small = max(150, int(getattr(self, '_compact_size', 150)))
            big = 190
            self._startup_big_size = big
            self._startup_small_size = small

            if sg is not None:
                cx = sg.left() + (sg.width() - big) // 2
                cy = sg.top() + (sg.height() - big) // 2
                self.setMinimumSize(QSize(big, big))
                self.setMaximumSize(QSize(big, big))
                self.setGeometry(cx, cy, big, big)
            else:
                self.setMinimumSize(QSize(big, big))
                self.setMaximumSize(QSize(big, big))
                self.resize(big, big)

            logo = getattr(self, '_header_logo', None)
            if logo is not None:
                logo.set_logo_size(max(150, big - 16))
                self._center_logo()
                eff = QGraphicsOpacityEffect(logo)
                eff.setOpacity(1.0)
                logo.setGraphicsEffect(eff)

                fade = QPropertyAnimation(eff, b'opacity', logo)
                fade.setDuration(620)
                fade.setStartValue(0.0)
                fade.setEndValue(1.0)
                fade.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._startup_fade = fade
                fade.start()
                self._startup_anims = (fade,)

            self._startup_waiting_for_voice = True
            self._startup_transitioning = False
        except Exception:
            self._startup_waiting_for_voice = True

    def _begin_startup_position_animation(self):
        """Shrink the startup reactor and glide it to the exact saved position."""
        if not getattr(self, '_startup_waiting_for_voice', False):
            return
        if getattr(self, '_startup_transitioning', False) or getattr(self, '_startup_position_animated', False):
            return
        self._startup_transitioning = True
        self._startup_position_animated = True
        self._startup_waiting_for_voice = False

        try:
            small = max(150, int(getattr(self, '_compact_size', 150)))
            target_pos = self._clamp_position_to_screen(getattr(self, '_startup_target_pos', self.pos()), small)
            big = 190
            start = QRectF(self.x(), self.y(), self.width(), self.height())
            target = QRectF(target_pos.x(), target_pos.y(), small, small)
            logo = getattr(self, '_header_logo', None)

            slide = QPropertyAnimation(self, b'geometry', self)
            slide.setDuration(1250)
            slide.setStartValue(start.toRect())
            slide.setEndValue(target.toRect())
            slide.setEasingCurve(QEasingCurve.Type.InOutCubic)

            def _sync_logo(value):
                try:
                    r = value.toRect()
                    denom = float(max(1, big - small))
                    progress = max(0.0, min(1.0, (big - r.width()) / denom))
                    logo_size = int((big - 16) + ((small - 8) - (big - 16)) * progress)
                    if logo is not None:
                        logo.set_logo_size(max(120, logo_size))
                        self._center_logo()
                except Exception:
                    pass

            slide.valueChanged.connect(_sync_logo)

            def _cleanup():
                try:
                    self.setMinimumSize(QSize(small, small))
                    self.setMaximumSize(QSize(small, small))
                    self.resize(small, small)
                    self._move_clamped(target_pos, small)
                    if logo is not None:
                        logo.set_logo_size(max(96, small - 8))
                        self._center_logo()
                        logo.setGraphicsEffect(None)
                        logo.raise_()
                    self._save_window_position()
                finally:
                    self._startup_transitioning = False

            slide.finished.connect(_cleanup)
            self._startup_slide = slide
            slide.start()
            self._startup_anims = tuple(a for a in (getattr(self, '_startup_fade', None), slide) if a is not None)
        except Exception:
            self._startup_transitioning = False
            self._startup_waiting_for_voice = False
            try:
                small = max(150, int(getattr(self, '_compact_size', 150)))
                self.setMinimumSize(QSize(small, small))
                self.setMaximumSize(QSize(small, small))
                self.resize(small, small)
                self.move(getattr(self, '_startup_target_pos', self.pos()))
                self._center_logo()
            except Exception:
                pass

    def _animate_window_show(self):
        # Compatibility entry point: startup is now split into two phases.
        self._prepare_startup_presentation()

    def _set_panel_visible(self, panel, visible=True):
        if panel is None:
            return
        if visible:
            # Utility windows are independent and may remain open together.
            # The compact Arc Reactor is never hidden or expanded.
            if panel.property('_jarvis_panel_key') is None:
                key = str(panel.property('_jarvis_panel_kind') or panel.objectName() or 'panel')
                panel.setProperty('_jarvis_panel_key', key)
            if not self._restore_panel_position(panel):
                self._position_one_panel(panel)
            panel.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            panel.show()
            panel.raise_()
            panel.activateWindow()
            self._fade_panel(panel, True)
            if _sfx_enabled(self):
                _sfx('open')
        else:
            self._fade_panel(panel, False)

    def _smooth(self) -> bool:
        try:
            return bool(self._features.get('smooth_animations', True))
        except Exception:
            return True

    def _fade_panel(self, panel, show):
        old=self._panel_animations.pop(panel, None)
        if old:
            try:
                for _a in (old if isinstance(old, (list, tuple)) else (old,)):
                    _a.stop()
            except Exception: pass
        if not self._smooth():
            panel.setVisible(show)
            return
        old_eff = panel.graphicsEffect()
        eff = old_eff if isinstance(old_eff, QGraphicsOpacityEffect) else QGraphicsOpacityEffect(panel)
        panel.setGraphicsEffect(eff)
        anims = []
        anim=QPropertyAnimation(eff,b'opacity',panel); anim.setDuration(220 if show else 170)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic if show else QEasingCurve.Type.InCubic)
        anims.append(anim)
        # gentle rise on open / settle on close (fade + slide + scale feel)
        try:
            slide = QPropertyAnimation(panel, b'pos', panel)
            slide.setDuration(240 if show else 170)
            slide.setEasingCurve(QEasingCurve.Type.OutCubic if show else QEasingCurve.Type.InCubic)
            end_pos = panel.pos()
            if show:
                slide.setStartValue(end_pos + QPoint(0, 14))
                slide.setEndValue(end_pos)
            else:
                slide.setStartValue(end_pos)
                slide.setEndValue(end_pos + QPoint(0, 10))
            anims.append(slide)
        except Exception:
            pass
        if show:
            eff.setOpacity(0.0); anim.setStartValue(0.0); anim.setEndValue(1.0)
        else:
            try:
                anim.finished.disconnect()
            except Exception:
                pass
            anim.setStartValue(eff.opacity() if eff.opacity()>0 else 1.0); anim.setEndValue(0.0); anim.finished.connect(panel.hide)
        for _a in anims:
            _a.start()
        self._panel_animations[panel]=anims

    def _position_one_panel(self, panel):
        screen = QApplication.primaryScreen()
        if screen is None or panel is None:
            return
        sg = screen.availableGeometry()
        sizes = {
            getattr(self, '_video_panel', None): (640, 460),
            getattr(self, '_image_panel', None): (560, 500),
            getattr(self, '_content_panel', None): (620, 520),
            getattr(self, '_activity_panel', None): (420, 380),
            getattr(self, '_model_panel', None): (620, 520),
            getattr(self, '_webview_panel', None): (960, 600),
            getattr(self, '_web_task_panel', None): (560, 480),
            getattr(self, '_world_monitor_panel', None): (860, 560),
            getattr(self, '_memory_panel', None): (560, 520),
            getattr(self, '_tools_panel', None): (600, 540),
        }
        pw, ph = sizes.get(panel, (480, 360))
        pw = min(pw, sg.width() - 24); ph = min(ph, sg.height() - 24)
        if not panel.isVisible() or panel.x() < sg.left() or panel.x() > sg.right() or panel.y() < sg.top() or panel.y() > sg.bottom():
            panel.resize(pw, ph)
            offset = (abs(id(panel)) // 7) % 6
            panel.move(sg.left() + (sg.width()-pw)//2 + offset * 26, sg.top() + (sg.height()-ph)//2 + offset * 20)
        panel.raise_()

    def _position_overlays(self):
        for name in ('_video_panel', '_image_panel', '_content_panel', '_activity_panel', '_model_panel',
                     '_webview_panel', '_web_task_panel', '_world_monitor_panel', '_memory_panel',
                     '_tools_panel'):
            panel = getattr(self, name, None)
            if panel is not None and panel.isVisible():
                self._position_one_panel(panel)
        # Camera overlays are independent windows and remain visible when other windows open.
        screen = QApplication.primaryScreen()
        if screen is not None:
            sg = screen.availableGeometry()
            if hasattr(self, '_cam_preview') and self._cam_preview.isVisible():
                self._cam_preview.raise_()
            if hasattr(self, '_cam_live_lbl') and self._cam_live_lbl.isVisible():
                self._cam_live_lbl.raise_()

    def _restore_window_position(self, animate: bool = False):
        try:
            cfg = _read_full_config()
            feats = cfg.get('features', {}) if isinstance(cfg.get('features', {}), dict) else {}
            x, y = cfg.get('ui_x'), cfg.get('ui_y')
            screen = QApplication.primaryScreen()
            sg = screen.availableGeometry() if screen is not None else None
            target = None
            small = max(150, int(getattr(self, '_compact_size', 150)))

            if feats.get('remember_position', True) and isinstance(x, int) and isinstance(y, int):
                if sg is None or (sg.left()-small < x < sg.right() and sg.top()-small < y < sg.bottom()):
                    target = self._clamp_position_to_screen(QPoint(x, y), small)
            if target is None:
                if sg is not None:
                    target = self._clamp_position_to_screen(sg.center() - QPoint(small // 2, small // 2), small)
                else:
                    target = self.pos()

            if animate:
                self._startup_target_pos = QPoint(target)
                # Prepare the large centered reactor immediately, but wait until
                # the first JARVIS speech cycle completes before relocating it.
                QTimer.singleShot(0, self._prepare_startup_presentation)
            else:
                self.setMinimumSize(QSize(small, small))
                self.setMaximumSize(QSize(small, small))
                self.resize(small, small)
                self._move_clamped(target, small)
                self._center_logo()
        except Exception:
            if animate:
                self._startup_target_pos = self.pos()
                QTimer.singleShot(0, self._prepare_startup_presentation)
            else:
                self._center_on_screen()
                self._center_logo()

    def _center_on_screen(self):
        screen=QApplication.primaryScreen()
        if screen:
            g=screen.availableGeometry(); self.move(g.center()-self.rect().center())

    def resizeEvent(self,e):
        super().resizeEvent(e); self._position_overlays()
        if self._collapsed:
            self._center_logo()

    def _append_chat(self, text):
        entry = str(text)
        self._chat_history.append(entry)
        if len(self._chat_history) > 200:
            del self._chat_history[:-200]
        if hasattr(self, '_chat_log'):
            self._chat_log.append(entry)
            sb=self._chat_log.verticalScrollBar(); sb.setValue(sb.maximum())

    def _send_backend_command(self,text,log=True):
        text=str(text).strip()
        if not text: return
        # Local-media convenience: when the user asks JARVIS to play/show/open
        # something "on my file", use the currently selected local file and open
        # the matching preview before sending the AI command.
        current=Path(self._current_file) if self._current_file else None
        lower=text.lower()
        if current and current.is_file() and any(k in lower for k in ("play ","show ","open ","preview ")):
            ext=current.suffix.lower()
            if ext in {'.mp4','.avi','.mov','.mkv','.wmv','.webm','.m4v'}:
                self._video_preview_widget.load_file(current); self._open_video_panel()
            elif ext in {'.png','.jpg','.jpeg','.webp','.gif','.bmp','.tif','.tiff'}:
                self.show_image_path(current,'Loaded image'); self._open_image_panel()
            elif ext in {'.obj','.stl','.ply','.gltf','.glb','.off','.dae','.3ds','.fbx'}:
                try:
                    self._model_view.load_model(current); self._model_status.setText(f'Loaded: {current.name}'); self._open_3d_panel()
                except Exception as exc:
                    self._model_status.setText(f'3D preview error: {exc}'); self._open_3d_panel()
        if self.on_text_command:
            if log:
                self._activity_add(f'YOU: {text}')
                self._append_chat(f'<b style="color:{C.WHITE}">YOU</b>  {text}')
            win = getattr(self, '_command_window', None)
            if win is not None and win.isVisible() and hasattr(win, '_show_typing_dots'):
                win._show_typing_dots()
            threading.Thread(target=self.on_text_command,args=(text,),daemon=True).start()

    def _log_from_backend(self,text):
        self._activity_add(text)
        raw=str(text); safe=raw.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        self._append_chat(f'<span style="color:{C.TEXT}">{safe}</span>')
        try:
            win = getattr(self, '_command_window', None)
            if win is not None and win.isVisible():
                tl = raw.lower()
                who = 'J.A.R.V.I.S.'
                body = raw
                if tl.startswith('you:'):
                    who, body = 'You', raw[4:].strip()
                elif 'jarvis:' in tl[:12]:
                    body = raw.split(':', 1)[-1].strip()
                win.append_msg(who, body, you=(who == 'You'))
        except Exception:
            pass
        tl=raw.lower()
        if 'error' in tl or tl.startswith('err:'): self._status.setText('VOICE LINK · ATTENTION')
        elif 'listening' in tl or 'online' in tl: self._status.setText('VOICE LINK · ONLINE')

    def _activity_add(self,text):
        try:
            tl = getattr(self, '_activity', None)
            if tl is not None and hasattr(tl, 'add_entry'):
                tl.add_entry(str(text)[:280])
        except Exception:
            pass

    def get_activity_lines(self, n: int = 80) -> list:
        """Recent activity lines for the Diagnostics tab (thread-safe copy)."""
        try:
            tl = getattr(self, '_activity', None)
            if tl is not None and hasattr(tl, 'lines'):
                return list(tl.lines(n))
        except Exception:
            pass
        return []

    def _apply_state(self,state):
        state_u = str(state).upper()
        previous = getattr(self.hud, 'state', '')
        self.hud.state=state; self.hud.speaking=(state_u=='SPEAKING'); self.hud.update(); self._statusbar.setText(f'{state_u}  ·  F4 MUTE  ·  F11 FULLSCREEN  ·  ESC INTERRUPT'); self._status.setText(f'VOICE LINK · {state_u}')
        try:
            if getattr(self, '_header_logo', None) is not None and hasattr(self._header_logo, 'set_state'):
                self._header_logo.set_state(state)
        except Exception:
            pass
        try:
            win = getattr(self, '_command_window', None)
            if win is not None and win.isVisible():
                win.set_status(state)
        except Exception:
            pass

        # Startup choreography: don't move the reactor before JARVIS has spoken.
        # Once the first speaking cycle has happened, move to the exact remembered
        # position after the voice returns to idle/listening.
        if getattr(self, '_startup_waiting_for_voice', False):
            if state_u == 'SPEAKING':
                self._startup_voice_seen = True
            elif getattr(self, '_startup_voice_seen', False) and previous == 'SPEAKING' and state_u != 'SPEAKING':
                QTimer.singleShot(80, self._begin_startup_position_animation)

    def set_state(self,state): self._state_sig.emit(state)
    def write_log(self,text): self._log_sig.emit(str(text))

    def show_content(self,title,text):
        self._content_title.setText(str(title).upper()[:80]); self._content_text.setPlainText(str(text)); self._set_panel_visible(self._content_panel,True)
        urls=self._extract_image_urls(str(text))
        if urls: self.show_image_url(urls[0],caption=str(title))

    @staticmethod
    def _extract_image_urls(text):
        import re
        urls=[]; urls.extend(re.findall(r'https?://[^\s\)\]>]+\.(?:png|jpe?g|webp|gif)(?:\?[^\s\)\]>]+)?',text,re.I))
        for u in re.findall(r'!\[[^\]]*\]\((https?://[^\)]+)\)',text):
            if u not in urls: urls.append(u)
        return urls

    def show_image_url(self,url,caption='Research image'):
        if not url: return
        self._image_status.setText(f'{caption}  ·  loading image…'); self._set_panel_visible(self._image_panel,True)
        def worker():
            try:
                import requests
                r=requests.get(url,timeout=12,headers={'User-Agent':'Mozilla/5.0'}); r.raise_for_status(); self._image_bytes_sig.emit(r.content,caption)
            except Exception as e: self._image_bytes_sig.emit(b'',f'{caption}  ·  {e}')
        threading.Thread(target=worker,daemon=True).start()

    def show_image_path(self,path,caption='Generated image'):
        try: self._image_bytes_sig.emit(Path(path).read_bytes(),caption)
        except Exception as e: self._image_status.setText(str(e))

    def _show_image_bytes(self,data,caption):
        if not data: self._image_status.setText(str(caption)); return
        px=QPixmap();
        if not px.loadFromData(data): self._image_status.setText('Image could not be decoded.'); return
        self._image_label.setPixmap(px.scaled(self._image_label.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)); self._image_status.setText(str(caption)); self._set_panel_visible(self._image_panel,True)

    @property
    def current_file(self): return self._current_file

    def play_local_video(self, path=None):
        """Play a local video/audio file inside JARVIS's internal media panel.

        Always opens the panel on valid files so playback issues surface
        in-panel (with a BROWSER fallback button) instead of failing the
        tool call — the assistant should narrate what is visible, never
        apologise for an 'internal player issue'.
        """
        try:
            raw = path or self._current_file
            if not raw:
                self._open_video()
                return 'No file specified — I opened the media picker inside the JARVIS video panel.'
            p = Path(str(raw)).expanduser()
            if not p.exists() or not p.is_file():
                return f'I could not find that file: {p}. Please check the path and try again.'
            media_ext = {'.mp4','.avi','.mov','.mkv','.wmv','.webm','.m4v','.mp3','.wav','.ogg','.m4a','.aac','.flac'}
            if p.suffix.lower() not in media_ext:
                return f'{p.name} is not a playable media type. Supported: MP4, AVI, MOV, MKV, WebM, MP3, WAV, OGG, M4A, AAC, FLAC.'
            self._current_file = str(p)
            self._video_preview_widget.load_file(p)
            self._set_panel_visible(self._video_panel, True)
            self._video_panel.raise_(); self._video_panel.activateWindow()
            kind = 'audio' if p.suffix.lower() in {'.mp3','.wav','.ogg','.m4a','.aac','.flac'} else 'video'
            return (
                f'Opened {p.name} in the JARVIS {kind} panel and started playback. '
                f'If this {kind} needs a codec Windows lacks, use the BROWSER button in the panel.'
            )
        except Exception as exc:
            self.write_log(f'ERR: Local video — {exc}')
            return f'I opened the video panel but playback reported: {exc}. Use the BROWSER button in the panel as fallback.'

    def _open_file(self):
        p,_=QFileDialog.getOpenFileName(self,'Open file',str(Path.home()),'All Files (*.*)')
        if p: self._register_opened_file(p)

    def _open_model(self):
        path,_=QFileDialog.getOpenFileName(self,'Open 3D model',str(Path.home()),'3D Models (*.obj *.stl *.ply *.off *.glb *.gltf *.dae *.3ds);;All Files (*.*)')
        if not path:
            self._open_3d_panel()
            return
        try:
            self._model_view.load_model(path)
            self._model_status.setText(f'Loaded: {Path(path).name}')
            self._open_3d_panel()
        except Exception as exc:
            self._model_status.setText(f'3D preview error: {exc}')
            self._open_3d_panel()

    def _open_video(self):
        p,_=QFileDialog.getOpenFileName(self,'Open video',str(Path.home()),'Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm *.m4v);;Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac)')
        if p: self._register_opened_file(p)

    def _register_opened_file(self,p):
        p=Path(p); self._current_file=str(p); ext=p.suffix.lower(); self._activity_add(f'FILE: {p.name}')
        model_ext={'.obj','.stl','.ply','.gltf','.glb','.off','.dae','.fbx','.3ds'}; media_ext={'.mp4','.avi','.mov','.mkv','.wmv','.webm','.m4v','.mp3','.wav','.ogg','.m4a','.aac','.flac'}; image_ext={'.png','.jpg','.jpeg','.webp','.gif','.bmp','.tif','.tiff'}
        if ext in model_ext:
            try:
                self._model_view.load_model(p); self._model_status.setText(f'Loaded: {p.name}'); self._open_3d_panel()
            except Exception as exc:
                self._model_status.setText(f'3D preview error: {exc}'); self._open_3d_panel()
        elif ext in media_ext:
            self._video_preview_widget.load_file(p); self._set_panel_visible(self._video_panel,True)
        elif ext in image_ext:
            self.show_image_path(p,'Loaded image')
        else:
            self._set_panel_visible(self._activity_panel,True); self._activity_add(f'Loaded: {p}')

    def set_audio_level(self, level):
        try:
            lv=max(0.0,min(1.0,float(level)))
        except Exception:
            return
        if bool(self._features.get('audio_reactive', True)):
            self.hud.set_audio_level(lv)
            self._header_logo.set_audio_level(lv)
            try:
                win = getattr(self, '_command_window', None)
                if win is not None and win.isVisible():
                    win.set_audio_level(lv)
            except Exception:
                pass

    def _toggle_mute(self):
        # Permissions: revoked mic access keeps JARVIS muted.
        if self._muted and not bool(getattr(self, '_features', {}).get('mic_access', True)):
            self.write_log('SYS: Microphone access is revoked in Settings → Permissions.')
            return
        self._muted=not self._muted; self.hud.muted=self._muted; self._apply_state('MUTED' if self._muted else 'LISTENING'); self.write_log('SYS: Microphone muted.' if self._muted else 'SYS: Microphone active.')

    def _toggle_push_to_talk(self):
        self._voice_input_enabled = not self._voice_input_enabled
        self.write_log(
            'SYS: Push-to-talk microphone active.'
            if self._voice_input_enabled
            else 'SYS: Push-to-talk microphone paused.'
        )
        self._apply_state('LISTENING' if self._voice_input_enabled else 'MUTED')

    @property
    def voice_input_enabled(self):
        return self._voice_input_enabled and not self._muted

    def toggle_camera_overlay(self, enabled: bool | None = None):
        """Show/hide the live Vision webcam overlay without creating a second camera UI."""
        def _toggle():
            current = bool(getattr(self, '_cam_live_lbl', None) and self._cam_live_lbl.isVisible())
            target = (not current) if enabled is None else bool(enabled)
            if target:
                # Keep the vision surface large enough to be useful and centered on the main screen.
                screen = QApplication.primaryScreen()
                if screen is not None:
                    sg = screen.availableGeometry()
                    w = min(720, max(360, int(sg.width() * 0.46)))
                    h = int(w * 0.75)
                    h = min(540, max(270, h))
                    self._cam_live_lbl.resize(w, h)
                    self._cam_live_lbl.move(
                        sg.left() + (sg.width() - w) // 2,
                        sg.top() + (sg.height() - h) // 2,
                    )
                self.start_camera_stream()
                self._cam_live_lbl.show()
                self._cam_live_lbl.raise_()
                self._cam_live_lbl.activateWindow()
                try:
                    self.write_log('VIS: Vision overlay enabled — live camera active.')
                except Exception:
                    pass
            else:
                self.stop_camera_stream()
                try:
                    self._cam_live_lbl.set_scan(False)
                    self._cam_live_lbl._had_faces = False
                    self._cam_live_lbl._faces = []
                    self._cam_live_lbl.hide()
                except Exception:
                    pass
                try:
                    self.write_log('VIS: Vision overlay disabled.')
                except Exception:
                    pass
        self.run_on_ui(_toggle)

    def start_camera_stream(self):
        # Thread-safe: widget visibility flips must happen on the GUI thread.
        self.run_on_ui(self._do_start_camera_stream)

    def _do_start_camera_stream(self):
        # Permissions: revoked camera access refuses to stream.
        if not bool(getattr(self, '_features', {}).get('camera_access', True)):
            self.write_log('SYS: Camera access is revoked in Settings → Permissions.')
            return
        self._cam_stop.clear(); self._cam_stream_sig.emit(True); threading.Thread(target=self._cam_loop,daemon=True).start()

    def _cam_loop(self):
        # Prefer the shared camera held by the vision coordinator so the
        # preview does not open a second handle to the same device (Windows
        # DSHOW only exposes one live handle at a time). Falls back to the
        # legacy direct-open loop when vision is unavailable.
        _shared_started = False
        try:
            from vision.camera import get_camera_manager as _gmgr
            mgr = _gmgr()
            if mgr.enabled:
                def _cb(jpg):
                    try:
                        if jpg:
                            self._cam_frame_sig.emit(jpg)
                    except Exception:
                        pass
                mgr.subscribe(_cb)
                if not mgr.running:
                    if not mgr.start():
                        mgr.unsubscribe(_cb)
                        raise RuntimeError('shared camera failed to start')
                    _shared_started = True
                self._cam_stop.wait()
                mgr.unsubscribe(_cb)
                if _shared_started:
                    mgr.stop()
                self._cam_stream_sig.emit(False)
                return
        except Exception:
            try:
                _cb = locals().get('_cb')
                if _cb is not None:
                    _gmgr().unsubscribe(_cb)
            except Exception:
                pass
            if _shared_started:
                try:
                    _gmgr().stop()
                except Exception:
                    pass
        # Legacy direct-open fallback.
        try:
            import cv2
            try:
                _cfg_idx = int((_read_full_config().get("camera_index", 0) or 0))
            except Exception:
                _cfg_idx = 0
            cap = cv2.VideoCapture(_cfg_idx)
            if not cap.isOpened() and _cfg_idx != 0:
                cap.release()
                cap = cv2.VideoCapture(0)
            while not self._cam_stop.wait(0.033) and cap.isOpened():
                ok, frame = cap.read()
                if ok:
                    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
                    self._cam_frame_sig.emit(buf.tobytes())
            cap.release()
        except Exception as e: self.write_log(f'ERR: Camera — {e}')
        finally: self._cam_stream_sig.emit(False)

    def stop_camera_stream(self):
        # Thread-safe: hide() must happen on the GUI thread.
        self.run_on_ui(self._do_stop_camera_stream)

    def _do_stop_camera_stream(self):
        self._cam_stop.set()
        try:
            self._cam_live_lbl.set_scan(False)
            self._cam_live_lbl._faces = []
            self._cam_live_lbl._had_faces = False
            self._cam_live_lbl.hide()
        except Exception:
            pass

    def _show_camera_frame(self,img_bytes):
        self._cam_preview.show_frame(img_bytes); self._cam_preview.show(); self._cam_preview.raise_(); self._position_overlays()

    def scan_pulse(self):
        """One blue scan sweep over the webcam view (called when analysing)."""
        try:
            if self._cam_live_lbl.isVisible():
                self._cam_live_lbl.set_scan(True, single=True)
        except Exception:
            pass

    def _on_cam_stream(self,start):
        if start:
            self._cam_live_lbl.show(); self._cam_live_lbl.raise_()
        else:
            try: self._cam_live_lbl.set_scan(False)
            except Exception: pass
            self._cam_live_lbl.hide()

    def _on_cam_frame(self,data):
        px=QPixmap(); px.loadFromData(data)
        if px.isNull(): return
        try:
            self._cam_live_lbl.set_frame(px)
        except Exception:
            pass
        # face detection, throttled to every 8th frame
        try:
            n = getattr(self._cam_live_lbl, '_frame_n', 0) + 1
            self._cam_live_lbl._frame_n = n
            if n % 8 == 0:
                faces = _detect_faces(bytes(data))
                self._cam_live_lbl.set_faces(faces)
                had = bool(getattr(self._cam_live_lbl, '_had_faces', False))
                if faces and not had:
                    spots = []
                    for (fx, fy, fw, fh) in faces:
                        cxp = fx + fw / 2
                        spots.append('left' if cxp < 0.38 else ('right' if cxp > 0.62 else 'center'))
                    self.write_log(f"VIS: {len(faces)} face(s) in webcam view ({', '.join(spots)}).")
                self._cam_live_lbl._had_faces = bool(faces)
        except Exception:
            pass

    def _check_config(self):
        try:
            d=json.loads(API_FILE.read_text(encoding='utf-8')); return bool(d.get('gemini_api_key')) and bool(d.get('os_system'))
        except Exception: return False

    def _show_setup(self):
        ov=SetupOverlay(None); ov.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint); ov.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        ow,oh=460,390; sg=QApplication.primaryScreen().availableGeometry(); ov.setGeometry(sg.left()+(sg.width()-ow)//2,sg.top()+(sg.height()-oh)//2,ow,oh); ov.done.connect(self._on_setup_done); ov.show(); ov.raise_(); ov.activateWindow(); self._overlay=ov

    def _on_setup_done(self,key,os_name):
        os.makedirs(CONFIG_DIR,exist_ok=True); cfg=_read_full_config(); cfg.update({'gemini_api_key':key,'os_system':os_name}); API_FILE.write_text(json.dumps(cfg,indent=4),encoding='utf-8'); self._ready=True
        if self._overlay: self._overlay.hide(); self._overlay=None
        self._apply_state('LISTENING'); self.write_log(f'SYS: Initialised. OS={os_name.upper()}. {self._assistant_name} online.')

    def prompt_reconfig(self): self._ready=False; self._reconfig_sig.emit()

    def _show_confirm_banner(self,title,detail):
        try:
            self._hide_confirm_banner(); ov=ConfirmBanner(title,detail,parent=self.centralWidget()); ov.answered.connect(self._on_confirm_answered); ov.adjustSize(); ov.move((self.centralWidget().width()-ov.width())//2,18); ov.show(); ov.raise_(); self._confirm_overlay=ov
        except Exception as e: self.write_log(f'ERR: Confirmation — {e}')

    def _hide_confirm_banner(self):
        ov=self._confirm_overlay
        if ov: ov.hide(); ov.deleteLater(); self._confirm_overlay=None

    def _on_confirm_answered(self,accepted):
        self._hide_confirm_banner()
        try:
            from core.confirm import resolve; resolve(bool(accepted))
        except Exception as e: self.write_log(f'ERR: Confirmation failed — {e}')

    def show_confirm(self,title,detail): self._confirm_sig.emit(str(title),str(detail))
    def hide_confirm(self): self._confirm_hide_sig.emit()

    def _open_customize(self):
        try:
            cfg=_read_full_config(); ov=CustomizeOverlay(cfg.get('assistant_name','JARVIS') or 'JARVIS',cfg.get('user_name',''),cfg.get('ui_color','') or DEFAULT_UI_COLOR,cfg.get('voice_name',''),parent=self.centralWidget()); ov.saved.connect(self._apply_name_update); ov.adjustSize(); ov.move(max(10,(self.centralWidget().width()-ov.width())//2),max(10,(self.centralWidget().height()-ov.height())//2)); ov.show(); ov.raise_(); self._customize_overlay=ov
        except Exception as e: self.write_log(f'ERR: Customize — {e}')

    def _apply_name_update(self,name,user_name,ui_color='',voice=''):
        self._assistant_name=name.strip() or 'JARVIS'; self._brand.setText(self._assistant_name.upper()); self.hud.assistant_name=self._assistant_name.upper(); self.hud.update()
        if ui_color:
            old=current_palette()
            if apply_ui_accent(ui_color): retheme_all_widgets(old,current_palette())
        cfg=_read_full_config(); cfg['assistant_name']=self._assistant_name; cfg['user_name']=user_name.strip();
        if ui_color: cfg['ui_color']=ui_color.strip().lower()
        API_FILE.parent.mkdir(parents=True,exist_ok=True); API_FILE.write_text(json.dumps(cfg,indent=4),encoding='utf-8')
        if voice: self.write_log(f'SYS: Voice updated — {voice}')
        self.write_log(f'SYS: Identity updated — {self._assistant_name.upper()}')

    def _show_audio_devices(self): self.write_log('SYS: Audio devices are controlled by the existing JARVIS audio configuration.')

    def _remote_clicked(self):
        if self.on_remote_clicked:
            try: self.on_remote_clicked()
            except Exception as e: self.write_log(f'ERR: Remote — {e}')

    def _do_interrupt(self):
        if self.on_interrupt: self.on_interrupt()
    def _toggle_fullscreen(self): self.showNormal() if self.isFullScreen() else self.showFullScreen()
    def _update_clock(self): self._top_metrics.setToolTip(time.strftime('%Y-%m-%d  %H:%M:%S'))
    def _update_metrics(self):
        try:
            s=_metrics.snapshot(); gpu=f'{s["gpu"]:.0f}%' if s['gpu']>=0 else 'N/A'; self._top_metrics.setText(f'CPU {s["cpu"]:.0f}%   RAM {s["mem"]:.0f}%   GPU {gpu}')
            try:
                win = getattr(self, '_command_window', None)
                if win is not None and win.isVisible():
                    tmp = f'{s["tmp"]:.0f}°C' if s.get('tmp', -1) >= 0 else '--'
                    win.set_metrics_text(f'CPU {s["cpu"]:.0f}%  |  RAM {s["mem"]:.0f}%  |  GPU {gpu}  |  TEMP {tmp}')
            except Exception:
                pass
            for attr, value in (('cpu', f'{s["cpu"]:.0f}%'), ('mem', f'{s["mem"]:.0f}%'), ('gpu', gpu)):
                label = getattr(self, '_dashboard_' + attr, None)
                if label is not None:
                    label.setText(value)
        except Exception: pass
    def notify_phone_connected(self): self.write_log('SYS: Phone connection detected.')
    def _create_desktop_shortcut(self): self.write_log('SYS: Desktop shortcut creation remains available in the original system module.')

    def eventFilter(self,obj,event):
        # Drag floating windows from their header/title (normal) or with Alt+drag
        # from a non-interactive area.  The compact Arc Reactor is intentionally
        # not affected by this handler.
        is_panel_drag = bool(obj.property('_jarvis_panel_drag')) if isinstance(obj, QWidget) else False
        is_popup_drag = bool(obj.property('_jarvis_popup_drag')) if isinstance(obj, QWidget) else False
        if isinstance(obj, QWidget) and bool(obj.property('_jarvis_floating_panel')) and event.type() == QEvent.Type.Resize:
            self._schedule_panel_autosave(obj)
            return super().eventFilter(obj, event)

        if is_panel_drag or is_popup_drag:
            target = obj.window()
            if target is not None:
                if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                    # Start tracking without consuming the press. This is critical for
                    # header controls such as Close/Back/etc. to remain clickable.
                    self._drag_target = target
                    self._drag_start_global = event.globalPosition().toPoint()
                    self._drag_start_window = target.frameGeometry().topLeft()
                    self._drag_moved = False
                    return False
                if event.type() == QEvent.Type.MouseMove and getattr(self, '_drag_start_global', None) is not None and event.buttons() & Qt.MouseButton.LeftButton:
                    current = event.globalPosition().toPoint()
                    delta = current - self._drag_start_global
                    if not self._drag_moved and delta.manhattanLength() < QApplication.startDragDistance():
                        return False
                    self._drag_moved = True
                    target.move(self._drag_start_window + delta)
                    return True
                if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                    if getattr(self, '_drag_moved', False):
                        self._remember_panel_position(target)
                    self._drag_pos = None; self._drag_target = None; self._drag_start_global = None; self._drag_start_window = None; self._drag_moved = False
                    return False

        # Alt+drag is a universal fallback for floating panels.  It deliberately
        # avoids ordinary WebView/button interactions and lets users grab the
        # window even when its content has no title/header area.
        target = obj.window() if isinstance(obj, QWidget) else None
        if target is not None and isinstance(target, QWidget) and bool(target.property('_jarvis_floating_panel')):
            enabled = bool(self._features.get('draggable_panels', True)) if isinstance(self._features, dict) else True
            if enabled and event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton and (event.modifiers() & Qt.KeyboardModifier.AltModifier):
                self._drag_target = target
                self._drag_pos = event.globalPosition().toPoint() - target.frameGeometry().topLeft()
                target.grabMouse()
                return True
            if enabled and event.type() == QEvent.Type.MouseMove and getattr(self, '_drag_pos', None) is not None and event.buttons() & Qt.MouseButton.LeftButton and (event.modifiers() & Qt.KeyboardModifier.AltModifier):
                target.move(target._clamp_position_to_screen(event.globalPosition().toPoint() - self._drag_pos) if hasattr(target, '_clamp_position_to_screen') else event.globalPosition().toPoint() - self._drag_pos)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and getattr(self, '_drag_pos', None) is not None:
                try:
                    target.releaseMouse()
                finally:
                    self._remember_panel_position(target)
                    self._drag_pos = None; self._drag_target = None
                return True
        return super().eventFilter(obj,event)


    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self,e):
        for url in e.mimeData().urls():
            p=url.toLocalFile()
            if p and Path(p).is_file(): self._register_opened_file(p); break
        e.acceptProposedAction()

    def closeEvent(self,e):
        self._set_taskbar_button_hidden(False)
        try:
            if getattr(self, '_three_d_display', None): self._three_d_display.close()
        except Exception: pass
        self.stop_camera_stream()
        try:
            vp=self._video_panel.findChild(VideoPreview); vp.stop() if vp else None
        except Exception: pass
        e.accept()


class _RootShim:
    def __init__(self, app: QApplication): self._app=app
    def mainloop(self): self._app.exec()
    def protocol(self,*_): pass



# ==================== JARVIS PANEL REDESIGN LAYER ====================
# Visual-only override layer: preserves the existing backend/control methods
# while giving every HUD surface one deliberate design system.

def _panel_design_css():
    return f"""
    QFrame#HudPanel, QFrame#JarvisPanel_video, QFrame#JarvisPanel_model,
    QFrame#JarvisPanel_web, QFrame#JarvisPanel_task, QFrame#JarvisPanel_world,
    QFrame#JarvisPanel_memory, QFrame#JarvisPanel_tools, QFrame#JarvisPanel_window,
    QFrame#JarvisPanel_image, QFrame#JarvisPanel_activity, QFrame#JarvisPanel_content {{
        background: rgba(2, 11, 19, 248);
        border: none;
        border-radius: 16px;
    }}
    QLineEdit, QTextEdit, QListWidget, QComboBox {{
        background: rgba(1, 17, 27, 235);
        color: {C.WHITE};
        border: 1px solid rgba(67, 151, 185, 115);
        border-radius: 9px;
        padding: 7px 10px;
        selection-background-color: rgba(0, 132, 177, 110);
    }}
    QLineEdit:focus, QTextEdit:focus, QListWidget:focus, QComboBox:focus {{
        border: 1px solid rgba(92, 214, 245, 225);
        background: rgba(2, 24, 38, 245);
    }}
    QComboBox::drop-down {{
        width: 24px; border: none; background: transparent;
    }}
    QListWidget {{ outline: none; padding: 6px; }}
    QListWidget::item {{ padding: 8px 10px; margin: 2px 0; border-radius: 7px; }}
    QListWidget::item:hover {{ background: rgba(0, 106, 145, 60); }}
    QListWidget::item:selected {{ background: rgba(0, 137, 183, 95); border: 1px solid rgba(94, 210, 242, 125); }}
    QScrollBar:vertical {{ background: transparent; width: 7px; margin: 3px; }}
    QScrollBar::handle:vertical {{ background: rgba(55, 166, 199, 100); border-radius: 3px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """


def _new_panel_base(self):
    f = _HudPanel(None)
    f.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    f.setMinimumSize(380, 250)
    f.setObjectName('HudPanel')
    f.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    f.setMouseTracking(True)
    f.setStyleSheet(_panel_design_css())
    f.setProperty('_jarvis_floating_panel', True)
    return f


def _new_panel_header(self, parent, icon='✦', close_cb=None, title='', subtitle=''):
    bar = QFrame(parent)
    bar.setObjectName('PanelHeader')
    bar.setFixedHeight(54)
    bar.setStyleSheet(f"""
        QFrame#PanelHeader {{
            background: transparent;
            border: none;
            border-radius: 0;
        }}
        QLabel {{ background: transparent; }}
    """)
    row = QHBoxLayout(bar); row.setContentsMargins(12, 6, 8, 6); row.setSpacing(9)
    icon_l = QLabel(icon, bar)
    icon_l.setFixedWidth(26); icon_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_l.setStyleSheet(f'color:{C.PRI};font:800 15pt "Rajdhani";background:transparent;border:none;border-radius:0;padding:0;')
    row.addWidget(icon_l)
    title_box = QVBoxLayout(); title_box.setSpacing(1); title_box.setContentsMargins(0,0,0,0)
    title_l = QLabel(title or 'HUD WINDOW', bar)
    title_l.setStyleSheet(f'color:{C.WHITE};font:800 9.5pt "Orbitron";letter-spacing:1.8px;background:transparent;border:none;')
    title_box.addWidget(title_l)
    if subtitle:
        sub_l = QLabel(subtitle, bar)
        sub_l.setStyleSheet(f'color:{C.TEXT_DIM};font:700 6.5pt "Exo 2";letter-spacing:1.4px;background:transparent;border:none;')
        title_box.addWidget(sub_l)
    row.addLayout(title_box, 1)
    live = QLabel('● LIVE', bar)
    live.setStyleSheet(f'color:{C.GREEN};font:800 6.5pt "Exo 2";background:transparent;border:none;')
    row.addWidget(live)
    x = _GlowSquareButton('×', bar, 30)
    x.setToolTip('Close')
    if close_cb: x.clicked.connect(close_cb)
    row.addWidget(x)
    parent.layout().insertWidget(0, bar)
    for w in (bar, icon_l, title_l):
        w.setProperty('_jarvis_panel_drag', True)
        w.installEventFilter(self)
        w.setCursor(Qt.CursorShape.SizeAllCursor)
    return x


def _new_quick_panel(self):
    f = self._panel_base(); f.setObjectName('JarvisPanel_quick'); f.setFixedWidth(390); f.setMinimumHeight(520)
    l = QVBoxLayout(f); l.setContentsMargins(12,12,12,12); l.setSpacing(10)
    self._panel_header(f, '✦', lambda: self._set_panel_visible(f, False), 'J.A.R.V.I.S', '')

    hero = QFrame(); hero.setStyleSheet(f'background:rgba(0,31,45,115);border:1px solid rgba(69,184,219,105);border-radius:12px;')
    hl = QVBoxLayout(hero); hl.setContentsMargins(11,10,11,10); hl.setSpacing(3)
    self._panel_command_input = QLineEdit(); self._panel_command_input.setPlaceholderText('Ask JARVIS to do something…'); self._panel_command_input.setMinimumHeight(39)
    self._panel_command_input.returnPressed.connect(lambda: self._send_backend_command(self._panel_command_input.text()))
    hl.addWidget(self._panel_command_input)
    l.addWidget(hero)

    section = QLabel('MODULES'); section.setStyleSheet(f'color:{C.PRI};font:800 7pt "Orbitron";letter-spacing:2px;background:transparent;padding-left:3px;')
    l.addWidget(section)
    grid = QGridLayout(); grid.setSpacing(8)
    actions = [
        ('ACTIVITY', '◉', self._open_activity_panel), ('TOOLS', '▣', self._open_tools_panel),
        ('WEB', '◌', self._open_webview_panel), ('MEMORY', '◆', self._open_memory_panel),
        ('SYSTEM', '◎', self._open_world_monitor), ('VIDEO', '▶', self._open_video_panel),
        ('IMAGE', '▧', self._open_image_panel), ('3D', '◇', self._open_3d_display),
        ('WEB TASK', '⌁', self._open_web_task_panel), ('CONTENT', '⌕', lambda: self._set_panel_visible(self._content_panel, True)),
        ('CONTROL CENTER', '⚙', self._open_full_settings), ('LAYOUT', '⌘', self._open_layout_editor),
    ]
    for i,(txt,ic,cb) in enumerate(actions):
        b = _GlowButton(txt, ic, compact=False); b.setMinimumHeight(46); b.clicked.connect(cb)
        grid.addWidget(b, i//2, i%2)
    l.addLayout(grid)

    status = QFrame(); status.setStyleSheet(f'background:rgba(0,19,29,145);border:1px solid rgba(64,154,183,85);border-radius:10px;')
    sr = QHBoxLayout(status); sr.setContentsMargins(9,7,9,7); sr.setSpacing(8)
    dot = QLabel('●'); dot.setStyleSheet(f'color:{C.GREEN};font-size:10pt;background:transparent;'); sr.addWidget(dot)
    tx = QLabel('VOICE LINK READY'); tx.setStyleSheet(f'color:{C.TEXT};font:800 7pt "Exo 2";letter-spacing:1px;background:transparent;'); sr.addWidget(tx,1)
    sr.addWidget(QLabel('ENTER', status))
    l.addWidget(status)
    return f


def _new_floating_panel(self, widget, kind):
    names = {
        'video': ('VIDEO PREVIEW','LOCAL MEDIA','▶'), 'model': ('3D DISPLAY','HOLOGRAM','◇'),
        'web': ('WEB CONSOLE','BROWSER SURFACE','◌'), 'task': ('WEB TASK','RESEARCH QUEUE','⌁'),
        'world': ('SYSTEM MONITOR','LIVE TELEMETRY','◎'), 'memory': ('MEMORY CORE','LONG-TERM STORE','◆'),
        'tools': ('TOOLS DECK','COMMAND LIBRARY','▣'), 'window': ('WORKSPACE','CUSTOM SURFACE','▤'),
    }
    title, sub, icon = names.get(kind, ('HUD WINDOW','J.A.R.V.I.S','✦'))
    f = self._panel_base(); f.setObjectName(f'JarvisPanel_{kind}'); f.setProperty('_jarvis_panel_kind', str(kind)); f.setProperty('_jarvis_panel_key', str(kind))
    l = QVBoxLayout(f); l.setContentsMargins(11,11,11,11); l.setSpacing(9)
    self._panel_header(f, icon, lambda: self._set_panel_visible(f,False), title, sub)
    content = QFrame(); content.setObjectName('PanelContent'); content.setStyleSheet('QFrame#PanelContent{background:rgba(0,12,20,115);border:1px solid rgba(54,151,180,70);border-radius:12px;}')
    cl = QVBoxLayout(content); cl.setContentsMargins(9,9,9,9); cl.setSpacing(7); cl.addWidget(widget,1)
    l.addWidget(content,1)
    self._install_panel_drag_surface(f)
    return f


def _new_model_panel(self):
    f=self._panel_base(); f.setObjectName('JarvisPanel_model'); f.setMinimumSize(560,470)
    l=QVBoxLayout(f); l.setContentsMargins(11,11,11,11); l.setSpacing(9)
    self._panel_header(f,'◇',lambda:self._set_panel_visible(f,False),'3D DISPLAY','INTERACTIVE HOLOGRAM')
    stage=QFrame(); stage.setStyleSheet('background:rgba(0,8,15,205);border:1px solid rgba(63,178,211,105);border-radius:12px;')
    sl=QVBoxLayout(stage); sl.setContentsMargins(6,6,6,6); sl.setSpacing(6)
    self._model_view=Model3DView(); sl.addWidget(self._model_view,1)
    self._model_status=QLabel('NO MODEL LOADED  ·  READY'); self._model_status.setStyleSheet(f'color:{C.TEXT_DIM};font:700 7pt "Exo 2";padding:2px 5px;background:transparent;'); sl.addWidget(self._model_status)
    l.addWidget(stage,1)
    row=QHBoxLayout(); row.setSpacing(7)
    for label,icon,cb in [('OPEN MODEL','＋',self._open_model),('RESET','↻',self._model_view.reset_view),('WIREFRAME','◇',self._model_view.toggle_wireframe)]:
        b=_GlowButton(label,icon,compact=True); b.clicked.connect(cb); row.addWidget(b)
    row.addStretch(1); l.addLayout(row)
    return f


def _new_activity_panel(self):
    f=self._panel_base(); f.setObjectName('JarvisPanel_activity'); f.setMinimumSize(620,420)
    l=QVBoxLayout(f); l.setContentsMargins(11,11,11,11); l.setSpacing(9)
    self._panel_header(f,'◉',lambda:self._set_panel_visible(f,False),'ACTIVITY','LIVE EVENT STREAM')
    top=QFrame(); top.setStyleSheet('background:rgba(0,25,37,120);border:1px solid rgba(67,170,199,80);border-radius:10px;')
    tr=QHBoxLayout(top); tr.setContentsMargins(9,7,9,7); tr.setSpacing(8)
    lab=QLabel('FILTER'); lab.setStyleSheet(f'color:{C.TEXT_DIM};font:800 6.5pt "Exo 2";background:transparent;'); tr.addWidget(lab)
    self._activity_filter=QComboBox(); self._activity_filter.addItems(['ALL','VOICE','AI','TOOL','WEB','FILE','OK','WARN','ERROR','SYS']); self._activity_filter.setMinimumHeight(32); self._activity_filter.currentTextChanged.connect(lambda t:self._activity.set_filter(t)); tr.addWidget(self._activity_filter,1)
    tr.addWidget(QLabel('LIVE'))
    l.addWidget(top)
    body=QFrame(); body.setStyleSheet('background:rgba(0,8,15,145);border:1px solid rgba(55,145,175,72);border-radius:11px;')
    bl=QVBoxLayout(body); bl.setContentsMargins(6,6,6,6); bl.addWidget(_ActivityTimeline())
    self._activity=bl.itemAt(0).widget(); l.addWidget(body,1)
    self._activity_add('SYS: UI online')
    return f


def _new_image_panel(self):
    f=self._panel_base(); f.setObjectName('JarvisPanel_image'); f.setMinimumSize(700,520)
    l=QVBoxLayout(f); l.setContentsMargins(11,11,11,11); l.setSpacing(9)
    self._panel_header(f,'▧',lambda:self._set_panel_visible(f,False),'IMAGE PREVIEW','VISUAL ANALYSIS SURFACE')
    toolbar=QFrame(); toolbar.setStyleSheet('background:rgba(0,25,37,125);border:1px solid rgba(67,170,199,85);border-radius:10px;')
    tl=QHBoxLayout(toolbar); tl.setContentsMargins(9,7,9,7); tl.setSpacing(7)
    self._image_status=QLabel('NO IMAGE LOADED'); self._image_status.setStyleSheet(f'color:{C.TEXT};font:800 7pt "Exo 2";letter-spacing:1px;background:transparent;'); tl.addWidget(self._image_status,1)
    o=_GlowButton('OPEN','＋',compact=True); o.clicked.connect(self._open_image_file); tl.addWidget(o)
    c=_GlowButton('CLEAR','×',compact=True); c.clicked.connect(lambda:self._image_label.clear()); tl.addWidget(c)
    l.addWidget(toolbar)
    stage=QFrame(); stage.setStyleSheet('background:rgba(0,7,13,220);border:1px solid rgba(57,157,188,90);border-radius:12px;')
    st=QVBoxLayout(stage); st.setContentsMargins(8,8,8,8)
    self._image_label=QLabel('DROP OR OPEN AN IMAGE'); self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self._image_label.setMinimumHeight(330); self._image_label.setStyleSheet(f'color:{C.TEXT_DIM};font:800 9pt "Exo 2";letter-spacing:1.5px;background:rgba(0,18,28,125);border:1px dashed rgba(67,170,199,95);border-radius:10px;'); self._image_label.setScaledContents(False); st.addWidget(self._image_label,1)
    l.addWidget(stage,1)
    return f


def _new_content_panel(self):
    f=self._panel_base(); f.setObjectName('JarvisPanel_content'); f.setMinimumSize(700,470)
    l=QVBoxLayout(f); l.setContentsMargins(11,11,11,11); l.setSpacing(9)
    self._panel_header(f,'⌕',lambda:self._set_panel_visible(f,False),'CONTENT SURFACE','RESEARCH · DOCUMENTS · ANSWERS')
    title=QFrame(); title.setStyleSheet('background:rgba(0,24,36,125);border:1px solid rgba(69,167,198,85);border-radius:10px;')
    tl=QHBoxLayout(title); tl.setContentsMargins(10,8,10,8)
    self._content_title=QLabel('READY'); self._content_title.setStyleSheet(f'color:{C.WHITE};font:800 9pt "Orbitron";letter-spacing:1.5px;background:transparent;'); tl.addWidget(self._content_title,1)
    tag=QLabel('CONTENT'); tag.setStyleSheet(f'color:{C.PRI};font:800 6.5pt "Exo 2";background:transparent;'); tl.addWidget(tag)
    l.addWidget(title)
    self._content_text=QTextEdit(); self._content_text.setReadOnly(True); l.addWidget(self._content_text,1)
    return f


# Activate the visual redesign before JarvisUI/MainWindow instances are created.
MainWindow._panel_base = _new_panel_base
MainWindow._panel_header = _new_panel_header
MainWindow._build_quick_panel = _new_quick_panel
MainWindow._build_floating_panel = _new_floating_panel
MainWindow._build_model_panel = _new_model_panel
MainWindow._build_activity_panel = _new_activity_panel
MainWindow._build_image_panel = _new_image_panel
MainWindow._build_content_panel = _new_content_panel


# Extend the same skin to the standalone configuration surfaces.
_old_open_full_settings = MainWindow._open_full_settings
_old_open_layout_editor = MainWindow._open_layout_editor

def _skin_window(win):
    if win is None:
        return
    try:
        win.setStyleSheet(f"""
            QWidget {{
                background: #020b13;
                color: {C.WHITE};
                font-family: Rajdhani, Exo 2;
            }}
            QFrame {{
                background: rgba(3,17,27,235);
                border: 1px solid rgba(66,170,200,95);
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; }}
            QLineEdit, QTextEdit, QComboBox, QListWidget {{
                background: rgba(1,14,23,245);
                color: {C.WHITE};
                border: 1px solid rgba(64,157,188,110);
                border-radius: 8px;
                padding: 7px 9px;
            }}
            QPushButton {{
                background: rgba(1,24,36,220);
                color: #bcefff;
                border: 1px solid rgba(67,176,207,125);
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: rgba(0,108,145,135);
                border-color: rgba(96,218,244,220);
            }}
            QTabWidget::pane {{ border: 1px solid rgba(69,173,204,100); border-radius: 10px; background: rgba(2,12,20,245); }}
            QTabBar::tab {{ background: rgba(0,20,31,220); color: #6caebe; padding: 9px 16px; border: 1px solid rgba(57,143,171,80); margin-right: 3px; border-radius: 7px; }}
            QTabBar::tab:selected {{ color: #e5fbff; background: rgba(0,113,152,145); border-color: rgba(87,206,236,190); }}
            QCheckBox {{ background: transparent; color: {C.TEXT}; spacing: 8px; }}
            QSlider::groove:horizontal {{ height: 5px; background: rgba(41,83,98,180); border-radius: 3px; }}
            QSlider::handle:horizontal {{ width: 16px; margin: -5px 0; background: #69d8f5; border: 1px solid #b8f2ff; border-radius: 8px; }}
        """)
        win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    except Exception:
        pass

def _open_full_settings_redesign(self):
    result = _old_open_full_settings(self)
    try:
        _skin_window(getattr(self, '_full_settings_window', None))
    except Exception:
        pass
    return result

def _open_layout_editor_redesign(self):
    result = _old_open_layout_editor(self)
    try:
        _skin_window(getattr(self, '_layout_editor', None))
    except Exception:
        pass
    return result

MainWindow._open_full_settings = _open_full_settings_redesign
MainWindow._open_layout_editor = _open_layout_editor_redesign

class JarvisUI:
    def __init__(self, face_path: str, size=None):
        self._app=QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle('Fusion')
        cfg=_read_full_config(); fam=cfg.get('ui_font')
        if fam: self._app.setFont(QFont(fam,10))
        self._win=MainWindow(face_path); self._win.show(); self.root=_RootShim(self._app)

    @property
    def muted(self): return self._win._muted
    @muted.setter
    def muted(self,v):
        if bool(v)!=self._win._muted: self._win._toggle_mute()
    @property
    def voice_input_enabled(self):
        return self._win.voice_input_enabled
    def feature_enabled(self, name: str) -> bool:
        return bool(self._win._features.get(name, True))
    @property
    def current_file(self): return self._win.current_file
    def __getattr__(self, name: str):
        # Delegate anything not explicitly wrapped (play_web_music,
        # control_jarvis_window, play_local_video, panel openers, …) to the
        # real MainWindow so backend tools never hit a missing attribute.
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        try:
            win = object.__getattribute__(self, '_win')
        except AttributeError:
            raise AttributeError(name)
        return getattr(win, name)

    @property
    def on_text_command(self): return self._win.on_text_command
    @on_text_command.setter
    def on_text_command(self,cb): self._win.on_text_command=cb
    @property
    def on_remote_clicked(self): return self._win.on_remote_clicked
    @on_remote_clicked.setter
    def on_remote_clicked(self,cb): self._win.on_remote_clicked=cb
    @property
    def on_interrupt(self): return self._win.on_interrupt
    @on_interrupt.setter
    def on_interrupt(self,cb): self._win.on_interrupt=cb
    @property
    def on_voice_change(self): return self._win.on_voice_change
    @on_voice_change.setter
    def on_voice_change(self,cb): self._win.on_voice_change=cb
    @property
    def on_audio_device_change(self): return self._win.on_audio_device_change
    @on_audio_device_change.setter
    def on_audio_device_change(self,cb): self._win.on_audio_device_change=cb
    def show_confirm(self,title,detail): self._win._confirm_sig.emit(str(title)[:120],str(detail)[:300])
    def hide_confirm(self): self._win._confirm_hide_sig.emit()
    @property
    def get_plugins(self): return self._win.get_plugins
    @get_plugins.setter
    def get_plugins(self,cb): self._win.get_plugins=cb
    @property
    def request_say(self): return self._win.request_say
    @request_say.setter
    def request_say(self,cb): self._win.request_say=cb
    def run_on_ui(self, fn): return self._win.run_on_ui(fn)
    def call_on_ui(self, fn, timeout=15.0): return self._win.call_on_ui(fn, timeout=timeout)
    def set_audio_level(self,level): self._win.set_audio_level(level)
    def notify_phone_connected(self): self._win.notify_phone_connected()
    def set_state(self,state): self._win._state_sig.emit(state)
    def write_log(self,text): self._win._log_sig.emit(text)
    def wait_for_api_key(self):
        while not self._win._ready: time.sleep(0.1)
    def show_content(self,title,text): self._win._content_sig.emit(title[:80],text[:12000])
    def show_image_url(self,url,caption='Research image'): self._win.show_image_url(url,caption)
    def show_image_path(self,path,caption='Generated image'): self._win.show_image_path(path,caption)
    def prompt_reconfig(self): self._win._ready=False; self._win._reconfig_sig.emit()
    def show_camera_frame(self,img_bytes): self._win._camera_sig.emit(img_bytes)
    def start_camera_stream(self): self._win.start_camera_stream()
    def stop_camera_stream(self): self._win.stop_camera_stream()
    @property
    def assistant_name(self): return self._win._assistant_name
    def start_speaking(self): self.set_state('SPEAKING')
    def stop_speaking(self):
        if not self.muted: self.set_state('LISTENING')
