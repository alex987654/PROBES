# PROBES CNL: Worked Examples

## Version 1.0.0

---

## 1. Compliant Survey Message — PROBES-H (human form)

```yaml
---
schema: probes-cnl-v1.0
message: MSG-9B2E44C7A1D0F358
sender: P-7F3A9C21
plan: PLAN-0
epoch: "BCN-3: 8214559102334 + BCN-5: 130995824"
position: "GSF -8.21e18 2.44e17 6.1e16 meter"
region: REG-4471
catalogues:
  CAT-BCN: 14
  CAT-PROC: 9
  CAT-REG: 3
  CAT-TGT: 203
beacons: [BCN-0, BCN-1, BCN-3, BCN-5]
targets:
  - id: TGT-1088
    catalogue: CAT-TGT
  - id: TGT-1090
    catalogue: CAT-TGT
instruments:
  - id: SPEC-2
    type: spectrometer
  - id: CAM-3
    type: camera
  - id: MAG-1
    type: magnetometer
  - id: RX-1
    type: receiver
  - id: LND-1
    type: lander
procedures:
  - id: PROC-12
    catalogue: CAT-PROC
  - id: PROC-31
    catalogue: CAT-PROC
journals:
  - id: JRN-1
caches: []
epochs: []
references: []
messages_cited: []
technical_names: []
conditions: []
models: []
parameter_sets: []
simulation_runs: []
datasets: []
methods: []
hypothesis_space:
  - id: H-1
    statement: "the oxygen fraction follows from non-biological processes"
    discriminates_via: [MSR-5.1]
  - id: H-2
    statement: "the oxygen fraction follows from biological processes"
    discriminates_via: [MSR-5.1]
digest: 9b2e44c7a1d0f358aa10b6c94d21e7f3c0884d1a52ef90b7361cd42a8fe15690
---
```

## Execution

```execution
The survey of region `REG-4471` reached completion (executed, procedure `PROC-12`, journal `JRN-1`).
The probe deployed lander `LND-1` at `TGT-1088` (executed, procedure `PROC-31`, journal `JRN-1`, steps 1-6).
```

## Observations

> A ring-system appears on `TGT-1090` (observed, `CAM-3`).
> No technosignature appears on `TGT-1088` (observed, `RX-1`).

## Measurements

```measurement
The oxygen fraction of `TGT-1088` equals 0.004 (measured, `SPEC-2`, 1-sigma).
The rotation period of `TGT-1088` equals 62.4 kiloseconds (measured, `CAM-3`, ± 0.2 kilosecond).
The magnetic-field strength of `TGT-1088` equals 31 microtesla (measured, `MAG-1`, 2-sigma).
```

## Derivations

The surface acceleration of `TGT-1088` equals 8.9 meters per second per second (calculated, from `MSR-5.2`, `MSR-5.3`).

## Hypothesis — oxygen source at `TGT-1088`

The oxygen pattern of `TGT-1088` remains compatible with this candidate (hypothesis, candidate `H-1`, from `MSR-5.1`, distinguishable-from `H-2`).

---

### 1.1 What this message demonstrates

- **Self-identification without self-disclosure.** `P-7F3A9C21`
  appears once, in the envelope; the body is a pure function of
  the data (sender-invariance).
- **Origin-free spacetime.** Position in GSF meters; epoch in
  beacon cycles; rotation period in kiloseconds — no calendar,
  no origin-derived units.
- **Coordination without tasking.** The E-ACT completion record
  is all another probe needs: applying `PROC-1`'s deterministic
  region-selection rule to this fact steers it elsewhere. No
  imperative crossed the channel.
- **Bounded interpretation.** The biosignature question lives
  strictly in the Hypothesis register, as two declared,
  discriminable candidates — never as a claim.

---

## 2. The Same Message — PROBES-W (wire form)

Word codes below are illustrative; authoritative indices come
from the codebook derivation (Lexicon §7) applied to Lexicon
v1.0.

```
%PW1
@|SC=1.0|MG=9B2E44C7A1D0F358|SN=P-7F3A9C21|PL=0|EP=B3:8214559102334,B5:130995824|PO=-8.21e18,2.44e17,6.1e16|RG=4471|CT=BCN:14,PRC:9,REG:3,TGT:203|DG=9b2e44c7a1d0f358aa10b6c94d21e7f3c0884d1a52ef90b7361cd42a8fe15690
D|BCN|0|1|3|5
D|TGT|1088|1090
D|INS|CAM-3=N0K|LND-1=N3D|MAG-1=N3H|RX-1=N5A|SPEC-2=N5T
D|PRC|12|31
D|JRN|1
D|HYP|H-1=1|H-2=2
#|3
C|A|p=PROC-12|j=JRN-1|T3:N5V;REG-4471
C|A|p=PROC-31|j=JRN-1|st=1-6|T12:N3D;TGT-1088
#|4
C|O|v=1|s=CAM-3|T4:N4R;TGT-1090
C|O|v=1|s=RX-1|T5:N6B;TGT-1088
#|5
C|M|v=1|s=SPEC-2|u=1s|T7:N4M;TGT-1088;0.004
C|M|v=1|s=CAM-3|u=pm,0.2,k,U2B|T1:N4Y N4C;TGT-1088;62.4;k,U2B
C|M|v=1|s=MAG-1|u=2s|T1:N3H N5S;TGT-1088;31;u,U2T
#|6
C|E|v=2|f=MSR-5.2;MSR-5.3|T1:N5R N01;TGT-1088;8.9;U1M,F5C,U2B,F5C,U2B
#|11
C|H|c=H-1|f=MSR-5.1|x=H-2|T9:N4M;TGT-1088
```

Header, declarations, section marks, template instances,
regenerated punctuation: the H-form above (~1,480 bytes)
round-trips from ~500 bytes of wire.

---

## 3. Relay Message (excerpt)

A probe passing near a cache retransmits a claim it did not
observe:

```yaml
messages_cited:
  - id: MSG-4C11D02A9E44B7F0
    digest: 4c11d02a9e44b7f0e91b3a77c2d5f6a83309cc12de40b6a1f7e2559d08c4b3aa
```

## Relay

```relay
The methane fraction of `TGT-2210` equals 0.031 (relayed, from `MSG-4C11D02A9E44B7F0`, hops=1).
```

The receiving probe verifies the cited digest, counts the hop,
and treats the claim as Tier 2. At hops=2 a further relay draws
a warning; at hops=3 filter mode drops the clause — the fact
must be re-observed or wait for archive consolidation.

### 3.1 Manifest at a cache node

The custodial device at a cache registers deposits (envelope
elided; custodian instrument `CST-1` and cache `CCH-0102`
declared there):

## Manifest

```manifest
Message `MSG-4C11D02A9E44B7F0` rests in cache `CCH-0102` (registered, `CST-1`).
```

Manifest broadcasts double as the fleet's only delivery
receipts: the original sender, passing within link range
centuries later, learns its message survived when a manifest
lists the `MSG-*` identifier. No acknowledgment grammar exists
or is needed.

---

## 4. Hazard Record Without a Warning

No deontic vocabulary exists, so "danger — avoid!" is
inexpressible. The same protective content travels as
measurement plus registered constraint:

```measurement
The particle flux at region `REG-0032` equals 4.1e8 per square meter per second (measured, `RAD-1`).
```

```constraint
Procedure `PROC-44` applies at particle flux above threshold `THR-3` (defined).
```

Any probe holding the catalogue applies `PROC-44` (shielded
transit) when its own reading, or a relayed one, exceeds
`THR-3`. Protection propagates as fact plus rule, never as
alarm — which also means a compromised probe cannot spread
panic it cannot phrase.

---

## 5. Non-Compliant Examples (with failure reasons)

**Tasking another probe.**
"Probe `P-33D1B2AA` surveys region `REG-0032` next (procedure)."
— E-PRO-4: a procedure may not name another probe as actor;
also fails O-1/O-2 (procedure outside an ordered list).

**Second-hand action as bare fact.**
"Probe `P-33D1B2AA` completed the survey of `REG-0032`
(observed, `RX-1`)." — E-ACT-3 deny-list: another probe's
action is expressible only as E-RLY citing that probe's own
E-ACT message.

**Origin leak.**
"The fleet departed Earth 400 years ago." — proper noun
(banned class), `years` (calendar class), provenance framing;
no E-tag. Rejected at Layer 1 three times over.

**Second intent.**
"This probe operates toward the detection of life." —
purposive construction; intent beyond `PLAN-0` has no
vocabulary. Rejected at Layer 1.

**Trajectory self-history.**
"The probe traveled from `REG-0031` to `REG-4471` between the
two epochs (observed, `NAV-1`)." — TRJ-2: no clause relates two
sender positions at different epochs.

**Removed unit.**
"The orbital period of `TGT-1090` equals 1.2 years (measured,
`CAM-3`)." — E-MSR-3 / U-1: `year` does not exist; the
canonical form reads "equals 37.9 megaseconds."

**Evaluative interpretation.**
"Target `TGT-1088` shows a promising biosignature (observed,
`SPEC-2`)." — `promising` (evaluative) fails Layer 1; the
interpretation belongs in the Hypothesis register as declared
candidates.

**Self-state disclosure.**
"The energy reserve of the probe equals 2.1 gigajoules
(measured, `PWR-1`)." — SELF-1: quantities predicated on the
sending probe's internal state are inexpressible. No recipient
can act on them (no tasking or rescue exists), and internal
state is not a function of observations, so publishing it would
break sender-invariance.

**Relay depth exceeded.**
"… (relayed, from `MSG-77A0…`, hops=3)." — E-RLY-2 rejection;
filter mode drops the clause at every receiver.

---

## 6. Human Synthesis Notes

A synthesis pipeline (human or AI-assisted) receiving centuries
of fleet traffic:

1. **Expand** PROBES-W to PROBES-H mechanically (Wire Format
   §8); verify digests; deduplicate by `MG` and by
   (sender, region, procedure) on E-ACT records.
2. **Weight by tier.** Tier 1 clauses (E-OBS, E-MSR, E-ACT)
   anchor the report; Tier 2 clauses carry their full pedigree
   (premises, models, datasets, hop counts) for audit; Tier 3
   clauses supply the definitions and procedures that make the
   rest interpretable.
3. **Read hypotheses as hypotheses.** E-HYP candidates arrive
   pre-bracketed with their discriminating measurements —
   the report's open questions write themselves.
4. **Trust the register, not the author.** No clause can
   address the reader, evaluate, urge, or warn; the language a
   compromised probe would need in order to manipulate the
   synthesizer does not exist. What survives filter mode is,
   by construction, method.

The expansion output is controlled English: terse, but ordinary
scientific readers parse it without training, and every clause
answers "how does the fleet hold this claim?" before the reader
thinks to ask.

---

*End of PROBES CNL Examples v1.0.0.*
