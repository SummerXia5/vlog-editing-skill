# Local alpha validation

Validated on macOS with Python 3.12, PyAV 18.1.0, Pillow 10.3.0, NumPy 1.26.4 and FFmpeg 7.1. Synthetic media only; no customer or private trip media used for these tests.

## Automated integration — passed

Three integration scenarios exercise:

1. Session, Origin and Host enforcement; traversal/invalid upload type denial.
2. Upload and deduplication, LRV/original review assertions, bounds and cross-project rejection, missing audio/timecode checks, queued preview/export, original-only XML references, HTTP byte ranges, full MP4 download hash, database persistence and unchanged sources.
3. Malformed media produces a failed job, retry creates a distinct job, and no successful export is published.

Command: `STUDIO_FFMPEG=/path/to/ffmpeg python -m unittest discover -s studio/tests -v`.

## Browser — verified in Chrome

- Created a project through the interface.
- Uploaded a four-second silent synthetic test pattern through the file chooser.
- Requested an actual browser preview and played it.
- Saved a three-second reviewed test range and selected a story template.
- Generated a version through the interface; download links appeared after successful processing.
- Clicked the MP4 download control. The resulting complete local download matched the export receipt's SHA-256 and measured three seconds.
- Inspected the library/review and story-plan layouts at desktop size.

## Not verified / not implemented

Native Final Cut Pro import/relink, production cloud hosting, cross-tenant security, payment flow, automatic AI review, real-world long-form quality, mobile responsive interaction, final sound/grade and advanced title/map parity remain outside this validation. The GitHub Actions workflow is supplied separately; local results do not imply its Linux run succeeded.
