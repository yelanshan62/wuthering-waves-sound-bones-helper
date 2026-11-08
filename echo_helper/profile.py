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
    "material": "优先用密音筒",
    "echo": "优先用已废弃的声骸",
}

C4_TELEPORTS = ("Weekly Challenge", "Boss Challenge", "Special Nightmare")
C4_BOSS_LEVELS = ("50", "60", "70", "80", "90")


@dataclass
class FarmConfig:
    farm_c1c3: bool = True
    tacet_index: int = 1
    stamina_mode: str = "daily"
    farm_c4: bool = False
    c4_teleport: str = "Boss Challenge"
    c4_index: int = 1
    c4_boss_level: str = "80"
    c4_count: int = 20

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
        if self.c4_count < 1:
            raise ValueError("C4 刷取次数至少 1 次")


@dataclass
class Profile:
    name: str
    sonata_set: str
    main_stats: dict[int, list[str]]
    required: list[str]
    optional: list[str] = field(default_factory=list)
    fodder_priority: str = "material"
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
            raise ValueError(f"喂料优先级只能是 {list(FODDER_PRIORITIES)}")
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
        profile = cls(
            name=data["name"],
            sonata_set=data["sonata_set"],
            main_stats={int(k): list(v) for k, v in data["main_stats"].items()},
            required=list(data["required"]),
            optional=list(data.get("optional", [])),
            fodder_priority=data.get("fodder_priority", "material"),
            farm=FarmConfig(**data.get("farm", {})),
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


def list_profiles(folder: Path = PROFILES_DIR) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.json"))
