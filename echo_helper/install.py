"""把声骸助手任务挂进 ok-ww 的自定义任务目录 ok_tasks。"""

from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
OKWW_DIR = Path(r"D:\ok-wuthering-waves")
OKWW_PYTHON = OKWW_DIR / ".venv" / "python.exe"
OKWW_PYTHONW = OKWW_DIR / ".venv" / "pythonw.exe"
TASK_CLASS = "EchoHelperTask"


def entry_source(repo: Path = REPO_DIR) -> str:
    return f'''import sys

_REPO = r"{repo}"
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from echo_helper.okww_task import EchoHelperTask as _EchoHelperTask


class {TASK_CLASS}(_EchoHelperTask):
    pass
'''


def ensure_installed(okww: Path = OKWW_DIR, repo: Path = REPO_DIR) -> Path:
    """写入（或更新）ok_tasks 入口文件，返回它的路径。"""
    if not (okww / "main.py").is_file():
        raise FileNotFoundError(f"找不到 ok-ww：{okww}")
    target = okww / "ok_tasks" / f"{TASK_CLASS}.py"
    source = entry_source(repo)
    if not target.is_file() or target.read_text(encoding="utf-8-sig") != source:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    return target


if __name__ == "__main__":
    print(f"已安装：{ensure_installed()}")
