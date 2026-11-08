import tempfile
import unittest
from pathlib import Path

from echo_helper.judge import Substat
from echo_helper.parse import pair_rows, parse_main_stat, parse_substat
from echo_helper.profile import FarmConfig, Profile, list_profiles, load_profile, save_profile
from echo_helper.stats import is_lowest_tier, tier_of


class Tiers(unittest.TestCase):
    def test_lowest(self):
        self.assertTrue(is_lowest_tier("暴击", 6.3))
        self.assertFalse(is_lowest_tier("暴击", 6.9))

    def test_flat_stats(self):
        self.assertEqual(tier_of("攻击", 60), 4)
        self.assertEqual(tier_of("生命", 320), 1)

    def test_unknown_value(self):
        with self.assertRaises(ValueError):
            tier_of("暴击伤害", 13.0)


class Parse(unittest.TestCase):
    def test_percent_vs_flat(self):
        self.assertEqual(parse_substat("攻击", "8.6%"), Substat("攻击百分比", 8.6))
        self.assertEqual(parse_substat("攻击", "40"), Substat("攻击", 40))

    def test_full_width_percent(self):
        self.assertEqual(parse_substat("暴击伤害", "13.8％"), Substat("暴击伤害", 13.8))

    def test_crit_not_confused(self):
        self.assertEqual(parse_substat("暴击", "6.3%").name, "暴击")

    def test_damage_bonus(self):
        self.assertEqual(parse_substat("共鸣解放伤害加成", "7.9%").name, "共鸣解放伤害加成")
        self.assertEqual(parse_substat("共鸣技能伤害加成", "7.9%").name, "共鸣技能伤害加成")

    def test_main_stat_element(self):
        self.assertEqual(parse_main_stat(3, "导电伤害加成", "30.0%"), "导电伤害加成")

    def test_main_stat_wrong_cost(self):
        with self.assertRaises(ValueError):
            parse_main_stat(1, "暴击", "22%")

    def test_unreadable(self):
        with self.assertRaises(ValueError):
            parse_substat("暴击", "--")


class PairRows(unittest.TestCase):
    def test_separate_boxes_sorted_top_down(self):
        texts = [("7.1%", 190), ("重击伤害加成", 191), ("暴击", 160), ("6.9%", 161)]
        self.assertEqual(pair_rows(texts, max_dy=10), [("暴击", "6.9%"), ("重击伤害加成", "7.1%")])

    def test_combined_box(self):
        self.assertEqual(pair_rows([("暴击伤害 13.8%", 100)], max_dy=10), [("暴击伤害", "13.8%")])

    def test_ignores_locked_slot_hints(self):
        texts = [("暴击", 160), ("6.9%", 161), ("强化至+10并激活辅音属性", 200)]
        self.assertEqual(pair_rows(texts, max_dy=10), [("暴击", "6.9%")])

    def test_missing_value_raises(self):
        with self.assertRaises(ValueError):
            pair_rows([("暴击", 160)], max_dy=10)

    def test_value_on_other_row_raises(self):
        with self.assertRaises(ValueError):
            pair_rows([("暴击", 160), ("6.9%", 220)], max_dy=10)


def sample_profile() -> Profile:
    return Profile(
        name="测试角色",
        sonata_set="浮星祛暗",
        main_stats={4: ["暴击", "暴击伤害"], 3: ["衍射伤害加成"], 1: ["攻击百分比"]},
        required=["暴击", "暴击伤害"],
        optional=["攻击百分比", "共鸣解放伤害加成"],
        fodder_priority="echo",
        farm=FarmConfig(tacet_index=7, stamina_mode="all", farm_c4=True, c4_index=3),
    )


class ProfileStore(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            original = sample_profile()
            save_profile(original, Path(folder))
            self.assertEqual(list_profiles(Path(folder)), ["测试角色"])
            self.assertEqual(load_profile("测试角色", Path(folder)), original)

    def test_rejects_bad_main_stat(self):
        profile = sample_profile()
        profile.main_stats[1] = ["暴击"]
        with self.assertRaises(ValueError):
            profile.validate()

    def test_rejects_no_required(self):
        profile = sample_profile()
        profile.required = []
        with self.assertRaises(ValueError):
            profile.validate()

    def test_rejects_bad_stamina_mode(self):
        profile = sample_profile()
        profile.farm.stamina_mode = "half"
        with self.assertRaises(ValueError):
            profile.validate()

    def test_missing_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                load_profile("不存在", Path(folder))


if __name__ == "__main__":
    unittest.main()
