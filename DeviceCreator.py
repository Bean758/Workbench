#!/usr/bin/env python3
"""
ArduSim Device Creator — Build .adev device files visually
Upload a 2D image, place pins, add LED indicators, define display regions,
write emulation rules, test it live, and export as .adev.

Install:  pip install PyQt5
Run:      python ardusim_device_creator.py
"""
import sys, os, json, math, base64
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# ═══════════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════════
class T:
    bg="#18191c"; panel="#1e1f23"; panelAlt="#222327"; border="#2c2d32"
    borderL="#35363c"; surface="#26272c"; surfHov="#2e2f35"
    accent="#3ea8ff"; accentDim="#163040"
    red="#e5534b"; green="#56d364"; yellow="#f5a623"; purple="#b87aff"
    text="#cdd1d8"; textSec="#7d8590"; textMut="#484c56"
    MONO="Consolas"; UI="Segoe UI"; R=3

PIN_CLR = {
    "digital":"#3ea8ff","analog":"#56d364","power":"#e5534b","ground":"#6e7681",
    "gnd":"#6e7681","signal":"#f5a623","passive":"#8b949e",
    "i2c_sda":"#f5a623","i2c_scl":"#f5a623","spi_mosi":"#3ea8ff",
    "spi_miso":"#3ea8ff","spi_sck":"#3ea8ff","serial_tx":"#b87aff","serial_rx":"#b87aff",
}

PIN_TYPES = ["digital","analog","power","ground","signal","passive",
             "i2c_sda","i2c_scl","spi_mosi","spi_miso","spi_sck","serial_tx","serial_rx"]
PIN_DIRS = ["io","in","out"]
PIN_SIDES = ["left","right","top","bottom"]
CATEGORIES = ["Boards","Output","Display","Input","Sensor","Passive","Communication","Other"]
EMU_TYPES = ["passive","active","microcontroller","display"]

SS = """
QMainWindow{background:"""+T.bg+"""}
QMenuBar{background:"""+T.panel+""";color:"""+T.text+""";border-bottom:1px solid """+T.border+"""}
QMenuBar::item:selected{background:"""+T.surfHov+"""}
QToolBar{background:"""+T.panel+""";border-bottom:1px solid """+T.border+""";spacing:4px;padding:3px 8px}
QStatusBar{background:"""+T.panel+""";color:"""+T.textMut+""";border-top:1px solid """+T.border+"""}
QSplitter::handle{background:"""+T.border+""";width:2px}
QTabWidget::pane{background:"""+T.panel+""";border:none;border-top:1px solid """+T.border+"""}
QTabBar::tab{background:"""+T.panel+""";color:"""+T.textMut+""";padding:7px 16px;border-bottom:2px solid transparent;font-family:Consolas;font-size:11px}
QTabBar::tab:selected{color:"""+T.accent+""";border-bottom-color:"""+T.accent+"""}
QTabBar::tab:hover{color:"""+T.text+"""}
QPushButton{background:"""+T.surface+""";color:"""+T.text+""";border:1px solid """+T.border+""";border-radius:3px;padding:5px 12px;font-size:11px;font-weight:bold}
QPushButton:hover{background:"""+T.surfHov+""";border-color:"""+T.accent+"""}
QPushButton:disabled{opacity:0.4}
QLineEdit,QSpinBox,QComboBox{background:"""+T.bg+""";color:"""+T.text+""";border:1px solid """+T.border+""";border-radius:3px;padding:4px 8px;font-size:11px}
QLineEdit:focus,QSpinBox:focus,QComboBox:focus{border-color:"""+T.accent+"""}
QComboBox::drop-down{border:none;padding-right:6px}
QComboBox QAbstractItemView{background:"""+T.surface+""";color:"""+T.text+""";border:1px solid """+T.border+""";selection-background-color:"""+T.accent+"""}
QPlainTextEdit,QTextEdit{background:"""+T.bg+""";color:#c8d0dc;border:none;font-family:Consolas;font-size:12px;selection-background-color:rgba(62,168,255,0.25)}
QGroupBox{background:"""+T.panel+""";border:1px solid """+T.border+""";border-radius:3px;margin-top:12px;padding-top:14px;font-weight:bold;color:"""+T.textSec+"""}
QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;color:"""+T.textMut+""";font-size:10px;letter-spacing:1.5px}
QLabel{color:"""+T.text+"""}
QScrollBar:vertical{background:"""+T.bg+""";width:8px}
QScrollBar::handle:vertical{background:"""+T.border+""";min-height:30px;border-radius:4px}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}
QListWidget{background:"""+T.bg+""";color:"""+T.text+""";border:1px solid """+T.border+""";border-radius:3px;font-size:11px;outline:none}
QListWidget::item{padding:4px 8px}
QListWidget::item:selected{background:"""+T.accentDim+""";color:"""+T.accent+"""}
QListWidget::item:hover{background:"""+T.surfHov+"""}
"""

# ═══════════════════════════════════════════════════════════════
#  HELPER: Labeled field
# ═══════════════════════════════════════════════════════════════
def make_field(label_text, widget, parent_layout):
    lbl = QLabel(label_text)
    lbl.setFont(QFont(T.MONO, 9, QFont.Bold))
    lbl.setStyleSheet("color:" + T.textMut + ";letter-spacing:1px;margin-top:4px")
    parent_layout.addWidget(lbl)
    parent_layout.addWidget(widget)
    return widget

def make_spin(val, lo, hi, parent_layout, label):
    s = QSpinBox()
    s.setRange(lo, hi); s.setValue(val); s.setFont(QFont(T.MONO, 11))
    return make_field(label, s, parent_layout)

def make_combo(items, current, parent_layout, label):
    c = QComboBox()
    c.addItems(items)
    if current in items: c.setCurrentText(current)
    c.setFont(QFont(T.MONO, 11))
    return make_field(label, c, parent_layout)

def make_line(text, parent_layout, label, mono=False):
    e = QLineEdit(text)
    e.setFont(QFont(T.MONO if mono else T.UI, 11))
    return make_field(label, e, parent_layout)

# ═══════════════════════════════════════════════════════════════
#  VISUAL CANVAS — place pins, LEDs, display regions on image
# ═══════════════════════════════════════════════════════════════
class VisualCanvas(QWidget):
    pinPlaced = pyqtSignal(int, int)
    ledPlaced = pyqtSignal(int, int)
    displayDrawn = pyqtSignal(int, int, int, int)
    itemClicked = pyqtSignal(str, int)  # type ("pin"/"led"), index

    def __init__(self, main_win):
        super().__init__()
        self.mw = main_win
        self.setMouseTracking(True)
        self.tool = "select"  # select | pin | led | display
        self.zoom = 2
        self.image = None  # QImage
        self.image_path = None
        self._drag_start = None  # for display region drawing

    def set_image(self, img: QImage, path: str):
        self.image = img
        self.image_path = path
        self.update()

    def clear_image(self):
        self.image = None
        self.image_path = None
        self.update()

    def _to_dev(self, pos):
        return QPoint(int(pos.x() / self.zoom), int(pos.y() / self.zoom))

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        p = self._to_dev(e.pos())
        x, y = p.x(), p.y()
        mw = self.mw

        if self.tool == "pin":
            self.pinPlaced.emit(x, y)
        elif self.tool == "led":
            self.ledPlaced.emit(x, y)
        elif self.tool == "display":
            self._drag_start = (x, y)
        else:
            # Select: find pin or led near click
            for i, pin in enumerate(mw.pins):
                if math.hypot(x - pin["x"], y - pin["y"]) < 8:
                    self.itemClicked.emit("pin", i); return
            for i, led in enumerate(mw.leds):
                if math.hypot(x - led["x"], y - led["y"]) < led.get("radius", 8) + 2:
                    self.itemClicked.emit("led", i); return
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
            self.update()

    def mouseMoveEvent(self, e):
        if self._drag_start:
            self._drag_end = self._to_dev(e.pos())
            self.update()
        self.update()

    def paintEvent(self, event):
        mw = self.mw
        dw, dh = mw.dev_w.value(), mw.dev_h.value()
        cw, ch = dw * self.zoom, dh * self.zoom

        self.setMinimumSize(cw, ch)
        self.setMaximumSize(cw, ch)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(self.zoom, self.zoom)

        # Checkerboard
        cs = 8
        for gx in range(0, dw, cs):
            for gy in range(0, dh, cs):
                p.fillRect(gx, gy, cs, cs, QColor("#222" if (gx // cs + gy // cs) % 2 == 0 else "#1a1a1a"))

        # Image
        if self.image:
            p.drawImage(QRectF(0, 0, dw, dh), self.image)
        else:
            p.fillRect(0, 0, dw, dh, QColor(mw.dev_color.text()))
            p.setPen(QColor(T.textMut))
            p.setFont(QFont(T.MONO, 10))
            p.drawText(QRectF(0, 0, dw, dh), Qt.AlignCenter, "No image\nUpload one →")

        # Display region
        if mw.has_display.isChecked():
            dr = mw.disp_region
            p.fillRect(QRectF(dr["x"], dr["y"], dr["w"], dr["h"]), QColor(mw.disp_bg.text()))
            p.setPen(QPen(QColor(T.accent + "88"), 1, Qt.DashLine))
            p.drawRect(QRectF(dr["x"], dr["y"], dr["w"], dr["h"]))
            p.setPen(QColor(T.accent + "55"))
            p.setFont(QFont(T.MONO, 7))
            p.drawText(QRectF(dr["x"], dr["y"], dr["w"], dr["h"]), Qt.AlignCenter,
                        f'{mw.disp_px_w.value()}×{mw.disp_px_h.value()}')

        # Drawing region preview
        if self._drag_start and hasattr(self, '_drag_end'):
            x0, y0 = self._drag_start
            x1, y1 = self._drag_end.x(), self._drag_end.y()
            rx, ry = min(x0, x1), min(y0, y1)
            rw, rh = abs(x1 - x0), abs(y1 - y0)
            p.setPen(QPen(QColor(T.accent), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(rx, ry, rw, rh))

        # LED indicators
        test_state = mw.test_state if mw.test_running else {}
        for i, led in enumerate(mw.leds):
            is_on = mw.test_running and test_state.get(led.get("state_var")) == led.get("on_value", True)
            lx, ly, lr = led["x"], led["y"], led.get("radius", 8)
            lc = QColor(led.get("color", "#ff3344"))
            is_sel = mw.sel_type == "led" and mw.sel_idx == i

            if is_on:
                grad = QRadialGradient(lx, ly, lr * 3)
                grad.setColorAt(0, QColor(lc.red(), lc.green(), lc.blue(), 200))
                grad.setColorAt(1, QColor(lc.red(), lc.green(), lc.blue(), 0))
                p.setBrush(QBrush(grad)); p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(lx, ly), lr * 3, lr * 3)

            fill = QColor(lc) if is_on else QColor(lc.red() // 4, lc.green() // 4, lc.blue() // 4, 120)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor("#ffaa22") if is_sel else QColor(lc.red() // 2, lc.green() // 2, lc.blue() // 2), 2 if is_sel else 1))
            p.drawEllipse(QPointF(lx, ly), lr, lr)
            p.setPen(QColor(T.text)); p.setFont(QFont(T.MONO, 6, QFont.Bold))
            p.drawText(QPointF(lx - 8, ly - lr - 3), led.get("label", "?"))

        # Pins
        mouse = self._to_dev(self.mapFromGlobal(QCursor.pos()))
        for i, pin in enumerate(mw.pins):
            pc = QColor(PIN_CLR.get(pin.get("type", "digital"), "#8b949e"))
            is_sel = mw.sel_type == "pin" and mw.sel_idx == i
            is_hov = math.hypot(mouse.x() - pin["x"], mouse.y() - pin["y"]) < 8
            r = 6 if (is_hov or is_sel) else 4

            p.setBrush(QBrush(QColor(T.accent) if is_hov else QColor("#fff") if is_sel else pc))
            p.setPen(QPen(QColor("#ffaa22") if is_sel else QColor(T.accent + "88") if is_hov else QColor(pc.red(), pc.green(), pc.blue(), 80), 2 if is_sel else 1))
            p.drawEllipse(QPointF(pin["x"], pin["y"]), r, r)

            # Direction arrow
            dirs = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}
            dx, dy = dirs.get(pin.get("side", "left"), (0, 0))
            p.setPen(QPen(QColor(pc.red(), pc.green(), pc.blue(), 100), 1.5))
            p.drawLine(QPointF(pin["x"], pin["y"]), QPointF(pin["x"] + dx * 8, pin["y"] + dy * 8))

            # Label
            p.setPen(QColor(T.text)); p.setFont(QFont(T.MONO, 6, QFont.Bold))
            p.drawText(QPointF(pin["x"] - 8, pin["y"] - 7), pin.get("label", "?"))

            # Hover tooltip
            if is_hov:
                txt = f'{pin.get("label", "?")} ({pin.get("type", "?")})'
                fm = QFontMetrics(QFont(T.MONO, 7))
                tw = fm.horizontalAdvance(txt) + 10
                p.setBrush(QBrush(QColor(0, 0, 0, 200))); p.setPen(Qt.NoPen)
                p.drawRoundedRect(QRectF(pin["x"] - tw / 2, pin["y"] - 26, tw, 14), 3, 3)
                p.setPen(QColor("#fff")); p.setFont(QFont(T.MONO, 7, QFont.Bold))
                p.drawText(QRectF(pin["x"] - tw / 2, pin["y"] - 26, tw, 14), Qt.AlignCenter, txt)

        p.end()


# ═══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════
DEFAULT_EMU = '''{
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
}'''


class DeviceCreator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArduSim — Device Creator")
        self.setMinimumSize(1000, 650)
        self.resize(1300, 800)
        self.setStyleSheet(SS)

        # Data
        self.pins = []
        self.leds = []
        self.disp_region = {"x": 10, "y": 10, "w": 80, "h": 40}
        self.image_b64 = None
        self.sel_type = "none"  # "pin" / "led" / "none"
        self.sel_idx = -1
        self.test_running = False
        self.test_state = {}
        self.test_tick = 0

        self.test_timer = QTimer()
        self.test_timer.setInterval(500)
        self.test_timer.timeout.connect(self._test_tick)

        self._build_ui()
        self._build_status()

    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        ml = QVBoxLayout(cw)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # Top toolbar
        tb = QHBoxLayout()
        tb.setContentsMargins(8, 6, 8, 6)
        tb.setSpacing(6)
        bar = QWidget()
        bar.setLayout(tb)
        bar.setStyleSheet("background:" + T.panel + ";border-bottom:1px solid " + T.border)
        bar.setFixedHeight(40)

        lbl = QLabel("ArduSim")
        lbl.setFont(QFont(T.MONO, 13, QFont.Bold))
        lbl.setStyleSheet("color:" + T.accent + ";letter-spacing:1px")
        tb.addWidget(lbl)
        lbl2 = QLabel("Device Creator")
        lbl2.setFont(QFont(T.MONO, 10))
        lbl2.setStyleSheet("color:" + T.textMut)
        tb.addWidget(lbl2)
        tb.addSpacing(12)

        btn_import = QPushButton("Import .adev")
        btn_import.clicked.connect(self._import_adev)
        tb.addWidget(btn_import)

        tb.addStretch()

        btn_export = QPushButton("⬇ Export .adev")
        btn_export.setStyleSheet("QPushButton{background:" + T.accentDim + ";color:" + T.accent + ";border:1px solid " + T.accent + "44;border-radius:3px;padding:5px 16px;font-weight:bold}QPushButton:hover{background:" + T.accent + ";color:#000}")
        btn_export.clicked.connect(self._export)
        tb.addWidget(btn_export)

        ml.addWidget(bar)

        # Tab widget
        self.tabs = QTabWidget()
        ml.addWidget(self.tabs)

        # ── Tab 1: Info ──
        self._build_info_tab()

        # ── Tab 2: Visual ──
        self._build_visual_tab()

        # ── Tab 3: Emulation ──
        self._build_emu_tab()

        # ── Tab 4: Preview ──
        self._build_preview_tab()

        # ── Tab 5: Export ──
        self._build_export_tab()

    # ─────────────────────────────────────────────────────────
    # TAB 1: DEVICE INFO
    # ─────────────────────────────────────────────────────────
    def _build_info_tab(self):
        w = QWidget()
        scroll = QScrollArea(); scroll.setWidget(w); scroll.setWidgetResizable(True)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(4)

        hdr = QLabel("Device Information")
        hdr.setFont(QFont(T.UI, 16, QFont.Bold))
        lay.addWidget(hdr)
        lay.addSpacing(8)

        self.dev_id = make_line("my_device", lay, "DEVICE ID", mono=True)
        self.dev_name = make_line("My Device", lay, "NAME")
        self.dev_category = make_combo(CATEGORIES, "Output", lay, "CATEGORY")
        lbl_d = QLabel("DESCRIPTION"); lbl_d.setFont(QFont(T.MONO, 9, QFont.Bold)); lbl_d.setStyleSheet("color:" + T.textMut + ";letter-spacing:1px;margin-top:4px")
        lay.addWidget(lbl_d)
        self.dev_desc = QPlainTextEdit()
        self.dev_desc.setMaximumHeight(70)
        self.dev_desc.setFont(QFont(T.UI, 11))
        lay.addWidget(self.dev_desc)

        row = QHBoxLayout()
        vl = QVBoxLayout()
        self.dev_author = make_line("", vl, "AUTHOR")
        row.addLayout(vl)
        vr = QVBoxLayout()
        self.dev_version = make_line("1.0", vr, "VERSION", mono=True)
        row.addLayout(vr)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        vl2 = QVBoxLayout()
        self.dev_w = make_spin(100, 10, 2000, vl2, "CANVAS WIDTH")
        row2.addLayout(vl2)
        vr2 = QVBoxLayout()
        self.dev_h = make_spin(100, 10, 2000, vr2, "CANVAS HEIGHT")
        row2.addLayout(vr2)
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        vl3 = QVBoxLayout()
        self.dev_label = make_line("DEV", vl3, "LABEL", mono=True)
        row3.addLayout(vl3)
        vr3 = QVBoxLayout()
        l_c = QLabel("COLOR"); l_c.setFont(QFont(T.MONO, 9, QFont.Bold)); l_c.setStyleSheet("color:" + T.textMut + ";letter-spacing:1px;margin-top:4px")
        vr3.addWidget(l_c)
        ch = QHBoxLayout()
        self.dev_color = QLineEdit("#555555")
        self.dev_color.setFont(QFont(T.MONO, 11))
        self.color_btn = QPushButton("  ")
        self.color_btn.setFixedSize(28, 28)
        self.color_btn.setStyleSheet("background:#555555;border:1px solid " + T.border + ";border-radius:3px")
        self.color_btn.clicked.connect(self._pick_color)
        self.dev_color.textChanged.connect(lambda t: self.color_btn.setStyleSheet(f"background:{t};border:1px solid {T.border};border-radius:3px"))
        ch.addWidget(self.color_btn); ch.addWidget(self.dev_color)
        vr3.addLayout(ch)
        row3.addLayout(vr3)
        lay.addLayout(row3)
        lay.addStretch()

        self.tabs.addTab(scroll, "Info")

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.dev_color.text()), self, "Device Color")
        if c.isValid(): self.dev_color.setText(c.name())

    # ─────────────────────────────────────────────────────────
    # TAB 2: VISUAL EDITOR
    # ─────────────────────────────────────────────────────────
    def _build_visual_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left: canvas with toolbar
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        # Canvas toolbar
        ctb = QHBoxLayout()
        ctb.setContentsMargins(8, 4, 8, 4)
        ctb.setSpacing(4)
        ctb_w = QWidget()
        ctb_w.setLayout(ctb)
        ctb_w.setStyleSheet("background:" + T.panelAlt + ";border-bottom:1px solid " + T.border)
        ctb_w.setFixedHeight(34)

        self.vtool_btns = {}
        for tid, label in [("select", "↖ Select"), ("pin", "● Pin"), ("led", "◉ LED"), ("display", "▢ Display")]:
            b = QPushButton(label)
            b.setCheckable(True); b.setChecked(tid == "select")
            b.setFont(QFont(T.MONO, 10))
            b.clicked.connect(lambda _, t=tid: self._set_vtool(t))
            ctb.addWidget(b)
            self.vtool_btns[tid] = b

        ctb.addSpacing(8)
        lbl_z = QLabel("Zoom:")
        lbl_z.setFont(QFont(T.MONO, 9))
        lbl_z.setStyleSheet("color:" + T.textMut)
        ctb.addWidget(lbl_z)
        for z in [1, 2, 3, 4]:
            b = QPushButton(f"{z}x")
            b.setFixedWidth(32)
            b.setFont(QFont(T.MONO, 9))
            b.clicked.connect(lambda _, zz=z: self._set_zoom(zz))
            ctb.addWidget(b)

        ctb.addSpacing(8)
        btn_img = QPushButton("Upload Image")
        btn_img.clicked.connect(self._upload_image)
        ctb.addWidget(btn_img)
        btn_rm_img = QPushButton("Remove Image")
        btn_rm_img.setStyleSheet("QPushButton{color:" + T.red + "}")
        btn_rm_img.clicked.connect(self._remove_image)
        ctb.addWidget(btn_rm_img)

        ctb.addStretch()
        self.vis_info = QLabel("100×100 · 0 pins · 0 LEDs")
        self.vis_info.setFont(QFont(T.MONO, 9))
        self.vis_info.setStyleSheet("color:" + T.textMut)
        ctb.addWidget(self.vis_info)

        ll.addWidget(ctb_w)

        # Canvas scroll area
        self.canvas = VisualCanvas(self)
        self.canvas.pinPlaced.connect(self._on_pin_placed)
        self.canvas.ledPlaced.connect(self._on_led_placed)
        self.canvas.displayDrawn.connect(self._on_display_drawn)
        self.canvas.itemClicked.connect(self._on_item_clicked)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("background:#111;border:none")
        ll.addWidget(scroll)
        layout.addWidget(left, 1)

        # Right: property panel
        right = QWidget()
        right.setFixedWidth(270)
        right.setStyleSheet("background:" + T.panel + ";border-left:1px solid " + T.border)
        self.prop_layout = QVBoxLayout(right)
        self.prop_layout.setContentsMargins(10, 10, 10, 10)
        self.prop_layout.setSpacing(4)

        self.prop_stack = QStackedWidget()
        self.prop_layout.addWidget(self.prop_stack)

        # Page 0: overview
        self._build_overview_page()
        # Page 1: pin editor
        self._build_pin_editor_page()
        # Page 2: led editor
        self._build_led_editor_page()

        self.prop_stack.setCurrentIndex(0)
        layout.addWidget(right)
        self.tabs.addTab(w, "Visual")

    def _build_overview_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        # Pin list
        l1 = QLabel("PINS")
        l1.setFont(QFont(T.MONO, 9, QFont.Bold))
        l1.setStyleSheet("color:" + T.textMut + ";letter-spacing:1.5px")
        lay.addWidget(l1)
        self.pin_list = QListWidget()
        self.pin_list.setMaximumHeight(180)
        self.pin_list.currentRowChanged.connect(lambda i: self._on_item_clicked("pin", i) if i >= 0 else None)
        lay.addWidget(self.pin_list)

        # LED list
        l2 = QLabel("LED INDICATORS")
        l2.setFont(QFont(T.MONO, 9, QFont.Bold))
        l2.setStyleSheet("color:" + T.textMut + ";letter-spacing:1.5px;margin-top:8px")
        lay.addWidget(l2)
        self.led_list = QListWidget()
        self.led_list.setMaximumHeight(120)
        self.led_list.currentRowChanged.connect(lambda i: self._on_item_clicked("led", i) if i >= 0 else None)
        lay.addWidget(self.led_list)

        # Display
        l3 = QLabel("DISPLAY REGION")
        l3.setFont(QFont(T.MONO, 9, QFont.Bold))
        l3.setStyleSheet("color:" + T.textMut + ";letter-spacing:1.5px;margin-top:8px")
        lay.addWidget(l3)
        self.has_display = QCheckBox("Has display region")
        self.has_display.setStyleSheet("color:" + T.textSec)
        self.has_display.toggled.connect(lambda: self.canvas.update())
        lay.addWidget(self.has_display)
        dg = QWidget()
        dl = QVBoxLayout(dg)
        dl.setContentsMargins(0, 4, 0, 0)
        dl.setSpacing(4)
        self.disp_type = make_line("oled_ssd1306", dl, "TYPE", mono=True)
        r1 = QHBoxLayout()
        v1 = QVBoxLayout(); self.disp_px_w = make_spin(128, 1, 4096, v1, "PX W"); r1.addLayout(v1)
        v2 = QVBoxLayout(); self.disp_px_h = make_spin(64, 1, 4096, v2, "PX H"); r1.addLayout(v2)
        dl.addLayout(r1)
        r2 = QHBoxLayout()
        v3 = QVBoxLayout(); self.disp_color = make_line("#00aaff", v3, "PIXEL CLR", mono=True); r2.addLayout(v3)
        v4 = QVBoxLayout(); self.disp_bg = make_line("#000510", v4, "BG CLR", mono=True); r2.addLayout(v4)
        dl.addLayout(r2)
        r3 = QHBoxLayout()
        v5 = QVBoxLayout(); self.disp_iface = make_combo(["i2c", "spi", "parallel"], "i2c", v5, "INTERFACE"); r3.addLayout(v5)
        v6 = QVBoxLayout(); self.disp_addr = make_line("0x3C", v6, "ADDR", mono=True); r3.addLayout(v6)
        dl.addLayout(r3)
        lay.addWidget(dg)
        lay.addStretch()

        hint = QLabel("Click a pin/LED to edit it.\nUse toolbar tools to place new items.")
        hint.setFont(QFont(T.UI, 9))
        hint.setStyleSheet("color:" + T.textMut + ";padding:8px 0;border-top:1px solid " + T.border)
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.prop_stack.addWidget(page)

    def _build_pin_editor_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        l = QLabel("Pin Properties"); l.setFont(QFont(T.UI, 12, QFont.Bold))
        hdr.addWidget(l)
        btn_back = QPushButton("← Back")
        btn_back.clicked.connect(lambda: self._deselect())
        hdr.addWidget(btn_back)
        lay.addLayout(hdr)

        self.pe_id = make_line("", lay, "ID", mono=True)
        self.pe_label = make_line("", lay, "LABEL", mono=True)
        r = QHBoxLayout()
        v1 = QVBoxLayout(); self.pe_x = make_spin(0, -9999, 9999, v1, "X"); r.addLayout(v1)
        v2 = QVBoxLayout(); self.pe_y = make_spin(0, -9999, 9999, v2, "Y"); r.addLayout(v2)
        lay.addLayout(r)
        self.pe_type = make_combo(PIN_TYPES, "digital", lay, "TYPE")
        self.pe_dir = make_combo(PIN_DIRS, "io", lay, "DIRECTION")
        self.pe_side = make_combo(PIN_SIDES, "left", lay, "SIDE")
        self.pe_notes = make_line("", lay, "NOTES")

        # Connect changes
        for widget, field in [(self.pe_id, "id"), (self.pe_label, "label"), (self.pe_notes, "notes")]:
            widget.textChanged.connect(lambda v, f=field: self._upd_pin(f, v))
        for widget, field in [(self.pe_x, "x"), (self.pe_y, "y")]:
            widget.valueChanged.connect(lambda v, f=field: self._upd_pin(f, v))
        for widget, field in [(self.pe_type, "type"), (self.pe_dir, "direction"), (self.pe_side, "side")]:
            widget.currentTextChanged.connect(lambda v, f=field: self._upd_pin(f, v))

        lay.addSpacing(8)
        btn_del = QPushButton("Delete Pin")
        btn_del.setStyleSheet("QPushButton{color:" + T.red + ";border-color:" + T.red + "44}")
        btn_del.clicked.connect(self._delete_sel_pin)
        lay.addWidget(btn_del)
        lay.addStretch()

        self.prop_stack.addWidget(page)

    def _build_led_editor_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        l = QLabel("LED Indicator"); l.setFont(QFont(T.UI, 12, QFont.Bold))
        hdr.addWidget(l)
        btn_back = QPushButton("← Back")
        btn_back.clicked.connect(lambda: self._deselect())
        hdr.addWidget(btn_back)
        lay.addLayout(hdr)

        self.le_label = make_line("", lay, "LABEL", mono=True)
        r = QHBoxLayout()
        v1 = QVBoxLayout(); self.le_x = make_spin(0, -9999, 9999, v1, "X"); r.addLayout(v1)
        v2 = QVBoxLayout(); self.le_y = make_spin(0, -9999, 9999, v2, "Y"); r.addLayout(v2)
        lay.addLayout(r)
        self.le_radius = make_spin(8, 1, 100, lay, "RADIUS")

        l_c = QLabel("COLOR"); l_c.setFont(QFont(T.MONO, 9, QFont.Bold)); l_c.setStyleSheet("color:" + T.textMut + ";letter-spacing:1px;margin-top:4px")
        lay.addWidget(l_c)
        ch = QHBoxLayout()
        self.le_color_btn = QPushButton("  ")
        self.le_color_btn.setFixedSize(28, 28)
        self.le_color_btn.clicked.connect(self._pick_led_color)
        ch.addWidget(self.le_color_btn)
        self.le_color = QLineEdit("#ff3344")
        self.le_color.setFont(QFont(T.MONO, 11))
        self.le_color.textChanged.connect(lambda t: self.le_color_btn.setStyleSheet(f"background:{t};border:1px solid {T.border};border-radius:3px"))
        ch.addWidget(self.le_color)
        lay.addLayout(ch)

        self.le_state_var = make_line("led_on", lay, "STATE VARIABLE", mono=True)
        self.le_on_value = make_line("true", lay, "ON VALUE", mono=True)

        info = QLabel()
        info.setFont(QFont(T.UI, 9))
        info.setStyleSheet("color:" + T.textSec + ";background:" + T.bg + ";padding:8px;border:1px solid " + T.border + ";border-radius:3px;margin-top:6px")
        info.setWordWrap(True)
        info.setText("This LED lights up when the emulation\nstate variable matches the ON value.")
        lay.addWidget(info)

        for widget, field in [(self.le_label, "label"), (self.le_color, "color"), (self.le_state_var, "state_var"), (self.le_on_value, "on_value_str")]:
            widget.textChanged.connect(lambda v, f=field: self._upd_led(f, v))
        for widget, field in [(self.le_x, "x"), (self.le_y, "y"), (self.le_radius, "radius")]:
            widget.valueChanged.connect(lambda v, f=field: self._upd_led(f, v))

        lay.addSpacing(8)
        btn_del = QPushButton("Delete LED")
        btn_del.setStyleSheet("QPushButton{color:" + T.red + ";border-color:" + T.red + "44}")
        btn_del.clicked.connect(self._delete_sel_led)
        lay.addWidget(btn_del)
        lay.addStretch()

        self.prop_stack.addWidget(page)

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

        tb = QHBoxLayout()
        tb.setContentsMargins(8, 4, 8, 4)
        tbw = QWidget(); tbw.setLayout(tb)
        tbw.setStyleSheet("background:" + T.panelAlt + ";border-bottom:1px solid " + T.border)
        tbw.setFixedHeight(30)
        lbl = QLabel("emulation.json"); lbl.setFont(QFont(T.MONO, 10)); lbl.setStyleSheet("color:" + T.textMut)
        tb.addWidget(lbl); tb.addStretch()
        self.emu_status = QLabel("✓ Valid"); self.emu_status.setFont(QFont(T.MONO, 10)); self.emu_status.setStyleSheet("color:" + T.green)
        tb.addWidget(self.emu_status)
        btn_fmt = QPushButton("Format")
        btn_fmt.clicked.connect(self._format_emu)
        tb.addWidget(btn_fmt)
        ll.addWidget(tbw)

        self.emu_editor = QPlainTextEdit()
        self.emu_editor.setPlainText(DEFAULT_EMU)
        self.emu_editor.setFont(QFont(T.MONO, 12))
        self.emu_editor.textChanged.connect(self._validate_emu)
        ll.addWidget(self.emu_editor)
        layout.addWidget(left, 1)

        # Reference panel
        right = QWidget()
        right.setFixedWidth(220)
        right.setStyleSheet("background:" + T.panel + ";border-left:1px solid " + T.border)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 10, 10, 10)
        rl.setSpacing(6)

        for title, items in [
            ("TRIGGERS", ["pin_high", "pin_low", "pin_pwm", "analog_read", "user_press",
                           "user_release", "user_adjust", "tone", "no_tone", "i2c_command",
                           "i2c_data", "display_print", "display_clear", "circuit_update", "servo_write"]),
            ("ACTIONS", ["set_state", "compute", "return_value", "visual_update",
                         "render_text", "set_pixel", "clear_framebuffer", "process_command"]),
        ]:
            l = QLabel(title); l.setFont(QFont(T.MONO, 9, QFont.Bold)); l.setStyleSheet("color:" + T.textMut + ";letter-spacing:1.5px")
            rl.addWidget(l)
            lw = QListWidget(); lw.setMaximumHeight(min(120, len(items) * 22))
            for item in items: lw.addItem(item)
            lw.setFont(QFont(T.MONO, 10))
            rl.addWidget(lw)

        l = QLabel("YOUR PINS"); l.setFont(QFont(T.MONO, 9, QFont.Bold)); l.setStyleSheet("color:" + T.textMut + ";letter-spacing:1.5px")
        rl.addWidget(l)
        self.emu_pin_list = QListWidget(); self.emu_pin_list.setMaximumHeight(100)
        self.emu_pin_list.setFont(QFont(T.MONO, 10))
        rl.addWidget(self.emu_pin_list)
        rl.addStretch()

        layout.addWidget(right)
        self.tabs.addTab(w, "Emulation")

    def _validate_emu(self):
        try:
            json.loads(self.emu_editor.toPlainText())
            self.emu_status.setText("✓ Valid")
            self.emu_status.setStyleSheet("color:" + T.green)
            return True
        except json.JSONDecodeError as e:
            self.emu_status.setText(f"✗ {e.args[0][:40]}")
            self.emu_status.setStyleSheet("color:" + T.red)
            return False

    def _format_emu(self):
        try:
            obj = json.loads(self.emu_editor.toPlainText())
            self.emu_editor.setPlainText(json.dumps(obj, indent=2))
        except:
            pass

    # ─────────────────────────────────────────────────────────
    # TAB 4: PREVIEW
    # ─────────────────────────────────────────────────────────
    def _build_preview_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tb = QHBoxLayout()
        tb.setContentsMargins(8, 4, 8, 4)
        tbw = QWidget(); tbw.setLayout(tb)
        tbw.setStyleSheet("background:" + T.panelAlt + ";border-bottom:1px solid " + T.border)
        tbw.setFixedHeight(34)
        lbl = QLabel("Live Preview"); lbl.setFont(QFont(T.MONO, 10)); lbl.setStyleSheet("color:" + T.textMut)
        tb.addWidget(lbl)
        tb.addSpacing(8)
        self.btn_test = QPushButton("▶ Test Emulation")
        self.btn_test.setStyleSheet("QPushButton{background:" + T.accentDim + ";color:" + T.accent + ";border:1px solid " + T.accent + "44}")
        self.btn_test.clicked.connect(self._toggle_test)
        tb.addWidget(self.btn_test)
        self.test_lbl = QLabel(""); self.test_lbl.setFont(QFont(T.MONO, 10)); self.test_lbl.setStyleSheet("color:" + T.green)
        tb.addWidget(self.test_lbl)
        tb.addStretch()
        layout.addWidget(tbw)

        # Preview canvas reuses VisualCanvas
        self.preview_canvas = VisualCanvas(self)
        self.preview_canvas.tool = "select"
        scroll = QScrollArea(); scroll.setWidget(self.preview_canvas)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("background:#111;border:none")
        self.preview_canvas.zoom = 3
        layout.addWidget(scroll, 1)

        # State inspector
        state_w = QWidget()
        state_w.setFixedHeight(80)
        state_w.setStyleSheet("background:" + T.panel + ";border-top:1px solid " + T.border)
        sl = QVBoxLayout(state_w)
        sl.setContentsMargins(10, 6, 10, 6)
        l = QLabel("STATE VARIABLES"); l.setFont(QFont(T.MONO, 9, QFont.Bold)); l.setStyleSheet("color:" + T.textMut + ";letter-spacing:1.5px")
        sl.addWidget(l)
        self.state_display = QLabel("No state — run test to see changes")
        self.state_display.setFont(QFont(T.MONO, 10))
        self.state_display.setStyleSheet("color:" + T.textSec)
        self.state_display.setWordWrap(True)
        sl.addWidget(self.state_display)
        layout.addWidget(state_w)

        self.tabs.addTab(w, "Preview")

    def _toggle_test(self):
        if self.test_running:
            self.test_running = False; self.test_state = {}; self.test_timer.stop()
            self.btn_test.setText("▶ Test Emulation")
            self.btn_test.setStyleSheet("QPushButton{background:" + T.accentDim + ";color:" + T.accent + ";border:1px solid " + T.accent + "44}")
            self.test_lbl.setText("")
        else:
            self.test_running = True; self.test_tick = 0; self.test_timer.start()
            self.btn_test.setText("■ Stop")
            self.btn_test.setStyleSheet("QPushButton{background:" + T.red + ";color:#fff;border:none}")
        self.canvas.update(); self.preview_canvas.update()

    def _test_tick(self):
        self.test_tick += 1
        try:
            emu = json.loads(self.emu_editor.toPlainText())
            sv = dict(emu.get("state_vars", {}))
            for rule in emu.get("rules", []):
                if rule.get("action") == "set_state" and rule.get("target"):
                    if rule.get("trigger") == "pin_high":
                        val = rule.get("value")
                        sv[rule["target"]] = val if self.test_tick % 2 == 0 else (not val if isinstance(val, bool) else 0)
            self.test_state = sv
            parts = [f"{k}: {v}" for k, v in sv.items()]
            self.state_display.setText("  |  ".join(parts) if parts else "Empty state")
        except:
            pass
        self.test_lbl.setText(f"● tick {self.test_tick}")
        self.canvas.update()
        self.preview_canvas.update()

    # ─────────────────────────────────────────────────────────
    # TAB 5: EXPORT
    # ─────────────────────────────────────────────────────────
    def _build_export_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        # Left: summary + button
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(24, 20, 24, 20)
        ll.setSpacing(8)

        hdr = QLabel("Export Device File"); hdr.setFont(QFont(T.UI, 16, QFont.Bold))
        ll.addWidget(hdr)
        ll.addSpacing(8)

        self.export_summary = QTextEdit()
        self.export_summary.setReadOnly(True)
        self.export_summary.setMaximumHeight(200)
        self.export_summary.setFont(QFont(T.MONO, 11))
        self.export_summary.setStyleSheet("background:" + T.bg + ";border:1px solid " + T.border + ";border-radius:3px;padding:8px")
        ll.addWidget(self.export_summary)

        self.export_err = QLabel("")
        self.export_err.setFont(QFont(T.MONO, 10))
        self.export_err.setStyleSheet("color:" + T.red)
        ll.addWidget(self.export_err)

        btn_exp = QPushButton("⬇  Download .adev file")
        btn_exp.setStyleSheet("QPushButton{background:" + T.accent + ";color:#000;border:none;border-radius:3px;padding:12px;font-size:14px;font-weight:bold}QPushButton:hover{background:#5ac0ff}")
        btn_exp.clicked.connect(self._export)
        ll.addWidget(btn_exp)
        ll.addStretch()
        layout.addWidget(left, 1)

        # Right: JSON preview
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        lbl = QLabel("  Output Preview")
        lbl.setFont(QFont(T.MONO, 10))
        lbl.setStyleSheet("background:" + T.panelAlt + ";color:" + T.textMut + ";padding:6px;border-bottom:1px solid " + T.border)
        rl.addWidget(lbl)
        self.export_preview = QPlainTextEdit()
        self.export_preview.setReadOnly(True)
        self.export_preview.setFont(QFont(T.MONO, 11))
        rl.addWidget(self.export_preview)
        layout.addWidget(right, 1)

        self.tabs.addTab(w, "Export")
        self.tabs.currentChanged.connect(self._on_tab_change)

    def _on_tab_change(self, idx):
        if self.tabs.tabText(idx) == "Export":
            self._update_export_preview()
        if self.tabs.tabText(idx) == "Emulation":
            self._update_emu_pin_list()

    def _update_emu_pin_list(self):
        self.emu_pin_list.clear()
        for pin in self.pins:
            self.emu_pin_list.addItem(f'{pin["id"]} ({pin["type"]})')

    def _update_export_preview(self):
        adev = self._build_adev()
        if adev:
            self.export_preview.setPlainText(json.dumps(adev, indent=2))
            self.export_summary.setPlainText(
                f'Name: {adev["device"]["name"]}\n'
                f'ID: {adev["device"]["id"]}\n'
                f'Category: {adev["device"]["category"]}\n'
                f'Size: {adev["visual"]["width"]}×{adev["visual"]["height"]}\n'
                f'Pins: {len(adev.get("pins", []))}\n'
                f'LED Indicators: {len(adev["visual"].get("led_indicators", []))}\n'
                f'Display: {"Yes" if "display" in adev else "No"}\n'
                f'Image: {"Embedded" if self.image_b64 else "None"}\n'
                f'Emulation: Valid'
            )
            self.export_err.setText("")
        else:
            self.export_err.setText("⚠ Fix emulation JSON errors before exporting.")

    # ─────────────────────────────────────────────────────────
    # STATUS BAR
    # ─────────────────────────────────────────────────────────
    def _build_status(self):
        sb = self.statusBar()
        self.st_info = QLabel("Ready")
        self.st_info.setFont(QFont(T.MONO, 10))
        sb.addWidget(self.st_info)

    # ─────────────────────────────────────────────────────────
    # VISUAL TOOL ACTIONS
    # ─────────────────────────────────────────────────────────
    def _set_vtool(self, t):
        self.canvas.tool = t
        for k, b in self.vtool_btns.items():
            b.setChecked(k == t)

    def _set_zoom(self, z):
        self.canvas.zoom = z
        self.canvas.update()

    def _upload_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Upload Device Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.svg);;All (*)")
        if not f:
            return
        img = QImage(f)
        if img.isNull():
            QMessageBox.warning(self, "Error", "Failed to load image."); return
        self.canvas.set_image(img, f)
        self.dev_w.setValue(img.width())
        self.dev_h.setValue(img.height())
        # Store base64 for export
        with open(f, "rb") as fh:
            self.image_b64 = base64.b64encode(fh.read()).decode("ascii")
        self.st_info.setText(f"Image loaded: {Path(f).name} ({img.width()}×{img.height()})")

    def _remove_image(self):
        self.canvas.clear_image()
        self.image_b64 = None

    def _on_pin_placed(self, x, y):
        idx = len(self.pins)
        pin = {"id": f"pin_{idx}", "label": f"P{idx}", "x": x, "y": y,
               "side": "left", "type": "digital", "direction": "io", "notes": ""}
        self.pins.append(pin)
        self._refresh_lists()
        self._on_item_clicked("pin", idx)
        self.canvas.update()

    def _on_led_placed(self, x, y):
        idx = len(self.leds)
        led = {"label": f"LED{idx}", "x": x, "y": y, "radius": 8,
               "color": "#ff3344", "state_var": "led_on", "on_value": True}
        self.leds.append(led)
        self._refresh_lists()
        self._on_item_clicked("led", idx)
        self.canvas.update()

    def _on_display_drawn(self, x, y, w, h):
        self.disp_region = {"x": x, "y": y, "w": w, "h": h}
        self.has_display.setChecked(True)
        self.canvas.update()

    def _on_item_clicked(self, typ, idx):
        self.sel_type = typ
        self.sel_idx = idx

        if typ == "pin" and 0 <= idx < len(self.pins):
            pin = self.pins[idx]
            self.pe_id.blockSignals(True); self.pe_id.setText(pin["id"]); self.pe_id.blockSignals(False)
            self.pe_label.blockSignals(True); self.pe_label.setText(pin["label"]); self.pe_label.blockSignals(False)
            self.pe_x.blockSignals(True); self.pe_x.setValue(pin["x"]); self.pe_x.blockSignals(False)
            self.pe_y.blockSignals(True); self.pe_y.setValue(pin["y"]); self.pe_y.blockSignals(False)
            self.pe_type.blockSignals(True); self.pe_type.setCurrentText(pin["type"]); self.pe_type.blockSignals(False)
            self.pe_dir.blockSignals(True); self.pe_dir.setCurrentText(pin["direction"]); self.pe_dir.blockSignals(False)
            self.pe_side.blockSignals(True); self.pe_side.setCurrentText(pin["side"]); self.pe_side.blockSignals(False)
            self.pe_notes.blockSignals(True); self.pe_notes.setText(pin.get("notes", "")); self.pe_notes.blockSignals(False)
            self.prop_stack.setCurrentIndex(1)
        elif typ == "led" and 0 <= idx < len(self.leds):
            led = self.leds[idx]
            self.le_label.blockSignals(True); self.le_label.setText(led["label"]); self.le_label.blockSignals(False)
            self.le_x.blockSignals(True); self.le_x.setValue(led["x"]); self.le_x.blockSignals(False)
            self.le_y.blockSignals(True); self.le_y.setValue(led["y"]); self.le_y.blockSignals(False)
            self.le_radius.blockSignals(True); self.le_radius.setValue(led.get("radius", 8)); self.le_radius.blockSignals(False)
            self.le_color.blockSignals(True); self.le_color.setText(led.get("color", "#ff3344")); self.le_color.blockSignals(False)
            self.le_color_btn.setStyleSheet(f"background:{led.get('color','#ff3344')};border:1px solid {T.border};border-radius:3px")
            self.le_state_var.blockSignals(True); self.le_state_var.setText(led.get("state_var", "")); self.le_state_var.blockSignals(False)
            ov = led.get("on_value", True)
            self.le_on_value.blockSignals(True); self.le_on_value.setText(str(ov).lower() if isinstance(ov, bool) else str(ov)); self.le_on_value.blockSignals(False)
            self.prop_stack.setCurrentIndex(2)
        else:
            self._deselect()

        self.canvas.update()
        self.preview_canvas.update()

    def _deselect(self):
        self.sel_type = "none"; self.sel_idx = -1
        self.prop_stack.setCurrentIndex(0)
        self.pin_list.clearSelection(); self.led_list.clearSelection()
        self.canvas.update()

    def _upd_pin(self, field, val):
        if self.sel_type == "pin" and 0 <= self.sel_idx < len(self.pins):
            self.pins[self.sel_idx][field] = val
            self._refresh_lists()
            self.canvas.update()

    def _upd_led(self, field, val):
        if self.sel_type == "led" and 0 <= self.sel_idx < len(self.leds):
            if field == "on_value_str":
                if val.lower() == "true": val = True
                elif val.lower() == "false": val = False
                else:
                    try: val = float(val) if "." in val else int(val)
                    except: pass
                self.leds[self.sel_idx]["on_value"] = val
            else:
                self.leds[self.sel_idx][field] = val
            self._refresh_lists()
            self.canvas.update()

    def _delete_sel_pin(self):
        if self.sel_type == "pin" and 0 <= self.sel_idx < len(self.pins):
            self.pins.pop(self.sel_idx)
            self._deselect(); self._refresh_lists(); self.canvas.update()

    def _delete_sel_led(self):
        if self.sel_type == "led" and 0 <= self.sel_idx < len(self.leds):
            self.leds.pop(self.sel_idx)
            self._deselect(); self._refresh_lists(); self.canvas.update()

    def _pick_led_color(self):
        c = QColorDialog.getColor(QColor(self.le_color.text()), self, "LED Color")
        if c.isValid(): self.le_color.setText(c.name())

    def _refresh_lists(self):
        self.pin_list.clear()
        for pin in self.pins:
            self.pin_list.addItem(f'{pin["label"]}  ({pin["type"]})  @{pin["x"]},{pin["y"]}')
        self.led_list.clear()
        for led in self.leds:
            self.led_list.addItem(f'{led["label"]}  → {led.get("state_var","?")}  {led.get("color","")}')
        self.vis_info.setText(f'{self.dev_w.value()}×{self.dev_h.value()} · {len(self.pins)} pins · {len(self.leds)} LEDs')

    # ─────────────────────────────────────────────────────────
    # BUILD .adev DICT
    # ─────────────────────────────────────────────────────────
    def _build_adev(self):
        if not self._validate_emu():
            return None
        try:
            emu = json.loads(self.emu_editor.toPlainText())
        except:
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
            "pins": [{k: v for k, v in pin.items()} for pin in self.pins],
            "emulation": emu,
        }

        if self.image_b64:
            ext = Path(self.canvas.image_path).suffix if self.canvas.image_path else ".png"
            mime = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
            adev["visual"]["image_svg"] = f"<svg xmlns='http://www.w3.org/2000/svg' width='{self.dev_w.value()}' height='{self.dev_h.value()}'><image href='data:{mime};base64,{self.image_b64}' width='{self.dev_w.value()}' height='{self.dev_h.value()}'/></svg>"

        if self.leds:
            adev["visual"]["led_indicators"] = [{
                "label": l["label"], "x": l["x"], "y": l["y"],
                "radius": l.get("radius", 8), "color": l.get("color", "#ff3344"),
                "state_var": l.get("state_var", ""), "on_value": l.get("on_value", True),
            } for l in self.leds]

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
    # EXPORT
    # ─────────────────────────────────────────────────────────
    def _export(self):
        adev = self._build_adev()
        if not adev:
            QMessageBox.warning(self, "Export Error", "Fix emulation JSON errors before exporting.")
            return

        name = self.dev_id.text() or "device"
        path, _ = QFileDialog.getSaveFileName(self, "Save Device File", f"{name}.adev", "Device Files (*.adev);;JSON (*.json);;All (*)")
        if not path:
            return

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(adev, f, indent=2)

        self.st_info.setText(f"Exported: {Path(path).name}")
        QMessageBox.information(self, "Export Complete", f"Device file saved to:\n{path}")

    # ─────────────────────────────────────────────────────────
    # IMPORT EXISTING .adev
    # ─────────────────────────────────────────────────────────
    def _import_adev(self):
        f, _ = QFileDialog.getOpenFileName(self, "Import Device File", "", "Device Files (*.adev *.json);;All (*)")
        if not f:
            return
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception as e:
            QMessageBox.warning(self, "Import Error", str(e)); return

        dev = data.get("device", {})
        vis = data.get("visual", {})
        self.dev_id.setText(dev.get("id", ""))
        self.dev_name.setText(dev.get("name", ""))
        idx = self.dev_category.findText(dev.get("category", "Other"))
        if idx >= 0: self.dev_category.setCurrentIndex(idx)
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
            idx = self.disp_iface.findText(d.get("interface", "i2c"))
            if idx >= 0: self.disp_iface.setCurrentIndex(idx)
            self.disp_addr.setText(d.get("address", "0x3C"))

        self._refresh_lists()
        self.canvas.update()
        self.st_info.setText(f"Imported: {Path(f).name}")


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
    pal.setColor(QPalette.Highlight, QColor(T.accent))
    pal.setColor(QPalette.HighlightedText, QColor("#000"))
    app.setPalette(pal)
    win = DeviceCreator()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
