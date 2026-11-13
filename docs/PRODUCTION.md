# From local alpha to a hosted product

## Current architecture

```text
Browser (same-machine, session cookie)
  -> loopback HTTP API
      -> SQLite project / asset / select / job / export records
      -> streamed uploads in isolated generated directories
      -> one durable queued worker
          -> PyAV media headers / FFmpeg browser preview
          -> explicit human review decisions
          -> existing skill FCPXML compiler
          -> original-sound straight-cut MP4 / edit package / receipt
```

The skill is the workflow/CLI layer. `studio/` is a separate product adapter. Project state, footage, credentials and runtime exports live outside the repository. The original 34-file skill manifest stays scoped to that package; it does not claim to checksum product additions.

## Why not claim production-ready now?

The HTTP server is intentionally single-user loopback only. It does not have SaaS identity, organization/tenant boundaries, isolated media processing, billing, public sharing, object storage, cloud retries, model budgets, abuse controls, backup restore verification or per-project deletion. The successful local rough cut is one vertical slice, not completion of these systems.

## Recommended next architecture (decision proposal, not deployed)

- Creator web app for project intake, proof-backed selects, plans and timecoded revisions.
- Authenticated API with project ownership enforced on every database/object-store operation. Workspace IDs must be assigned from the authenticated session, never trusted from client input.
- Private object storage with short-lived scoped upload/download URLs; multipart/resumable transfers, checksums, upload expiry, storage quota and predictable retention. Default original retention is a product choice to confirm before accepting paying users.
- PostgreSQL for transactional project/version/job state; queue with leases, heartbeats, bounded retries and idempotency. Each render version snapshots source hashes, ranges, configuration, model and code versions.
- Sandboxed non-root media workers with read-only source mounts, no external network for decoding, CPU/memory/disk/time limits. Model workers get only project-authorized proxies/windows. Test media parsers with malformed/oversized fixtures.
- A Mac bridge is needed to relink local originals and validate native FCP import/export. Cloud-generated XML cannot reference inaccessible server paths and still promise portable one-click import. Deliver a relink manifest; acceptance includes a second-Mac relink test.
- ASR + time-aligned words + visual/audio window review. Cache by content hash and model version. Separate machine transcripts, human-corrected text and uncertain utterances. Never turn inferred dialogue into quoted on-location captions.
- Billing only after a trusted merchant account is explicitly connected: server-side prices, signed webhook verification, event idempotency, cost limits, entitlements and refund/failed-job policy. No fake checkout UI or client-side paid flag.

## Milestones with exit criteria

| Milestone | What ships | Exit condition |
| --- | --- | --- |
| A · local alpha (this change) | Real upload → reviewed select → XML/MP4 download | Synthetic integration and browser flows pass; limitations visible |
| B · assisted pilot | Founder-assisted five-stage editing with cost/time log | 5 consented projects; accepted deliverables; source evidence and actual FCP import checks |
| C · review intelligence | Proxy pairing, ASR/OCR, motion/audio scene windows, supported proposals | Labeled evaluation set; reported precision/omissions; no unreviewed-complete states; provider budget cap |
| D · private cloud beta | Login, per-user storage, resumable upload, isolated jobs, deletion, signed preview/download | Cross-tenant denial tests; full-download hashes; restore drill; interruption/retry tests; entitlement checks |
| E · paid self-serve | Clear offer, metered cost, payment lifecycle, support runbook | Verified checkout/webhooks and rollback; measured margins; native FCP compatibility matrix; support owner |

No dates are promises until model providers, deployment destination, operating budget and pilot capacity are selected. Do not hide manual review labor when measuring cost.

## Quality contracts

- Original files immutable; all outputs versioned; a failed job cannot create a downloadable success record.
- Proxy filename match ≠ duration match ≠ visual alignment ≠ source timecode verification.
- Static FCPXML validation ≠ native import ≠ renderer parity ≠ final audiovisual approval.
- Upload receipt ≠ decode success. HTTP 200 ≠ complete download. Site deployment ≠ private audience restriction.
- For uploaded duplicate basenames from multiple devices, use content IDs and an explicit relink manifest, not filenames alone.
- Preview must preserve aspect ratio, declared color handling and audible dialogue; mixing/ducking and native effects need independent parity tests.
- Persist per-stage review state, cost, failures and edits. Avoid logging private transcripts, media bytes, access tokens or signed URLs.

## Operations before onboarding external footage

Document customer consent, allowed processing providers, deletion/retention, support and cancellation boundaries; implement their corresponding behavior. Test backup restoration without sharing customer footage. Assign clear responsibilities even if founder is the only operator. These are pending product work, not claims that the alpha implements compliance.
