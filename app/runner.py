"""运行页：选择做什么、开始 / 停止、显示状态、计数和日志，并处理任务的继续询问。"""

import subprocess
import time

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, Signal
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget)

from app.widgets import (Avatar, Card, FlowLayout, StatTag, ToggleRow, button, label)
from echo_helper.bridge import RUN_ENV, Bridge, RunRequest
from echo_helper.install import OKWW_DIR, OKWW_PYTHONW, REPO_DIR, TASK_CLASS
from echo_helper.profile import C4_TELEPORT_LABELS, FODDER_PRIORITIES, Profile

STATUS_COLORS = {
    "idle": ("#8A93A6", "待机"),
    "running": ("#4F6BFF", "运行中"),
    "stopping": ("#F59E0B", "正在停止"),
    "done": ("#10B981", "已完成"),
    "error": ("#E5484D", "出错了"),
}
OKWW_OUTPUT = REPO_DIR / "runtime" / "okww_output.log"
STOP_GRACE_SECONDS = 20


class AskDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, text: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setStyleSheet("QDialog { background: #FFFFFF; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(14)
        layout.addWidget(label("🎉 有新的毕业声骸", "bigName"))
        body = label(text, wrap=True)
        body.setStyleSheet("font-size: 14px; color: #3A4256;")
        layout.addWidget(body)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        stop = button("到此为止", "ghost")
        stop.clicked.connect(self.reject)
        go = button("继续升级", "primary")
        go.clicked.connect(self.accept)
        buttons.addWidget(stop)
        buttons.addWidget(go)
        layout.addLayout(buttons)


class StatBox(Card):
    def __init__(self, title: str, color: str):
        super().__init__(shadow=False)
        self.body.setContentsMargins(18, 14, 18, 14)
        self.body.setSpacing(2)
        self.value_label = label("0", "statValue")
        self.value_label.setStyleSheet(f"color: {color};")
        self.body.addWidget(self.value_label)
        self.body.addWidget(label(title, "statLabel"))

    def set_value(self, value):
        self.value_label.setText(str(value))


class RunPage(QWidget):
    running_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.profile: Profile | None = None
        self.bridge = Bridge()
        self.process: QProcess | None = None
        self.event_offset = 0
        self.finished_reported = False
        self.stop_requested_at = 0.0
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(300)
        self.poll_timer.timeout.connect(self._poll_events)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 12, 16)
        layout.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(self._hero_card(), 3)
        top.addWidget(self._control_card(), 2)
        layout.addLayout(top)

        stats = QGridLayout()
        stats.setSpacing(12)
        self.graduated_box = StatBox("毕业（已上锁）", "#10B981")
        self.discarded_box = StatBox("废弃（已标记）", "#E5484D")
        self.c4_box = StatBox("背包 0 级目标 C4", "#4F6BFF")
        self.rounds_box = StatBox("已刷 Boss 轮数", "#8B5CF6")
        for i, box in enumerate((self.graduated_box, self.discarded_box, self.c4_box, self.rounds_box)):
            stats.addWidget(box, 0, i)
        layout.addLayout(stats)

        log_card = Card("运行日志", shadow=True)
        self.current_label = label("当前声骸：—", "hint")
        self.substat_label = label("副词条：—", "hint")
        log_card.body.addWidget(self.current_label)
        log_card.body.addWidget(self.substat_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        log_card.body.addWidget(self.log_view, 1)
        layout.addWidget(log_card, 1)
        self._set_status("idle")

    # ---------- 页面 ----------

    def _hero_card(self) -> Card:
        card = Card()
        head = QHBoxLayout()
        head.setSpacing(16)
        self.avatar = Avatar("?", 64)
        head.addWidget(self.avatar)
        names = QVBoxLayout()
        names.setSpacing(4)
        self.name_label = label("还没有角色方案", "bigName")
        self.set_label = label("点左侧“新建角色”开始", "hint")
        names.addWidget(self.name_label)
        names.addWidget(self.set_label)
        head.addLayout(names, 1)
        card.body.addLayout(head)
        self.main_label = label("", "hint", wrap=True)
        card.body.addWidget(self.main_label)
        self.tag_flow = FlowLayout(4)
        card.body.addLayout(self.tag_flow)
        self.farm_label = label("", "hint", wrap=True)
        card.body.addWidget(self.farm_label)
        card.body.addStretch(1)
        return card

    def _control_card(self) -> Card:
        card = Card()
        self.farm_row = ToggleRow("刷取声骸", "按方案刷无音区 / Boss", True)
        self.enhance_row = ToggleRow("升级声骸", "逐个升级 0 级声骸并判断去留", True)
        card.body.addWidget(self.farm_row)
        card.body.addWidget(self.enhance_row)
        card.body.addSpacing(6)
        self.start_button = button("开 始", "start")
        self.start_button.setMinimumHeight(78)
        self.start_button.clicked.connect(self._on_start_clicked)
        card.body.addWidget(self.start_button)
        status = QHBoxLayout()
        self.status_dot = label("●")
        self.status_text = label("待机")
        self.status_text.setStyleSheet("font-size: 13px; font-weight: 600;")
        status.addStretch(1)
        status.addWidget(self.status_dot)
        status.addWidget(self.status_text)
        status.addStretch(1)
        card.body.addLayout(status)
        card.body.addWidget(label("开始前请先进游戏，并在背包声骸页设好筛选：五星 + 该角色套装，按等级从低到高排序。",
                                  "hint", wrap=True))
        return card

    def show_profile(self, profile: Profile | None):
        self.profile = profile
        self.tag_flow.clear()
        if profile is None:
            self.avatar.set_name("?")
            self.name_label.setText("还没有角色方案")
            self.set_label.setText("点左侧“新建角色”开始")
            self.main_label.setText("")
            self.farm_label.setText("")
            return
        self.avatar.set_name(profile.name)
        self.name_label.setText(profile.name)
        self.set_label.setText(f"套装：{profile.sonata_set}　·　喂料：{FODDER_PRIORITIES[profile.fodder_priority]}")
        mains = "　".join(f"C{cost}：{'/'.join(stats) if stats else '不要'}"
                         for cost, stats in sorted(profile.main_stats.items(), reverse=True))
        self.main_label.setText(f"主词条　{mains}")
        for stat in profile.required:
            self.tag_flow.add(StatTag(stat, "required", clickable=False))
        for stat in profile.optional:
            self.tag_flow.add(StatTag(stat, "optional", clickable=False))
        farm = profile.farm
        parts = []
        if farm.farm_c1c3:
            parts.append(f"无音区 #{farm.tacet_index}（{'只用当日体力' if farm.stamina_mode == 'daily' else '体力和结晶全用'}）")
        if farm.farm_c4:
            parts.append(f"{C4_TELEPORT_LABELS[farm.c4_teleport]} #{farm.c4_index} Lv{farm.c4_boss_level}，"
                         f"攒 {farm.c4_target} 个")
        self.farm_label.setText("刷取　" + ("；".join(parts) if parts else "不刷"))

    # ---------- 运行 ----------

    def is_running(self) -> bool:
        return self.process is not None and self.process.state() != QProcess.NotRunning

    def _on_start_clicked(self):
        if self.is_running():
            self._stop()
        else:
            self.start()

    def start(self):
        if self.profile is None:
            self._log("请先选择或新建一个角色方案")
            return
        farm, enhance = self.farm_row.toggle.isChecked(), self.enhance_row.toggle.isChecked()
        if not farm and not enhance:
            self._log("“刷取声骸”和“升级声骸”至少开一个")
            return
        run_file = self.bridge.prepare_run(RunRequest(profile=self.profile.name, farm=farm, enhance=enhance))
        self.event_offset = 0
        self.finished_reported = False
        self.stop_requested_at = 0.0
        for box in (self.graduated_box, self.discarded_box, self.c4_box, self.rounds_box):
            box.set_value("0")
        self.log_view.clear()
        if not OKWW_PYTHONW.is_file():
            self._log(f"找不到无窗口的 Python：{OKWW_PYTHONW}")
            self._set_status("error")
            return

        process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert(RUN_ENV, str(run_file))
        env.insert("PYTHONIOENCODING", "utf-8")
        process.setProcessEnvironment(env)
        process.setWorkingDirectory(str(OKWW_DIR))
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.setStandardOutputFile(str(OKWW_OUTPUT))
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_process_error)
        self.process = process
        process.start(str(OKWW_PYTHONW), ["main.py", "-t", TASK_CLASS, "-h"])
        self._log(f"启动 ok-ww 后台任务：{self.profile.name}（刷取 {'开' if farm else '关'}，升级 {'开' if enhance else '关'}）")
        self._set_status("running")
        self.poll_timer.start()
        self.running_changed.emit(True)

    def _stop(self):
        if self.stop_requested_at and time.time() - self.stop_requested_at > 1:
            self._log("强制结束 ok-ww 进程")
            self._kill()
            return
        self.bridge.request_stop()
        self.stop_requested_at = time.time()
        self._set_status("stopping")
        self._log(f"已请求停止，会在当前这一步做完后停下。再点一次按钮会强制结束"
                  f"（{STOP_GRACE_SECONDS} 秒内没停下也会强制结束）")
        QTimer.singleShot(STOP_GRACE_SECONDS * 1000, self._kill_if_still_running)

    def _kill_if_still_running(self):
        if self.is_running() and self.stop_requested_at:
            self._log(f"{STOP_GRACE_SECONDS} 秒内没有停下，强制结束 ok-ww 进程")
            self._kill()

    def _kill(self):
        if self.is_running():
            subprocess.run(["taskkill", "/PID", str(self.process.processId()), "/T", "/F"],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def shutdown(self):
        self._kill()

    def _on_process_error(self, error):
        if error == QProcess.FailedToStart:
            self._log(f"启动 ok-ww 失败：{OKWW_PYTHONW}")
            self._set_status("error")
            self._finish()

    def _on_finished(self, code: int, _status):
        self._poll_events()
        if not self.finished_reported:
            if self.stop_requested_at:
                self._log("ok-ww 已停止")
                self._set_status("idle")
            else:
                self._log(f"ok-ww 意外退出（退出码 {code}），详细输出见 {OKWW_OUTPUT}")
                self._set_status("error")
        self._finish()

    def _finish(self):
        self.poll_timer.stop()
        self.stop_requested_at = 0.0
        self.process = None
        self.running_changed.emit(False)

    def _poll_events(self):
        events, self.event_offset = self.bridge.read_events(self.event_offset)
        for event in events:
            self._handle_event(event)

    def _handle_event(self, event: dict):
        kind = event["kind"]
        if kind == "log":
            self._log(event["text"])
        elif kind == "stat":
            self._update_stat(event["key"], event["value"])
        elif kind == "ask":
            self._ask(event)
        elif kind == "done":
            self.finished_reported = True
            self._log(event["text"])
            self._set_status("done")
            self._notify()
        elif kind == "error":
            self.finished_reported = True
            self._log(f"出错：{event['text']}")
            self._set_status("error")
            self._notify()

    def _update_stat(self, key: str, value):
        if key == "成功声骸数量":
            self.graduated_box.set_value(value)
        elif key == "失败声骸数量":
            self.discarded_box.set_value(value)
        elif key == "背包 0 级目标 C4":
            self.c4_box.set_value(value)
        elif key == "已刷 Boss 轮数":
            self.rounds_box.set_value(value)
        elif key == "当前声骸":
            self.current_label.setText(f"当前声骸：{value}")
        elif key == "副词条":
            self.substat_label.setText(f"副词条：{value}")

    def _ask(self, event: dict):
        self._notify()
        dialog = AskDialog(self.window(), event["title"], event["text"])
        yes = dialog.exec() == QDialog.Accepted
        self.bridge.answer(event["id"], yes)
        self._log(f"你选择了：{'继续' if yes else '到此为止'}")

    def _notify(self):
        window = self.window()
        window.showNormal()
        window.raise_()
        window.activateWindow()
        QApplication.alert(window, 0)
        QApplication.beep()

    def _set_status(self, status: str):
        color, text = STATUS_COLORS[status]
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.status_text.setText(text)
        running = status in ("running", "stopping")
        self.start_button.setText("停 止" if running else "开 始")
        self.start_button.setProperty("running", "true" if running else "false")
        self.start_button.style().unpolish(self.start_button)
        self.start_button.style().polish(self.start_button)

    def _log(self, text: str):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")
