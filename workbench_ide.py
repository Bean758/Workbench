#!/usr/bin/env python3
"""
Asteron Workbench — IDE & Circuit Simulator
Load .adev device files, place components, wire them,
write Arduino code, and simulate.

Install:  pip install PyQt5
Run:      python workbench_ide.py
"""
import sys
import os
import json
import math
import random
import re
import base64
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QComboBox,
    QPlainTextEdit, QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QScrollArea, QSplitter, QFileDialog, QMessageBox, QFrame,
    QSizePolicy, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QRadialGradient,
    QImage, QPalette, QFontMetrics, QPainterPath, QPixmap,
    QSyntaxHighlighter, QTextCharFormat, QIcon
)


# ═══════════════════════════════════════════════════════════════
#  THEME — Modern black with blue/red/green/orange accents
# ═══════════════════════════════════════════════════════════════
class T:
    bg = "#0c0c0e"
    panel = "#131316"
    panelAlt = "#18181c"
    surface = "#1c1c22"
    surfHov = "#242430"
    border = "#222230"
    borderL = "#2a2a38"
    blue = "#4a9eff"
    blueDim = "#1a2844"
    red = "#ff4d4d"
    green = "#44dd66"
    orange = "#ff9933"
    text = "#d4d4dc"
    textSec = "#8888a0"
    textMut = "#505068"
    # Pin colors
    pDigi = "#4a9eff"
    pAna = "#44dd66"
    pPow = "#ff4d4d"
    pGnd = "#666680"
    pSig = "#ff9933"
    pPas = "#808090"
    MONO = "Consolas"
    UI = "Segoe UI"
    R = 4


PIN_CLR = {
    "digital": T.pDigi, "analog": T.pAna, "power": T.pPow,
    "ground": T.pGnd, "gnd": T.pGnd, "signal": T.pSig, "passive": T.pPas,
    "i2c_sda": T.orange, "i2c_scl": T.orange,
    "spi_mosi": T.blue, "spi_miso": T.blue, "spi_sck": T.blue,
    "serial_tx": "#cc66ff", "serial_rx": "#cc66ff",
}

SS = (
    "QMainWindow{background:" + T.bg + "}"
    "QMenuBar{background:" + T.panel + ";color:" + T.text
    + ";border-bottom:1px solid " + T.border + ";font-size:12px}"
    "QMenuBar::item:selected{background:" + T.surfHov + "}"
    "QMenu{background:" + T.surface + ";color:" + T.text
    + ";border:1px solid " + T.border + "}"
    "QMenu::item:selected{background:" + T.blue + ";color:#000}"
    "QToolBar{background:" + T.panel + ";border-bottom:1px solid "
    + T.border + ";spacing:6px;padding:4px 8px}"
    "QStatusBar{background:" + T.panel + ";color:" + T.textMut
    + ";border-top:1px solid " + T.border + "}"
    "QSplitter::handle{background:" + T.border + ";width:2px}"
    "QTreeWidget{background:" + T.panel + ";color:" + T.text
    + ";border:none;font-size:12px;outline:none}"
    "QTreeWidget::item{padding:4px 8px;margin:1px 4px}"
    "QTreeWidget::item:hover{background:" + T.surfHov + "}"
    "QTreeWidget::item:selected{background:" + T.blueDim + ";color:" + T.blue + "}"
    "QTreeWidget::branch{background:" + T.panel + "}"
    "QTabWidget::pane{background:" + T.panel + ";border:none;border-top:1px solid "
    + T.border + "}"
    "QTabBar::tab{background:" + T.panel + ";color:" + T.textMut
    + ";padding:7px 16px;border-bottom:2px solid transparent;"
    "font-family:Consolas;font-size:11px}"
    "QTabBar::tab:selected{color:" + T.blue + ";border-bottom-color:" + T.blue + "}"
    "QTabBar::tab:hover{color:" + T.text + "}"
    "QPlainTextEdit,QTextEdit{background:" + T.bg
    + ";color:#c8c8dc;border:none;font-family:Consolas;font-size:13px;"
    "selection-background-color:rgba(74,158,255,0.25)}"
    "QPushButton{background:" + T.surface + ";color:" + T.text + ";border:1px solid "
    + T.border + ";border-radius:4px;padding:6px 14px;font-size:11px;font-weight:bold}"
    "QPushButton:hover{background:" + T.surfHov + ";border-color:" + T.blue + "}"
    "QPushButton:checked{background:" + T.blueDim + ";border-color:" + T.blue
    + ";color:" + T.blue + "}"
    "QLabel{color:" + T.text + "}"
    "QScrollBar:vertical{background:" + T.bg + ";width:8px}"
    "QScrollBar::handle:vertical{background:" + T.border
    + ";min-height:30px;border-radius:4px}"
    "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}"
)


# ═══════════════════════════════════════════════════════════════
#  DEVICE FILE LOADER
# ═══════════════════════════════════════════════════════════════
class DevPin:
    def __init__(self, d):
        self.id = d.get("id", "")
        self.label = d.get("label", "")
        self.x = d.get("x", 0)
        self.y = d.get("y", 0)
        self.side = d.get("side", "left")
        self.type = d.get("type", "digital")
        self.direction = d.get("direction", "io")
        self.notes = d.get("notes", "")


class DeviceDef:
    def __init__(self, data):
        dev = data.get("device", {})
        vis = data.get("visual", {})
        emu = data.get("emulation", {})
        self.id = dev.get("id", "?")
        self.name = dev.get("name", "?")
        self.category = dev.get("category", "Other")
        self.desc = dev.get("description", "")
        self.w = vis.get("width", 60)
        self.h = vis.get("height", 60)
        self.label = vis.get("label", self.name)
        self.color = vis.get("color", "#555")
        self.image_svg = vis.get("image_svg", None)
        self.pins = [DevPin(p) for p in data.get("pins", [])]
        self.emu_type = emu.get("type", "passive")
        self.state_vars = dict(emu.get("state_vars", {}))
        self.rules = list(emu.get("rules", []))
        self.props = dict(emu.get("properties", {}))
        self.display = data.get("display", None)
        self.leds = vis.get("led_indicators", [])
        self.raw = data

        # Parse embedded image from SVG wrapper
        self._qimage = None
        if self.image_svg:
            m = re.search(
                r"data:image/[^;]+;base64,([A-Za-z0-9+/=\s]+)",
                self.image_svg,
            )
            if m:
                try:
                    raw_bytes = base64.b64decode(m.group(1))
                    img = QImage()
                    img.loadFromData(raw_bytes)
                    if not img.isNull():
                        self._qimage = img
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════════
#  ORTHOGONAL WIRE ROUTER
# ═══════════════════════════════════════════════════════════════
def route_wire(x1, y1, s1, x2, y2, s2, existing):
    STUB = 18
    G = 8

    def snap(v):
        return round(v / G) * G

    def stub_dir(s):
        return {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}.get(s, (0, 0))

    dx1, dy1 = stub_dir(s1)
    dx2, dy2 = stub_dir(s2)
    sx, sy = snap(x1 + dx1 * STUB), snap(y1 + dy1 * STUB)
    ex, ey = snap(x2 + dx2 * STUB), snap(y2 + dy2 * STUB)
    pts = [(x1, y1), (sx, sy)]
    mx = snap((sx + ex) // 2)
    my = snap((sy + ey) // 2)

    def seg_conflict(ax, ay, bx, by):
        margin = 6
        for route in existing:
            for i in range(len(route) - 1):
                cx, cy = route[i]
                ddx, ddy = route[i + 1]
                if ay == by and cy == ddy and abs(ay - cy) < margin:
                    if min(ax, bx) < max(cx, ddx) and max(ax, bx) > min(cx, ddx):
                        return True
                if ax == bx and cx == ddx and abs(ax - cx) < margin:
                    if min(ay, by) < max(cy, ddy) and max(ay, by) > min(cy, ddy):
                        return True
        return False

    if not seg_conflict(sx, sy, mx, sy) and not seg_conflict(mx, sy, mx, ey):
        pts += [(mx, sy), (mx, ey)]
    elif not seg_conflict(sx, sy, sx, my) and not seg_conflict(sx, my, ex, my):
        pts += [(sx, my), (ex, my)]
    else:
        off = G
        done = False
        for _ in range(12):
            omx = mx + off
            if not seg_conflict(sx, sy, omx, sy) and not seg_conflict(omx, sy, omx, ey):
                pts += [(omx, sy), (omx, ey)]
                done = True
                break
            off = (-off) if off > 0 else (-off + G)
        if not done:
            pts += [(mx, sy), (mx, ey)]

    pts += [(ex, ey), (x2, y2)]

    # Clean collinear points
    clean = [pts[0]]
    for i in range(1, len(pts) - 1):
        pr = clean[-1]
        c = pts[i]
        n = pts[i + 1]
        if not ((pr[1] == c[1] == n[1]) or (pr[0] == c[0] == n[0])):
            clean.append(c)
    clean.append(pts[-1])
    return clean


# ═══════════════════════════════════════════════════════════════
#  SYNTAX HIGHLIGHTER
# ═══════════════════════════════════════════════════════════════
class ArduHL(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []

        # Keywords
        kf = QTextCharFormat()
        kf.setForeground(QColor("#c792ea"))
        kf.setFontWeight(QFont.Bold)
        keywords = [
            "void", "int", "long", "float", "double", "char", "bool", "boolean",
            "byte", "String", "unsigned", "const", "static", "return", "if", "else",
            "for", "while", "do", "switch", "case", "break", "continue", "class",
            "struct", "true", "false", "NULL", "#include", "#define",
        ]
        for kw in keywords:
            pat = rf"\b{re.escape(kw)}\b" if not kw.startswith("#") else re.escape(kw)
            self.rules.append((re.compile(pat), kf))

        # Functions / built-ins
        ff = QTextCharFormat()
        ff.setForeground(QColor("#82aaff"))
        funcs = [
            "pinMode", "digitalWrite", "digitalRead", "analogWrite", "analogRead",
            "Serial", "begin", "print", "println", "delay", "millis", "map",
            "constrain", "tone", "noTone", "INPUT", "OUTPUT", "INPUT_PULLUP",
            "HIGH", "LOW", "setup", "loop", "Servo", "attach", "write",
        ]
        for fn in funcs:
            self.rules.append((re.compile(rf"\b{fn}\b"), ff))

        # Strings
        sf = QTextCharFormat()
        sf.setForeground(QColor("#c3e88d"))
        self.rules.append((re.compile(r'"[^"]*"'), sf))

        # Numbers
        nf = QTextCharFormat()
        nf.setForeground(QColor("#f78c6c"))
        self.rules.append((re.compile(r"\b\d+\.?\d*\b"), nf))

        # Comments
        cf = QTextCharFormat()
        cf.setForeground(QColor("#546e7a"))
        self.rules.append((re.compile(r"//.*$"), cf))

    def highlightBlock(self, text):
        for pat, fmt in self.rules:
            for m in pat.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ═══════════════════════════════════════════════════════════════
#  CODE EDITOR WITH LINE NUMBERS
# ═══════════════════════════════════════════════════════════════
class LineNumArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_gutter(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.gutter = LineNumArea(self)
        self.blockCountChanged.connect(lambda _: self._upd_margins())
        self.updateRequest.connect(self._upd_gutter)
        self._upd_margins()
        self.setFont(QFont(T.MONO, 13))
        self.setTabStopDistance(
            QFontMetrics(self.font()).horizontalAdvance(" ") * 4
        )
        self.hl = ArduHL(self.document())

    def gutter_width(self):
        digits = max(1, len(str(self.blockCount())))
        return 14 + QFontMetrics(self.font()).horizontalAdvance("9") * digits

    def _upd_margins(self):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _upd_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.gutter.setGeometry(cr.left(), cr.top(), self.gutter_width(), cr.height())

    def paint_gutter(self, event):
        p = QPainter(self.gutter)
        p.fillRect(event.rect(), QColor(T.panel))
        p.setPen(QPen(QColor(T.border)))
        gw = self.gutter.width()
        p.drawLine(gw - 1, event.rect().top(), gw - 1, event.rect().bottom())

        blk = self.firstVisibleBlock()
        top = round(
            self.blockBoundingGeometry(blk).translated(self.contentOffset()).top()
        )
        bot = top + round(self.blockBoundingRect(blk).height())
        p.setFont(QFont(T.MONO, 9))
        fh = self.fontMetrics().height()

        while blk.isValid() and top <= event.rect().bottom():
            if blk.isVisible() and bot >= event.rect().top():
                p.setPen(QColor(T.textMut))
                p.drawText(0, top, gw - 6, fh, Qt.AlignRight, str(blk.blockNumber() + 1))
            blk = blk.next()
            top = bot
            bot = top + round(self.blockBoundingRect(blk).height())


# ═══════════════════════════════════════════════════════════════
#  CIRCUIT CANVAS
# ═══════════════════════════════════════════════════════════════
_uid = 0


def nid():
    global _uid
    _uid += 1
    return f"i{_uid}"


class CircuitCanvas(QWidget):
    selectionChanged = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.instances = []
        self.wires = []
        self.routes = {}
        self.camera = QPointF(0, 0)
        self.zoom_level = 1.0
        self.selected = None
        self.tool = "select"
        self.dragging = None
        self.panning = None
        self.connecting = None
        self.mouse_world = QPointF(0, 0)
        self.sim_running = False

    def to_world(self, pos):
        return QPointF(
            pos.x() / self.zoom_level - self.camera.x(),
            pos.y() / self.zoom_level - self.camera.y(),
        )

    def add_instance(self, dev):
        inst = {
            "id": nid(),
            "dev": dev,
            "x": -self.camera.x() + 300 + random.randint(-60, 60),
            "y": -self.camera.y() + 200 + random.randint(-60, 60),
            "state": dict(dev.state_vars),
        }
        self.instances.append(inst)
        self.selected = inst["id"]
        self.recompute_routes()
        self.update()
        return inst

    def delete_selected(self):
        if not self.selected:
            return
        self.instances = [i for i in self.instances if i["id"] != self.selected]
        self.wires = [
            w for w in self.wires
            if w["from"][0] != self.selected and w["to"][0] != self.selected
        ]
        self.selected = None
        self.recompute_routes()
        self.update()

    def find_pin_at(self, wx, wy):
        for inst in reversed(self.instances):
            for pin in inst["dev"].pins:
                px = inst["x"] + pin.x
                py = inst["y"] + pin.y
                if math.hypot(wx - px, wy - py) < 9 * max(1, 1 / self.zoom_level):
                    return inst["id"], pin, px, py
        return None

    def find_inst_at(self, wx, wy):
        for inst in reversed(self.instances):
            d = inst["dev"]
            if inst["x"] <= wx <= inst["x"] + d.w and inst["y"] <= wy <= inst["y"] + d.h:
                return inst
        return None

    def recompute_routes(self):
        self.routes = {}
        done = []
        for w in self.wires:
            fi = next((i for i in self.instances if i["id"] == w["from"][0]), None)
            ti = next((i for i in self.instances if i["id"] == w["to"][0]), None)
            if not fi or not ti:
                continue
            fp = next((p for p in fi["dev"].pins if p.id == w["from"][1]), None)
            tp = next((p for p in ti["dev"].pins if p.id == w["to"][1]), None)
            if not fp or not tp:
                continue
            route = route_wire(
                fi["x"] + fp.x, fi["y"] + fp.y, fp.side,
                ti["x"] + tp.x, ti["y"] + tp.y, tp.side,
                done,
            )
            self.routes[w["id"]] = route
            done.append(route)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(0, 0, W, H, QColor(T.bg))
        p.save()
        p.scale(self.zoom_level, self.zoom_level)
        p.translate(self.camera)

        # Grid dots
        sp = 20
        p.setPen(QPen(QColor("#ffffff0d"), 1))
        vw = W / self.zoom_level
        vh = H / self.zoom_level
        cx, cy = self.camera.x(), self.camera.y()
        x0 = int(-cx / sp) * sp - sp
        y0 = int(-cy / sp) * sp - sp
        gx = x0
        while gx < -cx + vw + sp:
            gy = y0
            while gy < -cy + vh + sp:
                p.drawPoint(QPointF(gx, gy))
                gy += sp
            gx += sp

        # Wires
        for wid, route in self.routes.items():
            if len(route) < 2:
                continue
            col = QColor(T.green) if self.sim_running else QColor(T.blue)
            p.setPen(QPen(col, 2.5, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
            path = QPainterPath()
            path.moveTo(route[0][0], route[0][1])
            for pt in route[1:]:
                path.lineTo(pt[0], pt[1])
            p.drawPath(path)
            # Junction dots
            p.setBrush(QBrush(col))
            p.setPen(Qt.NoPen)
            for pt in route:
                p.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        # Wire-in-progress preview
        if self.connecting:
            cx0, cy0 = self.connecting[2], self.connecting[3]
            mx_w, my_w = self.mouse_world.x(), self.mouse_world.y()
            preview = route_wire(
                cx0, cy0, self.connecting[1].side,
                mx_w, my_w, "left",
                list(self.routes.values()),
            )
            p.setPen(QPen(QColor(T.orange), 1.5, Qt.DashLine))
            path = QPainterPath()
            path.moveTo(preview[0][0], preview[0][1])
            for pt in preview[1:]:
                path.lineTo(pt[0], pt[1])
            p.drawPath(path)
            p.setBrush(QBrush(QColor(T.orange)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx0, cy0), 5, 5)

        # Instances
        for inst in self.instances:
            dev = inst["dev"]
            ix, iy = inst["x"], inst["y"]
            p.save()
            p.translate(ix, iy)

            # Selection highlight
            if inst["id"] == self.selected:
                p.setPen(QPen(QColor(T.blue), 1.5, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(-5, -5, dev.w + 10, dev.h + 10), 4, 4)

            is_board = dev.emu_type == "microcontroller"

            # Render device
            if dev._qimage:
                p.drawImage(QRectF(0, 0, dev.w, dev.h), dev._qimage)
            elif is_board:
                p.setBrush(QBrush(QColor("#0b3d1a")))
                p.setPen(QPen(QColor("#1a7a3a"), 1.5))
                p.drawRoundedRect(QRectF(8, 0, dev.w - 16, dev.h), 4, 4)
                p.setBrush(QBrush(QColor("#081410")))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(QRectF(14, 6, dev.w - 28, 24), 2, 2)
                p.setPen(QColor(T.blue))
                p.setFont(QFont(T.MONO, 10, QFont.Bold))
                p.drawText(QRectF(14, 6, dev.w - 28, 24), Qt.AlignCenter, dev.label)
                # Chip
                cw = min(50, dev.w * 0.35)
                ch_ = min(80, dev.h * 0.28)
                p.setBrush(QBrush(QColor("#0a0a0a")))
                p.setPen(QPen(QColor("#2a2a2a"), 0.8))
                p.drawRect(QRectF((dev.w - cw) / 2, dev.h * 0.32, cw, ch_))
                # USB
                p.setBrush(QBrush(QColor("#222")))
                p.setPen(QPen(QColor("#444"), 0.8))
                p.drawRoundedRect(QRectF((dev.w - 36) / 2, dev.h - 14, 36, 14), 2, 2)
                p.setPen(QColor(T.textMut))
                p.setFont(QFont(T.MONO, 7))
                p.drawText(
                    QRectF((dev.w - 36) / 2, dev.h - 14, 36, 14),
                    Qt.AlignCenter, "USB",
                )
            elif dev.display:
                p.setBrush(QBrush(QColor("#111418")))
                p.setPen(QPen(QColor("#2a2d33"), 1))
                p.drawRoundedRect(QRectF(0, 0, dev.w, dev.h), T.R, T.R)
                dr = dev.display.get("region", {})
                rx = dr.get("x", 4)
                ry = dr.get("y", 4)
                rw = dr.get("w", dev.w - 8)
                rh = dr.get("h", dev.h - 16)
                p.setBrush(QBrush(QColor(dev.display.get("background_color", "#000510"))))
                p.setPen(Qt.NoPen)
                p.drawRect(QRectF(rx, ry, rw, rh))
                p.setPen(QColor(T.textMut))
                p.setFont(QFont(T.MONO, 7))
                p.drawText(QRectF(0, dev.h - 12, dev.w, 12), Qt.AlignCenter, dev.label)
            else:
                p.setBrush(QBrush(QColor(dev.color)))
                p.setPen(QPen(QColor(T.borderL), 1))
                p.drawRoundedRect(QRectF(0, 0, dev.w, dev.h), T.R, T.R)

            # LED indicators
            for led in dev.leds:
                sv = led.get("state_var", "")
                onv = led.get("on_value", True)
                is_on = self.sim_running and inst["state"].get(sv) == onv
                lx = led.get("x", 0)
                ly = led.get("y", 0)
                lr = led.get("radius", 6)
                lc = QColor(led.get("color", "#ff3344"))

                if is_on:
                    grad = QRadialGradient(lx, ly, lr * 3)
                    grad.setColorAt(0, QColor(lc.red(), lc.green(), lc.blue(), 180))
                    grad.setColorAt(1, QColor(lc.red(), lc.green(), lc.blue(), 0))
                    p.setBrush(QBrush(grad))
                    p.setPen(Qt.NoPen)
                    p.drawEllipse(QPointF(lx, ly), lr * 3, lr * 3)

                fill = (
                    QColor(lc)
                    if is_on
                    else QColor(lc.red() // 4, lc.green() // 4, lc.blue() // 4, 120)
                )
                border_c = lc if is_on else QColor(lc.red() // 3, lc.green() // 3, lc.blue() // 3)
                p.setBrush(QBrush(fill))
                p.setPen(QPen(border_c, 1))
                p.drawEllipse(QPointF(lx, ly), lr, lr)

            # Pins
            for pin in dev.pins:
                pc = QColor(PIN_CLR.get(pin.type, T.pPas))
                wpx = ix + pin.x
                wpy = iy + pin.y
                dist = math.hypot(self.mouse_world.x() - wpx, self.mouse_world.y() - wpy)
                is_hov = dist < 9
                r = 6 if is_hov else 4

                fill_c = QColor(T.blue) if is_hov else pc
                border_c = (
                    QColor(T.blue + "88") if is_hov
                    else QColor(pc.red(), pc.green(), pc.blue(), 80)
                )
                p.setBrush(QBrush(fill_c))
                p.setPen(QPen(border_c, 1))
                p.drawEllipse(QPointF(pin.x, pin.y), r, r)

                if is_board:
                    p.setPen(QColor(T.textMut))
                    p.setFont(QFont(T.MONO, 7))
                    if pin.side == "left":
                        p.drawText(QPointF(pin.x + 8, pin.y + 3), pin.label)
                    else:
                        fm = QFontMetrics(p.font())
                        p.drawText(
                            QPointF(pin.x - 8 - fm.horizontalAdvance(pin.label), pin.y + 3),
                            pin.label,
                        )

                if is_hov:
                    txt = f"{pin.label} ({pin.type})"
                    p.setFont(QFont(T.MONO, 8, QFont.Bold))
                    fm = QFontMetrics(p.font())
                    tw = fm.horizontalAdvance(txt) + 10
                    p.setBrush(QBrush(QColor(0, 0, 0, 220)))
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(QRectF(pin.x - tw / 2, pin.y - 22, tw, 16), 4, 4)
                    p.setPen(QColor("#ffffff"))
                    p.drawText(
                        QRectF(pin.x - tw / 2, pin.y - 22, tw, 16),
                        Qt.AlignCenter, txt,
                    )

            # Component label
            if not is_board and not dev.display and not dev._qimage:
                p.setPen(QColor(T.textSec))
                p.setFont(QFont(T.MONO, 8, QFont.Bold))
                p.drawText(QRectF(0, dev.h + 2, dev.w, 14), Qt.AlignCenter, dev.label)

            p.restore()

        # Empty canvas hint
        if not self.instances:
            p.setPen(QColor(T.textMut))
            p.setFont(QFont(T.MONO, 12))
            hint_x = -self.camera.x() + vw / 2 - 200
            hint_y = -self.camera.y() + vh / 2
            p.drawText(QPointF(hint_x, hint_y), "Import .adev files, then click devices to place")

        p.restore()

    def mousePressEvent(self, e):
        w = self.to_world(e.pos())

        if e.button() == Qt.MiddleButton:
            self.panning = {"sx": e.pos(), "cam": QPointF(self.camera)}
            self.setCursor(Qt.ClosedHandCursor)
            return

        if e.button() != Qt.LeftButton:
            return

        hit = self.find_pin_at(w.x(), w.y())

        # Wire tool or pin click
        if self.tool == "wire" or (self.tool == "select" and hit):
            if hit:
                inst_id, pin, px, py = hit
                if not self.connecting:
                    self.connecting = (inst_id, pin, px, py)
                else:
                    if self.connecting[0] != inst_id or self.connecting[1].id != pin.id:
                        self.wires.append({
                            "id": nid(),
                            "from": (self.connecting[0], self.connecting[1].id),
                            "to": (inst_id, pin.id),
                        })
                        self.recompute_routes()
                    self.connecting = None
                self.update()
                return
            elif self.tool == "wire":
                return

        # Delete tool
        if self.tool == "delete":
            inst = self.find_inst_at(w.x(), w.y())
            if inst:
                self.instances.remove(inst)
                self.wires = [
                    wi for wi in self.wires
                    if wi["from"][0] != inst["id"] and wi["to"][0] != inst["id"]
                ]
                if self.selected == inst["id"]:
                    self.selected = None
                self.recompute_routes()
                self.update()
                return
            # Check wire click
            for wid, route in list(self.routes.items()):
                for i in range(len(route) - 1):
                    ax, ay = route[i]
                    bx, by = route[i + 1]
                    dx, dy = bx - ax, by - ay
                    l2 = dx * dx + dy * dy
                    t = max(0, min(1, ((w.x() - ax) * dx + (w.y() - ay) * dy) / l2)) if l2 > 0 else 0
                    if math.hypot(w.x() - (ax + t * dx), w.y() - (ay + t * dy)) < 8:
                        self.wires = [wi for wi in self.wires if wi["id"] != wid]
                        self.recompute_routes()
                        self.update()
                        return
            return

        # Select tool
        self.connecting = None
        inst = self.find_inst_at(w.x(), w.y())
        if inst:
            self.selected = inst["id"]
            self.dragging = {
                "id": inst["id"],
                "ox": w.x() - inst["x"],
                "oy": w.y() - inst["y"],
            }
            self.selectionChanged.emit(inst)
        else:
            self.selected = None
            self.panning = {"sx": e.pos(), "cam": QPointF(self.camera)}
            self.selectionChanged.emit(None)
        self.update()

    def mouseMoveEvent(self, e):
        self.mouse_world = self.to_world(e.pos())
        if self.panning:
            d = e.pos() - self.panning["sx"]
            self.camera = self.panning["cam"] + QPointF(
                d.x() / self.zoom_level, d.y() / self.zoom_level
            )
            self.update()
            return
        if self.dragging:
            w = self.mouse_world
            for inst in self.instances:
                if inst["id"] == self.dragging["id"]:
                    inst["x"] = w.x() - self.dragging["ox"]
                    inst["y"] = w.y() - self.dragging["oy"]
                    break
            self.recompute_routes()
            self.update()
            return
        self.update()

    def mouseReleaseEvent(self, e):
        self.dragging = None
        self.panning = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.zoom_level = max(0.25, min(4.0, self.zoom_level * f))
        self.update()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        elif e.key() == Qt.Key_Escape:
            self.connecting = None
            self.tool = "select"
            self.update()


# ═══════════════════════════════════════════════════════════════
#  SERIAL MONITOR
# ═══════════════════════════════════════════════════════════════
class SerialMon(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont(T.MONO, 11))
        self.document().setDefaultStyleSheet(
            ".i{color:" + T.textMut + "}"
            ".o{color:" + T.green + "}"
            ".e{color:" + T.red + "}"
            ".p{color:" + T.blue + "}"
        )
        self.log("Serial monitor ready.", "i")

    def log(self, t, cls="i"):
        self.append(f'<span class="{cls}">{t}</span>')

    def log_out(self, t):
        self.append(f'<span class="p">&gt; </span><span class="o">{t}</span>')


# ═══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════
class WorkbenchIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asteron Workbench \u2014 IDE")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 850)
        self.setStyleSheet(SS)

        self.devices = {}
        self.sim_timer = QTimer()
        self.sim_timer.setInterval(500)
        self.sim_timer.timeout.connect(self._sim_tick)
        self.sim_tick_count = 0
        self._has_dw = False
        self._has_blink = False

        self._build_menu()
        self._build_toolbar()
        self._build_ui()
        self._build_status()

    def _build_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("&File")
        fm.addAction("Import Sketch...", self._import_code)
        fm.addAction("Import Device Files...", self._import_devices)
        fm.addSeparator()
        fm.addAction("Exit", self.close)

        em = mb.addMenu("&Edit")
        em.addAction("Delete Selected", lambda: self.canvas.delete_selected())

        sm = mb.addMenu("&Simulation")
        sm.addAction("Run", self._run_sim)
        sm.addAction("Stop", self._stop_sim)

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        # Brand
        logo = QLabel(" ASTERON ")
        logo.setFont(QFont(T.MONO, 12, QFont.Bold))
        logo.setStyleSheet("color:" + T.blue + ";letter-spacing:2px;padding-right:8px")
        tb.addWidget(logo)
        sep0 = QFrame()
        sep0.setFrameShape(QFrame.VLine)
        sep0.setStyleSheet("color:" + T.border)
        tb.addWidget(sep0)

        btn_sketch = QPushButton("Import Sketch")
        btn_sketch.clicked.connect(self._import_code)
        tb.addWidget(btn_sketch)
        btn_dev = QPushButton("Import Devices")
        btn_dev.clicked.connect(self._import_devices)
        tb.addWidget(btn_dev)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color:" + T.border)
        tb.addWidget(sep1)

        self.tool_btns = {}
        for tid, label in [("select", "Select [1]"), ("wire", "Wire [2]"), ("delete", "Delete [3]")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(tid == "select")
            b.clicked.connect(lambda checked, t=tid: self._set_tool(t))
            tb.addWidget(b)
            self.tool_btns[tid] = b

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color:" + T.border)
        tb.addWidget(sep2)

        self.btn_run = QPushButton("Run")
        self.btn_run.setStyleSheet(
            "QPushButton{background:" + T.green + ";color:#000;border:none;"
            "border-radius:4px;padding:6px 16px;font-weight:bold}"
            "QPushButton:hover{background:#55ee77}"
        )
        self.btn_run.clicked.connect(self._run_sim)
        tb.addWidget(self.btn_run)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setStyleSheet(
            "QPushButton{background:" + T.red + ";color:#fff;border:none;"
            "border-radius:4px;padding:6px 16px;font-weight:bold}"
            "QPushButton:hover{background:#ff6666}"
        )
        self.btn_stop.clicked.connect(self._stop_sim)
        self.btn_stop.setEnabled(False)
        tb.addWidget(self.btn_stop)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.lbl_status = QLabel("IDLE")
        self.lbl_status.setFont(QFont(T.MONO, 10))
        self.lbl_status.setStyleSheet("color:" + T.textMut + ";padding:0 12px")
        tb.addWidget(self.lbl_status)

    def _set_tool(self, tid):
        self.canvas.tool = tid
        self.canvas.connecting = None
        self.canvas.update()
        for k, b in self.tool_btns.items():
            b.setChecked(k == tid)

    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        ml = QHBoxLayout(cw)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        sp = QSplitter(Qt.Horizontal)

        # ── Left: library ──
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        lib_lbl = QLabel("  DEVICES")
        lib_lbl.setFont(QFont(T.MONO, 9, QFont.Bold))
        lib_lbl.setStyleSheet(
            "color:" + T.textMut + ";padding:10px 4px 6px;letter-spacing:2px"
        )
        ll.addWidget(lib_lbl)

        self.dev_tree = QTreeWidget()
        self.dev_tree.setHeaderHidden(True)
        self.dev_tree.setRootIsDecorated(True)
        self.dev_tree.setIndentation(14)
        self.dev_tree.itemClicked.connect(self._on_dev_click)
        ll.addWidget(self.dev_tree)

        tip = QLabel(
            "Click to place\nDel remove\nScroll zoom\nMiddle-click pan"
        )
        tip.setFont(QFont(T.UI, 9))
        tip.setStyleSheet(
            "color:" + T.textMut + ";padding:10px;border-top:1px solid " + T.border
        )
        tip.setWordWrap(True)
        ll.addWidget(tip)

        self.dev_count_lbl = QLabel("  0 devices loaded")
        self.dev_count_lbl.setFont(QFont(T.MONO, 8))
        self.dev_count_lbl.setStyleSheet("color:" + T.textMut + ";padding:4px 8px")
        ll.addWidget(self.dev_count_lbl)

        left.setMaximumWidth(200)
        left.setMinimumWidth(150)
        sp.addWidget(left)

        # ── Center ──
        cs = QSplitter(Qt.Vertical)
        self.canvas = CircuitCanvas()
        self.canvas.selectionChanged.connect(self._on_select)
        cs.addWidget(self.canvas)

        self.btabs = QTabWidget()
        self.serial = SerialMon()
        self.btabs.addTab(self.serial, "Serial Monitor")
        self.problems = QTextEdit()
        self.problems.setReadOnly(True)
        self.problems.setStyleSheet(
            "background:" + T.bg + ";color:" + T.textMut + ";border:none"
        )
        self.problems.setPlainText("No problems detected.")
        self.btabs.addTab(self.problems, "Problems")
        cs.addWidget(self.btabs)
        cs.setSizes([500, 140])
        sp.addWidget(cs)

        # ── Right: code + properties ──
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        self.rtabs = QTabWidget()
        self.editor = CodeEditor()
        self.editor.setPlaceholderText("Import a .ino sketch or type code here...")
        self.rtabs.addTab(self.editor, "sketch.ino")

        self.props_panel = QTextEdit()
        self.props_panel.setReadOnly(True)
        self.props_panel.setStyleSheet(
            "background:" + T.bg + ";color:" + T.textSec + ";border:none;padding:14px"
        )
        self.props_panel.setFont(QFont(T.MONO, 11))
        self.props_panel.setPlainText("Select a component to view properties.")
        self.rtabs.addTab(self.props_panel, "Properties")
        rl.addWidget(self.rtabs)

        right.setMinimumWidth(300)
        sp.addWidget(right)
        sp.setSizes([180, 700, 380])
        ml.addWidget(sp)

    def _build_status(self):
        sb = self.statusBar()
        self.st_sim = QLabel("IDLE")
        self.st_parts = QLabel("0 parts | 0 wires")
        self.st_devs = QLabel("0 devices")
        for lbl in [self.st_sim, self.st_parts, self.st_devs]:
            lbl.setFont(QFont(T.MONO, 10))
            lbl.setStyleSheet("color:" + T.textMut + ";padding:0 10px")
            sb.addWidget(lbl)
        self.ui_timer = QTimer()
        self.ui_timer.setInterval(500)
        self.ui_timer.timeout.connect(self._upd_status)
        self.ui_timer.start()

    def _upd_status(self):
        n = len(self.canvas.instances)
        w = len(self.canvas.wires)
        self.st_parts.setText(f"{n} parts | {w} wires")
        self.st_devs.setText(f"{len(self.devices)} devices")
        running = self.canvas.sim_running
        self.st_sim.setText("SIM RUNNING" if running else "IDLE")
        self.st_sim.setStyleSheet(
            "color:" + (T.green if running else T.textMut) + ";padding:0 10px"
        )

    def _import_devices(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Device Files", "",
            "Device Files (*.adev *.json);;All (*)",
        )
        if not files:
            return
        count = 0
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                dev = DeviceDef(data)
                self.devices[dev.id] = dev
                count += 1
            except Exception as ex:
                self.serial.log(f"Error loading {Path(f).name}: {ex}", "e")
        self._rebuild_tree()
        self.serial.log(f"Loaded {count} device(s).", "i")
        self.dev_count_lbl.setText(f"  {len(self.devices)} devices loaded")

    def _import_code(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Import Sketch", "",
            "Arduino (*.ino *.c *.cpp *.txt);;All (*)",
        )
        if not f:
            return
        with open(f, "r", encoding="utf-8") as fh:
            self.editor.setPlainText(fh.read())
        self.rtabs.setTabText(0, Path(f).name)
        self.serial.log(f"Loaded sketch: {Path(f).name}", "i")

    def _rebuild_tree(self):
        self.dev_tree.clear()
        cats = {}
        cat_order = ["Boards", "Output", "Display", "Input", "Sensor", "Passive", "Other"]
        for d in self.devices.values():
            c = d.category or "Other"
            if c not in cats:
                cats[c] = []
            cats[c].append(d)
        all_cats = cat_order + [c for c in cats if c not in cat_order]
        for cat in all_cats:
            if cat not in cats:
                continue
            ci = QTreeWidgetItem(self.dev_tree, [cat])
            ci.setFlags(Qt.ItemIsEnabled)
            f = ci.font(0)
            f.setPointSize(10)
            f.setBold(True)
            ci.setFont(0, f)
            ci.setForeground(0, QColor(T.textMut))
            for d in cats[cat]:
                ch = QTreeWidgetItem(ci, [d.name])
                ch.setData(0, Qt.UserRole, d.id)
                pm = QPixmap(10, 10)
                pm.fill(QColor(d.color))
                ch.setIcon(0, QIcon(pm))
                ch.setToolTip(0, d.desc)
            ci.setExpanded(True)

    def _on_dev_click(self, item, col):
        did = item.data(0, Qt.UserRole)
        if did and did in self.devices:
            self.canvas.add_instance(self.devices[did])

    def _on_select(self, inst):
        if not inst:
            self.props_panel.setPlainText("Select a component to view properties.")
            return
        dev = inst["dev"]
        lines = [
            dev.name,
            "=" * len(dev.name),
            "",
            f"ID: {dev.id}",
            f"Category: {dev.category}",
            f"Type: {dev.emu_type}",
            f"Size: {dev.w}x{dev.h}",
            "",
            f"Description: {dev.desc}",
            "",
            f"PINS ({len(dev.pins)})",
            "-" * 30,
        ]
        for p in dev.pins:
            lines.append(f"  {p.label:10s} {p.type:10s} ({p.x},{p.y}) {p.side}")
        if dev.props:
            lines += ["", "PROPERTIES", "-" * 30]
            for k, v in dev.props.items():
                lines.append(f"  {k}: {v}")
        if dev.leds:
            lines += ["", f"LED INDICATORS ({len(dev.leds)})", "-" * 30]
            for led in dev.leds:
                lines.append(
                    f"  {led.get('label', '?')} -> {led.get('state_var', '?')}"
                    f"  color:{led.get('color', '?')}"
                )
        self.props_panel.setPlainText("\n".join(lines))

    def _run_sim(self):
        code = self.editor.toPlainText()
        if not code.strip():
            self.serial.log("No sketch loaded.", "e")
            return

        self.serial.clear()
        self.serial.log("--- Compiling... ---", "i")

        if "void setup()" not in code:
            self.serial.log("Warning: missing setup()", "e")
        if "void loop()" not in code:
            self.serial.log("Warning: missing loop()", "e")
        if code.count("{") != code.count("}"):
            self.serial.log("Warning: mismatched braces", "e")

        sz = len(code.encode()) * 2
        self.serial.log(
            f"Sketch uses ~{sz} bytes ({sz * 100 // 32768}% of storage).", "i"
        )
        self.serial.log("--- Simulation started ---", "i")

        # Extract Serial.print outputs
        matches = list(re.finditer(r'Serial\.println?\(\s*"([^"]+)"\s*\)', code))
        for idx, m in enumerate(matches):
            text = m.group(1)
            QTimer.singleShot(600 * (1 + idx), lambda t=text: self.serial.log_out(t))

        self.canvas.sim_running = True
        self.sim_tick_count = 0
        self.sim_timer.start()
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText("RUNNING")
        self.lbl_status.setStyleSheet("color:" + T.green + ";padding:0 12px")
        self._has_dw = "digitalWrite" in code
        self._has_blink = self._has_dw and "delay(" in code

    def _stop_sim(self):
        self.canvas.sim_running = False
        self.sim_timer.stop()
        for inst in self.canvas.instances:
            inst["state"] = dict(inst["dev"].state_vars)
        self.canvas.update()
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("IDLE")
        self.lbl_status.setStyleSheet("color:" + T.textMut + ";padding:0 12px")
        self.serial.log("--- Simulation stopped ---", "i")

    def _sim_tick(self):
        self.sim_tick_count += 1
        for inst in self.canvas.instances:
            dev = inst["dev"]
            for rule in dev.rules:
                if rule.get("action") == "set_state" and rule.get("target"):
                    if rule.get("trigger") == "pin_high":
                        if self._has_blink:
                            val = rule["value"]
                            if isinstance(val, bool):
                                inst["state"][rule["target"]] = (
                                    val if self.sim_tick_count % 2 == 0 else (not val)
                                )
                            else:
                                inst["state"][rule["target"]] = (
                                    val if self.sim_tick_count % 2 == 0 else 0
                                )
                        elif self._has_dw:
                            inst["state"][rule["target"]] = rule["value"]
        self.canvas.update()

    def keyPressEvent(self, e):
        if e.text() == "1":
            self._set_tool("select")
        elif e.text() == "2":
            self._set_tool("wire")
        elif e.text() == "3":
            self._set_tool("delete")
        else:
            super().keyPressEvent(e)


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
    win = WorkbenchIDE()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
