"""桌面软件与 ok-ww 任务进程之间的文件通信。

软件写 run.json 并以环境变量 RUN_ENV 指向它启动 ok-ww；
任务把日志、计数和询问逐行追加到 events.jsonl，软件把回答写到 answer_<id>.json。
"""

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
RUN_ENV = "ECHO_HELPER_RUN"


@dataclass
class RunRequest:
    profile: str
    farm: bool
    enhance: bool


class Bridge:
    def __init__(self, folder: Path = RUNTIME_DIR):
        self.folder = folder
        self.events_path = folder / "events.jsonl"
        self.run_path = folder / "run.json"
        self.stop_path = folder / "stop.flag"

    # ---------- 软件端 ----------

    def prepare_run(self, request: RunRequest) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        for old in self.folder.glob("answer_*.json"):
            old.unlink()
        self.stop_path.unlink(missing_ok=True)
        self.events_path.write_text("", encoding="utf-8")
        self.run_path.write_text(json.dumps(asdict(request), ensure_ascii=False), encoding="utf-8")
        return self.run_path

    def read_events(self, offset: int) -> tuple[list[dict], int]:
        """从字节偏移 offset 读出新的完整事件行，返回 (事件, 新偏移)。"""
        if not self.events_path.is_file():
            return [], offset
        with self.events_path.open("rb") as f:
            f.seek(offset)
            data = f.read()
        end = data.rfind(b"\n") + 1
        events = [json.loads(line) for line in data[:end].decode("utf-8").splitlines() if line.strip()]
        return events, offset + end

    def answer(self, question_id: str, yes: bool):
        path = self.folder / f"answer_{question_id}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"yes": yes}), encoding="utf-8")
        tmp.replace(path)

    def request_stop(self):
        self.stop_path.write_text("stop", encoding="utf-8")

    # ---------- 任务端 ----------

    def load_request(self) -> RunRequest:
        return RunRequest(**json.loads(self.run_path.read_text(encoding="utf-8")))

    def emit(self, kind: str, **data):
        line = json.dumps({"time": time.time(), "kind": kind, **data}, ensure_ascii=False)
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def stop_requested(self) -> bool:
        return self.stop_path.is_file()

    def ask(self, question_id: str, title: str, text: str, wait, poll: float = 0.5) -> bool:
        """发出询问并阻塞等待回答。wait(seconds) 由调用方提供，以便任务被停止时能抛出异常退出。"""
        path = self.folder / f"answer_{question_id}.json"
        path.unlink(missing_ok=True)
        self.emit("ask", id=question_id, title=title, text=text)
        while not path.is_file():
            if self.stop_requested():
                return False
            wait(poll)
        return bool(json.loads(path.read_text(encoding="utf-8"))["yes"])


def bridge_from_env() -> Bridge | None:
    run_file = os.environ.get(RUN_ENV)
    if not run_file:
        return None
    return Bridge(Path(run_file).parent)
