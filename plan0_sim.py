#!/usr/bin/env python3
"""plan0_sim.py - a direct simulation of the survey phase of PLAN-0.

The pace calculator (plan0_pace.py) adds up averages. This program follows
single probes from system to system instead, for a fleet so large that each
probe has only about a hundred systems to itself. In that case the stars
hardly move while the survey lasts, so what decides the outcome is local:
where the probes start, which rule sends them on, and what each probe
knows of the work of its neighbors.

Standard library only. Every run is seeded and can be repeated exactly.
Run with --help for the manual.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import multiprocessing
import os
import random
import sys
import time

INF = math.inf

# ---------------------------------------------------------------------------
# One run
#
# Units. Lengths are in mean spacings between systems (their density is 1).
# Time is in the time a probe needs to cruise one spacing. `stay` is the
# stay per system in that unit, `light` the cruise speed over light speed.
# ---------------------------------------------------------------------------

RULES = {
    "roam": "a probe goes to the nearest system it does not know to be "
            "done, wherever that lies",
    "cells": "a probe keeps to its own cell (the systems nearer to its "
             "starting point than to any other probe's) and stops when "
             "that is done",
    "cells-roam": "a probe finishes its own cell first and then goes on "
                  "as under roam",
}

# What a probe knows of the work of the others comes from two sources,
# and a system counts as taken if either says so:
#   foresight   the share of the others' choices that the probe has worked
#               out in advance from the common rule (1 = all of them, the
#               moment they are made; 0 = none)
#   records     completion records, which reach the probe at light speed
#               plus the delay given here (math.inf = never)
#   announce    whether a probe also announces, at light speed, the system
#               it sets out for
# A probe always knows its own work and what it has run into.

SEEDINGS = {
    "points": "every probe starts at a point drawn at random",
    "lattice": "the probes start on a regular lattice (the probe count "
               "must be a cube number)",
    "centres": "every probe draws one of the seed regions at random and "
               "starts at its middle, together with the others that drew "
               "the same region",
}

DEFAULTS = dict(
    probes=8000,            # probes in the box
    per_probe=100.0,        # systems per probe
    stay=0.2,               # stay per system, in cruise times per spacing
    light=0.1,              # cruise speed over light speed
    rule="roam",
    foresight=0.0,          # share of the others' choices worked out
    records=0.0,            # extra age of a completion record; inf = never
    announce=False,         # are departures announced as well?
    seeding="points",
    region=1000.0,          # centres: systems per seed region
    absent=0.0,             # share of the probes lost before the survey
    absent_known=True,      # do the others know which probes are lost?
    twins=0.0,              # share of probes that share start and key
    repeat_stay=False,      # does a wasted visit cost the stay as well?
    drift=0.0,              # speed of the stars, in cruise speeds
    until=1.0,              # stop when this share of the systems is done
    seed=1,
)

LEVELS = ([round(0.01 * i, 2) for i in range(1, 100)]
          + [0.995, 0.999, 0.9999, 1.0])

_MIX = 0x9E3779B97F4A7C15
_MASK = (1 << 61) - 1


def _mixed(key: int, j: int) -> int:
    """A fixed scramble of a probe key and a system number."""
    return ((key ^ (j * _MIX)) * 2654435761) & _MASK


def simulate(config: dict) -> dict:
    """Run one box and return its outcome. `config` overrides DEFAULTS."""
    c = dict(DEFAULTS)
    unknown = set(config) - set(c)
    if unknown:
        raise ValueError("unknown setting(s): %s" % ", ".join(sorted(unknown)))
    c.update(config)
    rule, seeding = c["rule"], c["seeding"]
    if rule not in RULES or seeding not in SEEDINGS:
        raise ValueError("unknown rule or seeding")
    P = int(c["probes"])
    N = int(round(P * c["per_probe"]))
    if P < 1 or N < 1:
        raise ValueError("at least one probe and one system are needed")
    stay, light, delay = float(c["stay"]), float(c["light"]), float(c["records"])
    share = float(c["foresight"])
    if not 0.0 <= share <= 1.0 or delay < 0.0 or stay < 0.0 or light < 0.0:
        raise ValueError("foresight must lie between 0 and 1; delays, the "
                         "stay and the speed cannot be negative")
    told = delay < INF                  # do completion records arrive?
    announce = bool(c["announce"]) and told
    started = time.time()
    rng = random.Random(c["seed"])
    L = N ** (1.0 / 3.0)
    half = 0.5 * L

    xs = [rng.random() * L for _ in range(N)]
    ys = [rng.random() * L for _ in range(N)]
    zs = [rng.random() * L for _ in range(N)]
    drift = float(c["drift"])
    if drift > 0.0:
        x0, y0, z0 = xs[:], ys[:], zs[:]
        vx = [rng.gauss(0.0, drift) for _ in range(N)]
        vy = [rng.gauss(0.0, drift) for _ in range(N)]
        vz = [rng.gauss(0.0, drift) for _ in range(N)]

    # ---- where the probes start -------------------------------------------
    if seeding == "points":
        seeds = [(rng.random() * L, rng.random() * L, rng.random() * L)
                 for _ in range(P)]
    elif seeding == "lattice":
        m = round(P ** (1.0 / 3.0))
        if m ** 3 != P:
            raise ValueError("a lattice needs a cube number of probes")
        ox, oy, oz = rng.random(), rng.random(), rng.random()
        seeds = [(((a + ox) / m * L) % L, ((b + oy) / m * L) % L,
                  ((d + oz) / m * L) % L)
                 for a in range(m) for b in range(m) for d in range(m)]
    else:
        m = max(1, round((N / float(c["region"])) ** (1.0 / 3.0)))
        seeds = [((rng.randrange(m) + 0.5) / m * L,
                  (rng.randrange(m) + 0.5) / m * L,
                  (rng.randrange(m) + 0.5) / m * L) for _ in range(P)]
    keys = [rng.getrandbits(60) for _ in range(P)]
    for i in range(int(c["twins"] * P / 2.0)):
        seeds[2 * i + 1] = seeds[2 * i]
        keys[2 * i + 1] = keys[2 * i]
    gone = [rng.random() < c["absent"] for _ in range(P)]
    phantoms = share > 0.0 and not c["absent_known"]

    px = [s[0] for s in seeds]
    py = [s[1] for s in seeds]
    pz = [s[2] for s in seeds]

    # ---- the systems on a grid ---------------------------------------------
    # About three listed systems per cell; rebuilt, coarser, as they go.
    ng, cw, rmax = 1, L, 1
    cells = [[]]
    cell_of = [0] * N
    flats = {}

    def fill_grid(members):
        nonlocal ng, cw, rmax, cells
        ng = max(1, int(L / (3.0 * L ** 3 / max(1, len(members)))
                        ** (1.0 / 3.0)))
        cw = L / ng
        rmax = ng // 2 + 1
        cells = [[] for _ in range(ng * ng * ng)]
        flats.clear()
        for j in members:
            k = (int(xs[j] / cw) % ng
                 + ng * (int(ys[j] / cw) % ng + ng * (int(zs[j] / cw) % ng)))
            cell_of[j] = k
            cells[k].append(j)
    in_grid = list(range(N))
    fill_grid(in_grid)
    built = listed = N          # systems on the grid at the last rebuild, now

    shells = {}

    def shell(r):
        got = shells.get(r)
        if got is None:
            span = range(-r, r + 1)
            got = [(dx, dy, dz) for dx in span for dy in span for dz in span
                   if max(abs(dx), abs(dy), abs(dz)) == r]
            shells[r] = got
        return got

    def flat(r):
        got = flats.get(r)
        if got is None:
            got = flats[r] = [dx + ng * (dy + ng * dz)
                              for dx, dy, dz in shell(r)]
        return got

    claim_by = [-1] * N         # the probe that surveyed the system
    done_t = [INF] * N          # when its survey was complete
    chosen_by = [-1] * N        # the probe that first set out for it
    chosen_t = [INF] * N
    if announce:
        fx = [0.0] * N          # where that probe set out from
        fy = [0.0] * N
        fz = [0.0] * N
    met = [None] * P            # systems a probe found done on arrival

    # ---- cells: the systems nearest each starting point ---------------------
    use_cells = rule != "roam"
    in_cell = [use_cells] * P   # still working inside its own cell?
    own = None
    if use_cells:
        sg = max(1, int(L / (L ** 3 / P) ** (1.0 / 3.0)))
        sw = L / sg
        scells = {}
        for p in range(P):
            scells.setdefault(
                (int(px[p] / sw) % sg, int(py[p] / sw) % sg,
                 int(pz[p] / sw) % sg), []).append(p)
        own = [[] for _ in range(P)]
        srmax = sg // 2 + 1
        for j in range(N):
            x, y, z = xs[j], ys[j], zs[j]
            ix, iy, iz = int(x / sw) % sg, int(y / sw) % sg, int(z / sw) % sg
            best, bp, r = INF, -1, 0
            while True:
                for dx, dy, dz in shell(r):
                    lst = scells.get(((ix + dx) % sg, (iy + dy) % sg,
                                      (iz + dz) % sg))
                    if not lst:
                        continue
                    for p in lst:
                        ax = abs(px[p] - x)
                        ay = abs(py[p] - y)
                        az = abs(pz[p] - z)
                        if ax > half:
                            ax = L - ax
                        if ay > half:
                            ay = L - ay
                        if az > half:
                            az = L - az
                        d2 = ax * ax + ay * ay + az * az
                        if d2 < best or (d2 == best and p < bp):
                            best, bp = d2, p
                if (bp >= 0 and best <= (r * sw) ** 2) or r > srmax:
                    break
                r += 1
            own[bp].append(j)

    # ---- what a probe knows -------------------------------------------------
    plan_all = share >= 1.0
    share_cut = int(share * 10000)
    # the same tests as in hidden(), written out where the search is hot
    mode = (0 if plan_all else
            4 if announce or (share > 0.0 and told) else
            2 if share > 0.0 else 3 if told else 1)

    def hidden(p, j, t, d2):
        """True if probe p, at time t and a distance sqrt(d2) from system
        j, does not count j among the systems still to do."""
        if claim_by[j] == p or chosen_by[j] == p:
            return True
        m = met[p]
        if m is not None and j in m:
            return True
        if chosen_by[j] != -1 and (
                plan_all or (share > 0.0
                             and _mixed(keys[p], j) % 10000 < share_cut)):
            return True
        if not told:
            return False
        if done_t[j] + delay + light * math.sqrt(d2) <= t:
            return True
        if announce and chosen_by[j] != -1:
            ax = abs(fx[j] - px[p])
            ay = abs(fy[j] - py[p])
            az = abs(fz[j] - pz[p])
            if ax > half:
                ax = L - ax
            if ay > half:
                ay = L - ay
            if az > half:
                az = L - az
            return chosen_t[j] + light * math.sqrt(
                ax * ax + ay * ay + az * az) <= t
        return False

    def nearest(p, t, want):
        """The `want` nearest systems that probe p takes for still to do,
        as (distance squared, system), nearest first."""
        qx, qy, qz = px[p], py[p], pz[p]
        if in_cell[p]:
            found = []
            for j in own[p]:
                ax = abs(xs[j] - qx)
                ay = abs(ys[j] - qy)
                az = abs(zs[j] - qz)
                if ax > half:
                    ax = L - ax
                if ay > half:
                    ay = L - ay
                if az > half:
                    az = L - az
                d2 = ax * ax + ay * ay + az * az
                if not hidden(p, j, t, d2):
                    found.append((d2, j))
            found.sort()
            return found[:want]
        ix, iy, iz = int(qx / cw) % ng, int(qy / cw) % ng, int(qz / cw) % ng
        base = ix + ng * (iy + ng * iz)
        best, bj, found, r = INF, -1, [], 0
        m = met[p]
        kp = keys[p]
        while True:
            if (r <= ix < ng - r and r <= iy < ng - r and r <= iz < ng - r):
                todo = [(cells[base + k], qx, qy, qz) for k in flat(r)]
            else:
                # across the wrap: the probe as seen from each cell
                todo = [(cells[(ix + dx) % ng + ng * (
                    (iy + dy) % ng + ng * ((iz + dz) % ng))],
                    qx - L * ((ix + dx) // ng), qy - L * ((iy + dy) // ng),
                    qz - L * ((iz + dz) // ng)) for dx, dy, dz in shell(r)]
            for lst, ux, uy, uz in todo:
                for j in lst:
                    ex = xs[j] - ux
                    ey = ys[j] - uy
                    ez = zs[j] - uz
                    d2 = ex * ex + ey * ey + ez * ez
                    if d2 >= best:
                        continue
                    if mode == 0:
                        if m is not None and j in m:
                            continue
                    elif mode == 1:
                        if claim_by[j] == p or (m is not None and j in m):
                            continue
                    elif mode == 2:
                        cb = chosen_by[j]
                        if cb != -1 and (
                                cb == p or claim_by[j] == p
                                or (m is not None and j in m)
                                or (((kp ^ (j * _MIX)) * 2654435761)
                                    & _MASK) % 10000 < share_cut):
                            continue
                    elif mode == 3:
                        dj = done_t[j]
                        if dj != INF and (
                                claim_by[j] == p
                                or dj + delay + light * math.sqrt(d2) <= t
                                or (m is not None and j in m)):
                            continue
                    elif hidden(p, j, t, d2):
                        continue
                    if want == 1:
                        best, bj = d2, j
                    else:
                        found.append((d2, j))
                        if len(found) >= want:
                            found.sort()
                            del found[want:]
                            best = found[-1][0]     # the farthest kept
            if want == 1:
                if bj >= 0 and best <= (r * cw) ** 2:
                    return [(best, bj)]
            elif len(found) >= want and best <= (r * cw) ** 2:
                return found
            r += 1
            if r > rmax:
                if want == 1:
                    return [(best, bj)] if bj >= 0 else []
                found.sort()
                return found

    # ---- the survey -----------------------------------------------------------
    events = []                 # (time, order, kind, probe, system)
    order = 0
    travel = [0.0] * P
    visits = [0] * P            # systems surveyed by each probe
    misses = [0] * P            # wasted visits of each probe
    last = [0.0] * P            # when each probe stopped
    hop_sum = 0.0               # length of the hops that ended in a survey
    first_sum, first_count = 0.0, 0     # the same, first five per probe
    taken_by_phantoms = 0
    surveyed = 0
    purge_at = max(2000, N // 20)
    since_purge = 0
    next_drift = 0.02 / drift if drift > 0.0 else INF

    def set_out(p, t, after_miss):
        nonlocal order, taken_by_phantoms, listed, built, in_grid
        if plan_all and listed < 0.5 * built and listed > 50:
            in_grid = [i for i in in_grid if chosen_by[i] == -1]
            fill_grid(in_grid)
            built = listed = len(in_grid)
        got = nearest(p, t, 8 if after_miss else 1)
        if not got and in_cell[p] and rule == "cells-roam":
            in_cell[p] = False
            got = nearest(p, t, 8 if after_miss else 1)
        if not got:
            last[p] = t
            return
        if after_miss and len(got) > 1:
            d2, j = min(got, key=lambda item: _mixed(keys[p], item[1]))
        else:
            d2, j = got[0]
        if chosen_by[j] == -1:
            chosen_by[j] = p
            chosen_t[j] = t
            if announce:
                fx[j], fy[j], fz[j] = px[p], py[p], pz[p]
            if plan_all:
                cells[cell_of[j]].remove(j)
                listed -= 1
                if gone[p]:
                    taken_by_phantoms += 1
        order += 1
        heapq.heappush(events, (t + math.sqrt(d2), order, 0, p, j))

    for p in range(P):
        if gone[p] and not phantoms:
            continue
        order += 1
        heapq.heappush(events, (0.0, order, 1, p, -1))

    goal = min(N, int(math.ceil(float(c["until"]) * N - 1e-9)))
    handled = 0
    while events and surveyed + taken_by_phantoms < goal:
        t, _, kind, p, j = heapq.heappop(events)
        handled += 1
        if t >= next_drift:
            for i in in_grid:
                xs[i] = (x0[i] + vx[i] * t) % L
                ys[i] = (y0[i] + vy[i] * t) % L
                zs[i] = (z0[i] + vz[i] * t) % L
            in_grid = [i for i in in_grid
                       if not (plan_all and chosen_by[i] != -1)]
            fill_grid(in_grid)
            next_drift = t + 0.02 / drift
        if kind == 1:
            set_out(p, t, False)
            continue
        ax = abs(xs[j] - px[p])
        ay = abs(ys[j] - py[p])
        az = abs(zs[j] - pz[p])
        if ax > half:
            ax = L - ax
        if ay > half:
            ay = L - ay
        if az > half:
            az = L - az
        hop = math.sqrt(ax * ax + ay * ay + az * az)
        travel[p] += hop
        px[p], py[p], pz[p] = xs[j], ys[j], zs[j]
        if gone[p]:
            # a lost probe that the others still reckon with: it never
            # arrives, and the plan goes on as if it had
            if met[p] is None:
                met[p] = set()
            met[p].add(j)
            order += 1
            heapq.heappush(events, (t + stay, order, 1, p, -1))
            continue
        if claim_by[j] != -1:
            misses[p] += 1
            if met[p] is None:
                met[p] = set()
            met[p].add(j)
            t += stay if c["repeat_stay"] else 0.0
            last[p] = t
            set_out(p, t, True)
            continue
        claim_by[j] = p
        done_t[j] = t + stay
        surveyed += 1
        if in_cell[p]:
            own[p].remove(j)
        hop_sum += hop
        if visits[p] < 5:
            first_sum += hop
            first_count += 1
        visits[p] += 1
        last[p] = t + stay
        if told and not plan_all:
            since_purge += 1
            if since_purge >= purge_at:
                # systems that every probe knows to be done leave the grid
                since_purge = 0
                limit = t - delay - light * 0.87 * L
                in_grid = [i for i in in_grid if done_t[i] > limit]
                fill_grid(in_grid)
                purge_at = max(2000, len(in_grid) // 10)
        order += 1
        heapq.heappush(events, (t + stay, order, 1, p, -1))

    # ---- what came out --------------------------------------------------------
    finished = sorted(d for d in done_t if d < INF)
    times = {}
    for level in LEVELS:
        need = int(math.ceil(level * N - 1e-9))
        times["%g" % level] = (finished[need - 1]
                               if 0 < need <= len(finished) else None)
    present = [p for p in range(P) if not gone[p]]
    loads = sorted(visits[p] for p in present)
    mean_load = sum(loads) / max(1, len(loads))
    spread = (math.sqrt(sum((x - mean_load) ** 2 for x in loads)
                        / max(1, len(loads))) / mean_load
              if mean_load else 0.0)

    def at(q):
        return loads[min(len(loads) - 1, int(q * len(loads)))] if loads else 0
    wasted = sum(misses[p] for p in present)
    end = finished[-1] if finished else 0.0
    return dict(
        config=c, systems=N, box=L,
        surveyed_share=surveyed / N,
        times=times,
        end=end,
        visits=surveyed, wasted_visits=wasted,
        wasted_share=wasted / max(1, wasted + surveyed),
        mean_hop=hop_sum / max(1, surveyed),
        mean_first_hops=first_sum / max(1, first_count),
        travel_per_system=sum(travel[p] for p in present) / max(1, surveyed),
        load=dict(mean=mean_load, spread=spread, least=at(0.0), low=at(0.05),
                  middle=at(0.5), high=at(0.95), most=at(1.0)),
        events=handled,
        clock_error=max(
            (abs(last[p] - travel[p] - stay * (
                visits[p] + (misses[p] if c["repeat_stay"] else 0)))
             for p in present), default=0.0),
        seconds=time.time() - started,
    )


# ---------------------------------------------------------------------------
# Many runs
# ---------------------------------------------------------------------------

def label_of(config: dict) -> str:
    """A short name for what a run varies, seed left out."""
    c = dict(DEFAULTS)
    c.update(config)
    if c["rule"] == "cells":
        know = ""               # a probe needs to know nothing of the others
    elif c["foresight"] >= 1.0:
        know = "plan"
    else:
        parts = []
        if c["foresight"] > 0.0:
            parts.append("plan%g" % c["foresight"])
        if c["records"] < INF:
            parts.append("announce" if c["announce"] else "records")
            if c["records"] > 0.0:
                parts.append("late%g" % c["records"])
        know = "+".join(parts) or "none"
    extra = []
    for key, text in (("probes", "probes%d"), ("per_probe", "each%g"),
                      ("stay", "stay%g"), ("seeding", "%s"),
                      ("absent", "absent%g"), ("twins", "twins%g"),
                      ("drift", "drift%g")):
        if c[key] != DEFAULTS[key]:
            extra.append(text % c[key])
    if not c["absent_known"]:
        extra.append("unseen")
    if c["repeat_stay"]:
        extra.append("restay")
    return " ".join(["%s/%s" % (c["rule"], know) if know else c["rule"]]
                    + extra)


def matrix(name: str) -> list:
    """The runs of a named set, most important first. Each entry is
    (group, config)."""
    never = INF
    runs = []
    seen = set()

    def add(group, seeds, **config):
        if (config.get("foresight", 0.0) < 1.0
                and config.get("records", 0.0) == never
                and config.get("rule", "roam") != "cells"):
            # without records the last few systems are found by chance;
            # stop these runs at 99.99 percent, and at 99.9 where probes
            # roam knowing nothing at all
            blind = (config.get("rule", "roam") == "roam"
                     and config.get("foresight", 0.0) == 0.0)
            config.setdefault("until", 0.999 if blind else 0.9999)
        for seed in seeds:
            job = dict(config, seed=seed)
            if _key(job) not in seen:       # asked for under two headings
                seen.add(_key(job))
                runs.append((group, job))

    if name == "trial":
        for rule in ("roam", "cells-roam"):
            add("trial", (1,), probes=216, rule=rule)
        add("trial", (1,), probes=216, rule="cells")
        add("trial", (1,), probes=216, rule="cells-roam", records=never)
        return runs

    full = name == "full"
    main_seeds = (1, 2, 3) if full else (1, 2)
    side_seeds = (1, 2) if full else (1,)
    big, small = (8000, 4096) if full else (4096, 1728)

    # 1. the rules side by side, each with four kinds of knowledge
    for rule in ("cells-roam", "roam"):
        add("main", main_seeds, probes=big, rule=rule, foresight=1.0)
        add("main", main_seeds, probes=big, rule=rule)
        add("main", main_seeds, probes=big, rule=rule, announce=True)
        # roaming without records is slow to simulate: a smaller box
        blind = big if rule == "cells-roam" else small
        add("main", main_seeds, probes=blind, rule=rule, foresight=0.95,
            records=never)
        add("main", main_seeds, probes=blind, rule=rule, records=never)
    add("main", main_seeds, probes=big, rule="cells")

    # 2. how much foresight, how late the records: the table for the
    #    calculator
    for rule in ("cells-roam", "roam"):
        shares = (0.0, 0.8, 0.95, 0.99) if rule == "cells-roam" else (0.0, 0.95)
        lates = ((3.0, 10.0, 30.0, 100.0) if rule == "cells-roam"
                 else (10.0, 100.0))
        for share in shares:
            for late in lates:
                add("knowledge", side_seeds, probes=small, rule=rule,
                    foresight=share, records=late)
            if share > 0.0:
                add("knowledge", side_seeds, probes=small, rule=rule,
                    foresight=share)
                add("knowledge", side_seeds, probes=small, rule=rule,
                    foresight=share, records=never)
        add("knowledge", side_seeds, probes=small, rule=rule)
        add("knowledge", side_seeds, probes=small, rule=rule, records=never)
        add("knowledge", side_seeds, probes=small, rule=rule, foresight=1.0)
    add("knowledge", side_seeds, probes=small, rule="cells")

    # 3. one thing changed at a time, for five ways of working
    ways = (dict(rule="cells"),
            dict(rule="cells-roam"),
            dict(rule="cells-roam", records=never),
            dict(rule="cells-roam", foresight=0.95, records=never),
            dict(rule="roam"))
    for way in ways:
        for each in (10.0, 30.0, 300.0):
            add("per probe", side_seeds, per_probe=each,
                probes=(1728 if each > 100 else small), **way)
        for stay in (0.05, 0.4):
            add("stay", side_seeds, probes=small, stay=stay, **way)
        for seeding in ("lattice", "centres"):
            add("start", side_seeds, probes=small, seeding=seeding, **way)
        for absent in (0.1, 0.5):
            add("losses", side_seeds, probes=small, absent=absent, **way)
        add("twins", side_seeds, probes=small, twins=0.2, **way)
    for rule in ("cells-roam", "roam"):
        add("losses", side_seeds, probes=small, rule=rule, foresight=1.0,
            absent=0.1, absent_known=False)
        add("losses", side_seeds, probes=small, rule=rule, foresight=1.0,
            absent=0.1)
    for way in ways[1:4]:
        add("repeat", side_seeds, probes=small, repeat_stay=True, **way)
    add("drift", (1,), probes=small, rule="cells-roam", drift=0.00067)
    add("drift", (1,), probes=small, rule="cells", drift=0.00067)

    # 4. does the size of the box matter?
    for probes in ((1000, 15625) if full else (512,)):
        add("size", (1,), probes=probes, rule="cells-roam")
        add("size", (1,), probes=probes, rule="cells")

    # 5. records that arrive only after most of the work is done
    for share in (0.0, 0.95, 0.8, 0.99):
        for late in (300.0, 400.0):
            add("late", side_seeds, probes=small, rule="cells-roam",
                foresight=share, records=late)

    # 6. two things changed at once: few systems per probe with short
    #    stays, many with long ones (probes given equal work have fewer
    #    systems where these lie far apart)
    add("corner", (1,), probes=small, rule="cells-roam", per_probe=30.0,
        stay=0.05)
    add("corner", (1,), probes=1728, rule="cells-roam", per_probe=300.0,
        stay=0.4)
    return runs


# Time of one run alone, in seconds: a measured constant times the number
# of systems to a measured power (boxes of 1,000 to 8,000 probes on the
# machine the sets were sized for, a 2023 desktop with eight cores).
def predicted_seconds(config: dict) -> float:
    c = dict(DEFAULTS)
    c.update(config)
    size = c["probes"] * c["per_probe"] / 1e5
    partial = 0.0 < c["foresight"] < 1.0
    if c["rule"] == "cells":
        return 6.2 * size ** 1.25
    if c["foresight"] >= 1.0:
        return 2.5 * size ** 1.35
    if c["records"] == INF:
        if c["rule"] == "roam":
            return (11.0 * size ** 1.4 if partial else 31.0 * size ** 1.16)
        return (7.2 if partial else 9.0) * size ** 1.4
    return (7.2 if partial or c["announce"] else 4.5) * size ** 1.5


def _one(job):
    group, config = job
    result = simulate(config)
    result["group"] = group
    result["label"] = label_of(config)
    result["asked"] = config
    return result


def _key(config: dict) -> str:
    return json.dumps(config, sort_keys=True)


def _spin(seconds_of_work):
    """A fixed piece of work, to measure how well this machine runs
    several processes at once."""
    started = time.time()
    simulate(dict(probes=512, seed=int(seconds_of_work)))
    return time.time() - started


def parallel_gain(processes: int) -> float:
    """How many runs' worth of work `processes` processes finish in the
    time one process needs for one run."""
    alone = _spin(1)
    started = time.time()
    with multiprocessing.Pool(processes) as pool:
        pool.map(_spin, range(1, processes + 1))
    return processes * alone / (time.time() - started)


def run_matrix(name: str, out_dir: str, processes: int, hours: float,
               say=print) -> str:
    """Run a named set, writing every finished run to results.jsonl in
    out_dir at once. Runs already there are skipped, so an interrupted
    set can be taken up again. Stops when `hours` are used up."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "results.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                if line.strip():
                    done.add(_key(json.loads(line)["asked"]))
    jobs = [(group, config) for group, config in matrix(name)
            if _key(config) not in done]
    say("%d runs to do, %d already there; %d processes; limit %.2f hours"
        % (len(jobs), len(done), processes, hours))
    started = time.time()
    finished = 0
    if not jobs:
        return path
    pool = multiprocessing.Pool(processes)
    try:
        results = pool.imap_unordered(_one, jobs, chunksize=1)
        while finished < len(jobs):
            left = hours * 3600.0 - (time.time() - started)
            if left <= 0.0:
                say("time limit reached with %d of %d runs done"
                    % (finished, len(jobs)))
                break
            try:
                result = results.next(timeout=min(left, 60.0))
            except multiprocessing.TimeoutError:
                continue
            with open(path, "a") as fh:
                fh.write(json.dumps(result) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            finished += 1
            say("%4d/%d  %6.0f s  %-60s %5.0f s"
                % (finished, len(jobs), time.time() - started,
                   result["label"], result["seconds"]))
    finally:
        pool.terminate()
        pool.join()
    say("stopped after %.2f hours" % ((time.time() - started) / 3600.0))
    return path


# ---------------------------------------------------------------------------
# Reading the results
# ---------------------------------------------------------------------------

SHOWN = ("0.5", "0.9", "0.99", "0.999", "1")

# The hop, in spacings, that the pace calculator assumes for a probe that
# clears a field of fixed points. With it one probe needs
# systems per probe x (0.78 + stay) for its share: the yardstick below.
NOMINAL_HOP = 0.78


def summarise(path: str) -> dict:
    """Average the runs of every way of working over their seeds.

    Times are also given over the share time: what one probe needs for
    the mean number of systems per probe at a hop of 0.78 spacings, the
    figure of the pace calculator. The same yardstick for every way, so
    that the ways can be compared."""
    ways = {}
    seen = set()
    with open(path) as fh:
        for line in fh:
            if line.strip():
                run = json.loads(line)
                if _key(run["asked"]) in seen:
                    continue                # the same run, done twice
                seen.add(_key(run["asked"]))
                ways.setdefault(run["label"], []).append(run)
    out = {}
    for label, runs in ways.items():
        c = runs[0]["config"]

        def mean(pick):
            values = [pick(r) for r in runs]
            values = [v for v in values if v is not None]
            return sum(values) / len(values) if values else None
        hop = mean(lambda r: r["mean_hop"])
        even = c["per_probe"] * (NOMINAL_HOP + c["stay"])
        times = {level: mean(lambda r: r["times"].get(level))
                 for level in runs[0]["times"]}
        ends = [r["times"].get("0.99") for r in runs]
        ends = [e for e in ends if e is not None]
        out[label] = dict(
            group=runs[0]["group"], runs=len(runs), config={
                key: value for key, value in c.items() if key != "seed"},
            hop=hop, first_hops=mean(lambda r: r["mean_first_hops"]),
            travel_per_system=mean(lambda r: r["travel_per_system"]),
            wasted_share=mean(lambda r: r["wasted_share"]),
            surveyed_share=mean(lambda r: r["surveyed_share"]),
            load_spread=mean(lambda r: r["load"]["spread"]),
            largest_load=mean(lambda r: r["load"]["most"]),
            share_time=even,
            times=times,
            over_share_time={level: (None if t is None else t / even)
                             for level, t in times.items()},
            scatter_at_99=((max(ends) - min(ends)) / even if ends else None),
            seconds=sum(r["seconds"] for r in runs))
    return out


def render_summary(summary: dict) -> str:
    lines = [
        "Times are in share times: 1.00 is what one probe needs for the mean",
        "number of systems per probe at a hop of 0.78 spacings.",
        "",
        "%-46s %4s %6s %6s %6s %6s %6s %7s %5s" % (
            "way of working", "runs", "half", "90%", "99%", "99.9%", "last",
            "wasted", "hop")]
    groups = []
    for entry in summary.values():
        if entry["group"] not in groups:
            groups.append(entry["group"])
    for group in groups:
        lines += ["", "[%s]" % group]
        for label, entry in summary.items():
            if entry["group"] != group:
                continue
            shown = ["%6.2f" % entry["over_share_time"][level]
                     if entry["over_share_time"].get(level) is not None
                     else "     -" for level in SHOWN]
            lines.append("%-46s %4d %s %6.1f%% %5.2f" % (
                label[:46], entry["runs"], " ".join(shown),
                100.0 * entry["wasted_share"], entry["hop"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The table for the pace calculator
#
# For the rule "cells-roam": when is each share of the systems done, per
# system and probe, as travel (in spacings) plus stays; how that changes
# with the systems per probe; and how it changes, with the visits wasted,
# when a probe foresees only a share of the others' choices and records
# reach it late.
# ---------------------------------------------------------------------------

TABLE_LEVELS = ("0.5", "0.9", "0.99", "0.999", "0.9999", "1")
_PLAIN = dict(rule="cells-roam", foresight=0.0, records=0.0, announce=False,
              per_probe=100.0, stay=0.2, seeding="points", absent=0.0,
              absent_known=True, twins=0.0, repeat_stay=False, drift=0.0)


def _pick(summary: dict, probes=None, **changed):
    """The entry of the summary whose settings are those of the plain
    cells-roam run except for `changed`: in a box of `probes` probes, or
    in the largest box there is."""
    want = dict(_PLAIN)
    want.update(changed)
    found = [entry for entry in summary.values()
             if all(entry["config"].get(key) == value
                    for key, value in want.items())
             and probes in (None, entry["config"]["probes"])]
    if not found:
        return None
    return max(found, key=lambda entry: (entry["config"]["probes"],
                                         entry["runs"]))


def calibration(summary: dict) -> dict:
    """The table that plan0_pace.py carries, from the results of a set.
    Every ratio compares two ways of working in boxes of the same size."""
    def per_system(entry):
        return [None if entry["times"].get(level) is None else
                entry["times"][level] / entry["config"]["per_probe"]
                for level in TABLE_LEVELS]

    def ratio(entry, base):
        return [None if a is None or b is None else round(a / b, 4)
                for a, b in zip(per_system(entry), per_system(base))]

    def base_for(entry):
        return (_pick(summary, probes=entry["config"]["probes"])
                or _pick(summary))

    plain = _pick(summary)
    stays = {}
    for stay in (0.05, 0.2, 0.4):
        entry = _pick(summary, stay=stay)
        if stay == 0.2 and _pick(summary, stay=0.05) is not None:
            # the plain run in the box of the other two
            entry = _pick(summary, probes=_pick(
                summary, stay=0.05)["config"]["probes"]) or entry
        if entry is not None:
            stays[stay] = per_system(entry)
    # time per system = travel + stays x stay, by least squares over stays
    travel, stops = [], []
    for i in range(len(TABLE_LEVELS)):
        xs = [stay for stay in stays if stays[stay][i] is not None]
        ys = [stays[stay][i] for stay in xs]
        if len(xs) < 2:
            travel.append(None)
            stops.append(None)
            continue
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                 / sum((x - mx) ** 2 for x in xs))
        travel.append(round(my - slope * mx, 4))
        stops.append(round(slope, 4))
    sizes = {}
    for each in (10.0, 30.0, 100.0, 300.0):
        entry = _pick(summary, per_probe=each)
        if entry is None:
            continue
        # a box of other systems per probe has no plain run of its own
        # size; the plain run of the usual small box stands in
        base = plain if each == 100.0 else (
            _pick(summary, probes=4096) or plain)
        sizes[each] = ([1.0] * len(TABLE_LEVELS) if each == 100.0
                       else ratio(entry, base))
    share_time = 100.0 * (NOMINAL_HOP + 0.2)
    knowledge = []
    for entry in summary.values():
        c = entry["config"]
        if any(c.get(key) != value for key, value in _PLAIN.items()
               if key not in ("foresight", "records")):
            continue
        best = _pick(summary, foresight=c["foresight"], records=c["records"])
        if best is not entry or plain is None:
            continue
        base = base_for(entry)
        knowledge.append(dict(
            foresight=c["foresight"],
            late=(None if c["records"] == INF
                  else round(c["records"] / share_time, 4)),
            times=ratio(entry, base),
            wasted=round(entry["wasted_share"], 4),
            wasted_travel=round(entry["travel_per_system"] - entry["hop"],
                                4)))
    knowledge.sort(key=lambda row: (row["foresight"],
                                    INF if row["late"] is None
                                    else row["late"]))
    # for comparison: probes on a lattice that keep to their own cell
    # and know nothing of the others, in share times
    even = _pick(summary, rule="cells", seeding="lattice")
    return dict(levels=[float(level) for level in TABLE_LEVELS],
                hop=None if plain is None else round(plain["hop"], 4),
                travel=travel, stops=stops, per_probe=sizes,
                knowledge=knowledge,
                even_starts=(None if even is None else [
                    None if even["over_share_time"].get(level) is None
                    else round(even["over_share_time"][level], 4)
                    for level in TABLE_LEVELS]))


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

_DESCRIPTION = """\
Follow single probes from star system to star system during the survey
phase of the fleet plan, for a fleet so large that every probe has only
about a hundred systems to itself. The pace calculator (plan0_pace.py)
works with averages; this program checks them, and measures what the
calculator cannot: how unevenly the work falls, how many visits are
wasted on systems that another probe has already surveyed, and how both
depend on the rule the probes follow and on what each knows of the
others.

A run places systems at random in a box that wraps around, places the
probes, and lets each one work until every system is surveyed. Lengths
are counted in mean distances between neighboring systems and times in
the time a probe needs to cruise one such distance.
"""

_EPILOG = """\
rules (--rule NAME):
%s

where the probes start (--start NAME):
%s

what a probe knows of the others:
  It always knows its own work and what it runs into. Beyond that,
  --foresight gives the share of the others' choices that it has worked
  out in advance from the common rule, and --records the delay with
  which completion records reach it on top of their travel at light
  speed (the word never switches records off). With --announce a probe
  also sends word of the system it sets out for.

sets of runs (--set NAME):
  full     every question the simulation was built for, about 240 runs
  limited  the same questions with smaller boxes and fewer repeats
  trial    four small runs, to check that everything works
  Finished runs are written to results.jsonl in the folder given by
  --out, one per line, as soon as they end. Starting the same set again
  skips what is already there. --estimate prints the expected duration
  without running anything, and --report prints a table of what is in
  the folder.

examples:
  python plan0_sim.py
      one run with the settings of the plan: a hundred systems per
      probe, records at light speed
  python plan0_sim.py --rule cells-roam --foresight 0.95 --records never
      probes that keep to their own cell first and are right about 95
      percent of what the others do, with no records at all
  python plan0_sim.py --set full --estimate --processes 6
      how long the full set would take on this machine
  python plan0_sim.py --set full --out results --processes 6 --hours 4.5
      run it, stopping after four and a half hours at the latest
"""


def _listing(table: dict) -> str:
    import textwrap
    return "\n".join(
        "\n".join(textwrap.wrap(text, width=78, initial_indent="  %-12s " % name,
                               subsequent_indent=" " * 15))
        for name, text in table.items())


def _delay(text: str) -> float:
    return INF if text.strip().lower() == "never" else float(text)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="plan0_sim.py", description=_DESCRIPTION,
        epilog=_EPILOG % (_listing(RULES), _listing(SEEDINGS)),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_argument_group("one run")
    g.add_argument("--probes", type=int, metavar="COUNT",
                   help="probes in the box (default 8000)")
    g.add_argument("--per-probe", type=float, metavar="COUNT",
                   dest="per_probe",
                   help="star systems per probe (default 100, the plan: "
                        "a hundred billion systems, a billion probes)")
    g.add_argument("--stay", type=float, metavar="NUMBER",
                   help="stay per system, in units of the time a probe "
                        "needs to cruise the mean distance between "
                        "systems (default 0.2: ten years where systems "
                        "lie 1.5 parsecs apart)")
    g.add_argument("--light", type=float, metavar="FRACTION",
                   help="cruise speed as a fraction of the speed of "
                        "light (default 0.1)")
    g.add_argument("--rule", choices=list(RULES), metavar="NAME",
                   help="how a probe chooses its next system; see below "
                        "(default roam)")
    g.add_argument("--foresight", type=float, metavar="FRACTION",
                   help="share of the other probes' choices that a probe "
                        "has worked out in advance (default 0)")
    g.add_argument("--records", type=_delay, metavar="DELAY",
                   help="delay of completion records beyond their travel "
                        "at light speed, or the word never (default 0)")
    g.add_argument("--announce", action="store_true", default=None,
                   help="probes also send word of the system they set "
                        "out for")
    g.add_argument("--start", choices=list(SEEDINGS), metavar="NAME",
                   dest="seeding",
                   help="where the probes start; see below (default "
                        "points)")
    g.add_argument("--region", type=float, metavar="COUNT",
                   help="systems per seed region, for --start centres "
                        "(default 1000)")
    g.add_argument("--absent", type=float, metavar="FRACTION",
                   help="share of the probes lost before the survey "
                        "starts (default 0)")
    g.add_argument("--unseen-losses", action="store_false", default=None,
                   dest="absent_known",
                   help="the other probes do not know which probes are "
                        "lost and go on reckoning with them")
    g.add_argument("--twins", type=float, metavar="FRACTION",
                   help="share of the probes that share their starting "
                        "point and their identifier with another probe "
                        "(default 0)")
    g.add_argument("--repeat-stay", action="store_true", default=None,
                   dest="repeat_stay",
                   help="a probe that arrives at a system already "
                        "surveyed stays there as long as for a survey")
    g.add_argument("--drift", type=float, metavar="NUMBER",
                   help="random speed of the stars, as a fraction of the "
                        "cruise speed (default 0: the stars stand still)")
    g.add_argument("--until", type=float, metavar="FRACTION",
                   help="stop when this share of the systems is surveyed "
                        "(default 1)")
    g.add_argument("--seed", type=int, metavar="NUMBER",
                   help="seed of the random numbers (default 1)")
    g = p.add_argument_group("sets of runs")
    g.add_argument("--set", choices=("full", "limited", "trial"),
                   metavar="NAME", dest="set_name",
                   help="run a whole set; see below")
    g.add_argument("--out", metavar="FOLDER", default="plan0_sim_results",
                   help="folder for the results of a set (default "
                        "plan0_sim_results)")
    g.add_argument("--processes", type=int, metavar="COUNT", default=6,
                   help="runs worked on at the same time (default 6, "
                        "which is also the most this program will use)")
    g.add_argument("--hours", type=float, metavar="NUMBER", default=5.0,
                   help="stop a set after this many hours at the latest "
                        "(default 5)")
    g.add_argument("--estimate", action="store_true",
                   help="print how long the set is expected to take, "
                        "and stop")
    g.add_argument("--report", action="store_true",
                   help="print a table of the results in the folder")
    g.add_argument("--table", action="store_true",
                   help="with --report: print the table that the pace "
                        "calculator carries, worked out from the results")
    g.add_argument("--json", metavar="FILE",
                   help="also write the result or the table to this file")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    processes = max(1, min(6, args.processes))
    path = os.path.join(args.out, "results.jsonl")
    if args.set_name and args.estimate:
        jobs = matrix(args.set_name)
        alone = sum(predicted_seconds(config) for _, config in jobs)
        gain = parallel_gain(processes)
        print("%d runs; one after another they would take about %.1f hours."
              % (len(jobs), alone / 3600.0))
        print("With %d processes this machine does the work of %.1f, so the "
              "set should take about %.1f hours."
              % (processes, gain, alone / 3600.0 / gain))
        return 0
    if args.set_name:
        path = run_matrix(args.set_name, args.out, processes, args.hours)
    if args.set_name or args.report:
        summary = summarise(path)
        if args.table:
            summary = calibration(summary)
            print(json.dumps(summary, indent=1))
        else:
            print(render_summary(summary))
        if args.json:
            with open(args.json, "w") as fh:
                json.dump(summary, fh, indent=1)
        return 0
    config = {key: value for key, value in vars(args).items()
              if key in DEFAULTS and value is not None}
    try:
        result = simulate(config)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    c = result["config"]
    even = c["per_probe"] * (NOMINAL_HOP + c["stay"])
    print("%s: %d systems, %d probes" % (label_of(config), result["systems"],
                                         c["probes"]))
    print("  surveyed: %.2f%% of the systems; %.1f%% of all visits wasted"
          % (100.0 * result["surveyed_share"],
             100.0 * result["wasted_share"]))
    print("  mean hop to a system surveyed: %.3f spacings (first five per "
          "probe: %.3f)" % (result["mean_hop"], result["mean_first_hops"]))
    print("  at a hop of %.2f spacings one probe needs %.1f time units for "
          "its share;" % (NOMINAL_HOP, even))
    print("  share of the systems done after")
    for level in SHOWN:
        t = result["times"].get(level)
        print("    %5s%%  %s" % (
            "%g" % (100.0 * float(level)),
            "not reached" if t is None else "%.2f share times" % (t / even)))
    print("  systems per probe: %d to %d, spread %.0f%% of the mean"
          % (result["load"]["least"], result["load"]["most"],
             100.0 * result["load"]["spread"]))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(result, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
