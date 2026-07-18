# PROBES CNL: Wire Format (PROBES-W)

## Version 1.0.0

*Compact canonical encoding of PROBES CNL messages, with a
deterministic bijection to the human-readable form (PROBES-H)
defined by the Evidential System and Message Grammar document.*

---

## 1. Two-Layer Model

| Layer | Name | Role |
|---|---|---|
| PROBES-W | wire form | canonical form; transmitted, cached, relayed, digested |
| PROBES-H | human form | controlled-English Markdown message; generated on demand by expansion |

The mapping is a **bijection on canonical forms**:

```
expand(compact(H)) = canonical(H)
compact(expand(W)) = W
```

Compression is symbolic, never lossy. The digest is computed
over PROBES-W bytes, so any alteration in relay or caching is
detectable regardless of which layer a receiver inspects.

PROBES-W is a line-oriented ASCII format. The framing, forward
error correction, and erasure coding that carry canonical bytes
over links, media, and carriage are specified in the normative
companion `PROBES_CNL_Transport_Layer.md` (rules TR-1 … TR-5);
transport wraps, and never alters, the canonical form defined
here.

---

## 2. Record Model

A wire message is a sequence of LF-terminated records:

```ebnf
WireMessage   = Magic Header Declaration* SectionBlock* ;
Magic         = "%PW1" NL ;
Header        = "@" ( "|" HeaderField )+ NL ;
Declaration   = "D" "|" Namespace ( "|" Entry )+ NL ;
SectionBlock  = SectionMark ClauseRecord+ ;
SectionMark   = "#" "|" SectionNumber NL ;
ClauseRecord  = "C" "|" ETagCode TagArgs "|" Interior NL ;
```

Field separator is `|`; list separator inside a field is `;`;
key–value binding is `=`.

---

## 3. Header Record

Fixed key order, all keys mandatory:

| Key | Content | H-form envelope field |
|---|---|---|
| `SC` | `1.0` | `schema: probes-cnl-v1.0` |
| `MG` | 16 hex | `message:` |
| `SN` | 8 hex | `sender:` |
| `PL` | `0` | `plan: PLAN-0` |
| `EP` | `B<i>:<count>,B<j>:<count>` | `epoch:` |
| `PO` | `<x>,<y>,<z>` (meters, §6 number form) | `position:` |
| `RG` | region number | `region:` |
| `CT` | `<cat>:<ver>` pairs, comma-separated, sorted by key | `catalogues:` |
| `DG` | 64 hex | `digest:` |

Example:

```
@|SC=1.0|MG=9B2E44C7A1D0F358|SN=P-7F3A9C21|PL=0|EP=B3:8214559102334,B5:130995824|PO=-8.21e18,2.44e17,6.1e16|RG=4471|CT=BCN:14,PRC:9,REG:3,TGT:203|DG=9b2e…f3
```

## 4. Declaration Records

One `D|` record per non-empty envelope namespace, in this fixed
order:

| Namespace code | Envelope list | Entry form |
|---|---|---|
| `BCN` | `beacons:` | beacon number |
| `EPO` | `epochs:` | `id=PTS expression`, e.g. `1=B3:8214559102712` |
| `TGT` | `targets:` | target number |
| `FTR` | `features:` under `targets:` entries | full suffixed id, e.g. `TGT-0451-L1` |
| `INS` | `instruments:` | `ID=type-noun-code` |
| `PRC` | `procedures:` | procedure number (catalogue) or `L<n>=…` (local, body-defined) |
| `JRN` | `journals:` | journal number |
| `CCH` | `caches:` | cache number |
| `REF` | `references:` | `ARC-id=digest16` |
| `MSG` | `messages_cited:` | `msgid16=digest64` |
| `TCN` | `technical_names:` | `term-slug=definition-clause-ref` |
| `CND` | `conditions:` | `id=statement-clause-ref` |
| `MOD` `PAR` `RUN` `DAT` `MET` `HYP` | as in base schema | as in base schema |

Entries within a record sort ascending by entry key.

---

## 5. Clause Records

### 5.1 E-tag codes and argument keys

| Code | E-tag | Arguments (fixed order) |
|---|---|---|
| `O` | E-OBS | `v=` verb variant (1 observed, 2 detected, 3 registered); `s=` source ID |
| `M` | E-MSR | `v=` (1 measured, 2 sampled); `s=`; `u=` uncertainty (optional); `n=` (optional) |
| `A` | E-ACT | `p=` procedure; `j=` journal; `st=` steps `a-b` (optional) |
| `E` | E-DER | `v=` (1 derived, 2 calculated, 3 follows); `f=` premise list |
| `R` | E-RPT | `v=` (1 reported, 2 cited, 3 replicated); `r=` record; `s=` source (variant 3 only) |
| `L` | E-RLY | `m=` message; `h=` hops |
| `S` | E-SIM | `m=` model; `p=` parameters; `r=` run |
| `G` | E-AGG | `d=` dataset; `m=` method; `n=` |
| `H` | E-HYP | `c=` candidate; `f=` premises; `x=` distinguishable-from |
| `F` | E-DEF | none, or `s=` scope (stipulated form) |
| `P` | E-PRO | `st=` step; `if=` condition (optional); `for=` condition (optional) |

Example: `C|M|v=1|s=SPEC-2|u=1s|T1:N2F;TGT-1088;760.4;n,U33`
(`u=1s` encodes `1-sigma`; `±` and tolerance forms encode as
`u=pm,<num>,<unitexpr>` and `u=tol,<num>,<unitexpr>`).

### 5.2 Interior encodings

An interior is either a **template instance** or a **free-form
word stream**:

```ebnf
Interior     = TemplateForm | WordForm ;
TemplateForm = "T" Digit+ ":" Slot ( ";" Slot )* ;
WordForm     = "W:" Token ( SP Token )* ;
Token        = WordCode Suffix? | IdentifierLiteral | NumberLiteral
             | UnitExpr | "," ;
Suffix       = "+s" | "+ed" | "+ing" | "+er" | "+est" | "+ly" ;
UnitExpr     = UnitFactor ( "," UnitFactor )* ;
UnitFactor   = ( PrefixCode "," )? UnitCode ( "^" "-"? Digit+ )? ;
```

Compound units use exponent notation in the wire form only:
`U1M,U2B^-2` expands to "meters per second per second";
`U1M^-3` expands to "per cubic meter". The H-form always keeps
worded units.

- **Word codes** come from the deterministic codebook derivation
  in Lexicon §7 (`F`/`V`/`N`/`J`/`D`/`U` + two base-36 digits,
  assigned by ASCII sort within category).
- **Identifiers** (`TGT-1088`, `PROC-12`, `MSG-…`) appear
  literally; their typed prefixes make them self-delimiting.
- **Numbers** appear literally in the canonical number form
  (§6).
- **Inflection suffixes** attach to the code of the canonical
  spelling; expansion applies standard orthography (`survey+ed`
  → `surveyed`).
- Sentence-initial capitalization, the final period, backticks
  around identifiers, and E-tag parentheses are **not** stored;
  expansion regenerates them.

### 5.3 Registered clause templates

Templates are fixed lexicon-valid clause skeletons with typed
slots, corpus-validated (Survey Corpus §3). Registered set
(`{}` = slot; `{p}` = closed preposition selector
`of | on | in | at | within | across`; `{vb}` = verb selector
`equals | reaches`):

| ID | Expansion skeleton | Slots |
|---|---|---|
| `T1` | the {q} of {t} {vb} {v} {u}? | quantity noun phrase; catalogued id; number; unit expr (omitted for dimensionless quantities) |
| `T2` | — reserved (unused: uncertainty is expressed in E-MSR tag arguments, never in the clause interior) | |
| `T3` | the {a} of {t} reached completion | activity noun; id |
| `T4` | the {f} appears {p} {t} | feature noun phrase; id |
| `T5` | no {f} appears {p} {t} | as T4 |
| `T6` | the count of {f} {p} {t} equals {n} | feature; preposition; location; integer |
| `T7` | the {s} fraction of {t} equals {v} | noun phrase (any); id; number |
| `T8` | the {e} of the orbit of {t} equals {v} {u} | orbital-element noun; id; number; unit |
| `T9` | the {q} pattern of {t} remains compatible with this candidate | quantity noun; id |
| `T10` | the {q} at {t} exceeds threshold {th} | quantity noun; id; `THR-*` |
| `T11` | cache {c} rests at {pos} | `CCH-*`; GSF triple |
| `T12` | the probe deployed {d} at {t} | device noun; id |
| `T13` | the {q} at {loc} equals {v} {u} | noun phrase; catalogued id; number; unit |
| `T14` | the {k} feature of {s} appears at {v} {u} | absorption/emission; species (annex `Q` or `EL-*`); number; unit |
| `T15` | the ratio of {a} to {b} in {t} equals {v} | noun phrases ×2; id (optional); number |
| `T16` | a {e} appeared {p} {t} at epoch {ep} | event noun phrase; preposition and location (both optional together); `EP-*` |
| `T17` | the probe collected {v} {u} of {m} from {t} | number; unit; material; id |
| `T18` | the probe landed on {t} | id |
| `T19` | the distance from {a} to {b} equals {v} {u} | id or frame center; id; number; unit |
| `T20` | message {m} rests in cache {c} | `MSG-*`; `CCH-*` |

Slot values separate with `;`. Noun-typed slots ({q}, {f},
{a}, {s}, {e}, {d}) accept a noun phrase of up to three
space-separated word codes (e.g., "rotation period").
Location-typed slots ({t}, {loc}) accept a **location phrase**:
a catalogued identifier, optionally preceded by a part phrase
of up to three word codes plus "of" (e.g., "the atmosphere of
`TGT-0103`"); where a message declares a single target, the
bare part phrase may stand alone (e.g., "the ejecta plume").
A clause that fits no template uses `W:`. New templates enter only by specification revision
(they are part of the language, like the lexicon), because an
open template space would reopen the covert channel that
templates exist to close.

### 5.4 Section marks

`#|1` … `#|11` map to the CANON-1 section order (Definitions,
Procedures, Execution, Observations, Measurements, Derivations,
Simulations, Aggregations, Relay, Manifest, Hypothesis).
Expansion regenerates the corresponding `##` headings; sections
absent from the wire form are absent from the H-form.

Register mapping is implied: clauses in sections 3, 9, and 10
expand inside `execution` / `relay` / `manifest` code blocks;
section 4 clauses expand as blockquote lines; section 2 clauses
expand as ordered list items; section 1 clauses expand inside
`definition` blocks — matching the register table (grammar
§6.5).

---

## 6. Canonicalization Rules

Both compaction and validation apply these before digesting:

1. Line-feed (LF) line endings; no trailing whitespace; single spaces.
2. Header keys and declaration records in the fixed orders of
   §3–§4; list entries sorted ascending.
3. Sections in CANON-1 order; clauses within a section ordered
   by clause number.
4. Numbers: shortest exact decimal; scientific notation
   `m.mmm e±dd` written as `2.44e17` (lowercase `e`, no `+` on
   mantissa, no leading zeros); integers bare.
5. Word codes uppercase category letter + uppercase base-36
   digits; identifiers exactly as catalogued.
6. Exactly one clause per `C|` record.

## 7. Digest

`DG` = lowercase hex SHA-256 over the full canonical wire
message with the `DG` value replaced by 64 `0` characters.
`MG` = the first 16 hex digits of `DG`, uppercase. A relay
verifies `DG` before retransmission and cites `MG` in E-RLY
tags; `messages_cited:` carries the full digest so receivers
can verify ends-to-end without holding the original.

**Transport layering.** Forward error correction,
erasure coding, and framing sit strictly below the canonical
form and outside the language. Digests are computed and
verified over canonical wire bytes **after** transport decode;
no transport artifact enters the digest. The line-oriented
record format is self-resynchronizing, so an unrecoverable
burst error costs single records, and filter mode (grammar
§9.2) already defines the semantics of a message with dropped
clauses.

---

## 8. Expansion Algorithm (W → H)

1. Verify magic, header key order, digest.
2. Emit YAML envelope from header + declarations (§3–§4
   mappings), listing namespaces in the grammar §5 order.
3. For each section mark, emit the CANON-1 heading and the
   register wrapper (blockquote, ordered list, or fenced block)
   per §5.4.
4. For each clause record: expand the interior (template
   skeleton fill, or word-code lookup with suffix orthography);
   capitalize the first alphabetic token; wrap identifiers in
   backticks; append the E-tag in canonical English form from
   the tag code and arguments; append the period.
5. Emit hypothesis clauses under a `## Hypothesis` heading.

Compaction (H → W) is the inverse: parse per the message
grammar, normalize per §6, match interiors against templates
(longest match wins; template match is mandatory when a
template fits exactly — otherwise two encodings of one clause
would exist and the bijection would fail), code the residue,
assemble records, compute digest.

---

## 9. Size Behavior

Illustrative, using the worked example in the Examples
document: a 6-clause survey message runs ≈ 1,480 bytes in
PROBES-H and ≈ 500 bytes in PROBES-W (≈ 66% reduction) before
any transport-layer packing. Savings come from word codes
(≈ 45% on free-form interiors), templates (≈ 70% on templated
clauses), header/declaration key compression, and regenerated
punctuation. Identifiers and numbers — the scientific payload —
pass through untouched, which is where the accuracy guarantee
lives.

---

*End of PROBES CNL Wire Format v1.0.0.*
