"""ok-ww 自定义任务：按角色方案刷声骸、升级并判断去留。

只能在 ok-ww 进程里导入（依赖 ok-script 和 ok-ww 的 src 包）。
"""

import ctypes
import re
import time

import cv2
from ok.feature.Box import get_bounding_box
from src.task.EnhanceEchoTask import EnhanceEchoTask
from src.task.FarmEchoTask import FarmEchoTask
from src.task.TacetTask import TacetTask

from echo_helper.bridge import bridge_from_env
from echo_helper.judge import Verdict, judge_main_stat, judge_substats
from echo_helper.parse import pair_rows, parse_main_stat, parse_substat
from echo_helper.profile import (GRADUATE_ASK_AT, GRADUATE_STOP_AT, Profile, list_profiles,
                                 load_profile)

PROFILE_KEY = "角色方案"
FARM_KEY = "刷取声骸"
ENHANCE_KEY = "升级声骸"
GRADUATED = "成功声骸数量"
DISCARDED = "失败声骸数量"

TACET_STAMINA = 60
# farm_tacet 把 180 - used_stamina 当作必须消耗的体力，给一个极大值就会一直用到备用结晶耗尽。
UNLIMITED_STAMINA = 10 ** 9

C4_INDEX_KEYS = {
    "Weekly Challenge": "Which Weekly Boss to Teleport",
    "Boss Challenge": "Which Boss Challenge to Teleport",
    "Special Nightmare": "Which Special Nightmare to Teleport",
}

BAG_ECHO_TAB = (0.034, 0.293)
BAG_FIRST_CELL = (0.13, 0.21)
BAG_CELL_STEP = (0.0869, 0.191)
BAG_COLUMNS = 6
BAG_ROWS = 4
BAG_CELL_HALF = (0.035, 0.08)
BAG_GRID_BOX = (0.085, 0.09, 0.625, 0.87)
BAG_LAST_CLICK_Y = 0.80
BAG_SORT_TOGGLE = (0.35, 0.917)
BAG_COST_BOX = (0.87, 0.17, 0.98, 0.24)
BAG_MAIN_STAT_BOX = (0.68, 0.38, 0.98, 0.48)
BAG_DETAIL_BOX = (0.68, 0.36, 0.98, 0.90)
# 空格子是纯色背景，有声骸的格子有头像。落在两者之间就停下，不靠猜。
BAG_EMPTY_CELL_STD = 10
BAG_FILLED_CELL_STD = 28
BAG_ROW_MATCH = 0.85

ENHANCE_SETTINGS_GEAR = (0.332, 0.646)
SETTINGS_PANEL_BOX = (0.15, 0.12, 0.90, 0.80)
# 选项卡片右端的圆形勾选框：选中是深色实心，未选中是白色空心。
CHECK_X_LEFT_CARD = 0.473
CHECK_X_RIGHT_CARD = 0.863
CHECKED_MAX_GRAY = 110
UNCHECKED_MIN_GRAY = 170
FODDER_OPTION_TEXT = {"echo": "强化材料和声骸", "material": "仅强化材料"}
RARITY_DROPDOWN = (0.17, 0.647)
RARITY_MENU_BOX = (0.08, 0.30, 0.32, 0.66)
RARITY_LABEL_BOX = (0.10, 0.62, 0.25, 0.675)
MATERIAL_SORT_BUTTON = (0.83, 0.92)
MATERIAL_SORT_MENU_BOX = (0.60, 0.45, 0.98, 0.93)
MATERIAL_SORT_LABEL_BOX = (0.68, 0.88, 0.98, 0.97)
MATERIAL_SORT_TARGET = "等级顺序"
SUBSTAT_BOX = (0.09, 0.3, 0.40, 0.53)

_COST_PATTERN = re.compile(r"COST\s*(\d)", re.IGNORECASE)

MB_YESNO = 0x04
MB_ICONQUESTION = 0x20
MB_TOPMOST = 0x40000
MB_SETFOREGROUND = 0x10000
IDYES = 6


class StopRequested(Exception):
    pass


class EchoHelperTask(EnhanceEchoTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "🎯 声骸助手（按角色刷取 + 升级判断）"
        self.description = ("在“声骸助手”桌面软件里建好角色方案。升级前在背包声骸页设置筛选："
                            "五星 + 该角色套装，并按等级从低到高排序。")
        for key in ('必须有双爆', '双爆出现之前必须全有效词条', '双爆总计>=', '首条双爆>=', '有效词条>=',
                    '第一条必须为有效词条', '有效词条', 'Pause after Success'):
            self.default_config.pop(key, None)
            self.config_type.pop(key, None)
            self.config_description.pop(key, None)
        profiles = list_profiles()
        self.default_config.update({
            PROFILE_KEY: profiles[0] if profiles else "",
            FARM_KEY: True,
            ENHANCE_KEY: True,
        })
        self.config_type[PROFILE_KEY] = {"type": "drop_down", "options": profiles}
        self.config_description.update({
            PROFILE_KEY: "profiles 目录里的角色方案",
            FARM_KEY: "按方案刷 C1/C3（无音区）和 C4（Boss）",
            ENHANCE_KEY: "刷完后在背包里逐个升级 0 级声骸并判断去留",
        })
        self.skip_count = 0
        self.bridge = None
        self.graduate_limit = GRADUATE_ASK_AT

    def validate_config(self, key, value):
        if key == PROFILE_KEY and value not in list_profiles():
            return "还没有这个角色方案，请先在声骸助手软件里新建"
        return None

    def run(self):
        self.bridge = bridge_from_env()
        if self.bridge:
            request = self.bridge.load_request()
            profile_name, do_farm, do_enhance = request.profile, request.farm, request.enhance
        else:
            profile_name = self.config.get(PROFILE_KEY)
            do_farm, do_enhance = self.config.get(FARM_KEY), self.config.get(ENHANCE_KEY)
        try:
            profile = load_profile(profile_name)
            self.graduate_limit = GRADUATE_ASK_AT
            self.report_stat("角色方案", profile.name)
            self.report_stat(GRADUATED, 0)
            self.report_stat(DISCARDED, 0)
            if do_farm:
                self.farm(profile)
            if do_enhance:
                self.open_echo_bag()
                self.enhance_all(profile)
            self.emit("done", text="全部完成")
        except StopRequested:
            self.emit("done", text="已按你的要求停止")
        except Exception as e:
            self.emit("error", text=str(e))
            raise

    # ---------- 通信 ----------

    def emit(self, kind: str, **data):
        if self.bridge:
            self.bridge.emit(kind, **data)

    def report(self, text: str, notify: bool = False):
        self.log_info(text, notify=notify)
        self.emit("log", text=text)

    def report_stat(self, key: str, value):
        self.info_set(key, value)
        self.emit("stat", key=key, value=value)

    def check_stop(self):
        if self.bridge and self.bridge.stop_requested():
            raise StopRequested()

    def ask_user(self, question_id: str, title: str, text: str) -> bool:
        if self.bridge:
            return self.bridge.ask(question_id, title, text, wait=self.sleep)
        flags = MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND
        return ctypes.windll.user32.MessageBoxW(None, text, title, flags) == IDYES

    # ---------- 刷取 ----------

    def farm(self, profile: Profile):
        if profile.farm.farm_c1c3:
            self.farm_c1c3(profile)
        if profile.farm.farm_c4:
            self.farm_c4(profile)

    def farm_c1c3(self, profile: Profile):
        self.check_stop()
        tacet = self.get_task_by_class(TacetTask)
        old_info = tacet.info
        tacet.info = self.info
        try:
            tacet.ensure_main(time_out=180)
            tacet.wait_in_team_and_world(esc=True)
            tacet_config = {"Which Tacet Suppression to Farm": profile.farm.tacet_index}
            if profile.farm.stamina_mode == "daily":
                tacet.openF2Book("gray_book_boss")
                current, back_up, _ = tacet.get_stamina()
                if current == -1:
                    raise Exception("读不到体力，请确认 F2 书页能正常打开")
                tacet.ensure_main()
                if current < TACET_STAMINA:
                    self.report(f"当日体力 {current} 不够一次无音区，跳过 C1/C3（储存结晶 {back_up} 未使用）")
                    return
                self.report(f"开始刷无音区，用完当日体力 {current}")
                tacet.farm_tacet(daily=False, config=tacet_config)
            else:
                self.report("开始刷无音区，当日体力和储存结晶全部用完")
                tacet.farm_tacet(daily=True, used_stamina=180 - UNLIMITED_STAMINA, config=tacet_config)
        finally:
            tacet.info = old_info
        self.report("无音区刷完")

    def farm_c4(self, profile: Profile):
        farm = profile.farm
        rounds = 0
        while True:
            self.check_stop()
            count = self.count_target_c4(profile)
            self.report_stat("背包 0 级目标 C4", f"{count}/{farm.c4_target}")
            if count >= farm.c4_target:
                self.report(f"背包里已有 {count} 个 0 级 {profile.sonata_set} C4，去升级")
                return
            if rounds >= farm.c4_max_rounds:
                raise Exception(f"已刷 {rounds} 轮 Boss，0 级 {profile.sonata_set} C4 只有 {count} 个，"
                                f"没到 {farm.c4_target} 个。请确认 Boss 选对了，或调高最多轮数")
            batch = min(farm.c4_batch, farm.c4_max_rounds - rounds)
            self.report(f"目前 {count}/{farm.c4_target} 个，再刷 {batch} 轮 Boss（已刷 {rounds} 轮）")
            self.run_farm_echo(profile, batch)
            rounds += batch
            self.report_stat("已刷 Boss 轮数", rounds)

    def run_farm_echo(self, profile: Profile, rounds: int):
        farm_task = self.get_task_by_class(FarmEchoTask)
        overrides = {
            "Teleport to Boss": profile.farm.c4_teleport,
            C4_INDEX_KEYS[profile.farm.c4_teleport]: profile.farm.c4_index,
            "Boss Level": profile.farm.c4_boss_level,
            "Repeat Farm Count": rounds,
        }
        previous = {key: farm_task.config.get(key) for key in overrides}
        try:
            for key, value in overrides.items():
                farm_task.config[key] = value
            self.run_task_by_class(FarmEchoTask)
        finally:
            for key, value in previous.items():
                farm_task.config[key] = value

    def count_target_c4(self, profile: Profile) -> int:
        """在背包里数 0 级、COST4、目标套装的声骸，数到目标数就停。"""
        self.open_echo_bag()
        self.bag_to_top()
        count = 0
        for point in self.iter_bag_cells():
            self.click_relative(*point, after_sleep=0.5)
            if not self.is_0_level():
                break
            if self.read_bag_cost() == 4 and self.read_bag_set_ok(profile):
                count += 1
                if count >= profile.farm.c4_target:
                    break
        self.close_bag()
        return count

    # ---------- 背包 ----------

    def open_echo_bag(self):
        self.ensure_main(time_out=180)
        hotkey = self.key_config.get("Bag Key", "b")
        self.send_key(hotkey)
        if not self.wait_until(lambda: not self.in_team_and_world(), time_out=5, raise_if_not_found=False):
            raise Exception(f"按 {hotkey} 打不开背包")
        self.sleep(2)
        self.click_relative(*BAG_ECHO_TAB, after_sleep=1)
        if not self.find_echo_enhance():
            raise Exception("没有进入背包的声骸页")

    def close_bag(self):
        self.ensure_main(time_out=30)

    def bag_to_top(self):
        """点两次升降序，列表回到顶部且排序方向不变。"""
        for _ in range(2):
            self.click_relative(*BAG_SORT_TOGGLE, after_sleep=0.5)

    def fresh_frame(self):
        frame = self.next_frame()
        if frame is None:
            raise Exception("取不到游戏画面")
        return frame

    def cell_has_echo(self, point) -> bool:
        frame = self.fresh_frame()
        x0 = int((point[0] - BAG_CELL_HALF[0]) * self.width)
        x1 = int((point[0] + BAG_CELL_HALF[0]) * self.width)
        y0 = int((point[1] - BAG_CELL_HALF[1]) * self.height)
        y1 = int((point[1] + BAG_CELL_HALF[1]) * self.height)
        gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        std = float(gray.std())
        if std >= BAG_FILLED_CELL_STD:
            return True
        if std <= BAG_EMPTY_CELL_STD:
            return False
        self.screenshot("echo_helper_bag_cell")
        raise Exception(f"无法判断这个格子有没有声骸（对比度 {std:.0f}），已截图 echo_helper_bag_cell")

    def iter_bag_cells(self):
        """从当前列表顶部开始，按顺序给出每个有声骸的格子坐标，必要时向下滚动。"""
        row_ys = [BAG_FIRST_CELL[1] + BAG_CELL_STEP[1] * row for row in range(BAG_ROWS)]
        while True:
            for y in row_ys:
                for column in range(BAG_COLUMNS):
                    point = (BAG_FIRST_CELL[0] + BAG_CELL_STEP[0] * column, y)
                    if not self.cell_has_echo(point):
                        return
                    yield point
            last_y = self.scroll_bag_past(row_ys[-1])
            if last_y is None:
                return
            row_ys = []
            y = last_y + BAG_CELL_STEP[1]
            while y <= BAG_LAST_CLICK_Y:
                row_ys.append(y)
                y += BAG_CELL_STEP[1]
            if not row_ys:
                raise Exception("背包滚动后没有露出新的一行，无法继续")

    def scroll_bag_past(self, row_y: float) -> float | None:
        """一格一格向下滚，直到 row_y 这一行移到最上面一行附近。

        返回这一行滚动后的中心 y；列表已经到底（滚不动）时返回 None。
        """
        frame = self.fresh_frame()
        gx0, gy0 = int(BAG_GRID_BOX[0] * self.width), int(BAG_GRID_BOX[1] * self.height)
        gx1, gy1 = int(BAG_GRID_BOX[2] * self.width), int(BAG_GRID_BOX[3] * self.height)
        ty0 = int((row_y - BAG_CELL_HALF[1]) * self.height)
        ty1 = int((row_y + BAG_CELL_HALF[1]) * self.height)
        template = frame[ty0:ty1, gx0:gx1].copy()
        current_y = row_y
        center = ((BAG_GRID_BOX[0] + BAG_GRID_BOX[2]) / 2, (BAG_GRID_BOX[1] + BAG_GRID_BOX[3]) / 2)
        while current_y > BAG_FIRST_CELL[1] + BAG_CELL_STEP[1] / 2:
            self.scroll_relative(*center, -1)
            self.sleep(0.6)
            frame = self.fresh_frame()
            result = cv2.matchTemplate(frame[gy0:gy1, gx0:gx1], template, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(result)
            if score < BAG_ROW_MATCH:
                self.screenshot("echo_helper_bag_scroll")
                raise Exception("背包滚动后找不到上一屏的最后一行（可能一次滚太多），已截图 echo_helper_bag_scroll")
            new_y = (gy0 + location[1] + (ty1 - ty0) / 2) / self.height
            if abs(new_y - current_y) < 0.005:
                return None if current_y == row_y else current_y
            current_y = new_y
        return current_y

    def select_echo(self, index: int) -> bool:
        """选中列表里第 index 个声骸；它不是 0 级或不存在时返回 False。"""
        self.bag_to_top()
        for i, point in enumerate(self.iter_bag_cells()):
            if i == index:
                self.click_relative(*point, after_sleep=0.5)
                return bool(self.is_0_level())
        return False

    def read_bag_cost(self) -> int:
        cost_boxes = self.ocr(*BAG_COST_BOX, match=_COST_PATTERN)
        if not cost_boxes:
            self.screenshot("echo_helper_cost_unreadable")
            raise Exception("读不到声骸 COST，已截图 echo_helper_cost_unreadable")
        return int(_COST_PATTERN.search(cost_boxes[0].name).group(1))

    def read_bag_main_stat(self, cost: int) -> str:
        main_texts = self.ocr(*BAG_MAIN_STAT_BOX)
        rows = pair_rows([(box.name, box.y) for box in main_texts], max_dy=self.height * 0.015)
        if not rows:
            self.screenshot("echo_helper_main_unreadable")
            raise Exception("读不到声骸主词条，已截图 echo_helper_main_unreadable")
        return parse_main_stat(cost, *rows[0])

    def read_bag_set_ok(self, profile: Profile) -> bool:
        detail = "".join(box.name for box in self.ocr(*BAG_DETAIL_BOX))
        return profile.sonata_set in detail

    def is_locked(self) -> bool:
        lock_box = get_bounding_box([
            self.get_box_by_name('echo_locked'),
            self.get_box_by_name('echo_not_locked'),
        ]).scale(1.05)
        state = self.find_best_match_in_box(lock_box, ['echo_locked', 'echo_not_locked'], threshold=0.7)
        if not state:
            raise Exception("无法判断声骸是否上锁")
        return state.name == 'echo_locked'

    # ---------- 升级 ----------

    def enhance_all(self, profile: Profile):
        self.skip_count = 0
        rule = profile.substat_rule()
        allowed = profile.allowed_main_stats()
        settings_applied = False
        while True:
            self.check_stop()
            if not self.find_echo_enhance():
                raise Exception("不在背包声骸页")
            if not self.select_echo(self.skip_count):
                self.report(f"0 级声骸处理完毕：毕业 {self.info_get(GRADUATED)} 个，"
                            f"废弃 {self.info_get(DISCARDED)} 个", notify=True)
                return

            if self.is_locked():
                self.report("这个 0 级声骸已上锁，不动它，跳过")
                self.skip_count += 1
                continue
            cost = self.read_bag_cost()
            main_stat = self.read_bag_main_stat(cost)
            if not self.read_bag_set_ok(profile):
                self.report(f"不是 {profile.sonata_set} 套装，跳过（不打废弃标记）")
                self.skip_count += 1
                continue

            self.report_stat("当前声骸", f"COST{cost} {main_stat}")
            main_decision = judge_main_stat(cost, main_stat, allowed)
            if main_decision.verdict is Verdict.DISCARD:
                self.report(main_decision.reason)
                self.fail_reason = main_decision.reason
                self.open_enhance_page()
                self.trash_and_esc()
                self.report_stat(DISCARDED, self.info_get(DISCARDED))
                self.skip_count += 1
                continue

            self.open_enhance_page()
            if not settings_applied:
                self.apply_enhance_settings(profile.fodder_priority)
                settings_applied = True
            if self.enhance_until_decided(rule) is Verdict.LOCK and not self.after_graduate():
                return

    def after_graduate(self) -> bool:
        """毕业后检查上限，返回是否继续升级。"""
        graduated = self.info_get(GRADUATED)
        self.report_stat(GRADUATED, graduated)
        if graduated < self.graduate_limit:
            return True
        if self.graduate_limit >= GRADUATE_STOP_AT:
            self.report(f"已毕业 {graduated} 个，达到上限，结束升级", notify=True)
            return False
        yes = self.ask_user(
            "graduate", "声骸助手",
            f"本次已经毕业 {graduated} 个声骸。\n继续升级的话，做到 {GRADUATE_STOP_AT} 个毕业后结束。\n\n要继续吗？")
        if not yes:
            self.report(f"已毕业 {graduated} 个，按你的选择停止")
            return False
        self.graduate_limit = GRADUATE_STOP_AT
        self.report(f"继续升级，做到 {GRADUATE_STOP_AT} 个毕业后结束")
        return True

    def open_enhance_page(self):
        enhance = self.find_echo_enhance()
        start = time.time()
        while enhance and time.time() - start < 5:
            self.click(enhance, after_sleep=0.5)
            enhance = self.find_echo_enhance()
        if enhance:
            raise Exception("点不进培养页")

    def option_checked(self, check_point) -> bool:
        frame = self.fresh_frame()
        x, y = int(check_point[0] * self.width), int(check_point[1] * self.height)
        r = max(2, int(self.height * 0.005))
        gray = float(cv2.cvtColor(frame[y - r:y + r + 1, x - r:x + r + 1], cv2.COLOR_BGR2GRAY).mean())
        if gray <= CHECKED_MAX_GRAY:
            return True
        if gray >= UNCHECKED_MIN_GRAY:
            return False
        self.screenshot("echo_helper_check_unclear")
        raise Exception(f"看不清勾选框状态（灰度 {gray:.0f}），已截图 echo_helper_check_unclear")

    def find_option(self, boxes, text: str):
        matched = [box for box in boxes if box.name.strip() == text] or [box for box in boxes if text in box.name]
        if not matched:
            seen = "、".join(box.name for box in boxes) or "（没有识别到文字）"
            self.screenshot("echo_helper_enhance_settings")
            raise Exception(f"自动放入设置里找不到“{text}”。识别到：{seen}。已截图 echo_helper_enhance_settings")
        return matched[0]

    def select_setting(self, boxes, text: str):
        box = self.find_option(boxes, text)
        check_x = CHECK_X_RIGHT_CARD if box.center()[0] / self.width > 0.5 else CHECK_X_LEFT_CARD
        check_point = (check_x, box.center()[1] / self.height)
        if not self.option_checked(check_point):
            self.click(box, after_sleep=0.6)
            if not self.option_checked(check_point):
                self.screenshot("echo_helper_enhance_settings")
                raise Exception(f"点了“{text}”但没有勾上，已截图 echo_helper_enhance_settings")
        self.report(f"自动放入设置：{text} ✓")

    def apply_enhance_settings(self, fodder_priority: str):
        """把自动放入设置切到 阶段放入 + 开启同步调谐 + 方案的放入材料，品质设为不限，排序设为等级顺序。"""
        self.click_relative(*ENHANCE_SETTINGS_GEAR, after_sleep=1)
        if not self.wait_ocr(*SETTINGS_PANEL_BOX, match="自动放入设置", time_out=3):
            self.screenshot("echo_helper_enhance_settings")
            raise Exception("没打开自动放入设置，已截图 echo_helper_enhance_settings")
        boxes = self.ocr(*SETTINGS_PANEL_BOX)
        for text in ("阶段放入", "开启同步调谐", FODDER_OPTION_TEXT[fodder_priority]):
            self.select_setting(boxes, text)
        if not self.wait_click_ocr(0.55, 0.78, 0.92, 0.92, match="确认", time_out=2, after_sleep=1):
            self.screenshot("echo_helper_enhance_settings")
            raise Exception("找不到自动放入设置的“确认”，已截图 echo_helper_enhance_settings")
        if self.ocr(*SETTINGS_PANEL_BOX, match="自动放入设置"):
            raise Exception("点了确认，自动放入设置没有关闭")

        self.click_relative(*RARITY_DROPDOWN, after_sleep=0.6)
        menu = self.ocr(*RARITY_MENU_BOX)
        any_rarity = [box for box in menu if box.name.strip() == "不限"] or [box for box in menu if "不限" in box.name]
        if not any_rarity:
            seen = "、".join(box.name for box in menu) or "（没有识别到文字）"
            self.screenshot("echo_helper_rarity")
            raise Exception(f"品质菜单里没有“不限”。识别到：{seen}。已截图 echo_helper_rarity")
        self.click(any_rarity[0], after_sleep=0.6)
        if not self.wait_ocr(*RARITY_LABEL_BOX, match="不限", time_out=2):
            self.screenshot("echo_helper_rarity")
            raise Exception("材料品质没切到“不限”，已截图 echo_helper_rarity")
        self.report("材料品质上限：不限 ✓")
        self.apply_material_sort()

    def apply_material_sort(self):
        """把材料列表排序切成“等级顺序”，用来让已强化声骸排在密音筒前面。是否真按这个顺序取料，进游戏实测。"""
        self.click_relative(*MATERIAL_SORT_BUTTON, after_sleep=0.6)
        menu = self.ocr(*MATERIAL_SORT_MENU_BOX)
        matched = ([box for box in menu if box.name.strip() == MATERIAL_SORT_TARGET]
                   or [box for box in menu if MATERIAL_SORT_TARGET in box.name])
        if not matched:
            seen = "、".join(box.name for box in menu) or "（没有识别到文字）"
            self.screenshot("echo_helper_material_sort")
            raise Exception(f"材料排序菜单里没有“{MATERIAL_SORT_TARGET}”。识别到：{seen}。"
                            "已截图 echo_helper_material_sort")
        self.click(matched[0], after_sleep=0.6)
        if not self.wait_ocr(*MATERIAL_SORT_LABEL_BOX, match=MATERIAL_SORT_TARGET, time_out=2):
            self.screenshot("echo_helper_material_sort")
            raise Exception(f"材料排序没切到“{MATERIAL_SORT_TARGET}”，已截图 echo_helper_material_sort")
        self.report(f"材料排序：{MATERIAL_SORT_TARGET} ✓（先吃声骸还是先吃密音筒，第一次运行时看材料列表确认）")

    def read_substats(self):
        texts = self.ocr(*SUBSTAT_BOX)
        rows = pair_rows([(box.name, box.y) for box in texts], max_dy=self.height * 0.015)
        return [parse_substat(name, value) for name, value in rows]

    def enhance_until_decided(self, rule) -> Verdict:
        while True:
            self.check_stop()
            have_add_mat = False
            start_wait = time.time()
            while time.time() - start_wait < 5:
                add_mat = self.find_add_mat()
                if add_mat:
                    have_add_mat = True
                    self.click(add_mat, after_sleep=0.3)
                else:
                    self.next_frame()
                    if have_add_mat:
                        break
            if not have_add_mat:
                raise Exception("找不到“阶段放入”按钮，请确认材料充足")
            if not self.wait_click_ocr(0.1, 0.88, 0.29, 0.96, match=["强化并调谐"], settle_time=0.1,
                                       after_sleep=1.5):
                raise Exception("找不到“强化并调谐”，请确认材料和调谐器充足")
            while handle := self.wait_ocr(0.24, 0.18, 0.75, 0.98,
                                          match=[re.compile("不再提示"), "调谐成功", re.compile("点击任")],
                                          time_out=2):
                if "不再提示" in handle[0].name:
                    self.click_skip_dialog_confirm()
                else:
                    self.click(handle, after_sleep=1)
            self.sleep(0.1)

            substats = self.read_substats()
            decision = judge_substats(substats, rule)
            self.report_stat("副词条", " / ".join(f"{s.name} {s.value}" for s in substats))
            self.report(decision.reason)
            if decision.verdict is Verdict.CONTINUE:
                continue
            self.fail_reason = decision.reason
            if decision.verdict is Verdict.LOCK:
                self.lock_and_esc()
            else:
                self.trash_and_esc()
                self.report_stat(DISCARDED, self.info_get(DISCARDED))
            return decision.verdict
