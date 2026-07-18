# PROBES CNL: Transport Layer (TP)

## Version 1.0.0

*Normative companion to the Wire Format document. Defines the
framing, forward error correction, and erasure-coding profiles
that carry canonical PROBES-W bytes over links, media at rest,
and physical carriage. Everything in this document sits
**below** the canonical form: nothing here changes a single
canonical byte, and the language layers above never see it.*

---

## 1. Layering Contract

```
[ physical channel / storage medium ]
[ TP: framing + forward error correction + erasure coding ]
[ PROBES-W canonical bytes ]             <- digest computed here
[ PROBES-H expansion ]                   <- generated on demand
```

**TR-1 (subordination).** Transport carries opaque octets of
the canonical form. No transport mechanism may reorder, edit,
compress-lossily, or annotate canonical content.

**TR-2 (integrity locus).** The message digest `DG` is computed
and verified over canonical bytes **after** transport decode.
Frame CRCs detect damage; only `DG` establishes message
integrity.

**TR-3 (uniformity).** Every profile parameter in this document
is a fixed constant of the specification. No sender-selectable
knob exists — code rate, interleaver depth, modulation order,
frame length, and slot quantum admit no per-probe variation.
Rationale: any free transport parameter is a covert channel and
a sender fingerprint; uniformity is sender-invariance at the
octet level.

**TR-4 (emission discipline).** Transmissions occur only inside
catalogue-defined slots (Physical Architecture §6.3), padded to
the slot quantum. Padding consists of additional repair symbols
(§4), never idle fill — the padding is useful redundancy, and
constant-size emissions defeat traffic-shape analysis.

---

## 2. Channel Error Models

| Segment | Dominant impairments | Model |
|---|---|---|
| Optical link (node↔node, probe↔node) | photon starvation, pointing dropouts, background transients | erasure-dominated: whole frames arrive or vanish; surviving frames near-clean after inner decode |
| Media at rest (centuries–millennia) | radiation tracks, micrometeoroid strikes, media aging | spatially correlated block damage: small clusters of destroyed cells, slow uniform fade |
| Physical carriage | loss of an entire media unit or an entire cache | unit-level erasure |

Three profiles match the three models: **TP-L** (link),
**TP-M** (media), **TP-C** (cross-cache). A message may
traverse all three; each decode terminates at canonical bytes,
so profiles compose without interaction.

---

## 3. Framing (common to all profiles)

The frame is the atom of loss and recovery:

```
FRAME = SYNC(8) | HDR(17) | PAYLOAD(<=2048) | CRC32C(4)

HDR   = ver(1) | profile(1) | msgid(8) | frag_index(3)
      | frag_total(3) | hdr_crc8(1)
```

- `SYNC` is a fixed 8-octet marker with maximal
  autocorrelation distance; receivers resynchronize by scanning
  for it, so an unrecoverable burst costs the frames it
  touches, never the stream.
- `msgid` is the binary form of the canonical `MG` field —
  the only canonical value visible at transport, needed for
  reassembly. The sender identifier deliberately does **not**
  appear at transport; frames are attributable only after
  canonical decode.
- `frag_index/frag_total` support reassembly and erasure
  accounting; `hdr_crc8` lets a receiver trust the header even
  when the payload fails.
- A cyclic redundancy check (`CRC32C`) gates each frame:
  fail → the frame becomes an
  erasure, never a silent corruption.

**Fragment pool rule (TR-5).** Frames that pass CRC but belong
to a message whose `DG` cannot yet be verified are held in a
quarantine pool, keyed by `msgid`. Pooled fragments from
different copies, caches, and epochs may be combined —
cross-copy reconstruction — but **no clause from an unverified
message is ever ingested**. Verification (full `DG` match)
promotes the message; anything else stays inert. Fail-safe is
preserved: quarantine is storage, not belief.

---

## 4. TP-L — Photon-Starved Link Profile

For the bits-per-second optical regime (Physical Architecture
§2.2):

1. **Modulation:** pulse-position modulation, order fixed at
   PPM-256 (high peak-to-average, matched to photon-counting
   detection).
2. **Inner code:** serially concatenated PPM coding of the
   class standardized for deep-space optical links (Consultative Committee
   for Space Data Systems optical coding heritage; the same
   family flown on the 2023
   deep-space optical demonstration). Corrects channel noise
   within a frame; residual errors surface as CRC failures,
   i.e., erasures.
3. **Outer code — rateless fountain.** The frame set of a
   message forms a source block; the transmitter emits source
   frames followed by an unbounded stream of Raptor-class
   repair frames (systematic fountain code, RFC 6330 family)
   until the slot ends. A receiver reconstructs the message
   from **any** ~1.02 × k received frames, where k is the
   source count.

The fountain choice is forced by the regime, not preferred:
with no feedback channel possible at century latencies,
automatic-repeat-request protocols are meaningless and fixed-rate outer codes waste the slot whenever
conditions beat the design point. A rateless stream is the
optimal broadcast into the dark — every listener, whenever it
tuned in and whatever it missed, needs only *enough* frames,
not *specific* frames. TR-4's padding rule falls out for free:
the slot is always filled, and everything filling it is repair
information.

---

## 5. TP-M — Media-at-Rest Profile

For etched archival media holding messages across millennia:

1. **Block code:** Reed–Solomon (255, 223) over 8-bit symbols — the
   classic deep-space code, 16-symbol correction per codeword —
   arranged as a **product code** (rows and columns both RS),
   giving two-dimensional correction against clustered damage.
2. **Spatial interleaving:** codeword symbols are dispersed
   across physically distant zones of the medium, so a
   radiation track or micrometeoroid crater intersects many
   codewords shallowly instead of one codeword fatally.
   Interleaver geometry is a fixed constant (TR-3).
3. **Replication:** every message is written to **m = 3
   independent media units** per node, manufactured in
   different batches and stored with spatial separation, so
   unit-level failure modes decorrelate.
4. **Scrubbing:** at every consolidation cycle the custodian
   reads, decodes, digest-verifies, and rewrites degraded
   copies. Scrubbing converts slow fade into a renewable
   resource; the media budget assumes each copy survives
   several cycles unaided (§9).

Passive caches (no custodian) receive the same encoding at
double replication (m = 6) and rely on TP-C for long-run
survival.

## 6. TP-C — Cross-Cache Erasure Profile

For archives whose loss horizon is the cache itself (impact,
dynamical ejection, custodian death):

- Every `ARC-*` archive is sharded with a **(n = 5, k = 3)**
  Reed–Solomon erasure code across five caches, any three of
  which reconstruct it.
- Shard placement follows a deterministic catalogue rule:
  the five hosts are the archive's home node plus the four
  nodes selected by fixed rank order in `CAT-CCH`, each at
  least two graph edges apart, so no regional catastrophe
  (supernova sterilizing a neighborhood) claims a quorum.
- If per-cycle cache-loss probability is p, archive loss
  requires ≥3 simultaneous losses: P ≈ 10·p³ per cycle —
  p = 10⁻³ gives ~10⁻⁸ per cycle per archive.

Manifests advertise shard presence exactly like whole messages
(template T20); reconstruction is an ordinary custodial
procedure in `CAT-PROC`.

---

## 7. Decode Pipeline and Degraded Modes

```
octets -> SYNC scan -> frame CRC gate -> inner decode (TP-L)
       -> fountain / product / erasure decode (profile)
       -> canonical bytes -> DG verify -> linter (strict/filter)
```

| Condition | Behavior |
|---|---|
| All frames good, DG verifies | normal ingestion |
| Frames missing, fountain/erasure recovers | normal ingestion — indistinguishable by design |
| DG fails, frames pass CRC | fragment pool (TR-5); await cross-copy combination |
| DG verifies, linter rejects clauses | filter mode drops clauses — a language decision, not a transport one |
| SYNC lost mid-stream | resynchronize; lost span becomes erasures |

The pipeline never repairs canonical content semantically:
transport recovers bytes or nothing. All meaning-level
tolerance lives in the linter's filter mode, above the digest.

---

## 8. Covert Channels and Traffic Analysis

Transport is the layer an interceptor sees first, so it gets
the same discipline as the grammar:

- **No sender identity below the canonical layer** (§3).
- **No free parameters** (TR-3) — a probe cannot signal through
  code rate, frame timing jitter, or interleaver choice.
- **Constant emission shape** (TR-4) — fixed slot quantum,
  slots always filled with repair symbols; message count and
  size are not inferable from emission length.
- **Slot schedule is public and position-local** — emissions
  reveal that *a* compliant node transmitted in its catalogue
  slot, which every node does; nothing distinguishes senders.

Residual: the existence and locations of transmitting nodes
are physically observable — that is a property of shining
lasers in a galaxy, outside any coding layer, and is part of
why node placement carries no origin information (Physical
Architecture §3, §4.5).

---

## 9. Fixed Parameter Table

| Parameter | Value | Locus |
|---|---|---|
| Frame payload | ≤ 2048 octets | §3 |
| Frame CRC | CRC-32C | §3 |
| PPM order | 256 | TP-L |
| Inner code | serially concatenated pulse-position-modulation class | TP-L |
| Fountain | Raptor-class, systematic, overhead ~2% | TP-L |
| Media block code | Reed–Solomon (255,223) product | TP-M |
| Media replication | m = 3 custodial / m = 6 passive | TP-M |
| Scrub cadence | every consolidation cycle | TP-M |
| Cross-cache code | Reed–Solomon erasure (5,3) | TP-C |
| Shard separation | ≥ 2 graph edges | TP-C |
| Slot quantum | catalogue constant (`CAT-SLT`) | TR-4 |

All values are specification constants under TR-3; revision is
a language-suite revision, not an operational choice.

---

## 10. Grammar and Lexicon Impact

None, by construction — and that is the finding: a transport
layer designed under TR-1…TR-5 adds **zero** words, zero
E-tags, and zero envelope fields, because reliability lives
entirely below the digest. The only visible couplings are the
`msgid` mirror of `MG`, the manifest template T20 advertising
shards, and the custodial procedures (scrubbing,
reconstruction) that live as ordinary `CAT-PROC` entries in the
existing E-PRO/E-ACT machinery.

---

*End of PROBES CNL Transport Layer v1.0.0.*
