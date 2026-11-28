# Shareable telemetry and review scenarios

The event export retains numeric timing and usage, timestamps, constrained model and workflow labels, and pseudonymous turn relationships when those were present. It excludes transcripts, raw audio, free-text messages, map coordinates, contact details, credentials, and the local account database. Historical records include both hand testing and automated activity. Most records have no shared call or turn identifier.

The 28 November live conversation reviewed in chat covered 13 exchanges over roughly 175 seconds of observed activity. Browser playback start after transcript submission had a median of 828 ms, spanning 742 to 1,270 ms. That metric excluded endpoint waiting and recognition. The preceding day’s broader matching Sarvam sample had a median of 1,347 ms, and its last nine samples had a median of 861 ms. These comparisons do not estimate a build-level effect because historical events lack build IDs.

The live test also exposed an intake failure: after a road-waterlogging correction, the classifier still used a pipe-fault route, no ward was confirmed, and the dialogue implied progress beyond what the workflow had recorded. The branch added a correction case and tightened the draft flow afterward. The original dialogue stays local. The synthetic scenarios in this folder preserve the defects and desired checks without quoting the citizen transcript.

Regenerate an updated export with the same allowlist:

```powershell
.\.venv\Scripts\python.exe ops/export_cloud_telemetry.py --input logs/nammakural.jsonl --output research/civic/2026-11-28/telemetry/events.jsonl
```
