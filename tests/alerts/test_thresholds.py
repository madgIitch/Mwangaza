from __future__ import annotations

import unittest

from mwangaza.alerts.thresholds import (
    ALERT_LEVELS,
    ThresholdBand,
    ThresholdError,
    ThresholdPreset,
    classify_value,
    default_threshold_preset,
    validate_preset,
)


class ThresholdTests(unittest.TestCase):
    def test_allowed_levels_and_default_classification(self) -> None:
        self.assertEqual(ALERT_LEVELS, ("green", "yellow", "orange", "red", "unknown"))
        self.assertEqual(classify_value(10).level, "green")
        self.assertEqual(classify_value(25).level, "yellow")
        self.assertEqual(classify_value(50).level, "orange")
        self.assertEqual(classify_value(75).level, "red")
        self.assertEqual(classify_value(100).level, "red")

    def test_validate_preset_rejects_gaps_overlaps_and_bad_levels(self) -> None:
        with self.assertRaisesRegex(ThresholdError, "gaps"):
            validate_preset(
                ThresholdPreset(
                    "bad",
                    0,
                    100,
                    (ThresholdBand("green", 0, 40), ThresholdBand("red", 50, 100)),
                )
            )
        with self.assertRaisesRegex(ThresholdError, "unsupported"):
            validate_preset(ThresholdPreset("bad", 0, 100, (ThresholdBand("blue", 0, 100),)))

    def test_quality_blocked_and_missing_force_unknown(self) -> None:
        blocked = classify_value(90, quality_blocked=True)
        missing = classify_value(None)

        self.assertEqual(blocked.level, "unknown")
        self.assertEqual(blocked.reason, "quality_blocked")
        self.assertEqual(missing.level, "unknown")
        self.assertEqual(missing.reason, "value_missing")

    def test_classification_keeps_threshold_version_and_is_immutable(self) -> None:
        first = classify_value(20)
        custom = ThresholdPreset("custom-v2", 0, 100, (ThresholdBand("red", 0, 100),))
        second = classify_value(20, preset=custom)

        self.assertEqual(first.threshold_version, "prototype-thresholds-v1")
        self.assertEqual(second.threshold_version, "custom-v2")
        self.assertEqual(first.level, "green")
        self.assertEqual(second.level, "red")

    def test_default_preset_is_prototype_not_official(self) -> None:
        preset = default_threshold_preset()

        self.assertFalse(preset.is_official)
        self.assertIn("prototype", preset.label)


if __name__ == "__main__":
    unittest.main()
