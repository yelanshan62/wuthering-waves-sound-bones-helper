"""把游戏里 OCR 读到的词条名和数值，换算成 stats.py 里的标准词条。"""

import re

from echo_helper.judge import Substat
from echo_helper.stats import MAIN_STATS_BY_COST, SUBSTAT_TIERS

_NUMBER = re.compile(r"(\d+(?:\.\d+)?)")

_ELEMENTS = ("冷凝", "热熔", "导电", "气动", "衍射", "湮灭")


def parse_value(text: str) -> tuple[float, bool]:
    """返回 (数值, 是否百分比)。"""
    normalized = text.replace("％", "%").replace(" ", "")
    match = _NUMBER.search(normalized)
    if not match:
        raise ValueError(f"读不到数值: {text!r}")
    return float(match.group(1)), "%" in normalized


def normalize_stat_name(name: str, is_percent: bool) -> str:
    text = name.replace(" ", "")
    if "暴击伤害" in text:
        return "暴击伤害"
    if "暴击" in text:
        return "暴击"
    if "治疗" in text:
        return "治疗效果加成"
    if "效率" in text:
        return "共鸣效率"
    if "普攻" in text:
        return "普攻伤害加成"
    if "重击" in text:
        return "重击伤害加成"
    if "解放" in text:
        return "共鸣解放伤害加成"
    if "技能" in text:
        return "共鸣技能伤害加成"
    for element in _ELEMENTS:
        if element in text:
            return f"{element}伤害加成"
    for base in ("攻击", "生命", "防御"):
        if base in text:
            return f"{base}百分比" if is_percent else base
    raise ValueError(f"无法识别的词条名: {name!r}")


_NAME_TEXT = re.compile(r"[\u4e00-\u9fff]{2,}")
_VALUE_TEXT = re.compile(r"\d+(?:\.\d+)?\s*[%％]?")
_IGNORED_ROWS = ("强化至", "辅音", "调谐", "声骸技能", "合鸣")


def pair_rows(texts: list[tuple[str, float]], max_dy: float) -> list[tuple[str, str]]:
    """把 OCR 文本按行配成 (词条名, 数值)，从上到下排序。

    texts 是 (文本, 纵坐标) 列表；同一行的名字和数值可能被识别成一个框，也可能是两个框。
    """
    rows: list[tuple[float, str, str]] = []
    names: list[tuple[str, float]] = []
    values: list[tuple[str, float]] = []
    for text, y in texts:
        if any(word in text for word in _IGNORED_ROWS):
            continue
        name = _NAME_TEXT.search(text)
        value = _VALUE_TEXT.search(text)
        if name and value and value.start() > name.start():
            rows.append((y, name.group(), value.group()))
        elif name:
            names.append((name.group(), y))
        elif value:
            values.append((value.group(), y))
    unused = list(values)
    for name, y in names:
        if not unused:
            raise ValueError(f"词条 {name} 找不到对应数值")
        best = min(unused, key=lambda v: abs(v[1] - y))
        if abs(best[1] - y) > max_dy:
            raise ValueError(f"词条 {name} 和最近的数值 {best[0]} 不在同一行")
        unused.remove(best)
        rows.append((y, name, best[0]))
    return [(name, value) for _, name, value in sorted(rows)]


def parse_substat(name: str, value_text: str) -> Substat:
    value, is_percent = parse_value(value_text)
    stat = normalize_stat_name(name, is_percent)
    if stat not in SUBSTAT_TIERS:
        raise ValueError(f"{stat} 不是副词条")
    return Substat(stat, value)


def parse_main_stat(cost: int, name: str, value_text: str) -> str:
    _, is_percent = parse_value(value_text)
    stat = normalize_stat_name(name, is_percent)
    if stat not in MAIN_STATS_BY_COST[cost]:
        raise ValueError(f"COST{cost} 不可能出现主词条 {stat}")
    return stat
