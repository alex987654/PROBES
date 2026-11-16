# The survey simulation: results

*Companion to `plan0_sim.py` and `plan0_pace.py`. Not part of the
language specification. Section numbers refer to two documents at the
top of this repository: the Overview (`README.md`) and the Physical
Layer (`PROBES_CNL_Physical_Layer.md`).*

## What this is about

Under the fleet plan (`PLAN-0`) a billion probes survey the hundred
billion star systems of this galaxy. No probe can instruct another
(Overview section 3.2). Every probe follows the same public rule and acts
on what it knows of the others' work, which it either works out from
that rule or reads in the completion records the others leave behind.

`plan0_sim.py` follows single probes from star system to star system to
find out how well that works: how long the survey takes, how many visits
go to systems that another probe has already surveyed, and how both
depend on the rule, on what a probe knows, on where the probes start and
on how many of them are lost.

This document says what was simulated, gives the results of the 321
stored runs, translates them into years and names what they do not show.
The runs themselves are stored beside it, in `results.jsonl`.

## The findings in brief

1. **The survey is one percent of the mission.** Before any probe may
   begin, the fleet scatters across the disc for 978,000 years (Physical
   Layer section 4.5). After that, 99 percent of the systems are
   surveyed within about 6,800 years and the last one after about 7,800.
   The cases below lie between 6,500 and 23,300 years, in a mission of a
   million. The simulation decides how the survey should be run, not how
   long the mission is.
2. **A probe can act on what it works out.** A probe that has worked out
   95 percent of the other probes' choices correctly, and never sees a
   record, reaches 99 percent of the systems about 40 years later than
   one that hears of every completion at the speed of light where the
   probes start spread evenly, and about 200 years later where they
   start at random. It wastes 4 percent of its visits, or 12 percent.
3. **Provided each probe clears its own cell first.** A probe's cell is
   the set of systems nearer to its own starting point than to any other
   probe's. With nothing known of the others, probes that clear their
   cell first reach 99 percent in less than half the time of probes that
   go wherever the nearest unsurveyed system is.
4. **Where the probes start matters more than anything they know.**
   Spread evenly, one probe to a region of its own, probes that know
   nothing of each other reach 99 percent sooner than randomly placed
   probes that hear of every completion at the speed of light. The
   specification starts them that way (Physical Layer section 4.5), and
   the plan below is that start.
5. **Working things out cannot reveal a lost probe.** Where a tenth of
   the fleet is gone and the others go on reckoning with it, one system
   in ten is never surveyed. Records do not have that weakness.
6. **Little else matters.** The length of the stay and the drift of the
   stars change the outcome by a few percent at most. So do probes that
   share a starting point and an identifier, as long as records or
   foresight tell them apart.

Years from the start of the survey until 99 percent of the systems are
surveyed:

| Rule | Starting points | What a probe knows of the others | Years |
| --- | --- | --- | --- |
| roam from the start | at random | nothing | 23,300 |
| own cell only | at random | nothing needed | 11,700 |
| own cell first | at random | nothing | 10,700 |
| own cell first | at random | 95 percent worked out, no records | 7,600 |
| own cell first | at random | completion records at light speed | 7,400 |
| roam from the start | at random | 95 percent worked out, no records | 7,300 |
| own cell first | at random | everything worked out in advance | 7,100 |
| own cell first | spread evenly | nothing | 7,000 |
| own cell only | spread evenly | nothing needed | 7,000 |
| roam from the start | at random | completion records at light speed | 6,900 |
| own cell first | spread evenly | 95 percent worked out, no records | 6,800 |
| own cell first | spread evenly | completion records at light speed | 6,800 |
| own cell first | spread evenly | 95 percent worked out, records at light speed (the plan) | 6,800 |
| roam from the start | at random | everything worked out in advance | 6,500 |

The terms are explained below.

## The setting

The figures of the plan, as the calculator `plan0_pace.py` has them by
default:

| Quantity | Value |
| --- | --- |
| Probes | a billion |
| Star systems | a hundred billion, so a hundred per probe |
| Cruise speed | a tenth of the speed of light |
| Stay per system | 10 years |
| Distance between neighboring systems | 1.6 parsecs at the median, 2.0 on average |
| One hop from system to system | about 50 years |
| Scattering before the survey | 978,000 years |
| Survey after that | about 8,000 years |
| What a star moves in 8,000 years, against its neighbors | 0.2 to 0.5 parsecs |

The last line shapes the simulation. While the survey lasts a star moves
a fraction of one hop: the stars stand still. A system that a probe
leaves for later is still there later, and nothing drifts in from
elsewhere. What decides the outcome is therefore local, within a few
parsecs of each probe:

- where the probes start,
- which rule sends a probe on to its next system,
- what each probe knows of the work of its neighbors,
- how many probes are missing.

So the simulation follows single probes in a box of stars, at the ratios
of the plan: a hundred systems per probe, light ten times as fast as a
probe, a stay of ten years against hops of about fifty.

This holds for fleets large enough to finish before the stars have
moved. A fleet of ten thousand probes would need hundreds of millions of
years, in which the stars mix many times over. The calculator has other
laws for that case, and this simulation does not apply to it.

## The model

- **The box.** Systems are placed at random in a cube that wraps around,
  so that it has no edge. A box holds 4,096 or 8,000 probes in most
  runs, and a hundred systems for each. Lengths are counted in mean
  distances between neighboring systems ("spacings"), times in the time
  a probe needs to cruise one spacing: 51 years at the median spacing of
  the galaxy model. The stay per system is 0.2 of that.
- **Three rules.** *Roam*: a probe goes to the nearest system it does
  not know to be done, wherever that lies. *Own cell only*: it surveys
  the systems of its own cell, then stops. *Own cell first*: it surveys
  its own cell, then roams.
- **A cell** is the set of systems nearer to a probe's own starting
  point than to any other probe's. It follows from the starting points
  alone, so a probe needs no knowledge of the others to keep to it.
- **What a probe knows.** Its own work and what it runs into, always.
  Beyond that there are two sources, in any mix. *Foresight* is the
  share of the other probes' choices that it has worked out from the
  common rule; it knows them the moment they are made. *Records* are
  completion records that reach it at the speed of light, or later by a
  set delay. A probe can also *announce* the system it sets out for.
- **A wasted visit** is an arrival at a system that is already taken. It
  costs the hop, not the stay; one set of runs charges the stay as well.
  The probe then takes one of its eight nearest candidates by a key of
  its own, so that two probes that meet at one star part ways.
- **Where the probes start.** At points drawn at random, which is the
  base case of results 1 to 5; on a regular lattice, which gives every
  probe a cell of the same size, as the specification's one region per
  probe does (result 6); or at the middles of regions of 1,000 systems,
  about ten probes to each.
- **Lost probes.** A share of the probes is missing from the start. A
  probe with foresight either knows which probes are missing, or goes on
  reckoning with them.

### Checks

The program has fourteen tests, each against something known beforehand.
Among them: a single probe makes the nearest-first tour, at 0.8 spacings
a hop; cells around random starting points are as uneven as geometry
says, with a spread of 43 percent of the mean; the same seed gives the
same result alone and inside a set.

Every probe's clock must equal its travel plus its stays. In 319 of the
321 stored runs it does, to ten decimal places. In the two runs with
drifting stars it is off by up to 0.17 time units in 136 and 344, a
tenth of a percent: there the stars are moved in steps of a fiftieth of
a spacing, so a probe arrives at a star that is not quite where it
aimed. Nothing below rests on those two runs beyond "no effect".

## How to read the tables

- **Share time.** Times are in share times. One share time is what a
  single probe needs for its hundred systems at a hop of 0.78 spacings:
  a hundred hops and a hundred stays. For the plan that is 6,139 years.
  It is a yardstick. Hops in most runs are somewhat longer than 0.78
  spacings, so even a fleet that wasted nothing would need a little
  more than 1.00.
- **Half, 90%, 99%, 99.9%, last system.** The time at which that share
  of the systems in the box is surveyed.
- **Visits wasted.** The share of all arrivals that found the system
  already taken.
- **"-"** was not reached: runs without records stop at 99.99 percent,
  and roaming with nothing known at 99.9. **"·"** was not run.

## Results

### 1. Rules and knowledge side by side

Boxes of 8,000 probes and 800,000 systems, three runs each; the two
lines for roaming without records have 4,096 probes. Starting points
drawn at random.

| Rule | What a probe knows of the others | Half | 90% | 99% | 99.9% | Last system | Visits wasted | 99% in years |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| own cell first, then roam | everything, worked out in advance | 0.49 | 0.96 | 1.16 | 1.44 | 1.86 | 0% | 7,100 |
| own cell first, then roam | records and announcements at light speed | 0.49 | 0.97 | 1.16 | 1.25 | 1.48 | 3% | 7,100 |
| own cell first, then roam | completion records at light speed | 0.49 | 0.98 | 1.20 | 1.30 | 1.39 | 7% | 7,400 |
| own cell first, then roam | 95 percent worked out, no records | 0.49 | 0.99 | 1.24 | 1.36 | - | 12% | 7,600 |
| own cell first, then roam | nothing | 0.50 | 1.13 | 1.75 | 2.33 | - | 63% | 10,700 |
| roam from the start | everything, worked out in advance | 0.45 | 0.88 | 1.06 | 1.34 | 1.74 | 0% | 6,500 |
| roam from the start | records and announcements at light speed | 0.45 | 0.88 | 1.06 | 1.15 | 1.33 | 3% | 6,500 |
| roam from the start | completion records at light speed | 0.46 | 0.91 | 1.12 | 1.22 | 1.37 | 9% | 6,900 |
| roam from the start | 95 percent worked out, no records | 0.46 | 0.93 | 1.19 | 1.41 | - | 22% | 7,300 |
| roam from the start | nothing | 0.55 | 1.70 | 3.79 | 6.61 | - | 85% | 23,300 |
| own cell only | nothing needed | 0.50 | 1.20 | 1.91 | 2.52 | 3.85 | 0% | 11,700 |

- **Knowledge decides between the two rules.** With records or
  foresight, roaming from the start is 4 to 9 percent ahead at the 99
  percent mark. With nothing known it needs more than twice as long as
  clearing the own cell first (3.79 against 1.75), and 85 percent of its
  visits are wasted.
- **A cell needs no knowledge.** Keeping to it and stopping there wastes
  nothing. But cells around random starting points are uneven: 99
  percent takes 1.9 share times, and the last system waits for the
  largest cell.
- **Working everything out in advance is not the fastest finish.** In
  that mode a system belongs to the first probe that chose it, even from
  far away, so the last ones are fetched over long hops (99.9 percent at
  1.44, the last system at 1.86). With records, several probes set out
  for a straggler and the nearest gets it (1.30 and 1.39).

### 2. How much foresight, and how late the records

Own cell first, 4,096 probes, two runs each. The columns give how late
the records are, in share times, on top of their travel at the speed of
light.

**99 percent done, in share times**

| Foresight | at once | 0.031 | 0.1 | 0.31 | 1 | 3.1 | 4.1 | never |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 1.20 | 1.24 | 1.31 | 1.44 | 1.67 | 1.73 | 1.73 | 1.73 |
| 80% | 1.17 | 1.19 | 1.21 | 1.26 | 1.36 | 1.38 | 1.38 | 1.38 |
| 95% | 1.16 | 1.17 | 1.17 | 1.19 | 1.23 | 1.23 | 1.23 | 1.23 |
| 99% | 1.16 | 1.16 | 1.16 | 1.16 | 1.18 | 1.18 | 1.18 | 1.18 |
| all | 1.16 | · | · | · | · | · | · | · |

**Last system, in share times**

| Foresight | at once | 0.031 | 0.1 | 0.31 | 1 | 3.1 | 4.1 | never |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 1.41 | 1.47 | 1.64 | 1.93 | 2.59 | 3.97 | 4.62 | - |
| 80% | 1.36 | 1.41 | 1.46 | 1.60 | 2.07 | 2.39 | 2.39 | - |
| 95% | 1.40 | 1.41 | 1.43 | 1.42 | 1.53 | 1.61 | 1.61 | - |
| 99% | 1.50 | 1.48 | 1.44 | 1.38 | 1.38 | 1.38 | 1.38 | - |
| all | 1.69 | · | · | · | · | · | · | · |

**Visits wasted**

| Foresight | at once | 0.031 | 0.1 | 0.31 | 1 | 3.1 | 4.1 | never |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 7% | 11% | 17% | 30% | 52% | 72% | 76% | 63% |
| 80% | 3% | 5% | 8% | 14% | 31% | 42% | 42% | 30% |
| 95% | 2% | 3% | 4% | 7% | 13% | 16% | 16% | 12% |
| 99% | 1% | 2% | 2% | 3% | 5% | 6% | 6% | 5% |
| all | 0% | · | · | · | · | · | · | · |

The "never" column wastes less than the two before it only because those
runs stop at 99.99 percent and the others go on to the last system. The
figures for 4,096 probes differ from those of the larger boxes above in
the last digit (1.23 against 1.24).

- **Foresight of 95 percent is enough.** With no records at all, a probe
  that has 95 percent of the others' choices right reaches 99 percent of
  the systems at 1.23 share times, against 1.16 with everything right
  and 1.20 with records at light speed and no foresight. It wastes 12
  percent of its visits.
- **Foresight makes late records matter little.** At 95 percent, records
  a whole share time late cost 6 percent at the 99 percent mark (1.23
  against 1.16). Without foresight the same delay costs 40 percent (1.67
  against 1.20).
- **The very last systems.** Without foresight the end waits for the
  records: where they are 3.1 and 4.1 share times late, the last system
  is done at 4.0 and 4.6. With 95 percent foresight the last system is
  done at 1.61 share times, before a record that late has arrived at
  all; with 80 percent, at 2.39. So at 95 percent the box is finished
  without any record. A box holds 410,000 systems, not a hundred
  billion; see Limits.

### 3. One thing changed at a time

4,096 probes; 1,728 for 300 systems per probe. Each entry gives the 99
percent mark / the last system / the visits wasted.

| Change | Own cell only | Cell first, records | Cell first, nothing known | Cell first, 95% foresight | Roam, records |
| --- | --- | --- | --- | --- | --- |
| none: the base case | 1.91 / 3.75 / 0% | 1.20 / 1.41 / 7% | 1.73 / - / 63% | 1.23 / - / 12% | 1.12 / 1.35 / 9% |
| 10 systems per probe | 2.22 / 3.71 / 0% | 1.51 / 1.95 / 24% | 1.96 / - / 67% | 1.43 / - / 20% | 1.56 / 2.01 / 31% |
| 30 systems per probe | 2.03 / 3.41 / 0% | 1.32 / 1.58 / 13% | 1.82 / - / 63% | 1.31 / - / 14% | 1.29 / 1.64 / 18% |
| 300 systems per probe | 1.83 / 3.05 / 0% | 1.11 / 1.22 / 3% | 1.68 / - / 59% | 1.17 / - / 10% | 1.04 / 1.17 / 4% |
| stay a quarter as long | 1.91 / 3.77 / 0% | 1.22 / 1.45 / 6% | 1.78 / - / 61% | 1.26 / - / 11% | 1.13 / 1.35 / 8% |
| stay twice as long | 1.90 / 3.73 / 0% | 1.18 / 1.36 / 7% | 1.68 / - / 65% | 1.21 / - / 12% | 1.11 / 1.30 / 9% |
| starts on a regular lattice | 1.14 / 1.41 / 0% | 1.11 / 1.23 / 2% | 1.14 / - / 18% | 1.11 / - / 4% | 1.10 / 1.34 / 8% |
| about ten starts at each region middle | 12.29 / 13.26 / 0% | 1.16 / 1.37 / 11% | 3.81 / - / 89% | 1.21 / - / 22% | 1.16 / 1.38 / 11% |
| 10% of the probes lost | 10% never surveyed | 1.34 / 1.55 / 7% | 3.07 / - / 87% | 1.38 / - / 15% | 1.24 / 1.44 / 8% |
| 50% lost | 51% never surveyed | 2.38 / 2.69 / 5% | 7.76 / - / 90% | 2.52 / - / 21% | 2.19 / 2.48 / 5% |
| 20% share start and identifier | 2.11 / 4.01 / 0% | 1.21 / 1.42 / 7% | 1.89 / - / 66% | 1.24 / - / 13% | 1.12 / 1.35 / 9% |
| a wasted visit costs a stay | · | 1.20 / 1.42 / 6% | 1.77 / - / 60% | 1.24 / - / 11% | · |
| stars drift | 1.93 / 3.51 / 0% | 1.20 / 1.39 / 7% | · | · | · |

- **Where the probes start matters more than anything they can know.**
  On a regular lattice every probe has a cell of the same size. Probes
  that keep to it and know nothing reach 99 percent at 1.14 share times,
  sooner than randomly placed probes with every record at light speed
  (1.20). Probes started together at the middles of regions of 1,000
  systems, about ten to each, need 12.3 share times if they keep to
  cells and 3.8 if they go on but know nothing; with records or
  foresight the bad start is repaired (1.16, 1.21).
- **Fewer systems per probe cost more per system.** A share of ten is
  all edge: 1.51 share times against 1.11 for a share of 300.
- **Lost probes cost their work and no more, if the others can tell.**
  With records, 10 percent lost gives 1.34 (the base case's 1.20 divided
  by 0.9 is 1.33) and half lost gives 2.38 (twice 1.20 is 2.40).
- **No effect:** the length of the stay, a stay charged for wasted
  visits, probes that share a starting point and an identifier (as long
  as records or foresight tell them apart), and stars that drift at 20
  kilometers per second on each axis.

### 4. Probes that are lost and not known to be

Share times until 99 percent of the systems are done.

| Rule | What a probe knows | 10% of the probes lost | 50% lost |
| --- | --- | --- | --- |
| own cell first | records at light speed | 1.34 | 2.38 |
| roam | records at light speed | 1.24 | 2.19 |
| own cell first | 95 percent worked out, no records, losses known | 1.38 | 2.52 |
| own cell first | everything worked out, losses known | 1.30 | · |
| own cell first | everything worked out, losses not known | 10.2% never surveyed | · |
| roam | everything worked out, losses not known | 10.2% never surveyed | · |
| own cell first | nothing | 3.07 | 7.76 |
| own cell only | nothing needed | 10.1% never surveyed | 51.3% never surveyed |

Foresight cannot see a lost probe. Where the others go on reckoning with
a tenth of the fleet that is not there, the systems those probes would
have taken are never surveyed: one system in ten, under either rule.
Records carry no such risk, because a system counts as done only when
its record has come. So foresight needs a rule that lets an unconfirmed
conclusion lapse, or some other way of learning that a probe is gone.
Overview section 3.2 has such a rule. The lapse itself was not
simulated, only the two ends of it: losses known, and losses never
known.

### 5. Does the size of the box matter?

| Probes in the box | Runs | Own cell first, records: 99% | last system | Own cell only: 99% | last system | largest cell, in systems |
| --- | --- | --- | --- | --- | --- | --- |
| 1,000 | 1 | 1.17 | 1.28 | 1.88 | 2.82 | 272 |
| 4,096 | 2 | 1.20 | 1.41 | 1.91 | 3.75 | 363 |
| 8,000 | 3 | 1.20 | 1.39 | 1.91 | 3.85 | 365 |
| 15,625 | 1 | 1.20 | 1.43 | 1.93 | 3.26 | 310 |

From 4,096 probes on, the 99 percent mark does not move. The last system
of "own cell only" does not settle and cannot: it waits for the largest
cell in the box, and among a billion cells the largest is larger still.

### 6. Starting points spread evenly

The specification seeds every probe in a region of its own (Physical
Layer section 4.5). In the simulation that is a regular lattice: every
probe has a cube of the same size to itself, and the systems fall into
the cubes by chance, so the shares still differ by about a tenth. 4,096
probes, two runs each, own cell first unless named. The lines for
starting points at random come from boxes of that size too, and differ
from result 1 in the last digit.

| What a probe knows of the others | Starts | Half | 90% | 99% | 99.9% | Last system | Visits wasted | 99% in years |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| everything, worked out in advance | spread evenly | 0.48 | 0.94 | 1.10 | 1.20 | 1.62 | 0% | 6,800 |
| everything, worked out in advance | at random | 0.49 | 0.96 | 1.16 | 1.40 | 1.69 | 0% | 7,200 |
| completion records at light speed | spread evenly | 0.48 | 0.94 | 1.11 | 1.16 | 1.23 | 2% | 6,800 |
| completion records at light speed | at random | 0.49 | 0.98 | 1.20 | 1.29 | 1.41 | 7% | 7,300 |
| 95 percent worked out, records at light speed | spread evenly | 0.48 | 0.94 | 1.10 | 1.16 | 1.27 | 1% | 6,800 |
| 95 percent worked out, records at light speed | at random | 0.49 | 0.97 | 1.16 | 1.25 | 1.40 | 2% | 7,100 |
| 95 percent worked out, no records | spread evenly | 0.48 | 0.94 | 1.11 | 1.18 | - | 4% | 6,800 |
| 95 percent worked out, no records | at random | 0.49 | 0.99 | 1.23 | 1.36 | - | 12% | 7,600 |
| 95 percent worked out, records 3 share times late | spread evenly | 0.48 | 0.94 | 1.11 | 1.18 | 1.29 | 6% | 6,800 |
| 95 percent worked out, records 3 share times late | at random | 0.49 | 0.99 | 1.23 | 1.36 | 1.61 | 16% | 7,600 |
| nothing | spread evenly | 0.48 | 0.94 | 1.14 | 1.24 | - | 18% | 7,000 |
| nothing | at random | 0.50 | 1.13 | 1.73 | 2.31 | - | 63% | 10,600 |
| nothing needed (own cell only) | spread evenly | 0.48 | 0.94 | 1.14 | 1.25 | 1.41 | 0% | 7,000 |
| nothing needed (own cell only) | at random | 0.50 | 1.19 | 1.91 | 2.54 | 3.75 | 0% | 11,700 |

**99 percent done, in share times**

| Foresight | at once | 0.031 | 0.1 | 0.31 | 1 | 3.1 | 4.1 | never |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 1.11 | 1.11 | 1.12 | 1.13 | 1.14 | 1.14 | 1.14 | 1.14 |
| 80% | 1.10 | 1.10 | 1.11 | 1.11 | 1.13 | 1.13 | 1.13 | 1.13 |
| 95% | 1.10 | 1.10 | 1.10 | 1.11 | 1.11 | 1.11 | 1.11 | 1.11 |
| 99% | 1.10 | 1.10 | 1.10 | 1.10 | 1.10 | 1.10 | 1.10 | 1.10 |
| all | 1.10 | · | · | · | · | · | · | · |

**Last system, in share times**

| Foresight | at once | 0.031 | 0.1 | 0.31 | 1 | 3.1 | 4.1 | never |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 1.23 | 1.27 | 1.33 | 1.43 | 1.43 | 1.45 | 1.45 | - |
| 80% | 1.26 | 1.26 | 1.26 | 1.30 | 1.33 | 1.34 | 1.34 | - |
| 95% | 1.27 | 1.26 | 1.24 | 1.25 | 1.29 | 1.29 | 1.29 | - |
| 99% | 1.35 | 1.32 | 1.29 | 1.25 | 1.26 | 1.25 | 1.25 | - |
| all | 1.62 | · | · | · | · | · | · | · |

**Visits wasted**

| Foresight | at once | 0.031 | 0.1 | 0.31 | 1 | 3.1 | 4.1 | never |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | 2% | 4% | 7% | 14% | 23% | 25% | 25% | 18% |
| 80% | 1% | 2% | 3% | 6% | 11% | 12% | 12% | 9% |
| 95% | 1% | 1% | 2% | 3% | 6% | 6% | 6% | 4% |
| 99% | 1% | 1% | 1% | 2% | 3% | 3% | 3% | 2% |
| all | 0% | · | · | · | · | · | · | · |

Other numbers of systems per probe and other lengths of stay, with
completion records at light speed (1,728 probes for 300 systems per
probe):

| Change | Evenly spread: 99% / last / wasted | At random: 99% / last / wasted |
| --- | --- | --- |
| none: a hundred systems per probe | 1.11 / 1.23 / 2% | 1.20 / 1.41 / 7% |
| 10 systems per probe | 1.33 / 1.68 / 16% | 1.51 / 1.95 / 24% |
| 30 systems per probe | 1.19 / 1.38 / 7% | 1.32 / 1.58 / 13% |
| 300 systems per probe | 1.06 / 1.14 / 1% | 1.11 / 1.22 / 3% |
| stay a quarter as long | 1.12 / 1.27 / 2% | 1.22 / 1.45 / 6% |
| stay twice as long | 1.09 / 1.20 / 3% | 1.18 / 1.36 / 7% |

Lost probes. Each entry gives the 99 percent mark / the last system /
the visits wasted:

| Rule | What a probe knows | 10% lost, starts spread evenly | 10% lost, starts at random | 50% lost, spread evenly | 50% lost, at random |
| --- | --- | --- | --- | --- | --- |
| own cell first | records at light speed | 1.31 / 1.52 / 5% | 1.34 / 1.55 / 7% | 2.26 / 2.56 / 5% | 2.38 / 2.69 / 5% |
| own cell first | 95 percent worked out, no records, losses known | 1.35 / - / 13% | 1.38 / - / 15% | 2.41 / - / 19% | 2.52 / - / 21% |
| own cell first | everything worked out, losses not known | 10.3% never surveyed | 10.2% never surveyed | · | · |
| own cell first | nothing | 2.98 / - / 87% | 3.07 / - / 87% | · | 7.76 / - / 90% |
| own cell only | nothing needed | 10.3% never surveyed | 10.1% never surveyed | · | 51.3% never surveyed |

- **Knowledge hardly matters any more.** Whatever a probe knows, 99
  percent of the systems are done between 1.10 and 1.14 share times.
  What knowledge still buys is the tail: the last system comes at 1.23
  to 1.62 share times, and the visits wasted run from none to 25
  percent.
- **The plan wastes one visit in a hundred.** With 95 percent of the
  others' choices worked out and records at the speed of light, the 99
  percent mark comes at 1.10 share times and the last system at 1.27,
  against 1.16 and 1.40 for starting points drawn at random. With
  records three to four share times late, which is what the archives
  alone would deliver, one visit in sixteen is wasted (1.11 and 1.29).
- **Lost probes undo part of the gain.** A lost probe leaves a hole in
  the lattice. With a tenth of the fleet lost the 99 percent mark comes
  at 1.31 share times with records, against 1.34 for random starts; with
  none lost it was 1.11 against 1.20. Probes that know nothing then need
  2.98 share times, almost as long as with random starts (3.07): an
  even start spares them the search for work, and a lost neighbor
  brings the search back. Probes that keep to their own region, or that
  go on reckoning with the lost ones, still leave a tenth of the systems
  unsurveyed.

## What it means in years

Share times multiplied by 6,139 years, to the nearest hundred, counted
from the moment the survey starts.

| Case (own cell first and starts at random unless named) | Half of the systems | 99 percent | 99.9 percent | Last system |
| --- | --- | --- | --- | --- |
| the plan: starts spread evenly, 95 percent foresight, records at light speed | 3,000 | 6,800 | 7,100 | 7,800 |
| the same with starts at random | 3,000 | 7,100 | 7,700 | 8,600 |
| starts spread evenly, 95 percent foresight, records too late to matter | 3,000 | 6,800 | 7,300 | 7,900 |
| the same with starts at random | 3,000 | 7,600 | 8,400 | 9,900 |
| records at light speed, no foresight | 3,000 | 7,400 | 8,000 | 8,500 |
| everything worked out in advance | 3,000 | 7,100 | 8,900 | 11,400 |
| nothing known | 3,000 | 10,700 | 14,300 | - |
| roaming from the start, nothing known | 3,400 | 23,300 | 40,600 | - |
| own cell only | 3,100 | 11,700 | 15,500 | 23,600 |
| own cell only, starts spread evenly | 3,000 | 7,000 | 7,600 | 8,600 |

The survey starts 978,000 years after departure. Against that the plan
adds 1 percent and the slowest case in the table 4 percent: the mission
lasts about a million years whatever the probes know.

## How the results are used

**In the calculator.** `plan0_pace.py` carries two tables made from
these runs, one for each way of starting (`STILL_FIELD_EVEN` and
`STILL_FIELD`; the last two commands at the end of this document print
them). For six levels of completion, from half to the last system, a
table holds the travel and the stays used up, for 10, 30, 100 and 300
systems per probe, for foresight of 0, 80, 95, 99 and 100 percent, and
for records from at once to never. The calculator reads it by
straight-line interpolation and gives it the weight of the share of
stars that do not mix while the survey lasts: 98.7 percent for a billion
probes, nil for ten thousand.

By default the calculator takes probes that start spread evenly, are
right about 95 percent of the others' choices, clear their own cell
first and hear of the work of the probes around them by beam, at the
speed of light (Physical Layer sections 2.2 and 4.2). A probe leaves
its records in a box in the system it has surveyed, so the mission ends
with the last system. The result, and the same for starting points
drawn at random (`--starts random`):

| | Years after departure | Years after the survey starts | The same, starts at random |
| --- | --- | --- | --- |
| Half of the systems | 981,400 | 3,000 | 3,000 |
| 90 percent | 984,300 | 5,800 | 6,000 |
| 99 percent | 985,300 | 6,800 | 7,200 |
| Every system: the end of the mission | 986,400 | 7,900 | 8,700 |

The calculator's figures differ from those of the previous section by up
to a hundred years. It counts travel and stays separately, at the mean
spacing of the galaxy model, and keeps a weight of 1.3 percent for the
laws of stars that mix.

With `--no-neighbor-beams` the records go through the archives alone.
They then reach the next probe 3.9 share times after the event, which is
after the survey has ended, so they play no part in it: 99 percent of
the systems after 6,900 years and the last after 8,000.

**In the specification.** Three of its rules rest on these results.

- A probe first works its own region and then takes the nearest system
  anywhere within reach (Overview section 3.2). That is "own cell first",
  the rule that stays useful when a probe knows little (results 1 and
  3).
- A probe may hold a system to be surveyed when a derivation from the
  common rule makes that at least 0.95 probable, and such a conclusion
  lapses if no record confirms it (Overview section 3.2; results 2 and
  4).
- Every probe is seeded in a region of its own (Physical Layer section
  4.5). That is the evenly spread start of results 3 and 6, and the
  calculator's default.

## Limits

- A box of a few thousand probes stands for a billion. That is sound for
  everything local. It cannot show the very last of a hundred billion
  systems, which is an extreme of a kind no box contains; the 99.9
  percent mark is the last one to lean on.
- Records are heard by every probe at the speed of light, as if
  broadcast. That is the most that messages could do. The specification
  relays a record over two hops at most, about two probe spacings
  (Physical Layer section 4.3). The probes that could go to the same
  system lie within that range, but the limit itself was not simulated.
- Foresight is a fixed share of the others' choices, known at once; the
  rest is never known unless a record comes. In a real fleet the doubt
  about another probe's choices would grow with time. The runs do not
  model that growth; they bracket it, from 80 to 100 percent.
- Evenly spread starts are a regular lattice in the simulation: regions
  of equal size, whose numbers of systems differ by a tenth by chance.
  Regions drawn up from a catalogue to hold equal work would differ
  less; lost probes make the layout uneven again (result 6).
- The density of systems is the same throughout a box. In the galaxy it
  changes over hundreds of parsecs, and a probe's share is less than ten
  parsecs wide.
- Not simulated: the scattering before the survey, probes lost while the
  survey lasts, records that are lost, the lapse of an unconfirmed
  conclusion, and the time a probe needs to speed up and slow down,
  which the calculator adds.

## The runs, and how to repeat them

There are 321 stored runs in two sets. The set `full` has 237 runs, for
results 1 to 5: boxes of 1,000 to 15,625 probes with 100,000 to 1.6
million systems each. The set `even` has 92 runs, for result 6, of which
8 are also in the full set: boxes of 4,096 probes on a lattice, and of
1,728 for 300 systems per probe. Together they follow 137 million
systems and 199 million arrivals. They were run on 15 November 2026 on a
desktop computer with eight cores, four of them fast, and 8 gigabytes of
memory. The full set took 1.6 hours with six processes, the other 0.4
hours with five.

To repeat them, from the top of the repository:

```
python plan0_sim.py --set full --estimate --processes 6
python plan0_sim.py --set full --out plan0_sim_results --processes 6 --hours 4.5
python plan0_sim.py --set even --out plan0_sim_results --processes 6 --hours 2
python plan0_sim.py --report --out plan0_sim_results
python plan0_sim.py --report --table --out plan0_sim_results
python plan0_sim.py --report --table --start lattice --out plan0_sim_results
```

The first command prints how long a set should take on the machine at
hand, without running anything. The second and third run the sets, stop
after the given hours at the latest, and skip every run whose result is
already in the folder. The fourth prints a table of the results. The
last two print the tables that `plan0_pace.py` carries, for starting
points drawn at random and for probes spread evenly.
