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


def banned_tokens(text):
    """Every deny-listed token found in a piece of user-facing text."""
    found = [word for word in DENYLIST_WORDS
             if re.search(r"\b%s\b" % re.escape(word), text)]
    found += [sub for sub in DENYLIST_SUBSTRINGS if sub in text]
    return found


class TestConstants(unittest.TestCase):
    def test_kiloparsec_is_thousand_parsecs(self):
        self.assertAlmostEqual(pp.KPC_M / pp.PARSEC_M, 1000.0)

    def test_parsec_in_light_years(self):
        self.assertAlmostEqual(pp.PARSEC_M / pp.LIGHT_YEAR_M, 3.2616, places=3)

    def test_year_seconds(self):
        self.assertAlmostEqual(pp.YEAR_S, 3.15576e7)


class TestModel(unittest.TestCase):
    def test_default_headline_in_sane_range(self):
        # A coarse tripwire only; the identities are pinned elsewhere.
        # The band moves whenever a default moves, on purpose. It is now
        # centered on 1.4 billion years: 1e11 systems in an exponential
        # disc with a bulge, at one mean spacing per hop.
        r = pp.derive(pp.Scenario())
        self.assertGreater(r["total_years"], 1.1e9)
        self.assertLess(r["total_years"], 1.8e9)

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
        sc = pp.Scenario(stellar_density=0.1, disc_radius_kpc=15.0,
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
        gal = pp.derive(pp.Scenario())["galaxy"]
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
        sc = pp.Scenario()
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

    def test_hop_identities(self):
        sc = pp.Scenario(path_factor=0.9)
        r = pp.derive(sc)
        self.assertAlmostEqual(
            r["hop_parsec"], 0.9 * r["galaxy"]["mean_spacing_pc"])
        self.assertAlmostEqual(
            r["hop_years"],
            r["hop_parsec"] * pp.PARSEC_M / pp.LIGHT_YEAR_M / sc.speed_c)
        # Visiting one system in eight doubles every hop.
        thin = pp.derive(pp.Scenario(path_factor=0.9, depth=0.125))
        self.assertAlmostEqual(thin["hop_parsec"], 2.0 * r["hop_parsec"])
        for pct in ("5", "50", "95"):
            self.assertAlmostEqual(thin["hop_percentiles_parsec"][pct],
                                   2.0 * r["hop_percentiles_parsec"][pct])
        # A uniform disc has one spacing: density^(-1/3).
        flat = pp.derive(pp.Scenario(stellar_density=0.08, path_factor=1.0))
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

    def test_no_acronyms_or_jargon(self):
        for label, text in self.texts():
            self.assertEqual(banned_tokens(text), [], label)


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
        self.assertIn("scale estimate", lines[at + 1])
        self.assertLess(at + 1, lines.index("Phase breakdown"))
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
