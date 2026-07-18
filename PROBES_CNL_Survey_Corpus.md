# PROBES CNL: Survey Message Corpus and Template Coverage Analysis

## Version 1.0.0 — Corpus C-01 … C-55

---

## 1. Method

**Basis selection.** Every entry restates a finding or operation
from a flown government-agency mission (NASA, ESA, JAXA, CNSA,
Soviet program) with published, widely replicated results, or —
for the enforcement architecture only, never for findings — from
historically discussed agency-adjacent studies documented in
reputable non-fiction. Contested findings (Viking Labeled
Release, Mars methane, irregular stellar dimming, interstellar
object acceleration) appear **only in the Hypothesis register**,
which is exactly what that register exists for.

**Values.** Numeric values are representative of published
results, rounded, and unit-converted to canonical PROBES units
(meters, seconds, kelvin, pascal, tesla, radians — no years, AU,
bars, or degrees). Precision here serves clause-shape analysis,
not metrology.

**Presentation.** Each entry shows body clauses only; envelopes,
section placement, and register blocks are elided. Every clause
is register-compatible per grammar §6.5. Catalogue identifiers
(`TGT-*`, `REG-*`, `CCH-*`, instrument IDs) are illustrative.
Each clause carries a bracket tag: `[T<n>]` = fits a v1.0
template; `[FREE→T<n>]` = no v1.0 template fits, captured by a
adopted new template; `[W-free]` = remains free-form;
`[E-PRO]` = imperative procedure step (templates do not apply).

---

## 2. Corpus

### A. Giant-planet systems

**C-01 · Eruption plumes on a volcanically active moon** — basis: Voyager 1 at Io (NASA, 1979).
An eruption plume appears on `TGT-0210` (observed, `CAM-3`). [T4]
The height of the plume reaches 300 kilometers (measured, `CAM-3`, 1-sigma). [T1]

**C-02 · Plasma torus along a moon's orbit** — basis: Voyager plasma observations of the Io torus (NASA, 1979).
The electron density at `REG-0210` equals 2.0e9 per cubic meter (measured, `PLW-1`, 1-sigma). [T13]

**C-03 · Vortex wind speeds on a gas giant** — basis: Voyager imaging of Jupiter's Great Red Spot (NASA, 1979).
The wind speed of `TGT-0201-V1` equals 120 meters per second (measured, `CAM-3`, 1-sigma). [T1]

**C-04 · Radiation belt hazard record** — basis: Pioneer 10 at Jupiter (NASA, 1973).
The particle flux at `REG-0201` exceeds threshold `THR-3` (measured, `RAD-1`). [T10]

**C-05 · Intrinsic magnetic field of a moon** — basis: Galileo at Ganymede (NASA, 1996).
The magnetic-field strength of `TGT-0453` equals 720 nanotesla (measured, `MAG-1`, 1-sigma). [T1]

**C-06 · Induced magnetic response of an ice-covered moon** — basis: Galileo magnetometer at Europa (NASA, 1997–2000).
The magnetic response of `TGT-0452` varies with the external field phase (observed, `MAG-1`). [W-free]
The response pattern of `TGT-0452` remains compatible with this candidate (hypothesis, candidate `H-1`, from `MSR-5.4`, distinguishable-from `H-2`). [T9]
*(H-1: a conductive subsurface liquid layer; H-2: a conductive core.)*

**C-07 · Plume venting and its composition on a small icy moon** — basis: Cassini at Enceladus (NASA/ESA/Italian Space Agency, 2005; plume hydrogen 2017).
A water-ice plume appears on `TGT-0455` (observed, `CAM-3`). [T4]
The hydrogen fraction of the plume equals 0.009 (measured, `MSP-1`, 1-sigma). [T7]
The plume composition remains compatible with this candidate (hypothesis, candidate `H-1`, from `MSR-5.2`, distinguishable-from `H-2`). [T9]
*(H-1: hydrothermal water-rock reactions; H-2: primordial ice outgassing.)*

**C-08 · Surface conditions under a haze-shrouded atmosphere** — basis: Huygens descent and landing on Titan (ESA/NASA, 2005).
The surface temperature of `TGT-0451` equals 93.7 kelvin (measured, `TMP-1`, 1-sigma). [T1]
The surface pressure of `TGT-0451` equals 146.7 kilopascal (measured, `PRS-1`, 1-sigma). [T1]

**C-09 · Hydrocarbon lakes and their depth** — basis: Cassini radar bathymetry of Titan's seas (NASA/ESA/Italian Space Agency, 2013).
A hydrocarbon lake appears on `TGT-0451` (detected, `RDR-1`). [T4]
The depth of `TGT-0451-L1` equals 160 meters (measured, `RDR-1`, 1-sigma). [T1]

**C-10 · Ring system radial structure** — basis: Voyager ring observations at Saturn (NASA, 1980–81).
The inner radius of the ring system of `TGT-0401` equals 6.7e7 meters (measured, `CAM-3`, 1-sigma). [T1]
The outer radius of the ring system of `TGT-0401` equals 1.37e8 meters (measured, `CAM-3`, 1-sigma). [T1]

**C-11 · Extreme winds on an ice giant** — basis: Voyager 2 at Neptune (NASA, 1989).
The wind speed of `TGT-0801` equals 400 meters per second (measured, `CAM-3`, 1-sigma). [T1]

**C-12 · Active geysers on a cold moon** — basis: Voyager 2 at Triton (NASA, 1989).
A dark geyser plume appears on `TGT-0810` (observed, `CAM-3`). [T4]
The height of the plume reaches 8 kilometers (measured, `CAM-3`, 1-sigma). [T1]

**C-13 · Anomalous axial tilt of an ice giant** — basis: Voyager 2 at Uranus (NASA, 1986).
The axial tilt of `TGT-0701` equals 1.71 radians (measured, `CAM-3`, 1-sigma). [T1]

### B. Terrestrial planets and their surfaces

**C-14 · Surface conditions on a runaway-greenhouse planet** — basis: Venera 7 and 9 landings on Venus (Soviet program, 1970/1975).
The surface temperature of `TGT-0102` equals 735 kelvin (measured, `TMP-1`, 1-sigma). [T1]
The surface pressure of `TGT-0102` equals 9.2 megapascal (measured, `PRS-1`, 1-sigma). [T1]

**C-15 · First surface imaging under dense cloud** — basis: Venera 9 surface panoramas (Soviet program, 1975).
The probe deployed lander `LND-1` at `TGT-0102` (executed, procedure `PROC-31`, journal `JRN-1`). [T12]
Flat rock slabs appear on `TGT-0102` (observed, `CAM-3`). [T4]

**C-16 · Global radar mapping of a cloud-covered planet** — basis: Magellan at Venus (NASA, 1990–1994).
The radar survey of `TGT-0102` reached completion (executed, procedure `PROC-12`, journal `JRN-1`). [T3]
The mapped fraction of `TGT-0102` equals 0.98 (derived, from `ACT-3.1`, `DEF-1.2`). [T7]

**C-17 · Aerobraking procedure** — basis: Magellan's first operational aerobraking campaign (NASA, 1993).
1. Lower the orbit periapsis into the upper atmosphere of `TGT-0102` (procedure, step 1). [E-PRO]
2. Measure the deceleration during each atmospheric passage (procedure, step 2). [E-PRO]
3. Raise the periapsis at target orbit energy (procedure, step 3, if `COND-2.1`). [E-PRO]

**C-18 · Spin-orbit resonance of an inner planet** — basis: radar rotation measurement of Mercury (1965) and MESSENGER (NASA, 2011–2015).
The ratio of the rotation period to the orbital period of `TGT-0101` equals 1.5 (derived, from `MSR-5.1`, `MSR-5.2`). [T15]

**C-19 · Polar ice in permanently shadowed craters** — basis: MESSENGER neutron spectrometry at Mercury (NASA, 2012).
A hydrogen excess appears at `REG-0101` (detected, `NSP-1`). [T4]
The hydrogen distribution follows from water-ice deposits within shadowed craters (derived, from `MSR-5.3`, `DEF-1.4`). [W-free]

**C-20 · Powered soft landing on a dusty planet** — basis: Viking 1 landing on Mars (NASA, 1976).
The probe landed on `TGT-0103` (executed, procedure `PROC-20`, journal `JRN-1`). [T18]

**C-21 · Ambiguous surface reactivity experiment** — basis: Viking Labeled Release experiment (NASA, 1976; interpretation debated in the peer-reviewed literature).
The gas release pattern of the soil samples remains compatible with this candidate (hypothesis, candidate `H-1`, from `MSR-5.6`, distinguishable-from `H-2`). [T9]
*(H-1: chemical oxidant reactions; H-2: biological activity.)*

**C-22 · Transient trace gas in a thin atmosphere** — basis: Curiosity tunable laser spectrometer methane detections (NASA, 2013/2019).
A methane increase appeared on `TGT-0103` at epoch `EP-2` (detected, `SPEC-2`). [T16]
The methane fraction of the atmosphere of `TGT-0103` equals 7.0e-9 (measured, `SPEC-2`, 1-sigma). [T7]
The transient pattern remains compatible with this candidate (hypothesis, candidate `H-1`, from `MSR-5.7`, distinguishable-from `H-2`). [T9]
*(H-1: subsurface gas seepage; H-2: instrument-local release.)*

**C-23 · Seasonal dark streaks on slopes** — basis: Mars Reconnaissance Orbiter recurring-slope-streak observations (NASA, 2011).
Dark slope streaks appear on `TGT-0103` (observed, `CAM-3`). [T4]
The streak pattern remains compatible with this candidate (hypothesis, candidate `H-1`, from `OBS-4.6`, distinguishable-from `H-2`). [T9]
*(H-1: dry granular flows; H-2: transient brine flows.)*

**C-24 · Subsurface ice exposed by digging** — basis: Phoenix trench operations (NASA, 2008).
The trench excavation at `TGT-0103` reached completion (executed, procedure `PROC-33`, journal `JRN-1`, steps 1-4). [T3]
A bright subsurface layer appeared at `TGT-0103-S2` at epoch `EP-3` (observed, `CAM-3`). [T16]
The layer receded within 350 kiloseconds (observed, `CAM-3`). [W-free]

**C-25 · Sample cache depot on a planetary surface** — basis: Perseverance sample depot at Three Forks (NASA, 2022–2023).
The probe deployed cache `CCH-0031` at `TGT-0103-S5` (executed, procedure `PROC-40`, journal `JRN-1`). [T12]
The count of sample containers in `CCH-0031` equals 10 (registered, `ARM-1`). [T6]

**C-26 · Bulk atmospheric composition** — basis: Viking atmospheric analysis at Mars (NASA, 1976).
The carbon-dioxide fraction of the atmosphere of `TGT-0103` equals 0.95 (measured, `MSP-1`, 1-sigma). [T7]

### C. Small bodies

**C-27 · Darkest-known nucleus albedo** — basis: Giotto at comet Halley (ESA, 1986).
The albedo of `TGT-0901` equals 0.04 (measured, `CAM-3`, 1-sigma). [T1]

**C-28 · Isotope ratio of cometary water** — basis: Rosetta ROSINA measurement at comet 67P (ESA, 2014).
The ratio of deuterium to hydrogen in the water vapor of `TGT-0902` equals 5.3e-4 (measured, `MSP-1`, 1-sigma). [T15]

**C-29 · Bouncing touchdown of a small lander** — basis: Philae landing on 67P (ESA, 2014).
The probe deployed lander `LND-2` at `TGT-0902` (executed, procedure `PROC-31`, journal `JRN-1`). [T12]
The count of surface contacts of `LND-2` equals 3 (registered, `IMU-1`). [T6]

**C-30 · End-of-mission touchdown on an asteroid** — basis: NEAR Shoemaker landing on Eros (NASA, 2001).
The probe landed on `TGT-0903` (executed, procedure `PROC-20`, journal `JRN-1`). [T18]

**C-31 · Kinetic impact experiment on a comet** — basis: Deep Impact at Tempel 1 (NASA, 2005).
The impactor release at `TGT-0904` reached completion (executed, procedure `PROC-45`, journal `JRN-1`). [T3]
An ejecta plume appears on `TGT-0904` (observed, `CAM-3`). [T4]

**C-32 · Rubble-pile bulk density** — basis: Hayabusa at Itokawa (JAXA, 2005).
The bulk density of `TGT-0905` equals 1900 kilograms per cubic meter (derived, from `MSR-5.1`, `MSR-5.2`). [T1]

**C-33 · Subsurface sample collection via impactor** — basis: Hayabusa2 impactor operation and sampling at Ryugu (JAXA, 2019).
The impactor release at `TGT-0906` reached completion (executed, procedure `PROC-45`, journal `JRN-1`). [T3]
The probe collected 5.4 grams of regolith from `TGT-0906` (executed, procedure `PROC-46`, journal `JRN-1`). [T17]

**C-34 · Active particle ejection from an asteroid** — basis: OSIRIS-REx particle ejection events at Bennu (NASA, 2019) and sample return (2020–2023).
A particle ejection appeared on `TGT-0907` at epoch `EP-4` (observed, `CAM-3`). [T16]
The probe collected 121.6 grams of regolith from `TGT-0907` (executed, procedure `PROC-46`, journal `JRN-1`). [T17]

**C-35 · Bright carbonate deposits on a dwarf planet** — basis: Dawn at Ceres, Occator faculae (NASA, 2015).
Bright deposits appear on `TGT-0908` (observed, `CAM-3`). [T4]
The absorption feature of carbonate appears at 3.4 micrometers (measured, `SPEC-2`, 1-sigma). [T14]

**C-36 · Nitrogen-ice plain and layered haze** — basis: New Horizons at Pluto (NASA, 2015).
A nitrogen ice sheet appears on `TGT-0910` (observed, `CAM-3`). [T4]
The count of haze layers in the atmosphere of `TGT-0910` equals 20 (observed, `CAM-3`). [T6]
The flyby distance of `TGT-0910` equals 1.25e7 meters (executed, procedure `PROC-15`, journal `JRN-1`). [T1]

**C-37 · Contact-binary shape of a cold classical object** — basis: New Horizons at Arrokoth (NASA, 2019).
Two joined lobes form `TGT-0921` (observed, `CAM-3`). [W-free]
The length of `TGT-0921` equals 3.6e4 meters (measured, `CAM-3`, 1-sigma). [T1]

### D. Star, wind, and interstellar boundary

**C-38 · Crossing the stellar-wind boundary** — basis: Voyager 1 heliopause crossing (NASA, 2012).
The plasma density at `REG-0501` equals 2.0e3 per cubic meter (measured, `PLW-1`, 1-sigma). [T13]
The plasma density at `REG-0502` equals 8.0e4 per cubic meter (measured, `PLW-1`, 1-sigma). [T13]
The boundary between `REG-0501` and `REG-0502` follows from the density step (derived, from `MSR-5.1`, `MSR-5.2`). [W-free]

**C-39 · Fast polar wind of a star** — basis: Ulysses polar passes (ESA/NASA, 1994–1995).
The wind speed at `REG-0503` equals 7.5e5 meters per second (measured, `PLW-1`, 1-sigma). [T13]

**C-40 · Passage through a stellar corona** — basis: Parker Solar Probe corona passage (NASA, 2021).
The corona passage of `TGT-0001` reached completion (executed, procedure `PROC-16`, journal `JRN-1`). [T3]
**Switchbacks** appear within the wind flow (detected, `MAG-1`). [T4]

```definition
A switchback designates a rapid local reversal of the
magnetic-field direction along the wind flow (defined).
```

**C-41 · Sky-spanning band of energetic neutral atoms** — basis: Interstellar Boundary Explorer ribbon discovery (NASA, 2009).
A narrow emission band appears across `REG-0504` (detected, `ENA-1`). [T4]
The band geometry remains compatible with this candidate (hypothesis, candidate `H-1`, from `OBS-4.2`, distinguishable-from `H-2`). [T9]
*(H-1: alignment with the local interstellar magnetic field; H-2: local wind-medium pressure structure.)*

**C-42 · First detected gamma-ray burst** — basis: Vela satellite detections (US program, 1967; declassified and published 1973).
A gamma-ray burst appeared at epoch `EP-5` (detected, `GRD-1`). [T16]

**C-43 · Neutrino burst from a nearby supernova** — basis: Kamiokande-II detection of SN 1987A neutrinos (Japan, 1987).
The count of neutrino events within 13 seconds equals 11 (registered, `NTD-1`). [W-free]
A supernova appeared at `TGT-0940` at epoch `EP-6` (observed, `CAM-3`). [T16]

### E. Stellar and planetary surveys

**C-44 · Planetary transit photometry** — basis: Kepler mission transit detections (NASA, 2009–2018).
The transit depth of `TGT-0011-P1` equals 8.4e-5 (measured, `PHM-1`, 1-sigma). [T1]

**C-45 · Planet occurrence statistics** — basis: Kepler occurrence-rate analyses (NASA, 2010s).
The mean planet count per star equals 1.0 (aggregated, from dataset `DAT-1`, method `MET-1`, n=150000). [W-free]

**C-46 · Stellar wobble from an orbiting giant** — basis: the first radial-velocity giant-planet detection (Observatoire de Haute-Provence, 1995; program heritage adopted by agency surveys).
The velocity amplitude of `TGT-0009` equals 56 meters per second (measured, `SPEC-2`, 1-sigma). [T1]

**C-47 · Transmission spectroscopy of a giant planet's atmosphere** — basis: James Webb Space Telescope transmission spectrum of a hot giant planet (NASA/ESA/Canadian Space Agency, 2022).
The absorption feature of carbon-dioxide appears at 4.3 micrometers (measured, `SPEC-2`, 1-sigma). [T14]
The absorption feature of sulfur-dioxide appears at 4.05 micrometers (measured, `SPEC-2`, 1-sigma). [T14]

**C-48 · Irregular deep dimming of a star** — basis: Kepler photometry of an irregularly dimming star (published 2015; natural-origin candidates favored in follow-up literature).
A dimming of fraction 0.22 appeared at `TGT-0012` at epoch `EP-7` (measured, `PHM-1`, 1-sigma). [T16]
The dimming pattern remains compatible with this candidate (hypothesis, candidate `H-1`, from `MSR-5.3`, distinguishable-from `H-2`). [T9]
*(H-1: circumstellar dust clouds; H-2: fragmented body swarms.)*

**C-49 · Beacon timing maintenance** — basis: millisecond-pulsar timing practice and the SEXTANT X-ray pulsar navigation demonstration (NASA, 2018).
The rotation period of `BCN-3` equals 5.7575 milliseconds (measured, `XRT-1`, 1-sigma). [T1]
The period drift rate of `BCN-3` equals 5.7e-20 seconds per second (cited, from `ARC-0007`). [T1]

**C-50 · Fleet-baseline astrometry** — basis: space astrometry practice (ESA astrometry missions, 1989–present), re-realized with inter-probe baselines.
The parallax angle of `TGT-0007` equals 1.2e-8 radians (relayed, from `MSG-77A0B3C4D5E6F011`, hops=1). [T1]
The distance from the frame center to `TGT-0007` equals 2.1 exameters (derived, from `MSR-5.1`, `RLY-9.1`). [T19]

**C-51 · Interstellar object on a hyperbolic path** — basis: observations of the first detected interstellar object (2017; non-gravitational acceleration published 2018).
The ratio of the long axis to the short axis of `TGT-0930` equals 6 (derived, from `MSR-5.1`, `MSR-5.2`). [T15]
The residual acceleration of `TGT-0930` equals 5.0e-6 meters per second per second (derived, from `MSR-5.3`, `MOD-1`). [T1]
The residual acceleration remains compatible with this candidate (hypothesis, candidate `H-1`, from `DER-6.2`, distinguishable-from `H-2`). [T9]
*(H-1: outgassing without a visible coma; H-2: radiation-pressure effects on a low-density body.)*

**C-52 · Impact-plume volatile detection at a shadowed pole** — basis: Lunar Crater Observation and Sensing Satellite impact experiment at the lunar south pole (NASA, 2009).
The impactor release at `TGT-0104` reached completion (executed, procedure `PROC-45`, journal `JRN-1`). [T3]
The water-ice fraction of the ejecta plume equals 0.056 (measured, `SPEC-2`, 2-sigma). [T7]

### F. Simulation and relay registers

**C-53 · Ice-shell thickness from interior modeling** — basis: peer-reviewed interior models of Enceladus (2010s).
The simulated ice thickness of `TGT-0455` equals 21 kilometers (simulated, from model `MOD-1`, parameters `PAR-1`, run `RUN-1`). [T1]

**C-54 · Relay of a plume-composition claim** — basis: store-and-forward restatement of C-07.
The hydrogen fraction of the plume of `TGT-0455` equals 0.009 (relayed, from `MSG-6D0C11A94EB2F7A0`, hops=1). [T7]

**C-55 · First landing on the far side of a moon** — basis: Chang'e 4 landing (China National Space Administration, 2019).
The probe landed on `TGT-0104` (executed, procedure `PROC-20`, journal `JRN-1`). [T18]

---

*Statistics and findings follow in §3–§5.*

## 3. Coverage Statistics

55 messages; 95 clauses total; 3 imperative procedure steps;
**92 declarative clauses** analyzed against the registered
template set (Wire Format §5.3).

### 3.1 Template hits (85 clauses, 92.4%)

| Template | Hits | Notes |
|---|---|---|
| T1 measurement (incl. dimensionless and `reaches` forms) | 24 | the workhorse, as designed |
| T4 presence | 12 | uses every preposition in the selector |
| T9 hypothesis-compatibility | 8 | every contested finding routed here cleanly |
| T3 completion | 6 | E-ACT records |
| T7 fraction | 6 | |
| T16 dated event | 6 | all reference declared `EP-*` epochs |
| T13 locative measurement | 4 | value *at* a region, not *of* an object |
| T6 count | 3 | |
| T12 deployment | 3 | includes cache emplacement |
| T14 spectral feature | 3 | spectroscopy is the survey workhorse |
| T15 ratio | 3 | isotope ratios, resonances, axis ratios |
| T18 landing | 3 | one-slot, high-frequency |
| T17 sample collection | 2 | |
| T10 threshold exceedance | 1 | |
| T19 center-distance | 1 | |
| T5 absence | 0 | unexercised here; retained — null results matter |
| T8 orbital element | 0 | unexercised here; retained — orbit surveys will use it |
| T11 cache at coordinates | 0 | unexercised here; retained for deep-space (non-site) caches |
| T2 | — | reserved identifier; uncertainty is expressed in E-MSR tag arguments, never in the clause interior |

### 3.2 Residual free-form (7 clauses, 7.6%)

C-06 (co-variation), C-19 and C-38 (mechanism derivations),
C-24 (process verb with duration), C-37 (morphology), C-43
(count within a time window), C-45 (aggregate statistic).
Mechanism prose, morphology, and statistical aggregates resist
templating without loss; the `W:` free-form encoding remains
the right tool for them, and their share sets the expected
free-form floor for fleet traffic.

### 3.3 E-tag exercise across the corpus

E-MSR 32 · E-OBS 24 · E-ACT 15 · E-DER 8 · E-HYP 8 · E-PRO 3 ·
E-RLY 2 · E-DEF 1 · E-RPT 1 · E-SIM 1 · E-AGG 1. The heavy
E-ACT share (16% of declaratives) reflects real mission
traffic: it is thick with "what the craft did."

## 4. What the Corpus Establishes

*(The development trail from this corpus to the specification
is recorded in `PROBES_CNL_Amendment_Record.md`; the notes
below describe the language as it stands.)*

**N-1 · Uncertainty lives in the tag, not the interior.** Every
uncertain measurement in the corpus carries `1-sigma`,
`2-sigma`, or `± n unit` inside the E-MSR frame; no clause
needed an interior-level uncertainty form, which is why the T2
identifier stays reserved and unused — two encodings of one
clause would break the compaction bijection (Wire Format §8).

**N-2 · Preposition selectors earn their place.** Corpus usage
spans `of`, `on`, `in`, `at`, `within`, and `across` in T4, T6,
and T16 — the full closed selector, with no case falling
outside it.

**N-3 · Extents decompose.** Ring spans and plume heights
resolve into T1 pairs (inner/outer radius) or the T1 `reaches`
form; the template set needs no range template.

**N-4 · Dated events require declared epochs.** Six transients
(eruptions, bursts, dimmings, ejections) reference `EP-*`
entries from the `epochs:` envelope list; writing beacon-cycle
expressions inline would exceed the 18-token clause cap.

**N-5 · Cache and feature identifiers are live vocabulary.**
Sample-depot emplacement (C-25) exercises `CCH-*` with a
feature-site identifier, and part-of-body features
(`TGT-0451-L1`, `TGT-0103-S5`) appear throughout — the
location-phrase slot grammar (Wire Format §5.3) matches how
survey clauses are actually written.

**N-6 · Composition claims run through the nomenclature
annex.** `hydrogen`, `deuterium`, `oxygen`, `methane`,
`carbonate`, `carbon-dioxide`, `sulfur-dioxide`, and `water-ice`
all occur; the closed annex (Lexicon §5.5) covers the corpus
without ad-hoc admissions.

**N-7 · Gram-based masses read naturally.** Sample masses
appear as "5.4 grams" and "121.6 grams"; bulk density composes
as "kilograms per cubic meter" through the prefix system.

**N-8 · Corpus-demanded vocabulary is present.** `plume`,
`geyser`, `haze`, `lake`, `streak`, `ejecta`, `impactor`,
`albedo`, `tilt`, `parallax`, `corona`, `neutrino`,
`gamma-ray`, and `vapor` are carried in Lexicon §5.1, subject
to the §1 idempotence rule against the base.

## 5. Cross-Reference

Template skeletons and slot grammar: Wire Format §5.3.
Evidential frames and register rules: Evidential System and
Message Grammar §2, §6.5. Identifier namespaces: Lexicon §6.

---

*End of PROBES CNL Survey Corpus v1.0.0.*
