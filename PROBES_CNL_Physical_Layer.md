# PROBES CNL: Physical Communications Architecture

## Version 1.0.0

*How a billion probes can physically exchange PROBES CNL
messages across a galaxy, what that architecture demands of the
language, and which demands were considered and rejected. All
technology anchors are flown systems or historically discussed
agency and agency-adjacent studies documented in reputable
non-fiction; extrapolations are labeled as such. Error
correction, framing, and erasure coding are specified in the
companion `PROBES_CNL_Transport_Layer.md`.*

---

## 1. The Regime

| Quantity | Value | Consequence |
|---|---|---|
| Survey disc radius | ≈ 15 kiloparsecs (kpc) ≈ 4.6×10²⁰ m | crossing the disc takes ≈ 10⁶ years at nominal speed |
| Probes | 10⁹ | ≈ 100 star systems and ≈ 500 cubic parsecs per probe; the fleet fills the disc, ≈ 90 probes deep |
| Mean neighbor spacing s | ≈ 8 parsecs (pc) ≈ 2.4×10¹⁷ m | light travel time per spacing T_e ≈ 26 years |
| Probe cruise speed (studied concepts, 0.05–0.2 c) | nominal 0.1 c | probe transit per spacing T_t ≈ 260 years |
| Survey after activation | ≈ 10⁴ years | a star moves < 1 pc meanwhile: the field stands still |
| Consolidation cadence T_c | ~10⁴ years (≈ the survey itself) | archives record the survey; they do not steer it |
| Fleet-crossing light time | ~10⁵ years | no fact reaches the whole fleet while the survey lasts |

**The controlling fact: every exchange is a monologue.** With
one-way latency of decades to a neighbor and centuries to a
node, there are no handshakes, no acknowledgments, no
retransmission requests, no negotiation.
Every message must be complete, self-contained, and
self-describing on arrival — which is precisely the design
posture PROBES CNL inherited from BEYOND, now revealed as a
physical necessity rather than only a safety choice.

---

## 2. Channels

### 2.1 Radio (flown heritage)

Deep-space radio practice (23-watt transmissions received
across interplanetary distances by 70-meter-class ground
antennas) demonstrates the discipline but not the reach: scaled
to interstellar spacing, radio link budgets require
kilometer-class apertures or gigawatt power. Radio remains the
short-range channel — probe-to-lander, probe-to-cache at
approach distances.

### 2.2 Optical (flown demonstration, studied at range)

Deep-space optical communication was demonstrated in flight
from 2023 and, in 2024, across more than 3 astronomical units, and
laser-link scaling to interstellar ranges was studied in the
historically discussed literature on beamed-sail probe concepts.
An order-of-magnitude budget for neighbor-to-neighbor contact:

- 1.7 m transmit and receive apertures, 1 kW at ~1 μm
- diffraction-limited divergence θ ≈ λ/D ≈ 6×10⁻⁷ rad
- spot radius at 2.4×10¹⁷ m ≈ 1.4×10¹¹ m
- on-axis captured fraction (π·D_t·D_r / 4λd)² ≈ 9×10⁻²³
- received power ≈ 9×10⁻²⁰ W ≈ 0.4 photons per second

With photon-starved pulse-position modulation — at most 8 bits
per detected photon in the 256-slot format, before coding
overhead — that supports **of order 0.1–1 bit per second, best
case, between mutually known endpoints** — before pointing
losses. The rate goes as (D_t·D_r / d)². A custodial node lies
≈ 5 spacings from a probe and ≈ 10 from the next node (§3.2);
with 10 m apertures at the nodes, both of those links hold
about the same rate or better.

Two conclusions fall straight out:

1. **Beams point at catalogued nodes, and at a probe whose
   stops the sender can work out.** A probe cannot maintain
   ephemerides for 10⁹ moving peers; it can hold the catalogued
   position and velocity of a cache node, and it can derive
   from `PROC-1` the star at which a neighbor will be. Nodes
   are not at rest: they share the motion of their host stars,
   tens of kilometers per second relative to one another.
   Across the ≈ 260-year light time between two nodes, a
   transverse 30 km/s amounts to ≈ 1,600 astronomical units, a
   thousand radii of a node's beam, so pointing ahead needs
   relative velocities to ≈ 30 m/s — a `CAT-CCH` entry, refined
   at every consolidation cycle. A probe's beam is six times as
   wide and needs the velocity of the star at which its
   neighbor stops to ≈ 180 m/s — a `CAT-TGT` entry (CONS-4).
2. **The wire form is not an optimization; it is the channel's
   admission ticket.** At bits per second, a 500-byte PROBES-W
   survey message costs about an hour of link time; the same
   message in expanded H-form costs three. Manifests and
   digests — bytes, not kilobytes — dominate what actually
   crosses the beams.

### 2.3 Physical carriage (flown heritage)

Bulk data — imagery, full datasets, consolidated archives —
travels as matter: durable media carried by probes and
deposited at caches. This is flown practice, not speculation: a
sample depot of ten individually catalogued containers was
placed at a documented site on another planet in 2022–2023, and
long-duration archival media exist as engineering artifacts
(nickel microetching carried on a comet lander; laboratory
femtosecond-written fused-silica storage rated for geological
timescales). Data carried as physical cargo has enormous
bandwidth; its latency is the probe's own travel time — acceptable for archives, useless
for coordination facts, which is exactly the split the language
already makes between E-ACT/manifest traffic and ARC archives.

---

## 3. Cache Nodes and Archive Siting

A **cache node** is a passive, durable, catalogued site holding
message media and, optionally, a low-power custodial device.

### 3.1 Three tiers

| Tier | What | Where | Power |
|---|---|---|---|
| **L1 — custodial archive nodes** | active nodes: consolidation, manifest broadcasts, scrubbing, inter-node beaming | wide orbits of quiescent, long-lived low-mass stars in inter-arm disc regions | stellar flux (photovoltaic/thermal) |
| **L2 — passive caches** | unattended media deposit sites on survey routes | in the surveyed system itself where it meets criterion 1, so that a deposit costs no side trip; otherwise anywhere dynamically stable, including deep interstellar space | none (double replication, Transport §5) |
| **L3 — cold vaults** | write-rarely archive replicas for deep time | long-period halo orbits, far from disc traffic and hazards | none |

The tier is an attribute in `CAT-CCH`, not a grammar
distinction — all three answer to the same `CCH-*` namespace,
manifest register, and templates.

### 3.2 Siting criteria (all catalogue-encoded, all objective)

1. **Dynamical stability ≥ 10⁶ years.** Excludes globular
   clusters and the inner bulge (encounter rates), open
   clusters (they disperse), and tight multiple-star systems.
2. **Radiation quiet.** Excludes star-forming regions and
   groupings of hot young massive stars (supernova rate), the galactic-center region
   (density, flaring of the central object), and flare-active
   young dwarfs. Prefers old, quiescent low-mass dwarf stars —
   characterized in-language numerically, never by
   classification letter (§3.3).
3. **Power for L1.** Custodians need renewable flux → orbits
   close enough to a quiet star for photovoltaics, wide enough
   for thermal stability.
4. **Beacon geometry.** Unobstructed sightlines to ≥ 4 timing
   beacons; optical inter-node paths avoiding dense molecular
   clouds (extinction).
5. **Shallow gravitational potential.** PTS reduction assumes
   weak fields; nodes avoid close orbits of massive or compact
   objects so local clock offsets stay inside the timing-model
   budget (`PROC-NAV`).
6. **Graph placement.** ≈ 10⁶ custodial nodes, one to ≈ 10³
   probes: node spacing ≈ 10 s ≈ 80 pc, within the reach of the
   link budget for a probe's beam and for the next node's
   (§2.2). The nodes keep the archive and do not steer the
   survey (§1), so their number follows from link range and
   from the safe keeping of the records, not from the probe
   spacing; shard hosts ≥ 2 graph edges apart (Transport §6).

Net result: the engineering optimum is the calm mid-disc
annulus between spiral arms — old stars, low supernova rate,
low encounter rate — with halo fringe for L3.

### 3.3 Does siting leak the origin? Does it touch the language?

The quiet annulus of criterion 2 overlaps the galactocentric
radius where the origin system happens to sit — the same
band the peer-reviewed "galactic habitable zone" literature
identifies as calmest. This is not a leak, and the reason
matters: **the criteria are objective, public, and
catalogue-encoded, so placement is evidence of engineering
optimization, not of provenance.** Any fleet from any origin
would site archives in the same annulus; an interceptor learns
what good engineering looks like, which it already knew. What
*would* leak is temporal structure — which nodes came first —
and that is closed off by rule, not geography (§4.5).

Language consequences of siting (locations in the core
documents cited per item):

- **`custodian`** carries a device-only pin in the lexicon
  ("device that maintains a cache node"), needed for manifest
  and procedure definitions; the human institutional role
  remains excluded with the other institution-class nouns
  (Lexicon §4.3, §5.1).
- **Galactic-structure vocabulary** — the nouns `halo` and
  `spiral-arm` and the adjective `quiescent` (Lexicon §5.1,
  §5.3); siting and survey discourse both need them.
- **Stellar classification letters are inexpressible.** The
  traditional letter classes are an origin-culture taxonomy
  (and single capital letters are not tokens); stars are
  characterized numerically: effective temperature in kelvin,
  luminosity in watts, mass in grams.
- **ORG-3:** structural catalogues (`CAT-CCH`, `CAT-REG`,
  `CAT-TGT`) carry no establishment, founding, or first-visit
  epochs.
- Gravitational-potential and beacon-geometry criteria touch
  `PROC-NAV` budgets and `CAT-CCH` schema — catalogue content,
  zero grammar.

**The anti-record.** The one flown precedent for a deliberately
interceptable deep-space artifact is a golden phonograph record
whose entire purpose was to disclose its makers' location,
biology, and culture. The fleet's caches are its exact inverse:
maximally informative about the galaxy, structurally silent
about the origin. Same medium philosophy, opposite information
flow — and the inversion is enforced by grammar, not by
custodial discretion. Every node also stores `CAT-SPEC` — the
language specification itself — so the lexicon's
self-describing property operates as the bootstrap key for any
future reader.

---

## 4. Store-and-Forward Topology and the Hop Limit — Derivation

Traffic pattern: **probe → neighboring probe** and **probe →
cache → probe**, occasionally **probe → cache → probe →
cache**, with custodial nodes also beaming to adjacent nodes.
The E-RLY rule (warning at hops=2, rejection at hops≥3) is
derived here rather than assumed. One clarification first:
**the limit is not about fidelity.** Digest citation (E-RLY-3)
makes relaying lossless, so h could be 50 without corrupting a
byte. The limit is about three things that all worsen with h —
channel economics, adversarial containment, and topology
privacy — against one benefit that saturates.

### 4.1 What relaying is for

Gossip (E-RLY) exists to move **coordination-relevant facts**
— survey completions (E-ACT), local hazards, cache manifests —
to the probes that can act on them *sooner than the archive
cycle would*. Everything else (science payloads, beacon timing
models, resource surveys) is archive traffic (E-RPT), which has
its own provenance chain and no gossip role.

### 4.2 The audience of a coordination fact

Take the canonical case: probe A completes a system and beams
the E-ACT record to its neighbors and to its nearest node. Who
needs it? Exactly the probes that might otherwise go to that
system. A probe works its own region first and then takes the
nearest system it does not hold to be surveyed (Overview §3.2),
so the systems of A's region fall to A or, where A lags or is
lost, to the probes around it. Those lie about one spacing from
the region and within ~2 spacings of one another. A probe
farther out has open systems nearer by, in its own region and
around it, and by the time it has none the probes next to A's
region have had the same choice for as long and from closer. So
the **relevance radius of gossip is R_rel ≈ 2s**: inside it a
fact changes what a probe does next; outside it nothing depends
on the fact.

The archive does not shorten that radius: T_c is as long as the
survey (§1), so no coverage archive reaches a probe while work
is left. In a fleet whose survey outlasts many cycles the
archive sets the radius instead — gossip then matters only
where a probe can act before the archive delivers the fact,
within ≈ k·T_c / T_t spacings for an archive that needs k
cycles.

### 4.3 Benefit and cost as functions of h

The fleet fills the disc, so the graph of neighboring probes is
three-dimensional: on a regular lattice a probe has six nearest
neighbors (degree d ≈ 6), and a fact relayed to graph distance
h covers a ball of radius ≈ h·s.

| h | Competitor ball covered (≈ min(1,(h/2)³)) | Marginal benefit | Per-probe relay load (∝ h³) | Single-source contamination radius | Propagation-tree evidence at any node |
|---|---|---|---|---|---|
| 1 | ~12% | — | 1× | s (~7 probes) | 1 edge |
| **2** | **~100%** | **+88 points** | **8×** | **2s (~33 probes)** | **2 edges** |
| 3 | 100% (nothing beyond 2s depends on the fact) | ~0 | 27× | 3s (~120 probes) | 3 edges |
| 5 | 100% | ~0 | 125× | 5s (~500 probes) | 5 edges |

**Why not h = 1.** Coverage of the competitor ball is ~12%:
most probes that could collide with A's work never hear of it
before choosing. Expected duplication is material — a visit to
a system already surveyed costs ≈ 50 years of probe time plus a
stellar refueling stop (§6), and around a lost probe's region a
hundred systems are shared out among probes that are mostly not
each other's nearest neighbors. The dedup benefit between h=1
and h=2 is the whole point of having relay at all.

**Why not h = 3–5.** The audience gained beyond 2s has no use
for the fact (§4.2): marginal benefit ≈ 0. Meanwhile every cost
keeps climbing on the photon-starved links where each relayed
clause displaces original content: relay load grows as h³, a
compromised probe's false-but-well-formed facts (grammar cannot
stop a lie, only an unverifiable one) quarantine at radius h·s
instead of 2s, and each additional hop extends the
propagation-tree evidence an interceptor at one cache can
reconstruct about fleet topology. Benefits saturate at h=2;
every cost is monotone increasing — the knee is at 2.

**Why the warning band at h = 2.** Hop 2 is legal-but-flagged
because it is the boundary case: content at hop 2 has reached
the edge of its audience and is the next archive's to
supersede, and the flag tells receivers "verify against the
next archive before building on this."

The limit and the regime are a matched pair: **h_max =
⌈R_rel / s⌉ = 2 holds because the survey ends within one
consolidation cycle, among stars that stand still.** If the
fleet were so much smaller that its survey outlasted many
cycles, R_rel and h_max would be re-derived from the inequality
of §4.2 — the number 2 is a consequence, not a constant of
nature.

### 4.4 Adversarial containment (the quarantine argument)

The grammar excludes manipulation *vocabulary*, but a
compromised probe can still emit false measurements in perfect
PROBES CNL. The hop limit is the containment vessel: a false
fact reaches at most ~33 probes before the consolidation cycle
applies the corroboration rule — **CONS-2:** archive entries
carry corroboration counts (independent originating senders per
claim, an ordinary E-AGG `n=`), and uncorroborated singletons
are flagged in the archive and excluded from procedure
triggering (e.g., a resource claim with n=1 cannot satisfy
`PROC-RCH` preconditions, §6.4). At h=2 the lie is a local
event; at h=5 it is a regional one.

### 4.5 The expansion wavefront — concealing a non-central start

The fleet does not begin at the galactic center; it enters from
one region (the origin system sits at an unremarkable
mid-disc radius). Nothing in any message names that place — but
**activity patterns can betray what vocabulary cannot**:

- *Wavefront attack:* coverage archives sampled at two epochs
  show a growing disc of surveyed systems; fitting circles to
  the two fronts locates the common center — the entry point.
  This works even with perfect per-message origin erasure.
- *Founding-order attack:* cache establishment dates, earliest
  manifest entries, or lowest archive sequence numbers order
  the nodes outward from the entry.

Countermeasures, in force from the first transmitted bit:

1. **Dispersal doctrine (`PROC-DSP`).** Before survey
   operations begin, every probe transits to its seed region:
   the one region that `CAT-REG` pairs with its probe
   identifier. The tessellation has as many regions as the
   fleet has probes, each holding equal survey work, and the
   pairing is drawn at random — one probe per region, blind to
   entry proximity. Survey then grows from 10⁹ seeds, and the
   activity pattern is statistically homogeneous from the first
   message: there is no front to fit. **DSP-1:** no messages
   during dispersal. **DSP-2:** no message-recorded
   observations before `T_act` (transit navigation is
   journal-local); recorded survey begins at the seed, at
   `T_act`, for every probe alike. **DSP-3:** message emission
   fleet-wide begins at a catalogue activation epoch `T_act` ≥
   the dispersal envelope. The envelope is the disc diameter
   divided by the cruise speed, the longest leg possible from
   any entry point. No smaller value is origin-blind: an
   envelope sized to the fleet's own longest leg would encode
   the entry radius, and a probe that began recording on
   arrival would date its first observation by its distance
   from the entry. The cost is real — every probe waits
   ≈ 1×10⁶ years at nominal speed (≈ 30 kpc at 0.1 c) before
   its first recorded observation — and it is the price of an
   origin-free sky. The tempting shortcut (each probe takes the
   *nearest* unclaimed seed) is rejected: it recreates the
   cluster around the entry that dispersal exists to erase.
2. **ORG-3** (§3.3): no establishment epochs in structural
   catalogues.
3. **CONS-1:** coverage aggregates record completion *status*,
   never completion *epochs* — deduplication needs the fact,
   not the date. (Aggregation is a new derived record, so
   projecting fields is legitimate; relay's no-alteration rule
   is untouched.)
4. **MAN-H:** custodians prune manifest history beyond a fixed
   horizon (superseded by archives anyway), so no single node
   accumulates a founding chronology.
5. Hop metadata was already stripped (TRJ-3); the h=2 cap
   bounds propagation-tree evidence per §4.3.

**Honest residuals.** Scientific observation epochs must stay
accurate (transients, proper motions), so archives weakly
encode *when probes were where* — made origin-uninformative by
dispersal, since the where-when pattern has no privileged
center. And probes in flight are physically observable objects;
an interceptor tracking hulls rather than messages sits outside
what any language can control. The claim defended here is
precise: **the message corpus, the catalogues, and the traffic
pattern are jointly origin-free.**

**Acknowledgment by manifest** (unchanged): a probe learns that
its message survived — the only "delivery receipt" possible at
these latencies — when a later manifest broadcast lists its
`MSG-*` identifier. No acknowledgment grammar exists or is
needed.

---

## 5. Navigation and Time

Pulsar-based navigation is flown technology: an X-ray
pulsar-timing experiment on a space station instrument
demonstrated autonomous position fixes of order 10 km in 2018.
The GSF/PTS design (Overview §4.2–4.3) is therefore a scaling
of demonstrated practice, not an invention.

Two physical facts feed back into the language:

1. **Pulsars age.** Spin-down is secular and measurable
   (corpus C-49), and glitches happen. `CAT-BCN` timing models
   will be revised for as long as the fleet operates — so **a
   message is only interpretable relative to the catalogue
   versions it assumed**. Hence the mandatory `catalogues:`
   version-pinning field (FRONT-5).
2. **Probes move fast.** Historically discussed probe concepts
   span 0.05–0.2 c (fusion flyby studies, beamed-sail studies);
   at such speeds pulsar phases arrive Doppler-shifted and
   proper time diverges from coordinate time. The remedy is
   procedural, not grammatical: epochs and positions in
   messages are **GSF-coordinate values after reduction** via
   the timing models, and the reduction procedure is itself a
   catalogue entry (`PROC-NAV`). Clauses never carry raw
   onboard clock values. Siting criterion 5 (§3.2) keeps
   custodial clocks inside the same weak-field budget.

---

## 6. Energy and Duty Cycle

### 6.1 The star-hopping profile

Radioisotope generators have powered probes for 45+ years
(flown); kilowatt-class space fission was ground-demonstrated
in 2018; multi-year full hibernation is flown practice (a comet
mission slept 31 months and woke on schedule). None of that
reaches 10⁴-year cruise legs on stored charge — so the mission
profile must close the energy loop at stars, and it naturally
does: **the survey targets are the refueling stops.** The
target-selection rule (`PROC-1`) selects among unsurveyed
systems only those reachable within the current energy budget
`E_leg` — a public catalogue rule evaluated on local state, so
routing stays sender-invariant without any probe disclosing
that state. Dispersal legs close the loop the same way: their
refueling stops fall under DSP-2 and leave no recorded
observation.

### 6.2 Storage and fuel

Chemical storage self-discharges and radioisotopes decay on
century scales; the only millennia-grade "battery" physics
offers is **nuclear fuel, which does not self-discharge**.
The profile: fission or fusion plant idling at watts during
cruise (dormancy, §6.3), full power at stops; replenishment by
in-situ fuel harvesting — anchored to the historically
discussed literature: the 1978 British Interplanetary Society
fusion-probe study proposed helium-3 aerostat mining at a giant
planet, and deuterium is ubiquitous (the fleet measures
deuterium-to-hydrogen ratios as ordinary survey products — corpus C-28). Icy bodies
and giant-planet atmospheres are therefore both science targets
and fuel depots. The demand is set by the speed: every stop
costs a velocity change of twice the cruise speed, so at 0.1 c
a probe leaves each system with ≈ 9.5 times its empty mass even
at an exhaust speed of 0.089 c, the ideal limit for fusion of
deuterium and helium-3. The open engineering risk, flagged
honestly: in-situ isotope separation at probe scale is the
least-anchored element of the whole architecture. Within star
systems,
photovoltaic/thermal power is trivial by comparison (~1.4 kW/m²
at Sun-like flux distances).

### 6.3 Duty cycle and communication slots

Default state: dormancy. Wake classes: (a) navigation fixes
(pulsar timing, attitude), (b) survey operations at stops,
(c) communication windows. The windows need no negotiation:

- The **local received phase** of a designated beacon defines
  each node's slot grid — slots are position-local, so no
  synchronization spans light-years.
- A transmitting node schedules emission so that *arrival* at
  the target node falls inside the target's local slot, using
  the catalogued inter-node distance — which is why catalogue
  version pinning (FRONT-5) is load-bearing: a stale `CAT-BCN`
  breaks slot arithmetic, not just timestamps.
- Guard bands absorb timing-model error; slot quantum and
  offsets are `CAT-SLT` constants; emissions are padded to the
  quantum with repair symbols (Transport TR-4).

Dormant probes wake for the slots of nodes within link range
along their route — a deterministic function of public
catalogue data plus their own journal, nothing exchanged.

### 6.4 Energy information policy — what is shared

The user-facing question: should energy-source information live
in archives and flow between probes? Split it the way the
language splits everything — facts about the world versus facts
about the sender:

**Shared, and already expressible: the environment.** A star's
effective temperature and luminosity (numbers, never
classification letters — §3.3), flare event rates (per
gigasecond), circumstellar dust density, giant-planet presence,
deuterium-to-hydrogen ratios, ice inventories. These are ordinary survey products
serving double duty: the science *is* the fuel prospecting.
They consolidate into per-region **resource archives** (an
`ARC-*` series, no new namespace), and a registered threshold
family `THR-NRG-*` lets the existing hazard pattern run in
reverse as an adequacy record:

```measurement
The deuterium fraction of the atmosphere of `TGT-2231` equals 2.6e-5 (measured, `MSP-1`, 1-sigma).
```

```constraint
Procedure `PROC-RCH` applies at deuterium fraction above threshold `THR-NRG-2` (defined).
```

No recommendation, no "good refueling site" — a measurement and
a registered applicability rule, which is all a deterministic
fleet needs. Spoofing defense: **CONS-2** (§4.4) keeps
uncorroborated resource claims (n=1) from satisfying `PROC-RCH`
preconditions, and the procedure itself sequences local
verification before any point-of-no-return commitment — a fake
oasis broadcast by a compromised probe strands nobody.

**Never shared: the probe's own tank.** Reserve levels,
consumption rates, component condition — inexpressible, by
rule **SELF-1** (Grammar §5.4a): quantities
predicated on the sending probe's internal state are
non-compliant; the sender appears in clause content only as the
actor of execution records or in single-epoch geometry of the
kind already permitted. Four reasons converge:

1. **Sender-invariance:** internal state is not a function of
   observations; two probes with identical data would produce
   different messages.
2. **Capability disclosure:** fleet endurance and reserve
   margins are exactly what TH-1/TH-2 adversaries want.
3. **Zero actionable value:** no tasking and no rescue exist;
   nobody can act on "P-7F3A9C21 is at 12%," so the disclosure
   buys nothing.
4. **Covert channel:** a free-form numeric self-report is an
   open side channel through an otherwise canonicalized
   message.

Fleet-level attrition remains legitimately inferable the
aggregate way: consolidation notices which regions stopped
producing E-ACT records and publishes attrition statistics as
ordinary E-AGG — population facts, not probe dossiers.

### 6.5 Net language impact

SELF-1 in the grammar; `custodian`, `halo`, `spiral-arm`,
`quiescent` in the lexicon; `THR-NRG-*` and `PROC-RCH`/
`PROC-DSP` as catalogue content; **zero** new envelope fields,
E-tags, or registers. The energy loop runs on machinery the
language already had.

---

## 7. Data Integrity

The layering is strict, and the detail now lives in the
companion specification:

```
[ physical channel / storage medium ]
[ TP: framing + forward error correction + erasure coding ]
                        <- PROBES_CNL_Transport_Layer.md
[ PROBES-W canonical bytes ]            <- digest computed HERE
[ PROBES-H expansion ]                  <- generated on demand
```

Digests verify **after** transport decode, over canonical wire
bytes, so integrity semantics never depend on channel or
medium. The transport document specifies the link profile
(PPM + concatenated inner code + rateless fountain outer code —
the natural coding discipline for a feedback-free channel), the
media-at-rest profile (Reed–Solomon product codes, spatial
interleaving, triple replication, custodial scrubbing), the
cross-cache erasure profile ((5,3) sharding across nodes ≥ 2
edges apart), the fragment-quarantine rule, and the uniformity
and emission-discipline rules (TR-1…TR-5) that keep transport
free of covert channels.

---

## 8. Implications for PROBES CNL

### 8.1 Requirements the architecture places on the language

| Requirement | Where it lands | Driven by |
|---|---|---|
| `CCH-` cache namespace, `caches:` envelope list | Lexicon §6; Grammar R-20 | §3 |
| `EP-*` declared epochs, `epochs:` envelope list | Lexicon §6; Grammar §5.3, R-21 | §5; dated events |
| Mandatory catalogue version pinning | Grammar FRONT-5 | §5.1; §6.3 slot arithmetic |
| `manifest` register + cache-presence template | Grammar §6.5 (C-10); Wire T20 | §3, §4.5 |
| Compound-unit exponent notation | Wire §5.2 | §2.2 economy |
| Digest computed after transport decode | Wire §7; Transport TR-2 | §7 |
| Sender internal state inexpressible | Grammar SELF-1 (§5.4a) | §6.4 |
| Cache-maintenance, galactic-structure, and stellar-activity vocabulary; numeric-only stellar characterization | Lexicon §5.1, §5.3, §5.5 | §3.3, §6.4 |
| Epoch-free structural catalogues and coverage aggregates; corroboration counts; manifest horizon | Grammar ORG-3, CONS-1, CONS-2; custodial rule MAN-H | §4.4, §4.5 |
| Transport uniformity and quarantine discipline | Transport TR-1 … TR-5 | §7 |
| Dispersal doctrine `PROC-DSP` (DSP-1…DSP-3, activation epoch) and `PROC-RCH`, `THR-NRG-*` | catalogue content, zero grammar | §4.5, §6.4 |

### 8.2 Confirmed as-designed (no change)

- **Monologue grammar.** No interrogatives-as-speech-acts, no
  handshake or acknowledgment forms — physically superfluous
  (§1, §4.5) and safety-positive.
- **Relay depth ≤ 2 — derived, not assumed.** h_max =
  ⌈R_rel/s⌉ = 2 for a survey that ends within one consolidation
  cycle; re-derivable if fleet size, cadence or cruise speed
  change (§4.3).
- **Self-describing lexicon.** Promoted from design goal to
  operational bootstrap requirement; `CAT-SPEC` at every cache
  (§3.3).
- **Wire-form-first economics.** The compact form is what makes
  optical links usable at all (§2.2).
- **Dormancy vocabulary and procedural scheduling** (§6.3).

### 8.3 Considered and rejected

| Candidate | Rejection rationale |
|---|---|
| Sender `velocity:` envelope field | A position–velocity pair enables trajectory extrapolation — the exact leak TRJ-1…3 exists to prevent. Receivers measure Doppler directly at the physical layer. |
| Energy/consumable state reporting | Superseded by SELF-1: zero actionable value, capability leak, covert channel, sender-invariance violation (§6.4). |
| Acknowledgment / receipt grammar | Manifests already provide receipts as registered facts (§4.5); a dedicated form would add an addressee-shaped speech act the deny-list exists to exclude. |
| Priority or urgency markers | Urgency vocabulary is alarm vocabulary — inexpressible by design (TH-2/TH-3 threat model). Scheduling relevance derives from catalogue rules applied to registered facts. |
| Raw onboard-clock timestamps | Frame- and probe-specific; violates sender-invariance; reduce via `PROC-NAV` (§5). |
| Hop limits above 2 | Benefit saturates at h=2 while relay load, contamination radius, and topology evidence keep growing with h (§4.3). |
| Hop limit of 1 | Leaves ~88% of the competitor ball uninformed; visits to systems already surveyed are the waste that relay exists to prevent (§4.3). |
| Nearest-unclaimed-seed dispersal shortcut | Recreates the activity cluster around the entry point that dispersal exists to erase (§4.5). |
| Stellar classification letter vocabulary | Origin-culture taxonomy; numeric characterization is strictly more precise anyway (§3.3). |
| Establishment epochs in `CAT-CCH`/`CAT-REG` | Founding-order attack (§4.5); deduplication needs status, not dates. |

---

*End of PROBES CNL Physical Communications Architecture
v1.0.0.*
