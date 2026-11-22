---
name: reels-creator
description: Create or revise a local vertical reel and cover from a user-selected photo and video folder using a reviewed JSON edit plan and the EUN.PANCHI Signature style.
---

# REELS CREATOR

Use [the local engine guide](references/local-engine.md) for execution, the plan schema, and personal style settings. For installation use [README.md](README.md).

- For user media, resolve a local `reels-workspace` outside the program and Git repositories, and pass `--workspace` to the engine. Read originals from `input`, keep plans and presets under `projects`, and export MP4 and PNG to `output`. Offer to initialize the workspace if it does not exist. Use the original files in place.
- Keep user media on the local machine. Do not attach it to the Codex conversation or send it through image tools, cloud APIs, Git, or other network destinations. Use local scan results and user-provided scene descriptions and timecodes. If a requested feature would require sending media or derived frames to an external service, explain the destination and data and obtain approval before sending.
- Run `reel_engine.py plan` for an editable plan or `auto` when the user wants a deterministic file-order render in one operation. For a creative plan, use the media list, the user's descriptions and timecodes, and any images or video frames inspected entirely on-device. Record the basis in `planningBasis`. File metadata does not establish scene content.
- For a new reel, set title, audience, story, cuts, captions and cover. Keep the hook in the first three seconds. For a stronger hook, update both `hook.text` and the opening caption cue. For caption placement, edit `style.y` on relevant cues. When changing cut or video length, recalculate subsequent frame starts, caption ends, and total duration.
- Prefer the user's cover photo, then a selected video frame, then the first usable photo or frame in the edit. Ask for suitable media if none is available. Leave `cover.text` empty to keep existing text in a source cover. Use `render --cover-only` for a cover-only revision.
- For a reusable personal style, prepare a JSON file based on `examples/personal-style.json`, register it with `save-style`, and set `personalStyle` in the plan. Keep the built-in Signature preset intact.
- Keep color selection in AUTO for new reels unless the user names a palette. Use `manual` for a reel-wide color request. For a single accent such as a burgundy hook, copy the chosen palette colors into that cue's style and keep the other cues consistent. For an AUTO accent, inspect representative media before recording `captionAccent` and `captionAccentReason`. To keep the colors on a revision, carry forward the previous render report's resolved background, text, and opacity as manual values and preserve existing cue overrides.
- If requested, show the plan and wait for approval before rendering. Run the plan validator before export and report the versioned paths for MP4 and PNG or the cover-only PNG.
- If “this folder” is ambiguous or contains no usable media, ask for the input folder path. Present the plan in plain language with the title, opening hook, cut times and captions, cover title, style, and total duration. Do not treat silence or a request to see the plan as permission to render. On a revision, keep the original plan and report both the new video and cover links. Explain failures by saying what stopped and what the user can fix or provide.
