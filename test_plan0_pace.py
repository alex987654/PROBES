"""Tests for plan0_pace.py. Run with: python -m unittest test_plan0_pace -v"""

import contextlib
import io
import json
import math
import os
import random
import re
import tempfile
import unittest

import plan0_pace as pp


# The manual and the report must stay free of bare acronyms and
# specification shorthand. Word-boundary tokens plus raw substrings.
DENYLIST_WORDS = ["CNL", "FEC", "PPM", "GSF", "PTS", "CCSDS", "YAML",
                  "kpc", "pc", "ly", "Myr", "Gyr", "L1", "L2", "L3",
                  "AU", "SI"]
DENYLIST_SUBSTRINGS = ["T_c", "h_max", "PROC-", "CAT-", "CCH-", "e.g."]


def by_region(**inputs):
    """A scenario as the specification stands, completion recorded by
    region. The identities of the travel model are pinned on it: a hop of
    one length, work in step with the systems visited."""
    return pp.Scenario(strategy="regions", **inputs)


def banned_tokens(text):
    """Every deny-listed token found in a piece of user-facing text."""
    found = [word for word in DENYLIST_WORDS
             if re.search(r"\b%s\b" % re.escape(word), text)]
    found += [sub for sub in DENYLIST_SUBSTRINGS if sub in text]
    return found


class TestConstants(unittest.TestCase):
    def test_kiloparsec_is_thousand_parsecs(self):
        self.assertAlmostEqual(pp.KPC_M / pp.PARSEC_M, 1000.0)

    def test_light_year_is_light_speed_times_one_year(self):
        self.assertAlmostEqual(
            pp.C_M_PER_S * pp.YEAR_S / pp.LIGHT_YEAR_M, 1.0, places=14)
        self.assertEqual(pp.YEAR_S, 365.25 * 86_400)
        self.assertEqual(pp.C_M_PER_S, 299_792_458.0)

    def test_parsec_follows_from_the_astronomical_unit(self):
        # One parsec is 648000 / pi astronomical units of 149,597,870,700
        # meters each (the definition, not a measurement).
        self.assertAlmostEqual(
            149_597_870_700.0 * 648_000.0 / math.pi / pp.PARSEC_M, 1.0,
            places=14)

    def test_report_prefixes_are_powers_of_a_thousand(self):
        self.assertEqual(pp.si_quantity(2.5e12, "second"), "2.5 teraseconds")
        self.assertEqual(pp.si_quantity(9.5e16, "second"), "95 petaseconds")
        self.assertEqual(pp.si_quantity(1.5e7, "meter"), "15 megameters")
        self.assertEqual(pp.human_count(2.0e7), "20 million")
        self.assertEqual(pp.human_count(1.42e12), "1.42 trillion")

    def test_parsec_in_light_years(self):
        self.assertAlmostEqual(pp.PARSEC_M / pp.LIGHT_YEAR_M, 3.2616, places=3)

    def test_year_seconds(self):
        self.assertAlmostEqual(pp.YEAR_S, 3.15576e7)


class TestModel(unittest.TestCase):
    def test_default_headline_in_sane_range(self):
        # A coarse tripwire only; the identities are pinned elsewhere.
        # The band moves whenever a default moves, on purpose. It is now
        # centered on 1.4 billion years: 1e11 systems in an exponential
        # disc with a bulge, completion recorded by system. That is every
        # system, where the 1.1 billion years of one pass by regions
        # reached 63 percent of them. Hops are 0.65 mean spacings at
        # first instead of 0.78 and 1.5 times that on average, because
        # the systems still to do thin out: 1.25 times the travel.
        r = pp.derive(pp.Scenario())
        self.assertEqual(r["strategy"], "systems-midplane")
        self.assertGreater(r["total_years"], 1.2e9)
        self.assertLess(r["total_years"], 1.6e9)
        # The specification as it stands: one pass by regions.
        by_region = pp.derive(pp.Scenario(strategy="regions"))
        self.assertGreater(by_region["total_years"], 0.9e9)
        self.assertLess(by_region["total_years"], 1.4e9)

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


def parse(argv):
    """Scenario exactly as the command line would build it."""
    return pp.scenario_from_args(pp.build_parser().parse_args(argv))


class TestIdentities(unittest.TestCase):
    """Audit A10: pin what the model computes, not what it printed."""

    def assertSame(self, first, second, msg=None):
        """Equal to twelve digits; the values span many magnitudes."""
        self.assertAlmostEqual(first / second, 1.0, places=12, msg=msg)

    # Inputs spelled out so that no later change of a default can move
    # this check; they are the values the audit was run against.
    AUDITED = dict(systems=2e11, stellar_density=0.1, path_factor=1.0,
                   dispersal_leg_kpc=10.0, envelope_factor=1.5,
                   consolidation_years=1e4, cache_spacing_kpc=0.27,
                   strategy="regions")

    def test_headline_from_first_principles(self):
        sc = pp.Scenario(**self.AUDITED)
        r = pp.derive(sc)
        year = 365.25 * 86_400.0
        light_year = 299_792_458.0 * year
        parsec = 149_597_870_700.0 * 648_000.0 / math.pi
        speed = 0.05 * 299_792_458.0
        hop_years = 0.1 ** (-1.0 / 3.0) * parsec / speed / year
        per_system = hop_years + 10.0
        per_probe = 2e11 / 10_000
        work = per_probe * per_system
        region_cycle = 1000.0 * per_system
        staleness = region_cycle + 1e4 + 270.0 * parsec / light_year
        duplication = staleness / region_cycle * 6 / (per_probe / 1000.0)
        dispersal = 10_000.0 * parsec / speed / year * 1.5
        detours = (per_probe / 1000.0) * 2 * 10.0 * parsec / speed / year
        total = dispersal + work * (1 + duplication) + detours
        self.assertAlmostEqual(r["hop_years"] / hop_years, 1.0, places=12)
        self.assertAlmostEqual(r["hop_parsec"], 2.1544, places=4)
        self.assertAlmostEqual(r["duplication_fraction"] / duplication, 1.0,
                               places=12)
        self.assertAlmostEqual(r["total_years"] / total, 1.0, places=12)
        # The figure the audit reproduced, to the three digits it quoted.
        self.assertAlmostEqual(r["total_years"] / 1e9, 3.04, places=2)
        self.assertAlmostEqual(r["phases"]["survey_work_years"] / 1e9, 3.01,
                               places=2)
        self.assertAlmostEqual(r["phases"]["archive_detours_years"] / 1e6,
                               26.1, places=1)

    def test_phases_add_up_to_the_total_in_every_layout(self):
        for name in pp.ARCHIVE_PRESETS:
            for kwargs in [dict(), dict(speed_c=0.2, depth=0.3),
                           dict(probes=37, systems=5e9)]:
                r = pp.derive(pp.Scenario(archives=name, **kwargs))
                self.assertAlmostEqual(
                    sum(r["phases"].values()) / r["total_years"], 1.0,
                    places=12, msg=(name, kwargs))
                ph = r["phases"]
                self.assertSame(
                    ph["duplicated_work_years"],
                    ph["survey_work_years"] * r["duplication_fraction"])
                self.assertSame(
                    ph["survey_work_years"],
                    r["visited_per_probe"] * r["per_system_years"])

    def test_distances_add_up(self):
        r = pp.derive(by_region(archives="stations-only"))
        d = r["distance"]
        self.assertSame(
            d["per_probe_m"],
            d["dispersal_m"] + d["survey_path_m"] + d["detour_m"])
        self.assertSame(d["fleet_m"], d["per_probe_m"] * 10_000)
        self.assertSame(
            d["survey_path_m"],
            r["visited_per_probe"] * r["hop_parsec"] * pp.PARSEC_M
            * (1 + r["duplication_fraction"]))
        # Detours: one round trip to the archive point per deposit.
        deposits = r["regions_per_probe"] / r["layout"]["deposit_every"]
        self.assertSame(
            d["detour_m"],
            deposits * 2 * r["layout"]["detour_kpc"] * pp.KPC_M)

    def test_milestones_are_linear_without_losses(self):
        r = pp.derive(by_region())
        dispersal = r["phases"]["dispersal_years"]
        survey = r["total_years"] - dispersal
        for m in r["milestones"]:
            self.assertSame(m["years"], dispersal + m["fraction"] * survey)

    def test_link_time_is_bits_over_bit_rate(self):
        # At the reference distance of the link budget the rate is the
        # one given.
        reference_kpc = pp.LINK_REFERENCE_M / pp.KPC_M
        sc = pp.Scenario(bitrate_bps=0.25, message_bytes=800.0,
                         cache_spacing_kpc=reference_kpc)
        c = pp.derive(sc)["comms"]
        self.assertSame(c["link_rate_bps"], 0.25)
        self.assertSame(c["link_seconds_per_message"], 800.0 * 8 / 0.25)
        self.assertSame(c["fleet_messages"],
                        c["messages_per_probe"] * sc.probes)

    def test_bit_rate_falls_with_the_square_of_the_link_distance(self):
        # Audit C9: the sparse layout kept the full rate over 5
        # kiloparsecs.
        reference_kpc = pp.LINK_REFERENCE_M / pp.KPC_M
        near = pp.derive(pp.Scenario(cache_spacing_kpc=reference_kpc))
        far = pp.derive(pp.Scenario(cache_spacing_kpc=3 * reference_kpc))
        self.assertSame(far["comms"]["link_rate_bps"] * 9,
                        near["comms"]["link_rate_bps"])
        self.assertSame(far["comms"]["link_seconds_per_message"],
                        9 * near["comms"]["link_seconds_per_message"])
        sparse = pp.derive(pp.Scenario(archives="sparse"))["comms"]
        self.assertSame(sparse["link_rate_bps"],
                        0.5 * (8.0e18 / (5.0 * pp.KPC_M)) ** 2)
        self.assertLess(sparse["link_rate_bps"], 0.002)
        self.assertIn("days at", pp.render_report(
            pp.derive(pp.Scenario(archives="sparse"))))
        none = pp.derive(pp.Scenario(archives="none"))
        self.assertIsNone(none["comms"]["link_distance_m"])
        self.assertIn("no messages are sent", pp.render_report(none))
        # Unattended boxes cannot beam: records are handed over at the
        # box, so the budget rate applies whatever the box spacing.
        boxes = pp.derive(pp.Scenario(archives="route-boxes-only",
                                      cache_spacing_kpc=40.0))
        self.assertIsNone(boxes["comms"]["link_distance_m"])
        self.assertEqual(boxes["comms"]["link_rate_bps"], 0.5)
        self.assertIn("handed over at the unattended boxes",
                      " ".join(pp.render_report(boxes).split()))

    @staticmethod
    def probe_years_worked(rate, start_years, end_years, steps=20_000):
        """Work one starting probe delivers between two dates when the
        fleet shrinks by `rate` per year: the integral of exp(-rate t),
        by Simpson's rule, independent of the closed form."""
        h = (end_years - start_years) / steps
        total = math.exp(-rate * start_years) + math.exp(-rate * end_years)
        for i in range(1, steps):
            total += (4 if i % 2 else 2) * math.exp(
                -rate * (start_years + i * h))
        return total * h / 3.0

    def test_attrition_closed_form_matches_numerical_integration(self):
        base = pp.derive(by_region())
        needed = base["total_years"] - base["phases"]["dispersal_years"]
        dispersal = base["phases"]["dispersal_years"]
        for rate in (1e-12, 1e-10, 3e-10, 6e-10):
            r = pp.derive(by_region(attrition_per_year=rate))
            self.assertEqual(r["attrition"]["completed_fraction"], 1.0, rate)
            worked = self.probe_years_worked(rate, dispersal,
                                             r["total_years"])
            self.assertAlmostEqual(worked / needed, 1.0, places=9, msg=rate)
            for m in r["milestones"]:
                worked = self.probe_years_worked(rate, dispersal, m["years"])
                self.assertAlmostEqual(worked / (m["fraction"] * needed),
                                       1.0, places=9, msg=(rate, m))

    def test_exhausted_fleet_fraction_matches_numerical_integration(self):
        base = pp.derive(pp.Scenario())
        needed = base["total_years"] - base["phases"]["dispersal_years"]
        dispersal = base["phases"]["dispersal_years"]
        for rate in (1e-9, 1e-8):
            r = pp.derive(pp.Scenario(attrition_per_year=rate))
            self.assertTrue(r["fleet_exhausted"])
            # Everything the fleet will ever do: integrate far past the
            # point where no probe is left.
            ever = self.probe_years_worked(rate, dispersal,
                                           dispersal + 60.0 / rate)
            self.assertAlmostEqual(
                r["attrition"]["completed_fraction"] / (ever / needed), 1.0,
                places=9, msg=rate)
            reached = [m for m in r["milestones"] if m["years"] is not None]
            for m in reached:
                self.assertLess(m["fraction"],
                                r["attrition"]["completed_fraction"])

    def test_loss_rate_threshold_is_one_over_the_survey_time(self):
        # Completion needs loss rate x survey time below about one.
        base = pp.derive(pp.Scenario())
        survey = base["total_years"] - base["phases"]["dispersal_years"]
        just_below = pp.derive(pp.Scenario(attrition_per_year=0.99 / survey))
        just_above = pp.derive(pp.Scenario(attrition_per_year=1.01 / survey))
        self.assertFalse(just_below["fleet_exhausted"])
        self.assertTrue(just_above["fleet_exhausted"])


class TestUncertainty(unittest.TestCase):
    """Audit D: a range per input, seeded draws, a two-figure headline."""

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = pp.main(argv)
        return code, out.getvalue(), err.getvalue()

    def headline_block(self, text):
        lines = text.splitlines()
        at = next(i for i, line in enumerate(lines) if "HEADLINE" in line)
        return " ".join(line.strip() for line in lines[at:lines.index("", at)])

    def test_figures_are_rounded_the_way_the_report_claims(self):
        self.assertEqual(pp.sig(978.4, 3), "978")
        self.assertEqual(pp.sig(978.4, 2), "980")
        self.assertEqual(pp.sig(999.6, 3), "1000")
        self.assertEqual(pp.sig(0.2931, 2), "0.29")
        self.assertEqual(pp.sig(45.16, 2), "45")
        self.assertEqual(pp.sig(20.0, 3), "20")       # three: zeros dropped
        self.assertEqual(pp.sig(6.0, 2), "6.0")       # two: both figures kept
        self.assertEqual(pp.sig(0.0), "0")
        self.assertEqual(pp.fmt_span(2.9e8, 6.0e9),
                         "0.29 to 6.0 billion years")
        self.assertEqual(pp.fmt_span(9e8, math.inf),
                         "900 million years to never")
        self.assertEqual(pp.fmt_span(2.9e8, 6.0e9, canonical=True),
                         "9.2 to 190 petaseconds")

    def test_headline_has_two_significant_figures(self):
        for kwargs in [dict(), dict(speed_c=0.2), dict(systems=3.33e9),
                       dict(dwell_years=777.0), dict(probes=123)]:
            r = pp.derive(pp.Scenario(**kwargs))
            block = self.headline_block(pp.render_report(r))
            match = re.search(r"about ([0-9.]+) (\w+ )?years \(([0-9.]+) ",
                              block)
            self.assertIsNotNone(match, block)
            for figure in (match.group(1), match.group(3)):
                digits = figure.replace(".", "").lstrip("0")
                self.assertEqual(len(digits.rstrip("0") or "0") <= 2, True,
                                 (figure, block))
            # The stated value is the computed one, to two figures.
            words = {None: 1.0, "thousand ": 1e3, "million ": 1e6,
                     "billion ": 1e9, "trillion ": 1e12}
            stated = float(match.group(1)) * words[match.group(2)]
            self.assertAlmostEqual(stated / r["total_years"], 1.0, delta=0.05)

    def test_interval_stands_beside_the_headline_when_ranges_are_given(self):
        code, out, _ = self.run_main(["--uncertainty"])
        self.assertEqual(code, 0)
        block = self.headline_block(out)
        self.assertIn("5 to 95 percent interval:", block)
        self.assertIn("median", block)
        self.assertIn("2,000 seeded draws", block)
        self.assertIn("Input ranges, and the full survey with each varied "
                      "alone", out)
        code, out, _ = self.run_main([])
        block = self.headline_block(out)
        self.assertIn("no input ranges were varied", block)
        self.assertIn("--uncertainty", block)
        self.assertNotIn("Input ranges, and", out)

    def test_same_seed_repeats_and_other_seeds_agree(self):
        sc = pp.Scenario()
        ranges = pp.builtin_ranges()
        first = pp.run_uncertainty(sc, ranges, draws=1500, seed=5)
        again = pp.run_uncertainty(sc, ranges, draws=1500, seed=5)
        other = pp.run_uncertainty(sc, ranges, draws=1500, seed=6)
        self.assertEqual(first, again)
        self.assertNotEqual(first["percentiles_years"],
                            other["percentiles_years"])
        # Seed-to-seed scatter at this many draws is about 2 percent at
        # the 5th percentile and the median and 4 percent at the 95th.
        for key in ("5", "50", "95"):
            self.assertAlmostEqual(
                other["percentiles_years"][key]
                / first["percentiles_years"][key], 1.0, delta=0.25, msg=key)
        # The order in which a file lists the ranges must not matter.
        shuffled = dict(reversed(list(ranges.items())))
        self.assertEqual(
            pp.run_uncertainty(sc, shuffled, draws=1500, seed=5), first)

    def test_interval_brackets_the_median_and_one_at_a_time_rows(self):
        sc = pp.Scenario()
        u = pp.run_uncertainty(sc, pp.builtin_ranges(), draws=1000)
        pct = u["percentiles_years"]
        self.assertLess(pct["5"], pct["50"])
        self.assertLess(pct["50"], pct["95"])
        self.assertAlmostEqual(u["spread_factor"], pct["95"] / pct["5"])
        self.assertEqual(u["unfinished_share"], 0.0)
        base = pp.derive(sc)["total_years"]
        for row in u["one_at_a_time"]:
            name = row["input"]
            for end in ("low", "high"):
                expected = pp.derive(pp.replace(sc, **{name: row[end]}))
                self.assertEqual(row["total_years_at_" + end],
                                 expected["total_years"], (name, end))
            # No input in the default set is idle (audit A5).
            self.assertNotEqual(row["total_years_at_low"],
                                row["total_years_at_high"], name)
            self.assertTrue(row["set_value_inside"], name)
            low, high = sorted([row["total_years_at_low"],
                                row["total_years_at_high"]])
            self.assertLessEqual(low, base * (1 + 1e-12), name)
            self.assertGreaterEqual(high, base * (1 - 1e-12), name)

    def test_percentile_of_a_known_list(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(pp._percentile(values, 0), 1.0)
        self.assertEqual(pp._percentile(values, 50), 3.0)
        self.assertEqual(pp._percentile(values, 100), 5.0)
        self.assertAlmostEqual(pp._percentile(values, 5), 1.2)
        self.assertAlmostEqual(pp._percentile(values, 95), 4.8)
        self.assertEqual(pp._percentile([1.0, 2.0, math.inf], 50), 2.0)
        self.assertEqual(pp._percentile([1.0, 2.0, math.inf], 95), math.inf)

    def test_audited_scenario_reproduces_the_audit_spread(self):
        # Audit D, on the inputs it was run against: 5th percentile 0.64,
        # median 2.3, 95th percentile 16.7 billion years, a factor of 26.
        sc = pp.Scenario(**TestIdentities.AUDITED)
        ranges = pp.normalize_ranges({
            "systems": {"low": 1e11, "high": 4e11, "scale": "log"},
            "stellar_density": [0.07, 0.14],
            "path_factor": [0.70, 1.0],
            "speed_c": [0.05, 0.2],
            "dwell_years": [1, 1000],
        })
        self.assertEqual(ranges["stellar_density"]["scale"], "linear")
        self.assertEqual(ranges["speed_c"]["scale"], "log")
        u = pp.run_uncertainty(sc, ranges, draws=20_000, seed=1)
        pct = u["percentiles_years"]
        self.assertAlmostEqual(pct["5"] / 0.65e9, 1.0, delta=0.05)
        self.assertAlmostEqual(pct["50"] / 2.33e9, 1.0, delta=0.05)
        self.assertAlmostEqual(pct["95"] / 16.8e9, 1.0, delta=0.05)
        self.assertAlmostEqual(u["spread_factor"], 26.0, delta=2.0)

    def test_scenario_file_ranges_switch_the_mode_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ranged.json")
            out_path = os.path.join(tmp, "out.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"speed_c": 0.1, "ranges": {
                    "systems": [5e10, 1.2e11],
                    "dwell_years": {"low": 1, "high": 100, "scale": "log"},
                }}, fh)
            code, out, _ = self.run_main(
                ["--scenario", path, "--draws", "300", "--seed", "9",
                 "--json", out_path])
            self.assertEqual(code, 0)
            self.assertIn("5 to 95 percent interval:",
                          self.headline_block(out))
            self.assertIn("300 seeded draws", self.headline_block(out))
            with open(out_path, encoding="utf-8") as fh:
                result = json.load(fh)
            u = result["uncertainty"]
            self.assertEqual(sorted(u["ranges"]), ["dwell_years", "systems"])
            self.assertEqual((u["draws"], u["seed"]), (300, 9))
            self.assertEqual(result["scenario"]["speed_c"], 0.1)
            # With the flag as well, the built-in ranges fill in the rest,
            # and null takes one out again.
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"ranges": {"speed_c": None,
                                      "dwell_years": [5, 20]}}, fh)
            sc, ranges = pp.load_inputs(pp.build_parser().parse_args(
                ["--scenario", path, "--uncertainty"]))
            self.assertNotIn("speed_c", ranges)
            self.assertEqual(ranges["dwell_years"]["high"], 20.0)
            self.assertEqual(ranges["systems"],
                             pp.builtin_ranges()["systems"])

    def test_bad_ranges_are_rejected_by_name(self):
        for bad in [{"warp": [1, 2]}, {"archives": [1, 2]},
                    {"systems": [2e11, 1e11]}, {"systems": [1e11, 1e11]},
                    {"systems": [1e11]}, {"systems": "wide"},
                    {"systems": {"low": 1e10}},
                    {"systems": {"low": 1e10, "high": 1e11, "shape": "x"}},
                    {"systems": {"low": 1e10, "high": 1e11,
                                 "scale": "cubic"}},
                    {"dwell_years": {"low": 0, "high": 10, "scale": "log"}},
                    {"systems": [1e10, float("inf")]}, ["systems"]]:
            with self.assertRaises(ValueError, msg=bad):
                pp.normalize_ranges(bad)
        # An end of a range that the model itself cannot use.
        with self.assertRaises(ValueError) as caught:
            pp.run_uncertainty(pp.Scenario(), pp.normalize_ranges(
                {"speed_c": {"low": 0.5, "high": 2.0, "scale": "linear"}}))
        self.assertIn("speed_c", str(caught.exception))
        with self.assertRaises(ValueError):
            pp.run_uncertainty(pp.Scenario(), {})
        with self.assertRaises(ValueError):
            pp.run_uncertainty(pp.Scenario(), pp.builtin_ranges(), draws=0)

    def test_draws_and_seed_alone_are_refused(self):
        for argv in (["--draws", "50"], ["--seed", "3"]):
            code, out, err = self.run_main(argv)
            self.assertEqual(code, 2, argv)
            self.assertIn("--uncertainty", err)
            self.assertEqual(out, "")
        code, _, err = self.run_main(["--uncertainty", "--draws", "0"])
        self.assertEqual(code, 2)
        self.assertIn("draws", err)

    def test_losses_inside_a_range_are_counted_and_written_strictly(self):
        sc = pp.Scenario()
        ranges = pp.normalize_ranges(
            {"attrition_per_year": {"low": 1e-11, "high": 1e-8,
                                    "scale": "log"}})
        u = pp.run_uncertainty(sc, ranges, draws=400)
        self.assertGreater(u["unfinished_share"], 0.2)
        self.assertLess(u["unfinished_share"], 0.8)
        self.assertTrue(math.isinf(u["percentiles_years"]["95"]))
        result = pp.derive(sc)
        result["uncertainty"] = u
        text = json.dumps(pp.json_safe(result), allow_nan=False)
        self.assertIsNone(json.loads(text)["uncertainty"]
                          ["percentiles_years"]["95"])
        report = pp.render_report(result)
        self.assertIn("to never", self.headline_block(report))
        self.assertIn("fleet is exhausted before the end in", report)

    def test_set_value_outside_its_range_is_pointed_out(self):
        sc = pp.Scenario(dwell_years=5000.0)
        result = pp.derive(sc)
        result["uncertainty"] = pp.run_uncertainty(
            sc, pp.builtin_ranges(), draws=100)
        self.assertIn("--dwell lies outside its range",
                      " ".join(pp.render_report(result).split()))


class TestDefaultsTable(unittest.TestCase):
    """Audit D: one table of defaults with source and plausible range."""

    def test_every_input_has_exactly_one_row_in_field_order(self):
        self.assertEqual([row[0] for row in pp.INPUT_TABLE],
                         [f.name for f in pp.fields(pp.Scenario)])
        for name, low, high, scale, varied, source in pp.INPUT_TABLE:
            self.assertTrue(source.strip(), name)
            if low is None:
                self.assertFalse(varied, name)
                continue
            self.assertLess(low, high, name)
            self.assertIn(scale, pp.RANGE_SCALES, name)

    def test_every_default_lies_inside_its_range(self):
        default = pp.Scenario()
        for name, low, high, _, _, _ in pp.INPUT_TABLE:
            value = getattr(default, name)
            if name == "systems":
                value = pp.DEFAULT_SYSTEMS
            if low is not None and value is not None:
                self.assertLessEqual(low, value, name)
                self.assertLessEqual(value, high, name)

    def test_built_in_ranges_are_the_rows_marked_varied(self):
        ranges = pp.builtin_ranges()
        self.assertEqual(sorted(ranges),
                         sorted(row[0] for row in pp.INPUT_TABLE if row[4]))
        self.assertEqual(pp.normalize_ranges(ranges), ranges)

    def test_explain_prints_the_table(self):
        text = pp.render_explain(pp.derive(pp.Scenario()))
        self.assertIn("DEFAULTS, THEIR SOURCES AND PLAUSIBLE RANGES", text)
        table = " ".join(text[text.index("DEFAULTS, THEIR SOURCES"):].split())
        for action in pp.build_parser()._actions:
            if action.dest in {f.name for f in pp.fields(pp.Scenario)}:
                self.assertIn(action.option_strings[0], table)
        self.assertIn("range 50 to 120 billion *", table)
        self.assertIn("Cerf and others 1997", table)


class TestOneSourceOfTruth(unittest.TestCase):
    """Audit A1: the system count is the workload input and the density
    follows from it, so no default can contradict another."""

    def test_passing_any_default_explicitly_changes_nothing(self):
        flags = {action.dest: action.option_strings[0]
                 for action in pp.build_parser()._actions
                 if action.option_strings}
        default = pp.Scenario()
        base = pp.derive(default)
        base_report = pp.render_report(base)
        checked = 0
        for field in pp.fields(pp.Scenario):
            value = getattr(default, field.name)
            if value is None:
                continue        # no default value exists to pass
            self.assertIn(field.name, flags,
                          "%s cannot be set from the command line"
                          % field.name)
            text = value if isinstance(value, str) else repr(value)
            result = pp.derive(parse([flags[field.name], text]))
            self.assertEqual(result, base, field.name)
            self.assertEqual(pp.render_report(result), base_report,
                             field.name)
            checked += 1
        self.assertGreaterEqual(checked, 20)

    def test_default_count_passed_explicitly_changes_nothing(self):
        base = pp.derive(pp.Scenario())
        explicit = pp.derive(parse(["--systems", repr(pp.DEFAULT_SYSTEMS)]))
        self.assertEqual(explicit["scenario"]["systems"], pp.DEFAULT_SYSTEMS)
        for key in base:
            if key != "scenario":
                self.assertEqual(explicit[key], base[key], key)
        self.assertEqual(pp.render_report(explicit), pp.render_report(base))

    def test_scenario_file_of_defaults_changes_nothing(self):
        data = {key: value for key, value in pp.asdict(pp.Scenario()).items()
                if value is not None}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "defaults.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            self.assertEqual(pp.derive(parse(["--scenario", path])),
                             pp.derive(pp.Scenario()))

    def test_command_line_and_scenario_object_agree(self):
        # The old defect: the command line derived a count from the
        # density while the Scenario class did not.
        cases = [
            (dict(stellar_density=0.1), ["--stellar-density", "0.1"]),
            (dict(systems=2e11), ["--systems", "2e11"]),
            (dict(systems=2e11, stellar_density=0.1),
             ["--systems", "2e11", "--stellar-density", "0.1"]),
            (dict(galaxy_model="uniform"), ["--galaxy-model", "uniform"]),
        ]
        for kwargs, argv in cases:
            self.assertEqual(pp.derive(parse(argv)),
                             pp.derive(pp.Scenario(**kwargs)), argv)

    def test_density_alone_means_uniform_disc_with_derived_count(self):
        sc = by_region(stellar_density=0.1, disc_radius_kpc=15.0,
                         disc_thickness_kpc=0.6)
        r = pp.derive(sc)
        volume_pc3 = math.pi * 15_000.0 ** 2 * 600.0
        self.assertEqual(r["galaxy"]["model"], "uniform")
        self.assertEqual(r["galaxy"]["source"], "density")
        self.assertAlmostEqual(r["systems"] / (0.1 * volume_pc3), 1.0)
        self.assertAlmostEqual(r["hop_parsec"],
                               sc.path_factor * 0.1 ** (-1.0 / 3.0))
        self.assertAlmostEqual(r["visited_per_probe"] * sc.probes,
                               r["systems"])

    def test_count_alone_in_uniform_disc_gives_the_density(self):
        r = pp.derive(pp.Scenario(galaxy_model="uniform"))
        gal = r["galaxy"]
        self.assertEqual(gal["source"], "count")
        self.assertAlmostEqual(
            gal["uniform_density"] * gal["slab_volume_pc3"]
            / pp.DEFAULT_SYSTEMS, 1.0)
        # Feeding the derived density back in lands on the same count
        # and the same answer: there is no second source of truth.
        again = pp.derive(pp.Scenario(stellar_density=gal["uniform_density"]))
        self.assertAlmostEqual(again["systems"] / r["systems"], 1.0)
        self.assertAlmostEqual(again["total_years"] / r["total_years"], 1.0)

    def test_count_and_density_both_given_are_kept_and_flagged(self):
        r = pp.derive(pp.Scenario(systems=2e11, stellar_density=0.1))
        self.assertEqual(r["galaxy"]["source"], "count and density")
        self.assertEqual(r["systems"], 2e11)
        self.assertAlmostEqual(r["galaxy"]["mean_spacing_pc"],
                               0.1 ** (-1.0 / 3.0))
        self.assertIn("do not describe the same disc", pp.render_report(r))

    def test_shape_inputs_are_reported_unused_in_a_uniform_disc(self):
        r = pp.derive(pp.Scenario(stellar_density=0.1, scale_length_kpc=3.0,
                                  bulge_fraction=0.3))
        self.assertEqual({item["input"] for item in r["unused_inputs"]},
                         {"scale_length_kpc", "bulge_fraction"})


class TestGalaxyModel(unittest.TestCase):
    """Audit C2: count and hop lengths follow from one density field.
    Every closed form is checked against a direct numerical sum."""

    @staticmethod
    def disc_integral(gal, power, steps=4000):
        """Integral of density^power over the disc, midpoint rule."""
        scale, height = gal["scale_length_pc"], gal["scale_height_pc"]
        dr = gal["disc_radius_pc"] / steps
        radial = sum(2.0 * math.pi * r * math.exp(-power * r / scale) * dr
                     for r in ((i + 0.5) * dr for i in range(steps)))
        dz = 40.0 * height / steps
        vertical = 2.0 * sum(math.exp(-power * z / height) * dz
                             for z in ((i + 0.5) * dz for i in range(steps)))
        return gal["disc_central_density"] ** power * radial * vertical

    @staticmethod
    def bulge_integral(gal, power, steps=4000):
        sigma = gal["bulge_sigma_pc"]
        dr = 15.0 * sigma / steps
        return gal["bulge_central_density"] ** power * sum(
            4.0 * math.pi * r * r
            * math.exp(-power * r * r / (2.0 * sigma * sigma)) * dr
            for r in ((i + 0.5) * dr for i in range(steps)))

    def test_density_field_adds_up_to_the_count(self):
        for kwargs in [dict(), dict(systems=3e10, scale_length_kpc=3.3,
                                    disc_thickness_kpc=1.1,
                                    bulge_fraction=0.3, bulge_radius_kpc=2.0),
                       dict(disc_radius_kpc=6.0)]:
            gal = pp.derive(pp.Scenario(**kwargs))["galaxy"]
            total = self.disc_integral(gal, 1.0) + self.bulge_integral(gal,
                                                                       1.0)
            # places=4 leaves room for the error of the sum itself.
            self.assertAlmostEqual(total / gal["systems"], 1.0, places=4,
                                   msg=kwargs)
            self.assertAlmostEqual(
                gal["disc_systems"] + gal["bulge_systems"], gal["systems"])

    def test_mean_spacing_is_the_route_integral(self):
        # Mean of density^(-1/3) over systems
        #   = integral of density^(2/3) over volume / number of systems.
        gal = pp.derive(by_region())["galaxy"]
        disc, bulge = gal["parts"]
        self.assertAlmostEqual(
            self.disc_integral(gal, 2.0 / 3.0) / gal["disc_systems"]
            / disc["mean_spacing_pc"], 1.0, places=4)
        self.assertAlmostEqual(
            self.bulge_integral(gal, 2.0 / 3.0) / gal["bulge_systems"]
            / bulge["mean_spacing_pc"], 1.0, places=4)
        self.assertAlmostEqual(
            gal["mean_spacing_pc"],
            disc["share"] * disc["mean_spacing_pc"]
            + bulge["share"] * bulge["mean_spacing_pc"])

    def test_spacing_distribution_matches_sampled_systems(self):
        # Draw systems from the density field itself and compare.
        sc = by_region()
        gal = pp.derive(sc)["galaxy"]
        rng = random.Random(11)
        xm = gal["disc_radius_pc"] / gal["scale_length_pc"]
        spacings = []
        for _ in range(60_000):
            if rng.random() < sc.bulge_fraction:
                r2 = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(3))
                density = gal["bulge_central_density"] * math.exp(-r2 / 2.0)
            else:
                while True:     # radius: t exp(-t), cut at the disc edge
                    x = -math.log(rng.random() * rng.random())
                    if x <= xm:
                        break
                w = -math.log(rng.random())
                density = gal["disc_central_density"] * math.exp(-x - w)
            spacings.append(density ** (-1.0 / 3.0))
        spacings.sort()
        self.assertAlmostEqual(
            sum(spacings) / len(spacings) / gal["mean_spacing_pc"], 1.0,
            delta=0.02)
        for share in (0.05, 0.25, 0.5, 0.75, 0.95):
            sampled = spacings[int(share * len(spacings))]
            self.assertAlmostEqual(
                pp.spacing_percentile(gal, share) / sampled, 1.0, delta=0.02,
                msg=share)

    def test_percentile_inverts_the_distribution(self):
        for kwargs in [dict(), dict(bulge_fraction=0.0),
                       dict(galaxy_model="uniform")]:
            gal = pp.derive(pp.Scenario(**kwargs))["galaxy"]
            self.assertEqual(pp.spacing_cdf(gal, 1e-9), 0.0)
            self.assertAlmostEqual(pp.spacing_cdf(gal, 1e9), 1.0)
            if gal["model"] == "uniform":
                continue
            values = [pp.spacing_percentile(gal, share)
                      for share in (0.05, 0.5, 0.95)]
            self.assertEqual(values, sorted(values))
            for share, value in zip((0.05, 0.5, 0.95), values):
                self.assertAlmostEqual(pp.spacing_cdf(gal, value), share,
                                       places=9)

    def test_disc_density_falls_with_the_scale_length(self):
        gal = pp.derive(pp.Scenario(bulge_fraction=0.0))["galaxy"]
        self.assertEqual(len(gal["parts"]), 1)
        inner = pp.midplane_density(gal, 2_000.0)
        outer = pp.midplane_density(gal, 14_000.0)
        self.assertAlmostEqual(inner / outer, math.exp(12.0 / 2.6))
        self.assertAlmostEqual(inner / outer, 101.0, delta=0.5)
        self.assertEqual(pp.midplane_density(gal, 15_001.0), 0.0)

    def test_default_path_factor_is_the_nearest_unvisited_rule(self):
        # Audit C1. Walk 1200 random points in a box that wraps around,
        # always stepping to the nearest point not yet visited, and
        # compare the mean step with the default (in mean spacings).
        rng = random.Random(4)
        count = 1200
        points = [(rng.random(), rng.random(), rng.random())
                  for _ in range(count)]
        left = list(range(1, count))
        here = points[0]
        total = 0.0
        while left:
            best, best_d2 = 0, 9.0
            for slot, index in enumerate(left):
                p = points[index]
                dx = abs(p[0] - here[0])
                dy = abs(p[1] - here[1])
                dz = abs(p[2] - here[2])
                d2 = (min(dx, 1 - dx) ** 2 + min(dy, 1 - dy) ** 2
                      + min(dz, 1 - dz) ** 2)
                if d2 < best_d2:
                    best, best_d2 = slot, d2
            total += math.sqrt(best_d2)
            here = points[left[best]]
            left[best] = left[-1]
            left.pop()
        mean_step = total / (count - 1) / count ** (-1.0 / 3.0)
        self.assertAlmostEqual(mean_step, pp.Scenario().path_factor,
                               delta=0.03)
        # It sits between the shortest possible route and one mean
        # spacing per hop, the ends of its plausible range.
        row = next(row for row in pp.INPUT_TABLE if row[0] == "path_factor")
        self.assertEqual((row[1], row[2]), (0.70, 1.0))
        self.assertLess(0.6979, pp.Scenario().path_factor)

    def test_hop_identities(self):
        sc = by_region(path_factor=0.9)
        r = pp.derive(sc)
        self.assertAlmostEqual(
            r["hop_parsec"], 0.9 * r["galaxy"]["mean_spacing_pc"])
        self.assertAlmostEqual(
            r["hop_years"],
            r["hop_parsec"] * pp.PARSEC_M / pp.LIGHT_YEAR_M / sc.speed_c)
        # Visiting one system in eight doubles every hop.
        thin = pp.derive(by_region(path_factor=0.9, depth=0.125))
        self.assertAlmostEqual(thin["hop_parsec"], 2.0 * r["hop_parsec"])
        for pct in ("5", "50", "95"):
            self.assertAlmostEqual(thin["hop_percentiles_parsec"][pct],
                                   2.0 * r["hop_percentiles_parsec"][pct])
        # A uniform disc has one spacing: density^(-1/3).
        flat = pp.derive(by_region(stellar_density=0.08, path_factor=1.0))
        self.assertAlmostEqual(flat["hop_parsec"], 0.08 ** (-1.0 / 3.0))
        self.assertAlmostEqual(flat["hop_parsec"], 2.32, delta=0.005)

    def test_unknown_galaxy_model_rejected(self):
        with self.assertRaises(ValueError):
            pp.derive(pp.Scenario(galaxy_model="spiral"))
        for bad in [dict(bulge_fraction=1.0), dict(bulge_fraction=-0.1),
                    dict(scale_length_kpc=0), dict(bulge_radius_kpc=0),
                    dict(systems=0), dict(stellar_density=-1)]:
            with self.assertRaises(ValueError, msg=bad):
                pp.derive(pp.Scenario(**bad))


class TestFleetGeometry(unittest.TestCase):
    """Audit A6: the regime figures are computed, not fixed text."""

    def test_default_fleet_matches_the_regime_table(self):
        # Physical Layer section 1: about 0.07 square kiloparsecs per
        # probe, 0.27 kiloparsecs spacing, 880 years of light time,
        # 1.8e4 years of probe transit, 1e5 years to cross the fleet.
        g = pp.derive(pp.Scenario())["geometry"]
        self.assertAlmostEqual(g["area_per_probe_kpc2"], 0.07, delta=0.001)
        self.assertAlmostEqual(g["spacing_kpc"], 0.27, delta=0.005)
        self.assertAlmostEqual(g["light_years_per_spacing"] / 880, 1.0,
                               delta=0.02)
        self.assertAlmostEqual(g["transit_years_per_spacing"] / 1.8e4, 1.0,
                               delta=0.04)
        self.assertAlmostEqual(g["crossing_light_years"] / 1e5, 1.0,
                               delta=0.03)

    def test_identities(self):
        sc = pp.Scenario(probes=2500, disc_radius_kpc=12.0, speed_c=0.08)
        g = pp.derive(sc)["geometry"]
        self.assertAlmostEqual(g["area_per_probe_kpc2"] * sc.probes,
                               math.pi * 12.0 ** 2)
        self.assertAlmostEqual(g["spacing_kpc"] ** 2,
                               g["area_per_probe_kpc2"])
        # Six-neighbor lattice: each probe owns a hexagon of the same area.
        self.assertAlmostEqual(
            math.sqrt(3.0) / 2.0 * g["lattice_spacing_kpc"] ** 2,
            g["area_per_probe_kpc2"])
        self.assertAlmostEqual(
            g["light_years_per_spacing"],
            g["spacing_kpc"] * pp.KPC_M / pp.LIGHT_YEAR_M, places=6)
        self.assertAlmostEqual(
            g["transit_years_per_spacing"] * sc.speed_c,
            g["light_years_per_spacing"])

    def test_follows_probes_radius_and_speed(self):
        base = pp.derive(pp.Scenario())["geometry"]
        more = pp.derive(pp.Scenario(probes=40_000))["geometry"]
        wide = pp.derive(pp.Scenario(disc_radius_kpc=30.0))["geometry"]
        fast = pp.derive(pp.Scenario(speed_c=0.1))["geometry"]
        self.assertAlmostEqual(more["spacing_kpc"], base["spacing_kpc"] / 2)
        self.assertAlmostEqual(wide["spacing_kpc"], base["spacing_kpc"] * 2)
        self.assertAlmostEqual(fast["transit_years_per_spacing"],
                               base["transit_years_per_spacing"] / 2)
        self.assertAlmostEqual(fast["light_years_per_spacing"],
                               base["light_years_per_spacing"])
        text = pp.render_report(pp.derive(pp.Scenario(probes=100,
                                                      speed_c=0.2)))
        self.assertIn("2.66 kiloparsecs", text)
        self.assertNotIn("0.27 kiloparsecs", text)

    def test_relay_reach_follows_cadence_and_speed(self):
        # Physical Layer 4.2: reach over spacing = cycles x cadence / transit.
        g = pp.derive(pp.Scenario())["geometry"]
        low, high = g["relay_reach_spacings"]
        self.assertAlmostEqual(
            low, 10_000.0 / g["transit_years_per_spacing"])
        self.assertAlmostEqual(high, 2 * low)
        self.assertEqual(g["useful_relay_hops"], [1, 2])
        self.assertEqual(g["spec_hop_limit"], 2)
        fast = pp.derive(pp.Scenario(speed_c=0.1))["geometry"]
        self.assertEqual(fast["useful_relay_hops"], [2, 3])
        slow_cycle = pp.derive(
            pp.Scenario(consolidation_years=40_000.0))["geometry"]
        self.assertEqual(slow_cycle["useful_relay_hops"], [3, 5])

    def test_station_layouts_follow_the_probe_spacing(self):
        for probes in (10_000, 100):
            for name in ("full-network", "stations-only"):
                r = pp.derive(pp.Scenario(archives=name, probes=probes))
                self.assertAlmostEqual(r["layout"]["cache_spacing_kpc"],
                                       r["geometry"]["spacing_kpc"])
        self.assertIsNone(
            pp.derive(pp.Scenario(archives="none"))["layout"]
            ["cache_spacing_kpc"])
        self.assertEqual(
            pp.derive(pp.Scenario(archives="sparse"))["layout"]
            ["cache_spacing_kpc"], 5.0)


class TestReportWording(unittest.TestCase):
    """The report and the formula listing follow the plain-word rule of
    the help text."""

    def texts(self):
        for name in pp.ARCHIVE_PRESETS:
            r = pp.derive(pp.Scenario(archives=name))
            yield "report %s" % name, pp.render_report(r)
            yield "canonical %s" % name, pp.render_report(r, canonical=True)
            yield "explain %s" % name, pp.render_explain(r)
        odd = pp.derive(pp.Scenario(archives="none", cache_spacing_kpc=3.0,
                                    probes=1_000_000_000,
                                    attrition_per_year=1e-8))
        yield "odd report", pp.render_report(odd)
        yield "odd explain", pp.render_explain(odd)
        short = pp.derive(pp.Scenario(systems=2e5))
        yield "short survey", pp.render_report(short)
        for name in pp.STRATEGIES:
            for kwargs in [dict(), dict(galaxy_model="uniform"),
                           dict(depth=0.4, acceleration_m_s2=0.002),
                           dict(probes=400_000)]:
                other = pp.derive(pp.Scenario(strategy=name, **kwargs))
                yield "strategy %s" % name, pp.render_report(other)
                yield "strategy %s canonical" % name, pp.render_report(
                    other, canonical=True)
                yield "strategy %s explain" % name, pp.render_explain(other)
        lossy = pp.derive(pp.Scenario(attrition_per_year=5e-10))
        yield "further passes out of reach", pp.render_report(lossy)
        for kwargs in [dict(), dict(stellar_density=0.1, systems=2e11),
                       dict(acceleration_m_s2=0.003),
                       dict(speed_c=0.2, exhaust_speed_c=0.05,
                            refuel_years_per_mass=1.0),
                       dict(galaxy_model="uniform", scale_length_kpc=3.0)]:
            sc = pp.Scenario(**kwargs)
            ranged = pp.derive(sc)
            ranges = pp.builtin_ranges()
            ranges["attrition_per_year"] = dict(low=1e-12, high=1e-8,
                                                scale="log")
            ranged["uncertainty"] = pp.run_uncertainty(sc, ranges, draws=200)
            yield "ranged report", pp.render_report(ranged)
            yield "ranged canonical", pp.render_report(ranged, canonical=True)
            yield "ranged explain", pp.render_explain(ranged)

    def test_no_acronyms_or_jargon(self):
        for label, text in self.texts():
            self.assertEqual(banned_tokens(text), [], label)


class TestStopAndGo(unittest.TestCase):
    """Audit C3: hops start and end at rest."""

    V = 0.05 * pp.C_M_PER_S
    HOP_M = 0.1 ** (-1.0 / 3.0) * pp.PARSEC_M      # the audited hop

    def test_leg_time_formula(self):
        d, v = self.HOP_M, self.V
        self.assertEqual(pp.leg_seconds(d, v, None), d / v)
        # The audit: +0.3 percent at 1, +3.4 at 0.1, +34 at 0.01.
        for a, extra in ((1.0, 0.0034), (0.1, 0.034), (0.01, 0.338)):
            self.assertAlmostEqual(pp.leg_seconds(d, v, a), d / v + v / a)
            self.assertAlmostEqual(pp.leg_seconds(d, v, a) / (d / v) - 1,
                                   extra, delta=extra * 0.01)
        # Cruise speed is out of reach below v^2 / d = 0.0034.
        limit = v * v / d
        self.assertAlmostEqual(limit, 0.00338, delta=0.00001)
        self.assertAlmostEqual(pp.leg_seconds(d, v, limit), 2 * d / v)
        self.assertAlmostEqual(pp.leg_seconds(d, v, limit * 0.999999)
                               / (2 * d / v), 1.0, places=5)
        slow = limit / 4.0
        self.assertAlmostEqual(pp.leg_seconds(d, v, slow),
                               2 * math.sqrt(d / slow))
        # Half the distance speeding up, half slowing down: peak speed
        # sqrt(a d) is then below cruise speed.
        self.assertLess(math.sqrt(slow * d), v)

    def test_uniform_disc_is_one_leg(self):
        kwargs = dict(stellar_density=0.1, path_factor=1.0)
        r = pp.derive(by_region(acceleration_m_s2=0.1, **kwargs))
        self.assertAlmostEqual(
            r["hop_years"],
            pp.leg_seconds(self.HOP_M, self.V, 0.1) / pp.YEAR_S)
        self.assertAlmostEqual(r["kinematics"]["extra_hop_fraction"], 0.0338,
                               delta=0.0002)
        self.assertEqual(r["kinematics"]["hops_reaching_cruise"], 1.0)
        crawl = pp.derive(by_region(acceleration_m_s2=0.001, **kwargs))
        self.assertEqual(crawl["kinematics"]["hops_reaching_cruise"], 0.0)
        self.assertAlmostEqual(
            crawl["hop_years"],
            2 * math.sqrt(self.HOP_M / 0.001) / pp.YEAR_S)

    def test_very_strong_engines_recover_instant_stops(self):
        instant = pp.derive(pp.Scenario())
        strong = pp.derive(pp.Scenario(acceleration_m_s2=1e9))
        self.assertAlmostEqual(strong["total_years"] / instant["total_years"],
                               1.0, places=9)
        self.assertEqual(instant["kinematics"]["extra_hop_fraction"], 0.0)
        self.assertEqual(instant["kinematics"]["ramp_years"], 0.0)

    def test_numerical_average_matches_the_closed_form(self):
        # Where every hop reaches cruise speed the time is linear in the
        # hop length, so the average must equal the closed form. This
        # checks the weights of the numerical average (they sum to one).
        sc = pp.Scenario()
        gal = pp.derive(sc)["galaxy"]
        v, a = sc.speed_c * pp.C_M_PER_S, 50.0
        for part in gal["parts"]:
            seconds, share = pp._part_hop_seconds(part, sc.path_factor, v, a)
            mean_m = sc.path_factor * part["mean_spacing_pc"] * pp.PARSEC_M
            self.assertAlmostEqual(seconds / (mean_m / v + v / a), 1.0,
                                   places=4, msg=part["kind"])
            self.assertAlmostEqual(share, 1.0, places=4, msg=part["kind"])

    def test_shares_add_up_for_a_disc_smaller_than_its_scale_length(self):
        # Found by a sweep over random scenarios: the weights of the
        # numerical average summed to 1.00007 here, so the share of hops
        # reaching cruise speed could exceed one.
        sc = pp.Scenario(disc_radius_kpc=3.9, scale_length_kpc=11.2,
                         bulge_fraction=0.0, acceleration_m_s2=0.035,
                         speed_c=0.09)
        r = pp.derive(sc)
        self.assertLessEqual(r["kinematics"]["hops_reaching_cruise"], 1.0)
        gal = r["galaxy"]
        v = sc.speed_c * pp.C_M_PER_S
        seconds, share = pp._part_hop_seconds(gal["parts"][0],
                                              sc.path_factor, v, 1e6)
        mean_m = (sc.path_factor * gal["parts"][0]["mean_spacing_pc"]
                  * pp.PARSEC_M)
        self.assertAlmostEqual(seconds / (mean_m / v + v / 1e6), 1.0,
                               places=4)
        self.assertAlmostEqual(share, 1.0, places=12)

    def test_numerical_average_matches_sampled_systems(self):
        # Weak engines: many hops never reach cruise speed. Compare with
        # hops drawn from the density field itself.
        sc = by_region(acceleration_m_s2=0.004)
        r = pp.derive(sc)
        gal = r["galaxy"]
        v = sc.speed_c * pp.C_M_PER_S
        ramp_m = v * v / 0.004
        rng = random.Random(21)
        xm = gal["disc_radius_pc"] / gal["scale_length_pc"]
        total = reach = 0.0
        count = 60_000
        for _ in range(count):
            if rng.random() < sc.bulge_fraction:
                r2 = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(3))
                density = gal["bulge_central_density"] * math.exp(-r2 / 2.0)
            else:
                while True:
                    x = -math.log(rng.random() * rng.random())
                    if x <= xm:
                        break
                density = gal["disc_central_density"] * math.exp(
                    -x + math.log(rng.random()))
            d = sc.path_factor * density ** (-1.0 / 3.0) * pp.PARSEC_M
            total += pp.leg_seconds(d, v, 0.004)
            reach += d >= ramp_m
        self.assertAlmostEqual(
            total / count / pp.YEAR_S / r["hop_years"], 1.0, delta=0.02)
        self.assertAlmostEqual(reach / count,
                               r["kinematics"]["hops_reaching_cruise"],
                               delta=0.02)
        self.assertGreater(r["kinematics"]["hops_reaching_cruise"], 0.1)
        self.assertLess(r["kinematics"]["hops_reaching_cruise"], 0.9)

    def test_weaker_engines_always_take_longer(self):
        totals = [pp.derive(pp.Scenario(acceleration_m_s2=a))["total_years"]
                  for a in (None, 10.0, 1.0, 0.1, 0.01, 0.001, 0.0001)]
        self.assertEqual(totals, sorted(totals))
        self.assertEqual(len(set(totals)), len(totals))

    def test_scattering_and_detours_start_and_end_at_rest_too(self):
        sc = pp.Scenario(acceleration_m_s2=0.05, archives="stations-only")
        r = pp.derive(sc)
        v = sc.speed_c * pp.C_M_PER_S
        self.assertAlmostEqual(
            r["phases"]["dispersal_years"],
            pp.leg_seconds(30 * pp.KPC_M, v, 0.05) / pp.YEAR_S)
        deposits = r["regions_per_probe"] / r["layout"]["deposit_every"]
        self.assertAlmostEqual(
            r["phases"]["archive_detours_years"]
            / (deposits * 2 * pp.leg_seconds(0.5 * pp.KPC_M, v, 0.05)
               / pp.YEAR_S), 1.0, places=12)

    def test_report_quotes_reference_accelerations_when_none_is_given(self):
        r = pp.derive(by_region())
        refs = r["kinematics"]["reference"]
        self.assertEqual([ref["acceleration_m_s2"] for ref in refs],
                         list(pp.REFERENCE_ACCELERATIONS))
        for ref in refs:
            with_it = pp.derive(by_region(
                acceleration_m_s2=ref["acceleration_m_s2"]))
            self.assertAlmostEqual(
                ref["extra_hop_fraction"],
                with_it["kinematics"]["extra_hop_fraction"])
        text = " ".join(pp.render_report(r).split())
        self.assertIn("Stops and starts are treated as instant", text)
        self.assertIn("--acceleration", text)
        given = " ".join(pp.render_report(pp.derive(
            by_region(acceleration_m_s2=0.01))).split())
        self.assertIn("Cruise speed is reached on only", given)


class TestSystemsReached(unittest.TestCase):
    """A region is a catalogued volume (Lexicon 5.1) and completion is
    recorded by region, while the stars drift from region to region."""

    def test_limits_of_the_drift_law(self):
        full = 1e6                               # region changes per pass
        self.assertEqual(pp.share_seen(0.0), 1.0)            # nothing moves
        self.assertAlmostEqual(pp.share_seen(full), 1 - math.exp(-1))
        self.assertAlmostEqual(pp.share_seen(full, 2.0), 1 - math.exp(-2))
        self.assertAlmostEqual(pp.share_seen(full, 0.5), 1 - math.exp(-0.5))
        self.assertAlmostEqual(pp.share_seen(0.0, 0.5), 0.5)  # straight line
        self.assertEqual(pp.share_seen(full, 0.0), 0.0)
        for changes in (0.0, 0.5, 3.0, 50.0):
            self.assertAlmostEqual(pp.share_seen(changes, 1.0 - 1e-9),
                                   pp.share_seen(changes, 1.0), places=6)
            by_passes = [pp.share_seen(changes, w)
                         for w in (0.1, 0.5, 1.0, 1.5, 3.0, 10.0)]
            self.assertEqual(by_passes, sorted(by_passes))
        by_changes = [pp.share_seen(m) for m in (0, 0.3, 1, 3, 10, 100)]
        self.assertEqual(by_changes, sorted(by_changes, reverse=True))
        # A pass that visits three systems in ten.
        self.assertAlmostEqual(pp.share_seen(0.0, 1.0, 0.3), 0.3)
        self.assertAlmostEqual(pp.share_seen(full, 1.0, 0.3),
                               1 - math.exp(-0.3))

    def test_passes_needed_for_a_share(self):
        for share in (0.5, 0.9, 0.99):
            self.assertAlmostEqual(pp.passes_for_share(share, 1e6),
                                   -math.log(1 - share), places=6)
            # The same as the extra work of choosing at random (audit
            # C6): +39, +156 and +365 percent.
            self.assertAlmostEqual(
                pp.passes_for_share(share, 1e6) / share - 1,
                {0.5: 0.386, 0.9: 1.558, 0.99: 3.652}[share], places=3)
            self.assertAlmostEqual(
                pp.share_seen(1e6, pp.passes_for_share(share, 1e6)), share)
        self.assertAlmostEqual(pp.passes_for_share(0.5, 0.0), 0.5, places=6)
        self.assertAlmostEqual(pp.passes_for_share(1.0, 0.0), 1.0, places=6)
        self.assertTrue(math.isinf(pp.passes_for_share(0.99, 1e6, 1e-7)))

    @staticmethod
    def simulate(changes, passes, seed, side=14, per_cell=10):
        """Systems move in straight lines over a square of cells that
        wraps around. In every pass each cell is surveyed once, at a
        random moment, and every system found in it is visited. Returns
        the share of systems visited at least once."""
        rng = random.Random(seed)
        count = side * side * per_cell
        # A unit of path crosses 4 / pi cell borders on average.
        speed = changes * math.pi / 4.0
        start = [(rng.uniform(0, side), rng.uniform(0, side),
                  rng.uniform(0, 2 * math.pi)) for _ in range(count)]
        seen = [False] * count
        for number in range(passes):
            order = list(range(side * side))
            rng.shuffle(order)
            for slot, cell in enumerate(order):
                when = number + (slot + 0.5) / len(order)
                col, row = cell % side, cell // side
                for index, (x, y, angle) in enumerate(start):
                    if (int((x + speed * math.cos(angle) * when) % side)
                            == col and
                            int((y + speed * math.sin(angle) * when) % side)
                            == row):
                        seen[index] = True
        return sum(seen) / count

    def test_drift_law_against_a_small_simulation(self):
        self.assertEqual(self.simulate(0.0, 1, 1), 1.0)
        for changes, passes in ((2.0, 1), (40.0, 1), (40.0, 2)):
            self.assertAlmostEqual(
                self.simulate(changes, passes, 3),
                pp.share_seen(changes, passes), delta=0.04,
                msg=(changes, passes))

    def test_default_survey_is_fully_mixed(self):
        r = pp.derive(by_region())
        reached = r["reached"]
        # A region of 1000 systems at a mean spacing of 2.02 parsecs.
        self.assertAlmostEqual(reached["region_side_parsec"],
                               10 * r["galaxy"]["mean_spacing_pc"])
        slow, fast = reached["crossing_years"]
        self.assertAlmostEqual(
            slow, reached["region_side_parsec"] * pp.PARSEC_M / 2.0e4
            / pp.YEAR_S)
        self.assertAlmostEqual(slow / fast, 3.0)
        survey = r["total_years"] - r["phases"]["dispersal_years"]
        self.assertAlmostEqual(reached["region_changes_per_pass"][0],
                               survey / slow)
        self.assertGreater(min(reached["region_changes_per_pass"]), 1000)
        self.assertLess(max(reached["region_changes_per_pass"]), 5000)
        self.assertAlmostEqual(reached["seen_after_one_pass"],
                               1 - math.exp(-1), places=9)
        self.assertAlmostEqual(reached["repeat_visit_share"], math.exp(-1),
                               places=9)
        self.assertAlmostEqual(
            reached["stream_crossing_years"],
            reached["region_side_parsec"] * pp.PARSEC_M / 2.3e5 / pp.YEAR_S)
        for row, passes in zip(reached["rows"],
                               (math.log(2), math.log(10), math.log(100))):
            self.assertAlmostEqual(row["passes"], passes, places=6)
            self.assertAlmostEqual(
                row["years"] / (r["phases"]["dispersal_years"]
                                + passes * survey), 1.0, places=6)
        # 99 percent of the systems: 4.6 passes, 5.3 billion years.
        self.assertAlmostEqual(reached["rows"][2]["years"] / 5.26e9, 1.0,
                               delta=0.01)

    def test_a_short_survey_is_not_affected(self):
        r = pp.derive(by_region(systems=2e5))
        self.assertLess(r["total_years"], 3e6)
        self.assertLess(max(r["reached"]["region_changes_per_pass"]), 0.1)
        self.assertGreater(r["reached"]["seen_after_one_pass"], 0.995)
        text = " ".join(pp.render_report(r).split())
        self.assertIn("Stars barely move during a survey this short", text)
        self.assertNotIn("one pass over every region; stars drift", text)

    def test_report_says_what_one_pass_reaches(self):
        report = pp.render_report(pp.derive(by_region()))
        lines = report.splitlines()
        at = next(i for i, line in enumerate(lines) if "HEADLINE" in line)
        block = " ".join(line.strip() for line in lines[at:lines.index("", at)])
        self.assertIn("that is one pass over every region", block)
        self.assertIn("reaches about 63% of the systems", block)
        self.assertIn("Milestones (share of regions surveyed)", report)
        self.assertNotIn("fraction of systems surveyed", report)
        text = " ".join(report.split())
        for phrase in ["Systems reached (regions are fixed volumes",
                       "one pass over every region reaches 63% of the "
                       "systems, and 37% of its visits go to systems "
                       "already seen",
                       "99% 4.6 5.3 billion years",
                       "90% 2.3 2.6 billion years",
                       "50% 0.69 790 million years",
                       "the fleet stops after one pass"]:
            self.assertIn(phrase, text)

    def test_losses_can_put_further_passes_out_of_reach(self):
        r = pp.derive(by_region(attrition_per_year=5e-10))
        self.assertFalse(r["fleet_exhausted"])           # one pass is done
        rows = r["reached"]["rows"]
        self.assertIsNotNone(rows[0]["years"])           # 0.69 passes
        self.assertIsNone(rows[1]["years"])              # 2.3 passes
        self.assertIsNone(rows[2]["years"])
        self.assertIn("not reached", pp.render_report(r))
        json.dumps(pp.json_safe(r), allow_nan=False)


def simulate_line(sc, stars=20_000, seed=3, against_rotation=0.0,
                  ring_pc=150.0):
    """A direct simulation of the held line, to check the model against.

    Every disc system circles the center and swings in and out around its
    mean distance. The line is cut into rings; working inward, each ring
    is staffed for one turn as soon as the fleet has the capacity for the
    systems that cross it. A system is surveyed whenever it crosses a ring
    that is staffed at that moment. Returns the share of disc systems
    surveyed at least once, the visits per system, and the years taken.
    `against_rotation` turns the line backward at that angular speed."""
    r = pp.derive(sc, detail=False)
    gal = r["galaxy"]
    line = pp.sweep_line(sc, gal, r["per_system_years"])
    scale, radius = gal["scale_length_pc"], gal["disc_radius_pc"]
    xm = radius / scale
    speed = pp.ROTATION_SPEED_M_S * pp.YEAR_S / pp.PARSEC_M
    level = gal["disc_systems"] / (2 * math.pi * scale ** 2 * pp._g1(xm))
    top = radius * 1.25                 # the line reaches past the rim
    rings = []
    edge = top
    while edge > 1e-9:
        inner = max(0.0, edge - ring_pc)
        mid = 0.5 * (edge + inner)
        turning = speed / max(mid, 50.0) + against_rotation
        density = level * math.exp(-mid / scale) if mid <= radius else 0.0
        rings.append(dict(need=density * (edge - inner) * mid * turning,
                          turn=2 * math.pi / turning))
        edge = inner
    clock, staffed = 0.0, []
    for ring in rings:
        need = min(ring["need"], line["capacity_per_year"])
        while staffed and (sum(n for _, n in staffed) + need
                           > line["capacity_per_year"] * (1 + 1e-9)):
            staffed.sort()
            clock = max(clock, staffed.pop(0)[0])
        ring["open"], ring["shut"] = clock, clock + ring["turn"]
        staffed.append((ring["shut"], need))
    end = max(shut for shut, _ in staffed)
    rng = random.Random(seed)
    swing_per_pc = pp.RADIAL_RANDOM_SPEED_M_S / (math.sqrt(2)
                                                 * pp.ROTATION_SPEED_M_S)
    seen = visits = 0
    for _ in range(stars):
        while True:                         # mean distance from the center
            x = -math.log(rng.random() * rng.random())
            if x <= xm:
                break
        mean_r = x * scale
        turning = speed / max(mean_r, 50.0)
        swing = swing_per_pc * mean_r * math.sqrt(
            -2.0 * math.log(1.0 - rng.random()))
        phase = rng.uniform(0, 2 * math.pi)
        when = rng.uniform(0, 2 * math.pi) / (turning + against_rotation)
        count = 0
        while when < end:
            # in-and-out swings run sqrt(2) times as fast as the circling
            where = mean_r + swing * math.cos(
                math.sqrt(2.0) * turning * when + phase)
            if 0.0 <= where < top:
                ring = rings[min(len(rings) - 1, int((top - where) / ring_pc))]
                count += ring["open"] <= when < ring["shut"]
            when += 2 * math.pi / (turning + against_rotation)
        seen += count > 0
        visits += count
    return seen / stars, visits / stars, end


def simulate_midplane(stars=4000, height=12.0, layer=0.3, speed=0.1, seed=5,
                      marks=(0.5, 0.8)):
    """Stars swing through the mid-plane of a disc whose density falls off
    as exp(-|z| / height); a constant pull toward the plane keeps that
    profile. One probe keeps within `layer` x height of the plane and
    always goes to the nearest system there that is not yet surveyed.
    Lengths are in spacings at the mid-plane, speeds in probe speeds.
    Returns, for each share of all systems done, the share still to do of
    the systems then inside the layer."""
    rng = random.Random(seed)
    pull = speed * speed / height
    width = layer * height
    side = math.sqrt(stars / (2.0 * height))
    x0 = [rng.random() * side for _ in range(stars)]
    y0 = [rng.random() * side for _ in range(stars)]
    vx = [rng.gauss(0.0, speed) for _ in range(stars)]
    vy = [rng.gauss(0.0, speed) for _ in range(stars)]
    top, half_swing, phase = [], [], []
    for _ in range(stars):
        z = rng.expovariate(1.0 / height)
        v = rng.gauss(0.0, speed)                  # away from the plane
        v_plane = math.sqrt(v * v + 2.0 * pull * z)
        top.append(v_plane)
        half_swing.append(2.0 * v_plane / pull)    # plane to plane
        phase.append((v_plane - v) / pull
                     + (half_swing[-1] if rng.random() < 0.5 else 0.0))
    alive = list(range(stars))
    done = [False] * stars
    inside_at_start = None
    here = (0.0, 0.0, 0.0)
    clock = refresh_at = 0.0
    count = 0
    out = {}
    marks = list(marks)
    near = []
    trail = []          # unsurveyed inside the layer / inside at the start
    while marks:
        if clock >= refresh_at:
            alive = [j for j in alive if not done[j]]
            near = []
            for j in alive:
                t = phase[j] + clock
                swings = int(t / half_swing[j])
                t -= swings * half_swing[j]
                z = top[j] * t - 0.5 * pull * t * t
                if z < width:
                    near.append((j, (x0[j] + vx[j] * clock) % side,
                                 (y0[j] + vy[j] * clock) % side,
                                 z if swings % 2 == 0 else -z))
            if inside_at_start is None:
                inside_at_start = len(near)
            trail.append(len(near) / inside_at_start)
            refresh_at = clock + 0.5 / speed
        best = None
        for k, (j, x, y, z) in enumerate(near):
            if done[j]:
                continue
            dx = abs(x - here[0])
            dy = abs(y - here[1])
            dx = min(dx, side - dx)
            dy = min(dy, side - dy)
            d = dx * dx + dy * dy + (z - here[2]) ** 2
            if best is None or d < best[0]:
                best = (d, k)
        if best is None:
            clock = refresh_at
            continue
        j, x, y, z = near[best[1]]
        done[j] = True
        here = (x, y, z)
        clock += math.sqrt(best[0])
        count += 1
        if count >= marks[0] * stars:
            out[marks.pop(0)] = sum(trail[-4:]) / len(trail[-4:])
    return out


def simulate_open_field(stars=2000, speed=0.018, seed=7, marks=(0.5, 0.9)):
    """Stars drift at random through a cube that wraps around; one probe
    always goes to the nearest system not yet surveyed. Lengths are in
    spacings, speeds in probe speeds. Returns the distance traveled per
    system at each share done."""
    rng = random.Random(seed)
    side = stars ** (1.0 / 3.0)
    start = [[rng.random() * side for _ in range(3)] for _ in range(stars)]
    drift = [[rng.gauss(0.0, speed) for _ in range(3)] for _ in range(stars)]
    alive = list(range(stars))
    done = [False] * stars
    here = [0.0, 0.0, 0.0]
    clock = refresh_at = traveled = 0.0
    count = 0
    out = {}
    marks = list(marks)
    spots = []
    while marks:
        if clock >= refresh_at:
            alive = [j for j in alive if not done[j]]
            spots = [(j, [(start[j][a] + drift[j][a] * clock) % side
                          for a in range(3)]) for j in alive]
            refresh_at = clock + 0.5 / speed
        best = None
        for j, spot in spots:
            if done[j]:
                continue
            d = 0.0
            for a in range(3):
                gap = abs(spot[a] - here[a])
                gap = min(gap, side - gap)
                d += gap * gap
            if best is None or d < best[0]:
                best = (d, j, spot)
        done[best[1]] = True
        here = best[2]
        hop = math.sqrt(best[0])
        clock += hop
        traveled += hop
        count += 1
        if count >= marks[0] * stars:
            out[marks.pop(0)] = traveled / stars
    return out


class TestStrategies(unittest.TestCase):
    """Other ways of running the survey, compared with the specification."""

    def test_default_is_the_plan(self):
        # Completion recorded by system, probes waiting at the mid-plane.
        # The specification as it stands, by regions, comes first in the
        # list and stays one flag away.
        self.assertEqual(pp.Scenario().strategy, "systems-midplane")
        self.assertEqual(pp.derive(pp.Scenario())["strategy"],
                         "systems-midplane")
        self.assertEqual(parse([]).strategy, "systems-midplane")
        self.assertEqual(list(pp.STRATEGIES)[0], "regions")
        self.assertEqual(parse(["--strategy", "regions"]).strategy,
                         "regions")
        self.assertIn("default systems-midplane",
                      " ".join(pp.build_parser().format_help().split()))
        with self.assertRaises(ValueError):
            pp.derive(pp.Scenario(strategy="teleport"))
        for name in pp.STRATEGIES:
            r = pp.derive(parse(["--strategy", name]))
            self.assertEqual(r["strategy"], name)
            self.assertGreater(r["total_years"], 0)
            json.dumps(pp.json_safe(r), allow_nan=False)

    # ---- completion recorded by system ---------------------------------

    def test_thinning_integral(self):
        # Mean of (1 - x)^(-1/3) for x from 0 to f, times f.
        for share in (0.5, 0.9, 0.99, 1.0):
            steps = 200_000
            total = sum((1 - (i + 0.5) * share / steps) ** (-1 / 3)
                        for i in range(steps)) * share / steps
            self.assertAlmostEqual(
                total, 1.5 * (1 - (1 - share) ** (2 / 3)), places=3)

    def test_nearest_unsurveyed_system_among_drifting_stars(self):
        # Full-size runs (100,000 and 300,000 systems): hops of 0.65
        # times the spacing of the systems still to do, from the first
        # to the 99th percent, whatever the drift speed. A field of fixed
        # points starts at 0.65 too and ends at 0.78 on average. This is
        # a small run.
        self.assertEqual(pp.OPEN_FIELD_HOP, 0.65)
        self.assertEqual(pp.CLEARED_FIELD_HOP, pp.Scenario().path_factor)
        traveled = simulate_open_field()
        for share, per_system in traveled.items():
            even = 1.5 * (1 - (1 - share) ** (2 / 3))
            self.assertAlmostEqual(per_system / even, pp.OPEN_FIELD_HOP,
                                   delta=0.03)

    def test_records_by_system_shorten_the_first_hops(self):
        base = pp.derive(pp.Scenario(strategy="regions"))
        for path_factor in (0.78, 1.0):
            by_region = pp.derive(pp.Scenario(strategy="regions",
                                              path_factor=path_factor))
            by_system = pp.derive(pp.Scenario(strategy="systems",
                                              path_factor=path_factor))
            self.assertAlmostEqual(
                by_system["hop_parsec"] / by_region["hop_parsec"],
                0.65 / 0.78)
        self.assertAlmostEqual(
            pp.derive(pp.Scenario(strategy="systems"))["hop_parsec"],
            0.65 * base["galaxy"]["mean_spacing_pc"])
        # The route through a region is not touched.
        self.assertAlmostEqual(base["hop_parsec"],
                               0.78 * base["galaxy"]["mean_spacing_pc"])
        text = " ".join(line.strip() for line in pp.render_report(
            pp.derive(pp.Scenario(strategy="systems"))).splitlines())
        self.assertIn("its hops are 0.65 times the spacing of the systems "
                      "still to do, against 0.78", text)
        self.assertIn("path_factor x 0.65 / 0.78", pp.render_explain(
            pp.derive(pp.Scenario(strategy="systems"))))
        self.assertNotIn("0.65 / 0.78", pp.render_explain(base))

    def test_hop_spread_and_engines_follow_the_first_hops(self):
        by_region = pp.derive(pp.Scenario(strategy="regions"))
        for name in pp.RECORDS_BY_SYSTEM:
            r = pp.derive(pp.Scenario(strategy=name))
            # the spread of hop lengths is that of the first hops
            pct = r["hop_percentiles_parsec"]
            self.assertLess(pct["5"], pct["50"])
            self.assertLess(pct["50"], r["hop_parsec"])
            self.assertLess(r["hop_parsec"], pct["95"])
            # what an engine adds is measured on the same hops
            given = {a: pp.derive(pp.Scenario(strategy=name,
                                              acceleration_m_s2=a))
                     for a in pp.REFERENCE_ACCELERATIONS}
            for row in r["kinematics"]["reference"]:
                run = given[row["acceleration_m_s2"]]
                self.assertAlmostEqual(
                    row["extra_hop_fraction"],
                    run["kinematics"]["extra_hop_fraction"])
        plain = pp.derive(pp.Scenario(strategy="systems"))
        for key, value in plain["hop_percentiles_parsec"].items():
            self.assertAlmostEqual(
                value / by_region["hop_percentiles_parsec"][key], 0.65 / 0.78)

    def test_records_by_system_lengthen_hops_not_stays(self):
        base = pp.derive(pp.Scenario(strategy="regions"))
        r = pp.derive(pp.Scenario(strategy="systems"))
        first = base["hop_years"] * 0.65 / 0.78
        self.assertEqual(r["hop_thinning"], 1.5)
        self.assertEqual(base["hop_thinning"], 1.0)
        self.assertAlmostEqual(r["hop_years"], first)          # first hops
        self.assertAlmostEqual(r["hop_years_average"], 1.5 * first)
        self.assertAlmostEqual(r["per_system_years"], 1.5 * first + 10.0)
        self.assertAlmostEqual(
            r["phases"]["survey_work_years"]
            / (r["visited_per_probe"] * r["per_system_years"]), 1.0,
            places=12)
        self.assertAlmostEqual(
            r["distance"]["survey_path_m"] / base["distance"]["survey_path_m"]
            * (1 + base["duplication_fraction"])
            / (1 + r["duplication_fraction"]), 1.5 * 0.65 / 0.78)
        self.assertEqual(r["milestones_count"], "systems")
        self.assertEqual(r["reached"]["seen_after_one_pass"], 1.0)
        self.assertEqual(r["reached"]["repeat_visit_share"], 0.0)
        # Speeding up and slowing down is not stretched, only the cruise.
        slow = pp.derive(pp.Scenario(strategy="systems",
                                     acceleration_m_s2=0.05))
        ramp = slow["kinematics"]["ramp_years"]
        cruise = slow["hop_parsec"] * pp.PARSEC_M / slow["speed_m_per_s"] \
            / pp.YEAR_S
        self.assertAlmostEqual(slow["hop_years_average"],
                               1.5 * cruise + ramp)

    def test_milestones_by_system_follow_the_thinning_law(self):
        def check(sc, path):
            r = pp.derive(sc)
            scattering = r["phases"]["dispersal_years"]
            survey = r["total_years"] - scattering
            for m in r["milestones"]:
                share = m["fraction"]
                work = (r["hop_years"] * path(r, share)
                        + 10.0 * share) / r["per_system_years"]
                self.assertAlmostEqual(
                    m["years"] / (scattering + work * survey), 1.0, places=9)
            self.assertAlmostEqual(r["milestones"][-1]["years"],
                                   r["total_years"])
            return r

        def by_part(r, share):
            gal = r["galaxy"]
            return sum(part["share"] * part["mean_spacing_pc"]
                       * pp._WORK[part["kind"]][0](share)
                       for part in gal["parts"]) / gal["mean_spacing_pc"]

        # One density throughout: every system is equally likely to be
        # next, and the distance follows (1 - share)^(-1/3).
        check(pp.Scenario(strategy="systems", galaxy_model="uniform"),
              lambda r, share: 1.5 * (1 - (1 - share) ** (2 / 3)))
        check(pp.Scenario(strategy="systems-midplane"), by_part)
        r = check(pp.Scenario(strategy="systems"), by_part)
        # Half the systems take less than half the time, the last tenth
        # more than a tenth.
        half, ninety = r["milestones"][0]["years"], r["milestones"][1]["years"]
        self.assertLess(half, 0.5 * r["total_years"])
        self.assertGreater(r["total_years"] - ninety, 0.1 * r["total_years"])
        for row, m in zip(r["reached"]["rows"], r["milestones"]):
            self.assertEqual(row["systems_seen"], m["fraction"])
            self.assertAlmostEqual(row["years"], m["years"])
            self.assertIsNone(row["passes"])

    def test_a_sampled_survey_cannot_see_more_than_it_visits(self):
        r = pp.derive(pp.Scenario(strategy="systems", depth=0.6))
        rows = r["reached"]["rows"]
        self.assertAlmostEqual(r["reached"]["seen_after_one_pass"], 0.6)
        self.assertIsNotNone(rows[0]["years"])           # 50 percent
        self.assertIsNone(rows[1]["years"])              # 90 percent
        self.assertIn("not reached",
                      " ".join(pp.describe_strategies(r)))

    # ---- working at the mid-plane --------------------------------------

    def test_mid_plane_spacing_is_the_integral_over_the_plane(self):
        sc = pp.Scenario(strategy="systems-midplane")
        gal = pp.derive(sc)["galaxy"]
        disc, bulge = gal["parts"]
        # Only the disc has a mid-plane to wait at; the bulge is round.
        self.assertEqual((disc["kind"], bulge["kind"]),
                         ("disc-plane", "bulge"))
        scale, radius = gal["scale_length_pc"], gal["disc_radius_pc"]
        steps = 20_000
        dr = radius / steps
        top = bottom = 0.0
        for i in range(steps):          # systems per ring at the mid-plane
            r_pc = (i + 0.5) * dr
            density = gal["disc_central_density"] * math.exp(-r_pc / scale)
            top += r_pc * density ** (2 / 3) * dr
            bottom += r_pc * density * dr
        self.assertAlmostEqual(top / bottom / disc["mean_spacing_pc"], 1.0,
                               places=5)
        plain = pp.derive(pp.Scenario(strategy="systems"))["galaxy"]
        self.assertEqual(bulge, plain["parts"][1])

    def test_waiting_at_the_mid_plane_saves_nothing_overall(self):
        plain = pp.derive(pp.Scenario(strategy="systems"))
        plane = pp.derive(pp.Scenario(strategy="systems-midplane"))
        # The first hops are shorter: 2/3 of the spacing in the disc.
        self.assertAlmostEqual(
            plane["galaxy"]["parts"][0]["mean_spacing_pc"]
            / plain["galaxy"]["parts"][0]["mean_spacing_pc"], 2 / 3)
        self.assertAlmostEqual(plane["hop_parsec"] / plain["hop_parsec"],
                               0.70, delta=0.005)
        self.assertAlmostEqual(
            plane["galaxy"]["mean_spacing_at_large_pc"],
            plain["galaxy"]["mean_spacing_pc"])
        # They grow faster, by 9/4 against 3/2 over the whole survey, and
        # 2/3 x 9/4 = 3/2: the whole survey takes as long either way.
        self.assertAlmostEqual(plane["total_years"] / plain["total_years"],
                               1.0, places=12)
        self.assertAlmostEqual(plane["hop_years_average"],
                               plain["hop_years_average"])
        self.assertGreater(plane["hop_thinning"], plain["hop_thinning"])
        # Half of the systems come sooner; 90 and 99 percent do not.
        sooner = [a["years"] / b["years"] for a, b in zip(
            plane["reached"]["rows"], plain["reached"]["rows"])]
        self.assertAlmostEqual(sooner[0], 0.91, delta=0.02)
        self.assertAlmostEqual(sooner[1], 1.0, delta=0.01)
        self.assertAlmostEqual(sooner[2], 1.0, delta=0.001)
        self.assertAlmostEqual(plane["plane_left_at_half"], 0.187,
                               delta=0.001)
        self.assertIsNone(plain["plane_left_at_half"])
        # A uniform disc is as dense at the mid-plane as anywhere.
        flat = [pp.derive(pp.Scenario(strategy=name, galaxy_model="uniform"))
                for name in ("systems", "systems-midplane")]
        self.assertEqual(flat[0]["total_years"], flat[1]["total_years"])
        self.assertEqual(flat[0]["milestones"], flat[1]["milestones"])
        self.assertIsNone(flat[1]["plane_left_at_half"])

    def test_mid_plane_law_from_the_motion_of_the_stars(self):
        # A star in a constant pull toward the plane, turning at height
        # x, spends 1 - sqrt(1 - w / x) of its time below w: w / (2 x)
        # for a thin layer.
        for x in (0.5, 2.0, 6.0):
            below = 0
            steps = 100_000
            for i in range(steps):
                t = (i + 0.5) / steps           # plane to turning point
                if x * (2 * t - t * t) < 0.01:
                    below += 1
            self.assertAlmostEqual(below / steps / (0.01 / (2 * x)), 1.0,
                                   delta=0.01)
        # Stars of one random speed have x spread as sqrt(x) exp(-x).
        # Each is surveyed at a rate that goes as 1 / x, so after a while
        # the share exp(-s / x) of them is left. Summed over the stars
        # that gives the two shares of the formula, with y = 2 sqrt(s).
        def over_stars(weight):
            total = 0.0
            for i in range(20_000):             # x = t^2 keeps it smooth
                t = (i + 0.5) * 3e-4
                total += (4 / math.sqrt(math.pi) * t * t * math.exp(-t * t)
                          * weight(t * t) * 3e-4)
            return total
        self.assertAlmostEqual(over_stars(lambda x: 1.0), 1.0, places=6)
        self.assertAlmostEqual(over_stars(lambda x: 1.0 / x), 2.0, places=6)
        for s in (0.05, 0.7, 3.8, 11.0):
            y = 2 * math.sqrt(s)
            left = over_stars(lambda x: math.exp(-s / x))
            near = over_stars(lambda x: math.exp(-s / x) / x) / 2.0
            self.assertAlmostEqual(left / ((1 + y) * math.exp(-y)), 1.0,
                                   places=5)
            self.assertAlmostEqual(near / math.exp(-y), 1.0, places=5)
            self.assertAlmostEqual(pp._plane_progress(1 - left), y, places=4)
            self.assertAlmostEqual(pp.plane_left(1 - left) / near, 1.0,
                                   places=4)

    def test_mid_plane_distance_is_the_sum_of_its_hops(self):
        # A hop is (share left near the plane)^(-1/3) first hops.
        for share in (0.5, 0.9, 0.99):
            steps = 20_000
            total = sum(pp.plane_left((i + 0.5) * share / steps) ** (-1 / 3)
                        for i in range(steps)) * share / steps
            self.assertAlmostEqual(total / pp._plane_work(share), 1.0,
                                   places=3)
            self.assertAlmostEqual(
                pp._plane_growth(share),
                pp.plane_left(share) ** (-1 / 3))
        self.assertEqual(pp._plane_work(0.0), 0.0)
        self.assertEqual(pp._plane_work(1.0), 2.25)
        self.assertEqual(pp.plane_left(0.0), 1.0)
        self.assertEqual(pp.plane_left(1.0), 0.0)
        self.assertAlmostEqual(pp._plane_work(1e-4) / 1e-4, 1.0, delta=0.01)
        # Against even thinning: 1.25, 1.40 and 1.47 times the distance.
        for share, ratio in ((0.5, 1.25), (0.9, 1.40), (0.99, 1.47)):
            self.assertAlmostEqual(
                pp._plane_work(share) / pp._even_work(share), ratio,
                delta=0.005)

    def test_mid_plane_law_against_a_direct_simulation(self):
        # Full-size runs (100,000 systems, a layer of 0.3 scale heights
        # either side): 0.228 of the systems near the plane left when half
        # of all are done, 0.025 at 90 percent; distance 1.205, 1.372 and
        # 1.447 times that of a slab in which every system is equally
        # exposed, at 50, 90 and 99 percent. This is a small one.
        left = simulate_midplane()
        self.assertAlmostEqual(left[0.5], pp.plane_left(0.5), delta=0.07)
        self.assertAlmostEqual(left[0.8], pp.plane_left(0.8), delta=0.03)
        # Far less than the half and the fifth that even thinning leaves.
        self.assertLess(left[0.5], 0.3)
        self.assertLess(left[0.8], 0.1)

    def test_fleet_spread_like_the_systems(self):
        # First hops 3/2 of those at the mid-plane, the same distance in
        # the end, and in between the ratios of the full-size simulation
        # (eight probes, each in its own band of heights, against one at
        # the mid-plane): 1.115, 1.005 and 0.990 at 50, 90 and 99 percent.
        self.assertEqual(pp._spread_work(0.0), 0.0)
        self.assertAlmostEqual(pp._spread_work(1.0), 1.5)
        self.assertAlmostEqual(pp._spread_work(1e-4) / 1e-4, 1.0, delta=0.01)
        for share, simulated in ((0.5, 1.115), (0.9, 1.005), (0.99, 0.990)):
            ratio = pp._spread_work(share) / (2 / 3 * pp._plane_work(share))
            self.assertAlmostEqual(ratio, simulated, delta=0.015)
        # Each growth is the slope of its distance.
        for work, growth in pp._WORK.values():
            previous = 0.0
            for share in (0.1, 0.5, 0.9, 0.99):
                slope = (work(share + 1e-6) - work(share - 1e-6)) / 2e-6
                self.assertAlmostEqual(slope / growth(share), 1.0, places=5)
                self.assertGreater(work(share), previous)
                previous = work(share)
        self.assertEqual(set(pp._WORK),
                         {"disc", "disc-plane", "bulge", "uniform"})

    def test_mid_plane_distribution_is_consistent(self):
        sc = pp.Scenario(strategy="systems-midplane")
        r = pp.derive(sc)
        gal = r["galaxy"]
        for share in (0.05, 0.5, 0.95):
            value = pp.spacing_percentile(gal, share)
            self.assertAlmostEqual(pp.spacing_cdf(gal, value), share,
                                   places=9)
        pct = r["hop_percentiles_parsec"]
        self.assertLess(pct["5"], pct["50"])
        self.assertLess(pct["50"], pct["95"])
        v = sc.speed_c * pp.C_M_PER_S
        for part in gal["parts"]:
            seconds, share = pp._part_hop_seconds(part, sc.path_factor, v,
                                                  1e6)
            mean_m = sc.path_factor * part["mean_spacing_pc"] * pp.PARSEC_M
            self.assertAlmostEqual(seconds / (mean_m / v + v / 1e6), 1.0,
                                   places=4, msg=part["kind"])
        weak = pp.derive(pp.Scenario(strategy="systems-midplane",
                                     acceleration_m_s2=0.003))
        self.assertGreater(weak["kinematics"]["hops_reaching_cruise"], 0.0)
        self.assertLess(weak["kinematics"]["hops_reaching_cruise"], 1.0)

    # ---- where the stars do not mix ------------------------------------

    def test_default_fleet_is_fully_mixed(self):
        for name in pp.RECORDS_BY_SYSTEM:
            r = pp.derive(pp.Scenario(strategy=name))
            self.assertAlmostEqual(r["mixing"]["crossings"], 53, delta=1)
            self.assertEqual(r["mixing"]["share"], 1.0)
        for name in ("regions", "sweep-line"):
            r = pp.derive(pp.Scenario(strategy=name))
            self.assertIsNone(r["mixing"])
            self.assertIsNone(r["plane_wait"])

    def test_stars_that_stand_still_leave_nothing_to_gain(self):
        # A fleet so large that the survey is over before the stars have
        # moved: recording by system then changes nothing.
        huge = dict(probes=10_000_000_000)
        by_region = pp.derive(pp.Scenario(strategy="regions", **huge))
        for name in pp.RECORDS_BY_SYSTEM:
            r = pp.derive(pp.Scenario(strategy=name, **huge))
            self.assertLess(r["mixing"]["share"], 0.01)
            self.assertAlmostEqual(r["total_years"] / by_region["total_years"],
                                   1.0, delta=0.001)
            self.assertAlmostEqual(r["hop_parsec"] / by_region["hop_parsec"],
                                   1.0, delta=0.01)
            self.assertAlmostEqual(r["hop_thinning"], 1.0, delta=0.01)
            text = " ".join(x.strip() for x in pp.render_report(r).splitlines())
            self.assertIn("The stars barely move during a survey this short",
                          text)
            self.assertNotIn("thin out", text)

    def test_partial_mixing_lies_between_the_two_laws(self):
        still = pp.derive(pp.Scenario(strategy="regions"))
        mixed = pp.derive(pp.Scenario(strategy="systems"))
        previous = None
        for probes in (10_000, 300_000, 3_000_000, 30_000_000, 10 ** 9):
            r = pp.derive(pp.Scenario(strategy="systems", probes=probes))
            share = r["mixing"]["share"]
            self.assertAlmostEqual(share,
                                   1 - math.exp(-r["mixing"]["crossings"]))
            if previous is not None:
                self.assertLess(share, previous)    # shorter survey, less
            previous = share
            self.assertAlmostEqual(
                r["hop_parsec"],
                (1 - share) * still["hop_parsec"]
                + share * mixed["hop_parsec"])
            self.assertAlmostEqual(
                r["hop_parsec"] * r["hop_thinning"],
                (1 - share) * still["hop_parsec"]
                + share * 1.5 * mixed["hop_parsec"])
        r = pp.derive(pp.Scenario(strategy="systems", probes=3_000_000))
        self.assertGreater(r["mixing"]["share"], 0.05)
        self.assertLess(r["mixing"]["share"], 0.995)
        text = " ".join(x.strip() for x in pp.render_report(r).splitlines())
        self.assertIn("The stars mix only in part during a survey this "
                      "short", text)
        # One probe's share of the galaxy: its systems at the mean spacing.
        side = r["mixing"]["probe_share_side_parsec"]
        self.assertAlmostEqual(
            side, (1e11 / 3e6) ** (1 / 3) * r["galaxy"]["mean_spacing_pc"])

    def test_waiting_at_the_mid_plane_needs_several_swings(self):
        # Simulated (layer of 0.3 scale heights either side): distance to
        # 99 percent, over that of a slab in which every system is equally
        # exposed, for surveys of 7.8, 3.9, 1.9, 1.0 and 0.45 swings:
        # 1.45, 1.47, 1.58, 1.86 and 2.65, the last two with idle probes.
        r = pp.derive(pp.Scenario(strategy="systems-midplane"))
        wait = r["plane_wait"]
        self.assertTrue(wait["waits"])
        self.assertAlmostEqual(wait["swing_years"], 7 * 350 * pp.PARSEC_M
                               / 2.0e4 / pp.YEAR_S)
        self.assertAlmostEqual(wait["swing_years"] / 1.2e8, 1.0, delta=0.01)
        self.assertAlmostEqual(wait["swings"], 9.4, delta=0.1)
        self.assertEqual(r["galaxy"]["parts"][0]["kind"], "disc-plane")
        self.assertIsNone(
            pp.derive(pp.Scenario(strategy="systems"))["plane_wait"])
        # Ten times the fleet: the survey lasts one swing, and the probes
        # go to the systems instead.
        short = pp.derive(pp.Scenario(strategy="systems-midplane",
                                      probes=100_000))
        plain = pp.derive(pp.Scenario(strategy="systems", probes=100_000))
        self.assertFalse(short["plane_wait"]["waits"])
        self.assertLess(short["plane_wait"]["swings"],
                        pp.PLANE_SWINGS_NEEDED)
        self.assertEqual(short["milestones"], plain["milestones"])
        self.assertEqual(short["hop_parsec"], plain["hop_parsec"])
        self.assertEqual(short["galaxy"]["parts"][0]["kind"], "disc")
        self.assertIsNone(short["plane_left_at_half"])
        text = " ".join(x.strip()
                        for x in pp.render_report(short).splitlines())
        self.assertIn("Waiting at the mid-plane does not work for a survey "
                      "this short", text)
        # A uniform disc has no mid-plane to wait at.
        self.assertIsNone(pp.derive(pp.Scenario(
            strategy="systems-midplane",
            galaxy_model="uniform"))["plane_wait"])

    def test_wording_of_every_case(self):
        for name in pp.RECORDS_BY_SYSTEM:
            for probes in (10_000, 100_000, 3_000_000, 10 ** 9):
                for extra in ({}, {"galaxy_model": "uniform"}):
                    r = pp.derive(pp.Scenario(strategy=name, probes=probes,
                                              **extra))
                    for text in (pp.render_report(r), pp.render_explain(r),
                                 pp.render_report(r, canonical=True)):
                        self.assertEqual(banned_tokens(text), [])
                    json.dumps(pp.json_safe(r), allow_nan=False)

    # ---- a line held while the disc turns past it ----------------------

    def test_line_missed_share_and_its_limits(self):
        self.assertEqual(pp.line_missed(0.0), 0.0)
        self.assertAlmostEqual(pp.line_missed(1e6), math.exp(-1), places=4)
        values = [pp.line_missed(q) for q in
                  (0.001, 0.01, 0.1, 0.5, 1, 2, 8, 64, 500, 1e4)]
        self.assertEqual(values, sorted(values))
        for q in (0.03, 0.4, 1.0, 3.0, 20.0, 150.0):
            self.assertAlmostEqual(pp.line_missed(q), pp._tile_missed(q, 64),
                                   delta=0.004, msg=q)
        # A swing as wide as the staffed stretch: one system in five.
        self.assertAlmostEqual(pp.line_missed(1.0), 0.20, delta=0.01)
        self.assertAlmostEqual(pp.line_seen(0.25, 1.0), 0.75)
        self.assertAlmostEqual(pp.line_seen(0.25, 0.5), 0.375)
        self.assertAlmostEqual(pp.line_seen(0.25, 3.0), 1 - 0.25 ** 3)

    def test_crossings_capacity_and_staffing(self):
        sc = pp.Scenario(strategy="sweep-line")
        r = pp.derive(sc)
        gal, line = r["galaxy"], r["reached"]["line"]
        scale, radius = gal["scale_length_pc"], gal["disc_radius_pc"]
        speed = pp.ROTATION_SPEED_M_S * pp.YEAR_S / pp.PARSEC_M
        level = gal["disc_systems"] / (
            2 * math.pi * scale ** 2 * pp._g1(radius / scale))
        steps = 50_000
        crossings = sum(level * math.exp(-(i + 0.5) * radius / steps / scale)
                        * speed * radius / steps for i in range(steps))
        self.assertAlmostEqual(line["crossings_per_year"] / crossings, 1.0,
                               places=6)
        self.assertAlmostEqual(line["share_of_systems"], 0.85)
        self.assertAlmostEqual(
            line["capacity_per_year"],
            0.85 * sc.probes / r["per_system_years"])
        self.assertAlmostEqual(line["staffed_share"],
                               line["capacity_per_year"] / crossings)
        self.assertAlmostEqual(
            line["probes_to_staff_all"] * line["staffed_share"], sc.probes)
        # Far more systems cross than the fleet can survey.
        self.assertGreater(1 / line["staffed_share"], 10)
        self.assertAlmostEqual(line["rim_turn_years"] / 4.0e8, 1.0,
                               delta=0.01)
        # A uniform disc has no bulge: every system is on the line.
        flat = pp.derive(pp.Scenario(strategy="sweep-line",
                                     galaxy_model="uniform"))
        self.assertEqual(flat["reached"]["line"]["share_of_systems"], 1.0)
        self.assertAlmostEqual(
            flat["reached"]["line"]["crossings_per_year"],
            1e11 / (math.pi * radius ** 2) * radius * speed)

    def test_bigger_fleets_miss_fewer(self):
        missed = [pp.derive(pp.Scenario(strategy="sweep-line", probes=n))
                  ["reached"]["line"]["missed_per_sweep"]
                  for n in (300, 3_000, 30_000, 300_000, 3_000_000)]
        self.assertEqual(missed, sorted(missed, reverse=True))
        self.assertLess(missed[0], math.exp(-1))
        self.assertGreater(missed[0], 0.3)
        self.assertLess(missed[-1], 0.06)
        self.assertEqual(missed[-1], missed[-2])     # the whole line staffed

    def test_line_model_against_a_direct_simulation(self):
        for probes in (10_000, 40_000):
            sc = pp.Scenario(strategy="sweep-line", probes=probes)
            model = 1.0 - pp.derive(sc)["reached"]["line"]["missed_per_sweep"]
            seen, visits, years = simulate_line(sc)
            self.assertAlmostEqual(seen, model, delta=0.04, msg=probes)
            # One sweep makes one visit per system, whatever it reaches.
            self.assertAlmostEqual(visits, 1.0, delta=0.03, msg=probes)

    def test_moving_against_the_rotation_helps_only_a_fleet_that_waits(self):
        def pair(**inputs):
            sc = pp.Scenario(strategy="sweep-line", **inputs)
            # Backward at the rate the stars have at half the disc radius.
            backward = (pp.ROTATION_SPEED_M_S * pp.YEAR_S / pp.PARSEC_M
                        / (sc.disc_radius_kpc * 500.0))
            return (simulate_line(sc),
                    simulate_line(sc, against_rotation=backward))
        # While the work lasts longer than a turn of the disc, the sweep
        # takes as long either way. What it reaches moves by a few percent
        # of the systems: down at 0.05 of light speed, up at 0.1.
        for speed, change in ((0.05, -0.021), (0.1, 0.036)):
            still, moving = pair(speed_c=speed)
            self.assertAlmostEqual(moving[2] / still[2], 1.0, delta=0.05,
                                   msg=speed)
            self.assertAlmostEqual(moving[0] - still[0], change, delta=0.01,
                                   msg=speed)
            # The stars do arrive faster, but the same number must be
            # dealt with, so the work is the same.
            self.assertAlmostEqual(moving[1], still[1], delta=0.03)
        # A fleet that is held up by the turning disc finishes its sweep
        # three times sooner, and misses no more.
        still, moving = pair(speed_c=0.1, probes=40_000)
        self.assertAlmostEqual(still[2] / moving[2], 3.0, delta=0.1)
        self.assertGreater(moving[0], still[0])
        text = " ".join(pp.render_report(pp.derive(pp.Scenario(
            strategy="sweep-line"))).split())
        self.assertIn("it shortens the sweep only where the fleet would "
                      "otherwise be held up by the turning of the disc", text)
        self.assertNotIn("nothing is gained", text)

    def test_a_sweep_cannot_outrun_the_turning_disc(self):
        # A fleet that could finish its visits sooner still has to keep
        # every stretch staffed for one turn, and the rim takes longest.
        rim_turn = (2 * math.pi * 15 * pp.KPC_M / pp.ROTATION_SPEED_M_S
                    / pp.YEAR_S)
        self.assertAlmostEqual(rim_turn / 4.01e8, 1.0, delta=0.005)
        small = pp.derive(pp.Scenario(strategy="sweep-line"))
        self.assertEqual(small["phases"]["line_wait_years"], 0.0)
        self.assertNotIn("waiting for the disc to turn",
                         pp.render_report(small))
        big = pp.derive(pp.Scenario(strategy="sweep-line", probes=200_000))
        self.assertGreater(big["phases"]["line_wait_years"], 0.0)
        self.assertAlmostEqual(
            (big["total_years"] - big["phases"]["dispersal_years"])
            / rim_turn, 1.0, places=9)
        self.assertAlmostEqual(
            sum(big["phases"].values()) / big["total_years"], 1.0)
        self.assertIn("waiting for the disc to turn", pp.render_report(big))
        # The same fleet working by regions is not held up.
        regions = pp.derive(by_region(probes=200_000))
        self.assertLess(regions["total_years"], big["total_years"])
        self.assertEqual(regions["phases"]["line_wait_years"], 0.0)

    def test_sweeps_needed(self):
        r = pp.derive(pp.Scenario(strategy="sweep-line"))
        reached, line = r["reached"], r["reached"]["line"]
        self.assertEqual(reached["unit"], "sweep")
        self.assertEqual(r["milestones_count"], "line")
        changes = min(reached["region_changes_per_pass"])
        self.assertAlmostEqual(
            reached["seen_after_one_pass"],
            0.85 * (1 - line["missed_per_sweep"])
            + 0.15 * pp.share_seen(changes))
        self.assertAlmostEqual(reached["repeat_visit_share"],
                               1 - reached["seen_after_one_pass"])
        survey = r["total_years"] - r["phases"]["dispersal_years"]
        for row in reached["rows"]:
            seen = (0.85 * pp.line_seen(line["missed_per_sweep"],
                                        row["passes"])
                    + 0.15 * pp.share_seen(changes, row["passes"]))
            self.assertAlmostEqual(seen, row["systems_seen"], places=6)
            self.assertAlmostEqual(
                row["years"] / (r["phases"]["dispersal_years"]
                                + row["passes"] * survey), 1.0, places=6)
        # One sweep takes as long as one pass over the regions.
        self.assertEqual(r["total_years"],
                         pp.derive(by_region())["total_years"])

    # ---- side by side ---------------------------------------------------

    def test_every_report_compares_all_strategies(self):
        for name in pp.STRATEGIES:
            r = pp.derive(pp.Scenario(strategy=name))
            rows = r["strategies"]
            self.assertEqual([row["strategy"] for row in rows],
                             list(pp.STRATEGIES))
            for row in rows:
                own = pp.derive(pp.Scenario(strategy=row["strategy"]))
                self.assertAlmostEqual(
                    row["years_to_99_percent"],
                    own["reached"]["rows"][-1]["years"])
                self.assertAlmostEqual(row["one_pass_years"],
                                       own["total_years"])
            report = pp.render_report(r)
            self.assertIn("Ways to run the survey (--strategy)", report)
            marked = [line for line in report.splitlines()
                      if "(this run)" in line]
            self.assertEqual(len(marked), 1)
            self.assertTrue(marked[0].strip().startswith(name + " "))
            self.assertIn("Strategy:   %s - " % name, report)

    def test_ranking_for_the_default_fleet(self):
        rows = {row["strategy"]: row
                for row in pp.derive(pp.Scenario())["strategies"]}
        # 5.3, 3.9, 1.3 and 1.3 billion years: recording by system is
        # what counts, not where the probes wait.
        for name, expected in (("regions", 5.26e9), ("sweep-line", 3.93e9),
                               ("systems", 1.318e9),
                               ("systems-midplane", 1.318e9)):
            self.assertAlmostEqual(rows[name]["years_to_99_percent"]
                                   / expected, 1.0, delta=0.01, msg=name)
        self.assertAlmostEqual(rows["regions"]["seen_after_one_pass"], 0.632,
                               delta=0.001)
        self.assertAlmostEqual(rows["sweep-line"]["seen_after_one_pass"],
                               0.75, delta=0.01)

    def test_headline_says_what_it_covers(self):
        def block(name):
            lines = pp.render_report(
                pp.derive(pp.Scenario(strategy=name))).splitlines()
            at = next(i for i, line in enumerate(lines) if "HEADLINE" in line)
            return " ".join(x.strip() for x in lines[at:lines.index("", at)])
        self.assertIn("one pass over every region", block("regions"))
        self.assertIn("one sweep of the line", block("sweep-line"))
        self.assertIn("reaches about 75% of the systems", block("sweep-line"))
        for name in pp.RECORDS_BY_SYSTEM:
            self.assertNotIn("reaches about", block(name))
        report = pp.render_report(pp.derive(pp.Scenario(strategy="systems")))
        self.assertIn("Milestones (share of systems surveyed)", report)
        self.assertIn("Milestones (share of the line swept)", pp.render_report(
            pp.derive(pp.Scenario(strategy="sweep-line"))))

    def test_uncertainty_mode_runs_for_every_strategy(self):
        for name in pp.STRATEGIES:
            sc = pp.Scenario(strategy=name)
            u = pp.run_uncertainty(sc, pp.builtin_ranges(), draws=60)
            self.assertLess(u["percentiles_years"]["5"],
                            u["percentiles_years"]["95"])


class TestLeftOut(unittest.TestCase):
    """Audit C6 to C9: the caveats carry numbers for the scenario."""

    def test_share_leaving_a_cube(self):
        # Closed form against a direct average over directions.
        def direct(x, steps=300):
            stay = 0.0
            for i in range(steps):
                cos_t = (i + 0.5) / steps
                sin_t = math.sqrt(1 - cos_t * cos_t)
                for j in range(steps):
                    phi = (j + 0.5) / steps * math.pi / 2
                    stay += (max(0.0, 1 - x * sin_t * math.cos(phi))
                             * max(0.0, 1 - x * sin_t * math.sin(phi))
                             * max(0.0, 1 - x * cos_t))
            return 1 - stay / steps ** 2

        for x in (0.05, 0.143, 0.429, 0.9, 1.0):
            self.assertAlmostEqual(pp.share_leaving_cube(x), direct(x),
                                   places=4, msg=x)
        self.assertEqual(pp.share_leaving_cube(0.0), 0.0)
        self.assertAlmostEqual(pp.share_leaving_cube(1.0000001),
                               pp.share_leaving_cube(1.0), places=3)
        self.assertAlmostEqual(pp.share_leaving_cube(1.5), direct(1.5),
                               places=3)
        self.assertGreater(pp.share_leaving_cube(3.0), 0.999)
        # The audited region: 21.5 parsecs across, 150,500 years, stars
        # at 20 and 60 kilometers per second. The audit quotes 18 and 48
        # percent; a cube gives 20 and 53.
        self.assertAlmostEqual(pp.share_leaving_cube(3.08 / 21.54), 0.201,
                               delta=0.002)
        self.assertAlmostEqual(pp.share_leaving_cube(9.24 / 21.54), 0.532,
                               delta=0.002)

    def test_deep_time_figures_on_the_audited_inputs(self):
        out = pp.derive(pp.Scenario(**TestIdentities.AUDITED))["left_out"]
        # 3.04 billion years; one turn at 7.5 kiloparsecs and 230
        # kilometers per second takes 200 million years.
        self.assertAlmostEqual(out["turn_years"] / 2.003e8, 1.0, delta=0.002)
        self.assertAlmostEqual(out["turns_at_half_radius"], 15.2, delta=0.1)
        self.assertAlmostEqual(out["shear_years"] / 3.19e7, 1.0, delta=0.005)
        self.assertAlmostEqual(out["region_side_parsec"], 21.54, delta=0.01)
        low, high = out["drift_out_shares"]
        self.assertAlmostEqual(low, 0.201, delta=0.003)
        self.assertAlmostEqual(high, 0.532, delta=0.003)
        # 1.65 solar masses of new stars a year on 6.08e10: 8 percent
        # over 3.04 billion years.
        self.assertAlmostEqual(out["new_system_share"],
                               1.65 / 6.08e10 * 3.039e9, delta=0.0005)
        self.assertAlmostEqual(out["new_system_share"], 0.082, delta=0.001)
        self.assertEqual(out["central_load_factor"], 1.0)   # uniform disc

    def test_central_load_factor_of_the_exponential_disc(self):
        # Disc only: surface density at the center over the disc average,
        # xm^2 / (2 g(xm)); 17 for a scale length of 2.6 in a disc of 15.
        r = pp.derive(pp.Scenario(bulge_fraction=0.0))
        xm = 15.0 / 2.6
        expected = xm * xm / (2 * (1 - math.exp(-xm) * (1 + xm)))
        self.assertAlmostEqual(r["left_out"]["central_load_factor"],
                               expected)
        self.assertAlmostEqual(expected, 17.0, delta=0.05)
        with_bulge = pp.derive(pp.Scenario())["left_out"]
        self.assertGreater(with_bulge["central_load_factor"], expected)

    def test_scattering_stops(self):
        r = pp.derive(pp.Scenario())
        out = r["left_out"]
        self.assertAlmostEqual(out["scattering_stops"],
                               r["phases"]["dispersal_years"] / 1e4)
        self.assertAlmostEqual(out["scattering_stop_years"],
                               out["scattering_stops"] * 10.0)

    def test_caveats_name_each_effect_with_its_size(self):
        r = pp.derive(by_region())
        text = " ".join(pp.render_report(r).split())
        caveats = text[text.index("Caveats"):]
        for phrase in ["Balance.", "Duplication.", "Deep time.",
                       "Scattering.", "79% would be done",
                       "2.3 times as long",
                       "Regions are fixed volumes and the stars move "
                       "through them",
                       "A finished volume does not stay finished",
                       "In the Galactic Standard Frame, which turns with "
                       "one beacon",
                       "turns of the galaxy at half the disc radius"]:
            self.assertIn(phrase, caveats)
        self.assertIn("%s times as many systems per unit of disc area"
                      % pp.sig(r["left_out"]["central_load_factor"], 2),
                      caveats)
        self.assertNotIn("lists of targets", text)
        flat = " ".join(pp.render_report(
            pp.derive(by_region(galaxy_model="uniform"))).split())
        self.assertNotIn("per unit of disc area", flat)


class TestLossThreshold(unittest.TestCase):
    """Audit C5: the survey finishes only below a loss rate of about one
    over the survey time, and every report says so."""

    def test_threshold_solves_its_equation(self):
        for kwargs in [dict(), dict(speed_c=0.2), dict(systems=1e9),
                       dict(envelope_factor=300.0)]:
            r = pp.derive(pp.Scenario(**kwargs))
            scattering = r["phases"]["dispersal_years"]
            survey = r["total_years"] - scattering
            rate = r["attrition"]["threshold_per_year"]
            self.assertAlmostEqual(
                rate * math.exp(rate * scattering) * survey, 1.0, places=9,
                msg=kwargs)
            self.assertLessEqual(rate, 1.0 / survey)
            self.assertAlmostEqual(
                r["attrition"]["mean_life_needed_years"] * rate, 1.0)

    def test_survey_far_shorter_than_scattering_does_not_overflow(self):
        # Found by a sweep over random scenarios: with far more probes
        # than systems the survey lasts about a thousand years while
        # scattering lasts millions, and exp(rate x scattering)
        # overflowed once scattering / survey passed 709.
        r = pp.derive(pp.Scenario(probes=900_000_000, systems=2e6))
        scattering = r["phases"]["dispersal_years"]
        survey = r["total_years"] - scattering
        self.assertGreater(scattering / survey, 710)
        rate = r["attrition"]["threshold_per_year"]
        self.assertGreater(rate, 0.0)
        self.assertAlmostEqual(
            math.log(rate) + rate * scattering + math.log(survey), 0.0,
            places=6)
        self.assertIn("The survey can finish only if the loss rate",
                      " ".join(pp.render_report(r).split()))

    def test_threshold_separates_finishing_from_running_out(self):
        for kwargs in [dict(), dict(envelope_factor=300.0)]:
            rate = pp.derive(pp.Scenario(**kwargs))["attrition"][
                "threshold_per_year"]
            below = pp.derive(pp.Scenario(attrition_per_year=rate * 0.999,
                                          **kwargs))
            above = pp.derive(pp.Scenario(attrition_per_year=rate * 1.001,
                                          **kwargs))
            self.assertFalse(below["fleet_exhausted"], kwargs)
            self.assertTrue(above["fleet_exhausted"], kwargs)
            # The threshold does not depend on the losses assumed.
            self.assertAlmostEqual(
                below["attrition"]["threshold_per_year"] / rate, 1.0)

    def test_audited_figures(self):
        # 3.3e-10 per year, a mean life above 3 billion years; at 1e-9
        # the fleet finishes 33 percent.
        base = pp.derive(pp.Scenario(**TestIdentities.AUDITED))
        self.assertAlmostEqual(
            base["attrition"]["threshold_per_year"] / 3.29e-10, 1.0,
            delta=0.005)
        self.assertAlmostEqual(
            base["attrition"]["mean_life_needed_years"] / 3.04e9, 1.0,
            delta=0.005)
        lossy = pp.derive(pp.Scenario(attrition_per_year=1e-9,
                                      **TestIdentities.AUDITED))
        self.assertAlmostEqual(lossy["attrition"]["completed_fraction"],
                               0.329, delta=0.001)
        # Twice the threshold: about half the survey.
        twice = pp.derive(pp.Scenario(
            attrition_per_year=2 * base["attrition"]["threshold_per_year"],
            **TestIdentities.AUDITED))
        self.assertAlmostEqual(twice["attrition"]["completed_fraction"], 0.5,
                               delta=0.001)

    def test_fleet_left_at_the_end(self):
        r = pp.derive(pp.Scenario(attrition_per_year=2e-10))
        self.assertAlmostEqual(r["attrition"]["fleet_left_at_end"],
                               math.exp(-2e-10 * r["total_years"]))
        self.assertEqual(
            pp.derive(pp.Scenario())["attrition"]["fleet_left_at_end"], 1.0)
        self.assertEqual(pp.derive(pp.Scenario(attrition_per_year=1e-7))
                         ["attrition"]["fleet_left_at_end"], 0.0)

    def test_every_report_prints_the_threshold(self):
        for kwargs in [dict(), dict(archives="none"),
                       dict(attrition_per_year=1e-10),
                       dict(attrition_per_year=1e-8)]:
            r = pp.derive(pp.Scenario(**kwargs))
            text = " ".join(pp.render_report(r).split())
            self.assertIn("The survey can finish only if the loss rate "
                          "stays below %s per year"
                          % pp.sig(r["attrition"]["threshold_per_year"], 2),
                          text, kwargs)
            self.assertIn("Not modeled: records lost between deposits", text)
        self.assertIn("No probe is assumed to be lost", " ".join(
            pp.render_report(pp.derive(pp.Scenario())).split()))
        lossy = pp.derive(pp.Scenario(attrition_per_year=1e-8))
        self.assertIn(
            "the fleet runs out with %s of the survey done"
            % pp.percent(lossy["attrition"]["completed_fraction"]),
            " ".join(pp.render_report(lossy).split()))


class TestPropellant(unittest.TestCase):
    """Audit C4: every stop costs propellant that grows fast with speed."""

    def test_mass_ratio_per_stop(self):
        # exp(2 v / exhaust speed): 3.1 and 28 at 0.05 of light speed,
        # 90 and 6e5 at 0.2.
        for speed, exhaust, expected in [(0.05, 0.089, 3.08),
                                         (0.05, 0.03, 28.0),
                                         (0.2, 0.089, 89.5),
                                         (0.2, 0.03, 6.17e5)]:
            r = pp.derive(pp.Scenario(speed_c=speed, exhaust_speed_c=exhaust))
            ratio = r["propellant"]["mass_ratio_per_stop"]
            self.assertAlmostEqual(ratio, math.exp(2 * speed / exhaust))
            self.assertAlmostEqual(ratio / expected, 1.0, delta=0.005)

    def test_default_exhaust_speed_is_the_fusion_limit(self):
        # Deuterium plus helium-3 release 18.35 MeV from 5.030 atomic
        # mass units of 931.494 MeV each; all of it as exhaust motion
        # gives sqrt(2 x energy / mass) of light speed.
        limit = math.sqrt(2 * 18.35 / (5.030 * 931.494))
        self.assertAlmostEqual(pp.Scenario().exhaust_speed_c, limit,
                               delta=0.0006)
        self.assertEqual(pp.REFERENCE_EXHAUST[0][0],
                         pp.Scenario().exhaust_speed_c)

    def test_velocity_change_adds_up_over_the_survey(self):
        # The audited fleet: 2e7 systems per probe at 0.05 of light
        # speed is two million times light speed per probe.
        r = pp.derive(pp.Scenario(systems=2e11))
        p = r["propellant"]
        self.assertAlmostEqual(p["velocity_change_per_stop_c"], 0.1)
        self.assertAlmostEqual(p["velocity_change_per_probe_c"], 2e6)

    def test_stay_is_unchanged_unless_refuelling_is_switched_on(self):
        base = pp.derive(pp.Scenario())
        other = pp.derive(pp.Scenario(exhaust_speed_c=0.03))
        self.assertEqual(other["total_years"], base["total_years"])
        self.assertEqual(base["propellant"]["refuel_years_per_stop"], 0.0)
        self.assertEqual(base["propellant"]["stay_years_per_system"], 10.0)
        self.assertEqual([item["input"] for item in other["unused_inputs"]],
                         ["exhaust_speed_c"])
        self.assertEqual(base["unused_inputs"], [])
        used = pp.derive(pp.Scenario(exhaust_speed_c=0.03,
                                     refuel_years_per_mass=0.5))
        self.assertEqual(used["unused_inputs"], [])

    def test_refuelling_time_grows_with_the_mass_ratio(self):
        sc = by_region(refuel_years_per_mass=2.0)
        r = pp.derive(sc)
        ratio = r["propellant"]["mass_ratio_per_stop"]
        self.assertAlmostEqual(r["propellant"]["refuel_years_per_stop"],
                               2.0 * (ratio - 1.0))
        self.assertAlmostEqual(r["propellant"]["stay_years_per_system"],
                               10.0 + 2.0 * (ratio - 1.0))
        self.assertAlmostEqual(
            r["per_system_years"],
            r["hop_years"] + r["propellant"]["stay_years_per_system"])
        self.assertGreater(r["total_years"],
                           pp.derive(by_region())["total_years"])

    def test_faster_is_no_longer_a_free_win(self):
        # Without the mode, four times the speed is 3.2 times faster.
        plain = {v: pp.derive(by_region(speed_c=v))["total_years"]
                 for v in (0.05, 0.1, 0.2)}
        self.assertGreater(plain[0.05], plain[0.1])
        self.assertGreater(plain[0.1], plain[0.2])
        # With it, there is a best speed, and 0.2 is slower than 0.05.
        fueled = {v: pp.derive(by_region(
            speed_c=v, refuel_years_per_mass=1.0))["total_years"]
            for v in (0.05, 0.1, 0.2)}
        self.assertLess(fueled[0.1], fueled[0.05])
        self.assertGreater(fueled[0.2], fueled[0.05])

    def test_every_report_states_the_mass_ratio(self):
        for kwargs in [dict(), dict(speed_c=0.2), dict(archives="none"),
                       dict(refuel_years_per_mass=1.0)]:
            text = " ".join(pp.render_report(
                pp.derive(pp.Scenario(**kwargs))).split())
            self.assertIn("times its empty mass at an exhaust speed of "
                          "0.089 c", text, kwargs)
            self.assertIn("the class of the 1978 fusion-probe study", text)
        fast = " ".join(pp.render_report(
            pp.derive(pp.Scenario(speed_c=0.2))).split())
        self.assertIn("90 times its empty mass", fast)
        self.assertIn("a faster cruise is therefore optimistic", fast)
        self.assertNotIn("--refuel-\n", pp.render_report(
            pp.derive(pp.Scenario(speed_c=0.2))))

    def test_bad_propellant_inputs_rejected(self):
        for bad in [dict(exhaust_speed_c=0), dict(exhaust_speed_c=1.0),
                    dict(refuel_years_per_mass=-1)]:
            with self.assertRaises(ValueError, msg=bad):
                pp.derive(pp.Scenario(**bad))


class TestScattering(unittest.TestCase):
    """Audit B2, calculator side: the wait before the survey must hold
    for every starting point, so it cannot encode one."""

    def test_default_allowance_is_the_disc_diameter(self):
        for kwargs in [dict(), dict(disc_radius_kpc=20.0, speed_c=0.1)]:
            sc = pp.Scenario(**kwargs)
            r = pp.derive(sc)
            diameter_m = 2 * sc.disc_radius_kpc * pp.KPC_M
            self.assertAlmostEqual(
                r["phases"]["dispersal_years"]
                / (diameter_m / (sc.speed_c * pp.C_M_PER_S) / pp.YEAR_S),
                1.0, places=12)
            self.assertTrue(r["dispersal"]["covers_any_start"])
            self.assertEqual(r["distance"]["dispersal_m"], diameter_m)
        # 30 kiloparsecs at 0.05 of light speed: 1.96 million years.
        self.assertAlmostEqual(
            pp.derive(pp.Scenario())["phases"]["dispersal_years"] / 1.957e6,
            1.0, places=3)

    def test_it_covers_the_longest_leg_from_any_starting_radius(self):
        # From a start at radius r the farthest seed is at radius + r on
        # the far side. Sample starts across the disc, rim included.
        sc = pp.Scenario()
        allowance = pp.derive(sc)["dispersal"]["allowance_kpc"]
        for step in range(0, 101):
            start = sc.disc_radius_kpc * step / 100.0
            self.assertLessEqual(sc.disc_radius_kpc + start, allowance)
        # The old default (mean leg 10, margin 1.5) covered only a start
        # at the exact center.
        old = pp.derive(pp.Scenario(dispersal_leg_kpc=10.0,
                                    envelope_factor=1.5))
        self.assertAlmostEqual(old["dispersal"]["allowance_kpc"], 15.0)
        self.assertFalse(old["dispersal"]["covers_any_start"])
        self.assertIn("only holds if the starting point is known",
                      " ".join(pp.render_report(old).split()))
        self.assertNotIn("only holds if the starting point is known",
                         " ".join(pp.render_report(pp.derive(sc)).split()))

    def test_explicit_leg_and_margin_keep_working(self):
        r = pp.derive(pp.Scenario(dispersal_leg_kpc=10.0,
                                  envelope_factor=1.5))
        # The figure the audit reproduced: 978 thousand years.
        self.assertAlmostEqual(r["phases"]["dispersal_years"] / 9.785e5, 1.0,
                               places=3)
        wide = pp.derive(pp.Scenario(envelope_factor=2.0))
        self.assertAlmostEqual(
            wide["phases"]["dispersal_years"],
            2 * pp.derive(pp.Scenario())["phases"]["dispersal_years"])


class TestStaleness(unittest.TestCase):
    """Audit A5: every input either changes the result or is reported."""

    def test_delays_add_one_after_another(self):
        r = pp.derive(pp.Scenario())
        parts = r["staleness_parts_years"]
        self.assertAlmostEqual(sum(parts.values()), r["staleness_years"])
        self.assertAlmostEqual(parts["deposit_interval"],
                               r["region_cycle_years"])
        self.assertAlmostEqual(parts["consolidation_cycle"], 10_000.0)
        light_years = (r["layout"]["cache_spacing_kpc"] * pp.KPC_M
                       / pp.C_M_PER_S / pp.YEAR_S)
        self.assertAlmostEqual(parts["light_between_points"], light_years)

    def test_consolidation_cadence_matters_everywhere(self):
        # It used to change nothing between 100 and 150,000 years.
        cadences = [100.0, 1e3, 1e4, 1e5, 1.5e5, 1e6]
        runs = [pp.derive(pp.Scenario(consolidation_years=c))
                for c in cadences]
        for (c0, r0), (c1, r1) in zip(zip(cadences, runs),
                                      zip(cadences[1:], runs[1:])):
            self.assertAlmostEqual(
                r1["staleness_years"] - r0["staleness_years"], c1 - c0,
                places=3)
            self.assertGreater(r1["phases"]["duplicated_work_years"],
                               r0["phases"]["duplicated_work_years"])
            self.assertGreater(r1["total_years"], r0["total_years"])

    def test_cache_spacing_matters_in_station_layouts(self):
        # It used to be read only by the layout without stations.
        extra = 49.5 * pp.KPC_M / pp.C_M_PER_S / pp.YEAR_S
        for name in ("full-network", "stations-only", "sparse"):
            near = pp.derive(pp.Scenario(archives=name,
                                         cache_spacing_kpc=0.5))
            far = pp.derive(pp.Scenario(archives=name,
                                        cache_spacing_kpc=50.0))
            self.assertAlmostEqual(
                far["staleness_years"] - near["staleness_years"], extra,
                places=3, msg=name)
            self.assertGreater(far["total_years"], near["total_years"], name)

    def test_inputs_that_cannot_matter_are_reported(self):
        self.assertEqual(pp.derive(pp.Scenario())["unused_inputs"], [])
        r = pp.derive(pp.Scenario(archives="none", cache_spacing_kpc=5.0,
                                  consolidation_years=500.0,
                                  deposit_every=3, bitrate_bps=1.0))
        self.assertEqual(
            {item["input"] for item in r["unused_inputs"]},
            {"cache_spacing_kpc", "consolidation_years", "deposit_every",
             "bitrate_bps"})
        report = pp.render_report(r)
        self.assertIn("Inputs given but not used", report)
        for flag in ("--cache-spacing", "--consolidation-years",
                     "--deposit-every", "--bitrate"):
            self.assertIn(flag, report)
        r = pp.derive(pp.Scenario(archives="route-boxes-only",
                                  consolidation_years=500.0))
        self.assertEqual([item["input"] for item in r["unused_inputs"]],
                         ["consolidation_years"])
        self.assertNotIn("Inputs given but not used",
                         pp.render_report(pp.derive(pp.Scenario())))


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
    def setUp(self):
        self.help_text = pp.build_parser().format_help()

    def test_no_acronyms_or_jargon(self):
        self.assertEqual(banned_tokens(self.help_text), [])

    def test_denylist_itself_still_bites(self):
        self.assertEqual(banned_tokens("0.27 kpc, e.g. at T_c"),
                         ["kpc", "T_c", "e.g."])

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

    def test_scale_estimate_is_stated_at_the_headline(self):
        # Audit A8: the warning used to sit only under "Caveats", far
        # below a headline thirty times past its limit.
        code, out = self.run_main([])
        lines = out.splitlines()
        at = next(i for i, line in enumerate(lines) if "HEADLINE" in line)
        block = lines[at:lines.index("", at)]     # up to the blank line
        self.assertIn("scale estimate", " ".join(block))
        self.assertLess(at + len(block), lines.index("Phase breakdown"))
        self.assertTrue(pp.derive(pp.Scenario())["scale_estimate"])
        # A survey shorter than the limit carries no such label.
        short = pp.derive(pp.Scenario(systems=1e8))
        self.assertLess(short["total_years"], pp.SCALE_ESTIMATE_YEARS)
        self.assertFalse(short["scale_estimate"])
        self.assertNotIn("scale estimate only", pp.render_report(short))

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
