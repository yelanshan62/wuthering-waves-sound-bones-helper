"""角色方案编辑器：选角色 -> 刷取设置 -> 主词条 -> 副词条，保存到 profiles/。"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from echo_helper.profile import (C4_BOSS_LEVELS, C4_TELEPORTS, FODDER_PRIORITIES, STAMINA_MODES, FarmConfig,
                                 Profile, list_profiles, load_profile, save_profile)
from echo_helper.stats import COSTS, MAIN_STATS_BY_COST, SUBSTATS

NEW_PROFILE = "<新建角色>"


class ProfileEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("鸣潮声骸助手 - 角色方案")
        self.geometry("620x620")
        self.resizable(False, False)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self._build_basic_page()
        self._build_main_stat_page()
        self._build_substat_page()

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(buttons, text="上一步", command=lambda: self._step(-1)).pack(side="left")
        ttk.Button(buttons, text="下一步", command=lambda: self._step(1)).pack(side="left", padx=6)
        ttk.Button(buttons, text="保存方案", command=self._save).pack(side="right")

        self._refresh_profile_list()

    def _step(self, delta):
        index = self.notebook.index(self.notebook.select()) + delta
        if 0 <= index < self.notebook.index("end"):
            self.notebook.select(index)

    def _build_basic_page(self):
        page = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(page, text="1. 角色与刷取")

        row = 0
        ttk.Label(page, text="选择角色方案").grid(row=row, column=0, sticky="w")
        self.profile_choice = ttk.Combobox(page, state="readonly", width=28)
        self.profile_choice.grid(row=row, column=1, sticky="w")
        self.profile_choice.bind("<<ComboboxSelected>>", lambda _: self._load_selected())

        row += 1
        ttk.Label(page, text="角色名").grid(row=row, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(page, textvariable=self.name_var, width=30).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(page, text="套装名（与游戏内合鸣名一致）").grid(row=row, column=0, sticky="w", pady=4)
        self.set_var = tk.StringVar()
        ttk.Entry(page, textvariable=self.set_var, width=30).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Separator(page).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

        row += 1
        self.farm_c1c3_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(page, text="刷 C1/C3（无音区，消耗体力）", variable=self.farm_c1c3_var).grid(
            row=row, column=0, columnspan=2, sticky="w")

        row += 1
        ttk.Label(page, text="无音区序号（F2 列表从上到下，从 1 开始）").grid(row=row, column=0, sticky="w", pady=4)
        self.tacet_var = tk.IntVar(value=1)
        ttk.Spinbox(page, from_=1, to=50, textvariable=self.tacet_var, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(page, text="体力消耗").grid(row=row, column=0, sticky="nw", pady=4)
        self.stamina_var = tk.StringVar(value="daily")
        stamina_frame = ttk.Frame(page)
        stamina_frame.grid(row=row, column=1, sticky="w")
        for key, label in STAMINA_MODES.items():
            ttk.Radiobutton(stamina_frame, text=label, value=key, variable=self.stamina_var).pack(anchor="w")

        row += 1
        ttk.Separator(page).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

        row += 1
        self.farm_c4_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(page, text="刷 C4（打 Boss，不耗体力）", variable=self.farm_c4_var).grid(
            row=row, column=0, columnspan=2, sticky="w")

        row += 1
        ttk.Label(page, text="Boss 传送入口").grid(row=row, column=0, sticky="w", pady=4)
        self.c4_teleport_var = tk.StringVar(value="Boss Challenge")
        ttk.Combobox(page, state="readonly", values=C4_TELEPORTS, textvariable=self.c4_teleport_var,
                     width=20).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(page, text="Boss 序号（从上到下，从 1 开始）").grid(row=row, column=0, sticky="w", pady=4)
        self.c4_index_var = tk.IntVar(value=1)
        ttk.Spinbox(page, from_=1, to=50, textvariable=self.c4_index_var, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(page, text="Boss 等级").grid(row=row, column=0, sticky="w", pady=4)
        self.c4_level_var = tk.StringVar(value="80")
        ttk.Combobox(page, state="readonly", values=C4_BOSS_LEVELS, textvariable=self.c4_level_var,
                     width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(page, text="C4 刷取次数").grid(row=row, column=0, sticky="w", pady=4)
        self.c4_count_var = tk.IntVar(value=20)
        ttk.Spinbox(page, from_=1, to=999, textvariable=self.c4_count_var, width=8).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Separator(page).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

        row += 1
        ttk.Label(page, text="升级时优先消耗").grid(row=row, column=0, sticky="nw", pady=4)
        self.fodder_var = tk.StringVar(value="material")
        fodder_frame = ttk.Frame(page)
        fodder_frame.grid(row=row, column=1, sticky="w")
        for key, label in FODDER_PRIORITIES.items():
            ttk.Radiobutton(fodder_frame, text=label, value=key, variable=self.fodder_var).pack(anchor="w")

    def _build_main_stat_page(self):
        page = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(page, text="2. 主词条")
        ttk.Label(page, text="每个 COST 可以勾选多个主词条；不勾的 COST 一律不升级。").pack(anchor="w")
        self.main_vars: dict[int, dict[str, tk.BooleanVar]] = {}
        columns = ttk.Frame(page)
        columns.pack(fill="both", expand=True, pady=8)
        for cost in COSTS:
            box = ttk.LabelFrame(columns, text=f"COST{cost}", padding=8)
            box.pack(side="left", fill="both", expand=True, padx=4)
            self.main_vars[cost] = {}
            for stat in MAIN_STATS_BY_COST[cost]:
                var = tk.BooleanVar()
                ttk.Checkbutton(box, text=stat, variable=var).pack(anchor="w")
                self.main_vars[cost][stat] = var

    def _build_substat_page(self):
        page = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(page, text="3. 副词条")
        ttk.Label(page, text="必要：没有就算废；选要：不是必须，有更好。同一词条只能选一种。").pack(anchor="w")
        grid = ttk.Frame(page)
        grid.pack(fill="both", expand=True, pady=8)
        ttk.Label(grid, text="副词条").grid(row=0, column=0, sticky="w")
        ttk.Label(grid, text="必要").grid(row=0, column=1)
        ttk.Label(grid, text="选要").grid(row=0, column=2)
        ttk.Label(grid, text="无效").grid(row=0, column=3)
        self.sub_vars: dict[str, tk.StringVar] = {}
        for row, stat in enumerate(SUBSTATS, start=1):
            var = tk.StringVar(value="invalid")
            ttk.Label(grid, text=stat).grid(row=row, column=0, sticky="w", pady=2)
            for col, value in enumerate(("required", "optional", "invalid"), start=1):
                ttk.Radiobutton(grid, value=value, variable=var).grid(row=row, column=col, padx=16)
            self.sub_vars[stat] = var

    def _refresh_profile_list(self, select: str | None = None):
        names = list_profiles()
        self.profile_choice["values"] = [NEW_PROFILE, *names]
        self.profile_choice.set(select if select in names else NEW_PROFILE)

    def _load_selected(self):
        name = self.profile_choice.get()
        if name == NEW_PROFILE:
            self._fill(None)
            return
        try:
            self._fill(load_profile(name))
        except (ValueError, FileNotFoundError) as e:
            messagebox.showerror("读取失败", str(e))

    def _fill(self, profile: Profile | None):
        farm = profile.farm if profile else FarmConfig()
        self.name_var.set(profile.name if profile else "")
        self.set_var.set(profile.sonata_set if profile else "")
        self.farm_c1c3_var.set(farm.farm_c1c3)
        self.tacet_var.set(farm.tacet_index)
        self.stamina_var.set(farm.stamina_mode)
        self.farm_c4_var.set(farm.farm_c4)
        self.c4_teleport_var.set(farm.c4_teleport)
        self.c4_index_var.set(farm.c4_index)
        self.c4_level_var.set(farm.c4_boss_level)
        self.c4_count_var.set(farm.c4_count)
        self.fodder_var.set(profile.fodder_priority if profile else "material")
        for cost, stats in self.main_vars.items():
            chosen = set(profile.main_stats.get(cost, [])) if profile else set()
            for stat, var in stats.items():
                var.set(stat in chosen)
        for stat, var in self.sub_vars.items():
            if profile and stat in profile.required:
                var.set("required")
            elif profile and stat in profile.optional:
                var.set("optional")
            else:
                var.set("invalid")

    def _collect(self) -> Profile:
        return Profile(
            name=self.name_var.get().strip(),
            sonata_set=self.set_var.get().strip(),
            main_stats={cost: [s for s, v in stats.items() if v.get()] for cost, stats in self.main_vars.items()},
            required=[s for s, v in self.sub_vars.items() if v.get() == "required"],
            optional=[s for s, v in self.sub_vars.items() if v.get() == "optional"],
            fodder_priority=self.fodder_var.get(),
            farm=FarmConfig(
                farm_c1c3=self.farm_c1c3_var.get(),
                tacet_index=int(self.tacet_var.get()),
                stamina_mode=self.stamina_var.get(),
                farm_c4=self.farm_c4_var.get(),
                c4_teleport=self.c4_teleport_var.get(),
                c4_index=int(self.c4_index_var.get()),
                c4_boss_level=self.c4_level_var.get(),
                c4_count=int(self.c4_count_var.get()),
            ),
        )

    def _save(self):
        try:
            profile = self._collect()
            path = save_profile(profile)
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("保存失败", str(e))
            return
        self._refresh_profile_list(profile.name)
        messagebox.showinfo("已保存", f"已保存到 {path}")


if __name__ == "__main__":
    ProfileEditor().mainloop()
