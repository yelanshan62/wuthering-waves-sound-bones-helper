"""声骸助手桌面软件入口。"""

import ctypes
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import (QApplication, QButtonGroup, QHBoxLayout, QMainWindow, QMessageBox,  # noqa: E402
                               QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from app.editor import ProfileEditor  # noqa: E402
from app.runner import RunPage  # noqa: E402
from app.widgets import STYLE_SHEET, ProfileCard, button, label  # noqa: E402
from echo_helper.install import ensure_installed  # noqa: E402
from echo_helper.profile import list_profiles, load_profile  # noqa: E402

ICON_PATH = REPO_DIR / "app" / "assets" / "icon.ico"
APP_ID = "yelanshan62.wuwa.echo-helper"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("声骸助手 · 鸣潮")
        self.resize(1240, 820)
        self.setMinimumSize(1080, 720)
        self.selected: str | None = None
        self.cards: dict[str, ProfileCard] = {}

        root = QWidget()
        root.setObjectName("page")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._sidebar())

        main = QVBoxLayout()
        main.setContentsMargins(24, 18, 16, 0)
        main.setSpacing(12)
        tabs = QHBoxLayout()
        self.tab_group = QButtonGroup(self)
        self.stack = QStackedWidget()
        self.run_page = RunPage()
        self.editor = ProfileEditor()
        for index, (text, page) in enumerate((("开始运行", self.run_page), ("编辑方案", self.editor))):
            tab = button(text, "tab")
            tab.setCheckable(True)
            tab.clicked.connect(lambda _=False, i=index: self.stack.setCurrentIndex(i))
            self.tab_group.addButton(tab, index)
            tabs.addWidget(tab)
            self.stack.addWidget(page)
        tabs.addStretch(1)
        self.tab_group.button(0).setChecked(True)
        main.addLayout(tabs)
        main.addWidget(self.stack, 1)
        layout.addLayout(main, 1)

        self.editor.saved.connect(self._on_saved)
        self.editor.deleted.connect(lambda _: self._refresh_cards())
        self.run_page.running_changed.connect(self._on_running_changed)
        self._refresh_cards()

    def _sidebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("sidebar")
        bar.setFixedWidth(290)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(6)
        layout.addWidget(label("声骸助手", "appTitle"))
        layout.addWidget(label("按角色刷取 · 升级 · 自动判断去留", "appSubtitle"))
        layout.addSpacing(14)
        layout.addWidget(label("角色方案", "hint"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        self.card_layout = QVBoxLayout(holder)
        self.card_layout.setContentsMargins(0, 4, 4, 4)
        self.card_layout.setSpacing(10)
        self.card_layout.addStretch(1)
        scroll.setWidget(holder)
        layout.addWidget(scroll, 1)
        self.new_button = button("＋  新建角色", "newProfile")
        self.new_button.clicked.connect(self._new_profile)
        layout.addWidget(self.new_button)
        self.sidebar = bar
        return bar

    def _refresh_cards(self, select: str | None = None):
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()
        names = list_profiles()
        for name in names:
            try:
                profile = load_profile(name)
            except (ValueError, KeyError) as e:
                QMessageBox.warning(self, "方案读取失败", f"{name}：{e}")
                continue
            summary = "、".join(profile.required) or "未设必要词条"
            card = ProfileCard(profile.name, profile.sonata_set, summary)
            card.clicked.connect(self._select)
            self.card_layout.insertWidget(self.card_layout.count() - 1, card)
            self.cards[name] = card
        target = select if select in self.cards else (self.selected if self.selected in self.cards else None)
        if target is None and self.cards:
            target = next(iter(self.cards))
        if target:
            self._select(target)
        else:
            self.selected = None
            self.run_page.show_profile(None)
            self.editor.fill(None)

    def _select(self, name: str):
        self.selected = name
        for card_name, card in self.cards.items():
            card.set_selected(card_name == name)
        profile = load_profile(name)
        self.run_page.show_profile(profile)
        self.editor.fill(profile)

    def _new_profile(self):
        self.editor.fill(None)
        self.tab_group.button(1).setChecked(True)
        self.stack.setCurrentIndex(1)
        self.editor.name_edit.setFocus()

    def _on_saved(self, name: str):
        self._refresh_cards(select=name)
        self.tab_group.button(0).setChecked(True)
        self.stack.setCurrentIndex(0)

    def _on_running_changed(self, running: bool):
        self.sidebar.setEnabled(not running)
        self.editor.setEnabled(not running)

    def closeEvent(self, event):
        if self.run_page.is_running():
            answer = QMessageBox.question(self, "任务还在运行", "关闭软件会强制结束正在运行的任务，确定关闭吗？")
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.run_page.shutdown()
        event.accept()


def main():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    if ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.show()
    try:
        ensure_installed()
    except FileNotFoundError as e:
        QMessageBox.critical(window, "找不到 ok-ww", f"{e}\n请先把 ok-ww 放在这个位置，或修改 echo_helper/install.py 里的 OKWW_DIR。")
        window.run_page.start_button.setEnabled(False)
    if not ctypes.windll.shell32.IsUserAnAdmin():
        QMessageBox.warning(window, "没有管理员权限",
                            "ok-ww 需要管理员权限才能操作游戏。请用桌面上的“声骸助手”快捷方式启动（会自动请求管理员权限）。")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
