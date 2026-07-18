# PROBES CNL

A controlled natural language for inter-probe messaging across an autonomous exploration fleet. Derived from BEYOND CNL v0.4
(Lexicon v0.4.2, Evidential System and Envelope Grammar v0.4.1).

See BEYOND CNL:

[BEYOND Intro](https://github.com/alex987654/BEYOND)

Overview and Design Rationale for PROBES CNL

Version 1.0.0

---

## 1. Scenario and Purpose

Ten thousand autonomous probes travel a galaxy to survey its
stars, planets, and interstellar medium. Probes exchange messages
in a controlled natural language directly, through relay chains,
and through physical caches left at fixed sites.
Messages must remain useful to other probes,
harmless to the probes' planet of origin and its inhabitants,
and interpretable by human synthesizers who later assemble the
fleet's findings into exploration reports.

PROBES CNL is the language of that traffic. Like its
parent BEYOND CNL, it achieves safety **through grammar, not
policy**: the vocabulary and syntax needed to express unsafe
content do not exist in the language.

---

## 2. How the Threat Model Differs from BEYOND

BEYOND CNL conceals the sender's identity, location, values,
intentions, and capabilities from a recipient of arbitrarily
higher capability. A probe fleet inverts several of those
requirements and keeps others:

| Property | BEYOND CNL | PROBES CNL |
|---|---|---|
| Sender identity | Inexpressible | **Required** — opaque random probe ID in the envelope, nowhere else |
| Location of observations | Inexpressible | **Required** — Galactic Standard Frame coordinates |
| Location of origin (home system, makers) | Inexpressible | **Inexpressible** — reinforced (§4) |
| Intent | Inexpressible | **One constant**: the fleet-wide plan `PLAN-0` (§3) |
| Tasking other agents | Inexpressible | Inexpressible — coordination is emergent (§3.2) |
| Evidential coverage | 0.4 mandatory | 1.0 mandatory |
| Efficiency | Secondary | Primary co-goal — wire codes, templates, canonical units |

### 2.1 Threats addressed

**TH-1 — Interception by unknown third parties.** Any message may
outlive its channel and be read by an entity the fleet never
modeled. Countermeasure: origin-erasure rules (§4) make the
origin system, the makers, and the launch history inexpressible;
coordinates and epochs use only galaxy-anchored references.

**TH-2 — Compromised or spoofed probes.** A captured or defective
probe writes in the same language as everyone else.
Countermeasure: the language contains no imperatives addressed
to other agents, no suasive or deontic vocabulary, and no
expressible tasking, so a hostile author cannot command,
persuade, or panic the fleet; relay depth is bounded; message
digests make alteration detectable.

**TH-3 — Contamination of human synthesis.** Reports return to
human (or AI-assisted) readers who must not be manipulable by
message content. Countermeasure: no second-person forms, no
addressee vocabulary, no evaluative or affect vocabulary;
every clause carries an evidential tag, so synthesis pipelines
can weight or filter claims mechanically by evidential tier.

**TH-4 — Origin back-inference.** Even without explicit origin
references, trajectory histories, launch epochs, calendar
units, and origin-derived measurement units can be inverted to
locate the home system. Countermeasure: trajectory-anonymity
rules, the Pulsar Time Standard, and removal of every
origin-derived unit from the lexicon (§4.3).

### 2.2 Scope

- The language family (English-derived) reveals information about
  the makers. This is accepted by design: human interpretability
  of expanded messages outranks linguistic forensics resistance.
- Covert channels are reduced, not fully eliminated. Canonical
  ordering, clause templates, and sender-invariance shrink the
  free variation available for steganography; residual freedom
  (which observations a probe chooses to report) remains.
- Cryptographic authentication is out of scope for a language
  specification. The wire envelope reserves fields for whatever
  attestation scheme the fleet deploys.

---

## 3. The One Plan To Rule All Probes Doctrine

BEYOND bans intent because differential intent leaks who you
are. A probe fleet cannot ban intent outright: the mere choice
and quantity of procedures a probe reports would still reveal
intent implicitly. PROBES CNL therefore **canonicalizes intent
instead of concealing it**: exactly one plan exists, it is a
constant of the language specification, and every message
references it.

```
The fleet surveys the stars, planets, and interstellar medium
of this galaxy and records the results for later analysis
(stipulated, for `PLAN-0`).
```

Because `PLAN-0` is identical across all probes and all
messages, referencing it carries **zero differential
information** — the sender-invariance property (§5) is
preserved. No other plan identifier may exist (linter rule
PLAN-2); goal, purpose, and desire vocabulary remain absent
from the lexicon, so no second intent can be composed in prose.

### 3.1 The Procedure Catalogue

The fixed annex of `PLAN-0` is the fleet-wide **Procedure
Catalogue** (`CAT-PROC`), a public library of registered
procedures `PROC-1`, `PROC-2`, … Every probe carries the same
catalogue. Messages reference procedures by identifier instead
of restating steps. This serves both goals at once:

- **Intent flattening.** All probes select from the same public
  menu, so the set of procedures in a message reveals which
  catalogue entries ran — nothing more.
- **Compression.** A catalogue reference costs one identifier
  instead of a procedure section.

Novel procedures remain expressible (declared locally in the
message envelope, written method-only), and enter the catalogue
at the next consolidation cycle.

### 3.2 Coordination without tasking

No probe can instruct another. Coordination emerges from shared
facts plus shared deterministic rules:

1. A probe publishes **execution records** (E-ACT, §see grammar
   doc): "survey of region `REG-4471` completed per `PROC-12`."
2. The catalogue procedure `PROC-1` (region selection) contains
   a deterministic rule: from the regions with zero completion
   records visible to the probe, select by the fixed ordering
   in `CAT-REG`.

Every probe applying the same rule to the same facts makes
compatible choices. No imperative ever crosses the channel.

---

## 4. Origin Erasure

The grammar makes reference to the origin system structurally
impossible. Four mechanisms:

### 4.1 No proper nouns

PROBES CNL bans **all** proper nouns (BEYOND banned only proper
nouns of groups). Stars, planets, regions, instruments, and
probes are designated by typed catalogue identifiers
(`TGT-1088`, `REG-4471`, `BCN-3`, `P-7F3A9C21`). The home
galaxy is "this galaxy." The words for the origin star, the
origin planet, and the makers do not exist; the noun `origin`
itself is removed from the lexicon.

### 4.2 Galactic Standard Frame (GSF)

All positions use one right-handed Cartesian frame anchored to
galaxy-level observables:

- **Center:** the central massive compact object of this
  galaxy, registered as beacon `BCN-0`.
- **Plane:** the disc plane of this galaxy; +Z chosen such that
  the disc rotation, viewed from +Z, runs clockwise.
- **+X axis:** direction from `BCN-0` toward beacon `BCN-1`,
  projected onto the disc plane.
- **Unit:** the meter, with SI prefixes (`petameter`,
  `exameter`, `zettameter`).

No frame centered on the origin system is definable in the
language.

### 4.3 Pulsar Time Standard (PTS) and unit scrub

Epochs are integer cycle counts of registered millisecond-pulsar
beacons (`BCN-1` … `BCN-8`, catalogued in `CAT-BCN`), quoted
against at least two beacons for disambiguation. Durations use
the SI second with prefixes.

Every origin-derived unit is removed from the lexicon:

| Removed unit | Leak |
|---|---|
| `year`, `day`, `hour`, `minute` (time) | orbital period, rotation period, and base-60 timekeeping of the origin planet and culture |
| `light-year` | year-derived |
| `parsec` | defined via the origin planet's orbital baseline |
| `astronomical-unit` | the origin planet's orbital radius |
| `degree` (angle) | base-360 cultural convention (use `radian`) |
| `byte` | 8-bit architecture convention (use `bit`) |
| calendar nouns (`date`, `week`, `month`, `decade`, `century`) | origin calendar structure |

Rotation and orbital periods of *surveyed* bodies are expressed
with the lexicon nouns `rotation` + `period` and `orbit` +
`period`, measured in seconds.

### 4.4 Trajectory anonymity

Positions in a message are limited to observation targets,
cache/relay sites, and the single emission point in the message
header. No clause may relate two positions of the sender at
different epochs; relayed content strips prior-hop positions.
This blocks back-extrapolation of any probe's path toward a
common launch point. (Rules TRJ-1 … TRJ-3 in the grammar
document.)

---

## 5. Sender-Invariance (the Non-Interference Test, Restated)

BEYOND's Goguen–Meseguer test becomes, for a fleet:

> Two probes with identical instruments, identical catalogue
> versions, and identical observational data produce
> **byte-identical message bodies**. Their messages differ only
> in the `sender`, `message`, `position`, `epoch`, and `digest`
> envelope fields.

Every lexicon exclusion, canonical-ordering rule, and template
in PROBES CNL serves this property. It is tested by
differential authoring across probe firmware builds, exactly as
BEYOND §7.4 prescribes for human authors.

---

## 6. Efficiency Model

PROBES CNL is deliberately terser than BEYOND while remaining
losslessly expandable to controlled English:

1. **Two layers.** PROBES-W (wire form): compact, canonical,
   digest-bearing. PROBES-H (human form): controlled English
   with full evidential tags. The mapping is a deterministic
   bijection (Wire Format document).
2. **Clause templates.** The most common clause shapes
   (measurements, presence, completions, fractions, ratios,
   spectral features, dated events, landings, collections,
   distances, cache manifests, hazard thresholds, hypotheses)
   are registered templates T1–T20, validated against a
   55-message corpus drawn from historical missions: a template
   code plus slot values replaces a full word-coded clause.
3. **Codebook word codes.** Every lexicon entry has a stable
   short code derived algorithmically from the published
   lexicon (no separate codebook file to synchronize).
4. **One canonical unit per dimension.** Meter and second with
   SI prefixes; no unit synonyms to encode or convert.
5. **Identifiers replace names and repeated phrases.**
6. **Shorter clause cap.** 18 tokens per clause interior
   (BEYOND: 25 words).
7. **Catalogue references replace restated procedures.**

Accuracy is protected because compression is *symbolic*, never
lossy: expansion of a W-form message reproduces the H-form
exactly, and the digest is computed over the canonical W-form.

---

## 7. Document Map

| File | Contents |
|---|---|
| `README.md` | This document — scenario, threat model, design rationale |
| `PROBES_CNL_Lexicon.md` | Lexicon rules, inheritance from BEYOND v0.4.2, removals, additions, banned classes, code assignment |
| `PROBES_CNL_Evidential_System_and_Grammar.md` | Eleven E-tags, message envelope schema, formal grammar, register and linter rules |
| `PROBES_CNL_Wire_Format.md` | PROBES-W encoding: records, codebook derivation, templates, canonicalization, digests |
| `PROBES_CNL_Examples.md` | Compliant survey message in H- and W-form, relay, manifest, and hazard examples, non-compliant examples, human-synthesis notes |
| `PROBES_CNL_Survey_Corpus.md` | 55-message corpus from historical agency missions; measured template coverage and findings |
| `PROBES_CNL_Physical_Layer.md` | Channels, cache/archive siting tiers, hop-limit derivation, dispersal doctrine, energy loop, navigation and time |
| `PROBES_CNL_Transport_Layer.md` | Framing, forward error correction, and erasure-coding profiles (TR-1 … TR-5) below the canonical form |
| `PROBES_CNL_Amendment_Record.md` | Development and design-decision record (kept separate from the specification documents) |

---

## 8. Design Lineage

| Tradition | Contribution |
|---|---|
| BEYOND CNL v0.4 | Method-only vocabulary, E-Prime copula ban, mandatory evidentials, envelope grammar, non-interference discipline |
| E-Prime | Copula ban |
| ASD-STE100 (Simplified Technical English) | One word, one meaning; sentence limits |
| Attempto Controlled English | Deterministic interpretation |
| Lojban | Mandatory evidentials |
| Interplanetary spacecraft telemetry practice | Channel/wire vs. display split; canonical units; beacon-referenced time |
| Saltzer–Schroeder | Default-deny, fail-safe rejection, open design |

---

*End of PROBES CNL Overview v1.0.0.*
