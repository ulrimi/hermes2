---
name: slop-factory
description: "Render narrated videos locally from a script.yaml: ComfyUI stills + F5-TTS narration + MusicGen bed + faster-whisper subs + ffmpeg compositing. Composer skill over the ComfyUI skill — orchestrates a sibling repo at ~/code/slop-factory."
version: 0.1.0
author: [ulrimi]
license: MIT
platforms: [macos]
compatibility: "Requires the slop-factory sibling repo at ~/code/slop-factory plus a working ComfyUI install (use the creative/comfyui skill to set that up)."
prerequisites:
  commands: ["python3", "ffmpeg"]
setup:
  help: "Clone or scaffold ~/code/slop-factory, then `python -m venv venv && pip install -r requirements.txt` inside it. ComfyUI, F5-TTS, MusicGen, faster-whisper install separately — see src/*.py module docstrings."
metadata:
  hermes:
    tags:
      - video-generation
      - narrated-video
      - tts
      - f5-tts
      - musicgen
      - ffmpeg
      - comfyui
      - creative
      - slop-factory
    related_skills: [comfyui, youtube-content, songwriting-and-ai-music]
    category: creative
---

# slop-factory

Author and render narrated videos from a single YAML scene script. Stays local (Apple Silicon friendly), composes over hermes2's existing ComfyUI skill for image generation.

**Backing implementation lives outside this skill:** sibling repo at `~/code/slop-factory/`. This skill is the interface; the sibling repo is the runtime.

## What's in this skill

**References (`references/`):**

- `script-schema.md` — full YAML schema with all fields and defaults

**Scripts (`scripts/`):**

- `render.sh` — thin wrapper: cd into sibling repo, activate venv, run `render.py`

## When to Use

- User asks to render a narrated video / slideshow / short
- User wants to iterate on a `script.yaml` they wrote
- User wants to generate a video script from a topic (draft yaml → render)
- User wants to re-render a single scene of an existing video
- "Make me a video about X" → produce script.yaml, then call render

## Architecture

```
hermes2 agent
  └── this skill (orchestration + script authoring)
        └── shells out to ~/code/slop-factory/render.py
              ├── ComfyUI (uses hermes2 creative/comfyui skill under the hood)
              ├── F5-TTS (local, MPS)
              ├── MusicGen (local, MPS)
              ├── faster-whisper (local)
              └── ffmpeg (system)
```

This skill does NOT reimplement the pipeline — it documents the contract and invokes the sibling repo. To extend rendering capability, edit modules in `~/code/slop-factory/src/`, not this skill.

## Typical flow

1. User describes desired video topic + style
2. Agent drafts `~/code/slop-factory/scripts/<slug>.yaml` per `references/script-schema.md`
3. Show draft to user, accept edits
4. Run `scripts/render.sh <slug>.yaml`
5. Report `outputs/<slug>/<slug>.mp4` path to user
6. On feedback, edit scene entries → re-render (use `--skip` to cache unchanged stages)

## Important behavior

- Always confirm script.yaml with the user before invoking the renderer. Rendering is slow (minutes to hours on M3 Max).
- Always pass `--skip` flags for stages whose inputs haven't changed when re-rendering.
- Re-rendering a single scene is exposed via `--scene <id>` but not yet implemented in render.py — note this to the user if requested.
- The sibling repo is independent of hermes2's mission (memory research). Treat it as auxiliary infra.

## Status

Sibling repo is scaffolded with `NotImplementedError` stubs. When a stage is requested before implementation, surface the contract from the relevant module's docstring rather than fabricating output.
