"""角色方案编辑页。"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QScrollArea,
                               QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from app.widgets import Card, FlowLayout, Segmented, StatTag, ToggleRow, button, chip, label
from echo_helper.profile import (C4_BOSS_LEVELS, C4_TELEPORT_LABELS, FODDER_PRIORITIES, STAMINA_MODES, FarmConfig,
                                 Profile, delete_profile, save_profile)
from echo_helper.stats import COSTS, MAIN_STATS_BY_COST, SUBSTATS


def spin(minimum: int, maximum: int) -> QSpinBox:
    widget = QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setFixedWidth(110)
    return widget


class ProfileEditor(QScrollArea):
    saved = Signal(str)
    deleted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.original_name: str | None = None
        content = QWidget()
        content.setObjectName("page")
        self.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 12, 24)
        layout.setSpacing(16)

        layout.addWidget(self._basic_card())
        layout.addWidget(self._farm_card())
        layout.addWidget(self._fodder_card())
        layout.addWidget(self._main_stat_card())
        layout.addWidget(self._substat_card())

        actions = QHBoxLayout()
        self.delete_button = button("删除这个方案", "danger")
        self.delete_button.clicked.connect(self._delete)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)
        save = button("保存方案", "primary")
        save.setMinimumWidth(160)
        save.clicked.connect(self.save)
        actions.addWidget(save)
        layout.addLayout(actions)
        layout.addStretch(1)
        self.fill(None)

    # ---------- 页面 ----------

    def _basic_card(self) -> Card:
        card = Card("角色", "套装名要和游戏里合鸣效果的名字完全一致，脚本靠它识别声骸套装。")
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：今汐")
        self.set_edit = QLineEdit()
        self.set_edit.setPlaceholderText("例如：浮星祛暗")
        form.addRow(label("角色名"), self.name_edit)
        form.addRow(label("套装名"), self.set_edit)
        card.body.addLayout(form)
        return card

    def _farm_card(self) -> Card:
        card = Card("刷取")
        self.c1c3_row = ToggleRow("刷 C1 / C3（无音区）", "消耗体力；把能用的体力全部用完后，再统一升级。")
        card.body.addWidget(self.c1c3_row)
        tacet_form = QFormLayout()
        tacet_form.setHorizontalSpacing(18)
        self.tacet_spin = spin(1, 50)
        self.stamina_seg = Segmented(STAMINA_MODES)
        tacet_form.addRow(label("无音区序号"), self.tacet_spin)
        tacet_form.addRow(label("体力"), self.stamina_seg)
        card.body.addLayout(tacet_form)
        card.body.addWidget(label("序号是 F2 书页无音区列表从上往下数，第一个是 1。", "hint"))

        self.c4_row = ToggleRow("刷 C4（打 Boss）", "不耗体力；背包里攒够目标数量的 0 级目标套装 C4 后，再去升级。")
        card.body.addSpacing(8)
        card.body.addWidget(self.c4_row)
        c4_form = QFormLayout()
        c4_form.setHorizontalSpacing(18)
        c4_form.setVerticalSpacing(10)
        self.teleport_combo = QComboBox()
        for key, text in C4_TELEPORT_LABELS.items():
            self.teleport_combo.addItem(text, key)
        self.teleport_combo.setFixedWidth(160)
        self.c4_index_spin = spin(1, 50)
        self.level_combo = QComboBox()
        self.level_combo.addItems(C4_BOSS_LEVELS)
        self.level_combo.setFixedWidth(110)
        self.c4_target_spin = spin(1, 200)
        self.c4_batch_spin = spin(1, 100)
        self.c4_max_spin = spin(1, 5000)
        c4_form.addRow(label("传送入口"), self.teleport_combo)
        c4_form.addRow(label("Boss 序号"), self.c4_index_spin)
        c4_form.addRow(label("Boss 等级"), self.level_combo)
        c4_form.addRow(label("目标数量"), self.c4_target_spin)
        c4_form.addRow(label("每批轮数"), self.c4_batch_spin)
        c4_form.addRow(label("最多轮数"), self.c4_max_spin)
        card.body.addLayout(c4_form)
        card.body.addWidget(label("每刷完一批就去背包数一次；刷到最多轮数还没攒够会停下提示，防止 Boss 选错一直刷。",
                                  "hint", wrap=True))
        return card

    def _fodder_card(self) -> Card:
        card = Card("喂料", "开始升级前，脚本会自动把游戏的“自动放入设置”切成：阶段放入 + 开启同步调谐 + 下面选的材料，"
                          "材料品质设为不限。毕业声骸会被自动上锁，游戏不会拿上锁的声骸当材料。")
        self.fodder_group = QButtonGroup(self)
        self.fodder_buttons = {}
        for key, text in FODDER_PRIORITIES.items():
            choice = button(text, "chip")
            choice.setCheckable(True)
            choice.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            choice.setMinimumHeight(40)
            self.fodder_group.addButton(choice)
            self.fodder_buttons[key] = choice
            card.body.addWidget(choice)
        self.fodder_buttons["echo"].setChecked(True)
        return card

    def _main_stat_card(self) -> Card:
        card = Card("主词条", "每个 COST 可以多选；没选任何主词条的 COST 一律直接废弃。")
        self.main_chips: dict[int, dict[str, object]] = {}
        for cost in COSTS:
            card.body.addWidget(label(f"COST {cost}", "sectionTitle"))
            flow = FlowLayout(5)
            self.main_chips[cost] = {}
            for stat in MAIN_STATS_BY_COST[cost]:
                widget = chip(stat)
                flow.add(widget)
                self.main_chips[cost][stat] = widget
            card.body.addLayout(flow)
        return card

    def _substat_card(self) -> Card:
        card = Card("副词条", "点标签切换：灰色 无效 → 红色 必要 → 蓝色 选要。必要词条缺一个就算废；选要不强制，出了更好。")
        flow = FlowLayout(4)
        self.sub_tags: dict[str, StatTag] = {}
        for stat in SUBSTATS:
            tag = StatTag(stat)
            flow.add(tag)
            self.sub_tags[stat] = tag
        card.body.addLayout(flow)
        return card

    # ---------- 数据 ----------

    def fill(self, profile: Profile | None):
        self.original_name = profile.name if profile else None
        self.delete_button.setVisible(profile is not None)
        farm = profile.farm if profile else FarmConfig()
        self.name_edit.setText(profile.name if profile else "")
        self.set_edit.setText(profile.sonata_set if profile else "")
        self.c1c3_row.toggle.setChecked(farm.farm_c1c3)
        self.tacet_spin.setValue(farm.tacet_index)
        self.stamina_seg.set_value(farm.stamina_mode)
        self.c4_row.toggle.setChecked(farm.farm_c4)
        self.teleport_combo.setCurrentIndex(self.teleport_combo.findData(farm.c4_teleport))
        self.c4_index_spin.setValue(farm.c4_index)
        self.level_combo.setCurrentText(farm.c4_boss_level)
        self.c4_target_spin.setValue(farm.c4_target)
        self.c4_batch_spin.setValue(farm.c4_batch)
        self.c4_max_spin.setValue(farm.c4_max_rounds)
        fodder = profile.fodder_priority if profile else "echo"
        self.fodder_buttons[fodder].setChecked(True)
        for cost, chips in self.main_chips.items():
            chosen = set(profile.main_stats.get(cost, [])) if profile else set()
            for stat, widget in chips.items():
                widget.setChecked(stat in chosen)
        for stat, tag in self.sub_tags.items():
            if profile and stat in profile.required:
                tag.set_state("required")
            elif profile and stat in profile.optional:
                tag.set_state("optional")
            else:
                tag.set_state("invalid")
        self.verticalScrollBar().setValue(0)

    def collect(self) -> Profile:
        return Profile(
            name=self.name_edit.text().strip(),
            sonata_set=self.set_edit.text().strip(),
            main_stats={cost: [s for s, w in chips.items() if w.isChecked()] for cost, chips in self.main_chips.items()},
            required=[s for s, t in self.sub_tags.items() if t.state == "required"],
            optional=[s for s, t in self.sub_tags.items() if t.state == "optional"],
            fodder_priority=next(key for key, choice in self.fodder_buttons.items() if choice.isChecked()),
            farm=FarmConfig(
                farm_c1c3=self.c1c3_row.toggle.isChecked(),
                tacet_index=self.tacet_spin.value(),
                stamina_mode=self.stamina_seg.value(),
                farm_c4=self.c4_row.toggle.isChecked(),
                c4_teleport=self.teleport_combo.currentData(),
                c4_index=self.c4_index_spin.value(),
                c4_boss_level=self.level_combo.currentText(),
                c4_target=self.c4_target_spin.value(),
                c4_batch=self.c4_batch_spin.value(),
                c4_max_rounds=self.c4_max_spin.value(),
            ),
        )

    def save(self) -> bool:
        try:
            profile = self.collect()
            save_profile(profile)
        except ValueError as e:
            QMessageBox.warning(self, "保存失败", str(e))
            return False
        if self.original_name and self.original_name != profile.name:
            delete_profile(self.original_name)
        self.original_name = profile.name
        self.delete_button.setVisible(True)
        self.saved.emit(profile.name)
        return True

    def _delete(self):
        if not self.original_name:
            return
        if QMessageBox.question(self, "删除方案", f"确定删除“{self.original_name}”的方案吗？") != QMessageBox.Yes:
            return
        name = self.original_name
        delete_profile(name)
        self.fill(None)
        self.deleted.emit(name)
