"""鸣潮五星声骸的主词条与副词条数据。

副词条档位数据来源：wuwa.uk 副词条 Roll 值表与 GameKee 声骸属性页，两者一致。
"""

SUBSTAT_TIERS: dict[str, tuple[float, ...]] = {
    "暴击": (6.3, 6.9, 7.5, 8.1, 8.7, 9.3, 9.9, 10.5),
    "暴击伤害": (12.6, 13.8, 15.0, 16.2, 17.4, 18.6, 19.8, 21.0),
    "攻击百分比": (6.4, 7.1, 7.9, 8.6, 9.4, 10.1, 10.9, 11.6),
    "生命百分比": (6.4, 7.1, 7.9, 8.6, 9.4, 10.1, 10.9, 11.6),
    "防御百分比": (8.1, 9.0, 10.0, 10.9, 11.8, 12.8, 13.8, 14.7),
    "共鸣效率": (6.8, 7.6, 8.4, 9.2, 10.0, 10.8, 11.6, 12.4),
    "普攻伤害加成": (6.4, 7.1, 7.9, 8.6, 9.4, 10.1, 10.9, 11.6),
    "重击伤害加成": (6.4, 7.1, 7.9, 8.6, 9.4, 10.1, 10.9, 11.6),
    "共鸣技能伤害加成": (6.4, 7.1, 7.9, 8.6, 9.4, 10.1, 10.9, 11.6),
    "共鸣解放伤害加成": (6.4, 7.1, 7.9, 8.6, 9.4, 10.1, 10.9, 11.6),
    "攻击": (30, 40, 50, 60),
    "防御": (40, 50, 60, 70),
    "生命": (320, 360, 390, 430, 470, 510, 540, 580),
}

SUBSTATS: tuple[str, ...] = tuple(SUBSTAT_TIERS)

MAIN_STATS_BY_COST: dict[int, tuple[str, ...]] = {
    4: ("暴击", "暴击伤害", "治疗效果加成", "攻击百分比", "生命百分比", "防御百分比"),
    3: ("攻击百分比", "生命百分比", "防御百分比", "共鸣效率",
        "冷凝伤害加成", "热熔伤害加成", "导电伤害加成", "气动伤害加成", "衍射伤害加成", "湮灭伤害加成"),
    1: ("攻击百分比", "生命百分比", "防御百分比"),
}

COSTS: tuple[int, ...] = (4, 3, 1)

MAX_SUBSTATS = 5

_TIER_TOLERANCE = 0.051


def tier_of(stat: str, value: float) -> int:
    """返回副词条数值所在档位，1 为最低档。数值不在档位表里时抛出 ValueError。"""
    if stat not in SUBSTAT_TIERS:
        raise ValueError(f"未知副词条: {stat}")
    for index, tier_value in enumerate(SUBSTAT_TIERS[stat], start=1):
        if abs(tier_value - value) <= _TIER_TOLERANCE:
            return index
    raise ValueError(f"副词条 {stat} 的数值 {value} 不在档位表中: {SUBSTAT_TIERS[stat]}")


def is_lowest_tier(stat: str, value: float) -> bool:
    return tier_of(stat, value) == 1
