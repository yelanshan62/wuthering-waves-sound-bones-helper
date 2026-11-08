"""角色方案：一个角色一个 JSON 文件，保存刷取、主词条、副词条和喂料设置。"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from echo_helper.judge import SubstatRule
from echo_helper.stats import COSTS, MAIN_STATS_BY_COST

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"

STAMINA_MODES = {
    "daily": "只用当日体力",
    "all": "当日体力 + 储存的结晶一起用完",
}

FODDER_PRIORITIES = {
    "echo": "强化材料和声骸（没上锁的声骸都能吃）",
    "material": "仅强化材料（只用密音筒）",
}

C4_TELEPORTS = ("Weekly Challenge", "Boss Challenge", "Special Nightmare")
C4_TELEPORT_LABELS = {
    "Weekly Challenge": "周常挑战",
    "Boss Challenge": "首领挑战",
    "Special Nightmare": "梦魇首领",
}
C4_BOSS_LEVELS = ("50", "60", "70", "80", "90")

# 毕业声骸数达到 GRADUATE_ASK_AT 时暂停询问，继续则做到 GRADUATE_STOP_AT 结束。
GRADUATE_ASK_AT = 2
GRADUATE_STOP_AT = 4


@dataclass
class FarmConfig:
    farm_c1c3: bool = True
    tacet_index: int = 1
    stamina_mode: str = "daily"
    farm_c4: bool = False
    c4_teleport: str = "Boss Challenge"
    c4_index: int = 1
    c4_boss_level: str = "80"
    c4_target: int = 30
    c4_batch: int = 10
    c4_max_rounds: int = 300

    def validate(self):
        if self.tacet_index < 1:
            raise ValueError("无音区序号从 1 开始")
        if self.stamina_mode not in STAMINA_MODES:
            raise ValueError(f"体力模式只能是 {list(STAMINA_MODES)}")
        if self.c4_teleport not in C4_TELEPORTS:
            raise ValueError(f"C4 传送方式只能是 {C4_TELEPORTS}")
        if self.c4_index < 1:
            raise ValueError("C4 Boss 序号从 1 开始")
        if self.c4_boss_level not in C4_BOSS_LEVELS:
            raise ValueError(f"Boss 等级只能是 {C4_BOSS_LEVELS}")
        if self.c4_target < 1:
            raise ValueError("C4 目标数量至少 1 个")
        if self.c4_batch < 1:
            raise ValueError("每批刷取轮数至少 1 轮")
        if self.c4_max_rounds < self.c4_batch:
            raise ValueError("C4 最多刷取轮数不能少于每批轮数")


@dataclass
class Profile:
    name: str
    sonata_set: str
    main_stats: dict[int, list[str]]
    required: list[str]
    optional: list[str] = field(default_factory=list)
    fodder_priority: str = "echo"
    farm: FarmConfig = field(default_factory=FarmConfig)

    def validate(self):
        if not self.name.strip():
            raise ValueError("角色名不能为空")
        if not self.sonata_set.strip():
            raise ValueError("套装名不能为空")
        for cost, stats in self.main_stats.items():
            if cost not in MAIN_STATS_BY_COST:
                raise ValueError(f"未知 COST: {cost}")
            bad = set(stats) - set(MAIN_STATS_BY_COST[cost])
            if bad:
                raise ValueError(f"COST{cost} 没有这些主词条: {sorted(bad)}")
        if not any(self.main_stats.get(c) for c in COSTS):
            raise ValueError("至少要给一个 COST 选主词条")
        if self.fodder_priority not in FODDER_PRIORITIES:
            raise ValueError(f"喂料方式只能是 {list(FODDER_PRIORITIES)}")
        self.substat_rule()
        self.farm.validate()

    def substat_rule(self) -> SubstatRule:
        return SubstatRule(frozenset(self.required), frozenset(self.optional))

    def allowed_main_stats(self) -> dict[int, frozenset[str]]:
        return {cost: frozenset(stats) for cost, stats in self.main_stats.items()}

    def to_json(self) -> str:
        data = asdict(self)
        data["main_stats"] = {str(k): v for k, v in self.main_stats.items()}
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Profile":
        data = json.loads(text)
        try:
            farm = FarmConfig(**data["farm"])
        except (KeyError, TypeError) as e:
            raise ValueError(f"刷取设置格式不对，请在软件里重新保存这个方案: {e}") from e
        profile = cls(
            name=data["name"],
            sonata_set=data["sonata_set"],
            main_stats={int(k): list(v) for k, v in data["main_stats"].items()},
            required=list(data["required"]),
            optional=list(data.get("optional", [])),
            fodder_priority=data["fodder_priority"],
            farm=farm,
        )
        profile.validate()
        return profile


def profile_path(name: str, folder: Path = PROFILES_DIR) -> Path:
    return folder / f"{name}.json"


def save_profile(profile: Profile, folder: Path = PROFILES_DIR) -> Path:
    profile.validate()
    folder.mkdir(parents=True, exist_ok=True)
    path = profile_path(profile.name, folder)
    path.write_text(profile.to_json(), encoding="utf-8")
    return path


def load_profile(name: str, folder: Path = PROFILES_DIR) -> Profile:
    path = profile_path(name, folder)
    if not path.is_file():
        raise FileNotFoundError(f"找不到角色方案: {path}")
    return Profile.from_json(path.read_text(encoding="utf-8"))


def delete_profile(name: str, folder: Path = PROFILES_DIR):
    profile_path(name, folder).unlink()


def list_profiles(folder: Path = PROFILES_DIR) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.json"))
