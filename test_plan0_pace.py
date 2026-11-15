"""Tests for plan0_pace.py. Run with: python -m unittest test_plan0_pace -v"""

import contextlib
import io
import json
import math
import os
import re
import tempfile
import unittest

import plan0_pace as pp


class TestConstants(unittest.TestCase):
    def test_kiloparsec_is_thousand_parsecs(self):
        self.assertAlmostEqual(pp.KPC_M / pp.PARSEC_M, 1000.0)

    def test_parsec_in_light_years(self):
        self.assertAlmostEqual(pp.PARSEC_M / pp.LIGHT_YEAR_M, 3.2616, places=3)

    def test_year_seconds(self):
        self.assertAlmostEqual(pp.YEAR_S, 3.15576e7)


class TestModel(unittest.TestCase):
    def test_default_headline_in_sane_range(self):
        r = pp.derive(pp.Scenario())
        self.assertGreater(r["total_years"], 2e9)
        self.assertLess(r["total_years"], 6e9)

    def test_regime_table_cross_checks(self):
        # Physical Layer section 1: 0.27 kiloparsecs at 0.05 c takes about
        # 1.8e4 years; a 500-byte message takes about an hour at 1 bit/s.
        v = 0.05 * pp.C_M_PER_S
        transit_years = 0.27 * pp.KPC_M / v / pp.YEAR_S
        self.assertAlmostEqual(transit_years / 1.8e4, 1.0, delta=0.03)
        self.assertAlmostEqual(500 * 8 / 1.0 / 3600, 1.11, delta=0.01)

    def test_phases_sum_to_total(self):
        r = pp.derive(pp.Scenario())
        ph = r["phases"]
        self.assertAlmostEqual(
            sum(ph.values()) / r["total_years"], 1.0, places=6)

    def test_faster_probes_finish_sooner(self):
        slow = pp.derive(pp.Scenario(speed_c=0.05))["total_years"]
        fast = pp.derive(pp.Scenario(speed_c=0.1))["total_years"]
        self.assertLess(fast, slow)

    def test_shallower_depth_is_faster(self):
        full = pp.derive(pp.Scenario(depth=1.0))["total_years"]
        tenth = pp.derive(pp.Scenario(depth=0.1))["total_years"]
        self.assertLess(tenth, full)
        # Sampling thins the visited set, so the gain is less than tenfold.
        self.assertGreater(tenth, full / 10.0)

    def test_no_archives_hits_duplication_cap(self):
        sc = pp.Scenario(archives="none")
        r = pp.derive(sc)
        self.assertTrue(r["staleness_infinite"])
        self.assertAlmostEqual(r["duplication_fraction"], sc.dup_cap)
        self.assertEqual(r["comms"]["messages_per_probe"], 0.0)

    def test_archives_never_worse_than_none(self):
        worst = pp.derive(pp.Scenario(archives="none"))
        for name in pp.ARCHIVE_PRESETS:
            r = pp.derive(pp.Scenario(archives=name))
            self.assertLessEqual(r["duplication_fraction"],
                                 worst["duplication_fraction"], name)

    def test_all_presets_run(self):
        for name in pp.ARCHIVE_PRESETS:
            r = pp.derive(pp.Scenario(archives=name))
            self.assertGreater(r["total_years"], 0, name)

    def test_region_never_exceeds_one_probes_share(self):
        # Audit A7: with a billion probes each share is 200 systems, but
        # the region cycle stayed at 1000 systems, five times the whole
        # survey of that probe.
        sc = pp.Scenario(probes=1_000_000_000)
        r = pp.derive(sc)
        self.assertTrue(r["region_shrunk"])
        self.assertAlmostEqual(r["region_systems"], r["visited_per_probe"])
        self.assertAlmostEqual(r["regions_per_probe"], 1.0)
        self.assertAlmostEqual(r["region_cycle_years"],
                               r["phases"]["survey_work_years"])
        # The ceiling is still reached, and the result says so: the
        # formula grows with fleet size and passes the ceiling long
        # before a share drops below one region.
        self.assertTrue(r["duplication_capped"])
        self.assertTrue(
            pp.derive(pp.Scenario(probes=50_000_000))["duplication_capped"])
        self.assertFalse(
            pp.derive(pp.Scenario(probes=50_000_000))["region_shrunk"])
        self.assertFalse(
            pp.derive(pp.Scenario(archives="none"))["duplication_capped"])
        # An ordinary fleet is untouched.
        r = pp.derive(pp.Scenario())
        self.assertFalse(r["region_shrunk"])
        self.assertFalse(r["duplication_capped"])
        self.assertEqual(r["region_systems"], pp.Scenario().region_systems)
        self.assertAlmostEqual(
            r["regions_per_probe"] * r["region_systems"],
            r["visited_per_probe"])

    def test_milestones_monotonic(self):
        r = pp.derive(pp.Scenario())
        years = [m["years"] for m in r["milestones"]]
        self.assertEqual(years, sorted(years))
        self.assertAlmostEqual(years[-1], r["total_years"], places=6)

    def test_attrition_stretches_or_truncates(self):
        base = pp.derive(pp.Scenario())["total_years"]
        mild = pp.derive(pp.Scenario(attrition_per_year=1e-11))
        self.assertGreater(mild["total_years"], base)
        self.assertEqual(mild["attrition"]["completed_fraction"], 1.0)
        harsh = pp.derive(pp.Scenario(attrition_per_year=1e-3))
        self.assertLess(harsh["attrition"]["completed_fraction"], 1.0)
        self.assertTrue(math.isinf(harsh["total_years"]))

    def test_scenario_round_trip_through_dict(self):
        sc = pp.Scenario(speed_c=0.1, archives="sparse")
        clone = pp.Scenario.from_dict(
            json.loads(json.dumps(pp.asdict(sc))))
        self.assertEqual(pp.derive(sc)["total_years"],
                         pp.derive(clone)["total_years"])

    def test_unknown_scenario_key_rejected(self):
        with self.assertRaises(ValueError):
            pp.Scenario.from_dict({"warp_factor": 9})

    def test_invalid_values_rejected(self):
        for bad in [dict(depth=0), dict(depth=1.5), dict(speed_c=1.0),
                    dict(probes=0), dict(archives="orbital-mind-lasers")]:
            with self.assertRaises(ValueError):
                pp.derive(pp.Scenario(**bad))


class TestInputValidation(unittest.TestCase):
    """Every input the model reads is checked before use (audit A2-A4)."""

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pp.main(argv)
        return code, out.getvalue(), err.getvalue()

    def assert_rejected(self, argv, mention):
        code, out, err = self.run_main(argv)
        self.assertEqual(code, 2, argv)
        self.assertIn("error:", err)
        self.assertIn(mention, err)
        self.assertEqual(out, "", "no report may be printed for %r" % argv)

    def test_deposit_every_below_one_rejected(self):
        self.assert_rejected(["--deposit-every", "0"], "deposit_every")
        self.assert_rejected(["--deposit-every", "-2"], "deposit_every")
        with self.assertRaises(ValueError):
            pp.derive(pp.Scenario(deposit_every=0))

    def test_station_count_below_one_rejected(self):
        # Zero used to end in an uncaught ZeroDivisionError, a negative
        # count in a bare "math domain error".
        self.assert_rejected(["--station-count", "0"], "station_count")
        self.assert_rejected(["--station-count", "-3"], "station_count")

    def test_negative_tuning_and_distance_inputs_rejected(self):
        for bad in [dict(dup_gain=-5), dict(dup_cap=-0.1),
                    dict(neighbors=-1), dict(dispersal_leg_kpc=-1),
                    dict(cache_spacing_kpc=0), dict(cache_spacing_kpc=-2),
                    dict(detour_kpc=-0.5), dict(dwell_years=-1),
                    dict(attrition_per_year=-1e-9)]:
            with self.assertRaises(ValueError, msg=bad):
                pp.derive(pp.Scenario(**bad))
        self.assert_rejected(["--dup-gain", "-5"], "dup_gain")

    def test_zero_is_accepted_where_it_has_a_meaning(self):
        for fine in [dict(dup_gain=0), dict(dup_cap=0), dict(neighbors=0),
                     dict(detour_kpc=0), dict(dwell_years=0)]:
            r = pp.derive(pp.Scenario(**fine))
            self.assertGreater(r["total_years"], 0, fine)
        self.assertEqual(
            pp.derive(pp.Scenario(dup_gain=0))["duplication_fraction"], 0)

    def test_values_that_are_not_finite_numbers_rejected(self):
        for flag in ["--speed", "--dwell", "--systems", "--dup-gain"]:
            for word in ["nan", "inf", "-inf"]:
                # "=" keeps a leading minus sign from reading as a flag.
                code, _, err = self.run_main(["%s=%s" % (flag, word)])
                self.assertEqual(code, 2, (flag, word))
                self.assertIn("error:", err)
        for bad in [dict(probes="many"), dict(probes=True),
                    dict(probes=10.5), dict(speed_c=None),
                    dict(archives=["full-network"])]:
            with self.assertRaises(ValueError, msg=bad):
                pp.derive(pp.Scenario(**bad))

    def test_whole_number_written_as_float_accepted(self):
        self.assertEqual(pp.Scenario(probes=10000.0).probes, 10000)
        self.assertEqual(pp.derive(pp.Scenario(probes=10000.0))["total_years"],
                         pp.derive(pp.Scenario())["total_years"])

    def test_scenario_file_must_hold_an_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "list.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([1, 2, 3], fh)
            self.assert_rejected(["--scenario", path], "one object")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"probes": "many"}, fh)
            self.assert_rejected(["--scenario", path], "probes")


class TestHelpText(unittest.TestCase):
    # The manual must stay free of bare acronyms and specification
    # shorthand (matching the readability rule of Amendment Record
    # section 8). Word-boundary tokens plus raw substrings.
    DENYLIST_WORDS = ["CNL", "FEC", "PPM", "GSF", "PTS", "CCSDS", "YAML",
                      "kpc", "pc", "ly", "Myr", "Gyr", "L1", "L2", "L3",
                      "AU", "SI"]
    DENYLIST_SUBSTRINGS = ["T_c", "h_max", "PROC-", "CAT-", "CCH-", "e.g."]

    def setUp(self):
        self.help_text = pp.build_parser().format_help()

    def test_no_acronyms_or_jargon(self):
        for word in self.DENYLIST_WORDS:
            self.assertIsNone(
                re.search(r"\b%s\b" % re.escape(word), self.help_text),
                "help text contains banned token %r" % word)
        for sub in self.DENYLIST_SUBSTRINGS:
            self.assertNotIn(sub, self.help_text,
                             "help text contains banned token %r" % sub)

    def test_every_option_documented(self):
        for action in pp.build_parser()._actions:
            for opt in action.option_strings:
                self.assertIn(opt, self.help_text, opt)

    def test_every_preset_described(self):
        for name in pp.ARCHIVE_PRESETS:
            self.assertIn(name, self.help_text)


class TestCommandLine(unittest.TestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pp.main(argv)
        return code, out.getvalue()

    def test_default_run(self):
        code, out = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn("HEADLINE", out)

    def test_explain_run(self):
        code, out = self.run_main(["--explain"])
        self.assertEqual(code, 0)
        self.assertIn("FORMULAS", out)

    def test_canonical_run(self):
        code, out = self.run_main(["--canonical"])
        self.assertEqual(code, 0)
        self.assertIn("seconds", out)
        self.assertNotIn("light-years", out)

    def test_list_presets(self):
        code, out = self.run_main(["--list-presets"])
        self.assertEqual(code, 0)
        for name in pp.ARCHIVE_PRESETS:
            self.assertIn(name, out)

    def test_scenario_and_json_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenario_path = os.path.join(tmp, "scenario.json")
            out_path = os.path.join(tmp, "out.json")
            with open(scenario_path, "w", encoding="utf-8") as fh:
                json.dump({"speed_c": 0.2, "archives": "sparse"}, fh)
            code, _ = self.run_main(
                ["--scenario", scenario_path, "--json", out_path])
            self.assertEqual(code, 0)
            with open(out_path, encoding="utf-8") as fh:
                result = json.load(fh)
            self.assertEqual(result["scenario"]["speed_c"], 0.2)
            self.assertEqual(result["layout"]["name"], "sparse")
            expected = pp.derive(
                pp.Scenario(speed_c=0.2, archives="sparse"))
            self.assertEqual(result["total_years"], expected["total_years"])

    def test_json_file_is_strict_when_fleet_is_exhausted(self):
        # Audit A9: an exhausted fleet used to write the bare word
        # Infinity, which strict parsers reject.
        def reject(constant):
            raise AssertionError("non-standard constant %s" % constant)

        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "out.json")
            code, _ = self.run_main(
                ["--attrition", "1e-8", "--json", out_path])
            self.assertEqual(code, 0)
            with open(out_path, encoding="utf-8") as fh:
                text = fh.read()
            result = json.loads(text, parse_constant=reject)
        self.assertNotIn("Infinity", text)
        self.assertNotIn("NaN", text)
        self.assertTrue(result["fleet_exhausted"])
        self.assertIsNone(result["total_years"])
        self.assertIsNone(result["attrition"]["survey_seconds"])
        self.assertLess(result["attrition"]["completed_fraction"], 1.0)
        self.assertIsNone(result["milestones"][-1]["years"])

    def test_json_safe_leaves_finite_results_untouched(self):
        result = pp.derive(pp.Scenario())
        self.assertFalse(result["fleet_exhausted"])
        self.assertEqual(pp.json_safe(result), result)

    def test_bad_scenario_file_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{not valid json")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = pp.main(["--scenario", path])
            self.assertEqual(code, 2)
            self.assertIn("error:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
