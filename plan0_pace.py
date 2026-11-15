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
import random
import sys
import textwrap
from dataclasses import asdict, dataclass, fields, replace
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

# Star systems in the galaxy: the one authoritative workload input. It
# follows from galaxy-wide measurements only: about 5e10 to 6e10 solar
# masses of stars (Licquia and Newman 2015; Bland-Hawthorn and Gerhard
# 2016) at about 0.54 solar masses per system (0.043 solar masses per cubic
# parsec of stars, McKee and others 2015, over 0.080 systems per cubic
# parsec in the 10-parsec census, Reyle and others 2021). A 2025 estimate
# of 2.6e10 solar masses (Lian and others) would halve it.
DEFAULT_SYSTEMS = 1.0e11

GALAXY_MODELS = ("exponential", "uniform")

# Ways to run the survey. "regions" is the specification as it stands; the
# others change how the fleet moves or what it records. The plan, and the
# default, is "systems-midplane".
STRATEGIES = {
    "regions": ("as the specification stands: the fleet spreads over the "
                "disc and each probe surveys one region after another; "
                "completion is recorded by region"),
    "sweep-line": ("the fleet works along a line held from the galactic "
                   "center to the rim while the disc turns past it; a "
                   "system is surveyed when it crosses the line"),
    "systems": ("as regions, but completion is recorded by system, so a "
                "system surveyed anywhere is recognized and never visited "
                "twice; a probe goes to the nearest system not yet "
                "surveyed"),
    "systems-midplane": ("as systems, with the probes waiting in a thin "
                         "layer at the mid-plane of the disc, where "
                         "systems are closest together, and taking each "
                         "system as it passes through"),
}
RECORDS_BY_SYSTEM = ("systems", "systems-midplane")

# Hops where completion is recorded by system. Simulated (stars drifting at
# random through a volume that wraps around, up to 300,000 systems): a
# probe that always goes to the nearest system not yet surveyed makes hops
# of 0.65 times the spacing of the systems still to do, at every stage of
# the survey, because the drift evens out whatever it leaves behind. A
# route that has to clear a field of fixed points starts the same way and
# averages 0.78 only because its last points lie in scattered leftovers.
# The path factor, which describes such a route, is scaled by the ratio.
OPEN_FIELD_HOP = 0.65
CLEARED_FIELD_HOP = 0.78

# Both hold only where the stars mix during the survey. The measure is how
# often a star crosses one probe's share of the galaxy while the survey
# lasts; the share of the mixed law in the result is 1 - exp(-crossings).
# In the simulations 0.8, 1.7 and 3.4 crossings gave 0.75, 0.87 and 0.97
# of the way from a field of fixed points to full mixing.
#
# Waiting at the mid-plane needs more: the stars have to swing through it
# many times. A star of typical swing takes about 7 scale heights over its
# random speed to go up, down and back. In the simulations the law for the
# mid-plane held for surveys of 4 swings or more; with 2 swings the 99
# percent mark came 9 percent later, with 1 swing 28 percent later, and
# the probes began to stand idle. Below 4 swings the probes are taken to
# go to the systems instead of waiting for them.
PLANE_SWING_IN_HEIGHTS = 7.0
PLANE_SWINGS_NEEDED = 4.0

# Beyond this duration the galaxy itself rotates, shears and forms stars
# on the timescale of the survey, none of which the model follows; any
# longer result is a scale estimate and is labeled so at the headline.
SCALE_ESTIMATE_YEARS = 1.0e8

# Distance at which the link budget of Physical Layer section 2.2 holds;
# the bit rate given for the link refers to it.
LINK_REFERENCE_M = 8.0e18

# Figures used only to put numbers on what the model leaves out.
ROTATION_SPEED_M_S = 2.3e5              # orbital speed, similar at all radii
RANDOM_SPEEDS_M_S = (2.0e4, 6.0e4)      # stars relative to their neighbors
# Random speed of disc stars toward and away from the center. It makes
# every star swing in and out around its mean distance, by about a tenth
# of that distance.
RADIAL_RANDOM_SPEED_M_S = 3.5e4
# New stars per year as a share of the stars that exist: 1.65 solar masses
# per year on 6.08e10 (Licquia and Newman 2015). A share, so that it holds
# for any system count.
STAR_FORMATION_SHARE_PER_YEAR = 2.71e-11
STORED_ENERGY_LEG_YEARS = 1.0e4         # cruise leg named in section 6.1
# Simulated: 10,000 seeds scattered at random through a uniform disc, each
# probe keeping to the systems nearest its seed, no work handed over.
UNBALANCED_DONE_AT_NOMINAL_TIME = 0.79
UNBALANCED_TIME_FOR_99_PERCENT = 2.3

# Exhaust speeds (fractions of light speed) quoted in every report.
REFERENCE_EXHAUST = (
    (0.089, "the ideal limit for fusion of deuterium and helium-3"),
    (0.03, "the class of the 1978 fusion-probe study"),
)

# ---------------------------------------------------------------------------
# Archive layout presets
#
# Each layout resolves to four model quantities:
#   cache_spacing_kpc  distance between archive points a probe can reach;
#                      None means "the mean probe spacing of this fleet",
#                      which is what the doctrine asks for (Physical Layer
#                      section 3.2, criterion 6)
#   detour_kpc         mean one-way off-route distance to the nearest point
#   consolidated       whether staffed stations merge records fleet-wide
#                      on the consolidation cycle (Physical Layer section 3.1)
#   deposit_every      probe deposits records after every Nth region
#
# Preset names and notes use plain words so the --help and report output
# stay free of specification shorthand; the spec_note maps each layout
# back to the archive tiers of Physical Layer sections 3.1-3.2.
# ---------------------------------------------------------------------------

ARCHIVE_PRESETS = {
    "full-network": dict(
        cache_spacing_kpc=None, detour_kpc=0.01, consolidated=True,
        deposit_every=1,
        help=("staffed archive stations in the calm zones between spiral "
              "arms, plus unattended deposit boxes along every survey "
              "route; records merge into shared archives on the regular "
              "consolidation cycle"),
        spec_note=("custodial archive nodes plus passive caches, the first "
                   "and second tiers of Physical Layer sections 3.1-3.2; "
                   "node spacing follows the mean probe spacing"),
    ),
    "route-boxes-only": dict(
        cache_spacing_kpc=0.10, detour_kpc=0.005, consolidated=False,
        deposit_every=1,
        help=("unattended deposit boxes placed densely along survey routes "
              "with no staffed stations, so a record is readable only at "
              "the box where it was left and knowledge spreads slowly"),
        spec_note=("passive caches only, the second tier of Physical Layer "
                   "section 3.1"),
    ),
    "stations-only": dict(
        cache_spacing_kpc=None, detour_kpc=0.5, consolidated=True,
        deposit_every=10,
        help=("staffed archive stations confined to the calm zones between "
              "spiral arms; probes must detour to reach them, so they "
              "deposit records less often"),
        spec_note=("custodial archive nodes only, the first tier, sited per "
                   "Physical Layer section 3.2; node spacing follows the "
                   "mean probe spacing"),
    ),
    "sparse": dict(
        cache_spacing_kpc=5.0, detour_kpc=2.5, consolidated=True,
        deposit_every=50,
        help=("a handful of staffed archive stations across the whole "
              "galaxy; long detours and long information delays"),
        spec_note=("a thinned-out first tier, far below the density the "
                   "doctrine asks for"),
    ),
    "none": dict(
        cache_spacing_kpc=None, detour_kpc=0.0, consolidated=False,
        deposit_every=None,
        help=("no shared archives at all; probes never learn what others "
              "have finished, so duplicated work sits at the model's cap "
              "- included to show why the archive network exists"),
        spec_note=("no cache nodes at all; against fleet doctrine, shown "
                   "for contrast"),
    ),
}

# Relay hop limit fixed by the specification (Physical Layer section 4.3).
SPEC_HOP_LIMIT = 2

# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------

# Allowed range of every numeric input:
#   name: (lowest value, lowest allowed itself?, highest value or None,
#          highest allowed itself?)
_NUMBER_RULES = {
    "probes": (1, True, None, False),
    "speed_c": (0, False, 1, False),
    "systems": (0, False, None, False),
    "stellar_density": (0, False, None, False),
    "disc_radius_kpc": (0, False, None, False),
    "disc_thickness_kpc": (0, False, None, False),
    "scale_length_kpc": (0, False, None, False),
    "bulge_fraction": (0, True, 1, False),
    "bulge_radius_kpc": (0, False, None, False),
    "depth": (0, False, 1, True),
    "dwell_years": (0, True, None, False),
    "path_factor": (0, False, None, False),
    "acceleration_m_s2": (0, False, None, False),
    "exhaust_speed_c": (0, False, 1, False),
    "refuel_years_per_mass": (0, True, None, False),
    "region_systems": (0, False, None, False),
    "dispersal_leg_kpc": (0, True, None, False),
    "envelope_factor": (0, False, None, False),
    "bitrate_bps": (0, False, None, False),
    "message_bytes": (0, False, None, False),
    "cache_spacing_kpc": (0, False, None, False),
    "detour_kpc": (0, True, None, False),
    "station_count": (1, True, None, False),
    "consolidation_years": (0, False, None, False),
    "deposit_every": (1, True, None, False),
    "attrition_per_year": (0, True, None, False),
    "dup_cap": (0, True, None, False),
    "dup_gain": (0, True, None, False),
    "neighbors": (0, True, None, False),
}
_WHOLE_NUMBER_FIELDS = ("probes", "station_count", "deposit_every",
                        "neighbors")
# Inputs that may be left unset (the layout preset or the model fills in).
_OPTIONAL_FIELDS = ("systems", "stellar_density", "acceleration_m_s2",
                    "dispersal_leg_kpc",
                    "cache_spacing_kpc", "detour_kpc", "station_count",
                    "deposit_every")


@dataclass
class Scenario:
    """Every assumption the model uses. All fields overridable from the
    command line or a scenario file; defaults cite the specification or
    standard galactic-astronomy values."""

    probes: int = 10_000                 # Physical Layer section 1
    # Fraction of light speed. The plan asks for at least 0.1; Physical
    # Layer section 1 names 0.05 as nominal.
    speed_c: float = 0.1
    # Workload. The system count is authoritative; densities and the
    # distances between systems follow from it through the galaxy model.
    # None means DEFAULT_SYSTEMS (or density x volume if a density is given).
    systems: Optional[float] = None
    # A single density, systems per cubic parsec. Giving one replaces the
    # galaxy model by a uniform disc; there is deliberately no default.
    stellar_density: Optional[float] = None
    galaxy_model: str = "exponential"    # or "uniform"
    disc_radius_kpc: float = 15.0        # survey disc radius; section 1
    # Effective thickness: surface density over mid-plane density, twice
    # the vertical scale height. Thin plus thick disc give 0.65 to 0.73
    # (Bland-Hawthorn and Gerhard 2016); the measured ratio of stellar
    # surface to volume density is 0.78 (McKee and others 2015).
    disc_thickness_kpc: float = 0.7
    scale_length_kpc: float = 2.6        # radial scale length of the disc
    bulge_fraction: float = 0.15         # share of systems in the bulge
    bulge_radius_kpc: float = 1.0        # sphere holding half the bulge
    depth: float = 1.0                   # fraction of systems visited
    dwell_years: float = 10.0            # survey + refuel stay per system
    # Route length per hop in units of the mean spacing between systems.
    # 0.78: always going to the nearest unvisited system, in an open field
    # of random points (simulated; 0.83 when confined to one region of
    # 1000 systems). 0.70: the shortest route through random points
    # (Cerf and others 1997). 1.0: one mean spacing per hop, the old
    # default, an upper bound for any sensible route.
    path_factor: float = 0.78
    # Acceleration and braking, meters per second squared. None treats
    # stops and starts as instant, the limit of strong engines.
    acceleration_m_s2: Optional[float] = None
    # Propellant. Every stop costs a velocity change of twice the cruise
    # speed, so a probe leaves each system carrying exp(2 v / exhaust
    # speed) times its empty mass. 0.089 is the ideal limit for fusion of
    # deuterium and helium-3 (18.35 MeV from 5.03 atomic mass units).
    exhaust_speed_c: float = 0.089
    # Years to gather propellant equal to the empty mass. 0 leaves the
    # stay per system at dwell_years whatever the speed.
    refuel_years_per_mass: float = 0.0
    region_systems: float = 1000.0       # visited systems per record region
    # Scattering before the survey (Physical Layer section 4.5). No probe
    # may start before the last one can have arrived, or the start times
    # would point back to where the fleet set out. The only allowance that
    # holds for every starting point is the disc diameter, so that is the
    # default (None). A shorter leg presumes knowledge of the start.
    dispersal_leg_kpc: Optional[float] = None
    envelope_factor: float = 1.0         # extra margin on that allowance
    bitrate_bps: float = 0.5             # optical link; section 2.2 (0.1-1)
    message_bytes: float = 500.0         # wire-form message; Wire Format s.9
    archives: str = "full-network"
    strategy: str = "systems-midplane"   # see STRATEGIES
    cache_spacing_kpc: Optional[float] = None   # overrides preset
    detour_kpc: Optional[float] = None          # overrides preset
    station_count: Optional[int] = None         # derives spacing + detour
    consolidation_years: float = 10_000.0       # cadence T_c; section 1
    deposit_every: Optional[int] = None         # overrides preset
    attrition_per_year: float = 0.0             # fleet loss rate
    dup_cap: float = 0.5                 # ceiling on duplicated-work fraction
    dup_gain: float = 1.0                # tuning gain on duplication model
    neighbors: int = 6                   # planar node degree; section 4.3

    def __post_init__(self) -> None:
        # A scenario file may spell a whole number as 10000.0; accept that.
        for name in _WHOLE_NUMBER_FIELDS:
            value = getattr(self, name)
            if isinstance(value, float) and value.is_integer():
                setattr(self, name, int(value))

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        if not isinstance(data, dict):
            raise ValueError("a scenario must be one object of named values")
        valid = {f.name for f in fields(cls)}
        unknown = set(data) - valid
        if unknown:
            raise ValueError(
                "unknown scenario keys: %s (valid keys: %s)"
                % (", ".join(sorted(unknown)), ", ".join(sorted(valid))))
        return cls(**data)

    def validate(self) -> None:
        """Reject any value the model cannot use, naming the input."""
        for name, (low, low_ok, high, high_ok) in _NUMBER_RULES.items():
            value = getattr(self, name)
            if value is None:
                if name in _OPTIONAL_FIELDS:
                    continue
                raise ValueError("%s needs a value" % name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("%s must be a number (got %r)"
                                 % (name, value))
            if not math.isfinite(value):
                raise ValueError("%s must be a finite number (got %r)"
                                 % (name, value))
            if name in _WHOLE_NUMBER_FIELDS and not isinstance(value, int):
                raise ValueError("%s must be a whole number (got %r)"
                                 % (name, value))
            if value < low or (value == low and not low_ok):
                raise ValueError(
                    "%s must be %s %g (got %r)"
                    % (name, "at least" if low_ok else "greater than",
                       low, value))
            if high is not None and (value > high
                                     or (value == high and not high_ok)):
                raise ValueError(
                    "%s must be %s %g%s (got %r)"
                    % (name, "at most" if high_ok else "below", high,
                       " (light speed)" if name == "speed_c" else "", value))
        if self.galaxy_model not in GALAXY_MODELS:
            raise ValueError("unknown galaxy model %r (choices: %s)"
                             % (self.galaxy_model, ", ".join(GALAXY_MODELS)))
        if (not isinstance(self.strategy, str)
                or self.strategy not in STRATEGIES):
            raise ValueError("unknown strategy %r (choices: %s)"
                             % (self.strategy, ", ".join(STRATEGIES)))
        if (not isinstance(self.archives, str)
                or self.archives not in ARCHIVE_PRESETS):
            raise ValueError("unknown archive layout %r (choices: %s)"
                             % (self.archives,
                                ", ".join(sorted(ARCHIVE_PRESETS))))


def fleet_geometry(sc: Scenario) -> dict:
    """Spacing and timing of the fleet, computed from the scenario
    (the quantities of the regime table, Physical Layer section 1)."""
    area_kpc2 = math.pi * sc.disc_radius_kpc ** 2 / sc.probes
    spacing_kpc = math.sqrt(area_kpc2)          # one probe per square cell
    # Same area per probe on a lattice where each probe has six neighbors.
    lattice_kpc = math.sqrt(2.0 * area_kpc2 / math.sqrt(3.0))
    light_years = spacing_kpc * KPC_M / C_M_PER_S / YEAR_S
    transit_years = light_years / sc.speed_c
    # Relay reach (Physical Layer section 4.2): a relayed fact is worth
    # having only where a probe could act on it before the archives
    # deliver it, one to two consolidation cycles later. In that time a
    # probe covers this many probe spacings.
    reach_low = sc.consolidation_years / transit_years
    reach_high = 2.0 * reach_low
    return dict(
        area_per_probe_kpc2=area_kpc2,
        spacing_kpc=spacing_kpc,
        lattice_spacing_kpc=lattice_kpc,
        light_years_per_spacing=light_years,
        transit_years_per_spacing=transit_years,
        crossing_light_years=(2.0 * sc.disc_radius_kpc * KPC_M
                              / C_M_PER_S / YEAR_S),
        cadence_in_transits=reach_low,
        relay_reach_spacings=[reach_low, reach_high],
        useful_relay_hops=[max(1, math.ceil(reach_low)),
                           max(1, math.ceil(reach_high))],
        spec_hop_limit=SPEC_HOP_LIMIT,
    )


def resolve_layout(sc: Scenario) -> dict:
    """Merge the archive preset with any user overrides into the four
    quantities the model consumes."""
    preset = ARCHIVE_PRESETS[sc.archives]
    spacing_kpc = preset["cache_spacing_kpc"]
    if spacing_kpc is None and preset["deposit_every"] is not None:
        spacing_kpc = fleet_geometry(sc)["spacing_kpc"]
    layout = dict(
        name=sc.archives,
        cache_spacing_kpc=spacing_kpc,
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
# Defaults, where they come from, and how far they can plausibly be off
# ---------------------------------------------------------------------------
#
# One row per scenario input:
#   (name, low, high, scale, varied, source)
# low/high  plausible range, or None where the value is a choice of the
#           plan rather than something uncertain
# scale     "log" draws evenly in the logarithm (ranges spanning factors),
#           "linear" draws evenly in the value
# varied    True for the inputs that --uncertainty varies by default: the
#           uncertain ones that move the survey time
# The ranges are illustrative judgments from the sources named, not
# measured error bars.

INPUT_TABLE = [
    ("probes", None, None, None, False,
     "the plan (Physical Layer section 1)"),
    ("speed_c", 0.1, 0.2, "log", True,
     "the plan: at least 0.1 of light speed, up to the fastest of the "
     "studied probe concepts (Physical Layer section 5). Physical Layer "
     "section 1 names 0.05 as nominal: --speed 0.05"),
    ("systems", 5e10, 1.2e11, "log", True,
     "stellar mass of the galaxy, 2.6e10 to 6.1e10 solar masses (Lian and "
     "others 2025; Licquia and Newman 2015), over 0.54 solar masses per "
     "system (McKee and others 2015; Reyle and others 2021)"),
    ("stellar_density", None, None, None, False,
     "not used unless given; the census of systems within 10 parsecs "
     "counts 0.080 per cubic parsec (Reyle and others 2021)"),
    ("galaxy_model", None, None, None, False,
     "disc that thins outward plus a central bulge"),
    ("disc_radius_kpc", None, None, None, False,
     "Physical Layer section 1"),
    ("disc_thickness_kpc", 0.6, 0.8, "linear", True,
     "surface density over mid-plane density of the stars, 0.65 to 0.78 "
     "(Bland-Hawthorn and Gerhard 2016; McKee and others 2015)"),
    ("scale_length_kpc", 2.1, 3.1, "linear", True,
     "2.6 plus or minus 0.5 (Bland-Hawthorn and Gerhard 2016)"),
    ("bulge_fraction", 0.1, 0.3, "linear", True,
     "0.15 by mass (Licquia and Newman 2015); other estimates reach 0.3"),
    ("bulge_radius_kpc", 0.5, 2.0, "log", True,
     "assumption, order of magnitude only"),
    ("depth", None, None, None, False,
     "the plan surveys every system"),
    ("dwell_years", 1.0, 1000.0, "log", True,
     "assumption; no study fixes the stay per system"),
    ("path_factor", 0.70, 1.0, "linear", True,
     "0.78 is the rule 'go to the nearest unvisited system' in an open "
     "field of random points (simulated; 0.83 inside one region of 1000 "
     "systems); the shortest route through random points costs 0.70 "
     "(Cerf and others 1997); 1.0 is one mean spacing per hop, an upper "
     "bound. Where completion is recorded by system the factor is scaled "
     "by 0.65 / 0.78: a probe that need not clear a region, among "
     "drifting stars, makes hops of 0.65 spacings (simulated)"),
    ("acceleration_m_s2", 0.01, 1.0, "log", False,
     "not modeled unless given; the 1978 fusion-probe study reached 0.12 "
     "of light speed after 3.8 years of thrust, about 0.3 meters per "
     "second squared"),
    ("exhaust_speed_c", 0.03, 0.089, "log", False,
     "0.089 is the ideal limit for fusion of deuterium and helium-3; the "
     "1978 fusion-probe study assumed 0.031 to 0.035. It sets the "
     "propellant per stop, and the survey time only together with the "
     "next input"),
    ("refuel_years_per_mass", None, None, None, False,
     "not modeled unless given; no study fixes a harvesting rate"),
    ("region_systems", None, None, None, False,
     "assumption; the specification fixes no region size"),
    ("dispersal_leg_kpc", None, None, None, False,
     "the disc diameter unless given: the longest leg possible from any "
     "starting point, so the wait does not depend on where the fleet "
     "starts (Physical Layer section 4.5)"),
    ("envelope_factor", None, None, None, False,
     "no extra margin is needed on the longest possible leg"),
    ("bitrate_bps", 0.1, 1.0, "log", False,
     "link budget of Physical Layer section 2.2"),
    ("message_bytes", None, None, None, False,
     "Physical Layer section 2.2"),
    ("archives", None, None, None, False,
     "the doctrine layout (Physical Layer section 3)"),
    ("strategy", None, None, None, False,
     "the plan: completion recorded by system, probes waiting at the "
     "mid-plane of the disc. The specification as it stands records "
     "completion by region (README section 3.2): --strategy regions"),
    ("cache_spacing_kpc", None, None, None, False,
     "set by the archive layout"),
    ("detour_kpc", None, None, None, False,
     "set by the archive layout"),
    ("station_count", None, None, None, False,
     "set by the archive layout"),
    ("consolidation_years", None, None, None, False,
     "Physical Layer section 1"),
    ("deposit_every", None, None, None, False,
     "set by the archive layout"),
    ("attrition_per_year", None, None, None, False,
     "assumption: no probe is ever lost"),
    ("dup_cap", None, None, None, False,
     "tuning of the duplication estimate, not measured"),
    ("dup_gain", None, None, None, False,
     "tuning of the duplication estimate, not measured"),
    ("neighbors", None, None, None, False,
     "Physical Layer section 4.3"),
]

DEFAULT_DRAWS = 2000
DEFAULT_SEED = 1
RANGE_SCALES = ("log", "linear")


def builtin_ranges() -> dict:
    """Plausible ranges of the inputs that --uncertainty varies."""
    return {name: dict(low=low, high=high, scale=scale)
            for name, low, high, scale, varied, _ in INPUT_TABLE if varied}


def normalize_ranges(raw) -> dict:
    """Check ranges read from a scenario file and bring them to one form:
    {input: {"low": .., "high": .., "scale": "log" or "linear"}}; an
    input mapped to None is dropped from the built-in set."""
    if not isinstance(raw, dict):
        raise ValueError('"ranges" must map input names to [low, high]')
    default_scale = {name: scale for name, _, _, scale, _, _ in INPUT_TABLE}
    ranges = {}
    for name, spec in raw.items():
        if name not in _NUMBER_RULES:
            raise ValueError(
                "no range can be given for %r (numeric inputs: %s)"
                % (name, ", ".join(sorted(_NUMBER_RULES))))
        if spec is None:
            ranges[name] = None
            continue
        scale = default_scale.get(name) or "linear"
        if isinstance(spec, (list, tuple)) and len(spec) == 2:
            low, high = spec
        elif isinstance(spec, dict) and set(spec) <= {"low", "high", "scale"} \
                and "low" in spec and "high" in spec:
            low, high, scale = spec["low"], spec["high"], spec.get("scale",
                                                                   scale)
        else:
            raise ValueError(
                'the range of %s must be [low, high] or {"low": .., '
                '"high": .., "scale": "log" or "linear"}' % name)
        for end in (low, high):
            if (isinstance(end, bool) or not isinstance(end, (int, float))
                    or not math.isfinite(end)):
                raise ValueError("the range of %s needs two finite numbers "
                                 "(got %r)" % (name, spec))
        if not low < high:
            raise ValueError("the range of %s must run from a lower to a "
                             "higher value (got %r)" % (name, spec))
        if scale not in RANGE_SCALES:
            raise ValueError("the scale of %s must be one of: %s (got %r)"
                             % (name, ", ".join(RANGE_SCALES), scale))
        if scale == "log" and low <= 0:
            raise ValueError("a log range of %s must start above 0 (got %r)"
                             % (name, spec))
        ranges[name] = dict(low=float(low), high=float(high), scale=scale)
    return ranges


def _set_input(sc: Scenario, name: str, value: float) -> Scenario:
    if name in _WHOLE_NUMBER_FIELDS:
        value = int(round(value))
    return replace(sc, **{name: value})


def _percentile(ordered: list, percent: float) -> float:
    """Percentile of an ascending list, interpolating between neighbors;
    unbounded entries (surveys that never finish) sort last."""
    position = percent / 100.0 * (len(ordered) - 1)
    below = int(math.floor(position))
    above = min(below + 1, len(ordered) - 1)
    weight = position - below
    if weight == 0.0 or ordered[below] == ordered[above]:
        return ordered[below]
    if math.isinf(ordered[above]):
        return math.inf
    return ordered[below] + weight * (ordered[above] - ordered[below])


def run_uncertainty(sc: Scenario, ranges: dict,
                    draws: int = DEFAULT_DRAWS,
                    seed: int = DEFAULT_SEED) -> dict:
    """Vary the ranged inputs together (seeded draws) and one at a time.

    Returns the 5th, 50th and 95th percentile of the full-survey time over
    the draws, and for every ranged input the survey time at each end of
    its range with all other inputs at their set values."""
    if isinstance(draws, bool) or not isinstance(draws, int) or draws < 1:
        raise ValueError("draws must be a whole number of at least 1")
    order = [f.name for f in fields(Scenario)]
    names = sorted((name for name, spec in ranges.items() if spec),
                   key=order.index)
    if not names:
        raise ValueError("no input has a range to vary")

    one_at_a_time = []
    for name in names:
        spec = ranges[name]
        ends = []
        for end in ("low", "high"):
            try:
                ends.append(derive(_set_input(sc, name, spec[end]),
                                   detail=False)["total_years"])
            except ValueError as exc:
                raise ValueError("the %s end of the range of %s is not a "
                                 "usable value: %s" % (end, name, exc))
        central = getattr(sc, name)
        one_at_a_time.append(dict(
            input=name, low=spec["low"], high=spec["high"],
            scale=spec["scale"], total_years_at_low=ends[0],
            total_years_at_high=ends[1],
            set_value_inside=(central is None
                              or spec["low"] <= central <= spec["high"])))

    rng = random.Random(seed)
    totals = []
    for _ in range(draws):
        drawn = sc
        for name in names:
            spec = ranges[name]
            if spec["scale"] == "log":
                value = math.exp(rng.uniform(math.log(spec["low"]),
                                             math.log(spec["high"])))
            else:
                value = rng.uniform(spec["low"], spec["high"])
            drawn = _set_input(drawn, name, value)
        totals.append(derive(drawn, detail=False)["total_years"])
    totals.sort()
    low, median, high = (_percentile(totals, p) for p in (5, 50, 95))
    return dict(
        draws=draws, seed=seed,
        ranges={name: ranges[name] for name in names},
        percentiles_years={"5": low, "50": median, "95": high},
        spread_factor=(high / low if math.isfinite(high) and low > 0
                       else math.inf),
        unfinished_share=sum(1 for t in totals if math.isinf(t)) / draws,
        one_at_a_time=one_at_a_time)


# ---------------------------------------------------------------------------
# The galaxy: one model from which both the system count and the
# distances between neighboring systems follow
# ---------------------------------------------------------------------------
#
# Route length through points of varying density (Beardwood, Halton and
# Hammersley 1959): a tour through systems of number density n costs,
# per system, a constant times n^(-1/3) evaluated where that system is.
# The mean hop is therefore that constant (the path factor) times the
# mean of n^(-1/3) taken over systems, called the "mean spacing" below.
#
# exponential model
#   disc   n(R, z) = n0 exp(-R / L) exp(-|z| / h) for R up to the disc
#          radius, with scale length L and scale height h = thickness / 2
#   bulge  n(r) = nb exp(-r^2 / (2 s^2)), a round Gaussian cloud whose
#          half-count radius is the bulge radius
#   The two parts are treated as separate populations. Where they overlap
#   the true spacing is a little shorter, so this slightly overstates the
#   route.
#   For the strategy that waits in a thin layer at the mid-plane, each
#   disc system is taken as it passes through that layer, so the density
#   is that of the mid-plane, n0 exp(-R / L). The bulge is round and has
#   no such plane: its systems are taken wherever they are.
# uniform model
#   one density throughout a disc of the given radius and thickness
#
# No input refers to a place inside the galaxy, so the model carries no
# information about where the fleet starts.

_HALF_COUNT_RADIUS_IN_SIGMAS = 1.5381723     # round Gaussian cloud


def _g1(x: float) -> float:
    """Integral of t exp(-t) from 0 to x."""
    if x < 1e-3:
        return x * x * (0.5 - x / 3.0 + x * x / 8.0)
    return 1.0 - math.exp(-x) * (1.0 + x)


def _disc_cdf(u: float, xm: float) -> float:
    """Share of disc systems whose density is above exp(-u) times the
    central density; u = R / L + |z| / h, and xm = disc radius / L."""
    if u <= 0.0:
        return 0.0
    m = min(u, xm)
    return (_g1(m) - math.exp(-u) * m * m / 2.0) / _g1(xm)


def _bulge_cdf(q: float) -> float:
    """Share of bulge systems whose density is above exp(-q) times the
    central density; q = r^2 / (2 s^2)."""
    if q <= 0.0:
        return 0.0
    root = math.sqrt(q)
    return math.erf(root) - 2.0 * root * math.exp(-q) / math.sqrt(math.pi)


def resolve_galaxy(sc: Scenario, plane=None) -> dict:
    """Turn the workload inputs into the system count and the spacing
    between neighboring systems. Exactly one of the two is an input in
    any run unless the user gives both on purpose. `plane` says whether
    disc systems are taken at the mid-plane; by default the strategy
    decides."""
    radius_pc = sc.disc_radius_kpc * 1e3
    thickness_pc = sc.disc_thickness_kpc * 1e3
    slab_volume_pc3 = math.pi * radius_pc ** 2 * thickness_pc

    gal = dict(disc_radius_pc=radius_pc, thickness_pc=thickness_pc,
               slab_volume_pc3=slab_volume_pc3)
    if sc.stellar_density is not None:
        # An explicit density means a uniform disc. The count follows
        # from the disc volume unless a count was given as well.
        implied = sc.stellar_density * slab_volume_pc3
        gal.update(
            model="uniform", uniform_density=sc.stellar_density,
            systems_implied_by_density=implied,
            systems=implied if sc.systems is None else sc.systems,
            source="density" if sc.systems is None else "count and density")
    else:
        systems = DEFAULT_SYSTEMS if sc.systems is None else sc.systems
        gal.update(model=sc.galaxy_model, systems=systems, source="count")
        if sc.galaxy_model == "uniform":
            gal.update(uniform_density=systems / slab_volume_pc3)

    if gal["model"] == "uniform":
        spacing = gal["uniform_density"] ** (-1.0 / 3.0)
        gal.update(mean_spacing_pc=spacing, mean_spacing_at_large_pc=spacing,
                   parts=[dict(kind="uniform", share=1.0,
                               central_spacing_pc=spacing,
                               mean_spacing_pc=spacing)])
        return gal

    scale_pc = sc.scale_length_kpc * 1e3
    height_pc = thickness_pc / 2.0
    xm = radius_pc / scale_pc
    n_bulge = sc.bulge_fraction * gal["systems"]
    n_disc = gal["systems"] - n_bulge
    disc_central = n_disc / (2.0 * math.pi * scale_pc ** 2 * _g1(xm)
                             * 2.0 * height_pc)
    disc_spacing0 = disc_central ** (-1.0 / 3.0)
    # Mean of exp(u / 3) over systems: 9/4 g(2x/3)/g(x) from the radius,
    # and 3/2 more from the height unless the probes wait at the
    # mid-plane.
    if plane is None:
        plane = sc.strategy == "systems-midplane"
    parts = [dict(
        kind="disc-plane" if plane else "disc",
        share=1.0 - sc.bulge_fraction, xm=xm,
        central_spacing_pc=disc_spacing0,
        mean_spacing_pc=(disc_spacing0 * (9.0 / 4.0 if plane else 27.0 / 8.0)
                         * _g1(2.0 * xm / 3.0) / _g1(xm)))]
    gal.update(scale_length_pc=scale_pc, scale_height_pc=height_pc,
               disc_systems=n_disc, disc_central_density=disc_central,
               bulge_systems=n_bulge, bulge_central_density=0.0,
               bulge_sigma_pc=None)
    if n_bulge > 0.0:
        sigma_pc = sc.bulge_radius_kpc * 1e3 / _HALF_COUNT_RADIUS_IN_SIGMAS
        bulge_central = n_bulge / ((2.0 * math.pi) ** 1.5 * sigma_pc ** 3)
        bulge_spacing0 = bulge_central ** (-1.0 / 3.0)
        parts.append(dict(
            kind="bulge", share=sc.bulge_fraction,
            central_spacing_pc=bulge_spacing0,
            mean_spacing_pc=bulge_spacing0 * 1.5 ** 1.5))
        gal.update(bulge_central_density=bulge_central,
                   bulge_sigma_pc=sigma_pc)
    gal.update(parts=parts, mean_spacing_pc=sum(
        part["share"] * part["mean_spacing_pc"] for part in parts))
    # The same without the restriction to the mid-plane, for comparison.
    gal["mean_spacing_at_large_pc"] = (
        (1.0 - sc.bulge_fraction) * disc_spacing0 * 27.0 / 8.0
        * _g1(2.0 * xm / 3.0) / _g1(xm)
        + (sc.bulge_fraction * bulge_spacing0 * 1.5 ** 1.5
           if n_bulge > 0.0 else 0.0))
    return gal


def midplane_density(gal: dict, radius_pc: float) -> float:
    """Systems per cubic parsec in the mid-plane at a distance from the
    galactic center (both parts of the exponential model together)."""
    if gal["model"] == "uniform":
        return gal["uniform_density"] if radius_pc <= gal["disc_radius_pc"] \
            else 0.0
    density = 0.0
    if radius_pc <= gal["disc_radius_pc"]:
        density += gal["disc_central_density"] * math.exp(
            -radius_pc / gal["scale_length_pc"])
    if gal["bulge_sigma_pc"]:
        density += gal["bulge_central_density"] * math.exp(
            -radius_pc ** 2 / (2.0 * gal["bulge_sigma_pc"] ** 2))
    return density


def spacing_cdf(gal: dict, spacing_pc: float) -> float:
    """Share of all systems whose local spacing is below a value."""
    total = 0.0
    for part in gal["parts"]:
        if spacing_pc <= part["central_spacing_pc"]:
            continue
        if part["kind"] == "uniform":
            total += part["share"]
            continue
        # spacing = central spacing x exp(u / 3)
        u = 3.0 * math.log(spacing_pc / part["central_spacing_pc"])
        if part["kind"] == "disc":
            share = _disc_cdf(u, part["xm"])
        elif part["kind"] == "disc-plane":      # u = R / L alone
            share = _g1(min(u, part["xm"])) / _g1(part["xm"])
        else:
            share = _bulge_cdf(u)
        total += part["share"] * share
    return total


def spacing_percentile(gal: dict, share: float) -> float:
    """Local spacing that the given share of systems stays below."""
    low = math.log(min(part["central_spacing_pc"] for part in gal["parts"]))
    high = low + 40.0
    for _ in range(80):
        mid = 0.5 * (low + high)
        if spacing_cdf(gal, math.exp(mid)) < share:
            low = mid
        else:
            high = mid
    return math.exp(high)


# ---------------------------------------------------------------------------
# Distance traveled where completion is recorded by system
# ---------------------------------------------------------------------------
#
# No system is visited twice, but the systems still to do thin out among
# those already done, because the stars mix long before the survey ends.
# The functions below give the distance traveled by the time a share f of
# the systems is surveyed, in first hops per system.
#
# Where all systems are equally likely to be next (a uniform disc, the
# bulge), the density of those still to do is (1 - f) times the full one,
# a hop is (1 - f)^(-1/3) first hops, and the distance is
#     3/2 x (1 - (1 - f)^(2/3)),      3/2 for the whole survey.
#
# In a disc that thins out away from its mid-plane they are not equally
# likely, least of all for probes that wait at the mid-plane. A star swings through the plane
# and spends less of its time near it the wider it swings: in a disc
# whose density falls off as exp(-|z| / h), with stars of one random
# speed, the time near the plane goes as 1 / x, where x is the star's
# energy of swing over the square of that speed. Wide swingers are met
# rarely and are left for last. With a measure y of how far the survey
# has come,
#     share surveyed                        f = 1 - (1 + y) exp(-y)
#     share left of those near the plane        exp(-y)
#     distance traveled                         9/4 x g(2 y / 3)
# and 9/4 for the whole survey, with g as in the galaxy model. The first
# hops are shorter at the mid-plane by 2/3, and 2/3 x 9/4 = 3/2: over the
# whole survey waiting at the mid-plane saves nothing. It brings the
# first half of the systems sooner.
#
# A direct simulation of stars swinging through the plane, the probe
# always taking the nearest unsurveyed system in a layer of 0.3 h either
# side, gives 1.21, 1.37 and 1.45 times the distance of even thinning at
# 50, 90 and 99 percent; the formula gives 1.25, 1.40 and 1.47 for a
# layer of no thickness.
#
# A fleet spread like the systems, each probe keeping to its own band of
# heights, starts with hops 3/2 as long as those at the mid-plane and
# ends level with the fleet that waits there: in the same simulation it
# needs 1.115, 1.005 and 0.990 times that fleet's distance at 50, 90 and
# 99 percent. The factor 1 + (1 - f)^2 / 2 on the mid-plane distance
# joins those points (1.125, 1.005, 1.000) and has the right start, 3/2.


def _even_work(share: float) -> float:
    """Distance traveled, in first hops per system, when a share of the
    systems is surveyed and every system is equally likely to be next."""
    return 1.5 * (1.0 - (1.0 - min(1.0, share)) ** (2.0 / 3.0))


def _plane_progress(share: float) -> float:
    """The measure y with 1 - (1 + y) exp(-y) = share surveyed."""
    if share <= 0.0:
        return 0.0
    if share >= 1.0:
        return math.inf
    low, high = 0.0, 60.0
    for _ in range(80):
        mid = 0.5 * (low + high)
        if _g1(mid) < share:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def plane_left(share: float) -> float:
    """Share of the systems near the mid-plane that are still to do when
    a share of all systems is surveyed by probes waiting there."""
    return math.exp(-_plane_progress(share))


def _plane_work(share: float) -> float:
    """As _even_work, for probes waiting at the mid-plane."""
    y = _plane_progress(share)
    return 2.25 if math.isinf(y) else 2.25 * _g1(2.0 * y / 3.0)


def _spread_work(share: float) -> float:
    """As _even_work, for probes spread through the disc like its
    systems. Its first hops are 3/2 of those at the mid-plane."""
    left = 1.0 - min(1.0, share)
    return 2.0 / 3.0 * _plane_work(share) * (1.0 + 0.5 * left * left)


def _even_growth(share: float) -> float:
    """Length of a hop, in first hops, when a share is surveyed."""
    return (1.0 - share) ** (-1.0 / 3.0)


def _plane_growth(share: float) -> float:
    return math.exp(_plane_progress(share) / 3.0)


def _spread_growth(share: float) -> float:
    left = 1.0 - share
    return 2.0 / 3.0 * (_plane_growth(share) * (1.0 + 0.5 * left * left)
                        - _plane_work(share) * left)


# Which of the three applies to each part of the galaxy model.
_WORK = {"disc": (_spread_work, _spread_growth),
         "disc-plane": (_plane_work, _plane_growth),
         "bulge": (_even_work, _even_growth),
         "uniform": (_even_work, _even_growth)}


# ---------------------------------------------------------------------------
# Stop-and-go travel
# ---------------------------------------------------------------------------
#
# A probe that must stop at every system cannot cruise the whole hop. With
# acceleration a it needs the time v / a and the distance v^2 / (2 a) to
# reach cruise speed v, and the same again to stop. A leg of length d
# therefore takes
#     d / v + v / a           if d >= v^2 / a   (cruise speed is reached)
#     2 sqrt(d / a)           otherwise         (it turns around halfway)
# Newtonian motion: at 0.2 of light speed the error is about two percent.

# Accelerations quoted for comparison when none is given.
REFERENCE_ACCELERATIONS = (1.0, 0.1, 0.01)


def leg_seconds(distance_m: float, v: float, acceleration) -> float:
    """Travel time of one leg from rest to rest."""
    if acceleration is None:
        return distance_m / v
    if distance_m * acceleration >= v * v:
        return distance_m / v + v / acceleration
    return 2.0 * math.sqrt(distance_m / acceleration)


def _part_hop_seconds(part: dict, hop_scale: float, v: float,
                      acceleration: float, steps: int = 1500) -> tuple:
    """Mean hop time over one part of the galaxy, and the share of its
    hops that reach cruise speed, by midpoint quadrature over the local
    hop length (which is central hop x exp(u / 3))."""
    shortest_m = hop_scale * part["central_spacing_pc"] * PARSEC_M
    ramp_m = v * v / acceleration
    total = reach = weights = 0.0

    def add(u, weight):
        nonlocal total, reach, weights
        d = shortest_m * math.exp(u / 3.0)
        weights += weight
        total += weight * leg_seconds(d, v, acceleration)
        if d >= ramp_m:
            reach += weight

    if part["kind"] in ("disc", "disc-plane"):
        # Whole disc: u = R / L + |z| / h has density proportional to
        # exp(-u) min(u, xm)^2. Mid-plane: u = R / L, density u exp(-u)
        # up to xm. Either has a corner at u = xm, so each side of it
        # gets its own grid of midpoints.
        xm = part["xm"]
        whole = part["kind"] == "disc"
        spans = [(0.0, xm, steps // 3)]
        if whole:
            spans.append((xm, xm + 45.0, steps))
        for start, stop, count in spans:
            du = (stop - start) / count
            for i in range(count):
                u = start + (i + 0.5) * du
                m = min(u, xm)
                add(u, math.exp(-u) * (m * m if whole else u) * du)
    else:
        # bulge: q = r^2 / (2 s^2) = y^2 has density proportional to
        # y^2 exp(-y^2)
        dy = 8.0 / steps
        for i in range(steps):
            y = (i + 0.5) * dy
            add(y * y, y * y * math.exp(-y * y))
    # Dividing by the summed weights, not by the exact normalization,
    # keeps the shares adding up to one whatever the step size.
    return total / weights, reach / weights


def mean_hop_seconds(gal: dict, hop_scale: float, v: float,
                     acceleration) -> tuple:
    """Mean time of one hop between systems, averaged over all systems,
    and the share of hops on which cruise speed is reached."""
    if acceleration is None:
        return hop_scale * gal["mean_spacing_pc"] * PARSEC_M / v, 1.0
    ramp_m = v * v / acceleration
    total = reach = 0.0
    for part in gal["parts"]:
        shortest_m = hop_scale * part["central_spacing_pc"] * PARSEC_M
        if part["kind"] == "uniform":
            total += leg_seconds(shortest_m, v, acceleration)
            reach += 1.0 if shortest_m >= ramp_m else 0.0
        elif shortest_m >= ramp_m:
            # Every hop of this part reaches cruise speed, so the time is
            # linear in the hop length and the mean hop length suffices.
            mean_m = hop_scale * part["mean_spacing_pc"] * PARSEC_M
            total += part["share"] * (mean_m / v + v / acceleration)
            reach += part["share"]
        else:
            seconds, share = _part_hop_seconds(part, hop_scale, v,
                                               acceleration)
            total += part["share"] * seconds
            reach += part["share"] * share
    return total, reach


# ---------------------------------------------------------------------------
# Numbers on what the model leaves out
# ---------------------------------------------------------------------------


def share_leaving_cube(x: float) -> float:
    """Share of points spread evenly through a cube that end up outside
    it after each moves the same distance, x cube sides, in a random
    direction."""
    if x <= 0.0:
        return 0.0
    if x <= 1.0:
        # 1 - mean of (1 - x|a|)(1 - x|b|)(1 - x|c|) over unit vectors
        return 1.5 * x - 2.0 / math.pi * x * x + x ** 3 / (4.0 * math.pi)
    # Past one side a factor can reach zero: average over the directions
    # of one octant numerically.
    steps = 120
    stay = 0.0
    for i in range(steps):
        cos_t = (i + 0.5) / steps
        sin_t = math.sqrt(1.0 - cos_t * cos_t)
        for j in range(steps):
            phi = (j + 0.5) / steps * math.pi / 2.0
            stay += (max(0.0, 1.0 - x * sin_t * math.cos(phi))
                     * max(0.0, 1.0 - x * sin_t * math.sin(phi))
                     * max(0.0, 1.0 - x * cos_t))
    return 1.0 - stay / steps ** 2


# ---------------------------------------------------------------------------
# What a pass over fixed-volume regions reaches while stars drift
# ---------------------------------------------------------------------------
#
# A region is a catalogued volume (Lexicon section 5.1) and completion is
# recorded per region. The stars do not stay put: at 20 to 60 kilometers
# per second relative to their neighbors a system leaves a region of 1000
# systems within a million years, thousands of times during the survey.
# A pass over every region therefore makes one visit per system on
# average, but which systems it meets is a matter of chance. With frequent
# region changes the number of visits a system receives follows the
# Poisson law with mean 1: a share exp(-1) = 37 percent is never met, and
# as many visits go to systems already seen.
#
# share missed in one pass = exp(-1) x mixed, mixed = 1 - exp(-changes / 2)
#
# "changes" is how often a system changes region during one pass. The
# factor "mixed" joins the two limits, nothing moving (nothing missed) and
# full mixing. It matches a simulation of systems moving in straight lines
# through a grid of cells, each cell surveyed once per pass, to within
# 0.02 for 0.3 to 300 changes per pass and for one to three passes. For
# any galaxy-sized survey it equals 1.
#
# Nothing here lets a probe recognize a system that was surveyed in
# another region; the specification records completion by region only.


def share_seen(changes_per_pass: float, passes: float = 1.0,
               depth: float = 1.0) -> float:
    """Share of all systems visited at least once after so many passes
    over every region. `depth` is the share of the systems found in a
    region that a pass visits."""
    if passes <= 0.0:
        return 0.0
    mixed = -math.expm1(-changes_per_pass / 2.0) if changes_per_pass > 0 \
        else 0.0
    if passes < 1.0:
        # Within a pass: a straight line where nothing moves, the Poisson
        # curve where everything mixes.
        return ((1.0 - mixed) * depth * passes
                + mixed * -math.expm1(-depth * passes))
    missed_once = (1.0 - depth) + (math.exp(-depth) - (1.0 - depth)) * mixed
    return 1.0 - missed_once ** passes


def _passes_for(seen, share: float) -> float:
    """Passes (or sweeps) after which `seen(passes)` first reaches the
    given share; infinite if it is out of reach."""
    low, high = 0.0, 1.0
    while seen(high) < share:
        low, high = high, high * 2.0
        if high > 1e6:
            return math.inf
    for _ in range(100):
        mid = 0.5 * (low + high)
        if seen(mid) < share:
            low = mid
        else:
            high = mid
    return high


def passes_for_share(share: float, changes_per_pass: float,
                     depth: float = 1.0) -> float:
    """Passes over every region needed before the given share of all
    systems has been visited at least once (infinite if out of reach)."""
    return _passes_for(
        lambda passes: share_seen(changes_per_pass, passes, depth), share)


# ---------------------------------------------------------------------------
# A line held while the disc turns past it
# ---------------------------------------------------------------------------
#
# The disc turns, so every disc system crosses a line that runs from the
# galactic center to the rim, at rest, once per turn. If the fleet works
# along such a line and surveys what comes through, "done" needs no record
# of any system or region: a stretch of the line is done when it has been
# staffed for one turn.
#
# The fleet is far too small to staff the whole line (the stars cross it
# faster than the probes can survey them), so it staffs a stretch at a
# time, each for one turn, working inward. The stretch at a given distance
# from the center has the width w that brings stars through as fast as the
# fleet can deal with them, and it moves inward by w per turn.
#
# Stars also swing in and out around their mean distance from the center,
# by a = about a tenth of that distance. A star therefore crosses the line
# at a slightly different distance each turn, and may cross outside the
# staffed stretch every time (missed) or inside it twice. With successive
# crossings meeting successive "tiles" of width w, a star of swing a is
# missed with the probability
#     missed(q) = mean over tile offsets of the product of (1 - p_j),
#     q = 2 a / w,   p_j = share of its crossings that fall into tile j,
# which rises from 0 (narrow swing) to exp(-1) (swing much wider than the
# staffed stretch). Against a simulation that follows each star's swing
# turn by turn this is a few percent too hopeful; counting the swing 1.5
# times closes the gap to within 0.02 for fleets of 1,000 to 150,000
# probes.
#
# Moving the line against the rotation is not modeled. The stars arrive
# sooner, but in proportion more of them per year, so the staffed stretch
# is shorter. In the simulation (10,000 probes, line turning backward at
# the rate of the stars at half the disc radius) a sweep takes as long as
# before while the work lasts longer than a turn of the disc, and reaches
# 2 percent fewer of the systems at 0.05 of light speed, 3 to 4 percent
# more at 0.1 to 0.2. A fleet that is held up by the turning disc gains
# time: 40,000 probes at 0.1 finish a sweep three times sooner.

LINE_SWING_CALIBRATION = 1.5
_LINE_TABLE = []


def _tile_missed(q: float, offsets: int = 16) -> float:
    """Share missed by a staffed stretch of width w = 2a / q (see above)."""
    def below(c):               # share of crossings with cos(phase) < c
        return 0.0 if c <= -1.0 else 1.0 if c >= 1.0 \
            else 1.0 - math.acos(c) / math.pi
    width = 2.0 / q             # in units of the swing a
    total = 0.0
    for i in range(offsets):
        edge = -1.0 - width * (i + 0.5) / offsets
        product = 1.0
        while edge < 1.0:
            product *= 1.0 - (below(edge + width) - below(edge))
            edge += width
        total += product
    return total / offsets


def line_missed(q: float) -> float:
    """Share of systems that one sweep of the line misses, for a swing of
    q staffed widths. Read from a table built on first use."""
    if q <= 0.0:
        return 0.0
    if not _LINE_TABLE:
        for step in range(53):                  # q from 0.01 to 200
            value = 10.0 ** (-2.0 + step / 12.0)
            _LINE_TABLE.append((math.log(value), _tile_missed(value)))
    x = math.log(q)
    if x <= _LINE_TABLE[0][0]:
        return _LINE_TABLE[0][1] * q / math.exp(_LINE_TABLE[0][0])
    if x >= _LINE_TABLE[-1][0]:
        last = _LINE_TABLE[-1][1]
        return math.exp(-1.0) - (math.exp(-1.0) - last) * math.exp(
            _LINE_TABLE[-1][0]) / q
    position = (x - _LINE_TABLE[0][0]) * 12.0 / math.log(10.0)
    index = min(int(position), len(_LINE_TABLE) - 2)
    weight = position - index
    return ((1.0 - weight) * _LINE_TABLE[index][1]
            + weight * _LINE_TABLE[index + 1][1])


def line_seen(missed: float, sweeps: float, depth: float = 1.0) -> float:
    """Share of the line's systems seen at least once after so many
    sweeps, each of which misses the given share."""
    reach = depth * (1.0 - missed)
    if sweeps < 1.0:
        return reach * max(0.0, sweeps)
    return 1.0 - (1.0 - reach) ** sweeps


def sweep_line(sc: Scenario, gal: dict, per_system_years: float) -> dict:
    """The line strategy for this fleet: how fast systems cross the line,
    what the fleet can deal with, and the share one sweep misses."""
    radius_pc = gal["disc_radius_pc"]
    speed = ROTATION_SPEED_M_S * YEAR_S / PARSEC_M          # parsecs a year
    if gal["model"] == "uniform":
        on_line = gal["systems"]
        level = on_line / (math.pi * radius_pc ** 2)        # per square parsec

        def surface(r_pc):
            return level
        crossings = level * radius_pc * speed
    else:
        # The disc turns in step; the bulge does not, and stays with the
        # regions.
        on_line = gal["disc_systems"]
        scale = gal["scale_length_pc"]
        xm = radius_pc / scale
        level = on_line / (2.0 * math.pi * scale ** 2 * _g1(xm))

        def surface(r_pc):
            return level * math.exp(-r_pc / scale)
        crossings = level * scale * -math.expm1(-xm) * speed
    share = on_line / gal["systems"]
    # Systems a year the fleet can survey on the line, and how many cross
    # that it sets out to visit.
    capacity = sc.probes / per_system_years * share
    wanted = crossings * sc.depth
    swing_per_pc = RADIAL_RANDOM_SPEED_M_S / (math.sqrt(2.0)
                                              * ROTATION_SPEED_M_S)
    steps, quantiles = 60, 6
    missed = weights = 0.0
    for i in range(steps):
        r_pc = (i + 0.5) * radius_pc / steps
        weight = surface(r_pc) * r_pc
        width = capacity / (surface(r_pc) * sc.depth * speed)
        for j in range(quantiles):
            # swings are spread around their typical size (Rayleigh law)
            swing = swing_per_pc * r_pc * math.sqrt(
                -2.0 * math.log(1.0 - (j + 0.5) / quantiles))
            missed += weight / quantiles * max(
                line_missed(LINE_SWING_CALIBRATION * 2.0 * swing / width),
                # even a fully staffed line misses a few: a star that
                # swings inward turns faster than its stretch stays open
                min(1.0, swing / (math.pi * r_pc)))
        weights += weight
    return dict(
        share_of_systems=share,
        crossings_per_year=crossings,
        capacity_per_year=capacity,
        staffed_share=min(1.0, capacity / wanted),
        probes_to_staff_all=sc.probes * wanted / capacity,
        missed_per_sweep=missed / weights,
        rim_turn_years=2.0 * math.pi * radius_pc / speed)


REACHED_SHARES = (0.5, 0.9, 0.99)


def systems_reached(sc: Scenario, gal: dict, side_pc: float,
                    dispersal_s: float, survey_s: float,
                    per_system_years: float, work_share) -> dict:
    """What the chosen way of running the survey reaches. `side_pc` is the
    size of one region; `work_share(share)` is the part of the whole
    survey's work done when that share of the systems is surveyed (used
    where completion is recorded by system)."""
    # Time for a system to cross one region at each random speed, and
    # how often it does so during one pass.
    crossing_years = [side_pc * PARSEC_M / speed / YEAR_S
                      for speed in RANDOM_SPEEDS_M_S]
    changes = [survey_s / YEAR_S / years for years in crossing_years]
    # The slower speed mixes least; it is used so as not to overstate.
    least = min(changes)
    out = dict(
        strategy=sc.strategy,
        region_side_parsec=side_pc,
        crossing_years=crossing_years,
        region_changes_per_pass=changes,
        # the same at the full orbital speed: how fast stars stream
        # through a volume that does not turn with them
        stream_crossing_years=(side_pc * PARSEC_M / ROTATION_SPEED_M_S
                               / YEAR_S))

    def years_after(work):
        seconds = (None if math.isinf(work) else
                   _survey_time_for_fraction(sc, dispersal_s, survey_s, work))
        return None if seconds is None else (dispersal_s + seconds) / YEAR_S

    if sc.strategy in RECORDS_BY_SYSTEM:
        # Every visit is to a new system; the survey ends when all the
        # systems it set out to visit are done.
        rows = []
        for share in REACHED_SHARES:
            reachable = share <= sc.depth * (1.0 + 1e-12)
            rows.append(dict(
                systems_seen=share, passes=None,
                years=(years_after(work_share(min(1.0, share / sc.depth)))
                       if reachable else None)))
        out.update(unit=None, seen_after_one_pass=sc.depth,
                   repeat_visit_share=0.0, rows=rows)
        return out

    if sc.strategy == "sweep-line":
        line = sweep_line(sc, gal, per_system_years)
        out.update(line=line, unit="sweep")

        def seen(passes):
            return (line["share_of_systems"]
                    * line_seen(line["missed_per_sweep"], passes, sc.depth)
                    + (1.0 - line["share_of_systems"])
                    * share_seen(least, passes, sc.depth))
    else:
        out.update(unit="pass")

        def seen(passes):
            return share_seen(least, passes, sc.depth)

    seen_once = seen(1.0)
    rows = []
    for share in REACHED_SHARES:
        passes = _passes_for(seen, share)
        rows.append(dict(systems_seen=share, passes=passes,
                         years=years_after(passes)))
    out.update(seen_after_one_pass=seen_once,
               # visits of one pass that go to systems already seen
               repeat_visit_share=1.0 - seen_once / sc.depth,
               rows=rows)
    return out


def central_load_factor(sc: Scenario, gal: dict) -> float:
    """Systems per unit of disc area at the center, over the average.
    With seeds spread evenly over the disc area this is how many times
    the mean workload the central probes would carry."""
    if gal["model"] == "uniform":
        return 1.0
    radius2 = gal["disc_radius_pc"] ** 2
    xm = gal["disc_radius_pc"] / gal["scale_length_pc"]
    factor = (1.0 - sc.bulge_fraction) * radius2 / (
        2.0 * gal["scale_length_pc"] ** 2 * _g1(xm))
    if gal["bulge_sigma_pc"]:
        factor += sc.bulge_fraction * radius2 / (
            2.0 * gal["bulge_sigma_pc"] ** 2)
    return factor


def left_out(sc: Scenario, gal: dict, nominal_years: float,
             region_cycle_years: float, side_pc: float,
             stay_years: float, dispersal_years: float) -> dict:
    """Sizes of the effects the model does not follow, for the caveats.
    `side_pc` is the size of one region."""
    half_radius_m = sc.disc_radius_kpc / 2.0 * KPC_M
    turn_years = 2.0 * math.pi * half_radius_m / ROTATION_SPEED_M_S / YEAR_S
    drift = []
    for speed in RANDOM_SPEEDS_M_S:
        moved_pc = speed * region_cycle_years * YEAR_S / PARSEC_M
        drift.append(share_leaving_cube(moved_pc / side_pc))
    stops = dispersal_years / STORED_ENERGY_LEG_YEARS
    return dict(
        turns_at_half_radius=nominal_years / turn_years,
        turn_years=turn_years,
        # Orbits at different radii slide past each other: with the same
        # orbital speed everywhere, two points drift apart by their own
        # separation in radius / speed.
        shear_years=half_radius_m / ROTATION_SPEED_M_S / YEAR_S,
        region_side_parsec=side_pc,
        drift_out_shares=drift,
        new_system_share=STAR_FORMATION_SHARE_PER_YEAR * nominal_years,
        central_load_factor=central_load_factor(sc, gal),
        scattering_stops=stops,
        scattering_stop_years=stops * stay_years)


def _unused_inputs(sc: Scenario, layout: dict, gal: dict) -> list:
    """Inputs that were set to something other than their default but
    cannot change this run, each with the reason. An input that does
    nothing must not pass silently (audit A5)."""
    default = Scenario()

    def given(name):
        return getattr(sc, name) != getattr(default, name)

    unused = []

    def note(name, reason):
        if given(name):
            unused.append(dict(input=name, reason=reason))

    if gal["model"] == "uniform":
        why = ("a single density was given, so the galaxy is a uniform disc"
               if sc.stellar_density is not None
               else "the uniform disc has no such shape")
        for name in ("scale_length_kpc", "bulge_fraction",
                     "bulge_radius_kpc"):
            note(name, why)
    if sc.refuel_years_per_mass == 0:
        note("exhaust_speed_c",
             "it changes the propellant figures shown, but the stay per "
             "system does not grow with them unless %s is set"
             % "--refuel-years")
    if gal["source"] == "count and density":
        note("disc_thickness_kpc",
             "count and density were both given, so the disc volume is "
             "not needed")

    if layout["deposit_every"] is None:
        why = "the chosen layout has no archive points"
        for name in ("cache_spacing_kpc", "detour_kpc", "deposit_every",
                     "consolidation_years"):
            note(name, why)
        for name in ("bitrate_bps", "message_bytes"):
            note(name, "without archive points no messages are sent")
    elif not layout["consolidated"]:
        note("consolidation_years",
             "the chosen layout has no staffed stations, so nothing is "
             "consolidated")
    return unused


# ---------------------------------------------------------------------------
# The analytic model
# ---------------------------------------------------------------------------


def derive(sc: Scenario, detail: bool = True, _compare: bool = True) -> dict:
    """Compute the pace estimate. Pure function of the scenario; returns a
    dict holding every intermediate quantity (for --explain and --json).
    detail=False skips the extras that only the report needs, for the
    many repeated runs of the uncertainty mode. (_compare is internal: it
    stops the comparison of strategies from calling itself.)"""
    sc.validate()
    layout = resolve_layout(sc)
    gal = resolve_galaxy(sc)

    v = sc.speed_c * C_M_PER_S
    accel = sc.acceleration_m_s2
    visited_per_probe = gal["systems"] * sc.depth / sc.probes

    # Propellant (classical rocket equation; the relativistic correction
    # is about one percent in the exponent at 0.2 of light speed). Each
    # visited system costs one braking and one acceleration, a velocity
    # change of 2 v. Hops too short to reach cruise speed cost less.
    mass_ratio = math.exp(2.0 * sc.speed_c / sc.exhaust_speed_c)
    refuel_s = sc.refuel_years_per_mass * (mass_ratio - 1.0) * YEAR_S
    dwell_s = sc.dwell_years * YEAR_S + refuel_s

    # Inter-system hop: the path factor times the mean spacing between
    # neighboring systems. Sampling at depth < 1 thins the visited set, so
    # the density of *visited* systems is the local density times depth
    # and every spacing stretches by depth^(-1/3).
    #
    # Where completion is recorded by system a probe goes to the nearest
    # system not yet surveyed and never has to clear a volume, which
    # shortens its hops (see OPEN_FIELD_HOP). No system is visited twice,
    # but the systems still to do thin out among those already done, so
    # the hops grow as the survey proceeds: path_share() below is the
    # distance traveled, in first hops per system, when a share of the
    # systems is surveyed. Only the distance grows: the time spent
    # speeding up and slowing down stays as it is.
    #
    # All of that needs the stars to mix while the survey lasts. Where
    # they do not, the field stands still and the survey runs as it would
    # by regions; in between the two laws are weighted (see the note at
    # OPEN_FIELD_HOP). Waiting at the mid-plane needs the stars to swing
    # through it several times as well.
    by_system = sc.strategy in RECORDS_BY_SYSTEM
    hop_scale = sc.path_factor * sc.depth ** (-1.0 / 3.0)
    mixing = plane_wait = None
    if by_system:
        at_large = (gal if gal["parts"][0]["kind"] != "disc-plane"
                    else resolve_galaxy(sc, plane=False))
        still_hop_m = hop_scale * at_large["mean_spacing_pc"] * PARSEC_M
        still_first_s, still_cruise = mean_hop_seconds(at_large, hop_scale,
                                                       v, accel)
        still_years = visited_per_probe * (still_first_s + dwell_s) / YEAR_S
        share_side_pc = ((gal["systems"] / sc.probes) ** (1.0 / 3.0)
                         * at_large["mean_spacing_pc"])
        crossings = (still_years * YEAR_S * RANDOM_SPEEDS_M_S[0]
                     / (share_side_pc * PARSEC_M))
        mixing = dict(crossings=crossings, share=-math.expm1(-crossings),
                      probe_share_side_parsec=share_side_pc)
        if at_large is not gal:
            swing_years = (PLANE_SWING_IN_HEIGHTS * gal["scale_height_pc"]
                           * PARSEC_M / RANDOM_SPEEDS_M_S[0] / YEAR_S)
            plane_wait = dict(swing_years=swing_years,
                              swings=still_years / swing_years,
                              waits=(still_years >= PLANE_SWINGS_NEEDED
                                     * swing_years))
            if not plane_wait["waits"]:
                gal = at_large
        mixed = mixing["share"]
        open_scale = hop_scale * OPEN_FIELD_HOP / CLEARED_FIELD_HOP
        open_hop_m = open_scale * gal["mean_spacing_pc"] * PARSEC_M
        open_first_s, open_cruise = mean_hop_seconds(gal, open_scale, v,
                                                     accel)
        hop_m = (1.0 - mixed) * still_hop_m + mixed * open_hop_m
        first_hop_s = (1.0 - mixed) * still_first_s + mixed * open_first_s
        cruise_share = (1.0 - mixed) * still_cruise + mixed * open_cruise
        # first hop over mean spacing, for the spread of hop lengths
        hop_scale = hop_m / (gal["mean_spacing_pc"] * PARSEC_M)
    else:
        hop_m = hop_scale * gal["mean_spacing_pc"] * PARSEC_M
        first_hop_s, cruise_share = mean_hop_seconds(gal, hop_scale, v, accel)

    def _over_parts(which, share):
        return sum(part["share"] * part["mean_spacing_pc"]
                   * _WORK[part["kind"]][which](share)
                   for part in gal["parts"]) / gal["mean_spacing_pc"]

    def path_share(share):
        if not by_system:
            return share
        return ((1.0 - mixed) * still_hop_m * share
                + mixed * open_hop_m * _over_parts(0, share)) / hop_m

    def hop_growth(share):
        """Length of a hop, in first hops, when a share is surveyed."""
        if not by_system:
            return 1.0
        return ((1.0 - mixed) * still_hop_m
                + mixed * open_hop_m * _over_parts(1, share)) / hop_m

    thinning = path_share(1.0)      # mean hop of the survey in first hops
    cruise_s = hop_m / v
    ramp_s = max(0.0, first_hop_s - cruise_s)
    t_hop_s = cruise_s * thinning + ramp_s      # average over the survey
    t_sys_s = t_hop_s + dwell_s
    work_s = visited_per_probe * t_sys_s

    # A region cannot be larger than one probe's whole share of the
    # survey. With more probes than regions the share is the smaller of
    # the two, and the region cycle must shrink with it; otherwise the
    # staleness below would be measured against a cycle longer than the
    # entire survey.
    region_systems = min(sc.region_systems, visited_per_probe)
    regions_per_probe = visited_per_probe / region_systems
    t_region_s = region_systems * t_sys_s

    # Archive effects -------------------------------------------------------
    dep_every = layout["deposit_every"]
    deposits_per_probe = regions_per_probe / dep_every if dep_every else 0.0
    detour_m_per_probe = deposits_per_probe * 2.0 * layout["detour_kpc"] * KPC_M
    # Out and back: two legs, each from rest to rest.
    detour_s = deposits_per_probe * 2.0 * leg_seconds(
        layout["detour_kpc"] * KPC_M, v, accel)

    # Knowledge staleness: how old, at region-selection time, the completion
    # facts of neighboring probes can be. The delays act one after another,
    # so they add. With staffed stations: a neighbor's region stays off the
    # record until that neighbor's next deposit (only completions are
    # recorded, so work in progress is invisible), the record then waits
    # for the station's next consolidation cycle, and finally crosses to
    # the reader's archive point at light speed. Without stations a fact
    # moves only when a probe carries it, so both probes' deposit
    # intervals count and the crossing happens at probe speed.
    tc_s = sc.consolidation_years * YEAR_S
    spacing_m = (layout["cache_spacing_kpc"] or 0.0) * KPC_M
    if dep_every is None:
        staleness_parts = {}
        tau_s = math.inf
    else:
        refresh_s = t_region_s * dep_every
        if layout["consolidated"]:
            staleness_parts = dict(
                deposit_interval=refresh_s,
                consolidation_cycle=tc_s,
                light_between_points=spacing_m / C_M_PER_S)
        else:
            staleness_parts = dict(
                deposit_interval=2.0 * refresh_s,
                carried_between_points=spacing_m / v)
        tau_s = sum(staleness_parts.values())

    # Duplicated-work fraction: each region selection risks colliding with
    # one of ~`neighbors` adjacent probes whose completions are up to tau
    # old; the risk per selection scales with how many region cycles of
    # staleness that represents, spread over the probe's own region budget.
    # A documented approximation (tunable via dup_gain), capped at dup_cap.
    if math.isinf(tau_s):
        f_dup_raw = math.inf
    else:
        f_dup_raw = (sc.dup_gain * (tau_s / t_region_s)
                     * sc.neighbors / regions_per_probe)
    f_dup = min(sc.dup_cap, f_dup_raw)

    # Phases ----------------------------------------------------------------
    # Scattering: every probe waits out the same allowance before the
    # survey starts fleet-wide, however short its own leg was.
    diameter_kpc = 2.0 * sc.disc_radius_kpc
    leg_kpc = (diameter_kpc if sc.dispersal_leg_kpc is None
               else sc.dispersal_leg_kpc)
    dispersal_s = leg_seconds(leg_kpc * KPC_M, v, accel) * sc.envelope_factor
    duplication_s = work_s * f_dup
    survey_s = work_s + duplication_s + detour_s
    # A line held while the disc turns cannot be swept faster than the
    # disc turns: every stretch has to stay staffed for one turn, and the
    # rim takes longest. A fleet large enough to finish its work sooner
    # waits out the rest of that turn.
    line_wait_s = 0.0
    if sc.strategy == "sweep-line":
        rim_turn_s = (2.0 * math.pi * sc.disc_radius_kpc * KPC_M
                      / ROTATION_SPEED_M_S)
        line_wait_s = max(0.0, rim_turn_s - survey_s)
        survey_s += line_wait_s

    # Attrition: solve for the survey time in which the decaying fleet
    # accumulates the required probe-seconds of work.
    attrition = _apply_attrition(sc, dispersal_s, survey_s)
    survey_s_effective = attrition["survey_seconds"]
    total_s = dispersal_s + survey_s_effective
    threshold_s = loss_rate_threshold(dispersal_s, survey_s)
    attrition.update(
        rate_per_year=sc.attrition_per_year,
        # the survey can finish only below this loss rate
        threshold_per_year=threshold_s * YEAR_S,
        mean_life_needed_years=1.0 / (threshold_s * YEAR_S),
        # share of the fleet still working when the survey ends
        fleet_left_at_end=(0.0 if math.isinf(total_s) else math.exp(
            -sc.attrition_per_year * total_s / YEAR_S)))

    def work_share(share):
        """Part of the whole survey's work done when this share of what
        the milestones count is surveyed: regions (or the line), in step
        with the work; or systems, with hops growing as they thin out."""
        if not by_system:
            return share
        done = cruise_s * path_share(share) + (ramp_s + dwell_s) * share
        return done / t_sys_s

    milestones = []
    for frac in MILESTONE_FRACTIONS:
        t_frac = _survey_time_for_fraction(sc, dispersal_s, survey_s,
                                           work_share(frac))
        milestones.append(dict(
            fraction=frac,
            years=None if t_frac is None else (dispersal_s + t_frac) / YEAR_S))

    # Communication totals (coordination traffic only; bulk data rides along
    # as physical cargo at probe speed, Physical Layer section 2.3).
    # The bit rate holds at the reference distance of the link budget;
    # received power, and the rate with it, falls with the square of the
    # distance. Between staffed stations a link spans their spacing.
    # Unattended boxes have no power to beam with: a probe hands its
    # records over at the box, at close range, so no distance penalty
    # applies there.
    messages_per_probe = 0.0 if dep_every is None else regions_per_probe
    link_m = spacing_m if dep_every and layout["consolidated"] else None
    link_rate_bps = sc.bitrate_bps
    if link_m is not None:
        link_rate_bps *= (LINK_REFERENCE_M / link_m) ** 2
    link_s_per_message = sc.message_bytes * 8.0 / link_rate_bps
    link_s_per_probe = messages_per_probe * link_s_per_message
    fleet_messages = messages_per_probe * sc.probes

    # A region is a volume: the one that holds region_systems visited
    # systems at the mean spacing.
    region_side_pc = ((region_systems / sc.depth) ** (1.0 / 3.0)
                      * gal["mean_spacing_at_large_pc"])

    # Distances -------------------------------------------------------------
    survey_path_m = visited_per_probe * hop_m * thinning * (1.0 + f_dup)
    dispersal_m = leg_kpc * KPC_M       # an upper bound for any probe
    per_probe_m = dispersal_m + survey_path_m + detour_m_per_probe
    fleet_m = per_probe_m * sc.probes

    return dict(
        scenario=asdict(sc),
        layout=layout,
        geometry=fleet_geometry(sc),
        galaxy=gal,
        systems=gal["systems"],
        speed_m_per_s=v,
        hop_parsec=hop_m / PARSEC_M,
        # Local hop length that 5, 50 and 95 percent of systems stay below.
        hop_percentiles_parsec={
            str(pct): hop_scale * spacing_percentile(gal, pct / 100.0)
            for pct in (5, 50, 95)} if detail else None,
        # the first hops, among systems none of which is surveyed yet
        hop_years=first_hop_s / YEAR_S,
        # the average over the survey (longer where systems thin out)
        hop_years_average=t_hop_s / YEAR_S,
        hop_thinning=thinning,
        # the same when half and when nine tenths of the systems are done
        hop_growth={"0.5": hop_growth(0.5), "0.9": hop_growth(0.9)},
        # share left of the systems near the mid-plane when half of all
        # systems are done, where the probes wait there
        plane_left_at_half=(plane_left(0.5) if any(
            part["kind"] == "disc-plane" for part in gal["parts"]) and
            by_system else None),
        # how far the stars mix during the survey, and whether it lasts
        # long enough for waiting at the mid-plane (both None unless
        # completion is recorded by system)
        mixing=mixing,
        plane_wait=plane_wait,
        propellant=dict(
            exhaust_speed_c=sc.exhaust_speed_c,
            mass_ratio_per_stop=mass_ratio,
            velocity_change_per_stop_c=2.0 * sc.speed_c,
            velocity_change_per_probe_c=(2.0 * sc.speed_c
                                         * visited_per_probe),
            refuel_years_per_stop=refuel_s / YEAR_S,
            stay_years_per_system=dwell_s / YEAR_S,
            reference=[dict(exhaust_speed_c=ve, label=label,
                            mass_ratio_per_stop=math.exp(
                                2.0 * sc.speed_c / ve))
                       for ve, label in REFERENCE_EXHAUST]),
        kinematics=dict(
            acceleration_m_s2=accel,
            # time and distance spent speeding up plus slowing down
            ramp_years=0.0 if accel is None else v / accel / YEAR_S,
            ramp_parsec=0.0 if accel is None else v * v / accel / PARSEC_M,
            hops_reaching_cruise=cruise_share,
            extra_hop_fraction=first_hop_s / (hop_m / v) - 1.0,
            # what standard accelerations would add to the mean hop time
            reference=[dict(
                acceleration_m_s2=a,
                extra_hop_fraction=(mean_hop_seconds(gal, hop_scale, v, a)[0]
                                    / (hop_m / v) - 1.0))
                for a in REFERENCE_ACCELERATIONS] if detail else None),
        per_system_years=t_sys_s / YEAR_S,
        visited_per_probe=visited_per_probe,
        region_systems=region_systems,
        region_shrunk=region_systems < sc.region_systems,
        regions_per_probe=regions_per_probe,
        region_cycle_years=t_region_s / YEAR_S,
        staleness_years=None if math.isinf(tau_s) else tau_s / YEAR_S,
        staleness_infinite=math.isinf(tau_s),
        dispersal=dict(
            leg_kpc=leg_kpc, diameter_kpc=diameter_kpc,
            allowance_kpc=leg_kpc * sc.envelope_factor,
            # False when the allowance is shorter than the longest leg a
            # start at the rim would need: it then depends on the start.
            covers_any_start=(leg_kpc * sc.envelope_factor
                              >= diameter_kpc * (1 - 1e-12))),
        staleness_parts_years={name: part / YEAR_S
                               for name, part in staleness_parts.items()},
        unused_inputs=_unused_inputs(sc, layout, gal),
        duplication_fraction=f_dup,
        # True when the formula asked for more than the ceiling although
        # archives exist: the fleet is too large for the approximation.
        duplication_capped=(not math.isinf(tau_s) and f_dup_raw > sc.dup_cap),
        phases=dict(
            dispersal_years=dispersal_s / YEAR_S,
            survey_work_years=work_s / YEAR_S,
            duplicated_work_years=duplication_s / YEAR_S,
            archive_detours_years=detour_s / YEAR_S,
            line_wait_years=line_wait_s / YEAR_S,
        ),
        attrition=attrition,
        fleet_exhausted=math.isinf(total_s),
        scale_estimate=total_s / YEAR_S > SCALE_ESTIMATE_YEARS,
        total_years=total_s / YEAR_S,
        total_seconds=total_s,
        milestones=milestones,
        comms=dict(
            messages_per_probe=messages_per_probe,
            fleet_messages=fleet_messages,
            link_rate_bps=link_rate_bps,
            link_distance_m=link_m,
            link_seconds_per_message=link_s_per_message,
            link_years_per_probe=link_s_per_probe / YEAR_S,
        ),
        strategy=sc.strategy,
        # What the milestones count: regions, the line, or systems.
        milestones_count=("systems" if by_system else
                          "line" if sc.strategy == "sweep-line"
                          else "regions"),
        # What share of the systems the chosen way of running the survey
        # reaches, and how long 50, 90 and 99 percent take.
        reached=systems_reached(
            sc, gal, region_side_pc, dispersal_s, survey_s,
            t_sys_s / YEAR_S, work_share) if detail or not _compare
        else None,
        # The same for every way of running the survey, side by side.
        strategies=[dict(
            strategy=name,
            seen_after_one_pass=other["reached"]["seen_after_one_pass"],
            years_to_99_percent=other["reached"]["rows"][-1]["years"],
            one_pass_years=other["total_years"])
            for name, other in (
                (name, derive(replace(sc, strategy=name), detail=False,
                              _compare=False)) for name in STRATEGIES)]
        if detail and _compare else None,
        left_out=left_out(
            sc, gal, (dispersal_s + survey_s) / YEAR_S, t_region_s / YEAR_S,
            region_side_pc, dwell_s / YEAR_S,
            dispersal_s / YEAR_S) if detail else None,
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


def loss_rate_threshold(dispersal_s: float, survey_s: float) -> float:
    """Highest loss rate, per second, at which the fleet still finishes.

    A fleet shrinking at rate L delivers, per starting probe and summed
    to the end of time, exp(-L x scattering time) / L seconds of work.
    The survey needs survey_s per starting probe, so it finishes only if
        L x exp(L x scattering time) x survey_s <= 1.
    For a short scattering phase that is L below 1 / survey time."""
    # Compared in logarithms: with a survey much shorter than the
    # scattering phase the exponential itself would overflow.
    low, high = 0.0, 1.0 / survey_s
    for _ in range(200):
        mid = 0.5 * (low + high)
        if mid > 0.0 and (math.log(mid) + mid * dispersal_s
                          + math.log(survey_s)) < 0.0:
            low = mid
        elif mid > 0.0:
            high = mid
        else:
            break
    return low


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


def sig(value: float, digits: int = 3) -> str:
    """A number rounded to so many significant figures, written without
    an exponent wherever that stays readable. At three figures and more,
    closing zeros are dropped (20, not 20.0); at two figures both are
    kept (6.0, not 6), since there the count of figures is the message."""
    if value == 0:
        return "0"
    if not 1e-4 <= abs(value) < 1e15:
        return "%.*g" % (digits, value)
    exponent = math.floor(math.log10(abs(value)))
    rounded = round(value, digits - 1 - exponent)
    exponent = math.floor(math.log10(abs(rounded)))     # 999.6 -> 1000
    text = "%.*f" % (max(0, digits - 1 - exponent), rounded)
    if digits >= 3 and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def si_quantity(value: float, unit: str, digits: int = 3) -> str:
    if value == 0:
        return "0 %ss" % unit
    if math.isinf(value):
        return "unbounded"
    for factor, prefix in _SI_PREFIXES:
        if value >= factor:
            return "%s %s%ss" % (sig(value / factor, digits), prefix, unit)
    return "%s %ss" % (sig(value, digits), unit)


_COUNT_WORDS = [(1e12, "trillion"), (1e9, "billion"), (1e6, "million"),
                (1e3, "thousand")]


def human_count(value: float, digits: int = 3) -> str:
    if math.isinf(value):
        return "unbounded"
    for factor, word in _COUNT_WORDS:
        if abs(value) >= factor:
            return "%s %s" % (sig(value / factor, digits), word)
    return sig(value, digits)


def fmt_years(years: float, canonical: bool = False, digits: int = 3) -> str:
    if years is None:
        return "not reached"
    if math.isinf(years):
        return "never (fleet exhausted)"
    seconds = years * YEAR_S
    if canonical:
        return si_quantity(seconds, "second", digits)
    return "%s years (%s)" % (human_count(years, digits),
                              si_quantity(seconds, "second", digits))


def fmt_span(low_years: float, high_years: float,
             canonical: bool = False, digits: int = 2) -> str:
    """Two durations in one shared unit: '0.35 to 6.1 billion years'."""
    ends = [low_years, high_years]
    finite = [abs(y) for y in ends if y is not None and math.isfinite(y)]
    if not finite:
        return "never"
    scale, unit = 1.0, "years"
    if canonical:
        top = max(finite) * YEAR_S
        scale, unit = YEAR_S, "seconds"
        for factor, prefix in _SI_PREFIXES:
            if top >= factor:
                scale, unit = YEAR_S / factor, prefix + "seconds"
                break
    else:
        for factor, word in _COUNT_WORDS:
            if max(finite) >= factor:
                scale, unit = 1.0 / factor, word + " years"
                break
    words = ["never" if y is None or math.isinf(y) else sig(y * scale, digits)
             for y in ends]
    if words[1] == "never":
        return "%s %s to never" % (words[0], unit)
    return "%s to %s %s" % (words[0], words[1], unit)


def fmt_duration(years: float, canonical: bool = False,
                 digits: int = 2) -> str:
    """One duration in one unit: years, or seconds if canonical."""
    if years is None or math.isinf(years):
        return "never"
    if canonical:
        return si_quantity(years * YEAR_S, "second", digits)
    return "%s years" % human_count(years, digits)


def fmt_number(value) -> str:
    """An input value as a reader would write it."""
    if value is None:
        return "none"
    if isinstance(value, str):
        return value
    if abs(value) >= 1e6:
        return human_count(value)
    return sig(value, 3)


def fmt_number_span(low: float, high: float) -> str:
    """Two input values, sharing the count word when both are large:
    '50 to 120 billion'."""
    for factor, word in _COUNT_WORDS[:3]:
        if abs(high) >= factor and abs(low) >= factor / 1e3:
            return "%s to %s %s" % (sig(low / factor, 3),
                                    sig(high / factor, 3), word)
    return "%s to %s" % (sig(low, 3), sig(high, 3))


def fmt_kiloparsecs(kpc: float, canonical: bool = False) -> str:
    if canonical:
        return si_quantity(kpc * KPC_M, "meter")
    return "%.3g kiloparsecs" % kpc


def fmt_meters(meters: float, canonical: bool = False) -> str:
    if canonical:
        return si_quantity(meters, "meter")
    ly = meters / LIGHT_YEAR_M
    return "%s light-years (%s)" % (human_count(ly), si_quantity(meters, "meter"))


_STALENESS_LABELS = {
    "deposit_interval": "between deposits of finished work",
    "consolidation_cycle": "waiting for the next consolidation",
    "light_between_points": "light time between archive points",
    "carried_between_points": "carried between boxes at probe speed",
}


def flag_for(name: str) -> str:
    """Command-line spelling of a scenario input, for messages."""
    for action in build_parser()._actions:
        if action.dest == name and action.option_strings:
            return action.option_strings[0]
    return name


def fill(text: str, indent: str = "  ", first: str = None,
         width: int = 76) -> list:
    """Wrap text to the report width. Hyphens are not break points, so a
    flag such as --refuel-years is never split across lines."""
    return textwrap.wrap(text, width=width,
                         initial_indent=indent if first is None else first,
                         subsequent_indent=indent, break_on_hyphens=False,
                         break_long_words=False)


def _wrap(label: str, text: str) -> list:
    """Wrap a header entry to the report width under a 12-column label."""
    return fill(text, indent=" " * 12, first="%-12s" % label)


def render_ranges(u: dict, canonical: bool = False) -> list:
    """The uncertainty section: every ranged input on its own, then all
    of them together."""
    lines = ["Input ranges, and the full survey with each varied alone",
             "-" * 60]
    for row in u["one_at_a_time"]:
        lines.append("  %-22s %-27s %s" % (
            flag_for(row["input"]),
            "%s, %s" % (fmt_number_span(row["low"], row["high"]),
                        row["scale"]),
            fmt_span(row["total_years_at_low"], row["total_years_at_high"],
                     canonical)))
    pct = u["percentiles_years"]
    lines.append("  all varied together (%s draws, seed %d):"
                 % (format(u["draws"], ","), u["seed"]))
    lines.append("    %-28s %s" % ("5 to 95 percent interval",
                                   fmt_span(pct["5"], pct["95"], canonical)))
    lines.append("    %-28s %s" % ("median",
                                   fmt_duration(pct["50"], canonical)))
    if math.isfinite(u["spread_factor"]):
        lines.append("    %-28s %s" % ("ratio of the two ends",
                                       sig(u["spread_factor"], 2)))
    if u["unfinished_share"] > 0:
        lines.append("    the fleet is exhausted before the end in %s%% of "
                     "the draws" % sig(100 * u["unfinished_share"], 2))
    outside = [flag_for(row["input"]) for row in u["one_at_a_time"]
               if not row["set_value_inside"]]
    if outside:
        lines += fill(
            "the value set for %s lies outside its range, so the headline "
            "is not a typical draw" % ", ".join(outside), indent="    ")
    lines += fill(
        "Draws are even in the logarithm where a range is marked log and "
        "even in the value where it is marked linear. The ranges are "
        "judgments, so the interval shows how far the inputs can move the "
        "answer; it is not a probability of anything.")
    return lines


def render_defaults() -> list:
    """Every default with its plausible range and where it comes from."""
    default = Scenario()
    lines = [
        "DEFAULTS, THEIR SOURCES AND PLAUSIBLE RANGES",
        "=" * 60,
        "Inputs marked * are the ones --uncertainty varies. Ranges are",
        "judgments from the sources named, not measured error bars.",
        "",
    ]
    for name, low, high, scale, varied, source in INPUT_TABLE:
        value = getattr(default, name)
        if name == "systems":
            value = DEFAULT_SYSTEMS
        head = "%-22s %s" % (flag_for(name), fmt_number(value))
        if low is not None:
            head += "   range %s%s" % (fmt_number_span(low, high),
                                       " *" if varied else "")
        lines.append(head)
        lines += fill(source, indent="    ", width=72)
    return lines


def percent(fraction: float) -> str:
    """A fraction as a percentage with two significant figures."""
    return "%s%%" % sig(100.0 * fraction, 2)


def describe_kinematics(r: dict, canonical: bool = False) -> list:
    """Report lines on what stopping at every system costs in time."""
    k = r["kinematics"]
    if k["acceleration_m_s2"] is None:
        text = ("Stops and starts are treated as instant, since no "
                "acceleration is given. With an acceleration, in meters "
                "per second squared, of %s the mean hop would take %s "
                "longer (--acceleration)."
                % (", ".join(sig(ref["acceleration_m_s2"], 3)
                             for ref in k["reference"]),
                   ", ".join(percent(ref["extra_hop_fraction"])
                             for ref in k["reference"])))
    else:
        text = ("At an acceleration of %s (meters per second squared) a "
                "probe spends %s and %s parsecs of every hop speeding up "
                "and slowing down. The mean hop takes %s longer than at "
                "steady cruise speed."
                % (sig(k["acceleration_m_s2"], 3),
                   fmt_duration(k["ramp_years"], canonical, 3),
                   sig(k["ramp_parsec"], 3),
                   percent(k["extra_hop_fraction"])))
        if k["hops_reaching_cruise"] < 0.9995:
            text += (" Cruise speed is reached on only %s of the hops; the "
                     "rest are too short and turn around halfway."
                     % percent(k["hops_reaching_cruise"]))
    return fill(text)


def _reached_table(reached: dict, canonical: bool) -> list:
    """The rows 'share of systems seen, passes, time'."""
    unit = reached["unit"]
    lines = ["    %-30s %-9s %s" % ("systems seen at least once",
                                    unit + ("es" if unit == "pass" else "s"),
                                    "time")]
    for row in reached["rows"]:
        lines.append("    %-30s %-9s %s" % (
            "%.0f%%" % (100 * row["systems_seen"]),
            "never" if math.isinf(row["passes"]) else sig(row["passes"], 2),
            "not reached" if row["years"] is None
            else fmt_duration(row["years"], canonical)))
    return lines


def describe_reached(r: dict, canonical: bool = False) -> list:
    """Report lines on the share of the systems that the chosen way of
    running the survey reaches."""
    reached = r["reached"]
    sc = r["scenario"]
    slow, fast = max(reached["crossing_years"]), min(reached["crossing_years"])
    few, many = (min(reached["region_changes_per_pass"]),
                 max(reached["region_changes_per_pass"]))
    speeds = "%s to %s kilometers per second" % (
        sig(RANDOM_SPEEDS_M_S[0] / 1e3, 2), sig(RANDOM_SPEEDS_M_S[1] / 1e3, 2))
    seen = reached["seen_after_one_pass"]

    if sc["strategy"] in RECORDS_BY_SYSTEM:
        growth = r["hop_growth"]
        mixing = r["mixing"]
        wait = r["plane_wait"]
        crossings = (human_count(mixing["crossings"], 2)
                     if mixing["crossings"] >= 10
                     else sig(mixing["crossings"], 2))
        lines = fill(
            "Completion is recorded by system: a probe recognizes a system "
            "that was surveyed anywhere and passes it by. No visit is "
            "repeated, and the milestones count systems.")
        open_field = (
            "a probe goes to the nearest system not yet surveyed and never "
            "has to clear a volume, so its hops are %s times the spacing "
            "of the systems still to do, against %s for a route that "
            "clears a region (simulated)"
            % (sig(sc["path_factor"] * OPEN_FIELD_HOP / CLEARED_FIELD_HOP, 2),
               sig(sc["path_factor"], 2)))
        grown = ("a hop is %s times the first ones when half are done, %s "
                 "times at 90%%, and %s times on average"
                 % (sig(growth["0.5"], 3), sig(growth["0.9"], 3),
                    sig(r["hop_thinning"], 3)))
        if mixing["share"] < 0.05:
            lines += fill(
                "The stars barely move during a survey this short: a "
                "system gets %s of the way across one probe's share of the "
                "galaxy. The systems still to do stay where they were, "
                "each probe clears its own share, and the survey runs as "
                "it would by regions." % percent(mixing["crossings"]))
        elif mixing["share"] < 0.995:
            lines += fill(
                "The stars mix only in part during a survey this short: a "
                "system crosses one probe's share of the galaxy %s times. "
                "The figures are weighted, %s to %s, between two cases. "
                "With stars that stand still the survey runs as it would "
                "by regions. With stars that mix fully %s, and those "
                "systems thin out among the ones already done. Here %s."
                % (crossings, percent(1.0 - mixing["share"]),
                   percent(mixing["share"]), open_field, grown))
        else:
            lines += fill(
                "%s%s. The price is that those systems thin out. The stars "
                "mix long before the survey ends (a system crosses one "
                "probe's share of the galaxy %s times), so %s."
                % (open_field[0].upper(), open_field[1:], crossings, grown))
        if wait is not None and not wait["waits"]:
            lines += fill(
                "Waiting at the mid-plane does not work for a survey this "
                "short. A star takes about %s to swing up through the "
                "plane, down through it and back; the survey is over after "
                "%s such swings, and waiting pays only from %s on "
                "(simulated). The probes go to the systems instead, as "
                "with --strategy systems."
                % (fmt_duration(wait["swing_years"], canonical, 2),
                   sig(wait["swings"], 2), sig(PLANE_SWINGS_NEEDED, 2)))
        elif r["plane_left_at_half"] is not None:
            lines += fill(
                "The probes wait in a thin layer at the mid-plane of the "
                "disc and take each system as it passes through; a star "
                "swings up through the plane, down through it and back in "
                "about %s, %s times during the survey. Systems are closest "
                "together there: the first hops are %s parsecs, against %s "
                "for a fleet spread like the systems. But a system that "
                "swings far above and below the plane is rarely near it, "
                "and such systems are left for last: when half of all "
                "systems are done, only %s of those near the mid-plane are "
                "still to do. That uses up the head start. Half of the "
                "systems are reached sooner than by a fleet spread like "
                "the systems (--strategy systems); 90%% and 99%% are "
                "reached at the same time, within three percent in "
                "simulation."
                % (fmt_duration(wait["swing_years"], canonical, 2),
                   sig(wait["swings"], 2), sig(r["hop_parsec"], 3),
                   sig(r["hop_parsec"]
                       * r["galaxy"]["mean_spacing_at_large_pc"]
                       / r["galaxy"]["mean_spacing_pc"], 3),
                   percent(r["plane_left_at_half"])))
        elif (sc["strategy"] == "systems" and mixing["share"] >= 0.995
              and r["galaxy"]["model"] != "uniform"):
            lines += fill(
                "The probes stay spread through the disc like its systems. "
                "Waiting at the mid-plane instead (--strategy "
                "systems-midplane) brings the first half of the systems "
                "sooner and the rest no sooner.")
        lines += fill(
            "The specification records completion by region. This needs a "
            "record per system, compact enough to tell it apart from every "
            "other, that every archive station holds.")
        return lines

    if sc["strategy"] == "sweep-line":
        line = reached["line"]
        whole = line["share_of_systems"] >= 1.0 - 1e-12
        text = (
            "The disc turns, so every %ssystem crosses a line held from "
            "the center to the rim once per turn (%s at the rim). Systems "
            "cross it at %s a year, %s times what the fleet can survey, so "
            "the fleet staffs a stretch of the line at a time, each for "
            "one turn, working inward. Stars also swing in and out by "
            "about a tenth of their distance from the center: some cross "
            "outside the staffed stretch every time and are missed, others "
            "are met twice. One sweep of the line reaches %s of %s."
            % ("" if whole else "disc ",
               fmt_duration(line["rim_turn_years"], canonical),
               human_count(line["crossings_per_year"], 2),
               sig(1.0 / line["staffed_share"], 2)
               if line["staffed_share"] < 1.0 else "not more than",
               percent(sc["depth"] * (1.0 - line["missed_per_sweep"])),
               "the systems" if whole else "the disc systems"))
        if not whole:
            text += (
                " The bulge does not turn in step; it is surveyed by "
                "regions, as in the specification. Together one sweep "
                "reaches %s of all systems, and %s of its visits go to "
                "systems already seen."
                % (percent(seen), percent(reached["repeat_visit_share"])))
        lines = fill(text) + _reached_table(reached, canonical)
        lines += fill(
            "Staffing the whole line at once would take %s probes. Moving "
            "the line against the rotation brings the stars past sooner, "
            "but in proportion more of them per year, so this fleet could "
            "staff only a shorter stretch. In simulation that changes "
            "what a sweep reaches by a few percent of the systems, up or "
            "down, and it shortens the sweep only where the fleet would "
            "otherwise be held up by the turning of the disc. It is not "
            "modeled here."
            % human_count(line["probes_to_staff_all"], 2))
        lines += fill(
            "The archive layout, the staleness and the side trips in this "
            "report still describe a fleet spread over the disc; along a "
            "line they would be smaller. A sweep is counted as taking as "
            "long as one pass; a real schedule cannot keep every probe "
            "busy between stretches and runs 5 to 15 percent longer in "
            "simulation.")
        return lines

    if seen >= 0.995 * sc["depth"]:
        return fill(
            "Stars barely move during a survey this short: at %s a system "
            "needs %s to cross one region, so it changes region %s times at "
            "most during the pass, and one pass reaches %s%% of the systems."
            % (speeds, fmt_span(fast, slow, canonical), sig(many, 2),
               sig(100.0 * seen, 3)))
    lines = fill(
        "A region is a volume, and completion is recorded by region. At "
        "%s a system crosses one region in %s, so it changes region %s to "
        "%s times during one pass. Which systems a pass meets is therefore "
        "a matter of chance: one pass over every region reaches %s of the "
        "systems, and %s of its visits go to systems already seen."
        % (speeds, fmt_span(fast, slow, canonical), human_count(few, 2),
           human_count(many, 2), percent(seen),
           percent(reached["repeat_visit_share"])))
    lines += _reached_table(reached, canonical)
    lines += fill(
        "A further pass needs the completion records of the one before to "
        "lapse. As the specification stands a finished region stays "
        "finished, and the fleet stops after one pass. Nothing lets a probe "
        "recognize a system that was surveyed in another region.")
    return lines


def describe_strategies(r: dict, canonical: bool = False) -> list:
    """Every way of running the survey side by side, for this scenario."""
    lines = []
    for row in r["strategies"]:
        if row["strategy"] in RECORDS_BY_SYSTEM:
            note = "every visit is to a new system"
        else:
            note = "one %s reaches %s" % (
                "sweep" if row["strategy"] == "sweep-line" else "pass",
                percent(row["seen_after_one_pass"]))
        if row["strategy"] == r["strategy"]:
            note += " (this run)"
        lines.append("  %-18s %-20s %s" % (
            row["strategy"],
            "not reached" if row["years_to_99_percent"] is None
            else fmt_duration(row["years_to_99_percent"], canonical),
            note))
    lines += fill(
        "The two that record by system finish together. Waiting at the "
        "mid-plane brings the first half of the systems sooner, not the "
        "last.")
    return lines


def describe_left_out(r: dict, canonical: bool = False) -> list:
    """The caveats, each with its size for this scenario."""
    out = r["left_out"]
    gal = r["galaxy"]
    balance = (
        "Balance. The milestones assume every probe ends with an equal "
        "share, as if work were handed over at no cost. If each probe "
        "kept to the systems nearest its seed, with seeds scattered at "
        "random through a uniform disc, %s would be done at the nominal "
        "time and reaching 99%% would take %s times as long (simulated)."
        % (percent(UNBALANCED_DONE_AT_NOMINAL_TIME),
           sig(UNBALANCED_TIME_FOR_99_PERCENT, 2)))
    if gal["model"] == "exponential":
        balance += (
            " In this galaxy model the center holds %s times as many "
            "systems per unit of disc area as the average, so seeds spread "
            "evenly over the area would leave the central probes with that "
            "many times the mean load." % sig(out["central_load_factor"], 2))
    balance += (" Moving work between probes is what the archives are for, "
                "and it is not modeled.")
    duplication = (
        "Duplication. The duplicated-work fraction is a rough formula (see "
        "--explain), not derived from the region-selection rule: it treats "
        "every choice of a region as an independent draw and holds the "
        "case without archives at its ceiling by decree.")
    low, high = out["drift_out_shares"]
    deep = (
        "Deep time. The survey lasts %s turns of the galaxy at half the "
        "disc radius, and two points on neighboring orbits there drift "
        "apart by their own separation every %s, so the archive network "
        "does not hold still."
        % (sig(out["turns_at_half_radius"], 2),
           fmt_duration(out["shear_years"], canonical)))
    drift = (fmt_duration(r["region_cycle_years"], canonical),
             sig(RANDOM_SPEEDS_M_S[0] / 1e3, 2),
             sig(RANDOM_SPEEDS_M_S[1] / 1e3, 2), percent(low), percent(high))
    if r["strategy"] == "regions":
        deep += (
            " Regions are fixed volumes and the stars move through them: "
            "while one region is surveyed (%s) the random motion of stars, "
            "%s to %s kilometers per second, replaces %s to %s of its "
            "systems." % drift)
        deep += (
            " In the Galactic Standard Frame, which turns with one beacon, "
            "stars at other distances from the center also stream through, "
            "at up to the orbital speed of %s kilometers per second, which "
            "replaces the whole content of a region in %s. A finished "
            "volume does not stay finished; \"Systems reached\" above "
            "gives what that costs."
            % (sig(ROTATION_SPEED_M_S / 1e3, 2),
               fmt_duration(r["reached"]["stream_crossing_years"],
                            canonical)))
    else:
        deep += (
            " The stars move as well: in the time one region takes (%s) "
            "their random motion, %s to %s kilometers per second, replaces "
            "%s to %s of the systems in a volume of that size." % drift)
    deep += (" About %s as many systems as are counted today form during "
             "the survey." % percent(out["new_system_share"]))
    scattering = (
        "Scattering. Counted as one uninterrupted cruise, although "
        "Physical Layer 6.1 has probes refuel at stars. A stop every %s "
        "would add about %s stays, %s in all."
        % (fmt_duration(STORED_ENERGY_LEG_YEARS, canonical, 1),
           sig(out["scattering_stops"], 2),
           fmt_duration(out["scattering_stop_years"], canonical)))
    lines = []
    for text in (balance, duplication, deep, scattering):
        lines += fill(text)
    return lines


def describe_losses(r: dict, canonical: bool = False) -> list:
    """Report lines on how many probes the survey can afford to lose."""
    a = r["attrition"]
    d = r["distance"]
    path = (si_quantity(d["per_probe_m"], "meter") if canonical
            else "%s light-years" % human_count(d["per_probe_m"]
                                                / LIGHT_YEAR_M))
    stops = human_count(r["visited_per_probe"]
                        * (1.0 + r["duplication_fraction"]))
    if not a["active"]:
        text = ("No probe is assumed to be lost, over %s and %s stops per "
                "probe." % (path, stops))
    elif a["completed_fraction"] < 1.0:
        text = ("At a loss rate of %s per year the fleet runs out with %s "
                "of the survey done."
                % (sig(a["rate_per_year"], 2),
                   percent(a["completed_fraction"])))
    else:
        text = ("At a loss rate of %s per year %s of the fleet is still "
                "working when the survey ends, after %s and %s stops per "
                "probe." % (sig(a["rate_per_year"], 2),
                            percent(a["fleet_left_at_end"]), path, stops))
    text += (" The survey can finish only if the loss rate stays below %s "
             "per year, that is, if a probe lasts longer than %s on "
             "average. Above that rate the fleet runs out first: at twice "
             "the rate with about half the survey done."
             % (sig(a["threshold_per_year"], 2),
                fmt_duration(a["mean_life_needed_years"], canonical)))
    lines = fill(text)
    lines += fill("Not modeled: records lost between deposits, and the "
                  "travel needed to take over the work of a lost probe.")
    return lines


def describe_propellant(r: dict, canonical: bool = False) -> list:
    """Report lines on the propellant every stop needs."""
    sc = r["scenario"]
    p = r["propellant"]
    cases = [(p["exhaust_speed_c"], p["mass_ratio_per_stop"], None)]
    cases += [(ref["exhaust_speed_c"], ref["mass_ratio_per_stop"],
               ref["label"]) for ref in p["reference"]
              if ref["exhaust_speed_c"] != p["exhaust_speed_c"]]
    labels = {ref["exhaust_speed_c"]: ref["label"] for ref in p["reference"]}
    parts = []
    for speed, ratio, label in cases:
        label = label or labels.get(speed)
        parts.append("%s times its empty mass at an exhaust speed of %s c%s"
                     % (human_count(ratio, 2), sig(speed, 3),
                        " (%s)" % label if label else ""))
    text = ("Every visited system costs a velocity change of twice the "
            "cruise speed, %s c, or %s c per probe over the survey. To pay "
            "for it a probe must leave each system weighing %s."
            % (sig(p["velocity_change_per_stop_c"], 3),
               human_count(p["velocity_change_per_probe_c"], 2),
               ", or ".join(parts)))
    if p["refuel_years_per_stop"] > 0:
        text += (" Gathering that propellant adds %s to every stay, which "
                 "is then %s."
                 % (fmt_duration(p["refuel_years_per_stop"], canonical, 3),
                    fmt_duration(p["stay_years_per_system"], canonical, 3)))
    else:
        text += (" The stay of %s per system is not lengthened for this"
                 % fmt_duration(sc["dwell_years"], canonical, 3))
        text += ("; a faster cruise is therefore optimistic "
                 "(--refuel-years)."
                 if p["mass_ratio_per_stop"] > 10 else " (--refuel-years).")
    return fill(text)


def describe_galaxy(r: dict) -> list:
    """Header lines saying which workload input was authoritative and
    what followed from it."""
    gal = r["galaxy"]
    sc = r["scenario"]
    count = human_count(gal["systems"])
    if gal["source"] == "count" and gal["model"] == "exponential":
        text = ("%s star systems, the input the densities follow from: "
                "%.0f%% in a disc that thins outward (scale length %.3g, "
                "thickness %.3g kiloparsecs), %.0f%% in a central bulge"
                % (count, 100 * (1 - sc["bulge_fraction"]),
                   sc["scale_length_kpc"], sc["disc_thickness_kpc"],
                   100 * sc["bulge_fraction"]))
    elif gal["source"] == "count":
        text = ("%s star systems, the input the density follows from, "
                "spread evenly through the disc: %.3g per cubic parsec"
                % (count, gal["uniform_density"]))
    elif gal["source"] == "density":
        text = ("a uniform disc at %.3g star systems per cubic parsec, as "
                "given; the count follows from the disc volume: %s systems"
                % (gal["uniform_density"], count))
    else:
        ratio = gal["systems"] / gal["systems_implied_by_density"]
        text = ("%s star systems at %.3g per cubic parsec, both as given. "
                "They do not describe the same disc: that density fills "
                "it with %s systems, %.3g times %s than the count"
                % (count, gal["uniform_density"],
                   human_count(gal["systems_implied_by_density"]),
                   ratio if ratio >= 1 else 1 / ratio,
                   "fewer" if ratio >= 1 else "more"))
    lines = _wrap("Galaxy:", text)
    pct = r["hop_percentiles_parsec"]
    # Where the hops grow during the survey these are the first ones.
    hop = "first hops" if r["hop_thinning"] > 1.0 else "hop"
    if gal["model"] == "exponential":
        lines += _wrap("", "-> %s between systems %.3g parsecs on average; "
                           "half are below %.3g, nine in ten between %.3g "
                           "and %.3g"
                       % (hop, r["hop_parsec"], pct["50"], pct["5"],
                          pct["95"]))
    else:
        lines += _wrap("", "-> %s between systems %.3g parsecs"
                       % (hop, r["hop_parsec"]))
    return lines


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
    for line in describe_galaxy(r):
        add(line)
    add("Workload:   survey depth %.3g -> %s systems per probe,"
        % (sc["depth"], human_count(r["visited_per_probe"])))
    add("            %.3g years per system%s"
        % (r["per_system_years"],
           " on average" if r["hop_thinning"] > 1.0 else ""))
    for line in _wrap("Archives:", "%s - %s" % (layout["name"],
                                                layout["description"])):
        add(line)
    for line in _wrap("", "(%s)" % layout["spec_note"]):
        add(line)
    for line in _wrap("Strategy:", "%s - %s" % (r["strategy"],
                                                STRATEGIES[r["strategy"]])):
        add(line)
    add("")
    if r["fleet_exhausted"]:
        add("HEADLINE:   the survey never finishes (fleet exhausted)")
    else:
        # Two significant figures: the inputs do not support a third.
        add("HEADLINE:   full survey in about %s"
            % fmt_years(r["total_years"], canonical, digits=2))
    u = r.get("uncertainty")
    if u:
        pct = u["percentiles_years"]
        text = ("5 to 95 percent interval: %s; median %s (%s seeded draws "
                "over the input ranges listed below)"
                % (fmt_span(pct["5"], pct["95"], canonical),
                   fmt_duration(pct["50"], canonical),
                   format(u["draws"], ",")))
    else:
        text = ("no input ranges were varied; add --uncertainty for the "
                "5 to 95 percent interval")
    for line in _wrap("", text):
        add(line)
    reached = r["reached"]
    if reached["seen_after_one_pass"] < 0.995 * sc["depth"]:
        text = ("that is one sweep of the line from the rim to the center; "
                "it" if r["strategy"] == "sweep-line" else
                "that is one pass over every region; stars drift between "
                "regions meanwhile, so it")
        for line in _wrap("", "%s reaches about %s of the systems (see "
                              "Systems reached)"
                          % (text, percent(reached["seen_after_one_pass"]))):
            add(line)
    if r["scale_estimate"] and not r["fleet_exhausted"]:
        for line in _wrap("", "a scale estimate only: past %s the galaxy "
                              "itself turns, shears and forms new stars, "
                              "which is not modeled (see Caveats)"
                          % fmt_duration(SCALE_ESTIMATE_YEARS, canonical, 1)):
            add(line)
    if r["attrition"]["completed_fraction"] < 1.0:
        add("            WARNING: attrition exhausts the fleet at %.1f%%"
            " completion" % (100 * r["attrition"]["completed_fraction"]))
    add("")
    add("Phase breakdown")
    add("-" * 60)
    total = r["total_years"]
    for label, key in [("scattering phase (Physical Layer 4.5)",
                        "dispersal_years"),
                       ("survey travel + dwell", "survey_work_years"),
                       ("duplicated work (stale knowledge)",
                        "duplicated_work_years"),
                       ("archive deposit detours", "archive_detours_years"),
                       ("waiting for the disc to turn", "line_wait_years")]:
        y = ph[key]
        if key == "line_wait_years" and y == 0:
            continue
        share = ("%5.1f%%" % (100 * y / total)
                 if total and not math.isinf(total) else "     ")
        add("  %-42s %s  %s" % (label, share, fmt_years(y, canonical)))
    if not r["dispersal"]["covers_any_start"]:
        for line in fill(
                "The scattering allowance of %s is shorter than the disc "
                "diameter (%s), the longest leg a start at the rim would "
                "need. It only holds if the starting point is known, which "
                "the plan rules out."
                % (fmt_kiloparsecs(r["dispersal"]["allowance_kpc"],
                                   canonical),
                   fmt_kiloparsecs(r["dispersal"]["diameter_kpc"],
                                   canonical))):
            add(line)
    add("")
    add("Milestones (share of %s)"
        % {"regions": "regions surveyed", "line": "the line swept",
           "systems": "systems surveyed"}[r["milestones_count"]])
    add("-" * 60)
    for m in r["milestones"]:
        add("  %4.0f%%   %s" % (100 * m["fraction"],
                                fmt_years(m["years"], canonical, digits=2)))
    add("")
    add("Systems reached (%s)"
        % {"regions": "regions are fixed volumes; stars drift through",
           "line": "a line held while the disc turns past it",
           "systems": "completion recorded by system"}[r["milestones_count"]])
    add("-" * 60)
    for line in describe_reached(r, canonical):
        add(line)
    add("")
    add("Ways to run the survey (--strategy), until 99% of systems are seen")
    add("-" * 60)
    for line in describe_strategies(r, canonical):
        add(line)
    if u:
        add("")
        for line in render_ranges(u, canonical):
            add(line)
    add("")
    add("Distance traveled")
    add("-" * 60)
    d = r["distance"]
    add("  per probe:   %s" % fmt_meters(d["per_probe_m"], canonical))
    add("  fleet total: %s" % fmt_meters(d["fleet_m"], canonical))
    add("")
    add("Fleet losses")
    add("-" * 60)
    for line in describe_losses(r, canonical):
        add(line)
    add("")
    add("Stops, starts and propellant")
    add("-" * 60)
    for line in describe_kinematics(r, canonical):
        add(line)
    for line in describe_propellant(r, canonical):
        add(line)
    add("")
    add("Coordination traffic (optical links, Physical Layer 2.2)")
    add("-" * 60)
    c = r["comms"]
    add("  wire messages per probe:  %s   fleet: %s"
        % (human_count(c["messages_per_probe"]),
           human_count(c["fleet_messages"])))
    if c["messages_per_probe"] == 0:
        add("  no archive points, so no messages are sent")
    else:
        hours = c["link_seconds_per_message"] / 3600.0
        text = ("link time per message: %s at %s bits per second."
                % ("%s hours" % sig(hours, 2) if hours < 48
                   else "%s days" % sig(hours / 24.0, 2),
                   sig(c["link_rate_bps"], 2)))
        if c["link_distance_m"] is None:
            text += (" Records are handed over at the unattended boxes "
                     "themselves, at close range, so the rate of the link "
                     "budget is used as it stands.")
        else:
            text += (" The link budget gives %s bits per second at its "
                     "reference distance of %s; the rate falls with the "
                     "square of the distance, here the %s between archive "
                     "stations."
                     % (sig(sc["bitrate_bps"], 2),
                        fmt_kiloparsecs(LINK_REFERENCE_M / KPC_M, canonical),
                        fmt_kiloparsecs(c["link_distance_m"] / KPC_M,
                                        canonical)))
        for line in fill(text):
            add(line)
        share = (c["link_years_per_probe"] / r["total_years"]
                 if math.isfinite(r["total_years"]) else 0.0)
        text = ("link time per probe: %s, %s. The wire form is the "
                "channel's admission ticket (Physical Layer 2.2)."
                % (fmt_years(c["link_years_per_probe"], canonical),
                   "negligible" if share < 1e-3
                   else "%s of the survey" % percent(share)))
        for line in fill(text):
            add(line)
    add("")
    add("Knowledge staleness and duplication")
    add("-" * 60)
    if r["staleness_infinite"]:
        add("  no shared archives: staleness unbounded, duplication at cap")
    else:
        add("  completion facts are up to %s old when a region is"
            % fmt_duration(r["staleness_years"], canonical, 3))
        add("  chosen, the sum of:")
        for name, years in r["staleness_parts_years"].items():
            add("    %-36s %s" % (_STALENESS_LABELS[name],
                                  fmt_duration(years, canonical, 3)))
    add("  duplicated-work fraction: %.3g (cap %.2g)"
        % (r["duplication_fraction"], sc["dup_cap"]))
    if r["duplication_capped"]:
        add("  the estimate sits at its ceiling: with this few regions per")
        add("  probe (%.3g) the formula is outside its range, so the true"
            % r["regions_per_probe"])
        add("  duplicated share is not known from this model")
    if r["region_shrunk"]:
        add("  each probe's share (%s systems) is smaller than one region"
            % human_count(r["visited_per_probe"]))
        add("  (%s systems), so the share itself is treated as the region"
            % human_count(sc["region_systems"]))
    if r["unused_inputs"]:
        add("")
        add("Inputs given but not used in this run")
        add("-" * 60)
        for item in r["unused_inputs"]:
            for line in fill("%s: %s" % (flag_for(item["input"]),
                                         item["reason"]), indent="    ",
                             first="  "):
                add(line)
    add("")
    g = r["geometry"]
    add("Fleet geometry for this scenario (Physical Layer section 1)")
    add("-" * 60)
    add("  mean probe spacing:        %s"
        % fmt_kiloparsecs(g["spacing_kpc"], canonical))
    add("                             (%s on a lattice with six neighbors)"
        % fmt_kiloparsecs(g["lattice_spacing_kpc"], canonical))
    add("  light time per spacing:    %s"
        % fmt_duration(g["light_years_per_spacing"], canonical, 3))
    add("  probe transit per spacing: %s"
        % fmt_duration(g["transit_years_per_spacing"], canonical, 3))
    add("  consolidation cadence:     %s, %.2f of a probe transit"
        % (fmt_duration(sc["consolidation_years"], canonical, 3),
           g["cadence_in_transits"]))
    low, high = g["relay_reach_spacings"]
    hops_low, hops_high = g["useful_relay_hops"]
    add("  relay reach: a relayed fact stays ahead of the archives for one")
    add("  to two consolidation cycles; in that time a probe covers %.2f to"
        % low)
    add("  %.2f probe spacings, so %s useful. The specification"
        % (high, ("%d relay hop is" % hops_low if hops_low == hops_high == 1
                  else "%d relay hops are" % hops_low
                  if hops_low == hops_high
                  else "%d to %d relay hops are" % (hops_low, hops_high))))
    add("  fixes the limit at %d (Physical Layer section 4.3)."
        % g["spec_hop_limit"])
    add("  Cold vaults (the third archive tier) change how soon results can")
    add("  be assembled, never the survey pace.")
    add("")
    add("Caveats")
    add("-" * 60)
    for line in describe_left_out(r, canonical):
        add(line)
    return "\n".join(lines)


_PROFILE_FRACTIONS = (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)


def explain_galaxy(r: dict) -> list:
    """Formula lines for the galaxy model, with numbers substituted."""
    gal = r["galaxy"]
    sc = r["scenario"]
    if gal["model"] == "uniform":
        lines = ["galaxy: one density throughout a disc of radius %.3g and "
                 "thickness %.3g kiloparsecs"
                 % (sc["disc_radius_kpc"], sc["disc_thickness_kpc"]),
                 "  disc volume = pi x radius^2 x thickness = %.4g cubic "
                 "parsecs" % gal["slab_volume_pc3"]]
        if gal["source"] == "count":
            lines.append("  density = systems / volume = %.4g / %.4g = %.4g "
                         "per cubic parsec"
                         % (gal["systems"], gal["slab_volume_pc3"],
                            gal["uniform_density"]))
        elif gal["source"] == "density":
            lines.append("  systems = density x volume = %.4g x %.4g = %.4g"
                         % (gal["uniform_density"], gal["slab_volume_pc3"],
                            gal["systems"]))
        else:
            lines.append("  systems = %.4g and density = %.4g per cubic "
                         "parsec, both as given"
                         % (gal["systems"], gal["uniform_density"]))
            lines.append("  (density x volume would be %.4g systems)"
                         % gal["systems_implied_by_density"])
        lines.append("  mean spacing = density^(-1/3) = %.4g parsecs"
                     % gal["mean_spacing_pc"])
        return lines
    xm = gal["disc_radius_pc"] / gal["scale_length_pc"]
    lines = [
        "galaxy: %.4g star systems (the input; densities follow from it)"
        % gal["systems"],
        "disc: %.4g systems, density n0 x exp(-R / L) x exp(-|z| / h) out "
        "to R = %.3g" % (gal["disc_systems"], sc["disc_radius_kpc"]),
        "  L = %.3g and h = thickness / 2 = %.3g kiloparsecs"
        % (sc["scale_length_kpc"], sc["disc_thickness_kpc"] / 2),
        "  n0 = disc systems / (2 pi L^2 x g(x) x 2 h), x = R / L = %.4g,"
        % xm,
        "       g(x) = 1 - exp(-x) x (1 + x) = %.4g" % _g1(xm),
        "     = %.4g per cubic parsec at the center"
        % gal["disc_central_density"],
    ]
    plane = gal["parts"][0]["kind"] == "disc-plane"
    if plane:
        lines += [
            "  taken at the mid-plane, where the density is n0 x exp(-R / L):",
            "  mean spacing over disc systems"
            " = n0^(-1/3) x (9/4) x g(2x/3) / g(x)",
        ]
    else:
        lines += [
            "  mean spacing over disc systems"
            " = n0^(-1/3) x (27/8) x g(2x/3) / g(x)",
        ]
    lines.append("     = %.4g parsecs" % gal["parts"][0]["mean_spacing_pc"])
    if gal["bulge_sigma_pc"]:
        lines += [
            "bulge: %.4g systems, density nb x exp(-r^2 / (2 s^2)),"
            % gal["bulge_systems"],
            "  s = half-count radius / 1.538 = %.4g parsecs"
            % gal["bulge_sigma_pc"],
            "  nb = bulge systems / ((2 pi)^(3/2) x s^3) = %.4g per cubic "
            "parsec" % gal["bulge_central_density"],
            "  mean spacing over bulge systems = nb^(-1/3) x (3/2)^(3/2)"
            " = %.4g parsecs" % gal["parts"][1]["mean_spacing_pc"],
        ]
    lines.append("mean spacing over all systems = %.4g parsecs"
                 % gal["mean_spacing_pc"])
    radius_kpc = sc["disc_radius_kpc"]
    lines.append("mid-plane density, systems per cubic parsec, at the "
                 "center, one third,")
    lines.append("two thirds and the full disc radius (%s kiloparsecs):"
                 % ", ".join("%.3g" % (frac * radius_kpc)
                             for frac in _PROFILE_FRACTIONS))
    lines.append("  " + ",  ".join(
        "%.3g" % midplane_density(gal, frac * radius_kpc * 1e3)
        for frac in _PROFILE_FRACTIONS))
    return lines


def render_explain(r: dict) -> str:
    sc = r["scenario"]
    ph = r["phases"]
    lines = [
        "FORMULAS WITH SUBSTITUTED VALUES",
        "=" * 60,
        "strategy: %s" % r["strategy"],
        "cruise speed  v = %.3g x speed of light = %.4g meters per second"
        % (sc["speed_c"], r["speed_m_per_s"]),
        "",
    ]
    lines += explain_galaxy(r)
    by_system = r["strategy"] in RECORDS_BY_SYSTEM
    lines += [""]
    if by_system:
        lines += [
            "inter-system hop, first ones = path_factor x %.3g / %.3g x "
            "depth^(-1/3)" % (OPEN_FIELD_HOP, CLEARED_FIELD_HOP),
            "    x mean spacing   (%.3g: nearest system not yet surveyed "
            "among" % OPEN_FIELD_HOP,
            "    drifting stars; %.3g: a route that clears a field of "
            "fixed points)" % CLEARED_FIELD_HOP,
            "  = %.3g x %.4g x %.3g^(-1/3) x %.4g parsecs"
            % (sc["path_factor"], OPEN_FIELD_HOP / CLEARED_FIELD_HOP,
               sc["depth"], r["galaxy"]["mean_spacing_pc"]),
        ]
    else:
        lines += [
            "inter-system hop = path_factor x depth^(-1/3) x mean spacing",
            "  = %.3g x %.3g^(-1/3) x %.4g parsecs"
            % (sc["path_factor"], sc["depth"],
               r["galaxy"]["mean_spacing_pc"]),
        ]
    lines += [
        "  = %.4g parsecs  ->  %.4g years at cruise speed"
        % (r["hop_parsec"],
           r["hop_parsec"] * PARSEC_M / r["speed_m_per_s"] / YEAR_S),
    ]
    k = r["kinematics"]
    if k["acceleration_m_s2"] is not None:
        lines += [
            "",
            "stop-and-go: a hop of length d takes d / v + v / a, or "
            "2 sqrt(d / a)",
            "  where d is below v^2 / a; with a = %.3g meters per second "
            "squared," % k["acceleration_m_s2"],
            "  v / a = %.4g years and v^2 / a = %.4g parsecs"
            % (k["ramp_years"], k["ramp_parsec"]),
            "  mean hop time over all systems = %.4g years (%.4g of the "
            "hops" % (r["hop_years"], k["hops_reaching_cruise"]),
            "  reach cruise speed)",
        ]
    lines += [
        "",
        "mass ratio per stop = exp(2 v / exhaust speed) = exp(2 x %.3g / "
        "%.3g) = %.4g" % (sc["speed_c"], sc["exhaust_speed_c"],
                          r["propellant"]["mass_ratio_per_stop"]),
        "stay per system = dwell + refuel years x (mass ratio - 1)",
        "  = %.4g + %.3g x %.4g = %.4g years"
        % (sc["dwell_years"], sc["refuel_years_per_mass"],
           r["propellant"]["mass_ratio_per_stop"] - 1.0,
           r["propellant"]["stay_years_per_system"]),
        "",
    ]
    if by_system:
        lines += [
            "hops where completion is recorded by system: the systems still "
            "to do",
            "  thin out, so a hop grows to %.3g first hops when half are "
            "done and" % r["hop_growth"]["0.5"],
            "  %.3g at nine tenths, %.3g on average; hop time averaged over "
            "the" % (r["hop_growth"]["0.9"], r["hop_thinning"]),
            "  survey = %.4g years" % r["hop_years_average"],
        ]
        lines += [
            "  a star crosses one probe's share of the galaxy (%.4g parsecs "
            "across)" % r["mixing"]["probe_share_side_parsec"],
            "  %.4g times during the survey; share of the mixed law = 1 - "
            "exp(-crossings)" % r["mixing"]["crossings"],
            "  = %.4g, the rest being a field of stars that stand still"
            % r["mixing"]["share"],
        ]
        if r["plane_wait"] is not None:
            lines += [
                "  one swing through the mid-plane and back = %.3g scale "
                "heights / %.3g" % (PLANE_SWING_IN_HEIGHTS,
                                    RANDOM_SPEEDS_M_S[0] / 1e3),
                "    kilometers per second = %.4g years; the survey lasts "
                "%.3g swings" % (r["plane_wait"]["swing_years"],
                                 r["plane_wait"]["swings"]),
                "    (waiting at the mid-plane is modeled from %.3g swings "
                "on)" % PLANE_SWINGS_NEEDED,
            ]
        if r["plane_left_at_half"] is not None:
            lines += [
                "  at the mid-plane, with y from 1 - (1 + y) exp(-y) = share "
                "done:",
                "    share left near the plane = exp(-y); distance in first "
                "hops",
                "    = 9/4 x g(2 y / 3); at half done, y = %.4g and %.4g is "
                "left" % (_plane_progress(0.5), r["plane_left_at_half"]),
            ]
        lines += [""]
    lines += [
        "time per system = hop time + stay = %.4g + %.4g = %.4g years"
        % (r["hop_years_average"], r["propellant"]["stay_years_per_system"],
           r["per_system_years"]),
        "",
        "systems per probe = total x depth / probes",
        "  = %.3g x %.3g / %s = %.4g"
        % (r["systems"], sc["depth"], format(sc["probes"], ","),
           r["visited_per_probe"]),
        "",
        "survey work = systems per probe x time per system = %.4g years"
        % ph["survey_work_years"],
        "",
        "region cycle = %.3g systems x %.4g years = %.4g years"
        % (r["region_systems"], r["per_system_years"],
           r["region_cycle_years"]),
        "regions per probe = %.4g" % r["regions_per_probe"],
        "",
        "knowledge staleness tau = %s"
        % ("unbounded (no archives)" if r["staleness_infinite"]
           else "the sum of delays that follow one another"),
    ]
    lines += ["  %-36s %.4g years" % (_STALENESS_LABELS[name], years)
              for name, years in r["staleness_parts_years"].items()]
    if not r["staleness_infinite"]:
        lines.append("  = %.4g years" % r["staleness_years"])
    lines += [
        "duplication fraction = min(cap, gain x (tau / region cycle)",
        "                           x neighbors / regions per probe)",
        "  = %.4g   (cap %.2g, gain %.2g, neighbors %d)"
        % (r["duplication_fraction"], sc["dup_cap"], sc["dup_gain"],
           sc["neighbors"]),
        "duplicated work = %.4g years" % ph["duplicated_work_years"],
        "",
        "scattering = allowed leg x margin / v",
        "  = %.4g kiloparsecs%s x %.3g / v = %.4g years"
        % (r["dispersal"]["leg_kpc"],
           " (the disc diameter)" if sc["dispersal_leg_kpc"] is None else "",
           sc["envelope_factor"], ph["dispersal_years"]),
        "archive detours = deposits x 2 x detour distance / v = %.4g years"
        % ph["archive_detours_years"],
        "",
        "highest loss rate at which the fleet still finishes: the rate "
        "L with",
        "  L x exp(L x scattering) x (work + duplication + detours) = 1",
        "  L = %.4g per year (a mean probe life of %.4g years)"
        % (r["attrition"]["threshold_per_year"],
           r["attrition"]["mean_life_needed_years"]),
        "",
        "TOTAL = scattering + work x (1 + duplication) + detours%s"
        % (" + wait for one turn of the rim"
           if ph["line_wait_years"] > 0 else ""),
        "      = %.4g years" % r["total_years"],
    ]
    if r.get("uncertainty"):
        lines += [""] + render_ranges(r["uncertainty"])
    if r["strategy"] == "sweep-line":
        line = r["reached"]["line"]
        lines += [
            "",
            "line held while the disc turns past it",
            "  systems crossing = surface density x orbital speed, summed "
            "along the line",
            "    = %.4g a year; the fleet can survey %.4g a year there"
            % (line["crossings_per_year"], line["capacity_per_year"]),
            "  staffed share of the line = %.4g; probes to staff all of "
            "it = %.4g" % (line["staffed_share"],
                           line["probes_to_staff_all"]),
            "  staffed width at each distance = fleet capacity / (surface "
            "density",
            "    x orbital speed); swing of a star = radial random speed x "
            "distance",
            "    / (sqrt(2) x orbital speed), counted %.3g times"
            % LINE_SWING_CALIBRATION,
            "  share of the line's systems missed by one sweep = %.4g"
            % line["missed_per_sweep"],
        ]
    lines += [""] + render_defaults()
    return "\n".join(lines)


def json_safe(value):
    """Copy of a result with every unbounded or undefined number replaced
    by None, so the output file is strict JavaScript Object Notation
    (which has no way to write infinity). The flag "fleet_exhausted"
    carries the meaning the missing number had."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


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

The report also says how sure the answer is, what every stop costs in
propellant, how many probes the survey can afford to lose, and which
effects the estimate leaves out, each with its size.

By default the fleet records which systems are done one by one and
waits for them at the mid-plane of the disc. The documents record
completion by region; --strategy regions gives the estimate for that.
"""

_EPILOG = """\
archive layouts (--archives NAME):
%s

ways to run the survey (--strategy NAME):
%s

what the output shows:
  A headline duration, a phase-by-phase breakdown, milestone times for
  half, ninety percent, ninety-nine percent, and all of the star systems
  (of the regions where completion is recorded by region, with the share
  of the systems that this reaches while they drift from region to
  region), every way of running the survey side by side, the distance
  traveled per probe and fleet-wide,
  message counts with their transmission time, and the assumptions the
  numbers rest on. Durations appear in years and also in seconds;
  distances in light-years and also in meters (one light-year is about
  9.46e15 meters; one parsec is about 3.26 light-years; one kiloparsec
  is one thousand parsecs).
  The headline is rounded to two digits, because the inputs do not
  support a third.

how sure the answer is (--uncertainty, or "ranges" in a scenario file):
  Most inputs are known only roughly. With --uncertainty the calculator
  redraws the uncertain inputs many times within their plausible ranges
  and prints, beside the headline, the middle outcome and the interval
  that holds nine draws in ten (the 5 to 95 percent interval), followed
  by a table of what each input does on its own. The draws are seeded,
  so a run can be repeated exactly. A scenario file can set its own
  ranges, which also switches this mode on:
      {"speed_c": 0.15,
       "ranges": {"systems": [5e10, 1.2e11],
                  "dwell_years": {"low": 1, "high": 1000, "scale": "log"}}}
  Mapping an input to null inside "ranges" leaves it fixed.
  --explain lists every default with its source and plausible range.

examples:
  python plan0_pace.py
      the default scenario: every star system, doctrine archive network
  python plan0_pace.py --archives stations-only --depth 0.1 --speed 0.2
      visit one system in ten, at double cruise speed, with staffed
      archive stations only
  python plan0_pace.py --explain
      print every formula with the numbers substituted in, then every
      default with its source and plausible range
  python plan0_pace.py --uncertainty
      add the interval that the plausible input ranges give
  python plan0_pace.py --strategy regions
      the specification as it stands; every report compares all the ways
      of running the survey
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
        epilog=_EPILOG % (preset_lines, "\n".join(
            "\n".join(fill(text, indent=" " * 21,
                           first="  %-18s " % name, width=78))
            for name, text in STRATEGIES.items())),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    g = p.add_argument_group("fleet and survey assumptions")
    g.add_argument("--probes", type=int, metavar="COUNT",
                   help="number of probes in the fleet (default 10000)")
    g.add_argument("--speed", type=float, metavar="FRACTION", dest="speed_c",
                   help="cruise speed as a fraction of the speed of light "
                        "(default 0.1; studied concepts span 0.05 to 0.2)")
    g.add_argument("--systems", type=float, metavar="COUNT",
                   help="total star systems in the galaxy; this count is "
                        "the input from which the densities and the "
                        "distances between systems follow (default 1e11)")
    g.add_argument("--galaxy-model", choices=GALAXY_MODELS, metavar="NAME",
                   dest="galaxy_model",
                   help="how the systems are spread: 'exponential' is a "
                        "disc that thins outward plus a central bulge; "
                        "'uniform' spreads the same count evenly through "
                        "the disc (default exponential)")
    g.add_argument("--stellar-density", type=float, metavar="NUMBER",
                   dest="stellar_density",
                   help="treat the galaxy as a uniform disc with this many "
                        "star systems per cubic parsec; the system count "
                        "is then the disc volume times this density, "
                        "unless --systems is given as well (no default: "
                        "normally the density follows from the count)")
    g.add_argument("--disc-radius", type=float, metavar="KILOPARSECS",
                   dest="disc_radius_kpc",
                   help="survey disc radius (default 15)")
    g.add_argument("--disc-thickness", type=float, metavar="KILOPARSECS",
                   dest="disc_thickness_kpc",
                   help="effective thickness of the disc of stars; in the "
                        "exponential disc the density falls off above and "
                        "below the mid-plane over half this distance "
                        "(default 0.7)")
    g.add_argument("--scale-length", type=float, metavar="KILOPARSECS",
                   dest="scale_length_kpc",
                   help="distance over which the density of the "
                        "exponential disc falls by a factor of about 2.7 "
                        "going outward (default 2.6)")
    g.add_argument("--bulge-fraction", type=float, metavar="FRACTION",
                   dest="bulge_fraction",
                   help="share of all star systems that sit in the central "
                        "bulge instead of the disc (default 0.15)")
    g.add_argument("--bulge-radius", type=float, metavar="KILOPARSECS",
                   dest="bulge_radius_kpc",
                   help="radius of the sphere that holds half of the "
                        "bulge's systems (default 1)")
    g.add_argument("--depth", type=float, metavar="FRACTION",
                   help="fraction of star systems each probe actually "
                        "visits; 1.0 means every system (default 1.0)")
    g.add_argument("--dwell", type=float, metavar="YEARS",
                   dest="dwell_years",
                   help="stay per visited system, covering both the survey "
                        "and refueling, since survey stops double as "
                        "refueling stops (default 10); with --refuel-years "
                        "the refueling is counted on top of it")
    g.add_argument("--path-factor", type=float, metavar="NUMBER",
                   dest="path_factor",
                   help="length of the route per visited system, as a "
                        "multiple of the mean distance between neighboring "
                        "systems: 1.0 is one mean distance per hop, 0.78 "
                        "is what always going to the nearest unvisited "
                        "system achieves, 0.70 is the shortest possible "
                        "route (default 0.78)")
    g.add_argument("--acceleration", type=float, metavar="NUMBER",
                   dest="acceleration_m_s2",
                   help="acceleration and braking of a probe in meters per "
                        "second squared; when given, every hop takes "
                        "longer by the time spent speeding up and slowing "
                        "down, and hops too short to reach cruise speed "
                        "are timed as such (no default: stops and starts "
                        "are instant)")
    g.add_argument("--exhaust-speed", type=float, metavar="FRACTION",
                   dest="exhaust_speed_c",
                   help="speed of the engine exhaust as a fraction of the "
                        "speed of light; together with the cruise speed "
                        "it sets how much propellant every stop needs "
                        "(default 0.089, the ideal limit for fusion of "
                        "deuterium and helium-3)")
    g.add_argument("--refuel-years", type=float, metavar="YEARS",
                   dest="refuel_years_per_mass",
                   help="years needed at a stop to gather propellant equal "
                        "to the probe's empty mass; when given, every stay "
                        "grows by this times the propellant the next hop "
                        "needs, so a faster cruise costs longer stops "
                        "(default 0: the stay is --dwell at any speed)")
    g.add_argument("--region-systems", type=float, metavar="COUNT",
                   dest="region_systems",
                   help="visited systems per completion-record region; sets "
                        "how often a probe deposits records (default 1000)")
    g.add_argument("--dispersal-leg", type=float, metavar="KILOPARSECS",
                   dest="dispersal_leg_kpc",
                   help="distance allowed for the initial scattering, "
                        "before any survey or message begins; the default "
                        "is the disc diameter, the longest leg possible "
                        "from any starting point, so that the wait does "
                        "not depend on where the fleet starts")
    g.add_argument("--envelope-factor", type=float, metavar="NUMBER",
                   dest="envelope_factor",
                   help="margin multiplier on the scattering distance "
                        "(default 1.0, since the default distance is "
                        "already the longest possible)")
    g.add_argument("--attrition", type=float, metavar="NUMBER",
                   dest="attrition_per_year",
                   help="fraction of the fleet lost per year to failures "
                        "(default 0)")

    g.add_argument("--strategy", choices=list(STRATEGIES), metavar="NAME",
                   help="way of running the survey; see the list below "
                        "(default systems-midplane; regions is the "
                        "specification as it stands)")

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
                   help="optical link speed in bits per second at the "
                        "reference distance of the specification's link "
                        "budget (default 0.5; the specification derives "
                        "0.1 to 1); the rate used falls with the square "
                        "of the distance between archive stations")
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
    g.add_argument("--neighbors", type=int, metavar="COUNT",
                   help="number of neighboring probes whose work a probe "
                        "could repeat by mistake (default 6)")

    g = p.add_argument_group("how sure the answer is")
    g.add_argument("--uncertainty", action="store_true",
                   help="vary the uncertain inputs over their plausible "
                        "ranges and print the 5 to 95 percent interval "
                        "and the middle outcome beside the headline, with "
                        "a table of what each input does alone")
    g.add_argument("--draws", type=int, metavar="COUNT",
                   help="number of random draws for the interval "
                        "(default %d)" % DEFAULT_DRAWS)
    g.add_argument("--seed", type=int, metavar="NUMBER",
                   help="starting number for the random draws; the same "
                        "number repeats the same draws (default %d)"
                        % DEFAULT_SEED)

    g = p.add_argument_group("input and output")
    g.add_argument("--scenario", metavar="FILE",
                   help="load assumptions from a file in JavaScript Object "
                        "Notation format; command-line flags override it")
    g.add_argument("--json", metavar="FILE", dest="json_out",
                   help="also write the full results, machine-readable, to "
                        "this file (JavaScript Object Notation format)")
    g.add_argument("--explain", action="store_true",
                   help="print every formula with the numbers substituted, "
                        "then every default with its source and "
                        "plausible range")
    g.add_argument("--canonical", action="store_true",
                   help="print durations only in seconds and distances only "
                        "in meters, the fleet's canonical units")
    g.add_argument("--list-presets", action="store_true",
                   help="list the archive layout presets and exit")
    return p


def load_inputs(args: argparse.Namespace) -> tuple:
    """The scenario and the input ranges (or None) exactly as the scenario
    file and the command line give them; flags override the file."""
    data = {}
    if args.scenario:
        with open(args.scenario, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if not isinstance(loaded, dict):
            raise ValueError("the scenario file must hold one object of "
                             "named values, not %s" % type(loaded).__name__)
        data.update(loaded)
    file_ranges = data.pop("ranges", None)
    for f in fields(Scenario):
        value = getattr(args, f.name, None)
        if value is not None:
            data[f.name] = value
    sc = Scenario.from_dict(data)
    ranges = builtin_ranges() if getattr(args, "uncertainty", False) else None
    if file_ranges is not None:
        ranges = dict(ranges or {})
        ranges.update(normalize_ranges(file_ranges))
    if ranges is not None:
        ranges = {name: spec for name, spec in ranges.items() if spec}
    return sc, ranges


def scenario_from_args(args: argparse.Namespace) -> Scenario:
    return load_inputs(args)[0]


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_presets:
        for name, preset in ARCHIVE_PRESETS.items():
            print("%-18s %s" % (name, preset["help"]))
        return 0
    try:
        sc, ranges = load_inputs(args)
        result = derive(sc)
        if ranges:
            result["uncertainty"] = run_uncertainty(
                sc, ranges,
                DEFAULT_DRAWS if args.draws is None else args.draws,
                DEFAULT_SEED if args.seed is None else args.seed)
        elif args.draws is not None or args.seed is not None:
            raise ValueError("--draws and --seed do nothing on their own; "
                             "add --uncertainty or ranges in the scenario "
                             "file")
    except (ValueError, OSError, ArithmeticError) as exc:
        # json.JSONDecodeError is a ValueError; ArithmeticError covers a
        # division by zero or overflow from inputs at the edge of range.
        print("error: %s" % (exc or type(exc).__name__), file=sys.stderr)
        return 2
    if args.explain:
        print(render_explain(result))
    else:
        print(render_report(result, canonical=args.canonical))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(json_safe(result), fh, indent=2, allow_nan=False)
            fh.write("\n")
        print("\nfull results written to %s" % args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
