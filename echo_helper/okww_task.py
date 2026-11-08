"""ok-ww 自定义任务：按角色方案刷声骸、升级并判断去留。

只能在 ok-ww 进程里导入（依赖 ok-script 和 ok-ww 的 src 包）。
"""

import re
import time

from ok.feature.Box import get_bounding_box
from src.task.EnhanceEchoTask import EnhanceEchoTask
from src.task.FarmEchoTask import FarmEchoTask
from src.task.TacetTask import TacetTask

from echo_helper.judge import Verdict, judge_main_stat, judge_substats
from echo_helper.parse import pair_rows, parse_main_stat, parse_substat
from echo_helper.profile import Profile, list_profiles, load_profile

PROFILE_KEY = "角色方案"
FARM_KEY = "刷取声骸"
ENHANCE_KEY = "升级声骸"

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
BAG_SORT_TOGGLE = (0.35, 0.917)
BAG_COST_BOX = (0.87, 0.17, 0.98, 0.24)
BAG_MAIN_STAT_BOX = (0.68, 0.38, 0.98, 0.48)
BAG_DETAIL_BOX = (0.68, 0.36, 0.98, 0.90)
ENHANCE_SETTINGS_GEAR = (0.332, 0.646)
SUBSTAT_BOX = (0.09, 0.3, 0.40, 0.53)

_COST_PATTERN = re.compile(r"COST\s*(\d)", re.IGNORECASE)

FODDER_OPTION_TEXT = {"material": "密音筒", "echo": "声骸"}


class EchoHelperTask(EnhanceEchoTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "🎯 声骸助手（按角色刷取 + 升级判断）"
        self.description = ("先用 tools/profile_editor.py 建好角色方案。升级前在背包声骸页设置筛选："
                            "五星 + 该角色套装 + 所需 COST，并按等级从低到高排序。")
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

    def validate_config(self, key, value):
        if key == PROFILE_KEY and value not in list_profiles():
            return "还没有这个角色方案，请先运行 tools/profile_editor.py 新建"
        return None

    def run(self):
        profile = load_profile(self.config.get(PROFILE_KEY))
        self.info_set("角色方案", profile.name)
        self.info_set("成功声骸数量", 0)
        self.info_set("失败声骸数量", 0)
        if self.config.get(FARM_KEY):
            self.farm(profile)
        if self.config.get(ENHANCE_KEY):
            self.open_echo_bag()
            self.enhance_all(profile)

    # ---------- 刷取 ----------

    def farm(self, profile: Profile):
        if profile.farm.farm_c1c3:
            self.farm_c1c3(profile)
        if profile.farm.farm_c4:
            self.farm_c4(profile)

    def farm_c1c3(self, profile: Profile):
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
                    self.log_info(f"当日体力 {current} 不够一次无音区，跳过 C1/C3（储存结晶 {back_up} 未使用）")
                    return
                tacet.farm_tacet(daily=False, config=tacet_config)
            else:
                tacet.farm_tacet(daily=True, used_stamina=180 - UNLIMITED_STAMINA, config=tacet_config)
        finally:
            tacet.info = old_info

    def farm_c4(self, profile: Profile):
        farm_task = self.get_task_by_class(FarmEchoTask)
        overrides = {
            "Teleport to Boss": profile.farm.c4_teleport,
            C4_INDEX_KEYS[profile.farm.c4_teleport]: profile.farm.c4_index,
            "Boss Level": profile.farm.c4_boss_level,
            "Repeat Farm Count": profile.farm.c4_count,
        }
        previous = {key: farm_task.config.get(key) for key in overrides}
        try:
            for key, value in overrides.items():
                farm_task.config[key] = value
            self.run_task_by_class(FarmEchoTask)
        finally:
            for key, value in previous.items():
                farm_task.config[key] = value
        self.ensure_main(time_out=180)

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

    def bag_cell(self, index: int) -> tuple[float, float]:
        column, row = index % BAG_COLUMNS, index // BAG_COLUMNS
        return (BAG_FIRST_CELL[0] + BAG_CELL_STEP[0] * column,
                BAG_FIRST_CELL[1] + BAG_CELL_STEP[1] * row)

    def select_next_echo(self) -> bool:
        """选中第 skip_count 个 0 级声骸；没有更多 0 级声骸时返回 False。"""
        if self.skip_count >= BAG_COLUMNS * BAG_ROWS:
            raise Exception(f"前 {self.skip_count} 个 0 级声骸都被跳过了，请收紧背包筛选（套装、COST、主词条）")
        self.click_relative(*BAG_FIRST_CELL, after_sleep=0.5)
        if not self.is_0_level():
            for _ in range(2):
                self.click_relative(*BAG_SORT_TOGGLE, after_sleep=0.5)
        self.click_relative(*self.bag_cell(self.skip_count), after_sleep=0.5)
        return bool(self.is_0_level())

    def read_bag_echo(self, profile: Profile) -> tuple[int, str, bool]:
        """在背包详情栏读出 (COST, 主词条, 套装是否符合)。"""
        cost_boxes = self.ocr(*BAG_COST_BOX, match=_COST_PATTERN)
        if not cost_boxes:
            self.screenshot("echo_helper_cost_unreadable")
            raise Exception("读不到声骸 COST")
        cost = int(_COST_PATTERN.search(cost_boxes[0].name).group(1))

        main_texts = self.ocr(*BAG_MAIN_STAT_BOX)
        rows = pair_rows([(box.name, box.y) for box in main_texts], max_dy=self.height * 0.015)
        if not rows:
            self.screenshot("echo_helper_main_unreadable")
            raise Exception("读不到声骸主词条")
        main_stat = parse_main_stat(cost, *rows[0])

        detail = "".join(box.name for box in self.ocr(*BAG_DETAIL_BOX))
        return cost, main_stat, profile.sonata_set in detail

    # ---------- 升级 ----------

    def enhance_all(self, profile: Profile):
        self.skip_count = 0
        rule = profile.substat_rule()
        allowed = profile.allowed_main_stats()
        fodder_applied = False
        while True:
            if not self.find_echo_enhance():
                raise Exception("不在背包声骸页")
            if not self.select_next_echo():
                self.log_info(f"0 级声骸处理完毕：毕业 {self.info_get('成功声骸数量')} 个，"
                              f"废弃 {self.info_get('失败声骸数量')} 个", notify=True)
                return

            cost, main_stat, set_ok = self.read_bag_echo(profile)
            if not set_ok:
                self.log_info(f"不是 {profile.sonata_set} 套装，跳过（不打废弃标记）")
                self.skip_count += 1
                continue

            self.open_enhance_page()
            if not fodder_applied:
                self.apply_fodder_priority(profile.fodder_priority)
                fodder_applied = True

            main_decision = judge_main_stat(cost, main_stat, allowed)
            self.info_set("当前声骸", f"COST{cost} {main_stat}")
            if main_decision.verdict is Verdict.DISCARD:
                self.log_info(main_decision.reason)
                self.fail_reason = main_decision.reason
                self.trash_and_esc()
                self.skip_count += 1
                continue

            self.enhance_until_decided(rule)

    def open_enhance_page(self):
        enhance = self.find_echo_enhance()
        start = time.time()
        while enhance and time.time() - start < 5:
            self.click(enhance, after_sleep=0.5)
            enhance = self.find_echo_enhance()
        if enhance:
            raise Exception("点不进培养页")

    def apply_fodder_priority(self, priority: str):
        """打开培养页齿轮里的强化设置，选中对应的优先消耗选项。"""
        self.click_relative(*ENHANCE_SETTINGS_GEAR, after_sleep=1)
        boxes = self.ocr(0.15, 0.1, 0.85, 0.9)
        keyword = FODDER_OPTION_TEXT[priority]
        options = [box for box in boxes if keyword in box.name and "优先" not in box.name]
        if priority == "echo":
            discarded_only = [box for box in boxes if "弃置" in box.name]
            if not discarded_only:
                self.screenshot("echo_helper_enhance_settings")
                raise Exception("强化设置里没找到“仅使用已弃置声骸”类选项，无法保证只吃废弃声骸。"
                                "已截图 echo_helper_enhance_settings，请发给开发者校准")
        if not options:
            self.screenshot("echo_helper_enhance_settings")
            raise Exception(f"强化设置里没找到“{keyword}”选项，已截图 echo_helper_enhance_settings，请发给开发者校准")
        self.click(options[0], after_sleep=0.5)
        if priority == "echo":
            self.click(discarded_only[0], after_sleep=0.5)
        self.log_info(f"强化设置已切到：{options[0].name}")
        self.send_key("esc", after_sleep=1)

    def read_substats(self):
        texts = self.ocr(*SUBSTAT_BOX)
        rows = pair_rows([(box.name, box.y) for box in texts], max_dy=self.height * 0.015)
        return [parse_substat(name, value) for name, value in rows]

    def enhance_until_decided(self, rule):
        while True:
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
                raise Exception("找不到“阶段放入”，请在强化设置中开启阶段放入")
            if not self.wait_click_ocr(0.1, 0.88, 0.29, 0.96, match=["强化并调谐"], settle_time=0.1,
                                       after_sleep=1.5):
                raise Exception("找不到“强化并调谐”，请在强化设置中开启同时调谐，并确认材料充足")
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
            self.info_set("副词条", " / ".join(f"{s.name} {s.value}" for s in substats))
            self.log_info(decision.reason)
            if decision.verdict is Verdict.CONTINUE:
                continue
            self.fail_reason = decision.reason
            if decision.verdict is Verdict.LOCK:
                self.lock_and_esc()
            else:
                self.trash_and_esc()
            return

    def ensure_unlocked(self):
        lock_box = get_bounding_box([
            self.get_box_by_name('echo_locked'),
            self.get_box_by_name('echo_not_locked'),
        ]).scale(1.05)
        state = self.find_best_match_in_box(lock_box, ['echo_locked', 'echo_not_locked'], threshold=0.7)
        if not state:
            raise Exception("无法判断声骸是否上锁")
        if state.name == 'echo_locked':
            self.send_key('c', after_sleep=1)
            state = self.find_best_match_in_box(lock_box, ['echo_locked', 'echo_not_locked'], threshold=0.7)
            if not state or state.name != 'echo_not_locked':
                raise Exception("解锁失败，无法打废弃标记")

    def trash_and_esc(self):
        self.ensure_unlocked()
        super().trash_and_esc()
