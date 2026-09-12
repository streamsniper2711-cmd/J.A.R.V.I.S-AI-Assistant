"""J.A.R.V.I.S centralized design system — Refined Stark HUD.

A precise, restrained holographic language: deep vacuum-black surfaces, a single
arc-reactor ice-cyan as the working color, and a sparing Stark repulsor-gold as
the one signature accent reserved for the live/active state. Strokes are thin and
consistent; glow is used as punctuation, never as wallpaper. Shared by every panel.

Design rules encoded here so the whole UI stays coherent:
  * One primary (CYAN), one signature accent (GOLD), a cold neutral ramp, three
    status colors. Nothing else earns a slot.
  * Three radii only (LG / MD / SM). Borders come in three weights (LINE / SOFT / FAINT).
  * Type: Orbitron for display/headings, Rajdhani for UI/body, Share Tech Mono for logs.
"""
from __future__ import annotations

# ── Surfaces ────────────────────────────────────────────────────────────────
# A vacuum-black base with a faint blue bias, then translucent panes stacked on
# top. Alphas are tuned so panels read as layered glass, not flat fills.
BG          = "#02060c"
BG_DEEP     = "#01040a"
PANEL       = "rgba(4, 20, 33, 240)"
PANEL_SOFT  = "rgba(2, 14, 24, 92)"
CARD        = "rgba(3, 16, 27, 168)"
CARD_HI     = "rgba(6, 26, 41, 190)"
HEADER      = "rgba(5, 24, 37, 150)"

# ── Strokes ─────────────────────────────────────────────────────────────────
# Three weights only. LINE = interactive edge, SOFT = grouping, FAINT = hairline.
BORDER       = "rgba(88, 214, 245, 120)"
BORDER_SOFT  = "rgba(60, 156, 190, 70)"
BORDER_FAINT = "rgba(52, 128, 158, 46)"

# ── Text ramp ───────────────────────────────────────────────────────────────
TEXT        = "#daf5ff"
TEXT_BRIGHT = "#f0fdff"
TEXT_MID    = "#a6e9ff"
TEXT_DIM    = "#6ba7bb"
TEXT_FAINT  = "#547f92"

# ── Color ───────────────────────────────────────────────────────────────────
# Primary is the arc-reactor cyan. GOLD is the single signature accent, reserved
# for the "live / armed / active" state so it never turns into noise.
ACCENT      = "#56d6f5"
ACCENT_BRIGHT = "#8ceaff"
ACCENT_DEEP = "#0a86b8"
ACCENT_INK  = "#063348"
GOLD        = "#f4b24a"
GOLD_DEEP   = "#b87d1e"

# Status
GREEN       = "#5df0b6"
AMBER       = "#ffc773"
RED         = "#ff6f8b"

# ── Geometry ────────────────────────────────────────────────────────────────
RADIUS_LG   = 12
RADIUS_MD   = 9
RADIUS_SM   = 6

# ── Type ────────────────────────────────────────────────────────────────────
FONT_UI    = "'Rajdhani'"
FONT_HEAD  = "'Orbitron'"
FONT_LOG   = "'Share Tech Mono'"
FONT_NUM   = "'Orbitron'"
FONT_SMALL = "'Exo 2'"
FONT_MONO  = "'Share Tech Mono'"
FONT_DISP  = "'Orbitron'"


def button_css(min_height: int = 34) -> str:
    """Quiet default control: hairline edge, cyan only on interaction."""
    return (
        "QPushButton {"
        f" color:{TEXT_MID}; background:rgba(5,22,34,120);"
        f" border:1px solid {BORDER_FAINT}; border-radius:{RADIUS_SM}px;"
        f" font:700 8pt {FONT_SMALL}; letter-spacing:1px;"
        f" min-height:{min_height}px; padding:6px 13px; }}"
        "QPushButton:hover {"
        f" color:{TEXT_BRIGHT}; border-color:{ACCENT}; background:rgba(10,134,184,64); }}"
        "QPushButton:pressed { background:rgba(9,110,152,150); }"
        "QPushButton:disabled {"
        " color:#37606f; border-color:rgba(52,128,158,20); background:rgba(5,22,34,44); }"
        "QPushButton:checked {"
        f" color:{TEXT_BRIGHT}; background:rgba(10,134,184,70); border-color:{ACCENT}; }}"
    )


def primary_button_css(min_height: int = 36) -> str:
    """The committed action. Gold edge marks it as the one thing to press."""
    return (
        "QPushButton {"
        f" color:#04121a; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
        f"  stop:0 {ACCENT_BRIGHT}, stop:1 {ACCENT});"
        f" border:1px solid {ACCENT_BRIGHT}; border-radius:{RADIUS_SM}px;"
        f" font:800 8pt {FONT_SMALL}; letter-spacing:1px;"
        f" min-height:{min_height}px; padding:6px 15px; }}"
        "QPushButton:hover {"
        f" background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
        f"  stop:0 #b6f2ff, stop:1 {ACCENT_BRIGHT}); }}"
        "QPushButton:pressed {"
        f" background:{ACCENT_DEEP}; color:{TEXT_BRIGHT}; }}"
    )


def accent_button_css(min_height: int = 34) -> str:
    """Gold signature button — use sparingly for a single 'armed/live' action."""
    return (
        "QPushButton {"
        f" color:#1c1204; background:rgba(244,178,74,30);"
        f" border:1px solid {GOLD}; border-radius:{RADIUS_SM}px;"
        f" font:800 8pt {FONT_SMALL}; letter-spacing:1px;"
        f" min-height:{min_height}px; padding:6px 13px; }}"
        f"QPushButton {{ color:{GOLD}; }}"
        "QPushButton:hover {"
        f" color:#1c1204; background:{GOLD}; border-color:#ffd48a; }}"
        f"QPushButton:pressed {{ background:{GOLD_DEEP}; color:#1c1204; }}"
    )


def field_css() -> str:
    return (
        "QLineEdit,QComboBox,QTextEdit,QListWidget,QSpinBox,QDoubleSpinBox "
        "{background:rgba(3,17,29,185);"
        f"color:{TEXT_BRIGHT};"
        f"border:1px solid {BORDER_FAINT};border-radius:{RADIUS_MD}px;"
        f"padding:6px 11px;font:9pt {FONT_UI};"
        f"selection-background-color:rgba(10,134,184,150);selection-color:{TEXT_BRIGHT};}}"
        "QLineEdit:hover,QComboBox:hover,QTextEdit:hover,QSpinBox:hover,QDoubleSpinBox:hover "
        f"{{border-color:{BORDER_SOFT};}}"
        "QLineEdit:focus,QComboBox:focus,QTextEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus "
        f"{{border-color:{ACCENT};background:rgba(4,26,40,225);}}"
        "QComboBox::drop-down{width:26px;border:none;background:transparent;}"
        f"QComboBox QAbstractItemView{{background:{BG};color:{TEXT};"
        f"border:1px solid {BORDER_SOFT};border-radius:{RADIUS_SM}px;padding:4px;"
        "selection-background-color:rgba(10,134,184,140);selection-color:#f0fdff;}"
        "QListWidget::item{padding:7px 9px;border:1px solid transparent;border-radius:5px;margin:1px 0;}"
        "QListWidget::item:selected{background:rgba(10,134,184,90);color:#f0fdff;"
        f"border-color:{BORDER_SOFT};}}"
        "QListWidget::item:hover{background:rgba(10,134,184,36);}"
    )


def card_css() -> str:
    return (
        f"QFrame {{ background:{CARD}; border:1px solid {BORDER_FAINT};"
        f" border-radius:{RADIUS_LG}px; }}"
    )


def header_css() -> str:
    return (
        f"QFrame {{ background:{HEADER}; border:1px solid {BORDER_SOFT};"
        f" border-radius:{RADIUS_MD}px; }}"
    )


def chip_css() -> str:
    return (
        f"color:{ACCENT_BRIGHT}; background:rgba(10,134,184,52);"
        f"border:1px solid {BORDER_FAINT}; border-radius:{RADIUS_SM}px;"
        "font:700 7pt 'Exo 2'; letter-spacing:1px; padding:5px 10px;"
    )


def section_css() -> str:
    return (
        f"color:{ACCENT}; font:800 8pt {FONT_HEAD}; letter-spacing:2px;"
        " background:transparent; padding:2px 2px 6px 2px;"
    )


def title_css(size: str = "10pt") -> str:
    return (
        f"color:{TEXT}; font:700 {size} {FONT_HEAD}; letter-spacing:3px;"
        " background:transparent; border:none;"
    )


def subtitle_css() -> str:
    return (
        f"color:{TEXT_FAINT}; font:600 6.5pt {FONT_SMALL}; letter-spacing:1px;"
        " background:transparent; border:none;"
    )


def scrollbar_css(width: int = 6) -> str:
    return (
        f"QScrollBar:vertical {{ background:transparent; width:{width}px; border:none; margin:2px; }}"
        "QScrollBar::handle:vertical { background:rgba(30,116,142,150); border-radius:3px; min-height:26px; }"
        f"QScrollBar::handle:vertical:hover {{ background:{ACCENT}; }}"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }"
        "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }"
        f"QScrollBar:horizontal {{ background:transparent; height:{width}px; border:none; margin:2px; }}"
        "QScrollBar::handle:horizontal { background:rgba(30,116,142,150); border-radius:3px; min-width:26px; }"
        f"QScrollBar::handle:horizontal:hover {{ background:{ACCENT}; }}"
        "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0px; }"
        "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background:transparent; }"
    )


def hidden_scrollbar_css() -> str:
    return (
        "QScrollBar:vertical { background:transparent; width:0px; border:none; }"
        "QScrollBar::handle:vertical { background:transparent; border:none; }"
        "QScrollBar:horizontal { background:transparent; height:0px; border:none; }"
        "QScrollBar::handle:horizontal { background:transparent; border:none; }"
    )


def tab_css() -> str:
    return (
        f"QPushButton {{ color:{TEXT_DIM}; background:rgba(5,22,34,70); border:1px solid transparent;"
        f" border-radius:{RADIUS_SM}px; font:700 7pt 'Exo 2'; letter-spacing:1px; padding:6px 10px; }}"
        f"QPushButton:hover {{ color:{TEXT_BRIGHT}; background:rgba(10,134,184,44); }}"
        f"QPushButton:checked {{ color:{TEXT_BRIGHT}; background:rgba(10,134,184,80);"
        f" border-color:{BORDER_SOFT}; }}"
    )


def icon_font_css() -> str:
    return "font-family:'Segoe UI Symbol','Segoe UI Emoji','Rajdhani','Segoe UI',sans-serif;"


def slider_css() -> str:
    return (
        "QSlider::groove:horizontal { height:4px; background:rgba(3,20,30,180);"
        f" border:1px solid {BORDER_FAINT}; border-radius:2px; }}"
        "QSlider::sub-page:horizontal { height:4px;"
        f" background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT_DEEP}, stop:1 {ACCENT});"
        " border:none; border-radius:2px; }"
        "QSlider::add-page:horizontal { background:rgba(3,18,26,150); border-radius:2px; }"
        f"QSlider::handle:horizontal {{ width:14px; height:14px; margin:-6px 0; background:{TEXT_BRIGHT};"
        f" border:2px solid {ACCENT}; border-radius:7px; }}"
        f"QSlider::handle:horizontal:hover {{ background:#ffffff; border-color:{ACCENT_BRIGHT}; }}"
    )


def checkbox_css() -> str:
    return (
        f"QCheckBox {{ spacing:8px; padding:6px 2px; color:{TEXT_MID}; background:transparent;"
        f" font:600 9pt {FONT_UI}; }}"
        "QCheckBox::indicator { width:15px; height:15px; border:1px solid #1f5f76;"
        " background:rgba(3,17,26,150); border-radius:4px; }"
        f"QCheckBox::indicator:hover {{ border-color:{ACCENT}; }}"
        f"QCheckBox::indicator:checked {{ background:{ACCENT}; border-color:{ACCENT_BRIGHT}; }}"
    )


def dialog_css() -> str:
    return (
        f"QDialog {{ background:{PANEL}; border:1px solid {BORDER_SOFT};"
        f" border-radius:{RADIUS_LG}px; color:{TEXT}; }}"
    )


def tooltip_css() -> str:
    return (
        f"QToolTip {{ background:{BG_DEEP}; color:{TEXT_BRIGHT};"
        f" border:1px solid {ACCENT_DEEP}; border-radius:5px; padding:5px 8px;"
        " font:8pt 'Exo 2'; }"
    )


STATUS_COLORS = {
    "ok": GREEN, "run": ACCENT, "think": ACCENT_BRIGHT, "warn": AMBER,
    "error": RED, "dim": TEXT_FAINT, "you": TEXT_BRIGHT, "ai": ACCENT_BRIGHT,
    "sys": TEXT_DIM, "live": GOLD,
}


def status_color(kind: str) -> str:
    return STATUS_COLORS.get(str(kind or "").lower(), STATUS_COLORS["dim"])


def meter_color(pct: float) -> str:
    try:
        pct = float(pct)
    except Exception:
        return ACCENT
    if pct >= 90:
        return RED
    if pct >= 70:
        return AMBER
    return ACCENT
