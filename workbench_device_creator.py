#!/usr/bin/env python3
"""
Asteron Workbench — Device Creator
Build .adev device files visually. Upload images, place pins, LEDs,
display regions, write emulation rules, preview, and export.

Install:  pip install PyQt5
Run:      python workbench_device_creator.py
"""
import sys
import os
import json
import math
import base64
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QComboBox, QCheckBox,
    QPlainTextEdit, QTextEdit, QTabWidget, QStackedWidget, QListWidget,
    QScrollArea, QFileDialog, QMessageBox, QColorDialog, QFrame,
    QSizePolicy, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QRadialGradient,
    QImage, QPalette, QFontMetrics, QPainterPath, QPixmap
)


# ═══════════════════════════════════════════════════════════════
#  THEME — Modern black with blue/red/green/orange accents
# ═══════════════════════════════════════════════════════════════
class T:
    # Backgrounds
    bg = "#0c0c0e"
    panel = "#131316"
    panelAlt = "#18181c"
    surface = "#1c1c22"
    surfHov = "#242430"
    # Borders
    border = "#222230"
    borderL = "#2a2a38"
    # Accents — blue, red, green, orange
    blue = "#4a9eff"
    blueDim = "#1a2844"
    red = "#ff4d4d"
    green = "#44dd66"
    orange = "#ff9933"
    # Text
    text = "#d4d4dc"
    textSec = "#8888a0"
    textMut = "#505068"
    # Fonts
    MONO = "Consolas"
    UI = "Segoe UI"
    R = 3


PIN_CLR = {
    "digital": T.blue, "analog": T.green, "power": T.red, "ground": "#666680",
    "gnd": "#666680", "signal": T.orange, "passive": "#808090",
    "i2c_sda": T.orange, "i2c_scl": T.orange, "spi_mosi": T.blue,
    "spi_miso": T.blue, "spi_sck": T.blue, "serial_tx": "#cc66ff",
    "serial_rx": "#cc66ff",
}

PIN_TYPES = [
    "digital", "analog", "power", "ground", "signal", "passive",
    "i2c_sda", "i2c_scl", "spi_mosi", "spi_miso", "spi_sck",
    "serial_tx", "serial_rx",
]
PIN_DIRS = ["io", "in", "out"]
PIN_SIDES = ["left", "right", "top", "bottom"]
CATEGORIES = [
    "Boards", "Output", "Display", "Input", "Sensor",
    "Passive", "Communication", "Other",
]

SS = (
    "QMainWindow{background:" + T.bg + "}"
    "QStatusBar{background:" + T.panel + ";color:" + T.textMut
    + ";border-top:1px solid " + T.border + "}"
    "QTabWidget::pane{background:" + T.panel + ";border:none;border-top:1px solid "
    + T.border + "}"
    "QTabBar::tab{background:" + T.panel + ";color:" + T.textMut
    + ";padding:8px 18px;border-bottom:2px solid transparent;"
    "font-family:Consolas;font-size:11px}"
    "QTabBar::tab:selected{color:" + T.blue + ";border-bottom-color:" + T.blue + "}"
    "QTabBar::tab:hover{color:" + T.text + "}"
    "QPushButton{background:" + T.surface + ";color:" + T.text + ";border:1px solid "
    + T.border + ";border-radius:4px;padding:6px 14px;font-size:11px;font-weight:bold}"
    "QPushButton:hover{background:" + T.surfHov + ";border-color:" + T.blue + "}"
    "QPushButton:checked{background:" + T.blueDim + ";border-color:" + T.blue
    + ";color:" + T.blue + "}"
    "QLineEdit,QSpinBox,QComboBox{background:" + T.bg + ";color:" + T.text
    + ";border:1px solid " + T.border + ";border-radius:4px;padding:5px 10px;font-size:11px}"
    "QLineEdit:focus,QSpinBox:focus{border-color:" + T.blue + "}"
    "QComboBox::drop-down{border:none;padding-right:8px}"
    "QComboBox QAbstractItemView{background:" + T.surface + ";color:" + T.text
    + ";border:1px solid " + T.border + ";selection-background-color:" + T.blue + "}"
    "QPlainTextEdit,QTextEdit{background:" + T.bg
    + ";color:#c8c8dc;border:none;font-family:Consolas;font-size:12px}"
    "QLabel{color:" + T.text + "}"
    "QScrollBar:vertical{background:" + T.bg + ";width:8px}"
    "QScrollBar::handle:vertical{background:" + T.border
    + ";min-height:30px;border-radius:4px}"
    "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}"
    "QScrollBar:horizontal{background:" + T.bg + ";height:8px}"
    "QScrollBar::handle:horizontal{background:" + T.border
    + ";min-width:30px;border-radius:4px}"
    "QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0}"
    "QListWidget{background:" + T.bg + ";color:" + T.text + ";border:1px solid "
    + T.border + ";border-radius:4px;font-size:11px;outline:none}"
    "QListWidget::item{padding:4px 8px}"
    "QListWidget::item:selected{background:" + T.blueDim + ";color:" + T.blue + "}"
    "QListWidget::item:hover{background:" + T.surfHov + "}"
    "QCheckBox{color:" + T.textSec + ";spacing:6px}"
    "QCheckBox::indicator{width:14px;height:14px;border:1px solid " + T.border
    + ";border-radius:3px;background:" + T.bg + "}"
    "QCheckBox::indicator:checked{background:" + T.blue + ";border-color:" + T.blue + "}"
)


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
def _section_label(text):
    """Create a styled section label."""
    lbl = QLabel(text)
    lbl.setFont(QFont(T.MONO, 9, QFont.Bold))
    lbl.setStyleSheet(
        "color:" + T.textMut + ";letter-spacing:1.5px;margin-top:6px"
    )
    return lbl


def make_field(label_text, widget, parent_layout):
    """Add a labeled field to a layout."""
    parent_layout.addWidget(_section_label(label_text))
    parent_layout.addWidget(widget)
    return widget


def make_spin(val, lo, hi, parent_layout, label):
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(val)
    s.setFont(QFont(T.MONO, 11))
    return make_field(label, s, parent_layout)


def make_combo(items, current, parent_layout, label):
    c = QComboBox()
    c.addItems(items)
    if current in items:
        c.setCurrentText(current)
    c.setFont(QFont(T.MONO, 11))
    return make_field(label, c, parent_layout)


def make_line(text, parent_layout, label, mono=False):
    e = QLineEdit(text)
    e.setFont(QFont(T.MONO if mono else T.UI, 11))
    return make_field(label, e, parent_layout)


# ═══════════════════════════════════════════════════════════════
#  VISUAL CANVAS
# ═══════════════════════════════════════════════════════════════
class VisualCanvas(QWidget):
    """Canvas for placing pins, LEDs, display regions on device image.
    KEY: sizing via update_size(), NEVER in paintEvent."""

    pinPlaced = pyqtSignal(int, int)
    ledPlaced = pyqtSignal(int, int)
    displayDrawn = pyqtSignal(int, int, int, int)
    itemClicked = pyqtSignal(str, int)

    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win
        self.setMouseTracking(True)
        self.tool = "select"
        self.zoom = 2
        self.image = None
        self.image_path = None
        self._drag_start = None
        self._drag_end = None

    def set_image(self, img, path):
        self.image = img
        self.image_path = path
        self.update_size()

    def clear_image(self):
        self.image = None
        self.image_path = None
        self.update_size()

    def update_size(self):
        dw = self.mw.dev_w.value()
        dh = self.mw.dev_h.value()
        self.setFixedSize(dw * self.zoom, dh * self.zoom)
        self.update()

    def _to_dev(self, pos):
        return QPoint(int(pos.x() / self.zoom), int(pos.y() / self.zoom))

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        p = self._to_dev(e.pos())
        x, y = p.x(), p.y()
        if self.tool == "pin":
            self.pinPlaced.emit(x, y)
        elif self.tool == "led":
            self.ledPlaced.emit(x, y)
        elif self.tool == "display":
            self._drag_start = (x, y)
            self._drag_end = None
        else:
            for i, pin in enumerate(self.mw.pins):
                if math.hypot(x - pin["x"], y - pin["y"]) < 8:
                    self.itemClicked.emit("pin", i)
                    return
            for i, led in enumerate(self.mw.leds):
                if math.hypot(x - led["x"], y - led["y"]) < led.get("radius", 8) + 2:
                    self.itemClicked.emit("led", i)
                    return
            self.itemClicked.emit("none", -1)

    def mouseReleaseEvent(self, e):
        if self.tool == "display" and self._drag_start:
            p = self._to_dev(e.pos())
            x0, y0 = self._drag_start
            x1, y1 = p.x(), p.y()
            rx, ry = min(x0, x1), min(y0, y1)
            rw, rh = abs(x1 - x0), abs(y1 - y0)
            if rw > 4 and rh > 4:
                self.displayDrawn.emit(rx, ry, rw, rh)
            self._drag_start = None
            self._drag_end = None
            self.update()

    def mouseMoveEvent(self, e):
        if self._drag_start:
            self._drag_end = self._to_dev(e.pos())
        self.update()

    def paintEvent(self, event):
        mw = self.mw
        dw = mw.dev_w.value()
        dh = mw.dev_h.value()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#0a0a0c"))
        p.scale(self.zoom, self.zoom)

        # Checkerboard
        cs = 8
        for gx in range(0, dw, cs):
            for gy in range(0, dh, cs):
                c = "#181820" if (gx // cs + gy // cs) % 2 == 0 else "#141418"
                p.fillRect(gx, gy, cs, cs, QColor(c))

        # Device image
        if self.image and not self.image.isNull():
            p.drawImage(QRectF(0, 0, dw, dh), self.image)
        else:
            p.fillRect(0, 0, dw, dh, QColor(mw.dev_color.text()))
            p.setPen(QColor(T.textMut))
            p.setFont(QFont(T.MONO, 10))
            p.drawText(QRectF(0, 0, dw, dh), Qt.AlignCenter, "No image\nUpload one")

        # Display region
        if mw.has_display.isChecked():
            dr = mw.disp_region
            p.fillRect(
                QRectF(dr["x"], dr["y"], dr["w"], dr["h"]),
                QColor(mw.disp_bg.text()),
            )
            p.setPen(QPen(QColor(T.blue), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(dr["x"], dr["y"], dr["w"], dr["h"]))
            p.setPen(QColor(T.blue + "88"))
            p.setFont(QFont(T.MONO, 7))
            p.drawText(
                QRectF(dr["x"], dr["y"], dr["w"], dr["h"]),
                Qt.AlignCenter,
                f"{mw.disp_px_w.value()}x{mw.disp_px_h.value()}",
            )

        # Region drag preview
        if self._drag_start and self._drag_end:
            x0, y0 = self._drag_start
            x1, y1 = self._drag_end.x(), self._drag_end.y()
            p.setPen(QPen(QColor(T.blue), 1.5, Qt.DashLine))
            p.setBrush(QBrush(QColor(74, 158, 255, 30)))
            p.drawRect(
                QRectF(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
            )

        # LED indicators
        test_state = mw.test_state if mw.test_running else {}
        for i, led in enumerate(mw.leds):
            sv = led.get("state_var", "")
            ov = led.get("on_value", True)
            is_on = mw.test_running and test_state.get(sv) == ov
            lx = led["x"]
            ly = led["y"]
            lr = led.get("radius", 8)
            lc = QColor(led.get("color", "#ff3344"))
            is_sel = mw.sel_type == "led" and mw.sel_idx == i

            if is_on:
                grad = QRadialGradient(lx, ly, lr * 3)
                grad.setColorAt(0, QColor(lc.red(), lc.green(), lc.blue(), 200))
                grad.setColorAt(1, QColor(lc.red(), lc.green(), lc.blue(), 0))
                p.setBrush(QBrush(grad))
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(lx, ly), lr * 3, lr * 3)

            fill = (
                QColor(lc)
                if is_on
                else QColor(lc.red() // 4, lc.green() // 4, lc.blue() // 4, 120)
            )
            p.setBrush(QBrush(fill))
            border_c = (
                QColor(T.orange)
                if is_sel
                else QColor(lc.red() // 2, lc.green() // 2, lc.blue() // 2)
            )
            p.setPen(QPen(border_c, 2 if is_sel else 1))
            p.drawEllipse(QPointF(lx, ly), lr, lr)
            p.setPen(QColor(T.text))
            p.setFont(QFont(T.MONO, 6, QFont.Bold))
            p.drawText(QPointF(lx - 10, ly - lr - 3), led.get("label", "?"))

        # Pins
        mouse_pos = self.mapFromGlobal(self.cursor().pos())
        if self.rect().contains(mouse_pos):
            mouse = self._to_dev(mouse_pos)
        else:
            mouse = QPoint(-999, -999)

        for i, pin in enumerate(mw.pins):
            pc = QColor(PIN_CLR.get(pin.get("type", "digital"), "#808090"))
            is_sel = mw.sel_type == "pin" and mw.sel_idx == i
            is_hov = math.hypot(mouse.x() - pin["x"], mouse.y() - pin["y"]) < 8
            r = 6 if (is_hov or is_sel) else 4

            fill_c = (
                QColor(T.blue)
                if is_hov
                else QColor("#ffffff")
                if is_sel
                else pc
            )
            border_c = (
                QColor(T.orange)
                if is_sel
                else QColor(T.blue)
                if is_hov
                else QColor(pc.red(), pc.green(), pc.blue(), 80)
            )
            p.setBrush(QBrush(fill_c))
            p.setPen(QPen(border_c, 2 if is_sel else 1))
            p.drawEllipse(QPointF(pin["x"], pin["y"]), r, r)

            # Direction arrow
            dirs = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}
            dx, dy = dirs.get(pin.get("side", "left"), (0, 0))
            p.setPen(QPen(QColor(pc.red(), pc.green(), pc.blue(), 100), 1.5))
            p.drawLine(
                QPointF(pin["x"], pin["y"]),
                QPointF(pin["x"] + dx * 10, pin["y"] + dy * 10),
            )

            # Label
            p.setPen(QColor(T.text))
            p.setFont(QFont(T.MONO, 6, QFont.Bold))
            p.drawText(QPointF(pin["x"] - 10, pin["y"] - 8), pin.get("label", "?"))

            # Hover tooltip
            if is_hov:
                txt = f'{pin.get("label", "?")} ({pin.get("type", "?")})'
                p.setFont(QFont(T.MONO, 7, QFont.Bold))
                fm = p.fontMetrics()
                tw = fm.horizontalAdvance(txt) + 12
                p.setBrush(QBrush(QColor(0, 0, 0, 220)))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(
                    QRectF(pin["x"] - tw / 2, pin["y"] - 28, tw, 16), 4, 4
                )
                p.setPen(QColor("#ffffff"))
                p.drawText(
                    QRectF(pin["x"] - tw / 2, pin["y"] - 28, tw, 16),
                    Qt.AlignCenter,
                    txt,
                )

        p.end()


# ═══════════════════════════════════════════════════════════════
#  DEFAULT EMULATION TEMPLATE
# ═══════════════════════════════════════════════════════════════
DEFAULT_EMU = """{
  "type": "active",
  "state_vars": {
    "led_on": false,
    "brightness": 0
  },
  "rules": [
    {
      "trigger": "pin_high",
      "pin": "anode",
      "action": "set_state",
      "target": "led_on",
      "value": true
    },
    {
      "trigger": "pin_low",
      "pin": "anode",
      "action": "set_state",
      "target": "led_on",
      "value": false
    }
  ],
  "properties": {
    "forward_voltage": 2.0,
    "max_current_ma": 20
  }
}"""


# ═══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════
class DeviceCreator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asteron Workbench \u2014 Device Creator")
        self.setMinimumSize(1000, 650)
        self.resize(1300, 800)
        self.setStyleSheet(SS)

        # Data model
        self.pins = []
        self.leds = []
        self.disp_region = {"x": 10, "y": 10, "w": 80, "h": 40}
        self.image_b64 = None
        self.sel_type = "none"
        self.sel_idx = -1
        self.test_running = False
        self.test_state = {}
        self.test_tick = 0

        self.test_timer = QTimer()
        self.test_timer.setInterval(500)
        self.test_timer.timeout.connect(self._test_tick)

        self._build_ui()
        self.st_msg = QLabel("Ready")
        self.st_msg.setFont(QFont(T.MONO, 10))
        self.statusBar().addWidget(self.st_msg)

    # ─────────────────────────────────────────────────────────
    # UI STRUCTURE
    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        ml = QVBoxLayout(cw)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # ── Top bar ──
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            "background:" + T.panel + ";border-bottom:1px solid " + T.border
        )
        tb = QHBoxLayout(bar)
        tb.setContentsMargins(12, 0, 12, 0)
        tb.setSpacing(8)

        logo = QLabel("ASTERON")
        logo.setFont(QFont(T.MONO, 15, QFont.Bold))
        logo.setStyleSheet("color:" + T.blue + ";letter-spacing:3px")
        tb.addWidget(logo)

        sub = QLabel("Workbench \u2022 Device Creator")
        sub.setFont(QFont(T.MONO, 10))
        sub.setStyleSheet("color:" + T.textMut)
        tb.addWidget(sub)
        tb.addSpacing(20)

        btn_imp = QPushButton("Import .adev")
        btn_imp.clicked.connect(self._import_adev)
        tb.addWidget(btn_imp)

        tb.addStretch()

        btn_exp = QPushButton("Export .adev")
        btn_exp.setStyleSheet(
            "QPushButton{background:" + T.blueDim + ";color:" + T.blue
            + ";border:1px solid " + T.blue + "55;border-radius:4px;"
            "padding:7px 20px;font-weight:bold}"
            "QPushButton:hover{background:" + T.blue + ";color:#000}"
        )
        btn_exp.clicked.connect(self._export)
        tb.addWidget(btn_exp)
        ml.addWidget(bar)

        # ── Tabs ──
        self.tabs = QTabWidget()
        ml.addWidget(self.tabs)
        self._build_info_tab()
        self._build_visual_tab()
        self._build_emu_tab()
        self._build_preview_tab()
        self._build_export_tab()

    # ─────────────────────────────────────────────────────────
    # TAB 1: INFO
    # ─────────────────────────────────────────────────────────
    def _build_info_tab(self):
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignTop)

        hdr = QLabel("Device Information")
        hdr.setFont(QFont(T.UI, 18, QFont.Bold))
        lay.addWidget(hdr)
        lay.addSpacing(10)

        self.dev_id = make_line("my_device", lay, "DEVICE ID", mono=True)
        self.dev_name = make_line("My Device", lay, "NAME")
        self.dev_category = make_combo(CATEGORIES, "Output", lay, "CATEGORY")

        lay.addWidget(_section_label("DESCRIPTION"))
        self.dev_desc = QPlainTextEdit()
        self.dev_desc.setMaximumHeight(70)
        self.dev_desc.setFont(QFont(T.UI, 11))
        lay.addWidget(self.dev_desc)

        row = QHBoxLayout()
        v1 = QVBoxLayout()
        self.dev_author = make_line("", v1, "AUTHOR")
        row.addLayout(v1)
        v2 = QVBoxLayout()
        self.dev_version = make_line("1.0", v2, "VERSION", mono=True)
        row.addLayout(v2)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        v3 = QVBoxLayout()
        self.dev_w = make_spin(100, 10, 2000, v3, "CANVAS WIDTH")
        row2.addLayout(v3)
        v4 = QVBoxLayout()
        self.dev_h = make_spin(100, 10, 2000, v4, "CANVAS HEIGHT")
        row2.addLayout(v4)
        lay.addLayout(row2)

        self.dev_w.valueChanged.connect(self._on_dims_changed)
        self.dev_h.valueChanged.connect(self._on_dims_changed)

        row3 = QHBoxLayout()
        v5 = QVBoxLayout()
        self.dev_label = make_line("DEV", v5, "LABEL", mono=True)
        row3.addLayout(v5)
        v6 = QVBoxLayout()
        # FIX: create QLabel properly, then add to layout
        color_lbl = _section_label("COLOR")
        v6.addWidget(color_lbl)
        color_row = QHBoxLayout()
        self.color_btn = QPushButton("  ")
        self.color_btn.setFixedSize(30, 30)
        self.color_btn.setStyleSheet(
            "background:#555555;border:1px solid " + T.border + ";border-radius:4px"
        )
        self.color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self.color_btn)
        self.dev_color = QLineEdit("#555555")
        self.dev_color.setFont(QFont(T.MONO, 11))
        self.dev_color.textChanged.connect(self._on_color_text_changed)
        color_row.addWidget(self.dev_color)
        v6.addLayout(color_row)
        row3.addLayout(v6)
        lay.addLayout(row3)
        lay.addStretch()

        outer.setWidget(w)
        self.tabs.addTab(outer, "Info")

    def _on_color_text_changed(self, t):
        if QColor(t).isValid():
            self.color_btn.setStyleSheet(
                "background:" + t + ";border:1px solid " + T.border + ";border-radius:4px"
            )

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.dev_color.text()), self)
        if c.isValid():
            self.dev_color.setText(c.name())

    def _on_dims_changed(self):
        if hasattr(self, "canvas"):
            self.canvas.update_size()
        if hasattr(self, "preview_canvas"):
            self.preview_canvas.update_size()
        self._refresh_info()

    # ─────────────────────────────────────────────────────────
    # TAB 2: VISUAL EDITOR
    # ─────────────────────────────────────────────────────────
    def _build_visual_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left: canvas
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        # Toolbar
        ctb_w = QWidget()
        ctb_w.setFixedHeight(38)
        ctb_w.setStyleSheet(
            "background:" + T.panelAlt + ";border-bottom:1px solid " + T.border
        )
        ctb = QHBoxLayout(ctb_w)
        ctb.setContentsMargins(10, 0, 10, 0)
        ctb.setSpacing(5)

        self.vtool_btns = {}
        for tid, label in [
            ("select", "Select"),
            ("pin", "Pin"),
            ("led", "LED"),
            ("display", "Display"),
        ]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(tid == "select")
            b.setFont(QFont(T.MONO, 10, QFont.Bold))
            b.clicked.connect(lambda checked, t=tid: self._set_vtool(t))
            ctb.addWidget(b)
            self.vtool_btns[tid] = b

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:" + T.border)
        ctb.addWidget(sep)

        zoom_lbl = QLabel("Zoom:")
        zoom_lbl.setFont(QFont(T.MONO, 9))
        zoom_lbl.setStyleSheet("color:" + T.textMut)
        ctb.addWidget(zoom_lbl)

        self.zoom_btns = {}
        for z in [1, 2, 3, 4]:
            b = QPushButton(f"{z}x")
            b.setFixedWidth(36)
            b.setCheckable(True)
            b.setChecked(z == 2)
            b.setFont(QFont(T.MONO, 10, QFont.Bold))
            b.clicked.connect(lambda checked, zz=z: self._set_zoom(zz))
            ctb.addWidget(b)
            self.zoom_btns[z] = b

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color:" + T.border)
        ctb.addWidget(sep2)

        btn_img = QPushButton("Upload Image")
        btn_img.clicked.connect(self._upload_image)
        ctb.addWidget(btn_img)
        btn_rm = QPushButton("Remove")
        btn_rm.setStyleSheet("QPushButton{color:" + T.red + "}")
        btn_rm.clicked.connect(self._remove_image)
        ctb.addWidget(btn_rm)
        ctb.addStretch()

        self.vis_info = QLabel("100x100 | 0 pins | 0 LEDs")
        self.vis_info.setFont(QFont(T.MONO, 9))
        self.vis_info.setStyleSheet("color:" + T.textMut)
        ctb.addWidget(self.vis_info)
        ll.addWidget(ctb_w)

        # Canvas
        self.canvas = VisualCanvas(self)
        self.canvas.pinPlaced.connect(self._on_pin_placed)
        self.canvas.ledPlaced.connect(self._on_led_placed)
        self.canvas.displayDrawn.connect(self._on_display_drawn)
        self.canvas.itemClicked.connect(self._on_item_clicked)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("QScrollArea{background:#0a0a0c;border:none}")
        ll.addWidget(scroll)
        layout.addWidget(left, 1)

        # Right: property panel
        right = QWidget()
        right.setFixedWidth(280)
        right.setStyleSheet(
            "background:" + T.panel + ";border-left:1px solid " + T.border
        )
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.prop_stack = QStackedWidget()
        rl.addWidget(self.prop_stack)
        self._build_overview_page()
        self._build_pin_editor_page()
        self._build_led_editor_page()
        self.prop_stack.setCurrentIndex(0)
        layout.addWidget(right)

        self.tabs.addTab(w, "Visual")

    def _build_overview_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        lay.addWidget(_section_label("PINS"))
        self.pin_list = QListWidget()
        self.pin_list.setMaximumHeight(180)
        self.pin_list.itemClicked.connect(
            lambda: self._on_item_clicked("pin", self.pin_list.currentRow())
        )
        lay.addWidget(self.pin_list)

        lay.addWidget(_section_label("LED INDICATORS"))
        self.led_list = QListWidget()
        self.led_list.setMaximumHeight(120)
        self.led_list.itemClicked.connect(
            lambda: self._on_item_clicked("led", self.led_list.currentRow())
        )
        lay.addWidget(self.led_list)

        lay.addWidget(_section_label("DISPLAY REGION"))
        self.has_display = QCheckBox("Has display region")
        self.has_display.toggled.connect(lambda _: self.canvas.update())
        lay.addWidget(self.has_display)

        dg = QWidget()
        dl = QVBoxLayout(dg)
        dl.setContentsMargins(0, 4, 0, 0)
        dl.setSpacing(4)
        self.disp_type = make_line("oled_ssd1306", dl, "TYPE", mono=True)
        r1 = QHBoxLayout()
        v1 = QVBoxLayout()
        self.disp_px_w = make_spin(128, 1, 4096, v1, "PX W")
        r1.addLayout(v1)
        v2 = QVBoxLayout()
        self.disp_px_h = make_spin(64, 1, 4096, v2, "PX H")
        r1.addLayout(v2)
        dl.addLayout(r1)
        r2 = QHBoxLayout()
        v3 = QVBoxLayout()
        self.disp_color = make_line("#00aaff", v3, "PIXEL CLR", mono=True)
        r2.addLayout(v3)
        v4 = QVBoxLayout()
        self.disp_bg = make_line("#000510", v4, "BG CLR", mono=True)
        r2.addLayout(v4)
        dl.addLayout(r2)
        r3 = QHBoxLayout()
        v5 = QVBoxLayout()
        self.disp_iface = make_combo(["i2c", "spi", "parallel"], "i2c", v5, "INTERFACE")
        r3.addLayout(v5)
        v6 = QVBoxLayout()
        self.disp_addr = make_line("0x3C", v6, "ADDR", mono=True)
        r3.addLayout(v6)
        dl.addLayout(r3)
        lay.addWidget(dg)
        lay.addStretch()

        hint = QLabel(
            "Click a pin or LED on the canvas to edit.\n"
            "Use the toolbar to place new items."
        )
        hint.setFont(QFont(T.UI, 9))
        hint.setStyleSheet(
            "color:" + T.textMut + ";padding:10px 0;border-top:1px solid " + T.border
        )
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.prop_stack.addWidget(page)

    def _build_pin_editor_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        title = QLabel("Pin Properties")
        title.setFont(QFont(T.UI, 13, QFont.Bold))
        hdr.addWidget(title)
        btn_back = QPushButton("Back")
        btn_back.clicked.connect(self._deselect)
        hdr.addWidget(btn_back)
        lay.addLayout(hdr)
        lay.addSpacing(4)

        self.pe_id = make_line("", lay, "ID", mono=True)
        self.pe_label = make_line("", lay, "LABEL", mono=True)
        r = QHBoxLayout()
        v1 = QVBoxLayout()
        self.pe_x = make_spin(0, -9999, 9999, v1, "X")
        r.addLayout(v1)
        v2 = QVBoxLayout()
        self.pe_y = make_spin(0, -9999, 9999, v2, "Y")
        r.addLayout(v2)
        lay.addLayout(r)
        self.pe_type = make_combo(PIN_TYPES, "digital", lay, "TYPE")
        self.pe_dir = make_combo(PIN_DIRS, "io", lay, "DIRECTION")
        self.pe_side = make_combo(PIN_SIDES, "left", lay, "SIDE")
        self.pe_notes = make_line("", lay, "NOTES")

        # Connect with proper lambda captures
        for widget, field in [
            (self.pe_id, "id"),
            (self.pe_label, "label"),
            (self.pe_notes, "notes"),
        ]:
            widget.textChanged.connect(lambda v, f=field: self._upd_pin(f, v))
        for widget, field in [(self.pe_x, "x"), (self.pe_y, "y")]:
            widget.valueChanged.connect(lambda v, f=field: self._upd_pin(f, v))
        for widget, field in [
            (self.pe_type, "type"),
            (self.pe_dir, "direction"),
            (self.pe_side, "side"),
        ]:
            widget.currentTextChanged.connect(lambda v, f=field: self._upd_pin(f, v))

        lay.addSpacing(12)
        btn_del = QPushButton("Delete Pin")
        btn_del.setStyleSheet("QPushButton{color:" + T.red + ";border-color:" + T.red + "44}")
        btn_del.clicked.connect(self._delete_sel_pin)
        lay.addWidget(btn_del)
        lay.addStretch()
        self.prop_stack.addWidget(page)

    def _build_led_editor_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        title = QLabel("LED Indicator")
        title.setFont(QFont(T.UI, 13, QFont.Bold))
        hdr.addWidget(title)
        btn_back = QPushButton("Back")
        btn_back.clicked.connect(self._deselect)
        hdr.addWidget(btn_back)
        lay.addLayout(hdr)
        lay.addSpacing(4)

        self.le_label = make_line("", lay, "LABEL", mono=True)
        r = QHBoxLayout()
        v1 = QVBoxLayout()
        self.le_x = make_spin(0, -9999, 9999, v1, "X")
        r.addLayout(v1)
        v2 = QVBoxLayout()
        self.le_y = make_spin(0, -9999, 9999, v2, "Y")
        r.addLayout(v2)
        lay.addLayout(r)
        self.le_radius = make_spin(8, 1, 100, lay, "RADIUS")

        lay.addWidget(_section_label("COLOR"))
        color_row = QHBoxLayout()
        self.le_color_btn = QPushButton("  ")
        self.le_color_btn.setFixedSize(30, 30)
        self.le_color_btn.setStyleSheet(
            "background:#ff3344;border:1px solid " + T.border + ";border-radius:4px"
        )
        self.le_color_btn.clicked.connect(self._pick_led_color)
        color_row.addWidget(self.le_color_btn)
        self.le_color = QLineEdit("#ff3344")
        self.le_color.setFont(QFont(T.MONO, 11))
        self.le_color.textChanged.connect(self._on_led_color_text_changed)
        color_row.addWidget(self.le_color)
        lay.addLayout(color_row)

        self.le_state_var = make_line("led_on", lay, "STATE VARIABLE", mono=True)
        self.le_on_value = make_line("true", lay, "ON VALUE", mono=True)

        info = QLabel(
            "LED lights up when the state variable\n"
            "equals the ON value during simulation."
        )
        info.setFont(QFont(T.UI, 9))
        info.setStyleSheet(
            "color:" + T.textSec + ";background:" + T.bg
            + ";padding:10px;border:1px solid " + T.border
            + ";border-radius:4px;margin-top:8px"
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        # Connect
        for widget, field in [
            (self.le_label, "label"),
            (self.le_color, "color"),
            (self.le_state_var, "state_var"),
            (self.le_on_value, "on_value_str"),
        ]:
            widget.textChanged.connect(lambda v, f=field: self._upd_led(f, v))
        for widget, field in [
            (self.le_x, "x"),
            (self.le_y, "y"),
            (self.le_radius, "radius"),
        ]:
            widget.valueChanged.connect(lambda v, f=field: self._upd_led(f, v))

        lay.addSpacing(12)
        btn_del = QPushButton("Delete LED")
        btn_del.setStyleSheet("QPushButton{color:" + T.red + ";border-color:" + T.red + "44}")
        btn_del.clicked.connect(self._delete_sel_led)
        lay.addWidget(btn_del)
        lay.addStretch()
        self.prop_stack.addWidget(page)

    def _on_led_color_text_changed(self, t):
        if QColor(t).isValid():
            self.le_color_btn.setStyleSheet(
                "background:" + t + ";border:1px solid " + T.border + ";border-radius:4px"
            )

    # ─────────────────────────────────────────────────────────
    # TAB 3: EMULATION
    # ─────────────────────────────────────────────────────────
    def _build_emu_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Editor
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        tbw = QWidget()
        tbw.setFixedHeight(34)
        tbw.setStyleSheet(
            "background:" + T.panelAlt + ";border-bottom:1px solid " + T.border
        )
        tbl = QHBoxLayout(tbw)
        tbl.setContentsMargins(12, 0, 12, 0)
        file_lbl = QLabel("emulation.json")
        file_lbl.setFont(QFont(T.MONO, 10))
        file_lbl.setStyleSheet("color:" + T.textMut)
        tbl.addWidget(file_lbl)
        tbl.addStretch()
        self.emu_status = QLabel("Valid JSON")
        self.emu_status.setFont(QFont(T.MONO, 10))
        self.emu_status.setStyleSheet("color:" + T.green)
        tbl.addWidget(self.emu_status)
        btn_fmt = QPushButton("Format")
        btn_fmt.clicked.connect(self._format_emu)
        tbl.addWidget(btn_fmt)
        ll.addWidget(tbw)

        self.emu_editor = QPlainTextEdit()
        self.emu_editor.setPlainText(DEFAULT_EMU)
        self.emu_editor.setFont(QFont(T.MONO, 12))
        self.emu_editor.textChanged.connect(self._validate_emu)
        ll.addWidget(self.emu_editor)
        layout.addWidget(left, 1)

        # Reference
        right = QWidget()
        right.setFixedWidth(230)
        right.setStyleSheet(
            "background:" + T.panel + ";border-left:1px solid " + T.border
        )
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 10, 10, 10)
        rl.setSpacing(6)

        triggers = [
            "pin_high", "pin_low", "pin_pwm", "analog_read", "user_press",
            "user_release", "user_adjust", "tone", "no_tone", "i2c_command",
            "display_print", "circuit_update", "servo_write",
        ]
        actions = [
            "set_state", "compute", "return_value", "visual_update",
            "render_text", "set_pixel", "clear_framebuffer", "process_command",
        ]
        for section_title, items in [("TRIGGERS", triggers), ("ACTIONS", actions)]:
            rl.addWidget(_section_label(section_title))
            lw = QListWidget()
            lw.setMaximumHeight(min(130, len(items) * 22))
            lw.setFont(QFont(T.MONO, 10))
            for item in items:
                lw.addItem(item)
            rl.addWidget(lw)

        rl.addWidget(_section_label("YOUR PINS"))
        self.emu_pin_list = QListWidget()
        self.emu_pin_list.setMaximumHeight(100)
        self.emu_pin_list.setFont(QFont(T.MONO, 10))
        rl.addWidget(self.emu_pin_list)
        rl.addStretch()
        layout.addWidget(right)

        self.tabs.addTab(w, "Emulation")

    def _validate_emu(self):
        try:
            json.loads(self.emu_editor.toPlainText())
            self.emu_status.setText("Valid JSON")
            self.emu_status.setStyleSheet("color:" + T.green)
            return True
        except json.JSONDecodeError as e:
            msg = str(e)[:40]
            self.emu_status.setText("Error: " + msg)
            self.emu_status.setStyleSheet("color:" + T.red)
            return False

    def _format_emu(self):
        try:
            obj = json.loads(self.emu_editor.toPlainText())
            self.emu_editor.setPlainText(json.dumps(obj, indent=2))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────
    # TAB 4: PREVIEW
    # ─────────────────────────────────────────────────────────
    def _build_preview_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tbw = QWidget()
        tbw.setFixedHeight(38)
        tbw.setStyleSheet(
            "background:" + T.panelAlt + ";border-bottom:1px solid " + T.border
        )
        tb = QHBoxLayout(tbw)
        tb.setContentsMargins(12, 0, 12, 0)
        tb.setSpacing(10)

        preview_lbl = QLabel("Live Preview")
        preview_lbl.setFont(QFont(T.MONO, 10))
        preview_lbl.setStyleSheet("color:" + T.textMut)
        tb.addWidget(preview_lbl)

        self.btn_test = QPushButton("Run Test")
        self.btn_test.setStyleSheet(
            "QPushButton{background:" + T.blueDim + ";color:" + T.blue
            + ";border:1px solid " + T.blue + "44}"
        )
        self.btn_test.clicked.connect(self._toggle_test)
        tb.addWidget(self.btn_test)

        self.test_lbl = QLabel("")
        self.test_lbl.setFont(QFont(T.MONO, 10))
        self.test_lbl.setStyleSheet("color:" + T.green)
        tb.addWidget(self.test_lbl)
        tb.addStretch()
        layout.addWidget(tbw)

        self.preview_canvas = VisualCanvas(self)
        self.preview_canvas.tool = "select"
        self.preview_canvas.zoom = 3
        scroll = QScrollArea()
        scroll.setWidget(self.preview_canvas)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("QScrollArea{background:#0a0a0c;border:none}")
        layout.addWidget(scroll, 1)

        state_w = QWidget()
        state_w.setFixedHeight(80)
        state_w.setStyleSheet(
            "background:" + T.panel + ";border-top:1px solid " + T.border
        )
        sl = QVBoxLayout(state_w)
        sl.setContentsMargins(12, 8, 12, 8)
        sl.addWidget(_section_label("STATE VARIABLES"))
        self.state_display = QLabel("No state \u2014 run test to see changes")
        self.state_display.setFont(QFont(T.MONO, 10))
        self.state_display.setStyleSheet("color:" + T.textSec)
        self.state_display.setWordWrap(True)
        sl.addWidget(self.state_display)
        layout.addWidget(state_w)

        self.tabs.addTab(w, "Preview")

    def _toggle_test(self):
        if self.test_running:
            self.test_running = False
            self.test_state = {}
            self.test_timer.stop()
            self.btn_test.setText("Run Test")
            self.btn_test.setStyleSheet(
                "QPushButton{background:" + T.blueDim + ";color:" + T.blue
                + ";border:1px solid " + T.blue + "44}"
            )
            self.test_lbl.setText("")
            self.state_display.setText("Stopped")
        else:
            self.test_running = True
            self.test_tick = 0
            self.test_timer.start()
            self.btn_test.setText("Stop")
            self.btn_test.setStyleSheet(
                "QPushButton{background:" + T.red + ";color:#fff;border:none}"
            )
        self.canvas.update()
        self.preview_canvas.update()

    def _test_tick(self):
        self.test_tick += 1
        try:
            emu = json.loads(self.emu_editor.toPlainText())
            sv = dict(emu.get("state_vars", {}))
            for rule in emu.get("rules", []):
                if rule.get("action") == "set_state" and rule.get("target"):
                    if rule.get("trigger") == "pin_high":
                        val = rule.get("value")
                        if isinstance(val, bool):
                            sv[rule["target"]] = val if self.test_tick % 2 == 0 else (not val)
                        else:
                            sv[rule["target"]] = val if self.test_tick % 2 == 0 else 0
            self.test_state = sv
            parts = "  |  ".join(f"{k}: {v}" for k, v in sv.items())
            self.state_display.setText(parts if parts else "Empty state")
        except Exception:
            pass
        self.test_lbl.setText(f"tick {self.test_tick}")
        self.canvas.update()
        self.preview_canvas.update()

    # ─────────────────────────────────────────────────────────
    # TAB 5: EXPORT
    # ─────────────────────────────────────────────────────────
    def _build_export_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(28, 24, 28, 24)
        ll.setSpacing(10)

        hdr = QLabel("Export Device File")
        hdr.setFont(QFont(T.UI, 18, QFont.Bold))
        ll.addWidget(hdr)
        ll.addSpacing(8)

        self.export_summary = QTextEdit()
        self.export_summary.setReadOnly(True)
        self.export_summary.setMaximumHeight(220)
        self.export_summary.setFont(QFont(T.MONO, 11))
        self.export_summary.setStyleSheet(
            "background:" + T.bg + ";border:1px solid " + T.border
            + ";border-radius:4px;padding:12px"
        )
        ll.addWidget(self.export_summary)

        self.export_err = QLabel("")
        self.export_err.setFont(QFont(T.MONO, 10))
        self.export_err.setStyleSheet("color:" + T.red)
        ll.addWidget(self.export_err)

        btn = QPushButton("Save .adev file")
        btn.setStyleSheet(
            "QPushButton{background:" + T.blue + ";color:#000;border:none;"
            "border-radius:4px;padding:14px;font-size:14px;font-weight:bold}"
            "QPushButton:hover{background:#5cb0ff}"
        )
        btn.clicked.connect(self._export)
        ll.addWidget(btn)
        ll.addStretch()
        layout.addWidget(left, 1)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        preview_lbl = QLabel("  JSON Preview")
        preview_lbl.setFont(QFont(T.MONO, 10))
        preview_lbl.setStyleSheet(
            "background:" + T.panelAlt + ";color:" + T.textMut
            + ";padding:8px;border-bottom:1px solid " + T.border
        )
        rl.addWidget(preview_lbl)
        self.export_preview = QPlainTextEdit()
        self.export_preview.setReadOnly(True)
        self.export_preview.setFont(QFont(T.MONO, 11))
        rl.addWidget(self.export_preview)
        layout.addWidget(right, 1)

        self.tabs.addTab(w, "Export")
        self.tabs.currentChanged.connect(self._on_tab_change)

    def _on_tab_change(self, idx):
        name = self.tabs.tabText(idx)
        if name == "Export":
            self._update_export_preview()
        elif name == "Emulation":
            self.emu_pin_list.clear()
            for pin in self.pins:
                self.emu_pin_list.addItem(f'{pin["id"]} ({pin["type"]})')
        elif name == "Preview":
            self.preview_canvas.image = self.canvas.image
            self.preview_canvas.image_path = self.canvas.image_path
            self.preview_canvas.update_size()
        elif name == "Visual":
            self.canvas.update_size()

    def _update_export_preview(self):
        adev = self._build_adev()
        if adev:
            preview = json.loads(json.dumps(adev))
            img_svg = preview.get("visual", {}).get("image_svg")
            if img_svg and len(img_svg) > 200:
                preview["visual"]["image_svg"] = "(image data truncated)"
            self.export_preview.setPlainText(json.dumps(preview, indent=2))
            self.export_summary.setPlainText(
                f'Name: {adev["device"]["name"]}\n'
                f'ID: {adev["device"]["id"]}\n'
                f'Category: {adev["device"]["category"]}\n'
                f'Size: {adev["visual"]["width"]}x{adev["visual"]["height"]}\n'
                f'Pins: {len(adev.get("pins", []))}\n'
                f'LEDs: {len(adev["visual"].get("led_indicators", []))}\n'
                f'Display: {"Yes" if "display" in adev else "No"}\n'
                f'Image: {"Embedded" if self.image_b64 else "None"}\n'
                f"Emulation: Valid"
            )
            self.export_err.setText("")
        else:
            self.export_err.setText("Fix emulation JSON errors before exporting.")

    # ─────────────────────────────────────────────────────────
    # VISUAL ACTIONS
    # ─────────────────────────────────────────────────────────
    def _set_vtool(self, t):
        self.canvas.tool = t
        self.canvas._drag_start = None
        self.canvas._drag_end = None
        for k, b in self.vtool_btns.items():
            b.setChecked(k == t)

    def _set_zoom(self, z):
        self.canvas.zoom = z
        for zz, b in self.zoom_btns.items():
            b.setChecked(zz == z)
        self.canvas.update_size()

    def _upload_image(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Upload Device Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All (*)",
        )
        if not f:
            return
        img = QImage(f)
        if img.isNull():
            QMessageBox.warning(self, "Error", "Failed to load image.")
            return
        self.canvas.set_image(img, f)
        self.dev_w.setValue(img.width())
        self.dev_h.setValue(img.height())
        with open(f, "rb") as fh:
            self.image_b64 = base64.b64encode(fh.read()).decode("ascii")
        self.preview_canvas.image = img
        self.preview_canvas.image_path = f
        self.preview_canvas.update_size()
        self.st_msg.setText(f"Image: {Path(f).name} ({img.width()}x{img.height()})")
        self._refresh_info()

    def _remove_image(self):
        self.canvas.clear_image()
        self.preview_canvas.image = None
        self.preview_canvas.update_size()
        self.image_b64 = None
        self.st_msg.setText("Image removed")

    def _on_pin_placed(self, x, y):
        idx = len(self.pins)
        self.pins.append({
            "id": f"pin_{idx}", "label": f"P{idx}", "x": x, "y": y,
            "side": "left", "type": "digital", "direction": "io", "notes": "",
        })
        self._refresh_lists()
        self._on_item_clicked("pin", idx)
        self.canvas.update()

    def _on_led_placed(self, x, y):
        idx = len(self.leds)
        self.leds.append({
            "label": f"LED{idx}", "x": x, "y": y, "radius": 8,
            "color": "#ff3344", "state_var": "led_on", "on_value": True,
        })
        self._refresh_lists()
        self._on_item_clicked("led", idx)
        self.canvas.update()

    def _on_display_drawn(self, x, y, w, h):
        self.disp_region = {"x": x, "y": y, "w": w, "h": h}
        self.has_display.setChecked(True)
        self.canvas.update()
        self.st_msg.setText(f"Display region: {w}x{h} at ({x},{y})")

    def _on_item_clicked(self, typ, idx):
        self.sel_type = typ
        self.sel_idx = idx

        if typ == "pin" and 0 <= idx < len(self.pins):
            pin = self.pins[idx]
            widgets = [
                self.pe_id, self.pe_label, self.pe_notes,
                self.pe_x, self.pe_y, self.pe_type, self.pe_dir, self.pe_side,
            ]
            for wgt in widgets:
                wgt.blockSignals(True)
            self.pe_id.setText(pin["id"])
            self.pe_label.setText(pin["label"])
            self.pe_x.setValue(pin["x"])
            self.pe_y.setValue(pin["y"])
            self.pe_type.setCurrentText(pin["type"])
            self.pe_dir.setCurrentText(pin["direction"])
            self.pe_side.setCurrentText(pin["side"])
            self.pe_notes.setText(pin.get("notes", ""))
            for wgt in widgets:
                wgt.blockSignals(False)
            self.prop_stack.setCurrentIndex(1)

        elif typ == "led" and 0 <= idx < len(self.leds):
            led = self.leds[idx]
            widgets = [
                self.le_label, self.le_x, self.le_y, self.le_radius,
                self.le_color, self.le_state_var, self.le_on_value,
            ]
            for wgt in widgets:
                wgt.blockSignals(True)
            self.le_label.setText(led["label"])
            self.le_x.setValue(led["x"])
            self.le_y.setValue(led["y"])
            self.le_radius.setValue(led.get("radius", 8))
            self.le_color.setText(led.get("color", "#ff3344"))
            self.le_color_btn.setStyleSheet(
                "background:" + led.get("color", "#ff3344")
                + ";border:1px solid " + T.border + ";border-radius:4px"
            )
            self.le_state_var.setText(led.get("state_var", ""))
            ov = led.get("on_value", True)
            self.le_on_value.setText(
                str(ov).lower() if isinstance(ov, bool) else str(ov)
            )
            for wgt in widgets:
                wgt.blockSignals(False)
            self.prop_stack.setCurrentIndex(2)
        else:
            self._deselect()

        self.canvas.update()
        self.preview_canvas.update()

    def _deselect(self):
        self.sel_type = "none"
        self.sel_idx = -1
        self.prop_stack.setCurrentIndex(0)
        self.pin_list.clearSelection()
        self.led_list.clearSelection()
        self.canvas.update()

    def _upd_pin(self, field, val):
        if self.sel_type == "pin" and 0 <= self.sel_idx < len(self.pins):
            self.pins[self.sel_idx][field] = val
            self._refresh_lists()
            self.canvas.update()

    def _upd_led(self, field, val):
        if self.sel_type == "led" and 0 <= self.sel_idx < len(self.leds):
            if field == "on_value_str":
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                else:
                    try:
                        val = float(val) if "." in val else int(val)
                    except ValueError:
                        pass
                self.leds[self.sel_idx]["on_value"] = val
            else:
                self.leds[self.sel_idx][field] = val
            self._refresh_lists()
            self.canvas.update()

    def _delete_sel_pin(self):
        if self.sel_type == "pin" and 0 <= self.sel_idx < len(self.pins):
            self.pins.pop(self.sel_idx)
            self._deselect()
            self._refresh_lists()
            self.canvas.update()

    def _delete_sel_led(self):
        if self.sel_type == "led" and 0 <= self.sel_idx < len(self.leds):
            self.leds.pop(self.sel_idx)
            self._deselect()
            self._refresh_lists()
            self.canvas.update()

    def _pick_led_color(self):
        c = QColorDialog.getColor(QColor(self.le_color.text()), self)
        if c.isValid():
            self.le_color.setText(c.name())

    def _refresh_lists(self):
        self.pin_list.clear()
        for pin in self.pins:
            self.pin_list.addItem(
                f'{pin["label"]}  ({pin["type"]})  @{pin["x"]},{pin["y"]}'
            )
        self.led_list.clear()
        for led in self.leds:
            self.led_list.addItem(
                f'{led["label"]}  -> {led.get("state_var", "?")}  {led.get("color", "")}'
            )
        self._refresh_info()

    def _refresh_info(self):
        if hasattr(self, "vis_info"):
            self.vis_info.setText(
                f"{self.dev_w.value()}x{self.dev_h.value()} | "
                f"{len(self.pins)} pins | {len(self.leds)} LEDs"
            )

    # ─────────────────────────────────────────────────────────
    # BUILD .adev
    # ─────────────────────────────────────────────────────────
    def _build_adev(self):
        if not self._validate_emu():
            return None
        try:
            emu = json.loads(self.emu_editor.toPlainText())
        except Exception:
            return None

        adev = {
            "format_version": "1.0",
            "device": {
                "id": self.dev_id.text(),
                "name": self.dev_name.text(),
                "category": self.dev_category.currentText(),
                "description": self.dev_desc.toPlainText(),
                "author": self.dev_author.text(),
                "version": self.dev_version.text(),
            },
            "visual": {
                "width": self.dev_w.value(),
                "height": self.dev_h.value(),
                "label": self.dev_label.text(),
                "color": self.dev_color.text(),
            },
            "pins": [dict(pin) for pin in self.pins],
            "emulation": emu,
        }

        if self.image_b64:
            img_path = self.canvas.image_path or ""
            ext = Path(img_path).suffix.lower() if img_path else ".png"
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            mime = mime_map.get(ext, "image/png")
            w_val = self.dev_w.value()
            h_val = self.dev_h.value()
            adev["visual"]["image_svg"] = (
                f"<svg xmlns='http://www.w3.org/2000/svg' width='{w_val}' height='{h_val}'>"
                f"<image href='data:{mime};base64,{self.image_b64}'"
                f" width='{w_val}' height='{h_val}'/></svg>"
            )

        if self.leds:
            adev["visual"]["led_indicators"] = [
                {
                    "label": led["label"],
                    "x": led["x"],
                    "y": led["y"],
                    "radius": led.get("radius", 8),
                    "color": led.get("color", "#ff3344"),
                    "state_var": led.get("state_var", ""),
                    "on_value": led.get("on_value", True),
                }
                for led in self.leds
            ]

        if self.has_display.isChecked():
            adev["display"] = {
                "type": self.disp_type.text(),
                "width_px": self.disp_px_w.value(),
                "height_px": self.disp_px_h.value(),
                "pixel_color": self.disp_color.text(),
                "background_color": self.disp_bg.text(),
                "region": dict(self.disp_region),
                "interface": self.disp_iface.currentText(),
                "address": self.disp_addr.text(),
            }

        return adev

    # ─────────────────────────────────────────────────────────
    # EXPORT / IMPORT
    # ─────────────────────────────────────────────────────────
    def _export(self):
        adev = self._build_adev()
        if not adev:
            QMessageBox.warning(self, "Error", "Fix emulation JSON errors first.")
            return
        name = self.dev_id.text() or "device"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Device File", f"{name}.adev",
            "Device Files (*.adev);;JSON (*.json);;All (*)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(adev, f, indent=2)
        self.st_msg.setText(f"Exported: {Path(path).name}")
        QMessageBox.information(self, "Done", f"Saved to:\n{path}")

    def _import_adev(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Import Device File", "",
            "Device Files (*.adev *.json);;All (*)",
        )
        if not f:
            return
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        dev = data.get("device", {})
        vis = data.get("visual", {})
        self.dev_id.setText(dev.get("id", ""))
        self.dev_name.setText(dev.get("name", ""))
        cat_idx = self.dev_category.findText(dev.get("category", "Other"))
        if cat_idx >= 0:
            self.dev_category.setCurrentIndex(cat_idx)
        self.dev_desc.setPlainText(dev.get("description", ""))
        self.dev_author.setText(dev.get("author", ""))
        self.dev_version.setText(dev.get("version", "1.0"))
        self.dev_w.setValue(vis.get("width", 100))
        self.dev_h.setValue(vis.get("height", 100))
        self.dev_label.setText(vis.get("label", ""))
        self.dev_color.setText(vis.get("color", "#555"))

        self.pins = list(data.get("pins", []))
        self.leds = list(vis.get("led_indicators", []))

        if data.get("emulation"):
            self.emu_editor.setPlainText(json.dumps(data["emulation"], indent=2))

        if data.get("display"):
            self.has_display.setChecked(True)
            d = data["display"]
            self.disp_type.setText(d.get("type", ""))
            self.disp_px_w.setValue(d.get("width_px", 128))
            self.disp_px_h.setValue(d.get("height_px", 64))
            self.disp_color.setText(d.get("pixel_color", "#00aaff"))
            self.disp_bg.setText(d.get("background_color", "#000510"))
            if "region" in d:
                self.disp_region = d["region"]
            iface_idx = self.disp_iface.findText(d.get("interface", "i2c"))
            if iface_idx >= 0:
                self.disp_iface.setCurrentIndex(iface_idx)
            self.disp_addr.setText(d.get("address", "0x3C"))

        self._refresh_lists()
        self.canvas.update_size()
        self.st_msg.setText(f"Imported: {Path(f).name}")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(T.bg))
    pal.setColor(QPalette.WindowText, QColor(T.text))
    pal.setColor(QPalette.Base, QColor(T.panel))
    pal.setColor(QPalette.Text, QColor(T.text))
    pal.setColor(QPalette.Button, QColor(T.panel))
    pal.setColor(QPalette.ButtonText, QColor(T.text))
    pal.setColor(QPalette.Highlight, QColor(T.blue))
    pal.setColor(QPalette.HighlightedText, QColor("#000"))
    app.setPalette(pal)
    win = DeviceCreator()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
