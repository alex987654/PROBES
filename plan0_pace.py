#!/usr/bin/env python3
"""Pace calculator for the PROBES CNL fleet's galaxy survey (PLAN-0).

Estimates how long ten thousand autonomous probes would need to survey
the star systems of this galaxy, given the communication and archive
architecture described in PROBES_CNL_Physical_Layer.md. Standard library
only; run `python plan0_pace.py --help` for the full plain-language manual.

This tool is a companion to the specification, not part of it. Spec
citations in the report output refer to sections of the Markdown
documents in this repository.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, fields
from typing import Optional

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

C_M_PER_S = 299_792_458.0            # speed of light
PARSEC_M = 3.0856775814913673e16     # IAU parsec
KPC_M = 1.0e3 * PARSEC_M             # kiloparsec
LIGHT_YEAR_M = 9.4607304725808e15    # IAU light-year
YEAR_S = 3.15576e7                   # Julian year in seconds

MILESTONE_FRACTIONS = (0.5, 0.9, 0.99, 1.0)

# ---------------------------------------------------------------------------
# Archive layout presets
#
# Each layout resolves to four model quantities:
#   cache_spacing_kpc  distance between archive points a probe can reach
#   detour_kpc         mean one-way off-route distance to the nearest point
#   consolidated       whether staffed stations merge records fleet-wide
#                      on the consolidation cycle (Physical Layer section 3.1)
#   deposit_every      probe deposits records after every Nth region
#
# Preset names use plain words so the --help output stays free of
# specification shorthand; the spec_note maps each back to the archive
# tiers of Physical Layer sections 3.1-3.2 for the report output.
# ---------------------------------------------------------------------------

ARCHIVE_PRESETS = {
    "full-network": dict(
        cache_spacing_kpc=0.27, detour_kpc=0.01, consolidated=True,
        deposit_every=1,
        help=("staffed archive stations in the calm zones between spiral "
              "arms, plus unattended deposit boxes along every survey "
              "route; records merge into shared archives on the regular "
              "consolidation cycle"),
        spec_note=("tiers L1 + L2, Physical Layer sections 3.1-3.2; node "
                   "spacing tracks the mean probe spacing s of ~0.27 "
                   "kiloparsecs"),
    ),
    "route-boxes-only": dict(
        cache_spacing_kpc=0.10, detour_kpc=0.005, consolidated=False,
        deposit_every=1,
        help=("unattended deposit boxes placed densely along survey routes "
              "with no staffed stations, so a record is readable only at "
              "the box where it was left and knowledge spreads slowly"),
        spec_note="tier L2 only, Physical Layer section 3.1",
    ),
    "stations-only": dict(
        cache_spacing_kpc=0.27, detour_kpc=0.5, consolidated=True,
        deposit_every=10,
        help=("staffed archive stations confined to the calm zones between "
              "spiral arms; probes must detour to reach them, so they "
              "deposit records less often"),
        spec_note="tier L1 only, sited per Physical Layer section 3.2",
    ),
    "sparse": dict(
        cache_spacing_kpc=5.0, detour_kpc=2.5, consolidated=True,
        deposit_every=50,
        help=("a handful of staffed archive stations across the whole "
              "galaxy; long detours and long information delays"),
        spec_note="degenerate tier L1 layout, far below doctrine density",
    ),
    "none": dict(
        cache_spacing_kpc=None, detour_kpc=0.0, consolidated=False,
        deposit_every=None,
        help=("no shared archives at all; probes never learn what others "
              "have finished, so duplicated work sits at the model's cap "
              "- included to show why the archive network exists"),
        spec_note="no CCH- nodes; violates fleet doctrine, shown for contrast",
    ),
}

# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------


@dataclass
class Scenario:
    """Every assumption the model uses. All fields overridable from the
    command line or a scenario file; defaults cite the specification or
    standard galactic-astronomy values."""

    probes: int = 10_000                 # Physical Layer section 1
    speed_c: float = 0.05                # fraction of light speed; section 1
    systems: float = 2.0e11              # Milky Way literature value
    stellar_density: float = 0.1         # systems per cubic parsec (local)
    disc_radius_kpc: float = 15.0        # survey disc radius; section 1
    disc_thickness_kpc: float = 0.6      # used when deriving systems count
    depth: float = 1.0                   # fraction of systems visited
    dwell_years: float = 10.0            # survey + refuel stay per system
    path_factor: float = 1.0             # route efficiency multiplier
    region_systems: float = 1000.0       # visited systems per record region
    dispersal_leg_kpc: float = 10.0      # PROC-DSP mean leg; section 4.5
    envelope_factor: float = 1.5         # activation-epoch margin on dispersal
    bitrate_bps: float = 0.5             # optical link; section 2.2 (0.1-1)
    message_bytes: float = 500.0         # wire-form message; Wire Format s.9
    archives: str = "full-network"
    cache_spacing_kpc: Optional[float] = None   # overrides preset
    detour_kpc: Optional[float] = None          # overrides preset
    station_count: Optional[int] = None         # derives spacing + detour
    consolidation_years: float = 10_000.0       # cadence T_c; section 1
    deposit_every: Optional[int] = None         # overrides preset
    attrition_per_year: float = 0.0             # fleet loss rate
    dup_cap: float = 0.5                 # ceiling on duplicated-work fraction
    dup_gain: float = 1.0                # tuning gain on duplication model
    neighbors: int = 6                   # planar node degree; section 4.3

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        valid = {f.name for f in fields(cls)}
        unknown = set(data) - valid
        if unknown:
            raise ValueError(
                "unknown scenario keys: %s (valid keys: %s)"
                % (", ".join(sorted(unknown)), ", ".join(sorted(valid))))
        return cls(**data)

    def validate(self) -> None:
        positive = ["probes", "speed_c", "systems", "stellar_density",
                    "disc_radius_kpc", "disc_thickness_kpc", "depth",
                    "path_factor", "region_systems", "envelope_factor",
                    "bitrate_bps", "message_bytes", "consolidation_years"]
        for name in positive:
            if getattr(self, name) <= 0:
                raise ValueError("%s must be positive" % name)
        if not 0 < self.depth <= 1:
            raise ValueError("depth must be in (0, 1]")
        if not 0 <= self.speed_c < 1:
            raise ValueError("speed_c must be below 1 (light speed)")
        if self.dwell_years < 0 or self.attrition_per_year < 0:
            raise ValueError("dwell_years and attrition_per_year must be >= 0")
        if self.archives not in ARCHIVE_PRESETS:
            raise ValueError("unknown archive layout %r (choices: %s)"
                             % (self.archives,
                                ", ".join(sorted(ARCHIVE_PRESETS))))


def resolve_layout(sc: Scenario) -> dict:
    """Merge the archive preset with any user overrides into the four
    quantities the model consumes."""
    preset = ARCHIVE_PRESETS[sc.archives]
    layout = dict(
        name=sc.archives,
        cache_spacing_kpc=preset["cache_spacing_kpc"],
        detour_kpc=preset["detour_kpc"],
        consolidated=preset["consolidated"],
        deposit_every=preset["deposit_every"],
        spec_note=preset["spec_note"],
        description=preset["help"],
    )
    if sc.station_count is not None:
        # Stations spread over the disc: spacing from equal-area cells,
        # mean detour of order half the spacing.
        area_kpc2 = math.pi * sc.disc_radius_kpc ** 2
        spacing = math.sqrt(area_kpc2 / sc.station_count)
        layout.update(cache_spacing_kpc=spacing, detour_kpc=spacing / 2.0,
                      consolidated=True,
                      deposit_every=layout["deposit_every"] or 1,
                      name="custom (%d stations)" % sc.station_count)
    if sc.cache_spacing_kpc is not None:
        layout["cache_spacing_kpc"] = sc.cache_spacing_kpc
    if sc.detour_kpc is not None:
        layout["detour_kpc"] = sc.detour_kpc
    if sc.deposit_every is not None and layout["deposit_every"] is not None:
        layout["deposit_every"] = sc.deposit_every
    return layout


# ---------------------------------------------------------------------------
# The analytic model
# ---------------------------------------------------------------------------


def derive(sc: Scenario) -> dict:
    """Compute the pace estimate. Pure function of the scenario; returns a
    dict holding every intermediate quantity (for --explain and --json)."""
    sc.validate()
    layout = resolve_layout(sc)

    v = sc.speed_c * C_M_PER_S

    # Inter-system hop: sampling at depth < 1 thins the visited set, so the
    # effective density of *visited* systems is stellar_density * depth.
    density_eff = sc.stellar_density * sc.depth
    hop_m = sc.path_factor * (1.0 / density_eff) ** (1.0 / 3.0) * PARSEC_M
    t_hop_s = hop_m / v
    dwell_s = sc.dwell_years * YEAR_S
    t_sys_s = t_hop_s + dwell_s

    visited_per_probe = sc.systems * sc.depth / sc.probes
    work_s = visited_per_probe * t_sys_s

    regions_per_probe = max(1.0, visited_per_probe / sc.region_systems)
    t_region_s = sc.region_systems * t_sys_s

    # Archive effects -------------------------------------------------------
    dep_every = layout["deposit_every"]
    deposits_per_probe = regions_per_probe / dep_every if dep_every else 0.0
    detour_m_per_probe = deposits_per_probe * 2.0 * layout["detour_kpc"] * KPC_M
    detour_s = detour_m_per_probe / v

    # Knowledge staleness: how old, at region-selection time, the completion
    # facts of neighboring probes are. Consolidated layouts refresh at each
    # deposit visit but never faster than the consolidation cycle; passive
    # layouts spread facts only through boxes both probes physically visit.
    # Beam propagation (~880 years per node spacing, section 1) is negligible
    # against these intervals and is folded into the refresh term.
    tc_s = sc.consolidation_years * YEAR_S
    if dep_every is None:
        tau_s = math.inf
    else:
        refresh_s = t_region_s * dep_every
        if layout["consolidated"]:
            tau_s = max(refresh_s, tc_s)
        else:
            spacing_s = (layout["cache_spacing_kpc"] or 0.0) * KPC_M / v
            tau_s = 2.0 * refresh_s + spacing_s

    # Duplicated-work fraction: each region selection risks colliding with
    # one of ~`neighbors` adjacent probes whose completions are up to tau
    # old; the risk per selection scales with how many region cycles of
    # staleness that represents, spread over the probe's own region budget.
    # A documented approximation (tunable via dup_gain), capped at dup_cap.
    if math.isinf(tau_s):
        f_dup = sc.dup_cap
    else:
        f_dup = min(sc.dup_cap,
                    sc.dup_gain * (tau_s / t_region_s)
                    * sc.neighbors / regions_per_probe)

    # Phases ----------------------------------------------------------------
    dispersal_s = sc.dispersal_leg_kpc * KPC_M / v * sc.envelope_factor
    duplication_s = work_s * f_dup
    survey_s = work_s + duplication_s + detour_s

    # Attrition: solve for the survey time in which the decaying fleet
    # accumulates the required probe-seconds of work.
    attrition = _apply_attrition(sc, dispersal_s, survey_s)
    survey_s_effective = attrition["survey_seconds"]
    total_s = dispersal_s + survey_s_effective

    milestones = []
    for frac in MILESTONE_FRACTIONS:
        t_frac = _survey_time_for_fraction(sc, dispersal_s, survey_s, frac)
        milestones.append(dict(
            fraction=frac,
            years=None if t_frac is None else (dispersal_s + t_frac) / YEAR_S))

    # Communication totals (coordination traffic only; bulk data rides along
    # as physical cargo at probe speed, Physical Layer section 2.3).
    if dep_every is None:
        messages_per_probe = 0.0
    else:
        messages_per_probe = regions_per_probe
    link_s_per_message = sc.message_bytes * 8.0 / sc.bitrate_bps
    link_s_per_probe = messages_per_probe * link_s_per_message
    fleet_messages = messages_per_probe * sc.probes

    # Distances -------------------------------------------------------------
    survey_path_m = visited_per_probe * hop_m * (1.0 + f_dup)
    dispersal_m = sc.dispersal_leg_kpc * KPC_M
    per_probe_m = dispersal_m + survey_path_m + detour_m_per_probe
    fleet_m = per_probe_m * sc.probes

    return dict(
        scenario=asdict(sc),
        layout=layout,
        speed_m_per_s=v,
        hop_parsec=hop_m / PARSEC_M,
        hop_years=t_hop_s / YEAR_S,
        per_system_years=t_sys_s / YEAR_S,
        visited_per_probe=visited_per_probe,
        regions_per_probe=regions_per_probe,
        region_cycle_years=t_region_s / YEAR_S,
        staleness_years=None if math.isinf(tau_s) else tau_s / YEAR_S,
        staleness_infinite=math.isinf(tau_s),
        duplication_fraction=f_dup,
        phases=dict(
            dispersal_years=dispersal_s / YEAR_S,
            survey_work_years=work_s / YEAR_S,
            duplicated_work_years=duplication_s / YEAR_S,
            archive_detours_years=detour_s / YEAR_S,
        ),
        attrition=attrition,
        total_years=total_s / YEAR_S,
        total_seconds=total_s,
        milestones=milestones,
        comms=dict(
            messages_per_probe=messages_per_probe,
            fleet_messages=fleet_messages,
            link_seconds_per_message=link_s_per_message,
            link_years_per_probe=link_s_per_probe / YEAR_S,
        ),
        distance=dict(
            dispersal_m=dispersal_m,
            survey_path_m=survey_path_m,
            detour_m=detour_m_per_probe,
            per_probe_m=per_probe_m,
            fleet_m=fleet_m,
        ),
    )


def _apply_attrition(sc: Scenario, dispersal_s: float,
                     survey_s: float) -> dict:
    """Stretch the survey phase for fleet attrition, or report the
    achievable fraction if the fleet dies out first."""
    if sc.attrition_per_year <= 0:
        return dict(active=False, survey_seconds=survey_s,
                    completed_fraction=1.0)
    lam = sc.attrition_per_year / YEAR_S
    needed_probe_s = sc.probes * survey_s
    fleet_at_start = sc.probes * math.exp(-lam * dispersal_s)
    if fleet_at_start <= 0.0:
        # The whole fleet is lost before dispersal completes.
        return dict(active=True, survey_seconds=math.inf,
                    completed_fraction=0.0)
    capacity_probe_s = fleet_at_start / lam       # integral to infinity
    if needed_probe_s >= capacity_probe_s:
        return dict(active=True, survey_seconds=math.inf,
                    completed_fraction=capacity_probe_s / needed_probe_s)
    t = -math.log(1.0 - needed_probe_s * lam / fleet_at_start) / lam
    return dict(active=True, survey_seconds=t, completed_fraction=1.0)


def _survey_time_for_fraction(sc: Scenario, dispersal_s: float,
                              survey_s: float, frac: float):
    """Survey-phase time to reach a completion fraction (None if
    unreachable under attrition)."""
    if sc.attrition_per_year <= 0:
        return frac * survey_s
    lam = sc.attrition_per_year / YEAR_S
    fleet_at_start = sc.probes * math.exp(-lam * dispersal_s)
    if fleet_at_start <= 0.0:
        return None
    needed = frac * sc.probes * survey_s * lam / fleet_at_start
    if needed >= 1.0:
        return None
    return -math.log(1.0 - needed) / lam


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

_SI_PREFIXES = [(1e24, "yotta"), (1e21, "zetta"), (1e18, "exa"),
                (1e15, "peta"), (1e12, "tera"), (1e9, "giga"),
                (1e6, "mega"), (1e3, "kilo"), (1.0, "")]


def si_quantity(value: float, unit: str) -> str:
    if value == 0:
        return "0 %ss" % unit
    if math.isinf(value):
        return "unbounded"
    for factor, prefix in _SI_PREFIXES:
        if value >= factor:
            return "%.3g %s%ss" % (value / factor, prefix, unit)
    return "%.3g %ss" % (value, unit)


def human_count(value: float) -> str:
    if math.isinf(value):
        return "unbounded"
    for factor, word in [(1e12, "trillion"), (1e9, "billion"),
                         (1e6, "million"), (1e3, "thousand")]:
        if abs(value) >= factor:
            return "%.3g %s" % (value / factor, word)
    return "%.3g" % value


def fmt_years(years: float, canonical: bool = False) -> str:
    if years is None:
        return "not reached"
    if math.isinf(years):
        return "never (fleet exhausted)"
    seconds = years * YEAR_S
    if canonical:
        return si_quantity(seconds, "second")
    return "%s years (%s)" % (human_count(years), si_quantity(seconds, "second"))


def fmt_meters(meters: float, canonical: bool = False) -> str:
    if canonical:
        return si_quantity(meters, "meter")
    ly = meters / LIGHT_YEAR_M
    return "%s light-years (%s)" % (human_count(ly), si_quantity(meters, "meter"))


def render_report(r: dict, canonical: bool = False) -> str:
    sc = r["scenario"]
    layout = r["layout"]
    ph = r["phases"]
    lines = []
    add = lines.append
    add("PLAN-0 GALAXY SURVEY PACE - analytic estimate")
    add("=" * 60)
    add("Fleet:      %s probes at %.3g c (%s per second)"
        % (format(sc["probes"], ","), sc["speed_c"],
           si_quantity(r["speed_m_per_s"], "meter")))
    add("Workload:   %s star systems, survey depth %.3g"
        % (human_count(sc["systems"]), sc["depth"]))
    add("            -> %s systems per probe, %.3g years per system"
        % (human_count(r["visited_per_probe"]), r["per_system_years"]))
    add("Archives:   %s - %s" % (layout["name"], layout["description"]))
    add("            (%s)" % layout["spec_note"])
    add("")
    add("HEADLINE:   full survey in %s" % fmt_years(r["total_years"], canonical))
    if r["attrition"]["completed_fraction"] < 1.0:
        add("            WARNING: attrition exhausts the fleet at %.1f%%"
            " completion" % (100 * r["attrition"]["completed_fraction"]))
    add("")
    add("Phase breakdown")
    add("-" * 60)
    total = r["total_years"]
    for label, key in [("dispersal (PROC-DSP, Physical Layer 4.5)",
                        "dispersal_years"),
                       ("survey travel + dwell", "survey_work_years"),
                       ("duplicated work (stale knowledge)",
                        "duplicated_work_years"),
                       ("archive deposit detours", "archive_detours_years")]:
        y = ph[key]
        share = ("%5.1f%%" % (100 * y / total)
                 if total and not math.isinf(total) else "     ")
        add("  %-42s %s  %s" % (label, share, fmt_years(y, canonical)))
    add("")
    add("Milestones (fraction of systems surveyed)")
    add("-" * 60)
    for m in r["milestones"]:
        add("  %4.0f%%   %s" % (100 * m["fraction"],
                                fmt_years(m["years"], canonical)))
    add("")
    add("Distance traveled")
    add("-" * 60)
    d = r["distance"]
    add("  per probe:   %s" % fmt_meters(d["per_probe_m"], canonical))
    add("  fleet total: %s" % fmt_meters(d["fleet_m"], canonical))
    add("")
    add("Coordination traffic (optical links, Physical Layer 2.2)")
    add("-" * 60)
    c = r["comms"]
    add("  wire messages per probe:  %s   fleet: %s"
        % (human_count(c["messages_per_probe"]),
           human_count(c["fleet_messages"])))
    add("  link time per message:    %.2g hours at %.2g bits per second"
        % (c["link_seconds_per_message"] / 3600, sc["bitrate_bps"]))
    add("  link time per probe:      %s  (negligible - the wire form is"
        % fmt_years(c["link_years_per_probe"], canonical))
    add("  the channel's admission ticket, Physical Layer 2.2)")
    add("")
    add("Knowledge staleness and duplication")
    add("-" * 60)
    if r["staleness_infinite"]:
        add("  no shared archives: staleness unbounded, duplication at cap")
    else:
        add("  completion facts stale by ~%s at selection time"
            % fmt_years(r["staleness_years"], canonical))
    add("  duplicated-work fraction: %.3g (cap %.2g)"
        % (r["duplication_fraction"], sc["dup_cap"]))
    add("")
    add("Doctrine constants echoed (Physical Layer section 1)")
    add("-" * 60)
    add("  probe spacing s ~ 0.27 kiloparsecs; light time per spacing ~880")
    add("  years; probe transit per spacing ~1.8e4 years; consolidation")
    add("  cadence T_c ~ %.3g years; relay hop limit h = 2; cold vaults"
        % sc["consolidation_years"])
    add("  (tier L3) affect synthesis latency only, never survey pace.")
    add("")
    add("Caveats")
    add("-" * 60)
    add("  Galactic rotation, stellar evolution, and density gradients are")
    add("  ignored; on timescales beyond ~1e8 years treat results as scale")
    add("  estimates. The duplication factor is a documented approximation")
    add("  (see --explain); the event-level dynamics are out of scope.")
    return "\n".join(lines)


def render_explain(r: dict) -> str:
    sc = r["scenario"]
    ph = r["phases"]
    lines = [
        "FORMULAS WITH SUBSTITUTED VALUES",
        "=" * 60,
        "cruise speed  v = %.3g x speed of light = %.4g meters per second"
        % (sc["speed_c"], r["speed_m_per_s"]),
        "",
        "inter-system hop = path_factor x (density x depth)^(-1/3)",
        "  = %.3g x (%.3g per cubic parsec x %.3g)^(-1/3)"
        % (sc["path_factor"], sc["stellar_density"], sc["depth"]),
        "  = %.4g parsecs  ->  %.4g years at cruise speed"
        % (r["hop_parsec"], r["hop_years"]),
        "",
        "time per system = hop time + dwell = %.4g + %.3g = %.4g years"
        % (r["hop_years"], sc["dwell_years"], r["per_system_years"]),
        "",
        "systems per probe = total x depth / probes",
        "  = %.3g x %.3g / %s = %.4g"
        % (sc["systems"], sc["depth"], format(sc["probes"], ","),
           r["visited_per_probe"]),
        "",
        "survey work = systems per probe x time per system = %.4g years"
        % ph["survey_work_years"],
        "",
        "region cycle = %.3g systems x %.4g years = %.4g years"
        % (sc["region_systems"], r["per_system_years"],
           r["region_cycle_years"]),
        "regions per probe = %.4g" % r["regions_per_probe"],
        "",
        "knowledge staleness tau = %s"
        % ("unbounded (no archives)" if r["staleness_infinite"]
           else "%.4g years" % r["staleness_years"]),
        "duplication fraction = min(cap, gain x (tau / region cycle)",
        "                           x neighbors / regions per probe)",
        "  = %.4g   (cap %.2g, gain %.2g, neighbors %d)"
        % (r["duplication_fraction"], sc["dup_cap"], sc["dup_gain"],
           sc["neighbors"]),
        "duplicated work = %.4g years" % ph["duplicated_work_years"],
        "",
        "dispersal = leg / v x envelope = %.3g kiloparsecs -> %.4g years"
        % (sc["dispersal_leg_kpc"], ph["dispersal_years"]),
        "archive detours = deposits x 2 x detour distance / v = %.4g years"
        % ph["archive_detours_years"],
        "",
        "TOTAL = dispersal + work x (1 + duplication) + detours",
        "      = %.4g years" % r["total_years"],
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

_DESCRIPTION = """\
Estimate how long a fleet of ten thousand autonomous space probes would
need to survey the star systems of our galaxy, following the fleet plan
and physical communication rules written in the Markdown documents of
this repository.

The estimate adds up four parts: (1) an initial scattering phase in
which every probe first travels to an assigned starting point, (2) the
survey itself - traveling star to star and pausing at each one, (3)
extra duplicated work done because probes only learn what others have
finished after a delay set by the archive layout, and (4) side trips to
archive sites to deposit and read records. Message transmission time is
also computed, and shown to be negligible.
"""

_EPILOG = """\
archive layouts (--archives NAME):
%s

what the output shows:
  A headline duration, a phase-by-phase breakdown, milestone times for
  half, ninety percent, ninety-nine percent, and full coverage, the
  distance traveled per probe and fleet-wide, message counts with their
  transmission time, and the assumptions the numbers rest on. Durations
  appear in years and also in seconds; distances in light-years and
  also in meters (one light-year is about 9.46e15 meters; one parsec
  is about 3.26 light-years; one kiloparsec is one thousand parsecs).

examples:
  python plan0_pace.py
      the default scenario: every star system, doctrine archive network
  python plan0_pace.py --archives stations-only --depth 0.1 --speed 0.1
      visit one system in ten, at double cruise speed, with staffed
      archive stations only
  python plan0_pace.py --explain
      print every formula with the numbers substituted in
  python plan0_pace.py --scenario my.json --json out.json
      load assumptions from a file, write full results to a file
"""


def build_parser() -> argparse.ArgumentParser:
    preset_lines = "\n".join(
        "  %-18s %s" % (name, preset["help"])
        for name, preset in ARCHIVE_PRESETS.items())
    p = argparse.ArgumentParser(
        prog="plan0_pace.py",
        description=_DESCRIPTION,
        epilog=_EPILOG % preset_lines,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    g = p.add_argument_group("fleet and survey assumptions")
    g.add_argument("--probes", type=int, metavar="COUNT",
                   help="number of probes in the fleet (default 10000)")
    g.add_argument("--speed", type=float, metavar="FRACTION", dest="speed_c",
                   help="cruise speed as a fraction of the speed of light "
                        "(default 0.05; studied concepts span 0.05 to 0.2)")
    g.add_argument("--systems", type=float, metavar="COUNT",
                   help="total star systems in the galaxy (default 2e11)")
    g.add_argument("--stellar-density", type=float, metavar="NUMBER",
                   dest="stellar_density",
                   help="star systems per cubic parsec, used for the "
                        "distance between neighboring stops (default 0.1); "
                        "if given without --systems, the system count is "
                        "derived from disc size times this density")
    g.add_argument("--disc-radius", type=float, metavar="KILOPARSECS",
                   dest="disc_radius_kpc",
                   help="survey disc radius (default 15)")
    g.add_argument("--disc-thickness", type=float, metavar="KILOPARSECS",
                   dest="disc_thickness_kpc",
                   help="effective disc thickness, used only when deriving "
                        "the system count from density (default 0.6)")
    g.add_argument("--depth", type=float, metavar="FRACTION",
                   help="fraction of star systems each probe actually "
                        "visits; 1.0 means every system (default 1.0)")
    g.add_argument("--dwell", type=float, metavar="YEARS",
                   dest="dwell_years",
                   help="stay per visited system, covering both the survey "
                        "and refueling, since survey stops double as "
                        "refueling stops (default 10)")
    g.add_argument("--path-factor", type=float, metavar="NUMBER",
                   dest="path_factor",
                   help="route efficiency multiplier on the hop between "
                        "neighboring systems (default 1.0)")
    g.add_argument("--region-systems", type=float, metavar="COUNT",
                   dest="region_systems",
                   help="visited systems per completion-record region; sets "
                        "how often a probe deposits records (default 1000)")
    g.add_argument("--dispersal-leg", type=float, metavar="KILOPARSECS",
                   dest="dispersal_leg_kpc",
                   help="mean initial scattering distance before any survey "
                        "or message begins (default 10)")
    g.add_argument("--envelope-factor", type=float, metavar="NUMBER",
                   dest="envelope_factor",
                   help="margin multiplier on the scattering phase so the "
                        "whole fleet has arrived before messages start "
                        "(default 1.5)")
    g.add_argument("--attrition", type=float, metavar="NUMBER",
                   dest="attrition_per_year",
                   help="fraction of the fleet lost per year to failures "
                        "(default 0)")

    g = p.add_argument_group("archives and communication")
    g.add_argument("--archives", choices=sorted(ARCHIVE_PRESETS),
                   metavar="NAME",
                   help="archive layout preset; see the list below "
                        "(default full-network)")
    g.add_argument("--cache-spacing", type=float, metavar="KILOPARSECS",
                   dest="cache_spacing_kpc",
                   help="override the distance between archive points")
    g.add_argument("--detour", type=float, metavar="KILOPARSECS",
                   dest="detour_kpc",
                   help="override the one-way side-trip distance to the "
                        "nearest archive point")
    g.add_argument("--station-count", type=int, metavar="COUNT",
                   dest="station_count",
                   help="place this many staffed archive stations evenly "
                        "over the disc, deriving spacing and side trips")
    g.add_argument("--consolidation-years", type=float, metavar="YEARS",
                   dest="consolidation_years",
                   help="how often staffed stations merge everyone's "
                        "records into shared archives (default 10000)")
    g.add_argument("--deposit-every", type=int, metavar="COUNT",
                   dest="deposit_every",
                   help="deposit records only after every Nth region")
    g.add_argument("--bitrate", type=float, metavar="NUMBER",
                   dest="bitrate_bps",
                   help="optical link speed in bits per second between a "
                        "probe and an archive point (default 0.5; the "
                        "specification derives 0.1 to 1)")
    g.add_argument("--message-bytes", type=float, metavar="COUNT",
                   dest="message_bytes",
                   help="size of one compact survey message (default 500)")

    g = p.add_argument_group("model tuning")
    g.add_argument("--dup-cap", type=float, metavar="FRACTION",
                   dest="dup_cap",
                   help="ceiling on the duplicated-work fraction "
                        "(default 0.5)")
    g.add_argument("--dup-gain", type=float, metavar="NUMBER",
                   dest="dup_gain",
                   help="tuning gain on the duplication model (default 1.0)")

    g = p.add_argument_group("input and output")
    g.add_argument("--scenario", metavar="FILE",
                   help="load assumptions from a file in JavaScript Object "
                        "Notation format; command-line flags override it")
    g.add_argument("--json", metavar="FILE", dest="json_out",
                   help="also write the full results, machine-readable, to "
                        "this file (JavaScript Object Notation format)")
    g.add_argument("--explain", action="store_true",
                   help="print every formula with the numbers substituted")
    g.add_argument("--canonical", action="store_true",
                   help="print durations only in seconds and distances only "
                        "in meters, the fleet's canonical units")
    g.add_argument("--list-presets", action="store_true",
                   help="list the archive layout presets and exit")
    return p


def scenario_from_args(args: argparse.Namespace) -> Scenario:
    data = {}
    if args.scenario:
        with open(args.scenario, "r", encoding="utf-8") as fh:
            data.update(json.load(fh))
    for f in fields(Scenario):
        value = getattr(args, f.name, None)
        if value is not None:
            data[f.name] = value
    # Derive the system count from geometry only when the user supplied a
    # density but no explicit count (in the file or on the command line).
    if "stellar_density" in data and "systems" not in data:
        sc_tmp = Scenario.from_dict(data)
        volume_pc3 = (math.pi * (sc_tmp.disc_radius_kpc * 1e3) ** 2
                      * sc_tmp.disc_thickness_kpc * 1e3)
        data["systems"] = sc_tmp.stellar_density * volume_pc3
    return Scenario.from_dict(data)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_presets:
        for name, preset in ARCHIVE_PRESETS.items():
            print("%-18s %s" % (name, preset["help"]))
        return 0
    try:
        sc = scenario_from_args(args)
        result = derive(sc)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if args.explain:
        print(render_explain(result))
    else:
        print(render_report(result, canonical=args.canonical))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, default=str)
        print("\nfull results written to %s" % args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
