"""Checks of plan0_sim.py, each against something known beforehand."""

import contextlib
import io
import json
import math
import os
import tempfile
import unittest

import plan0_sim as ps
from test_plan0_pace import banned_tokens

NEVER = math.inf


def run(**settings):
    settings.setdefault("probes", 216)
    return ps.simulate(settings)


class TestOneRun(unittest.TestCase):
    def test_same_seed_same_result(self):
        first, again = run(rule="cells-roam"), run(rule="cells-roam")
        self.assertEqual(first["times"], again["times"])
        self.assertEqual(first["wasted_visits"], again["wasted_visits"])
        other = run(rule="cells-roam", seed=2)
        self.assertNotEqual(first["times"], other["times"])

    def test_every_system_is_surveyed_once_and_the_clocks_add_up(self):
        # A probe's clock is its travel plus its stays: nothing is lost
        # and nothing counted twice, whatever the rule and the knowledge.
        for settings in (
                dict(foresight=1.0), dict(), dict(announce=True),
                dict(foresight=0.9, records=20.0), dict(rule="cells"),
                dict(rule="cells-roam", foresight=1.0),
                dict(rule="cells-roam"),
                dict(rule="cells-roam", repeat_stay=True),
                dict(rule="cells-roam", seeding="lattice"),
                dict(rule="cells-roam", seeding="centres"),
                dict(rule="cells-roam", twins=0.3),
                dict(rule="cells-roam", absent=0.3),
                dict(rule="roam", per_probe=7.0)):
            r = run(probes=125, **settings)
            self.assertEqual(r["surveyed_share"], 1.0, settings)
            self.assertEqual(r["visits"], r["systems"], settings)
            self.assertLess(r["clock_error"], 1e-9, settings)
            self.assertEqual(r["times"]["1"], r["end"], settings)
            levels = [r["times"]["%g" % level] for level in ps.LEVELS]
            self.assertEqual(levels, sorted(levels), settings)
        # Without records the last systems are found by chance; these runs
        # stop at 99 percent.
        for settings in (dict(records=NEVER),
                         dict(foresight=0.9, records=NEVER),
                         dict(rule="cells-roam", records=NEVER)):
            r = run(probes=125, until=0.99, **settings)
            self.assertEqual(r["visits"], math.ceil(0.99 * r["systems"]))
            self.assertLess(r["clock_error"], 1e-9, settings)
            self.assertIsNone(r["times"]["1"])

    def test_one_probe_makes_a_nearest_first_tour(self):
        # A single probe among 4,000 systems that stand still: the tour
        # that always goes to the nearest unvisited system. Its first hops
        # are the distance to the nearest neighbor in a field with a hole,
        # about 0.6; the whole tour averages about 0.8 spacings a hop.
        r = ps.simulate(dict(probes=1, per_probe=4000.0, foresight=1.0))
        self.assertEqual(r["wasted_visits"], 0)
        self.assertAlmostEqual(r["mean_hop"], 0.80, delta=0.05)
        self.assertAlmostEqual(r["end"], 4000 * (r["mean_hop"] + 0.2),
                               places=6)

    def test_cells_are_as_uneven_as_the_geometry_says(self):
        # Cells around points scattered at random have volumes with a
        # variance of 0.179 of the squared mean (a classic result); the
        # number of systems inside adds 1 / mean. For 100 systems per
        # probe the spread is the root of 0.189, 43 percent.
        runs = [run(probes=343, rule="cells", seed=seed) for seed in (1, 2, 3)]
        spreads = [r["load"]["spread"] for r in runs]
        self.assertAlmostEqual(sum(spreads) / 3, math.sqrt(0.179 + 0.01),
                               delta=0.03)
        # On a lattice every cell has the same volume and only the count
        # varies: a spread of 10 percent.
        even = run(probes=216, rule="cells", seeding="lattice")
        self.assertAlmostEqual(even["load"]["spread"], 0.10, delta=0.02)
        # A probe that keeps to its cell wastes nothing and needs to know
        # nothing; the last system is done when the largest cell is.
        r = runs[0]
        self.assertEqual(r["wasted_visits"], 0)
        self.assertGreater(r["end"],
                           0.9 * r["load"]["most"] * (r["mean_hop"] + 0.2))

    def test_more_knowledge_wastes_fewer_visits(self):
        wasted = [run(**settings)["wasted_share"] for settings in (
            dict(foresight=1.0), dict(announce=True), dict(),
            dict(records=30.0), dict(records=NEVER, until=0.99))]
        self.assertEqual(wasted[0], 0.0)
        self.assertEqual(wasted, sorted(wasted))
        self.assertLess(wasted[1], 0.04)
        self.assertGreater(wasted[4], 0.6)

    def test_keeping_to_cells_first_tames_missing_knowledge(self):
        roam = run(records=NEVER, until=0.99)
        cells = run(rule="cells-roam", records=NEVER, until=0.99)
        self.assertLess(cells["times"]["0.99"], 0.6 * roam["times"]["0.99"])
        self.assertLess(cells["wasted_share"], roam["wasted_share"])

    def test_foresight_alone_cannot_see_a_lost_probe(self):
        # The others go on reckoning with the lost probes, so the systems
        # those would have taken are never surveyed.
        r = run(probes=343, rule="cells-roam", foresight=1.0, absent=0.2,
                absent_known=False)
        self.assertAlmostEqual(r["surveyed_share"], 0.8, delta=0.05)
        self.assertIsNone(r["times"]["1"])
        known = run(rule="cells-roam", foresight=1.0, absent=0.2)
        self.assertEqual(known["surveyed_share"], 1.0)
        # Records show the gap: with them the work of the lost is taken up.
        seen = run(rule="cells-roam", absent=0.2)
        self.assertEqual(seen["surveyed_share"], 1.0)

    def test_stopping_early(self):
        r = run(records=NEVER, until=0.9)
        self.assertAlmostEqual(r["surveyed_share"], 0.9, delta=0.001)
        self.assertIsNone(r["times"]["0.99"])
        self.assertIsNotNone(r["times"]["0.9"])

    def test_bad_settings_are_refused(self):
        for bad in (dict(rule="wander"), dict(seeding="heap"),
                    dict(foresight=1.5), dict(records=-1.0),
                    dict(probes=0), dict(speed=3),
                    dict(seeding="lattice", probes=100)):
            with self.assertRaises(ValueError):
                ps.simulate(bad)


class TestSets(unittest.TestCase):
    def test_every_run_of_every_set_is_well_formed(self):
        for name, low, high in (("full", 200, 260), ("limited", 100, 140),
                                ("even", 85, 100), ("trial", 4, 4)):
            jobs = ps.matrix(name)
            self.assertGreaterEqual(len(jobs), low, name)
            self.assertLessEqual(len(jobs), high, name)
            keys = set()
            for group, config in jobs:
                self.assertFalse(set(config) - set(ps.DEFAULTS), config)
                keys.add(json.dumps(config, sort_keys=True))
                self.assertGreater(ps.predicted_seconds(config), 0.0)
                if config.get("seeding") == "lattice":
                    side = round(config["probes"] ** (1 / 3))
                    self.assertEqual(side ** 3, config["probes"])
            self.assertEqual(len(keys), len(jobs), name)     # no run twice
        # The limited set asks the same questions as the full one.
        self.assertEqual({group for group, _ in ps.matrix("full")},
                         {group for group, _ in ps.matrix("limited")})
        # The set for evenly spread starts has every probe on a lattice,
        # and the full set is what it was when its results were stored.
        self.assertTrue(all(config["seeding"] == "lattice"
                            for _, config in ps.matrix("even")))
        self.assertEqual(len(ps.matrix("full")), 237)

    def test_labels(self):
        self.assertEqual(ps.label_of(dict(rule="cells")), "cells")
        self.assertEqual(ps.label_of(dict(foresight=1.0)), "roam/plan")
        self.assertEqual(ps.label_of(dict(records=NEVER)), "roam/none")
        self.assertEqual(
            ps.label_of(dict(rule="cells-roam", foresight=0.95, records=30.0,
                             absent=0.1, absent_known=False)),
            "cells-roam/plan0.95+records+late30 absent0.1 unseen")

    def test_a_set_runs_resumes_and_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            said = []
            path = ps.run_matrix("trial", folder, 2, 0.1, say=said.append)
            self.assertIn("4 runs to do, 0 already there", said[0])
            with open(path) as fh:
                rows = [json.loads(line) for line in fh]
            self.assertEqual(len(rows), 4)
            again = []
            ps.run_matrix("trial", folder, 2, 0.1, say=again.append)
            self.assertIn("0 runs to do, 4 already there", again[0])
            summary = ps.summarise(path)
            self.assertEqual(set(summary), {
                "roam/records probes216", "cells-roam/records probes216",
                "cells probes216", "cells-roam/none probes216"})
            cells = summary["cells probes216"]
            self.assertEqual(cells["wasted_share"], 0.0)
            # half of the systems come within half a share time; the
            # last one waits for the largest cell
            self.assertLess(cells["over_share_time"]["0.5"], 0.55)
            self.assertGreater(cells["over_share_time"]["1"], 1.5)
            text = ps.render_summary(summary)
            self.assertIn("cells-roam/none probes216", text)
            self.assertEqual(banned_tokens(text), [])
            # The same run alone gives the same numbers as inside the set.
            alone = ps.simulate(dict(probes=216, rule="cells", seed=1))
            self.assertEqual(alone["times"]["0.99"], cells["times"]["0.99"])


class TestTables(unittest.TestCase):
    def test_the_calculator_carries_what_the_stored_runs_give(self):
        # The two tables of plan0_pace.py are made from the stored runs
        # and from nothing else: one for starting points drawn at random,
        # one for probes spread evenly on a lattice.
        import plan0_pace as pp
        here = os.path.dirname(os.path.abspath(__file__))
        summary = ps.summarise(os.path.join(here, "plan0_sim_results",
                                            "results.jsonl"))
        self.assertEqual(ps.calibration(summary), pp.STILL_FIELD)
        self.assertEqual(ps.calibration(summary, "points"), pp.STILL_FIELD)
        self.assertEqual(ps.calibration(summary, "lattice"),
                         pp.STILL_FIELD_EVEN)
        # every run of the two sets behind them is stored
        stored = set()
        with open(os.path.join(here, "plan0_sim_results",
                               "results.jsonl")) as fh:
            for line in fh:
                stored.add(json.dumps(json.loads(line)["asked"],
                                      sort_keys=True))
        for name in ("full", "even"):
            for _, config in ps.matrix(name):
                self.assertIn(json.dumps(config, sort_keys=True), stored)


class TestManual(unittest.TestCase):
    def test_plain_words(self):
        text = ps.build_parser().format_help()
        self.assertEqual(banned_tokens(text), [])
        for action in ps.build_parser()._actions:
            for option in action.option_strings:
                self.assertIn(option, text)
        for name in list(ps.RULES) + list(ps.SEEDINGS):
            self.assertIn(name, text)

    def test_single_run_from_the_command_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ps.main(["--probes", "125", "--rule", "cells-roam",
                            "--records", "never", "--until", "0.99"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("cells-roam/none probes125", text)
        self.assertIn("not reached", text)
        self.assertEqual(banned_tokens(text), [])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = ps.main(["--probes", "100", "--start", "lattice"])
        self.assertEqual(code, 2)
        self.assertIn("cube number", err.getvalue())


if __name__ == "__main__":
    unittest.main()
