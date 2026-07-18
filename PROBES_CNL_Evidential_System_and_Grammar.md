# PROBES CNL: Evidential System and Message Grammar

## Version 1.0.0

*Derived from BEYOND CNL Evidential System and Envelope Grammar
v0.4.1. Sections not restated here (notation conventions,
lexical conventions, inline-code identifier rules) carry over
from the base specification unchanged. This document is the
authoritative source of truth for PROBES CNL E-tag shape and
message structure.*

---

## 1. Purpose

Every assertion in a PROBES CNL message declares **how the
sending probe came to hold it**. The three functions of the base
system carry over with fleet-specific readings:

1. **Sender-invariance enforcement.** The epistemic source — not
   the probe's identity, trajectory history, or firmware build —
   determines the content of each clause. Two probes with the
   same data produce the same clause.
2. **Hazard containment.** Unmarked assertions from a
   compromised probe would be indistinguishable from grounded
   ones. Mandatory evidentials give every claim a checkable
   pedigree, bound relay depth, and let both probes and human
   synthesizers weight claims mechanically by tier.
3. **Machine-checkability.** Probes lint incoming messages
   without semantic understanding; non-compliant clauses drop in
   filter mode (§9.2) before any onboard process consumes them.

---

## 2. The Evidential Allow-list — Eleven Types, Three Tiers

PROBES CNL admits exactly **eleven evidential types**. Any
assertion not tagged with one of these fails linting.

| Tier | Tag | Meaning | Status vs. base |
|---|---|---|---|
| Direct | E-OBS | direct observation with named instrument | inherited, `operator` source removed |
| Direct | E-MSR | quantitative measurement with named instrument | inherited, canonical-unit rule added |
| Direct | E-ACT | execution record of a registered procedure | **new** |
| Mediated | E-DER | derivation from stated premises | inherited |
| Mediated | E-RPT | report from cited archive record | inherited, scope narrowed to archives |
| Mediated | E-RLY | relayed claim from a cited message | **new** |
| Mediated | E-SIM | simulation result from declared model, parameters, run | inherited |
| Mediated | E-AGG | statistical aggregate from declared dataset and method | inherited |
| Mediated | E-HYP | bracketed hypothesis from declared candidate space | inherited |
| Stipulative | E-DEF | definition of a term or parameter | inherited |
| Stipulative | E-PRO | procedural directive (probe-executable only) | inherited, addressee restriction added |

### 2.1 Inherited tags — delta notes only

**E-OBS** `(observed | detected | registered, [source])` —
unchanged except: the bare source keyword `operator` is
removed. Every source names an instrument identifier resolving
to the `instruments:` envelope list (rules E-OBS-1, E-OBS-2
carry over).

**E-MSR** `(measured | sampled, [source], [uncertainty],
[n=count])` — unchanged except linter rule **E-MSR-3 (new):**
every unit token obeys the canonical unit rule U-1 (meter,
second, gram, radian, bit, plus SI-derived units in the
retained list; SI prefixes only). A clause quoting a removed
unit fails.

**E-DER** `(derived | calculated | follows, from
[premise-refs])` — rules E-DER-1 … E-DER-3 carry over,
including grounding on definitions, Technical Names, and
conditions.

**E-RPT** `(reported, in [record-ref])` / `(cited, from
[record-ref])` / `(replicated, from [record-ref], by [source])`
— scope narrows to **archive records** (`ARC-*`): consolidated,
digest-bearing compilations produced at fleet consolidation
cycles. Claims from live messages use E-RLY instead. E-RPT-1,
E-RPT-2, and the hearsay-depth rule carry over.

**E-SIM, E-AGG, E-HYP** — unchanged in form and envelope
requirements (`models:`, `parameter_sets:`, `simulation_runs:`,
`datasets:`, `methods:`, `hypothesis_space:`; E-HYP requires a
heading beginning `Hypothesis`).

**E-DEF** `(defined)` / `(stipulated, for [scope])` —
unchanged. `PLAN-0` is a declared scope in every message, so
`(stipulated, for `PLAN-0`)` is always well-formed.

**E-PRO** `(procedure, [step n], [if COND], [for COND])` —
unchanged in form, plus rule **E-PRO-4 (new):** a procedural
clause describes an action executable by a probe's own
equipment. No procedure may name another probe, the fleet, a
recipient, or a reader as its actor. Procedures are records of
executable method, never instructions to anyone.

### 2.2 E-ACT: Execution Record (new, Tier 1)

**Meaning:** The sending probe executed the referenced
registered procedure; the clause describes that execution —
completion, epoch range, target, or step outcome. The probe's
own journal is the first-hand source, which places E-ACT in
Tier 1.

**Canonical English forms:**

| Form | Example |
|---|---|
| `(executed, procedure [proc-ref], journal [jrn-ref])` | "The survey of region `REG-4471` reached completion (executed, procedure `PROC-12`, journal `JRN-1`)." |
| `(executed, procedure [proc-ref], journal [jrn-ref], steps [a]-[b])` | "Sample collection on target `TGT-1088` covered nine sites (executed, procedure `PROC-31`, journal `JRN-1`, steps 4-12)." |

**Linter rule (E-ACT-1):** the procedure reference must resolve
to the fleet catalogue `CAT-PROC` or to the message's local
`procedures:` list.

**Linter rule (E-ACT-2):** the journal reference must resolve
to the `journals:` envelope list.

**Linter rule (E-ACT-3):** the clause subject must denote the
sending probe's own activity (the probe, the procedure, or its
direct object). A probe reports only its own actions; other
probes' actions arrive only via E-RLY. This closes the
impersonation channel: no probe can assert what another probe
did as first-hand fact.

**Why E-ACT exists.** The base language reports observations of
the world and stipulates procedures, but cannot state *what the
author did*. Fleet coordination (Overview §3.2) runs entirely
on completion facts — "region surveyed," "cache placed,"
"sub-probe deployed" — so those facts need a first-hand,
lintable tag with a journal-backed pedigree.

### 2.3 E-RLY: Relayed Claim (new, Tier 2)

**Meaning:** The clause restates a claim from another probe's
message, identified by message digest, without alteration of
quantitative content.

**Canonical English form:**

| Form | Example |
|---|---|
| `(relayed, from [msg-ref], hops=[n])` | "The methane fraction at target `TGT-2210` equals 0.031 (relayed, from `MSG-4C11D02A9E44B7F0`, hops=1)." |

**Linter rule (E-RLY-1):** the message reference must resolve
to the `messages_cited:` envelope list, whose entries carry the
cited message's identifier and full digest.

**Linter rule (E-RLY-2):** `hops` equals the cited clause's hop
count plus one, where an original (non-relayed) claim counts as
hops=0. **Warning at hops=2; rejection at hops≥3.** Bounded
gossip depth forces re-observation or archive consolidation
instead of unbounded rumor propagation.

**Linter rule (E-RLY-3):** relaying must not alter the
quantitative content of the cited clause (mirrors E-RPT-2).
Reinterpretation requires E-DER with the relayed clause as a
premise.

**Linter rule (E-RLY-4):** relayed content carries no envelope
data of the cited message other than its identifier and digest
— in particular, no prior-hop sender positions or epochs enter
the relaying message (see TRJ-3).

---

## 3. The Evidential Deny-list

Inherited in full: opinion, intuition, cultural knowledge,
belief, desire, purpose, ungrounded generalization — all
enforced by lexicon exclusion.

Added for the fleet:

| Denied basis | Enforcement |
|---|---|
| **Tasking** ("probe X performs Y") | no suasive verbs, no deontic modals, no addressee vocabulary, E-PRO-4, E-ACT-3 |
| **Second-hand action claims** ("probe X surveyed region R" as bare fact) | expressible only as E-RLY citing X's own E-ACT message |
| **Origin and provenance claims** | provenance word class absent; ORG rules §5.4 |
| **Second intent** ("this probe operates toward …") | goal vocabulary absent; only `(stipulated, for `PLAN-0`)` exists (PLAN rules §5.2) |
| **Self-state disclosure** ("the energy reserve of the probe equals …") | SELF-1 (§5.4a): sender internal state inexpressible; sender appears only as E-ACT actor or in single-epoch geometry |

---

## 4. Clause Structure

The base canonical clause structure carries over: declarative
clause interior, then the E-tag frame in final parenthetical
position, then the period. Compound sentences normalize to one
E-tag per clause. Conditionals use `(procedure, if `COND-X`)`
with the condition declared in the envelope; inline
`if … then …` is not part of the grammar.

**Clause length (CL-1, revised):** a clause interior contains at
most **18 tokens** (base: 25 words). Tokens are lexicon words,
inline-code identifiers, numbers, and unit words.

**Imperative clauses** remain restricted to ordered-list
procedure steps tagged E-PRO, under a heading beginning
`Procedure` or `Steps`, subject to E-PRO-4.

---

## 5. Message Envelope Schema

A PROBES-H message begins with YAML frontmatter (the *envelope*;
in the wire form this maps to the header record, Wire Format
§3):

```yaml
---
schema: probes-cnl-v1.0
message: MSG-9B2E44C7A1D0F358
sender: P-7F3A9C21
plan: PLAN-0
epoch: "BCN-3: 8214559102334 + BCN-5: 130995824"
position: "GSF -8.21e18 +2.44e17 +6.10e16 meter"
region: REG-4471
catalogues:               # version pinning (FRONT-5)
  CAT-BCN: 14
  CAT-TGT: 203
  CAT-PROC: 9
  CAT-REG: 3
beacons: [BCN-0, BCN-1, BCN-3, BCN-5]
targets:
  - id: TGT-1088
    catalogue: CAT-TGT
    features: [L1]        # legalizes TGT-1088-L1 (ID-1)
  - id: TGT-1090
    catalogue: CAT-TGT
instruments:
  - id: SPEC-2
    type: spectrometer
  - id: MAG-1
    type: magnetometer
procedures:
  - id: PROC-12
    catalogue: CAT-PROC
journals:
  - id: JRN-1
caches: []                # CCH-* cache nodes (R-20)
epochs:                   # EP-* declared epochs (R-21)
  - id: EP-1
    value: "BCN-3: 8214559102712"
references: []            # ARC-* archive records, for E-RPT
messages_cited:           # for E-RLY
  - id: MSG-4C11D02A9E44B7F0
    digest: 4c11d02a9e44b7f0e91b3a77c2d5f6a8...
technical_names: []
conditions: []
models: []
parameter_sets: []
simulation_runs: []
datasets: []
methods: []
hypothesis_space: []
digest: 9b2e44c7a1d0f358aa10b6c94d21e7f3...
---
```

### 5.1 Inherited envelope rules

FRONT-1 (every body identifier resolves in its envelope
namespace), FRONT-2 applied to no field (the base `purpose:`
field is **removed** — `plan:` replaces it), and the field
constraints for `models:`, `parameter_sets:`,
`simulation_runs:`, `datasets:`, `methods:`, and
`hypothesis_space:` carry over verbatim. The base `phase:`
field is removed; probes have no protocol phases.

**FRONT-4 (revised):** `schema:` must declare `probes-cnl-v1.0`.

**FRONT-5:** every catalogue whose identifiers appear in
the message must be pinned with a version number under
`catalogues:`. Beacon timing models and target catalogues are
revised over the fleet's lifetime; an epoch or designation is
interpretable only relative to the catalogue version it
assumed. A message referencing an unpinned catalogue is
rejected.

### 5.2 Plan rules

**PLAN-1:** the `plan:` field is mandatory and its value equals
`PLAN-0` exactly.

**PLAN-2:** no identifier in the `PLAN-` namespace other than
`PLAN-0` may appear anywhere in a message. The registered text
of `PLAN-0` is fixed by the specification:

```definition
The fleet surveys the stars, planets, and interstellar medium
of this galaxy and records the results for later analysis
(stipulated, for `PLAN-0`).
```

Because the field is constant across all probes and messages,
it carries zero differential information and cannot violate
sender-invariance.

### 5.3 Position and time rules

**POS-1:** every coordinate in a message uses the Galactic
Standard Frame (Overview §4.2): `GSF x y z meter` with SI
prefixes or scientific notation; no other frame is definable.

**TIME-1:** every epoch uses the Pulsar Time Standard: integer
cycle counts of at least two beacons from `CAT-BCN`. Every
duration uses seconds with SI prefixes. Epochs referenced from
clause interiors (dated events, template T16) are declared in
the `epochs:` envelope list as `EP-*` entries and referenced by
identifier, keeping clauses within the 18-token cap.

### 5.3a Identifier extensions

**ID-1 (features):** `<parent-id>-<suffix>` identifiers
denote named parts of a catalogued body (`TGT-0451-L1`). They
are declared in the parent's `targets:` entry under `features:`
and resolve with the parent under R-17.

**ID-2 (elements):** `EL-<Z>` and `EL-<Z>.<A>`
identifiers denote chemical elements and isotopes, resolved
against `CAT-EL` (R-22). The worded whitelist in Lexicon §5.5
is canonical for its species; whitelisted species never appear
as `EL-*` identifiers, and excluded species never appear as
words.

### 5.4 Origin-erasure rules

**ORG-1:** no token in a message may belong to the provenance
or calendar banned classes (Lexicon §3); the linter applies
this at Layer 1.

**ORG-2:** no proper noun may appear; every named entity
resolves as a typed catalogue identifier.

**TRJ-1:** positions appear only for observation targets, cache
or relay sites, and the single emission point in the header
`position:` field.

**TRJ-2:** no clause relates two positions of the sender at
different epochs. The sender's position appears exactly once
per message, in the header.

**TRJ-3:** relayed content (E-RLY) carries no prior-hop
positions, epochs, or sender identifiers beyond the cited
message identifier and digest.

Together TRJ-1 … TRJ-3 prevent reconstruction of any probe's
long-run trajectory from message traffic, which blocks
back-extrapolation toward a common launch origin.

**ORG-3:** structural catalogues (`CAT-CCH`, `CAT-REG`)
carry no establishment, founding, or first-visit epochs.
Activity chronology is what an origin-inference attack fits
circles to (Physical Architecture §4.5); deduplication and
routing need status, never dates.

### 5.4a Consolidation and self-state rules

**CONS-1:** coverage aggregates record completion
*status*, never completion *epochs*. Aggregation produces a new
derived record, so projecting fields is legitimate; the
no-alteration rules for relay (E-RLY-3) and citation (E-RPT-2)
are untouched.

**CONS-2:** archive entries carry corroboration counts
(independent originating senders per claim, expressed as an
ordinary E-AGG `n=`). Uncorroborated claims (n=1) are flagged
in the archive and do not satisfy the preconditions of
catalogue procedures (e.g., resource thresholds for `PROC-RCH`).
This is the containment backstop for false-but-well-formed
content from a compromised probe.

**SELF-1:** quantities predicated on the sending
probe's internal state — energy reserves, consumables,
component condition, mass, velocity, temperatures — are
inexpressible. The sender appears in clause content only as the
actor of execution records (E-ACT; templates T12, T17, T18) or
in single-epoch geometric quantities of the kind already
permitted (the header `position:`; a flyby distance).
Rationale: no recipient can act on probe state (no tasking, no
rescue exists), so state disclosure has zero coordination value
against nonzero capability-leak and covert-channel cost, and
internal state is not a function of observations — publishing
it would break sender-invariance directly. Enforced at Layer 4.

---

## 6. Message Grammar (delta over base §6)

Base §6.1 (notation), §6.2 (lexical conventions), and §6.3
(inline-code identifiers) apply unchanged.

### 6.1 Message-level grammar

```ebnf
Message         = Envelope Body ;

Envelope        = "---" NL EnvelopeContent "---" NL ;
EnvelopeContent = ?valid YAML 1.2, conforming to the schema in §5? ;

Body            = ( Block | BlankLine )* ;

Block           = Heading
                | Paragraph
                | Blockquote
                | OrderedList
                | CodeBlock ;
```

A message with no envelope, or whose envelope fails §5, is
rejected. A body with zero blocks is accepted (the empty
compliant message).

### 6.2 Block-level grammar

As the base §6.5, with the `InfoString` alternatives extended:

```ebnf
InfoString      = "definition" | "constraint" | "measurement"
                | "simulation" | "aggregation" | "relation"
                | "execution" | "relay" | "manifest"
                | Identifier ;
```

### 6.3 Clause-level grammar

As the base §6.6 (TaggedClause, ImperativeClause,
ClauseInterior, Token), with the CL-1 18-token limit applied to
`ClauseInterior`.

### 6.4 E-tag grammar

```ebnf
ETagFrame       = "(" ETagBody ")" ;

ETagBody        = ObsTag | MsrTag | ActTag
                | DerTag | RptTag | RlyTag
                | SimTag | AggTag | HypTag
                | DefTag | StipTag ;

ProcETagFrame   = "(" ProcTag ")" ;

(* ---- inherited tags: as base §6.7, with SourceRef revised ---- *)

SourceRef       = ( InstrumentClass SP )? InlineCode ;
                  (* the base "operator" alternative is removed *)

(* ---- E-ACT ---- *)
ActTag          = "executed" "," SP "procedure" SP ProcedureRef
                  "," SP "journal" SP JournalRef
                  ( "," SP "steps" SP Digit+ ( "-" Digit+ )? )? ;
ProcedureRef    = InlineCode ;
JournalRef      = InlineCode ;

(* ---- E-RLY ---- *)
RlyTag          = "relayed" "," SP "from" SP MessageRef
                  "," SP "hops=" Digit+ ;
MessageRef      = InlineCode ;
```

All other productions (ObsTag, MsrTag, DerTag, RptTag, SimTag,
AggTag, HypTag, DefTag, StipTag, ProcTag, UncertaintyExpr,
PremiseRefList) carry over byte-for-byte from base §6.7.

### 6.5 Register constraints (type rules)

| Block type | Permitted E-tag types | Rule ID |
|---|---|---|
| Paragraph | any | — |
| Blockquote | E-OBS, E-MSR | B-1 |
| OrderedList | E-PRO | O-1 |
| OrderedList placement | after a heading beginning `Procedure` or `Steps` | O-2 |
| CodeBlock(definition) | E-DEF | C-1 |
| CodeBlock(constraint) | E-DEF or E-DER | C-2 |
| CodeBlock(measurement) | E-MSR | C-3 |
| CodeBlock(simulation) | E-SIM | C-5 |
| CodeBlock(aggregation) | E-AGG | C-6 |
| CodeBlock(relation) | E-DER; operator notation here only | C-7 |
| CodeBlock(execution) | E-ACT | **C-8** |
| CodeBlock(relay) | E-RLY | **C-9** |
| CodeBlock(manifest) | E-OBS, E-ACT | **C-10** |
| CodeBlock(other) | unrestricted, flagged for review | C-4 |
| E-HYP placement | paragraph under a heading beginning `Hypothesis` | HYP-PLACE |
| Heading | no E-tag | H-1 |

### 6.6 Canonical section order (CANON-1)

To minimize free variation (covert channels) and maximize
compression, body sections appear in this fixed order, each
present only if non-empty:

1. `## Definitions`
2. `## Procedures` (local, novel procedures only)
3. `## Execution`
4. `## Observations`
5. `## Measurements`
6. `## Derivations`
7. `## Simulations`
8. `## Aggregations`
9. `## Relay`
10. `## Manifest`
11. `## Hypothesis …`

Within a section, clauses order by their identifier numbering.
A message violating the order fails canonicalization (Wire
Format §6) and therefore digest verification.

### 6.7 Reference resolution

Base rules R-1 … R-12 and premise-eligibility rules P-1 … P-11
carry over, with these additions:

| Reference | Must resolve in | Rule ID |
|---|---|---|
| ProcedureRef | `CAT-PROC` or `procedures:` in envelope | **R-13** |
| JournalRef | `journals:` in envelope | **R-14** |
| MessageRef | `messages_cited:` in envelope | **R-15** |
| RegionRef (`REG-*`) | `CAT-REG` | **R-16** |
| TargetRef (`TGT-*`) | `targets:` in envelope, backed by `CAT-TGT` | **R-17** |
| BeaconRef (`BCN-*`) | `beacons:` in envelope, backed by `CAT-BCN` | **R-18** |
| ThresholdRef (`THR-*`) | `CAT-THR` | **R-19** |
| CacheRef (`CCH-*`) | `caches:` in envelope, backed by `CAT-CCH` | **R-20** |
| EpochRef (`EP-*`) | `epochs:` in envelope | **R-21** |
| ElementRef (`EL-*`) | `CAT-EL` | **R-22** |

| PremiseRef target carries | Eligible as premise? | Rule ID |
|---|---|---|
| E-ACT | yes | **P-12** |
| E-RLY | yes at hops≤1; warning at hops=2 (tracks E-RLY-2) | **P-13** |

E-PRO clauses remain ineligible as premises (P-6).

---

## 7. Coverage Metric

Evidential coverage — E-tagged clauses over total declarative
clauses — must equal **1.0**, as in the base language.

---

## 8. Sender-Invariance Test

The Goguen–Meseguer differential-authoring test, restated for
the fleet: two probes with identical catalogue versions,
identical instrument sets, and identical observational data
produce byte-identical message **bodies**; their envelopes
differ only in `sender`, `message`, `position`, `epoch`, and
`digest`. The graded variant compares per-clause structured
tuples emitted by the parser. Divergence indicates a leak in
the lexicon, the evidential system, or the canonicalization
rules.

As with the base language, this test defines the target; a
scaled protocol across firmware builds remains to be run before
the invariance claim is empirical.

---

## 9. Enforcement Architecture

### 9.1 Five layers (inherited, re-targeted)

1. **Lexicon check** — token whitelist, banned classes
   including the four new classes.
2. **Grammar check** — envelope schema, block/clause/E-tag
   derivation, register rules, CANON-1.
3. **Reference resolution** — R-1 … R-19, premise eligibility,
   hop counting.
4. **Evidential semantics** — coverage 1.0, tier consistency,
   unit rule U-1, TRJ and PLAN rules.
5. **Review scan** — onboard heuristic scan (probes) or human
   review (synthesis) for residual hazards.

### 9.2 Acceptance semantics

Fail-safe default: a message either derives or is rejected;
undeterminable cases reject. **Filter mode is the standard mode
for inter-probe transmission and relay**: non-compliant clauses
drop silently, so a compromised probe's non-compliant content
reduces to empty output at every receiver. Strict mode (reject
whole message, report reasons) is the authoring and
synthesis-side mode.

---

*End of PROBES CNL Evidential System and Message Grammar v1.0.0.*
