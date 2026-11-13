# Vlog Editing Studio · local alpha

A runnable single-user product slice built on the five-stage skill. Target customer: travel vloggers and individual creators who want an editable rough cut from their own footage.

**This is a local alpha, not a production SaaS or an autonomous AI editor.** It has working upload, playback preparation, reviewed selects, three explicit ordering templates, queued rough-cut generation, original-media FCPXML/CSV, and downloadable MP4/package delivery. No fake progress, billing, generated dialogue, or cloud sharing.

## Start

Use Python 3.12 and an installed FFmpeg with libx264/AAC support. From repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r vlog-editing/requirements.txt
.venv/bin/python studio/server.py --data "$HOME/.vlog-studio" --port 4318
```

If FFmpeg is not on PATH, append `--ffmpeg /absolute/path/to/ffmpeg`.
Open **http://127.0.0.1:4318** on the same machine. Use this exact host; `localhost`, network exposure, reverse-proxy hosting, and remote multi-user deployment are intentionally not supported by this alpha.

1. Create a project and save the creative brief.
2. Upload LRV and/or MP4/MOV/M4V files. Upload stores a new local copy and reads headers; it does not automatically decode all original footage. Limits: 2 GiB/file, 20 GiB total local storage. Interrupted transfers can be retried; chunk resumption is not implemented.
3. Open a clip. After SDR confirmation, request its browser-compatible preview. Play the relevant motion and sound. The preview preserves aspect ratio.
4. Mark IN/OUT, category, chapter and notes. For an LRV, choose its original, compare front/back content, and attest to synchronization. The server also checks duration within 100 ms. Filename guesses are only suggestions. For timecoded originals enter verified rational start seconds; explicitly enter `0` only when appropriate.
5. Choose a plan and frame shape. The plans are **tag-based ordering templates**, not AI-generated stories. They use the exact selected ranges, preserving all selected dialogue. Current sequence frame rate is 30 fps; bounds snap to this grid.
6. Generate. The backend snapshots selects, verifies source hashes, reuses `build_fcpxml.py`, renders a separate straight-cut preview with source sound, and verifies its full decode, duration and hash. Download the MP4 or edit package.

The FCPXML references uploaded originals on this machine. On another Mac, relink the original files by name. The ZIP includes compile JSON, FCPXML, CSV, build report and receipt, but no original footage. The MP4 is a simple review render, **not** a verified Final Cut Pro render. XML native import, visual/audio approval, grading, sound design, titles/maps, and final mastering are not completed by this app.

## Scope and release boundaries

- All API records/files are gated by a local HttpOnly session cookie; mutations require the exact loopback Origin and a custom header. Host checks mitigate DNS rebinding. No external scripts/fonts, permissive CORS, or arbitrary file serving.
- This is a single-user trust boundary. It is **not** account authentication or tenant isolation. Do not expose the server publicly. Media parsing is not sandboxed. Security hardening does not make the stdlib HTTP server suitable for a hosted service.
- SQLite persists projects, uploaded asset hashes, review assertions, selects, jobs and exports. A single background worker limits simultaneous render load. Queued jobs recover after restart; interrupted running jobs become failed and can be explicitly retried into a new version. There is a 15-minute per-command timeout, but no subprocess memory/container limit.
- User review assertions are stored; the application cannot verify that a user actually watched/listened. No ASR, OCR, semantic search, face detection or AI scene scoring is connected.
- Tagged PQ/HLG is rejected. Unspecified color still needs human SDR confirmation. Automatic HDR tonemapping is not implemented. No implicit relabeling of HDR as SDR.
- No billing, accounts, public share links, analytics provider or remote AI calls. The creative brief is stored but not interpreted automatically. No user footage goes into source control.
- Storage quota is a coarse local-alpha limit, not a cloud quota system. Failed outputs/invalid uploads may take disk space. Stop the app and back up the data directory before manual cleanup; a safe per-project deletion/retention UI is a hosted-beta requirement.

## Tests

```sh
STUDIO_FFMPEG=/path/to/ffmpeg .venv/bin/python -m unittest discover -s studio/tests -v
```

Tests create synthetic audiovisual MP4/LRV fixtures and exercise the real HTTP endpoints, authentication/origin/Host checks, traversal/file-type denial, upload deduplication, proxy review gates, source bounds, cross-project validation, queued render/export, original-only XML, HTTP Range, MP4 download hash, persistent state, failed-job retry and unchanged input files.

See [product strategy](../docs/PRODUCT.md), [production roadmap](../docs/PRODUCTION.md), and [pilot operations](../docs/PILOT.md). The reusable skill remains separate in `vlog-editing/`.
