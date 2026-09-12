"""J.A.R.V.I.S standalone settings/control center.

The settings window is deliberately independent from the compact Arc Reactor.
Opening it never expands, hides, or replaces the main reactor.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QRectF, QPointF
from PyQt6.QtGui import (
    QColor, QFont, QBrush, QPainter, QPen, QPainterPath, QLinearGradient, QRadialGradient, QKeySequence, QShortcut, QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QSlider, QSpinBox, QTabBar, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget, QFileDialog, QDoubleSpinBox
)

DEFAULTS = {
    "compact_opacity": 0,
    "compact_size": 176,
    "ui_opacity": 82,
    "reactor_opacity": 100,
    "reactor_stroke_opacity": 100,
    "reactor_animation_speed": 1.0,
    "equalizer_sensitivity": 1.0,
    "voice_speed": 1.0,
    "voice_pitch": 0.0,
    "voice_volume": 1.0,
    "voice_mode": "standard",
    "tts_engine": "edgetts",
    "tts_voice": "en-GB-RyanNeural",
    "voice_name": "Charon",
    "fish_audio_api_key": "",
    "fish_audio_model_id": "s2-pro",
    "fish_audio_voice_id": "",
    "fish_audio_endpoint": "https://api.fish.audio/v1/tts",
    "fish_audio_format": "mp3",
    "fish_audio_latency": "normal",
    "elevenlabs_api_key": "",
    "elevenlabs_voice_id": "pNInz6obpgDQGcFmaJgB",
    "elevenlabs_model_id": "eleven_multilingual_v2",
    "assistant_name": "JARVIS",
    "user_name": "",
    "ai_provider": "gemini",
    "ai_model": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "groq_api_key": "",
    "custom_provider_name": "",
    "custom_ai_base_url": "",
    "custom_ai_api_key": "",
    "custom_ai_model": "",
    "ui_font": "Rajdhani",
    "ui_color": "#00d4ff",
    "web_homepage": "https://www.google.com",
    "world_monitor_refresh": 60,
    "memory_autosave": True,
    "panel_always_on_top": True,
    "hud_grid": True,
    "ui_x": None,
    "ui_y": None,
    "quick_actions": [],
    "features": {
        "audio_reactive": True,
        "smooth_animations": True,
        "chat_history": True,
        "compact_mode": True,
        "drag_reactor": True,
        "remember_position": True,
        "hide_taskbar_button": False,
        "autostart": False,
        "wake_word": True,
        "hands_free": True,
        "push_to_talk": False,
        "voice_activity_detection": True,
        "voice_interruption": True,
        "barge_in": True,
        "background_listening": True,
        "always_on": False,
        "voice_command_recognition": True,
        "computer_control": True,
        "desktop_awareness": True,
        "screen_understanding": True,
        "mouse_keyboard_control": True,
        "window_control": True,
        "terminal_control": True,
        "file_control": True,
        "desktop_automation": True,
        "webview": True,
        "webview_engine": True,
        "webview_music": True,
        "web_task": True,
        "world_monitor": True,
        "floating_windows": True,
        "draggable_panels": True,
        "enable_sfx": True,
        "proactive_speaking": False,
        "mic_access": True,
        "camera_access": True,
    },
}


def load(path: str | Path) -> dict:
    path = Path(path)
    data = dict(DEFAULTS)
    data["features"] = dict(DEFAULTS["features"])
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
            if isinstance(raw.get("features"), dict):
                data["features"].update(raw["features"])
    except Exception:
        pass
    return data


def save(path: str | Path, **updates) -> dict:
    path = Path(path)
    data = load(path)
    for k, v in updates.items():
        if k == "features" and isinstance(v, dict):
            merged = dict(data.get("features", {}))
            merged.update(v)
            data[k] = merged
        else:
            data[k] = v
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return data


def _default_config_path() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base / "config" / "api_keys.json"


class HorizontalNavBar(QTabBar):
    """Reference-style left rail with horizontal labels and angular cards."""
    def tabSizeHint(self, index):
        base = super().tabSizeHint(index)
        return QSize(150, max(46, base.height()))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i in range(self.count()):
            r = self.tabRect(i).adjusted(4, 4, -5, -4)
            cut = 8
            path = QPainterPath()
            path.moveTo(r.left()+cut, r.top())
            path.lineTo(r.right()-cut, r.top())
            path.lineTo(r.right(), r.top()+cut)
            path.lineTo(r.right(), r.bottom()-cut)
            path.lineTo(r.right()-cut, r.bottom())
            path.lineTo(r.left()+cut, r.bottom())
            path.lineTo(r.left(), r.bottom()-cut)
            path.lineTo(r.left(), r.top()+cut)
            path.closeSubpath()
            selected = i == self.currentIndex()
            p.setPen(QPen(QColor('#58d6f5' if selected else '#123543'), 1))
            p.fillPath(path, QBrush(QColor(6, 40, 56, 170) if selected else QColor(4, 16, 26, 92)))
            p.drawPath(path)
            if selected:
                p.setPen(QPen(QColor('#8ceaff'), 2))
                p.drawLine(r.left()+2, r.top()+10, r.left()+2, r.bottom()-10)
            p.setPen(QColor('#daf5ff' if selected else '#547f92'))
            p.setFont(QFont('Exo 2', 8, QFont.Weight.Bold))
            p.drawText(r.adjusted(16, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.tabText(i))
        p.end()


class HudGroupBox(QGroupBox):
    """Angular transparent HUD panel inspired by the supplied reference sheet."""
    def __init__(self, title='', parent=None):
        super().__init__(title, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setProperty('_jarvis_floating_panel', True)
        self.setProperty('_jarvis_panel_kind', 'control_center')
        self.setProperty('_jarvis_panel_key', 'control_center')
        self.setObjectName('HudGroupBox')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = self.rect().adjusted(1, 1, -1, -1)
        cut = 12
        path = QPainterPath()
        pts = [
            QPointF(r.left()+cut, r.top()), QPointF(r.right()-cut, r.top()),
            QPointF(r.right(), r.top()+cut), QPointF(r.right(), r.bottom()-cut),
            QPointF(r.right()-cut, r.bottom()), QPointF(r.left()+cut, r.bottom()),
            QPointF(r.left(), r.bottom()-cut), QPointF(r.left(), r.top()+cut),
        ]
        path.moveTo(pts[0])
        for pt in pts[1:]: path.lineTo(pt)
        path.closeSubpath()
        p.fillPath(path, QBrush(QColor(3, 18, 30, 158)))
        p.setPen(QPen(QColor(60, 156, 190, 70), 1))
        p.drawPath(path)
        # Title cutout and caption.
        title = self.title()
        if title:
            f = QFont('Orbitron', 7, QFont.Weight.Bold)
            fm = p.fontMetrics(); tw = fm.horizontalAdvance(title) + 18
            tr = QRectF(r.left()+10, r.top()-7, tw, 16)
            p.setPen(QColor('#56d6f5')); p.setFont(f)
            p.drawText(tr, Qt.AlignmentFlag.AlignCenter, title)
        p.end()


class HudHeader(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('HudHeader')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = self.rect().adjusted(1,1,-1,-1)
        cut = 9
        path = QPainterPath()
        path.moveTo(r.left()+cut, r.top()); path.lineTo(r.right()-22, r.top())
        path.lineTo(r.right(), r.top()+22); path.lineTo(r.right(), r.bottom()-cut)
        path.lineTo(r.right()-cut, r.bottom()); path.lineTo(r.left()+cut, r.bottom())
        path.lineTo(r.left(), r.bottom()-cut); path.lineTo(r.left(), r.top()+cut); path.closeSubpath()
        p.fillPath(path, QBrush(QColor(5, 24, 37, 160)))
        p.setPen(QPen(QColor(88, 214, 245, 90), 1))
        p.drawPath(path)
        p.end()


def _hud_cut_path(rect, cut=14):
    path = QPainterPath()
    cut = max(8, min(cut, min(rect.width(), rect.height()) / 6))
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


class _ControlCenterBackdrop(QFrame):
    """Angular grid-and-glow background used by the standalone control center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            w, h = max(1, self.width()), max(1, self.height())
            bounds = QRectF(1.5, 1.5, w - 3.0, h - 3.0)
            cut = max(12, min(18, min(w, h) * 0.03))
            clip = _hud_cut_path(bounds, cut)
            p.setClipPath(clip)
            gradient = QLinearGradient(0, 0, w, h)
            gradient.setColorAt(0.0, QColor(5, 34, 50, 238))
            gradient.setColorAt(0.5, QColor(2, 8, 16, 246))
            gradient.setColorAt(1.0, QColor(4, 30, 44, 234))
            p.fillPath(clip, QBrush(gradient))

            glow = QRadialGradient(QPointF(w * 0.80, h * 0.16), max(w, h) * 0.72)
            glow.setColorAt(0.0, QColor(86, 214, 245, 40))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillPath(clip, QBrush(glow))

            # A single warm counterpoint low-left so the cold field has depth.
            gold = QRadialGradient(QPointF(w * 0.10, h * 0.92), max(w, h) * 0.55)
            gold.setColorAt(0.0, QColor(244, 178, 74, 16))
            gold.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillPath(clip, QBrush(gold))

            p.setPen(QPen(QColor(60, 156, 190, 22), 1))
            for x in range(0, w + 28, 28):
                p.drawLine(x, 0, x, h)
            for y in range(0, h + 28, 28):
                p.drawLine(0, y, w, y)
            # Crisp inner frame to sell the glass edge.
            p.setPen(QPen(QColor(88, 214, 245, 60), 1))
            p.drawPath(clip)
            p.setClipping(False)
        except Exception:
            pass
        p.end()


class _SettingsRoot(QFrame):
    """Root shell that keeps the painted backdrop fitted to the dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._futuristic_backdrop = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_backdrop()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_backdrop()

    def _fit_backdrop(self):
        backdrop = self._futuristic_backdrop
        if backdrop is not None:
            backdrop.setGeometry(self.rect())
            backdrop.lower()


class SettingsWindow(QDialog):
    """Full-featured tabbed control center for J.A.R.V.I.S."""

    settings_saved = pyqtSignal(dict)
    voice_test_requested = pyqtSignal(str)

    def __init__(self, config_path: str | Path | None = None, parent=None):
        super().__init__(parent)
        self._config_path = Path(config_path) if config_path else _default_config_path()
        self._data = load(self._config_path)
        self._color = str(self._data.get("ui_color", DEFAULTS["ui_color"]))
        self._drag_offset = None
        self._layout_rows: dict[str, dict] = {}
        self._layout_selected_name = None

        self.setWindowTitle("J.A.R.V.I.S Settings")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setProperty('_jarvis_floating_panel', True)
        self.setProperty('_jarvis_panel_kind', 'control_center')
        self.setProperty('_jarvis_panel_key', 'control_center')
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setMinimumSize(940, 680)
        self.resize(1120, 760)

        self._build_style()
        self._build_ui()
        self._load_layout_values()
        self.tabs.currentChanged.connect(self._sync_nav_status)
        self._sync_nav_status(self.tabs.currentIndex())

    def _build_style(self):
        # One high-density visual language for the entire control center.
        # Refined Stark HUD: vacuum-black glass, arc-reactor cyan as the working
        # color, gold reserved for the single committed action.
        self.setStyleSheet("""
            QDialog { background: transparent; color: #daf5ff; }

            QFrame#SettingsRoot {
                background: transparent;
                border: none;
            }

            QFrame#HudHeader {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(6,30,45,238),
                    stop:0.55 rgba(3,18,30,222),
                    stop:1 rgba(4,32,47,205)
                );
                border: 1px solid rgba(88,214,245,150);
                border-radius: 12px;
            }

            QTabWidget { background: transparent; }
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar { background: transparent; }

            QTabBar::tab {
                min-width: 154px;
                min-height: 46px;
                color: #6ba7bb;
                background: rgba(4,18,29,92);
                border: 1px solid rgba(60,156,190,50);
                border-left: 2px solid transparent;
                border-radius: 9px;
                padding: 8px 13px;
                margin: 2px 8px 5px 0;
                text-align: left;
                font: 700 8pt "Exo 2";
            }
            QTabBar::tab:hover {
                color: #f0fdff;
                background: rgba(10,134,184,58);
                border-color: rgba(88,214,245,120);
            }
            QTabBar::tab:selected {
                color: #f0fdff;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(10,134,184,140),
                    stop:1 rgba(4,50,72,150)
                );
                border-color: rgba(88,214,245,120);
                border-left: 2px solid #56d6f5;
            }

            QLabel { color: #a6e9ff; background: transparent; }

            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: rgba(3,17,29,215);
                color: #f0fdff;
                border: 1px solid rgba(60,156,190,90);
                border-radius: 9px;
                padding: 8px 11px;
                min-height: 20px;
                selection-background-color: rgba(10,134,184,150);
            }
            QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: rgba(88,214,245,150);
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #56d6f5;
                background: rgba(4,26,40,238);
            }
            QComboBox::drop-down {
                width: 26px;
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background: #02060c;
                color: #daf5ff;
                border: 1px solid rgba(60,156,190,120);
                border-radius: 6px;
                selection-background-color: rgba(10,134,184,150);
                selection-color: #f0fdff;
                padding: 4px;
            }

            QPushButton {
                background: rgba(5,22,34,150);
                color: #a6e9ff;
                border: 1px solid rgba(60,156,190,90);
                border-radius: 6px;
                padding: 8px 13px;
                min-height: 20px;
                font: 700 8pt "Exo 2";
            }
            QPushButton:hover {
                background: rgba(10,134,184,90);
                border-color: #56d6f5;
                color: #f0fdff;
            }
            QPushButton:pressed {
                background: rgba(9,110,152,200);
                padding-top: 9px;
            }
            QPushButton#PrimaryButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8ceaff,
                    stop:1 #56d6f5
                );
                color: #04121a;
                border: 1px solid #b6f2ff;
                border-radius: 6px;
                font: 800 8pt "Exo 2";
            }
            QPushButton#PrimaryButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b6f2ff,
                    stop:1 #8ceaff
                );
                border-color: #d6f8ff;
            }

            QCheckBox {
                spacing: 9px;
                padding: 6px 4px;
                color: #a6e9ff;
                background: transparent;
                font: 600 9pt "Rajdhani";
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #1f5f76;
                background: rgba(3,17,26,180);
                border-radius: 4px;
            }
            QCheckBox::indicator:hover {
                border-color: #56d6f5;
            }
            QCheckBox::indicator:checked {
                background: #56d6f5;
                border-color: #b6f2ff;
            }

            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(3,20,30,200);
                border: 1px solid rgba(52,128,158,90);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                height: 4px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0a86b8,
                    stop:1 #56d6f5
                );
                border-radius: 2px;
            }
            QSlider::add-page:horizontal {
                background: rgba(3,18,26,150);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 15px;
                height: 15px;
                margin: -6px 0;
                background: #f0fdff;
                border: 2px solid #56d6f5;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #ffffff;
                border-color: #8ceaff;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(30,116,142,190);
                border-radius: 4px;
                min-height: 26px;
            }
            QScrollBar::handle:vertical:hover {
                background: #56d6f5;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QListWidget {
                background: rgba(2,12,21,160);
                color: #daf5ff;
                border: 1px solid rgba(60,156,190,80);
                border-radius: 10px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 9px 10px;
                margin: 2px 0;
                border: 1px solid transparent;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: rgba(10,134,184,55);
                border-color: rgba(88,214,245,60);
            }
            QListWidget::item:selected {
                background: rgba(10,134,184,110);
                color: #f0fdff;
                border-color: rgba(88,214,245,110);
            }

            QTextEdit {
                background: rgba(2,12,21,170);
                color: #daf5ff;
                border: 1px solid rgba(60,156,190,80);
                border-radius: 10px;
                padding: 8px;
            }
            QTextEdit:focus { border-color: #56d6f5; }

            QGroupBox {
                background: rgba(3,16,27,90);
                border: 1px solid rgba(60,156,190,85);
                border-radius: 12px;
                margin-top: 16px;
                padding: 16px 14px 13px 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #56d6f5;
                background: #02060c;
                font: 800 8pt "Orbitron";
            }

            QToolTip {
                background: #01040a;
                color: #f0fdff;
                border: 1px solid #0a86b8;
                padding: 6px 8px;
                border-radius: 5px;
            }
        """)

    def _build_ui(self):
        root = _SettingsRoot(self)
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.addWidget(root)
        backdrop = _ControlCenterBackdrop(root)
        root._futuristic_backdrop = backdrop
        root._fit_backdrop()

        outer = QVBoxLayout(root)
        outer.setContentsMargins(11, 11, 11, 11)
        outer.setSpacing(12)

        header = HudHeader(root)
        header.setFixedHeight(68)
        hb = QHBoxLayout(header)
        hb.setContentsMargins(18, 9, 10, 9)
        hb.setSpacing(14)

        icon = QLabel("◈")
        icon.setStyleSheet('color:#56d6f5;font:700 20pt "Segoe UI Symbol";background:transparent;')
        hb.addWidget(icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("J.A.R.V.I.S  //  CONTROL CENTER")
        title.setMinimumWidth(300)
        title.setWordWrap(False)
        title.setStyleSheet('color:#f0fdff;font:800 12pt "Orbitron";background:transparent; letter-spacing:2px;')
        subtitle = QLabel("GENERAL • AI • VOICE • SYSTEM • MEMORY • PLUGINS")
        subtitle.setStyleSheet('color:#547f92;font:700 7pt "Exo 2";background:transparent; letter-spacing:1px;')
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hb.addLayout(title_box)
        hb.addStretch(1)

        self._status = QLabel("●  READY  //  CONTROL CENTER")
        self._status.setStyleSheet('color:#5df0b6;font:800 8pt "Exo 2";background:rgba(9,64,50,90);padding:7px 12px;border:1px solid rgba(93,240,182,85);border-radius:7px; letter-spacing:1px;')
        hb.addWidget(self._status)
        close = QPushButton("×")
        close.setFixedSize(34, 34)
        close.setToolTip("Close control center")
        close.setStyleSheet("QPushButton { background: transparent; color: #6ba7bb; border: none; border-radius: 7px; font: 700 16pt 'Rajdhani'; padding: 0px; } QPushButton:hover { color: #ff6f8b; background: rgba(60, 10, 20, 130); }")
        close.clicked.connect(self.close)
        hb.addWidget(close)
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabBar(HorizontalNavBar())
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setUsesScrollButtons(True)
        self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideRight)
        body.addWidget(self.tabs, 1)
        outer.addLayout(body, 1)

        self._build_general_tab()
        self._build_ai_tab()
        self._build_voice_tab()
        self._build_personality_tab()
        self._build_system_tab()
        self._build_automation_tab()
        self._build_memory_settings_tab()
        self._build_permissions_tab()
        self._build_layout_tab()
        self._build_plugins_tab()
        self._build_diagnostics_tab()
        self._build_web_tab()
        self._build_3d_tab()
        self._build_video_tab()
        self._build_image_tab()

        footer = QHBoxLayout()
        footer.setSpacing(8)
        hint = QLabel("CHANGES ARE STORED IN CONFIG / API_KEYS.JSON")
        hint.setStyleSheet('color:#3f7b8a;font:600 7pt "Exo 2";padding-left:4px;')
        footer.addWidget(hint)
        footer.addStretch(1)
        reset = QPushButton("RESET")
        reset.setToolTip("Restore default J.A.R.V.I.S settings")
        reset.clicked.connect(self.reset_defaults)
        footer.addWidget(reset)
        save_btn = QPushButton("SAVE CHANGES")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save_settings)
        footer.addWidget(save_btn)
        outer.addLayout(footer)

        header.mousePressEvent = self._header_press
        header.mouseMoveEvent = self._header_move
        header.mouseReleaseEvent = self._header_release
        title.mousePressEvent = self._header_press
        title.mouseMoveEvent = self._header_move
        title.mouseReleaseEvent = self._header_release

        self._close_shortcut = QShortcut(QKeySequence("Shift+Home"), self)
        self._close_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._close_shortcut.activated.connect(self.close)

    def _sync_nav_status(self, index: int):
        labels = ["GENERAL", "AI", "VOICE", "PERSONALITY", "SYSTEM", "AUTOMATION",
                  "MEMORY", "PERMISSIONS", "LAYOUT", "PLUGINS", "DIAG", "WEB",
                  "3D", "VIDEO", "IMAGE"]
        if 0 <= index < len(labels):
            self._status.setText(f"●  {labels[index]}")

    def _scroll_tab(self):
        page = QWidget()
        page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        page.setStyleSheet('background: transparent;')
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setStyleSheet('QScrollArea { background: transparent; border: none; } QScrollArea > QWidget > QWidget { background: transparent; }')
        area.viewport().setStyleSheet('background: transparent;')
        area.setWidget(page)
        return page, QVBoxLayout(page), area

    def _tab_intro(self, lay, text):
        row = QFrame()
        row.setObjectName("TabIntro")
        row.setStyleSheet("""
            QFrame#TabIntro {
                background: rgba(1,18,29,115);
                border: 1px solid rgba(55,150,181,75);
                border-radius: 10px;
                padding: 2px;
            }
        """)
        rv = QHBoxLayout(row)
        rv.setContentsMargins(11, 7, 11, 7)
        rv.setSpacing(9)
        marker = QLabel("◈")
        marker.setStyleSheet('color:#51d9ff;font:700 12pt "Segoe UI Symbol";background:transparent;')
        label = QLabel(text)
        label.setStyleSheet('color:#51d9ff;font:800 8.5pt "Orbitron";background:transparent;letter-spacing:2px;')
        rv.addWidget(marker)
        rv.addWidget(label, 1)
        telemetry = QLabel("JARVIS CONTROL MATRIX")
        telemetry.setStyleSheet('color:#4f8d9f;font:700 6.5pt "Exo 2";background:transparent;letter-spacing:1px;')
        rv.addWidget(telemetry)
        lay.addWidget(row)

    def _build_general_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "GENERAL  //  THEME · REACTOR · WINDOWS")

        appearance = HudGroupBox("APPEARANCE / THEME")
        form = QFormLayout(appearance)
        self.font = QComboBox()
        fonts = ["Rajdhani", "Orbitron", "Share Tech Mono", "Exo 2", "Segoe UI", "Segoe UI Variable", "Consolas", "Cascadia Code", "JetBrains Mono", "Arial", "Tahoma"]
        self.font.addItems(fonts)
        self.font.setCurrentText(str(self._data.get("ui_font", "Rajdhani")))
        form.addRow("Font", self.font)
        self.color_btn = QPushButton(self._color)
        self.color_btn.clicked.connect(self.pick_color)
        form.addRow("Accent color", self.color_btn)
        quick = QHBoxLayout()
        for label, color in [("CYAN", "#00d4ff"), ("RED", "#ff3355"), ("GREEN", "#00ff88"), ("GOLD", "#ffcc00"), ("WHITE", "#d8f8ff")]:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, c=color: self._set_color(c))
            quick.addWidget(b)
        form.addRow("Presets", quick)
        lay.addWidget(appearance)

        reactor = HudGroupBox("REACTOR / UI")
        rv = QVBoxLayout(reactor)
        self.ui_opacity = self._slider_row(rv, "Glass opacity", int(self._data.get("ui_opacity", 82)), 0, 100, "%")
        self.reactor_opacity = self._slider_row(rv, "Reactor opacity", int(self._data.get("reactor_opacity", 60)), 0, 100, "%")
        self.reactor_stroke_opacity = self._slider_row(rv, "Reactor stroke opacity", int(self._data.get("reactor_stroke_opacity", 100)), 0, 100, "%")
        self.anim_speed = self._slider_row(rv, "Animation speed", int(float(self._data.get("reactor_animation_speed", 1.0))*100), 25, 250, "%")
        self.eq_sens = self._slider_row(rv, "Equalizer sensitivity", int(float(self._data.get("equalizer_sensitivity", 1.0))*100), 10, 300, "%")
        self.reactor_size = self._slider_row(rv, "Arc Reactor size", int(self._data.get("compact_size", 176)), 120, 500, " px")
        # Resizing (or tweaking) auto-saves so the reactor applies + persists live.
        for _sl in (self.ui_opacity, self.reactor_opacity, self.reactor_stroke_opacity,
                    self.anim_speed, self.eq_sens, self.reactor_size):
            try:
                _sl.sliderReleased.connect(self._autosave_quiet)
            except Exception:
                pass
        lay.addWidget(reactor)

        behavior = HudGroupBox("WINDOW BEHAVIOR")
        bv = QVBoxLayout(behavior)
        self._compact = QCheckBox("Always keep the main HUD compact")
        self._compact.setChecked(True)
        self._drag = QCheckBox("Allow the small Arc Reactor button to be dragged")
        self._drag.setChecked(bool(self._data.get("features", {}).get("drag_reactor", True)))
        self._remember = QCheckBox("Remember Arc Reactor position")
        self._remember.setChecked(bool(self._data.get("features", {}).get("remember_position", True)))
        self._remember.setToolTip("Save and restore the compact reactor window position.")
        for cb in (self._compact, self._drag, self._remember):
            bv.addWidget(cb)
        lay.addWidget(behavior)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "GENERAL")

    def _build_voice_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "VOICE  //  ENGINES · KEYS · TESTS")
        voice = HudGroupBox("VOICE ASSISTANT")
        vv = QVBoxLayout(voice)

        # ── 1 · Engine (pick one; only its fields are used) ──
        engine_box = HudGroupBox("1 · SPEECH ENGINE")
        ef = QFormLayout(engine_box)
        self.tts_engine = QComboBox()
        self.tts_engine.addItems(["edgetts", "elevenlabs", "fish_audio", "kokoro"])
        self.tts_engine.setCurrentText(str(self._data.get("tts_engine", "edgetts")))
        self.tts_engine.setToolTip("edgetts = free Microsoft voices · elevenlabs = cloud API key · fish_audio = Fish Audio API · kokoro = offline")
        self.tts_engine.currentTextChanged.connect(self._refresh_voice_fields)
        ef.addRow("Engine", self.tts_engine)
        self.tts_voice = QLineEdit(str(self._data.get("tts_voice", "en-GB-RyanNeural")))
        self.tts_voice.setPlaceholderText("e.g. en-GB-RyanNeural")
        ef.addRow("Edge voice", self.tts_voice)
        self.live_voice = QComboBox()
        self.live_voice.addItems(["Charon", "Puck", "Kore", "Fenrir", "Aoede"])
        self.live_voice.setCurrentText(str(self._data.get("voice_name", "Charon")))
        self.live_voice.setToolTip("Gemini Live voice used by the real-time voice assistant.")
        ef.addRow("Live assistant voice", self.live_voice)
        test_voice = QPushButton("TEST VOICE LINK")
        test_voice.setToolTip("Ask the active J.A.R.V.I.S session to speak a short professional greeting.")
        test_voice.clicked.connect(self._test_voice_link)
        ef.addRow("", test_voice)
        test_engine = QPushButton("TEST SELECTED ENGINE")
        test_engine.setToolTip("Speak a short test line through the selected speech engine. Exact API errors appear in the status bar.")
        test_engine.clicked.connect(self._test_tts_engine)
        ef.addRow("", test_engine)
        vv.addWidget(engine_box)

        # ── 2 · ElevenLabs (only used when engine = elevenlabs) ──
        self._eleven_box = HudGroupBox("2 · ELEVENLABS (cloud)")
        elf = QFormLayout(self._eleven_box)
        self.elevenlabs_api_key = QLineEdit(str(self._data.get("elevenlabs_api_key", "")))
        self.elevenlabs_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.elevenlabs_api_key.setPlaceholderText("sk_… ElevenLabs API key")
        elf.addRow("API key", self.elevenlabs_api_key)
        self.elevenlabs_voice_id = QLineEdit(str(self._data.get("elevenlabs_voice_id", DEFAULTS["elevenlabs_voice_id"])))
        self.elevenlabs_voice_id.setPlaceholderText("20-char voice ID (default Adam)")
        self.elevenlabs_voice_id.setToolTip("ElevenLabs voice ID — 20 characters, e.g. pNInz6obpgDQGcFmaJgB (Adam). NOT an Edge name like en-US-GuyNeural.")
        elf.addRow("Voice ID", self.elevenlabs_voice_id)
        self.elevenlabs_model_id = QComboBox()
        self.elevenlabs_model_id.addItems(["eleven_v3", "eleven_multilingual_v2", "eleven_flash_v2_5"])
        self.elevenlabs_model_id.setCurrentText(str(self._data.get("elevenlabs_model_id", DEFAULTS["elevenlabs_model_id"])))
        elf.addRow("Model", self.elevenlabs_model_id)
        vv.addWidget(self._eleven_box)

        # ── 3 · Fish Audio (only used when engine = fish_audio) ──
        self._fish_box = HudGroupBox("3 · FISH AUDIO (cloud)")
        ff = QFormLayout(self._fish_box)
        self.fish_api_key = QLineEdit(str(self._data.get("fish_audio_api_key", "")))
        self.fish_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.fish_api_key.setPlaceholderText("Fish Audio API key")
        ff.addRow("API key", self.fish_api_key)
        self.fish_model_id = QLineEdit(str(self._data.get("fish_audio_model_id", "s1")))
        self.fish_model_id.setPlaceholderText("Backend: s1 or s2-pro")
        self.fish_model_id.setToolTip("Fish Audio backend model (e.g. s1, s2.1-pro). A voice ID typed here is auto-detected as the voice.")
        ff.addRow("Model", self.fish_model_id)
        self.fish_voice_id = QLineEdit(str(self._data.get("fish_audio_voice_id", "")))
        self.fish_voice_id.setPlaceholderText("Reference voice ID")
        ff.addRow("Voice ID", self.fish_voice_id)
        self.fish_endpoint = QLineEdit(str(self._data.get("fish_audio_endpoint", DEFAULTS["fish_audio_endpoint"])))
        ff.addRow("Endpoint", self.fish_endpoint)
        fish_row = QHBoxLayout()
        self.fish_format = QComboBox()
        self.fish_format.addItems(["mp3", "wav", "opus"])
        self.fish_format.setCurrentText(str(self._data.get("fish_audio_format", "mp3")))
        fish_row.addWidget(self.fish_format)
        self.fish_latency = QComboBox()
        self.fish_latency.addItems(["normal", "balanced"])
        _lat = str(self._data.get("fish_audio_latency", "normal"))
        self.fish_latency.setCurrentText("balanced" if _lat == "low" else _lat)
        fish_row.addWidget(self.fish_latency)
        ff.addRow("Format / latency", fish_row)
        vv.addWidget(self._fish_box)
        self._refresh_voice_fields(self.tts_engine.currentText())
        lay.addWidget(voice)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "VOICE")

    def _build_personality_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "PERSONALITY  //  IDENTITY · DELIVERY · VOICE TUNE")
        ident = HudGroupBox("IDENTITY")
        form = QFormLayout(ident)
        self.assistant_name = QLineEdit(str(self._data.get("assistant_name", "JARVIS") or "JARVIS"))
        self.assistant_name.setPlaceholderText("JARVIS")
        form.addRow("Assistant name", self.assistant_name)
        self.user_name = QLineEdit(str(self._data.get("user_name", "") or ""))
        self.user_name.setPlaceholderText("How should JARVIS address you? (empty = sir)")
        form.addRow("Your name", self.user_name)
        lay.addWidget(ident)

        delivery = HudGroupBox("DELIVERY")
        dv = QVBoxLayout(delivery)
        form2 = QFormLayout()
        self.voice_mode = QComboBox()
        self.voice_mode.addItems(["standard", "executive", "friendly", "focus", "emergency", "cinematic"])
        self.voice_mode.setCurrentText(str(self._data.get("voice_mode", "standard")))
        form2.addRow("Delivery mode", self.voice_mode)
        dv.addLayout(form2)
        self.voice_speed = self._slider_row(dv, "Speaking speed", int(float(self._data.get("voice_speed", 1.0)) * 100), 50, 200, "%")
        self.voice_pitch = self._slider_row(dv, "Voice pitch", int(float(self._data.get("voice_pitch", 0.0)) * 10), -20, 20, " st")
        self.voice_volume = self._slider_row(dv, "Voice volume", int(float(self._data.get("voice_volume", 1.0)) * 100), 0, 100, "%")
        lay.addWidget(delivery)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "PERSONALITY")

    def _flag_checkbox(self, store: dict, key: str, label: str, default: bool = True,
                       tip: str = "") -> QCheckBox:
        cb = QCheckBox(label)
        cb.setChecked(bool(store.get(key, default)))
        if tip:
            cb.setToolTip(tip)
        store[key] = cb
        return cb

    def _build_automation_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "AUTOMATION  //  VOICE HANDS-FREE · COMPUTER · TASKS")
        self._voice_checks = {}
        voice_features = self._data.get("features", {}) or {}
        hands = HudGroupBox("VOICE AUTOMATION")
        hv = QVBoxLayout(hands)
        for key, label in [
            ("wake_word", 'Wake word: "Hey Jarvis"'),
            ("hands_free", "Hands-free voice mode"),
            ("push_to_talk", "Push-to-talk mode (F6)"),
            ("voice_activity_detection", "Voice activity detection"),
            ("voice_interruption", "Voice interruption"),
            ("barge_in", "Barge-in while JARVIS is speaking"),
            ("background_listening", "Background listening"),
            ("always_on", "Always-on mode"),
            ("voice_command_recognition", "Voice command recognition"),
            ("proactive_speaking", "Speak without being spoken to (proactive voice)"),
        ]:
            hv.addWidget(self._flag_checkbox(self._voice_checks, key, label,
                                             key not in {"push_to_talk", "always_on", "proactive_speaking"}))
        lay.addWidget(hands)

        computer = HudGroupBox("COMPUTER CONTROL")
        cv = QVBoxLayout(computer)
        for key, label in [
            ("computer_control", "Enable computer control"),
            ("desktop_awareness", "Desktop awareness and system status"),
            ("screen_understanding", "Screen capture and visual understanding"),
            ("mouse_keyboard_control", "Mouse, keyboard, clicking, and typing"),
            ("window_control", "Open, switch, move, resize, and control windows"),
            ("terminal_control", "Execute desktop and terminal commands"),
            ("file_control", "Control files and folders"),
            ("desktop_automation", "Automate repetitive desktop tasks"),
        ]:
            cv.addWidget(self._flag_checkbox(self._voice_checks, key, label, True))
        lay.addWidget(computer)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "AUTOMATION")

    def _build_permissions_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "PERMISSIONS  //  STARTUP · DEVICES · ACCESS")
        self._perm_checks = {}
        perms = HudGroupBox("SYSTEM ACCESS")
        pv = QVBoxLayout(perms)
        self._autostart = QCheckBox("Auto-start J.A.R.V.I.S with Windows")
        self._autostart.setChecked(bool(self._data.get("features", {}).get("autostart", False)))
        self._autostart.setToolTip("Registers J.A.R.V.I.S to start when you sign in to Windows.")
        pv.addWidget(self._autostart)
        self._taskbar = QCheckBox("Hide J.A.R.V.I.S from the Windows taskbar")
        feats = self._data.get("features", {}) or {}
        self._taskbar.setChecked(bool(feats.get("hide_taskbar_button", feats.get("hide_taskbar", False))))
        self._taskbar.setEnabled(sys.platform.startswith("win"))
        if not sys.platform.startswith("win"):
            self._taskbar.setToolTip("Windows only. The Windows taskbar itself stays visible; only the J.A.R.V.I.S taskbar button is hidden.")
        pv.addWidget(self._taskbar)
        lay.addWidget(perms)

        devices = HudGroupBox("DEVICE ACCESS")
        dv = QVBoxLayout(devices)
        dv.addWidget(self._flag_checkbox(self._perm_checks, "mic_access", "Microphone access (voice input)",
                                         True, "Off = JARVIS stays muted and cannot unmute."))
        dv.addWidget(self._flag_checkbox(self._perm_checks, "camera_access", "Camera access (webcam + vision)",
                                         True, "Off = camera captures are refused."))
        note = QLabel("Revoking a device takes effect on SAVE. The microphone mute (F4) still works as a quick override.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#5ab8cc;background:transparent;")
        dv.addWidget(note)
        lay.addWidget(devices)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "PERMISSIONS")

    def _test_voice_link(self):
        self.voice_test_requested.emit(
            "Please say a brief, professional greeting in refined natural British English."
        )
        self._status.setText("VOICE TEST SENT")

    def _test_tts_engine(self):
        """Speak a test line through the currently selected TTS engine.

        Runs off the GUI thread; the exact result (or API error) lands in
        the status bar so broken keys/voices can be diagnosed on the spot.
        """
        import threading

        try:
            cfg = self._collect()
        except Exception as exc:
            self._status.setText(f"TEST ERROR: {exc}")
            return
        engine = str(cfg.get("tts_engine", "edgetts"))
        self._status.setText(f"TESTING {engine.upper()}…")

        def _say(text: str):
            # Thread-safe status update: runs the functor on the GUI thread.
            QTimer.singleShot(0, self, lambda: self._status.setText(text))

        def _run():
            try:
                import sys as _sys
                _sys.path.insert(0, str(self._config_path.parent.parent))
                from core.tts import create_tts_player
                create_tts_player(cfg).speak("Voice link test OK.")
                _say(f"{engine.upper()} TEST OK")
            except Exception as exc:
                _say(f"{engine.upper()} FAILED")
                self._status.setToolTip(str(exc)[:400])
                self.write_log_safe(f"TTS test failed ({engine}): {exc}")

        threading.Thread(target=_run, daemon=True).start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        root = self.findChild(QFrame, "SettingsRoot")
        if root is not None and hasattr(root, "_fit_backdrop"):
            root._fit_backdrop()

    def _build_ai_tab(self):
        """AI agent assistant: provider + model dropdowns, custom provider, API keys."""
        from core.ai_providers import PROVIDERS, models_for
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        intro = QLabel("AI AGENT  //  PROVIDER · MODEL · CUSTOM ENDPOINT")
        intro.setStyleSheet('color:#00d4ff;font:800 9pt "Orbitron";padding:2px 2px 5px 2px;')
        lay.addWidget(intro)
        hint = QLabel("Gemini drives the voice session. Other providers answer typed text. Custom = any OpenAI-compatible endpoint.")
        hint.setWordWrap(True)
        hint.setStyleSheet("background:#00131c;border:1px solid #17465a;border-radius:9px;padding:10px;color:#5ab8cc;")
        lay.addWidget(hint)

        prov_box = HudGroupBox("PROVIDER & MODEL")
        pf = QFormLayout(prov_box)
        self.ai_provider = QComboBox()
        for key, meta in PROVIDERS.items():
            self.ai_provider.addItem(str(meta.get("label", key)), key)
        cur_prov = str(self._data.get("ai_provider", "gemini") or "gemini").strip().lower()
        idx = self.ai_provider.findData(cur_prov)
        self.ai_provider.setCurrentIndex(max(0, idx))
        self.ai_provider.currentIndexChanged.connect(self._refresh_ai_fields)
        pf.addRow("Provider", self.ai_provider)
        self.ai_model = QComboBox()
        self.ai_model.setEditable(True)
        saved_model = str(self._data.get("ai_model", "") or "").strip()
        self.ai_model.addItems(models_for(cur_prov))
        if saved_model:
            self.ai_model.setCurrentText(saved_model)
        self.ai_model.setToolTip("Pick a model or type your own (e.g. a newly released ID).")
        pf.addRow("Model", self.ai_model)
        lay.addWidget(prov_box)

        self._ai_key_box = HudGroupBox("PROVIDER API KEY")
        kf = QFormLayout(self._ai_key_box)
        self.openai_api_key = QLineEdit(str(self._data.get("openai_api_key", "")))
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText("sk-… OpenAI key")
        kf.addRow("OpenAI key", self.openai_api_key)
        self.anthropic_api_key = QLineEdit(str(self._data.get("anthropic_api_key", "")))
        self.anthropic_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthropic_api_key.setPlaceholderText("sk-ant-… Anthropic key")
        kf.addRow("Anthropic key", self.anthropic_api_key)
        self.groq_api_key = QLineEdit(str(self._data.get("groq_api_key", "")))
        self.groq_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_api_key.setPlaceholderText("gsk_… Groq key")
        kf.addRow("Groq key", self.groq_api_key)
        info = QLabel("Ollama needs no key — just run Ollama locally. Gemini uses the key from first-time setup.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#5ab8cc;background:transparent;")
        kf.addRow("", info)
        lay.addWidget(self._ai_key_box)

        self._custom_box = HudGroupBox("CUSTOM PROVIDER (OpenAI-compatible)")
        cf = QFormLayout(self._custom_box)
        self.custom_provider_name = QLineEdit(str(self._data.get("custom_provider_name", "")))
        self.custom_provider_name.setPlaceholderText("e.g. My Cloud GPU")
        cf.addRow("Name", self.custom_provider_name)
        self.custom_ai_base_url = QLineEdit(str(self._data.get("custom_ai_base_url", "")))
        self.custom_ai_base_url.setPlaceholderText("https://my-server:8000/v1")
        cf.addRow("Base URL", self.custom_ai_base_url)
        self.custom_ai_api_key = QLineEdit(str(self._data.get("custom_ai_api_key", "")))
        self.custom_ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.custom_ai_api_key.setPlaceholderText("Custom API key (if required)")
        cf.addRow("API key", self.custom_ai_api_key)
        self.custom_ai_model = QLineEdit(str(self._data.get("custom_ai_model", "")))
        self.custom_ai_model.setPlaceholderText("e.g. my-model-7b")
        cf.addRow("Model", self.custom_ai_model)
        lay.addWidget(self._custom_box)

        test = QPushButton("TEST CONNECTION")
        test.setToolTip("Send a tiny probe to the selected provider.")
        test.clicked.connect(self._test_ai_connection)
        lay.addWidget(test)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "AI")
        self._refresh_ai_fields(self.ai_provider.currentIndex())

    def _refresh_ai_fields(self, _index=None):
        """Refresh model list + dim the custom group unless provider = custom."""
        try:
            from core.ai_providers import models_for
            from PyQt6.QtWidgets import QGraphicsOpacityEffect as _OE
            prov = str(self.ai_provider.currentData() or "gemini")
            keep = self.ai_model.currentText().strip()
            self.ai_model.blockSignals(True)
            self.ai_model.clear()
            self.ai_model.addItems(models_for(prov))
            if keep:
                self.ai_model.setCurrentText(keep)
            self.ai_model.blockSignals(False)
            box = getattr(self, "_custom_box", None)
            if box is not None:
                eff = box.graphicsEffect()
                if not isinstance(eff, _OE):
                    eff = _OE(box)
                    box.setGraphicsEffect(eff)
                eff.setOpacity(1.0 if prov == "custom" else 0.45)
        except Exception:
            pass

    def _test_ai_connection(self):
        try:
            from core import ai_providers as _aip
            cfg = self._collect()
            reply = _aip.test_connection(cfg)
            self._status.setText("AI LINK OK")
            self.write_log_safe(f"AI test OK: {str(reply)[:120]}")
        except Exception as exc:
            self._status.setText("AI LINK FAILED")
            self.write_log_safe(f"AI test failed: {exc}")

    def write_log_safe(self, text: str):
        try:
            parent = self.parent()
            if parent is not None and hasattr(parent, "write_log"):
                parent.write_log(text)
        except Exception:
            pass
        try:
            self._status.setToolTip(str(text)[:300])
        except Exception:
            pass

    def _build_plugins_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "PLUGINS  //  EXTEND JARVIS")
        self._plugin_list = QListWidget()
        self._plugin_list.setStyleSheet(
            "QListWidget{background:rgba(0,12,20,130);color:#d8f8ff;border:1px solid #12465b;border-radius:10px;padding:5px;}"
            "QListWidget::item{padding:7px 8px;border-bottom:1px solid rgba(41,135,170,45);}"
            "QListWidget::item:selected{background:rgba(0,103,143,105);}"
        )
        lay.addWidget(self._plugin_list, 1)
        row = QHBoxLayout()
        row.setSpacing(8)
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self._reload_plugins)
        row.addWidget(refresh)
        toggle = QPushButton("ENABLE / DISABLE")
        toggle.setToolTip("Toggle the selected plugin. Takes effect on next voice request.")
        toggle.clicked.connect(self._toggle_plugin)
        row.addWidget(toggle)
        folder = QPushButton("OPEN FOLDER")
        folder.clicked.connect(self._open_plugins_folder)
        row.addWidget(folder)
        lay.addLayout(row)
        self._plugin_status = QLabel("")
        self._plugin_status.setWordWrap(True)
        self._plugin_status.setStyleSheet("color:#5ab8cc;background:transparent;")
        lay.addWidget(self._plugin_status)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "PLUGINS")
        self._reload_plugins()

    def _iter_plugins(self):
        try:
            fn = getattr(self, "get_plugins", None)
            if callable(fn):
                return list(fn() or [])
        except Exception:
            pass
        return []

    def _reload_plugins(self):
        try:
            self._plugin_list.clear()
            plugins = self._iter_plugins()
            if not plugins:
                self._plugin_list.addItem("No plugins found. Drop a plugin folder into plugins/ and press REFRESH.")
            for p in plugins:
                try:
                    state = "ON" if p.get("enabled", True) else "OFF"
                    problem = "" if p.get("valid", True) else f"  ·  BROKEN: {p.get('error', '?')}"
                    item = QListWidgetItem(f"[{state}]  {p.get('name', '?')}  —  {p.get('description', '')[:90]}{problem}")
                    item.setData(Qt.ItemDataRole.UserRole, p.get("name", ""))
                    self._plugin_list.addItem(item)
                except Exception:
                    pass
            self._plugin_status.setText(f"{len(plugins)} plugin(s) discovered.")
        except Exception as exc:
            self._plugin_status.setText(f"Plugin scan failed: {exc}")

    def _toggle_plugin(self):
        item = self._plugin_list.currentItem()
        if item is None:
            self._plugin_status.setText("Select a plugin first.")
            return
        name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not name:
            return
        try:
            cur = {p.get("name"): bool(p.get("enabled", True)) for p in self._iter_plugins()}
            new_state = not cur.get(name, True)
            fn = getattr(self, "set_plugin_enabled", None)
            if callable(fn):
                fn(name, new_state)
                self._plugin_status.setText(f"Plugin '{name}' {'enabled' if new_state else 'disabled'}. Applies to the next request.")
                self._reload_plugins()
            else:
                self._plugin_status.setText("Plugin control is unavailable while JARVIS is offline.")
        except Exception as exc:
            self._plugin_status.setText(f"Toggle failed: {exc}")

    def _open_plugins_folder(self):
        try:
            fn = getattr(self, "open_plugins_folder", None)
            if callable(fn):
                fn()
                return
            import subprocess
            path = str(Path(__file__).resolve().parent / "plugins")
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: S606 - local UI action
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            self._plugin_status.setText(f"Could not open folder: {exc}")

    def _build_diagnostics_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "DIAGNOSTICS  //  HEALTH · CHECKS · LOG")
        self._diag_box = HudGroupBox("SYSTEM CHECKS")
        dv = QVBoxLayout(self._diag_box)
        self._diag_list = QListWidget()
        self._diag_list.setStyleSheet(
            "QListWidget{background:rgba(0,12,20,130);color:#d8f8ff;border:1px solid #12465b;border-radius:10px;padding:5px;}"
            "QListWidget::item{padding:6px 8px;border-bottom:1px solid rgba(41,135,170,45);}"
        )
        dv.addWidget(self._diag_list)
        run = QPushButton("RUN CHECKS")
        run.setToolTip("Verify engine, keys, files and devices without speaking.")
        run.clicked.connect(self._run_diagnostics)
        dv.addWidget(run)
        lay.addWidget(self._diag_box)
        log_box = HudGroupBox("RECENT ACTIVITY")
        lv = QVBoxLayout(log_box)
        self._diag_log = QTextEdit()
        self._diag_log.setReadOnly(True)
        self._diag_log.setMinimumHeight(150)
        self._diag_log.setStyleSheet(
            "QTextEdit{background:rgba(0,12,20,130);color:#9ae8ff;border:1px solid #12465b;border-radius:10px;padding:8px;font:8pt 'Share Tech Mono';}"
        )
        lv.addWidget(self._diag_log)
        copy_log = QPushButton("REFRESH LOG")
        copy_log.clicked.connect(self._refresh_diag_log)
        lv.addWidget(copy_log)
        lay.addWidget(log_box)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "DIAG")
        self._refresh_diag_log()

    def _run_diagnostics(self):
        import platform as _plat
        results = []
        def _ok(name, good, detail=""):
            results.append((name, bool(good), str(detail or "")))
        _ok("Python", True, _plat.python_version())
        try:
            import PyQt6.QtCore as _qc
            _ok("PyQt6", True, _qc.QT_VERSION_STR)
        except Exception as exc:
            _ok("PyQt6", False, exc)
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa
            _ok("WebEngine", True, "embedded browser ready")
        except Exception:
            _ok("WebEngine", False, "pip install PyQt6-WebEngine")
        try:
            from core.tts import create_tts_player
            create_tts_player(self._collect())
            _ok("TTS engine", True, str(self.tts_engine.currentText()))
        except Exception as exc:
            _ok("TTS engine", False, str(exc)[:100])
        cfg = self._collect()
        try:
            _file_cfg = json.loads(self._config_path.read_text(encoding="utf-8"))
        except Exception:
            _file_cfg = {}
        _ok("Gemini key", bool(str(_file_cfg.get("gemini_api_key", "") or "").strip()), "voice session")
        _ok("ElevenLabs key", str(cfg.get("elevenlabs_api_key", "") or "").startswith("sk_"), "cloud voice")
        _ok("Fish key", bool(str(cfg.get("fish_audio_api_key", "") or "").strip()), "cloud voice")
        try:
            mem = Path(__file__).resolve().parent / "memory" / "long_term.json"
            _ok("Memory file", mem.is_file(), f"{mem.stat().st_size} bytes" if mem.is_file() else "missing")
        except Exception as exc:
            _ok("Memory file", False, exc)
        try:
            import shutil as _sh
            free_gb = _sh.disk_usage(str(Path.home())).free / (1024 ** 3)
            _ok("Disk free", free_gb > 1.0, f"{free_gb:.1f} GB")
        except Exception as exc:
            _ok("Disk free", False, exc)
        try:
            self._diag_list.clear()
            for name, good, detail in results:
                mark = "OK " if good else "FAIL"
                self._diag_list.addItem(f"[{mark}]  {name}" + (f"  —  {detail}" if detail else ""))
            self._status.setText("CHECKS DONE")
        except Exception as exc:
            self._status.setText(f"CHECKS ERROR: {exc}")

    def _refresh_diag_log(self):
        lines = []
        try:
            fn = getattr(self, "get_activity_log", None)
            if callable(fn):
                lines = list(fn(60) or [])
        except Exception:
            pass
        try:
            self._diag_log.setPlainText("\n".join(lines) if lines else "No activity yet — open the app and talk to JARVIS first.")
        except Exception:
            pass

    def _build_layout_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(9)

        intro = QLabel("ADVANCED LAYOUT EDITOR — move, resize, recolor, hide, and create custom UI elements without expanding the main Arc Reactor.")
        intro.setWordWrap(True)
        intro.setStyleSheet("background:#00131c;border:1px solid #17465a;border-radius:9px;padding:10px;color:#5ab8cc;")
        lay.addWidget(intro)

        top = QHBoxLayout()
        top.addWidget(QLabel("Element"))
        self.layout_element = QComboBox()
        top.addWidget(self.layout_element, 1)
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(self._load_layout_values)
        top.addWidget(refresh)
        open_editor = QPushButton("OPEN FULL EDITOR")
        open_editor.clicked.connect(self._open_external_layout_editor)
        top.addWidget(open_editor)
        lay.addLayout(top)

        props = HudGroupBox("SELECTED ELEMENT")
        pf = QFormLayout(props)
        self.layout_x = QSpinBox(); self.layout_x.setRange(-5000, 5000); pf.addRow("X", self.layout_x)
        self.layout_y = QSpinBox(); self.layout_y.setRange(-5000, 5000); pf.addRow("Y", self.layout_y)
        self.layout_w = QSpinBox(); self.layout_w.setRange(20, 5000); pf.addRow("Width", self.layout_w)
        self.layout_h = QSpinBox(); self.layout_h.setRange(20, 5000); pf.addRow("Height", self.layout_h)
        self.layout_opacity = QSlider(Qt.Orientation.Horizontal); self.layout_opacity.setRange(0, 100); pf.addRow("Opacity", self.layout_opacity)
        self.layout_visible = QCheckBox("Visible"); pf.addRow("", self.layout_visible)
        apply_btn = QPushButton("APPLY TO LAYOUT")
        apply_btn.clicked.connect(self._apply_layout_selection)
        pf.addRow("", apply_btn)
        lay.addWidget(props)

        add = HudGroupBox("ADD ELEMENT")
        af = QFormLayout(add)
        self.new_kind = QComboBox(); self.new_kind.addItems(["Text", "Button", "Panel", "Separator", "Window", "Monitor", "WebView"]); af.addRow("Type", self.new_kind)
        self.new_name = QLineEdit(); self.new_name.setPlaceholderText("e.g. System Status"); af.addRow("Name", self.new_name)
        self.new_text = QLineEdit(); self.new_text.setPlaceholderText("Display text"); af.addRow("Text", self.new_text)
        add_btn = QPushButton("ADD ELEMENT")
        add_btn.clicked.connect(self._add_layout_element)
        af.addRow("", add_btn)
        lay.addWidget(add)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "LAYOUT")
        self.layout_element.currentTextChanged.connect(self._on_layout_selection_changed)

    def _build_web_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        intro = QLabel("WEB SURFACE  //  WEBVIEW + TASK QUEUE")
        intro.setStyleSheet('color:#00d4ff;font:800 9pt "Orbitron";padding:2px 2px 5px 2px;')
        lay.addWidget(intro)
        box = HudGroupBox("WEBVIEW")
        form = QFormLayout(box)
        self.web_homepage = QLineEdit(str(self._data.get("web_homepage", DEFAULTS["web_homepage"])))
        self.web_homepage.setPlaceholderText("https://")
        form.addRow("Homepage", self.web_homepage)
        self._web_ontop = QCheckBox("Keep HUD windows always on top")
        self._web_ontop.setChecked(bool(self._data.get("panel_always_on_top", True)))
        form.addRow("", self._web_ontop)
        self._web_engine = QCheckBox("Use the internal WebView engine for search and video")
        self._web_engine.setChecked(bool(self._data.get("features", {}).get("webview_engine", True)))
        form.addRow("", self._web_engine)
        self._web_music = QCheckBox("Play music inside the internal WebView")
        self._web_music.setChecked(bool(self._data.get("features", {}).get("webview_music", True)))
        form.addRow("", self._web_music)
        lay.addWidget(box)
        tasks = HudGroupBox("WEB TASK DEFAULTS")
        tv = QVBoxLayout(tasks)
        self._web_js = QCheckBox("Allow JavaScript in Webview")
        self._web_js.setChecked(True)
        self._web_external = QCheckBox("Open unknown schemes in the system browser")
        self._web_external.setChecked(True)
        tv.addWidget(self._web_js); tv.addWidget(self._web_external)
        hint = QLabel("Web Task queues search, news, research, price, and browse jobs. Browse opens a dedicated Webview window.")
        hint.setWordWrap(True); hint.setStyleSheet("color:#5ab8cc;background:transparent;")
        tv.addWidget(hint)
        lay.addWidget(tasks)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "WEB")

    def _build_memory_settings_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        intro = QLabel("MEMORY CORE  //  LOCAL LONG-TERM STORE")
        intro.setStyleSheet('color:#00d4ff;font:800 9pt "Orbitron";padding:2px 2px 5px 2px;')
        lay.addWidget(intro)
        box = HudGroupBox("STORE")
        v = QVBoxLayout(box)
        self._memory_autosave = QCheckBox("Auto-save remembered facts to memory/long_term.json")
        self._memory_autosave.setChecked(bool(self._data.get("memory_autosave", True)))
        v.addWidget(self._memory_autosave)
        self._memory_index = QCheckBox("Keep a prompt index so JARVIS can recall facts that are not in the core prompt")
        self._memory_index.setChecked(True)
        v.addWidget(self._memory_index)
        info = QLabel("The Memory window lists every stored fact, lets you add keys, search, and forget entries. It is a real HUD window — not a popup on the tiny reactor.")
        info.setWordWrap(True); info.setStyleSheet("color:#5ab8cc;background:transparent;")
        v.addWidget(info)
        lay.addWidget(box)
        mon = HudGroupBox("WORLD MONITOR")
        mv = QVBoxLayout(mon)
        self.world_refresh = self._slider_row(mv, "Headline refresh", int(self._data.get("world_monitor_refresh", 60)), 15, 600, " s")
        note = QLabel("World Monitor shows global clocks, CPU/RAM/GPU telemetry, a grid sweep, and live world headlines.")
        note.setWordWrap(True); note.setStyleSheet("color:#5ab8cc;background:transparent;")
        mv.addWidget(note)
        lay.addWidget(mon)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "MEMORY")

    def _build_3d_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        status = QLabel("3D PREVIEW — load OBJ/STL/PLY and use the existing JARVIS 3D renderer.")
        status.setWordWrap(True); status.setStyleSheet("color:#5ab8cc;background:transparent;")
        lay.addWidget(status)
        self._3d_host = QFrame(); self._3d_host.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(0,18,28,235),stop:0.5 rgba(0,8,14,245),stop:1 rgba(0,27,38,220));border:1px solid rgba(81,217,255,120);border-radius:14px;")
        hv = QVBoxLayout(self._3d_host)
        self._3d_status = QLabel("No 3D model loaded")
        self._3d_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._3d_status.setMinimumHeight(300)
        hv.addWidget(self._3d_status, 1)
        lay.addWidget(self._3d_host, 1)
        row = QHBoxLayout()
        load_btn = QPushButton("OPEN 3D MODEL")
        load_btn.clicked.connect(self._open_3d_model)
        row.addWidget(load_btn)
        reset = QPushButton("RESET VIEW")
        reset.clicked.connect(self._reset_3d_view)
        row.addWidget(reset)
        wire = QPushButton("WIREFRAME")
        wire.clicked.connect(self._toggle_3d_wireframe)
        row.addWidget(wire)
        lay.addLayout(row)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "3D")

    def _scan_camera_indexes(self) -> list[int]:
        """Probe short-lived opens so the picker shows only live sources, and
        always expose 0/1 (built-in webcam / OBS virtual camera convention)."""
        idxs: list[int] = []
        try:
            from vision.camera import probe_camera
            for i in range(4):
                try:
                    if probe_camera(i):
                        idxs.append(i)
                except Exception:
                    pass
        except Exception:
            pass
        for fallback in (0, 1):
            if fallback not in idxs:
                idxs.append(fallback)
        return idxs

    def _build_video_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        self._tab_intro(lay, "VIDEO  //  CAMERA SOURCE · LOCAL PLAYBACK")

        camera_box = HudGroupBox("CAMERA SOURCE")
        cam_form = QFormLayout(camera_box)
        cam_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.camera_source = QComboBox()
        self.camera_source.setMinimumWidth(250)
        current = str((self._data or {}).get("camera_index", "auto"))
        found = self._scan_camera_indexes()
        source_labels = [("auto", "AUTO DETECT")]
        for idx in found:
            tag = "OBS VIRTUAL CAMERA" if idx == 1 else "WEBCAM" if idx == 0 else "CAMERA"
            if idx != 0 and idx != 1:
                tag = f"DEVICE {idx}"
            source_labels.append((str(idx), f"{tag} (INDEX {idx})"))
        for value, label in source_labels:
            self.camera_source.addItem(label, value)
        set_i = self.camera_source.findData(current)
        if set_i >= 0:
            self.camera_source.setCurrentIndex(set_i)
        elif str(current).lstrip("-").isdigit():
            self.camera_source.addItem(f"CAMERA (INDEX {current})", str(current))
            self.camera_source.setCurrentIndex(self.camera_source.count() - 1)
        cam_form.addRow("Video source", self.camera_source)
        src_hint = QLabel("Choose the live camera for vision and the webcam button. "
                          "Index 0 is the built-in webcam; authors using OBS should "
                          "pick the OBS Virtual Camera entry. Applies after a re-open.")
        src_hint.setWordWrap(True)
        src_hint.setStyleSheet("color:#5ab8cc;background:transparent;padding:2px;")
        cam_form.addRow(src_hint)
        lay.addWidget(camera_box)
        self._video_host = QFrame(); self._video_host.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #02080d,stop:0.5 #00050a,stop:1 #03131b);border:1px solid rgba(81,217,255,120);border-radius:14px;")
        vv = QVBoxLayout(self._video_host)
        self._video_widget = None
        self._video_status = QLabel("No video loaded")
        self._video_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_status.setMinimumHeight(300)
        vv.addWidget(self._video_status, 1)
        lay.addWidget(self._video_host, 1)
        row = QHBoxLayout()
        open_btn = QPushButton("OPEN VIDEO")
        open_btn.clicked.connect(self._open_video)
        row.addWidget(open_btn)
        self.video_play = QPushButton("PLAY / PAUSE")
        self.video_play.clicked.connect(self._toggle_video)
        row.addWidget(self.video_play)
        back = QPushButton("◀ 5s")
        back.clicked.connect(lambda: self._seek_video(-5000))
        row.addWidget(back)
        fwd = QPushButton("5s ▶")
        fwd.clicked.connect(lambda: self._seek_video(5000))
        row.addWidget(fwd)
        stop = QPushButton("STOP")
        stop.clicked.connect(self._stop_video)
        row.addWidget(stop)
        lay.addLayout(row)
        self.video_seek = QSlider(Qt.Orientation.Horizontal)
        self.video_seek.setRange(0,0); self.video_seek.setTracking(True)
        self.video_seek.sliderMoved.connect(lambda v: self._set_video_position(v))
        lay.addWidget(self.video_seek)
        self._video_time = QLabel("00:00 / 00:00")
        self._video_time.setStyleSheet("color:#5ab8cc;")
        lay.addWidget(self._video_time)
        self._video_file = QLabel("File: —")
        self._video_file.setStyleSheet("color:#5ab8cc;")
        lay.addWidget(self._video_file)
        self.tabs.addTab(scroll, "VIDEO")

    def _build_image_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        self._image_preview = QLabel("No image loaded")
        self._image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_preview.setMinimumHeight(430)
        self._image_preview.setStyleSheet('background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(1,13,22,235),stop:1 rgba(2,24,34,210));border:1px solid rgba(81,217,255,110);border-radius:14px;color:#538e9e;font:700 10pt "Exo 2";')
        lay.addWidget(self._image_preview, 1)
        row = QHBoxLayout()
        open_btn = QPushButton("OPEN IMAGE")
        open_btn.clicked.connect(self._open_image)
        row.addWidget(open_btn)
        clear = QPushButton("CLEAR")
        clear.clicked.connect(lambda: self._image_preview.clear())
        row.addWidget(clear)
        lay.addLayout(row)
        self.tabs.addTab(scroll, "IMAGE")

    def _build_system_tab(self):
        page, lay, scroll = self._scroll_tab()
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(10)
        self._tab_intro(lay, "SYSTEM  //  INTERFACE · WINDOWS · SOUND")
        box = HudGroupBox("FEATURES")
        v = QVBoxLayout(box)
        feats = self._data.get("features", {}) or {}
        self._feature_checks = {}
        for key, label in [
            ("audio_reactive", "Audio-reactive Arc Reactor"),
            ("smooth_animations", "Smooth animations"),
            ("chat_history", "Keep chat history"),
            ("compact_mode", "Start in compact mode"),
            ("drag_reactor", "Drag the Arc Reactor"),
            ("remember_position", "Remember window position"),
            ("advanced_layout", "Enable advanced layout editor"),
            ("preview_tabs", "Enable preview tabs"),
            ("webview", "Enable Webview windows"),
            ("web_task", "Enable Web Task queue"),
            ("world_monitor", "Enable World Monitor"),
            ("floating_windows", "Allow multiple independent HUD windows"),
            ("draggable_panels", "Drag windows from the title bar"),
            ("enable_sfx", "Futuristic UI sound effects"),
        ]:
            v.addWidget(self._flag_checkbox(self._feature_checks, key, label, True))
        lay.addWidget(box)
        info = QLabel("All options are saved to config/api_keys.json. Preview tabs do not create or reveal the old large HUD.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#5ab8cc;background:transparent;padding:5px;")
        lay.addWidget(info)
        lay.addStretch(1)
        self.tabs.addTab(scroll, "SYSTEM")

    def _slider_row(self, parent_layout, label, value, lo, hi, suffix):
        row = QHBoxLayout()
        lab = QLabel(label); lab.setMinimumWidth(185)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(max(lo, min(hi, int(value))))
        slider.setTracking(True)
        slider.setSingleStep(1)
        slider.setPageStep(max(1, (hi - lo) // 10))
        val = QLabel(f"{slider.value()}{suffix}")
        val.setMinimumWidth(78)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setStyleSheet('color:#8cecff;font:800 8pt "Orbitron";background:rgba(0,28,40,210);border:1px solid rgba(81,217,255,120);border-radius:7px;padding:4px 7px;')
        slider.valueChanged.connect(lambda v, out=val, s=suffix: out.setText(f"{int(v)}{s}"))
        row.addWidget(lab)
        row.addWidget(slider, 1)
        row.addWidget(val)
        parent_layout.addLayout(row)
        return slider

    def _set_color(self, color: str):
        self._color = color
        self.color_btn.setText(color)

    def pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Choose JARVIS accent color")
        if c.isValid():
            self._set_color(c.name())

    # ------------------------------------------------------------------ layout
    def _load_layout_values(self):
        self.layout_element.blockSignals(True)
        self.layout_element.clear()
        self._layout_rows = {}
        parent = self.parent()
        items = []
        if parent is not None:
            for name, w in getattr(parent, "_system_layout_widgets", {}).items():
                if w is None:
                    continue
                g = w.geometry()
                items.append((name, {"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height(), "opacity": 100, "visible": w.isVisible()}))
            for name, w in getattr(parent, "_layout_widgets", {}).items():
                if w is None:
                    continue
                g = w.geometry()
                items.append((name, {"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height(), "opacity": 100, "visible": w.isVisible()}))
            for name, elem in getattr(parent, "_layout_elements", {}).items():
                self._layout_rows[name] = dict(elem)
                items.append((name, dict(elem)))
        seen = set()
        for name, elem in items:
            if name in seen:
                continue
            seen.add(name)
            self.layout_element.addItem(name)
            self._layout_rows[name] = dict(self._layout_rows.get(name, {}))
            self._layout_rows[name].update(elem)
        if self.layout_element.count():
            self.layout_element.setCurrentIndex(0)
        self.layout_element.blockSignals(False)
        self._on_layout_selection_changed(self.layout_element.currentText())

    def _on_layout_selection_changed(self, name):
        if not name or name not in self._layout_rows:
            return
        self._layout_selected_name = name
        e = self._layout_rows[name]
        self.layout_x.setValue(int(e.get("x", 50)))
        self.layout_y.setValue(int(e.get("y", 50)))
        self.layout_w.setValue(int(e.get("w", 180)))
        self.layout_h.setValue(int(e.get("h", 50)))
        self.layout_opacity.setValue(int(e.get("opacity", 100)))
        self.layout_visible.setChecked(bool(e.get("visible", True)))

    def _apply_layout_selection(self):
        name = self._layout_selected_name
        parent = self.parent()
        if not name or parent is None:
            return
        elem = self._layout_rows.setdefault(name, {})
        elem.update({"name": name, "x": self.layout_x.value(), "y": self.layout_y.value(), "w": self.layout_w.value(), "h": self.layout_h.value(), "opacity": self.layout_opacity.value(), "visible": self.layout_visible.isChecked()})
        widget = getattr(parent, "_system_layout_widgets", {}).get(name) or getattr(parent, "_layout_widgets", {}).get(name)
        if widget is not None:
            widget.setGeometry(self.layout_x.value(), self.layout_y.value(), self.layout_w.value(), self.layout_h.value())
            widget.setVisible(self.layout_visible.isChecked())
        if hasattr(parent, "_layout_elements"):
            parent._layout_elements[name] = dict(elem)
            if hasattr(parent, "_apply_layout_elements"):
                parent._apply_layout_elements()
            if hasattr(parent, "_save_layout_elements"):
                parent._save_layout_elements()
        self._status.setText("LAYOUT APPLIED")

    def _add_layout_element(self):
        parent = self.parent()
        if parent is None or not hasattr(parent, "_layout_elements"):
            return
        name = self.new_name.text().strip() or f"{self.new_kind.currentText()} {len(parent._layout_elements)+1}"
        text = self.new_text.text().strip() or name
        idx = 1
        base = name
        while name in parent._layout_elements:
            idx += 1
            name = f"{base} {idx}"
        parent._layout_elements[name] = {"name": name, "kind": self.new_kind.currentText(), "x": 70, "y": 70, "w": 240, "h": 50, "opacity": 100, "visible": True, "text": text, "color": self._color}
        if hasattr(parent, "_apply_layout_elements"):
            parent._apply_layout_elements()
        if hasattr(parent, "_save_layout_elements"):
            parent._save_layout_elements()
        self.new_name.clear(); self.new_text.clear()
        self._load_layout_values()
        self.layout_element.setCurrentText(name)
        self._status.setText("ELEMENT ADDED")

    def _open_external_layout_editor(self):
        parent = self.parent()
        try:
            if parent is not None and hasattr(parent, "_open_layout_editor"):
                parent._open_layout_editor()
                self._status.setText("ADVANCED EDITOR OPEN")
        except Exception as exc:
            self._status.setText(f"LAYOUT ERROR: {exc}")

    # ---------------------------------------------------------------- preview tabs
    def _open_3d_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open 3D model", "", "3D Models (*.obj *.stl *.ply *.off *.glb *.gltf);;All Files (*.*)")
        if not path:
            return
        try:
            parent = self.parent()
            viewer_cls = None
            if parent is not None and parent.__class__.__module__:
                from ui import Model3DView as viewer_cls  # late import avoids circular import at module load
            if viewer_cls is None:
                raise RuntimeError("3D renderer unavailable")
            if getattr(self, "_model_view", None) is None:
                self._model_view = viewer_cls(self._3d_host)
                old = self._3d_status
                old.hide()
                self._3d_host.layout().addWidget(self._model_view, 1)
            self._model_view.load_model(path)
            self._3d_file = path
            self._3d_status.hide()
            self._status.setText("3D MODEL LOADED")
        except Exception as exc:
            self._3d_status.setText(f"3D preview error: {exc}")
            self._3d_status.show()

    def _reset_3d_view(self):
        viewer = getattr(self, "_model_view", None)
        if viewer is not None and hasattr(viewer, "reset_view"):
            viewer.reset_view()

    def _toggle_3d_wireframe(self):
        viewer = getattr(self, "_model_view", None)
        if viewer is not None and hasattr(viewer, "toggle_wireframe"):
            viewer.toggle_wireframe()

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open video", "", "Video Files (*.mp4 *.avi *.mkv *.mov *.webm *.wmv);;All Files (*.*)")
        if not path:
            return
        self._video_file.setText(f"File: {Path(path).name}")
        try:
            from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PyQt6.QtMultimediaWidgets import QVideoWidget
            if self._video_widget is None:
                self._video_widget = QVideoWidget(self._video_host)
                self._video_host.layout().insertWidget(0, self._video_widget, 1)
                self._video_player = QMediaPlayer(self)
                self._audio_output = QAudioOutput(self)
                self._video_player.setAudioOutput(self._audio_output)
                self._video_player.setVideoOutput(self._video_widget)
                self._video_player.positionChanged.connect(self._settings_video_position_changed)
                self._video_player.durationChanged.connect(lambda d: self.video_seek.setRange(0, int(d)))
            self._video_player.setSource(__import__('PyQt6.QtCore', fromlist=['QUrl']).QUrl.fromLocalFile(path))
            self._video_status.hide()
            self._video_player.play()
            self._status.setText("VIDEO PLAYING")
        except Exception as exc:
            self._video_status.setText(f"Video preview unavailable: {exc}")
            self._video_status.show()

    def _settings_video_position_changed(self, pos):
        if hasattr(self, "video_seek") and not self.video_seek.isSliderDown():
            self.video_seek.setValue(int(pos))
        if hasattr(self, "_video_time"):
            dur = self._video_player.duration() if getattr(self, "_video_player", None) is not None else 0
            self._video_time.setText(f"{self._fmt_ms(pos)} / {self._fmt_ms(dur)}")

    @staticmethod
    def _fmt_ms(ms):
        s=max(0,int(ms)//1000); m,sec=divmod(s,60); h,m=divmod(m,60)
        return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

    def _set_video_position(self, value):
        if getattr(self, "_video_player", None) is not None:
            self._video_player.setPosition(int(value))

    def _seek_video(self, delta):
        if getattr(self, "_video_player", None) is not None:
            self._video_player.setPosition(max(0, min(self._video_player.duration(), self._video_player.position()+int(delta))))

    def _toggle_video(self):
        p = getattr(self, "_video_player", None)
        if p is None:
            return
        from PyQt6.QtMultimedia import QMediaPlayer
        p.setPosition(p.position())
        p.play() if p.playbackState() != QMediaPlayer.PlaybackState.PlayingState else p.pause()

    def _stop_video(self):
        p = getattr(self, "_video_player", None)
        if p is not None:
            p.stop()

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All Files (*.*)")
        if not path:
            return
        from PyQt6.QtGui import QPixmap
        px = QPixmap(path)
        if px.isNull():
            self._image_preview.setText("Unable to load image")
            return
        self._image_path = path
        self._image_preview.setPixmap(px.scaled(self._image_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self._status.setText("IMAGE LOADED")

    def _refresh_voice_fields(self, engine: str):
        """Dim the provider group that is NOT active so only relevant fields stand out."""
        eng = str(engine or "").strip().lower()
        try:
            for box, active in (
                (getattr(self, "_eleven_box", None), eng == "elevenlabs"),
                (getattr(self, "_fish_box", None), eng in {"fish_audio", "fish", "fishaudio"}),
            ):
                if box is None:
                    continue
                box.setEnabled(True)
                # Active group: full opacity; inactive: visually dimmed but still editable.
                eff = box.graphicsEffect()
                from PyQt6.QtWidgets import QGraphicsOpacityEffect as _OE
                if not isinstance(eff, _OE):
                    eff = _OE(box)
                    box.setGraphicsEffect(eff)
                eff.setOpacity(1.0 if active else 0.45)
        except Exception:
            pass

    # ---------------------------------------------------------------- settings
    def _collect_camera_index(self) -> object:
        value = None
        try:
            value = self.camera_source.currentData()
        except Exception:
            value = None
        if value is None:
            return getattr(self, "_data", {}).get("camera_index", "auto")
        return value

    def _collect(self):
        features = {k: v.isChecked() for k, v in getattr(self, "_feature_checks", {}).items()}
        features["drag_reactor"] = self._drag.isChecked()
        features["remember_position"] = self._remember.isChecked()
        features["compact_mode"] = self._compact.isChecked()
        features["autostart"] = self._autostart.isChecked()
        features["hide_taskbar_button"] = self._taskbar.isChecked()
        features["hide_taskbar"] = False  # legacy key: never hide the Windows taskbar itself
        features["webview_engine"] = self._web_engine.isChecked()
        features["webview_music"] = self._web_music.isChecked()
        features["webview_js"] = self._web_js.isChecked()
        features["webview_external"] = self._web_external.isChecked()
        features.update({k: v.isChecked() for k, v in self._voice_checks.items()})
        features.update({k: v.isChecked() for k, v in getattr(self, "_perm_checks", {}).items()})
        return dict(
            ui_font=self.font.currentText(),
            ui_color=self._color,
            ui_opacity=self.ui_opacity.value(),
            compact_size=self.reactor_size.value(),
            reactor_opacity=self.reactor_opacity.value(),
            reactor_stroke_opacity=self.reactor_stroke_opacity.value(),
            reactor_animation_speed=self.anim_speed.value() / 100.0,
            equalizer_sensitivity=self.eq_sens.value() / 100.0,
            voice_speed=self.voice_speed.value() / 100.0,
            voice_pitch=self.voice_pitch.value() / 10.0,
            voice_volume=self.voice_volume.value() / 100.0,
            voice_mode=self.voice_mode.currentText(),
            tts_engine=self.tts_engine.currentText(),
            tts_voice=self.tts_voice.text().strip() or DEFAULTS["tts_voice"],
            voice_name=self.live_voice.currentText(),
            fish_audio_api_key=self.fish_api_key.text().strip(),
            fish_audio_model_id=self.fish_model_id.text().strip() or DEFAULTS["fish_audio_model_id"],
            fish_audio_voice_id=self.fish_voice_id.text().strip(),
            fish_audio_endpoint=self.fish_endpoint.text().strip() or DEFAULTS["fish_audio_endpoint"],
            fish_audio_format=self.fish_format.currentText(),
            fish_audio_latency=self.fish_latency.currentText(),
            elevenlabs_api_key=self.elevenlabs_api_key.text().strip(),
            elevenlabs_voice_id=self.elevenlabs_voice_id.text().strip() or DEFAULTS["elevenlabs_voice_id"],
            elevenlabs_model_id=self.elevenlabs_model_id.currentText(),
            assistant_name=self.assistant_name.text().strip() or "JARVIS",
            user_name=self.user_name.text().strip(),
            camera_index=self._collect_camera_index(),
            ai_provider=str(self.ai_provider.currentData() or "gemini"),
            ai_model=self.ai_model.currentText().strip(),
            openai_api_key=self.openai_api_key.text().strip(),
            anthropic_api_key=self.anthropic_api_key.text().strip(),
            groq_api_key=self.groq_api_key.text().strip(),
            custom_provider_name=self.custom_provider_name.text().strip(),
            custom_ai_base_url=self.custom_ai_base_url.text().strip().rstrip("/"),
            custom_ai_api_key=self.custom_ai_api_key.text().strip(),
            custom_ai_model=self.custom_ai_model.text().strip(),
            web_homepage=self.web_homepage.text().strip() or DEFAULTS["web_homepage"],
            world_monitor_refresh=self.world_refresh.value(),
            memory_autosave=self._memory_autosave.isChecked(),
            panel_always_on_top=self._web_ontop.isChecked(),
            features=features,
        )

    def reset_defaults(self):
        self.font.setCurrentText(DEFAULTS["ui_font"])
        self._set_color(DEFAULTS["ui_color"])
        self.ui_opacity.setValue(DEFAULTS["ui_opacity"])
        self.reactor_size.setValue(DEFAULTS["compact_size"])
        self.reactor_opacity.setValue(DEFAULTS["reactor_opacity"])
        self.reactor_stroke_opacity.setValue(DEFAULTS["reactor_stroke_opacity"])
        self.anim_speed.setValue(100)
        self.eq_sens.setValue(100)
        self.voice_speed.setValue(100)
        self.voice_pitch.setValue(0)
        self.voice_volume.setValue(100)
        self.voice_mode.setCurrentText(DEFAULTS["voice_mode"])
        self.tts_engine.setCurrentText(DEFAULTS["tts_engine"])
        self.tts_voice.setText(DEFAULTS["tts_voice"])
        self.live_voice.setCurrentText(DEFAULTS["voice_name"])
        self.fish_api_key.clear()
        self.fish_model_id.setText(DEFAULTS["fish_audio_model_id"])
        self.fish_voice_id.clear()
        self.fish_endpoint.setText(DEFAULTS["fish_audio_endpoint"])
        self.fish_format.setCurrentText(DEFAULTS["fish_audio_format"])
        self.fish_latency.setCurrentText(DEFAULTS["fish_audio_latency"])
        self.elevenlabs_api_key.clear()
        self.elevenlabs_voice_id.setText(DEFAULTS["elevenlabs_voice_id"])
        self.elevenlabs_model_id.setCurrentText(DEFAULTS["elevenlabs_model_id"])
        self.assistant_name.setText("JARVIS")
        self.user_name.clear()
        self.ai_provider.setCurrentIndex(max(0, self.ai_provider.findData("gemini")))
        self.ai_model.setCurrentText("")
        self.openai_api_key.clear()
        self.anthropic_api_key.clear()
        self.groq_api_key.clear()
        self.custom_provider_name.clear()
        self.custom_ai_base_url.clear()
        self.custom_ai_api_key.clear()
        self.custom_ai_model.clear()
        if hasattr(self, "web_homepage"):
            self.web_homepage.setText(DEFAULTS["web_homepage"])
        if hasattr(self, "world_refresh"):
            self.world_refresh.setValue(DEFAULTS["world_monitor_refresh"])
        if hasattr(self, "_memory_autosave"):
            self._memory_autosave.setChecked(True)
        if hasattr(self, "_web_ontop"):
            self._web_ontop.setChecked(True)
        if hasattr(self, "_web_engine"):
            self._web_engine.setChecked(True)
        if hasattr(self, "_web_music"):
            self._web_music.setChecked(True)
        self._compact.setChecked(True)
        self._drag.setChecked(True)
        self._remember.setChecked(True)
        self._autostart.setChecked(False)
        self._taskbar.setChecked(False)
        for key, cb in self._feature_checks.items():
            cb.setChecked(bool(DEFAULTS["features"].get(key, True)))
        for key, cb in self._voice_checks.items():
            cb.setChecked(key not in {"push_to_talk", "always_on"})
        for key, cb in getattr(self, "_perm_checks", {}).items():
            cb.setChecked(bool(DEFAULTS["features"].get(key, True)))
        self._status.setText("DEFAULTS READY — SAVE TO APPLY")

    def save_settings(self):
        try:
            self._data = save(self._config_path, **self._collect())
            self.setWindowTitle("J.A.R.V.I.S Settings — SAVED")
            self._status.setText("SAVED")
            self.settings_saved.emit(dict(self._data))
            parent = self.parent()
            if parent is not None and hasattr(parent, "_apply_full_settings"):
                parent._apply_full_settings(dict(self._data))
                if hasattr(parent, '_check_autostart') and hasattr(parent, '_toggle_autostart'):
                    desired = bool(self._autostart.isChecked())
                    if parent._check_autostart() != desired:
                        parent._toggle_autostart()
            return self._data
        except Exception as exc:
            self._status.setText(f"SAVE ERROR: {exc}")
            return None

    def _autosave_quiet(self):
        """Auto-save after a slider release (resize/opacity tweaks apply live)."""
        try:
            data = self.save_settings()
            if data is not None:
                self._status.setText("AUTO-SAVED")
        except Exception:
            pass

    def _header_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _header_move(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def _header_release(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()

    def closeEvent(self, event):
        try:
            self._stop_video()
        except Exception:
            pass
        self.hide()
        event.ignore()


def launch_settings(parent=None):
    created = QApplication.instance() is None
    app = QApplication.instance() or QApplication(sys.argv)
    win = SettingsWindow(parent=parent)
    win.show(); win.raise_(); win.activateWindow()
    return app.exec() if created else 0


if __name__ == "__main__":
    raise SystemExit(launch_settings())
