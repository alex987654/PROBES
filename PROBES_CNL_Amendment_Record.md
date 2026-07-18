# PROBES CNL: Amendment Record (AM-1 … AM-19)

## Status: ADOPTED — folded into the core v1.0 documents

*The schema string remains `probes-cnl-v1.0`; the pre-amendment
draft is superseded and out of use. This file is retained as
the evidence trail: consolidated from the Survey Corpus
analysis (empirical, 55 messages / 92 declarative clauses) and
the Physical Communications Architecture (structural). Each
amendment names its evidence.*

---

## 1. Envelope and Namespaces

**AM-1 — `CCH-` cache namespace.** New identifier prefix
`CCH-`, envelope list `caches:`, resolution rule R-20
(CacheRef resolves in `caches:`, backed by `CAT-CCH`).
*Evidence: corpus F-5 (T11 referenced caches v1.0 never
declared); physical §3.*

**AM-2 — Declared epochs.** New identifier prefix `EP-`,
envelope list `epochs:` (each entry: id + PTS beacon-cycle
expression), resolution rule R-21. Clauses reference epochs as
`` `EP-n` ``, keeping transient-event clauses within the
18-token cap. *Evidence: corpus F-4 (6 of 92 clauses were dated
events); physical §5.*

**AM-3 — Catalogue version pinning.** Mandatory envelope field:

```yaml
catalogues:
  CAT-BCN: 14
  CAT-TGT: 203
  CAT-PROC: 9
  CAT-REG: 3
```

Rule FRONT-5: every catalogue whose identifiers appear in the
message must be pinned. *Evidence: physical §5 — pulsar timing
models are revised over the fleet's lifetime; an epoch is
meaningless without its timing-solution version.*

**AM-4 — Feature identifiers.** `<parent-id>-<suffix>`
identifiers (e.g., `TGT-0451-L1`) are legal, declared as
`features:` under the parent's `targets:` entry. *Evidence:
corpus F-6 (5 uses).*

## 2. Registers

**AM-5 — `manifest` code block.** New InfoString `manifest`;
permitted E-tags E-OBS and E-ACT (rule C-10). Canonical content:
deposit/withdrawal/presence records at cache nodes. Manifest
listings double as delivery receipts (physical §4), so no
acknowledgment grammar is introduced.

## 3. Templates

**AM-6 — Withdraw T2.** Uncertainty is expressed once, in E-MSR
tag arguments; a second interior-level encoding would break the
compaction bijection. *Evidence: corpus F-1 (zero hits; every
uncertain measurement used tag arguments).*

**AM-7 — Widen T1.** Optional unit slot (dimensionless
quantities: albedo, transit depth) and verb selector
`equals | reaches`. *Evidence: corpus §3.2–3.3 (+4 clauses).*

**AM-8 — Widen T4/T5.** Closed preposition selector
`on | in | at | within | across`. *Evidence: corpus F-2.*

**AM-9 — Widen T7.** Fraction subject generalized from
substances to any noun phrase ≤3 codes. *Evidence: corpus §3.3.*

**AM-10 — Add T13–T20:**

| ID | Skeleton | Evidence |
|---|---|---|
| T13 | the {q} at {loc} equals {v} {u} | 4 corpus hits |
| T14 | the {k} feature of {s} appears at {v} {u} | 3 hits; spectroscopy workload |
| T15 | the ratio of {a} to {b} in {t} equals {v} | 3 hits |
| T16 | a {e} appeared on {t} at epoch {ep} | 6 hits; requires AM-2 |
| T17 | the probe collected {v} {u} of {m} from {t} | 2 hits |
| T18 | the probe landed on {t} | 3 hits |
| T19 | the distance from {a} to {b} equals {v} {u} | 1 hit; survey geometry recurs |
| T20 | message {m} rests in cache {c} | manifest traffic; requires AM-1, AM-5 |

Projected template coverage on the corpus rises from 64.1% to
93.5%; the six residual free-form clauses (mechanism
derivations, morphology, aggregates) are shapes that resist
templating without loss and correctly remain `W:`.

## 4. Lexicon

**AM-11 — Mass unit.** Replace unit word `kilogram` with
`gram`; SI prefixes attach to `gram`. *Evidence: corpus F-8
("0.0054 kilograms").*

**AM-12 — Chemistry nomenclature annex.** Closed annex: element
names plus a fixed simple-compound list (`carbon-dioxide`,
`sulfur-dioxide`, `methane`, `carbonate`, `water-ice`, …),
composition-pinned, codebook category `Q`. *Evidence: corpus
F-7 — composition claims are ubiquitous and ad-hoc admission
invites synonymy.*

**AM-13 — Verify-or-add list.** Fourteen corpus words pending
the idempotence check against the base lexicon, with proposed
pins recorded in corpus F-9 (`plume`, `geyser`, `haze`, `lake`,
`streak`, `ejecta`, `impactor`, `albedo`, `tilt`, `parallax`,
`corona`, `neutrino`, `gamma-ray`, `vapor`). Interim handling:
Technical Name mechanism.

## 5. Wire Format

**AM-14 — Unit exponents.** `UnitExpr` gains `^<int>` exponent
notation (`U<m>^-3`; `U<m>,U<s>^-2`). H-form keeps worded units.
*Evidence: corpus F-10.*

**AM-15 — Transport layering note.** Normative statement that
digests are computed over canonical wire bytes **after** FEC
decode; FEC/erasure/framing sit below the canonical layer and
outside the language. *Evidence: physical §7.*

## 6. Explicitly Rejected (recorded to prevent re-litigation)

| Candidate | Reason |
|---|---|
| Sender `velocity:` field | position+velocity enables trajectory extrapolation (TRJ intent); Doppler is a physical-layer concern |
| Acknowledgment/receipt grammar | manifests are receipts; addressee-shaped speech acts stay excluded |
| Priority/urgency markers | alarm vocabulary is inexpressible by design; relevance derives from catalogue rules over registered facts |
| Raw onboard-clock timestamps | frame- and probe-specific; violates sender-invariance; reduce via `PROC-NAV` |
| Range/extent template | decomposes into T1 pairs or T1-`reaches` (corpus F-3) |
| Contains-list template | decomposes into repeated presence clauses |

## 7. Second-Round Amendments (AM-16 … AM-19) — from the expanded physical architecture

**AM-16 — SELF-1: sender internal state inexpressible.**
Quantities predicated on the sending probe's own state (energy
reserves, consumables, component condition, mass, velocity,
temperatures) are non-compliant; the sender appears in clause
content only as E-ACT actor or in single-epoch geometry already
permitted. *Evidence: Physical §6.4 — zero actionable value (no
tasking, no rescue), capability leak, covert channel, and a
direct sender-invariance violation.*

**AM-17 — Lexicon: siting and energy vocabulary.** `custodian`
re-admitted under a device pin (removed at first pass as an
institution role); `halo`, `spiral-arm` nouns; `quiescent`
adjective; stellar classification letters declared
inexpressible (numeric characterization: effective temperature,
luminosity, mass). *Evidence: Physical §3.3, §6.4.*

**AM-18 — Chronology scrubbing and corroboration.** ORG-3
(structural catalogues carry no establishment epochs), CONS-1
(coverage aggregates record status, never epochs), CONS-2
(archive corroboration counts; n=1 claims cannot trigger
catalogue procedures), MAN-H (custodial manifest horizon).
*Evidence: Physical §4.4–4.5 — the wavefront and founding-order
attacks; quarantine backstop for false-but-well-formed content.*

**AM-19 — Transport Layer specification adopted as normative**
(`PROBES_CNL_Transport_Layer.md`, rules TR-1 … TR-5): fixed
profiles (rateless fountain link code, RS product media code,
(5,3) cross-cache erasure), fragment quarantine, transport
uniformity, slot-padded emission discipline. *Evidence:
Physical §7; Transport §1–§9. Grammar and lexicon impact: none,
by construction.*

Also recorded as doctrine (catalogue content, zero grammar):
the dispersal protocol `PROC-DSP` (DSP-1 … DSP-3, activation
epoch `T_act`), the recharge procedure family `PROC-RCH` with
thresholds `THR-NRG-*`, and the derived status of the hop
limit (h_max = ⌈R_rel/s⌉ = 2 under T_c ≈ T_t — a matched pair,
re-derivable if cadence or cruise speed change; Physical §4.3).
Additional rejected alternatives from this round (energy-state
reporting, hop limits of 1 or 3–5, the nearest-unclaimed-seed
dispersal shortcut, stellar class letters, establishment epochs
in structural catalogues) are recorded in Physical §8.3.

## 8. Editorial Synchronization (this record only)

Applied after adoption, recorded here so the specification
documents stay free of change history:

- All amendment references (AM-n), consolidation notes,
  supersession notices, and "re-admitted"-style change language
  were removed from the specification and analysis documents;
  they appear only in this record.
- Template synchronization from corpus usage: T16 gained the
  preposition selector with an optional location; T6's selector
  includes `of`; location-typed slots were defined as location
  phrases (identifier with optional part phrase); the T2 row
  reads as a reserved identifier without adoption history.
- The corpus findings were renumbered N-1 … N-8 in the
  synchronized edition; F-numbers cited in §1–§5 above refer to
  the pre-synchronization edition of the corpus document.
- Corpus synchronization: clauses retagged to the final
  template identifiers; sample masses restated in grams (5.4 g,
  121.6 g); cache emplacement recast as T12 deployment; the
  neutrino count-within-a-window clause reclassified free-form;
  the C-54 relay citation given its own message identifier
  (previously it cited the Examples message, which does not
  contain the relayed claim); minor wording fixes for
  lexicon-safe compounds ("nitrogen ice sheet", "ice
  thickness", "dark slope streaks"). Final measured coverage:
  85/92 templated (92.4%), 7 free-form.
- Readability: acronyms spelled out at first use (forward error
  correction, cyclic redundancy check, kiloparsec, agency
  names); informal jargon replaced with descriptive wording
  ("data carried as physical cargo", "unattended media deposit
  sites") for ease of translation.

---

*End of PROBES CNL Amendment Record (adopted).*
