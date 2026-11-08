import unittest

from echo_helper.judge import Decision, Substat, SubstatRule, Verdict, judge_main_stat, judge_substats

CRIT = "暴击"
CDMG = "暴击伤害"
ATK = "攻击百分比"
ER = "共鸣效率"
DEF = "防御"
HP = "生命"
FLAT_ATK = "攻击"

DOUBLE_CRIT = SubstatRule(frozenset({CRIT, CDMG}), frozenset({ATK, ER}))
SINGLE_CRIT = SubstatRule(frozenset({CRIT}), frozenset({CDMG, ATK, ER}))
THREE_REQUIRED = SubstatRule(frozenset({CRIT, CDMG, ATK}), frozenset({ER}))


def s(name, value=None):
    defaults = {CRIT: 8.1, CDMG: 16.2, ATK: 8.6, ER: 9.2, DEF: 50, HP: 430, FLAT_ATK: 40}
    return Substat(name, defaults[name] if value is None else value)


def verdict(substats, rule=DOUBLE_CRIT) -> Verdict:
    return judge_substats(substats, rule).verdict


class FirstTwo(unittest.TestCase):
    def test_first_invalid_still_continues(self):
        self.assertEqual(verdict([s(DEF)]), Verdict.CONTINUE)

    def test_two_invalid_still_continues_when_slots_enough(self):
        self.assertEqual(verdict([s(DEF), s(HP)]), Verdict.CONTINUE)

    def test_prune_when_required_cannot_fit(self):
        rule = SubstatRule(frozenset({CRIT, CDMG, ATK, ER}), frozenset())
        self.assertEqual(verdict([s(DEF), s(HP)], rule), Verdict.DISCARD)


class AfterThree(unittest.TestCase):
    def test_one_required_one_optional(self):
        self.assertEqual(verdict([s(CRIT), s(ATK), s(DEF)]), Verdict.CONTINUE)

    def test_two_required_no_optional(self):
        self.assertEqual(verdict([s(CRIT), s(CDMG), s(DEF)]), Verdict.CONTINUE)

    def test_three_required(self):
        self.assertEqual(verdict([s(CRIT), s(CDMG), s(ATK)], THREE_REQUIRED), Verdict.CONTINUE)

    def test_one_required_only(self):
        self.assertEqual(verdict([s(CRIT), s(DEF), s(HP)]), Verdict.DISCARD)

    def test_no_required(self):
        self.assertEqual(verdict([s(ATK), s(ER), s(DEF)]), Verdict.DISCARD)

    def test_three_required_rule_with_one_required_still_has_slots(self):
        self.assertEqual(verdict([s(CRIT), s(ER), s(DEF)], THREE_REQUIRED), Verdict.CONTINUE)


class FourthRequired(unittest.TestCase):
    def test_fourth_required_continues(self):
        self.assertEqual(verdict([s(CRIT), s(ATK), s(DEF), s(CDMG)]), Verdict.CONTINUE)


class FourthOptional(unittest.TestCase):
    def test_one_one_with_lowest_required_discards(self):
        result = judge_substats([s(CRIT, 6.3), s(ATK), s(DEF), s(ER)], DOUBLE_CRIT)
        self.assertEqual(result.verdict, Verdict.DISCARD)
        self.assertIn("最低 1 档", result.reason)

    def test_one_one_with_higher_required_continues(self):
        self.assertEqual(verdict([s(CRIT, 6.9), s(ATK), s(DEF), s(ER)]), Verdict.CONTINUE)

    def test_one_two_with_lowest_required_continues(self):
        self.assertEqual(verdict([s(CRIT, 6.3), s(CDMG), s(ATK), s(ER)], SINGLE_CRIT), Verdict.CONTINUE)

    def test_two_required_continues(self):
        self.assertEqual(verdict([s(CRIT, 6.3), s(CDMG, 12.6), s(DEF), s(ATK)]), Verdict.CONTINUE)


class FourthInvalid(unittest.TestCase):
    def test_three_effective_continues(self):
        self.assertEqual(verdict([s(CRIT), s(ATK), s(ER), s(DEF)]), Verdict.CONTINUE)

    def test_two_effective_discards(self):
        self.assertEqual(verdict([s(CRIT), s(ATK), s(DEF), s(HP)]), Verdict.DISCARD)

    def test_two_required_one_invalid_then_invalid_discards(self):
        self.assertEqual(verdict([s(CRIT), s(CDMG), s(DEF), s(HP)]), Verdict.DISCARD)


class FourthAfterFailedThird(unittest.TestCase):
    def test_failed_third_is_discarded_even_if_fourth_required(self):
        self.assertEqual(verdict([s(ATK), s(ER), s(DEF), s(CRIT)]), Verdict.DISCARD)


class FourthPruning(unittest.TestCase):
    def test_three_required_rule_missing_two_with_one_slot(self):
        self.assertEqual(verdict([s(CRIT), s(ER), s(DEF), s(HP)], THREE_REQUIRED), Verdict.DISCARD)


class Fifth(unittest.TestCase):
    def test_all_required_and_three_effective_locks(self):
        self.assertEqual(verdict([s(CRIT), s(ATK), s(DEF), s(CDMG), s(HP)]), Verdict.LOCK)

    def test_fifth_effective_but_missing_required_discards(self):
        self.assertEqual(verdict([s(CRIT), s(ATK), s(DEF), s(ER), s(FLAT_ATK)]), Verdict.DISCARD)

    def test_fifth_invalid_but_already_graduated_locks(self):
        self.assertEqual(verdict([s(CRIT), s(CDMG), s(ATK), s(DEF), s(HP)]), Verdict.LOCK)

    def test_all_required_but_only_two_effective_discards(self):
        rule = SubstatRule(frozenset({CRIT, CDMG}), frozenset())
        self.assertEqual(verdict([s(CRIT), s(CDMG), s(DEF), s(HP), s(FLAT_ATK)], rule), Verdict.DISCARD)

    def test_single_required_three_effective_locks(self):
        self.assertEqual(verdict([s(CRIT), s(CDMG), s(DEF), s(ATK), s(HP)], SINGLE_CRIT), Verdict.LOCK)


class InvalidInput(unittest.TestCase):
    def test_duplicate_substat(self):
        with self.assertRaises(ValueError):
            judge_substats([s(CRIT), s(CRIT)], DOUBLE_CRIT)

    def test_too_many(self):
        with self.assertRaises(ValueError):
            judge_substats([s(CRIT), s(CDMG), s(ATK), s(ER), s(DEF), s(HP)], DOUBLE_CRIT)

    def test_empty(self):
        with self.assertRaises(ValueError):
            judge_substats([], DOUBLE_CRIT)

    def test_unknown_name(self):
        with self.assertRaises(ValueError):
            judge_substats([Substat("治疗效果加成", 8.0)], DOUBLE_CRIT)

    def test_value_not_in_tier_table(self):
        with self.assertRaises(ValueError):
            judge_substats([s(CRIT, 7.0), s(ATK), s(DEF), s(ER)], DOUBLE_CRIT)

    def test_rule_needs_required(self):
        with self.assertRaises(ValueError):
            SubstatRule(frozenset(), frozenset({ATK}))

    def test_rule_overlap(self):
        with self.assertRaises(ValueError):
            SubstatRule(frozenset({CRIT}), frozenset({CRIT}))


class MainStat(unittest.TestCase):
    allowed = {4: frozenset({"暴击", "暴击伤害"}), 3: frozenset({"导电伤害加成"}), 1: frozenset({"攻击百分比"})}

    def test_allowed(self):
        self.assertEqual(judge_main_stat(4, "暴击", self.allowed).verdict, Verdict.CONTINUE)

    def test_not_selected(self):
        self.assertEqual(judge_main_stat(3, "攻击百分比", self.allowed).verdict, Verdict.DISCARD)

    def test_cost_not_selected_at_all(self):
        self.assertEqual(judge_main_stat(1, "生命百分比", {}).verdict, Verdict.DISCARD)

    def test_impossible_main_stat(self):
        with self.assertRaises(ValueError):
            judge_main_stat(1, "暴击", self.allowed)


if __name__ == "__main__":
    unittest.main()
