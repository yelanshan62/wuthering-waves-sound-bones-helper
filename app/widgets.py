"""浅色界面用到的通用控件和样式。"""

import hashlib

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

ACCENT = "#4F6BFF"
ACCENT_DARK = "#3A52E0"
TEXT = "#1F2433"
SUBTEXT = "#7A8299"
BORDER = "#E4E8F1"
BACKGROUND = "#F4F6FB"

TAG_STYLES = {
    "required": ("#E5484D", "#FFECEE", "必要"),
    "optional": ("#2F7BF6", "#E8F1FF", "选要"),
    "invalid": ("#8A93A6", "#F1F3F7", "无效"),
}
TAG_ORDER = ("invalid", "required", "optional")

AVATAR_COLORS = ("#4F6BFF", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#06B6D4", "#EF4444", "#6366F1")

STYLE_SHEET = f"""
* {{ font-family: "Microsoft YaHei UI", "Microsoft YaHei"; color: {TEXT}; }}
QMainWindow, #page {{ background: {BACKGROUND}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
#sidebar {{ background: #FFFFFF; border-right: 1px solid {BORDER}; }}
#card {{ background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 16px; }}
#appTitle {{ font-size: 20px; font-weight: 700; }}
#appSubtitle {{ font-size: 12px; color: {SUBTEXT}; }}
#sectionTitle {{ font-size: 15px; font-weight: 700; }}
#hint {{ font-size: 12px; color: {SUBTEXT}; }}
#bigName {{ font-size: 24px; font-weight: 700; }}
#statValue {{ font-size: 26px; font-weight: 700; }}
#statLabel {{ font-size: 12px; color: {SUBTEXT}; }}
QLineEdit, QSpinBox, QComboBox {{
    background: #F7F8FC; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 6px 10px; font-size: 13px; min-height: 22px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; background: #FFFFFF; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 8px;
    selection-background-color: #EEF1FF; selection-color: {TEXT}; outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}
QPlainTextEdit {{
    background: #FAFBFE; border: 1px solid {BORDER}; border-radius: 12px; padding: 8px;
    font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei UI"; font-size: 12px; color: #3A4256;
}}
QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5B7CFF, stop:1 #8A5CFF);
    color: #FFFFFF; border: none; border-radius: 12px; padding: 10px 22px; font-size: 14px; font-weight: 700;
}}
QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4C6EF5, stop:1 #7C4DFF); }}
QPushButton#primary:disabled {{ background: #C9CFE0; }}
QPushButton#start {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5B7CFF, stop:1 #8A5CFF);
    color: #FFFFFF; border: none; border-radius: 20px; font-size: 22px; font-weight: 800; letter-spacing: 4px;
}}
QPushButton#start:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4C6EF5, stop:1 #7C4DFF); }}
QPushButton#start[running="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF7A7A, stop:1 #F0457A);
}}
QPushButton#ghost {{
    background: #FFFFFF; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 9px 18px; font-size: 13px;
}}
QPushButton#ghost:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QPushButton#danger {{
    background: #FFFFFF; color: #E5484D; border: 1px solid #F6C9CC; border-radius: 12px;
    padding: 9px 18px; font-size: 13px;
}}
QPushButton#danger:hover {{ background: #FFF1F2; }}
QPushButton#newProfile {{
    background: #EEF1FF; color: {ACCENT}; border: 1px dashed #B9C4FF; border-radius: 14px;
    padding: 12px; font-size: 14px; font-weight: 700;
}}
QPushButton#newProfile:hover {{ background: #E3E8FF; }}
QPushButton#seg {{
    background: #F3F5FA; color: #5A6378; border: 1px solid {BORDER}; padding: 8px 14px; font-size: 13px;
}}
QPushButton#seg:checked {{ background: #FFFFFF; color: {ACCENT}; border: 1.5px solid {ACCENT}; font-weight: 700; }}
QPushButton#seg[pos="first"] {{ border-top-left-radius: 10px; border-bottom-left-radius: 10px; }}
QPushButton#seg[pos="last"] {{ border-top-right-radius: 10px; border-bottom-right-radius: 10px; }}
QPushButton#chip {{
    background: #F3F5FA; color: #5A6378; border: 1px solid {BORDER}; border-radius: 15px;
    padding: 6px 14px; font-size: 13px;
}}
QPushButton#chip:checked {{ background: #EEF1FF; color: {ACCENT}; border: 1.5px solid {ACCENT}; font-weight: 700; }}
QPushButton#tab {{
    background: transparent; color: {SUBTEXT}; border: none; border-bottom: 3px solid transparent;
    padding: 8px 4px; margin-right: 18px; font-size: 15px; font-weight: 600;
}}
QPushButton#tab:checked {{ color: {TEXT}; border-bottom: 3px solid {ACCENT}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: #D5DAE6; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


def add_shadow(widget: QWidget, blur: int = 24, alpha: int = 28):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(40, 55, 110, alpha))
    widget.setGraphicsEffect(shadow)


def label(text: str, name: str | None = None, wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text: str, name: str) -> QPushButton:
    widget = QPushButton(text)
    widget.setObjectName(name)
    widget.setCursor(Qt.PointingHandCursor)
    return widget


class Card(QFrame):
    def __init__(self, title: str | None = None, hint: str | None = None, shadow: bool = True):
        super().__init__()
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(22, 18, 22, 20)
        self.body.setSpacing(12)
        if title:
            self.body.addWidget(label(title, "sectionTitle"))
        if hint:
            self.body.addWidget(label(hint, "hint", wrap=True))
        if shadow:
            add_shadow(self)


class Toggle(QAbstractButton):
    """iOS 风格开关。"""

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self._offset = 1.0 if checked else 0.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(160)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self):
        return QSize(46, 26)

    def _animate(self, checked: bool):
        self._animation.stop()
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._offset = 1.0 if checked else 0.0
        self.update()

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(1, 1, -1, -1)
        off, on = QColor("#D5DAE6"), QColor(ACCENT)
        color = QColor(
            int(off.red() + (on.red() - off.red()) * self._offset),
            int(off.green() + (on.green() - off.green()) * self._offset),
            int(off.blue() + (on.blue() - off.blue()) * self._offset),
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        knob = rect.height() - 6
        x = rect.left() + 3 + (rect.width() - knob - 6) * self._offset
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(x, rect.top() + 3, knob, knob))


class ToggleRow(QWidget):
    """左边标题和说明，右边开关。"""

    def __init__(self, title: str, hint: str = "", checked: bool = False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(label(title, "sectionTitle"))
        if hint:
            texts.addWidget(label(hint, "hint", wrap=True))
        layout.addLayout(texts, 1)
        self.toggle = Toggle(checked)
        layout.addWidget(self.toggle, 0, Qt.AlignVCenter)


class Segmented(QWidget):
    """一组互斥的分段按钮，值为 options 的 key。"""
    changed = Signal(str)

    def __init__(self, options: dict[str, str]):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.group = QButtonGroup(self)
        self.buttons: dict[str, QPushButton] = {}
        keys = list(options)
        for i, key in enumerate(keys):
            btn = button(options[key], "seg")
            btn.setCheckable(True)
            if i == 0:
                btn.setProperty("pos", "first")
            if i == len(keys) - 1:
                btn.setProperty("pos", "last")
            self.group.addButton(btn)
            layout.addWidget(btn)
            self.buttons[key] = btn
            btn.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
        layout.addStretch(1)
        self.buttons[keys[0]].setChecked(True)

    def value(self) -> str:
        return next(key for key, btn in self.buttons.items() if btn.isChecked())

    def set_value(self, key: str):
        self.buttons[key].setChecked(True)


def chip(text: str) -> QPushButton:
    widget = button(text, "chip")
    widget.setCheckable(True)
    return widget


class StatTag(QPushButton):
    """副词条标签：点击在 无效 / 必要 / 选要 之间切换。"""
    changed = Signal()

    def __init__(self, stat: str, state: str = "invalid", clickable: bool = True):
        super().__init__()
        self.stat = stat
        self.clickable = clickable
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if clickable:
            self.setCursor(Qt.PointingHandCursor)
            self.clicked.connect(self._cycle)
        self.set_state(state)

    def _cycle(self):
        self.set_state(TAG_ORDER[(TAG_ORDER.index(self.state) + 1) % len(TAG_ORDER)])
        self.changed.emit()

    def set_state(self, state: str):
        self.state = state
        fg, bg, word = TAG_STYLES[state]
        self.setText(f"{self.stat} · {word}" if self.clickable else self.stat)
        weight = 700 if state != "invalid" else 500
        self.setStyleSheet(
            f"QPushButton {{ background: {bg}; color: {fg}; border: 1.5px solid {fg if state != 'invalid' else '#E4E8F1'};"
            f" border-radius: 14px; padding: 6px 14px; font-size: 13px; font-weight: {weight}; }}")


def avatar_color(name: str) -> str:
    digest = hashlib.md5(name.encode("utf-8")).digest()
    return AVATAR_COLORS[digest[0] % len(AVATAR_COLORS)]


class Avatar(QWidget):
    def __init__(self, name: str, size: int = 44):
        super().__init__()
        self.name = name
        self.setFixedSize(size, size)

    def set_name(self, name: str):
        self.name = name
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(avatar_color(self.name or "?")))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), self.width() * 0.3, self.width() * 0.3)
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Microsoft YaHei UI", int(self.height() * 0.36))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, (self.name or "?")[0])


class ProfileCard(QFrame):
    """侧边栏里的角色卡片。"""
    clicked = Signal(str)

    def __init__(self, name: str, sonata_set: str, summary: str):
        super().__init__()
        self.name = name
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.addWidget(Avatar(name))
        texts = QVBoxLayout()
        texts.setSpacing(2)
        title = label(name)
        title.setStyleSheet("font-size: 15px; font-weight: 700; background: transparent;")
        sub = label(f"{sonata_set} · {summary}")
        sub.setStyleSheet(f"font-size: 12px; color: {SUBTEXT}; background: transparent;")
        texts.addWidget(title)
        texts.addWidget(sub)
        layout.addLayout(texts, 1)
        self.set_selected(False)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(f"ProfileCard {{ background: #EEF1FF; border: 1.5px solid {ACCENT}; border-radius: 14px; }}")
        else:
            self.setStyleSheet(f"ProfileCard {{ background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 14px; }}"
                               f"ProfileCard:hover {{ border-color: #B9C4FF; }}")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.name)
        super().mouseReleaseEvent(event)


class FlowLayout(QVBoxLayout):
    """按固定列数把控件排成多行，用于词条标签。"""

    def __init__(self, columns: int):
        super().__init__()
        self.columns = columns
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(8)
        self._row: QHBoxLayout | None = None
        self._count = 0

    def add(self, widget: QWidget):
        if self._count % self.columns == 0:
            self._row = QHBoxLayout()
            self._row.setSpacing(8)
            self._row.addStretch(1)
            self.addLayout(self._row)
        self._row.insertWidget(self._row.count() - 1, widget)
        self._count += 1

    def clear(self):
        while self.count():
            item = self.takeAt(0)
            row = item.layout()
            if row:
                while row.count():
                    child = row.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
        self._count = 0
