---
name: reels-creator
description: Create or revise a local vertical reel and cover from a user-selected photo and video folder using a reviewed JSON edit plan and the EUN.PANCHI Signature style.
---

# REELS CREATOR

Use [the local engine guide](references/local-engine.md) for execution, the plan schema, and personal style settings. For installation use [README.md](README.md).

- Resolve the input folder or existing `reel-project.json`. Read media from the user-designated location and write versions to an authorized output directory in the active project. Keep sources and previous versions intact.
- Run `reel_engine.py plan` for an editable plan or `auto` when the user wants a deterministic file-order render in one operation. For a creative plan, use the media list, the user's descriptions and timecodes, and any images or video frames actually inspected. Record the basis in `planningBasis`. File metadata does not establish scene content.
- For a new reel, set title, audience, story, cuts, captions and cover. Keep the hook in the first three seconds. For a stronger hook, update both `hook.text` and the opening caption cue. For caption placement, edit `style.y` on relevant cues. When changing cut or video length, recalculate subsequent frame starts, caption ends, and total duration.
- Prefer the user's cover photo, then a selected video frame, then the first usable photo or frame in the edit. Ask for suitable media if none is available. Leave `cover.text` empty to keep existing text in a source cover. Use `render --cover-only` for a cover-only revision.
- For a reusable personal style, prepare a JSON file based on `examples/personal-style.json`, register it with `save-style`, and set `personalStyle` in the plan. Keep the built-in Signature preset intact.
- Keep color selection in AUTO for new reels unless the user names a palette. Use `manual` for a reel-wide color request. For a single accent such as a burgundy hook, copy the chosen palette colors into that cue's style and keep the other cues consistent. For an AUTO accent, inspect representative media before recording `captionAccent` and `captionAccentReason`. To keep the colors on a revision, carry forward the previous render report's resolved background, text, and opacity as manual values and preserve existing cue overrides.
- If requested, show the plan and wait for approval before rendering. Run the plan validator before export and report the versioned paths for MP4 and PNG or the cover-only PNG.
- If “this folder” is ambiguous or contains no usable media, ask for the input folder path. Present the plan in plain language with the title, opening hook, cut times and captions, cover title, style, and total duration. Do not treat silence or a request to see the plan as permission to render. On a revision, keep the original plan and report both the new video and cover links. Explain failures by saying what stopped and what the user can fix or provide.
