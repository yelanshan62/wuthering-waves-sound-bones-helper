import tempfile
import threading
import unittest
from pathlib import Path

from echo_helper.bridge import Bridge, RunRequest


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bridge = Bridge(Path(self.tmp.name))
        self.bridge.prepare_run(RunRequest(profile="今汐", farm=True, enhance=False))

    def tearDown(self):
        self.tmp.cleanup()

    def test_request_round_trip(self):
        self.assertEqual(self.bridge.load_request(), RunRequest(profile="今汐", farm=True, enhance=False))

    def test_events_are_read_incrementally(self):
        self.bridge.emit("log", text="开始")
        events, offset = self.bridge.read_events(0)
        self.assertEqual([e["text"] for e in events], ["开始"])
        self.bridge.emit("stat", key="成功声骸数量", value=1)
        events, offset = self.bridge.read_events(offset)
        self.assertEqual([(e["kind"], e["value"]) for e in events], [("stat", 1)])
        self.assertEqual(self.bridge.read_events(offset), ([], offset))

    def test_partial_line_is_not_read(self):
        with self.bridge.events_path.open("a", encoding="utf-8") as f:
            f.write('{"kind": "log", "te')
        self.assertEqual(self.bridge.read_events(0), ([], 0))

    def test_ask_waits_for_answer(self):
        results = []
        thread = threading.Thread(
            target=lambda: results.append(self.bridge.ask("graduate", "标题", "继续吗", wait=lambda s: None, poll=0)))
        thread.start()
        while not any(e["kind"] == "ask" for e in self.bridge.read_events(0)[0]):
            pass
        self.bridge.answer("graduate", True)
        thread.join(timeout=5)
        self.assertEqual(results, [True])

    def test_stop_ends_question_with_no(self):
        self.bridge.request_stop()
        self.assertFalse(self.bridge.ask("graduate", "标题", "继续吗", wait=lambda s: None, poll=0))

    def test_prepare_clears_previous_run(self):
        self.bridge.emit("log", text="旧日志")
        self.bridge.answer("graduate", True)
        self.bridge.request_stop()
        self.bridge.prepare_run(RunRequest(profile="今汐", farm=False, enhance=True))
        self.assertEqual(self.bridge.read_events(0), ([], 0))
        self.assertFalse(self.bridge.stop_requested())
        self.assertFalse(list(Path(self.tmp.name).glob("answer_*.json")))


if __name__ == "__main__":
    unittest.main()
