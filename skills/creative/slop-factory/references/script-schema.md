# script.yaml schema

Authoritative reference for the YAML format consumed by `~/code/slop-factory/render.py`. Mirrors the Pydantic models in `src/script.py`.

## Top-level

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `slug` | string | required | Used as output dir name and final mp4 filename stem. Use kebab-case. |
| `title` | string | required | Human-readable title. Not currently rendered into the video; used in metadata only. |
| `voice` | object | see voice section | TTS configuration. |
| `music` | object | see music section | Background music configuration. |
| `output` | object | see output section | Resolution, fps, subs. |
| `scenes` | list of scenes | required, non-empty | Rendered in array order. `id` is referenced by re-render flags. |

## voice

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `model` | string | `f5-tts` | Only `f5-tts` supported in v1. |
| `reference_audio` | string | null | Path (relative to slop-factory root) to a clean 5-15s voice sample for cloning. |
| `reference_text` | string | null | Transcript matching `reference_audio` — required when reference_audio is set. |
| `speed` | float | 1.0 | TTS playback rate. 0.8–1.2 sounds natural; outside that range degrades. |

## music

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `enabled` | bool | true | If false, render with narration only. |
| `bed_prompt` | string | "soft cinematic ambient bed, low energy" | MusicGen prompt for the background bed. |
| `volume_db` | float | -22.0 | Bed level relative to narration. -22 to -18 is typical for spoken-word content. |

## output

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `aspect` | enum | `"16:9"` | One of `16:9`, `9:16`, `1:1`. |
| `resolution` | `[int, int]` | `[1920, 1080]` | Width, height in px. Should match aspect. |
| `fps` | int | 30 | 24, 30, or 60 are sensible. |
| `subtitles` | bool | true | Burn faster-whisper SRT into the video. |

## scenes[]

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | int | required | Unique per script. Referenced by `--scene <id>` for single-scene re-render. |
| `duration` | float | required, > 0 | Seconds on screen. If narration is longer, narration wins (TODO: confirm during compositor impl). |
| `visual` | string | required | Positive prompt sent to ComfyUI image workflow. |
| `narration` | string | required | Text fed to F5-TTS. |
| `motion` | enum | `ken_burns` | `none` (static still), `ken_burns` (pan/zoom), `ltx` (LTX-Video img→vid, slow on MPS). |
| `music_cue` | string \| null | null | Reserved for v2 (per-scene stings). Ignored by v1. |

## Conventions

- Keep `narration` per scene to 1–3 sentences (~10s read time). Long scenes hurt pacing.
- `visual` prompts work best with explicit style anchors ("oil painting style", "cinematic photography") so the look stays consistent across scenes.
- Match `output.resolution` to `aspect`: 1920×1080 for 16:9, 1080×1920 for 9:16, 1080×1080 for 1:1.
- `slug` should be unique across scripts — outputs are namespaced by it.

## Example

See `~/code/slop-factory/scripts/example.yaml` for a working three-scene example.
