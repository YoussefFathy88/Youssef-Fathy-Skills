# CapCut Claude Montage

A Claude Code skill that adds **word-by-word captions** and **your own images and videos** into your CapCut desktop
project, as normal CapCut clips. You open the result in CapCut, fix anything by hand, and export as usual.

> **Windows only.** Mac is not supported.

## How it works

CapCut saves every project as files on your computer. Claude Code reads your project, makes a copy called
`<project> Edit`, and writes the captions and media into that copy. **Your original project is never changed.**

1. You cut your video in CapCut and close it.
2. You tell Claude Code: **"montage on CapCut"**.
3. Claude checks your setup, asks about your caption style once, and lets you pick a project.
4. It transcribes your voice straight from the project (no audio export), and adds the captions, with the spoken
   word highlighted.
5. Optional: it places your images or videos at the moments you choose.
6. You open `<project> Edit` in CapCut, adjust, and export.

## What you need

| | |
| --- | --- |
| **Windows** | 10 or 11 |
| **CapCut desktop** | From [capcut.com](https://www.capcut.com). Signing in inside CapCut is recommended (needed for Pro effects). |
| **Claude Code** | Needs a Claude Pro or Max plan. [Install guide](https://code.claude.com/docs) |
| **Python 3.9+** | [python.org](https://www.python.org/downloads/windows/), with Pillow: `python -m pip install pillow` |
| **ffmpeg** | `winget install Gyan.FFmpeg`, then open a new terminal |
| **Transcription** | **Whisper** (free, default): `python -m pip install faster-whisper`. Or **ElevenLabs** (optional, see below) |

You don't have to check all of this yourself: the skill runs a setup check first and tells you exactly what to fix.

## Install

1. Download [`capcut-claude-montage.zip`](https://github.com/YoussefFathy88/Youssef-Fathy-Skills/raw/main/downloads/capcut-claude-montage.zip).
2. Unzip it into your Claude Code skills folder, so you get:
   ```
   C:\Users\<you>\.claude\skills\capcut-claude-montage\SKILL.md
   ```
3. Open Claude Code in any folder and say **"montage on CapCut"**.

## Whisper or ElevenLabs?

The first time, the skill asks which one you want.

| | Whisper | ElevenLabs |
| --- | --- | --- |
| Cost | Free | Uses ElevenLabs credits (the free plan has monthly credits) |
| Where it runs | On your PC | Online |
| Speed | First run: several minutes (one-time model download). After that, in testing, about as long as the video itself on a laptop CPU | Seconds |
| Accuracy | Good for one language. In Arabic videos it makes more mistakes and sometimes writes English words in Arabic letters (e.g. "CV" became "السيفي") | Better, and keeps English words in English inside Arabic captions |
| Setup | Model downloads once (about 1.5 GB for the default "medium") | Account + API key |

**Speaking Arabic with English tech words?** ElevenLabs is strongly recommended.

**To use ElevenLabs:** create an account at [elevenlabs.io](https://elevenlabs.io), create an API key with
**Speech to Text** allowed, and paste it yourself into `C:\Users\<you>\.capcut-claude-montage\.env`:
```
ELEVENLABS_API_KEY=your-key-here
```
Never paste your key into the chat. If ElevenLabs fails (no credits, wrong key), the skill falls back to Whisper and
tells you why.

## Safety

- Works only on the `<project> Edit` copy. Your original project is never written to.
- Refuses to touch a project that is open in CapCut.
- Saves a backup before every change. Say "undo the last change" to go back.
- Never asks for your CapCut password or reads CapCut's account files.
- Only uses images and videos you give it.

## Limits

- **Unofficial.** CapCut doesn't document its project format. Tested on **CapCut desktop 9.7 for Windows**. A CapCut
  update can break it. Your original stays safe either way.
- Claude can't see CapCut's preview: your look in CapCut is the final check.
- Keep your video files where they were when you imported them into CapCut.
- CapCut's own animations and transitions aren't added; add them yourself in CapCut.
- Export is always done by you, in CapCut.

## Files

| File | What it does |
| --- | --- |
| `SKILL.md` | The steps Claude follows |
| `scripts/preflight.py` | Setup check (read-only) |
| `scripts/projects.py` | List projects, make the Edit copy |
| `scripts/audio.py` | The project's sound, for transcription only |
| `scripts/transcribe.py` | Whisper or ElevenLabs, word timings |
| `scripts/captions.py` | Captions into the copy |
| `scripts/add.py` | Your images and videos into the copy |
| `scripts/restore.py` | Undo |
| `templates/text-template.json` | The shape of one CapCut text clip |

Made by [Youssef Fathy](https://github.com/YoussefFathy88). Free to use (MIT license). Not affiliated with CapCut,
ByteDance, Anthropic or ElevenLabs.
