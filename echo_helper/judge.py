"""声骸升级判断引擎。

每调谐出一条副词条后调用 judge_substats，决定继续升级、上锁（毕业）还是打废弃标记。
规则：
  任何一步：还缺的必要词条数 > 剩余槽数 -> 废弃
  前 1~2 条：继续
  第 3 条后：必要 >= 1 且 有效 >= 2 -> 继续，否则废弃
  第 4 条：
    必要 -> 继续
    选要 -> 继续；前三条为 1 必要 1 选要 且该必要为最低 1 档 -> 废弃
    无效 -> 前三条三有效才继续，否则废弃
  第 5 条后：必要词条全部都有 且 有效 >= 3 -> 上锁，否则废弃
"""

from dataclasses import dataclass
from enum import Enum

from echo_helper.stats import MAIN_STATS_BY_COST, MAX_SUBSTATS, SUBSTAT_TIERS, is_lowest_tier


class Verdict(Enum):
    CONTINUE = "继续升级"
    LOCK = "毕业上锁"
    DISCARD = "废弃"


class Kind(Enum):
    REQUIRED = "必要"
    OPTIONAL = "选要"
    INVALID = "无效"


@dataclass(frozen=True)
class Substat:
    name: str
    value: float


@dataclass(frozen=True)
class SubstatRule:
    required: frozenset[str]
    optional: frozenset[str]

    def __post_init__(self):
        if not self.required:
            raise ValueError("必要词条至少要选 1 个")
        overlap = self.required & self.optional
        if overlap:
            raise ValueError(f"词条不能同时是必要和选要: {sorted(overlap)}")
        unknown = (self.required | self.optional) - set(SUBSTAT_TIERS)
        if unknown:
            raise ValueError(f"未知副词条: {sorted(unknown)}")

    def kind_of(self, stat: str) -> Kind:
        if stat in self.required:
            return Kind.REQUIRED
        if stat in self.optional:
            return Kind.OPTIONAL
        return Kind.INVALID


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str


def judge_main_stat(cost: int, main_stat: str, allowed: dict[int, frozenset[str]]) -> Decision:
    """0 级时的主词条过滤。"""
    if cost not in MAIN_STATS_BY_COST:
        raise ValueError(f"未知 COST: {cost}")
    if main_stat not in MAIN_STATS_BY_COST[cost]:
        raise ValueError(f"COST{cost} 不可能出现主词条 {main_stat}")
    wanted = allowed.get(cost, frozenset())
    if main_stat in wanted:
        return Decision(Verdict.CONTINUE, f"COST{cost} 主词条 {main_stat} 符合")
    return Decision(Verdict.DISCARD, f"COST{cost} 主词条 {main_stat} 不在所选范围 {sorted(wanted)}")


def _count(substats: list[Substat], rule: SubstatRule) -> tuple[int, int]:
    kinds = [rule.kind_of(s.name) for s in substats]
    return kinds.count(Kind.REQUIRED), kinds.count(Kind.OPTIONAL)


def judge_substats(substats: list[Substat], rule: SubstatRule) -> Decision:
    n = len(substats)
    if not 1 <= n <= MAX_SUBSTATS:
        raise ValueError(f"副词条数量必须在 1~{MAX_SUBSTATS} 之间，实际 {n}")
    names = [s.name for s in substats]
    if len(set(names)) != n:
        raise ValueError(f"副词条重复: {names}")
    for s in substats:
        if s.name not in SUBSTAT_TIERS:
            raise ValueError(f"未知副词条: {s.name}")

    missing = len(rule.required - set(names))
    remaining = MAX_SUBSTATS - n
    if missing > remaining:
        return Decision(Verdict.DISCARD, f"还缺 {missing} 个必要词条，只剩 {remaining} 个槽")

    if n <= 2:
        return Decision(Verdict.CONTINUE, f"前 {n} 条，继续到第 3 条再判断")

    first3_req, first3_opt = _count(substats[:3], rule)
    first3_ok = first3_req >= 1 and first3_req + first3_opt >= 2

    if n == 3:
        if first3_ok:
            return Decision(Verdict.CONTINUE, f"前三条 {first3_req} 必要 {first3_opt} 选要，继续")
        return Decision(Verdict.DISCARD, f"前三条 {first3_req} 必要 {first3_opt} 选要，不满足 必要>=1 且 有效>=2")

    if n == 4:
        if not first3_ok:
            return Decision(Verdict.DISCARD, f"前三条 {first3_req} 必要 {first3_opt} 选要，本应在第 3 条废弃")
        fourth = substats[3]
        kind = rule.kind_of(fourth.name)
        if kind is Kind.REQUIRED:
            return Decision(Verdict.CONTINUE, f"第 4 条 {fourth.name} 是必要词条，继续")
        if kind is Kind.OPTIONAL:
            if (first3_req, first3_opt) == (1, 1):
                required_stat = next(s for s in substats[:3] if rule.kind_of(s.name) is Kind.REQUIRED)
                if is_lowest_tier(required_stat.name, required_stat.value):
                    return Decision(Verdict.DISCARD,
                                    f"前三条 1 必要 1 选要，必要词条 {required_stat.name} {required_stat.value} 为最低 1 档")
            return Decision(Verdict.CONTINUE, f"第 4 条 {fourth.name} 是选要词条，继续")
        if first3_req + first3_opt == 3:
            return Decision(Verdict.CONTINUE, f"第 4 条无效，但前三条已三有效，继续")
        return Decision(Verdict.DISCARD, f"第 4 条 {fourth.name} 无效，且前三条不足三有效")

    total_req, total_opt = _count(substats, rule)
    if total_req == len(rule.required) and total_req + total_opt >= 3:
        return Decision(Verdict.LOCK, f"必要词条齐全，有效 {total_req + total_opt} 条，毕业")
    return Decision(Verdict.DISCARD, f"满级 {total_req} 必要 {total_opt} 选要，未毕业")
