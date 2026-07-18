# PROBES CNL: Sense-Pinned Lexicon

## Version 1.0.0 — Delta Specification over BEYOND CNL Lexicon v0.4.2

---

## 1. Inheritance Rule

PROBES CNL Lexicon v1.0 **=** BEYOND CNL Lexicon v0.4.2
**minus** the removals in §4 **plus** the additions in §5,
with the banned classes of §3 applied on top of BEYOND §1.4.

- The base lexicon's sense-pinning discipline (one spelling, one
  part of speech, one meaning, one transitivity, one
  countability), its approved inflection set (`-s`, `-ed`,
  `-ing` where permitted, `-er`, `-est`, `-ly`), and its copula
  ban (E-Prime) carry over unchanged.
- The Technical Name escape mechanism carries over: nouns only;
  first occurrence in **bold** with a `definition` code block;
  subsequent uses in `inline code`; registered in the message
  envelope under `technical_names:`.
- **Idempotence of additions.** Each §5 entry adds the word if
  absent from the base; if the word already exists in the base,
  the §5 sense pin *replaces* the base pin. This makes the delta
  well-defined regardless of base coverage.
- **Conflict rule.** Where this document and the base disagree,
  this document wins.

---

## 2. Validation Criteria (revised)

A word belongs in the PROBES CNL lexicon if and only if:

1. It has exactly one approved meaning serving a procedural or
   observational purpose.
2. It cannot disclose the origin system, the makers, launch
   history, or fleet manufacture structure.
3. It cannot address, task, persuade, or evaluate any recipient
   — probe or human.
4. It does not perform the copula function.
5. It does not express propositional attitude.
6. It does not evaluate, judge, or rank.
7. Its removal creates an unfillable gap within the 18-token
   clause limit.
8. Its inclusion does not create synonymy enabling sense-evasion
   or covert-channel word choice.

Criterion 8 is stricter than BEYOND's: any pair of admissible
words with overlapping senses creates one bit of covert channel
per use, so PROBES CNL keeps exactly one word per admitted
sense and one canonical unit per physical dimension.

---

## 3. Banned Word Classes

All BEYOND v0.4 banned classes remain banned:

| Inherited banned class | Reason |
|---|---|
| Copula forms | Identity function |
| First-person singular | Identity |
| Identity-constructing plurals | Identity |
| Propositional-attitude verbs (`believe`, `want`, `intend`, `hope`, `fear`, `expect`, …) | Intent / value |
| Evaluative adjectives (`good`, `bad`, `important`, …) | Value |
| Suasive verbs (`ask`, `demand`, `propose`, `recommend`, `urge`, …) | Coercion |
| Deontic modals (`should`, `ought`, `must` obligation) | Value imposition |
| Epistemic hedging modals (`might`, `may`, `could` speculation) | Cognitive architecture |
| Intensifiers, stance adverbs, interjections, affect nouns | Expressive / affect |
| Metaphor markers | Cognitive architecture |
| Purposive/causal subordinators (`so that`, `in order to`, `because`) | Teleology |
| Exclamation marks | Expressive |

PROBES CNL adds four classes:

| New banned class | Members (illustrative) | Reason |
|---|---|---|
| **Proper nouns — all** | any capitalized name of a star, planet, region, person, group, product | Origin / covert channel; catalogue identifiers replace every name (BEYOND banned only group proper nouns) |
| **Provenance class** | `origin`, `home`, `homeworld`, `source` (provenance sense), `native`, `birthplace`, `creator`, `maker`, `builder` (agent sense), `manufacturer`, `launch` (genesis sense) | Origin back-inference |
| **Calendar class** | `date`, `week`, `month`, `year`, `day`, `hour`, `minute` (time), `decade`, `century`, `dawn`, `sunrise`, `night` | Encodes origin-planet rotation, orbit, and calendar culture (see §4.1) |
| **Addressee class** | `you`, `your`, second-person imperative address, vocatives | No message may address its reader; protects probes (T2) and human synthesizers (T3) |

---

## 4. Removals from the Base Lexicon

### 4.1 Time and calendar nouns (Section E of base)

Removed: `century`, `date`, `dawn`, `day`, `decade`, `era`,
`hour`, `minute` (time sense), `month`, `night`, `origin` (time
sense), `sunrise`, `week`, `year`.

Retained from Section E: `beginning`, `cycle`, `duration`,
`end`, `epoch` (re-pinned in §5.1), `instant`, `interval`,
`moment`, `onset`, `period`, `second`, `start`.

Replacements: rotation period and orbital period of surveyed
bodies use `rotation` + `period` and `orbit` + `period`,
measured in seconds. The local illumination boundary of a
surveyed planet uses `terminator` (already in base).

### 4.2 Units (Section 8 of base)

Removed: `day`, `hour`, `minute` (time), `year`, `light-year`,
`parsec`, `astronomical-unit`, `degree` (angle), `byte`,
`pixel`, and `kilogram` (replaced by `gram` — SI prefixes
attach to `gram`, matching how prefixes actually compose).

Retained: all other SI base units, all SI derived units in the
base list, all SI prefixes, `gram`, `radian`, `steradian`,
`bit`, cardinals, ordinals, and mathematical operator words.

**Canonical unit rule (U-1):** exactly one unit per physical
dimension — length `meter`, time `second`, mass `gram`, angle
`radian`, information `bit` — scaled only by SI prefixes. A
measurement in any other unit fails linting.

### 4.3 Agent and role nouns (Section H of base)

Removed as institution-class roles that presuppose the makers'
social structure and never occur in probe registers:
`analyst`, `archivist`, `auditor`, `author`, `challenger`,
`coalition`, `custodian`, `delegate`, `federation`,
`inspector`, `party`, `reader`, `reviewer`, `team`.
(`custodian` appears in §5.1 under a device-only pin — equipment
that maintains a cache node; the institutional sense stays
excluded.)

Retained: `agent`, `cohort`, `group`, `monitor`, `observer`,
`operator` (system sense only — see §4.5), `recipient`,
`sender`.

### 4.4 Other removals

- `earthquake` — fossilized origin morphology; replaced by
  `quake` (§5.2).
- `virus`, `species`, `specimen`, `tissue` remain **retained**
  (surveyed worlds may host biology); their base pins are
  already origin-neutral.

### 4.5 Grammar-side removal (recorded here for completeness)

The bare E-tag source keyword `operator` (unaided human
observation) is removed from the evidential grammar: every
probe observation names an instrument identifier. The noun
`operator` survives only in its "system that controls
equipment" sense.

---

## 5. Additions

### 5.1 Nouns (41)

| Noun | Count | Sense pin |
|---|---|---|
| `probe` | countable | autonomous device that travels through space, executes catalogue procedures, and records observations |
| `sub-probe` | countable | probe deployed by another probe |
| `fleet` | countable | the set of all probes operating under `PLAN-0` |
| `plan` | countable | registered statement of scope for fleet activity; exactly one exists (`PLAN-0`) |
| `catalogue` | countable | fleet-wide registered table of identifiers and their entries |
| `beacon` | countable | catalogued celestial reference source used for position or time fixes |
| `cache` | countable | fixed physical site where messages or samples rest for later retrieval |
| `relay` | countable | retransmission of a message by a probe other than its sender |
| `journal` | countable | append-only record of a probe's executed procedure steps |
| `region` | countable | catalogued volume of this galaxy per the tessellation in `CAT-REG` |
| `target` | countable | catalogued object under observation |
| `epoch` | countable | point in time expressed as beacon cycle counts per the Pulsar Time Standard |
| `frame` | countable | coordinate system; in this language, the Galactic Standard Frame |
| `trajectory` | countable | path of a body through space |
| `flyby` | countable | passage near a body without capture into orbit |
| `gravity-assist` | countable | trajectory change obtained from a close passage of a massive body |
| `lander` | countable | device that descends to and operates on a surface |
| `orbiter` | countable | device that operates in orbit around a body |
| `dormancy` | uncountable | low-power operating state with suspended activity |
| `attitude` | countable | orientation of a device relative to a reference frame |
| `biosignature` | countable | measurable indicator compatible with biological processes |
| `technosignature` | countable | measurable indicator compatible with technological processes |
| `interstellar-medium` | uncountable | gas and dust occupying the space between star systems |
| `quake` | countable | sudden shaking of a body's surface from subsurface energy release |
| `plume` | countable | column of gas, dust, or liquid ejected from a source |
| `geyser` | countable | vent that intermittently ejects fluid |
| `haze` | uncountable | suspended fine particles that reduce transparency |
| `lake` | countable | surface body of standing liquid |
| `streak` | countable | narrow elongated surface marking |
| `ejecta` | uncountable | material thrown outward by an impact or eruption |
| `impactor` | countable | device or body that strikes a surface |
| `albedo` | countable | fraction of incident radiation that a surface reflects |
| `tilt` | countable | angle between a rotation axis and the orbit normal |
| `parallax` | countable | apparent angular displacement of an object with a change of observing position |
| `corona` | countable | outermost plasma envelope of a star |
| `neutrino` | countable | neutral lepton of very small mass |
| `gamma-ray` | countable | photon of the highest-energy class |
| `vapor` | uncountable | substance in gas phase below its critical temperature |
| `custodian` | countable | device that maintains a cache node: media scrubbing, consolidation, manifest broadcast |
| `halo` | countable | roughly spherical outer star population of a galaxy |
| `spiral-arm` | countable | elongated overdensity of stars and gas in a galactic disc |

*Pin notes.* `biosignature` and `technosignature` are pinned as
"compatible with" — presence claims, never interpretation
claims; interpretation lives in the E-HYP register.
`trajectory` is admissible for observed bodies; its use for the
sending probe is constrained by rules TRJ-1 … TRJ-3 in the
grammar document.

### 5.2 Verbs (8)

| Verb | Tr | Sense pin |
|---|---|---|
| `survey` | tr | examine a region or body systematically and record the results |
| `deploy` | tr | move a carried device into operational position |
| `land` | intr | descend to and come to rest on a surface |
| `dock` | intr | join physically with another device |
| `depart` | intr | leave a location |
| `approach` | tr | reduce distance to |
| `relay` | tr | retransmit a received message without altering its content |
| `hibernate` | intr | enter dormancy |

### 5.3 Adjectives (7)

| Adjective | Sense pin |
|---|---|
| `interstellar` | located or occurring between star systems |
| `circumstellar` | located in orbit around a star |
| `galactocentric` | referenced to the center of this galaxy |
| `dormant` | in dormancy |
| `autonomous` | operating without external control |
| `quiescent` | showing no eruptive or flaring activity |
| `uncatalogued` | lacking an entry in the referenced catalogue |

### 5.4 Function words

None added. The base function-word set (137 entries) carries
over minus nothing; `you`/`your` never existed in it.

### 5.5 Nomenclature annex (category `Q`)

Composition claims need species names, and ad-hoc admission
invites synonymy and sense drift. The annex is a **closed**
list, extended only by specification revision, entering the
wire codebook as category `Q`.

**Element naming rule.** Element names derived from proper
nouns are excluded — they fossilize origin culture in exactly
the way `earthquake` did (§4.4), and several literally name
origin-system bodies: the origin star (*helium*), the innermost
origin planet (*mercury*), the origin planet itself
(*tellurium*), its moon (*selenium*), and three outer origin
planets (*uranium*, *neptunium*, *plutonium*). Excluded
elements are designated by typed identifiers `EL-<Z>` (atomic
number), isotopes as `EL-<Z>.<A>`, resolved against `CAT-EL`
(rule R-22). Each species has exactly one canonical form:
whitelisted species use the word and never the identifier; all
others use the identifier only.

**Worded elements (26, descriptive roots only):** `hydrogen`,
`deuterium`, `lithium`, `boron`, `carbon`, `nitrogen`,
`oxygen`, `fluorine`, `neon`, `sodium`, `silicon`,
`phosphorus`, `sulfur`, `chlorine`, `argon`, `potassium`,
`calcium`, `iron`, `bromine`, `krypton`, `iodine`, `xenon`,
`gold`, `silver`, `tin`, `lead`.

**Compounds (10):** `water`, `water-ice`, `methane`, `ammonia`,
`carbon-dioxide`, `carbon-monoxide`, `sulfur-dioxide`,
`carbonate`, `silicate`, `hydrocarbon`. (Where a compound word
already exists in the base, the §1 idempotence rule applies.)

**Stellar classification.** The traditional stellar
class letters are an origin-culture taxonomy, and single
capital letters are not tokens; the classes are inexpressible.
Stars are characterized numerically — effective temperature in
kelvin, luminosity in watts, mass in grams — which is strictly
more precise than the letter it replaces.

---

## 6. Reserved Identifier Namespaces

Identifiers are typed by prefix and appear as `inline code` in
clause text, exactly as in the base language.

| Prefix | Namespace | Assigned by |
|---|---|---|
| `P-` | probe (8 hexadecimal characters, drawn uniformly at random at manufacture; no sequence, no batch structure) | manufacture |
| `MSG-` | message (16 hexadecimal characters = digest prefix) | content |
| `PLAN-` | plan; only `PLAN-0` exists | specification |
| `PROC-` | catalogue procedure | `CAT-PROC` |
| `REG-` | region | `CAT-REG` |
| `TGT-` | observation target | `CAT-TGT` (append-only) |
| `BCN-` | beacon | `CAT-BCN` |
| `CAT-` | catalogue | specification |
| `CCH-` | cache node | `CAT-CCH` |
| `EP-` | declared epoch (message-local; value in PTS beacon cycles) | per message |
| `EL-` | chemical element `EL-<Z>` or isotope `EL-<Z>.<A>` | `CAT-EL` |
| `JRN-` | journal | per probe |
| `ARC-` | archive record | consolidation cycles |
| `THR-` | registered threshold | `CAT-THR` |
| `T` + digits | clause template (T1–T20; T2 reserved) | Wire Format §5 |
| `OBS- MSR- ACT- DER- SIM- AGG- H- DEF- COND- MOD- PAR- RUN- DAT- MET-` | clause and infrastructure numbering | per message, as in the base language |

**Feature identifiers.** A catalogued body's named parts
(a lake, a vortex, a trench site) take suffixed identifiers of
the form `<parent-id>-<suffix>` (e.g., `TGT-0451-L1`), declared
in the message envelope under the parent's `targets:` entry
(`features:` list) and resolved with the parent.

Random probe identifiers prevent an interceptor from reading
fleet size, launch order, or manufacture batches out of the
identifier space.

---

## 7. Wire Code Assignment (normative summary)

Every lexicon entry carries a stable code used by the PROBES-W
wire form. Codes are **derived, not listed**: for each category,
merge the inherited base entries (after §4 removals) with the §5
additions, sort by ASCII byte order of the canonical spelling,
and assign 1-based indices rendered in base-36.

| Category | Code shape | Example |
|---|---|---|
| Function word | `F` + 2 base-36 digits | `F07` |
| Verb | `V` + 2 base-36 digits | `V3K` |
| Noun | `N` + 2 base-36 digits | `N1A` |
| Adjective | `J` + 2 base-36 digits | `J0Q` |
| Adverb | `D` + 2 base-36 digits | `D0C` |
| Numeral/unit word | `U` + 2 base-36 digits | `U11` |
| Nomenclature (annex `Q`, §5.5) | `Q` + 2 base-36 digits | `Q0F` |

Two base-36 digits address 1,296 entries per category, which
bounds every category after removals. Because the derivation is
deterministic from the published lexicon, any two parties
holding this document and the base lexicon compute identical
codebooks — there is no separate codebook artifact to
synchronize or corrupt. Full encoding rules, including template
codes and E-tag codes, live in the Wire Format document.

---

## 8. Lexicon Summary

| Category | Base v0.4.2 | Removed | Added | PROBES v1.0 |
|---|---|---|---|---|
| Function words | 137 | 0 | 0 | 137 |
| Verbs | 325 | 0 | 8 | 333 |
| Nouns | 1,084 | 29 | 41 | ~1,096 |
| Adjectives | 239 | 0 | 7 | 246 |
| Adverbs | 52 | 0 | 0 | 52 |
| Numerals and units | 69 | 11 | 1 | 59 |
| Nomenclature annex (`Q`) | 0 | — | 36 | 36 |
| Evidential markers | 15 | 1 (`operator` source) | 4 (E-ACT, E-RLY keyword forms) | 18 |
| **Core total** | ~2,284 | | | **~2,340** |

Noun count is approximate pending the idempotence resolution of
§5.1 against the base (entries such as `interstellar-medium`
may already exist in the base's Natural and Scientific
section; the replace-pin rule of §1 makes the outcome identical
either way).

### Self-describing property (inherited)

Every §5 sense pin uses only words present in the merged
lexicon or standard English function words, preserving the base
lexicon's goal that the language can define itself without
external dictionaries — which now also serves the human
synthesizers who will expand wire messages centuries after
authorship.

### Sender-invariance test

The lexicon passes if two probes with identical catalogue
versions, instruments, and observational data produce
byte-identical message bodies. Every removal in §4 and every
one-word-per-sense decision in §2 criterion 8 serves this
property.

---

*End of PROBES CNL Lexicon v1.0.0.*
