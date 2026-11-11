---
name: capcut-claude-montage
description: Adds word-by-word captions and the user's own images or videos INTO a copy of their CapCut desktop project (Windows), so they can still fix everything by hand and export from CapCut. Use when the user says "montage on CapCut", "edit my CapCut project", "add captions to my CapCut video", or names a CapCut project to caption.
---

# CapCut Claude Montage

You edit a **copy** of the user's CapCut desktop project by writing CapCut's own project files. Captions and media
appear in CapCut as normal clips. The user opens the copy, adjusts anything by hand, and clicks Export themselves.

Scripts are in this skill's `scripts/` folder. Run them with the full path, e.g. `python "<this skill folder>/scripts/preflight.py"`.
Settings, the optional API key, transcripts and backups live in `%USERPROFILE%\.capcut-claude-montage\`.

## Hard rules

- **Never write to the user's original project.** Only to `<project> Edit`, made by `projects.py copy`.
- **Never edit a project that is open in CapCut.** The scripts refuse; ask the user to close it.
- **Never ask for passwords or API keys in the chat.** CapCut sign-in happens inside CapCut. An ElevenLabs key goes into
  `%USERPROFILE%\.capcut-claude-montage\.env` by the user's own hand. Never read that file aloud or print the key.
- **Windows only.** On Mac, stop and say it isn't supported.
- **Only the user's own images and videos.** Don't download logos or media from the web in this skill.
- **One Edit copy per video.** If it exists, keep working on it: captions.py and add.py change it in place and keep
  the user's hand changes.
- Report what really happened. If a script refuses, explain why in plain words and what the user can do.

## Workflow

### 0. Preflight (every time)
Run `preflight.py` (`--quick` once config exists and the last full check passed). Then:
- **FIX** lines: tell the user each fix in simple steps, wait, run the check again. Don't continue until it says READY.
- **ASK "Signed in to CapCut"**: ask the user. When they confirm, run `preflight.py --confirm-signed-in`.
- **ASK "ElevenLabs: no key"**: captions always try **ElevenLabs first** (fastest, most accurate, keeps English words
  in English inside Arabic). Ask the user to add a key: elevenlabs.io > Developers > API keys, Speech to Text allowed,
  paste it themselves into `%USERPROFILE%\.capcut-claude-montage\.env` as `ELEVENLABS_API_KEY=...`. If they can't now,
  say Whisper will be used (free, less accurate, some words may need fixing). Only set `"engine": "whisper"` if they
  explicitly want Whisper every time.
- For Whisper accuracy, also ask once for ONE sentence written exactly how captions should look (with their English
  terms) and the names/terms they say often: save as `"styleExample"` and `"vocabulary"`.

### 1. Style (first time, or when the user wants a change)
Ask everything in ONE message, with the defaults shown, then write `%USERPROFILE%\.capcut-claude-montage\config.json`:
- Spoken language (or auto), caption colour, highlight colour for the spoken word, font (default Arial Bold, works for
  Arabic and English), caption height on screen (default y 1000 of 1920), max words per line.
- Optional: areas to never cover, as boxes in pixels (`"avoid": [[x0, y0, x1, y1]]`), e.g. where their face usually is.
- Optional: spellings to fix (`"spellings": {"superbase": "Supabase"}`).
Keep keys you don't change. Example config: `config.example.json` in this skill.

### 2. Pick the project
`projects.py list`, ask which one (newest first). Then `projects.py copy "<project>"`. Best with CapCut closed; if it's
running the copy still works, and if it doesn't show in CapCut's list, the user restarts CapCut.
If `<project> Edit` already exists, use it.

### 3. Captions
1. `audio.py "<project> Edit"`: the timeline's sound, from the original files. No export needed.
2. `transcribe.py "<project> Edit"`: ElevenLabs first. If it prints `ELEVENLABS NOT USED: <reason>` (NO KEY, NO
   CREDITS, BAD KEY, NO PERMISSION, BUSY, OFFLINE), tell the user the reason and the fix it printed, and that Whisper
   was used instead: free, less accurate, so some words may need fixing. Offer to rerun with ElevenLabs once fixed.
   Show the user the text and ask if any word is wrong; add fixes to `spellings` (and terms to `vocabulary`) and run
   it again if needed.
3. `captions.py "<project> Edit"`.

### 4. The user's images and videos (optional)
Ask if they want any. For each: the file path, when it shows (seconds), and where (top / middle / under the captions).
Write a `plan.json` in `%USERPROFILE%\.capcut-claude-montage\work\<project> Edit\` (format at the top of `add.py`),
then `add.py "<project> Edit" --plan <plan.json>`. If it refuses because something covers a B-roll or an avoid area,
offer another spot or time, or add `"allow": true` only after the user agrees.

### 5. Hand over
Tell the user: open **`<project> Edit`** in CapCut, check it, change anything by hand, and Export.
- More changes later: they close the project, you run the script again (captions are replaced, media is added).
- Undo the last change: `restore.py "<project> Edit"` (`--list` shows backups; hand changes made after that backup are lost).

## Known limits (say them when relevant)
- The CapCut project format is not official or documented. Tested on CapCut desktop 9.7 (Windows). An update can break
  it; the original project is always safe because the skill only edits the copy.
- You can't see CapCut's preview. The user's look in CapCut is the final check.
- Source files must stay where they were when imported into CapCut.
- CapCut's own animations and transitions aren't written by this skill; the user adds them in CapCut.
