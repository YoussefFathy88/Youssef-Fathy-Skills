---
name: claude-captions
description: Makes accurate, well-timed captions (SRT, VTT, word-by-word JSON, transcript) from any video or audio file, for reels, shorts and YouTube, including Arabic mixed with English. Uses ElevenLabs when the user has a key (recommended) and free Whisper on their computer otherwise, tuned for accuracy. Use when the user asks for captions, subtitles, a transcript, an SRT, or "caption this video".
---

# Claude Captions

Turns speech into captions people can read. Accuracy first: a wrong word on screen costs more trust than a missing one.

Scripts are in this skill's `scripts/` folder; run them with the full path. Settings and the optional key live in
`~/.claude-captions/` (`config.json`, `.env`). Results go in a `<video name> captions` folder next to the video.

## Hard rules

- **Never ask for API keys in the chat, never print or read the key aloud.** The user pastes it into
  `~/.claude-captions/.env` themselves (`ELEVENLABS_API_KEY=...`).
- **Recommend ElevenLabs, never force it.** If there's no key or it fails, say so in one line and use Whisper.
- **Always show the transcript before making files**, and list the low-confidence words. The user knows what they said.
- Never invent words to fill a gap. If audio is unclear, mark it for the user.
- Report honestly which engine was used and any fallback (the scripts print it).

## Workflow

### 0. Setup check
Run `preflight.py`. Handle every line:
- **FIX**: give the user the exact fix, wait, run it again.
- **ASK "Engine"** (first run, no key): one short message:
  > ElevenLabs is recommended: captions in seconds, more accurate, and English words stay in English inside Arabic. It
  > needs a free ElevenLabs account and an API key (the free plan has monthly credits). Or start now with free Whisper
  > on your computer: slower, a bit less accurate.
  If they choose ElevenLabs: elevenlabs.io > Developers > API keys > create a key with **Speech to Text** allowed >
  paste it yourself into `~/.claude-captions/.env`. Save the choice as `"engine"` in config (`"auto"` is fine).
- **ASK "Whisper accuracy"**: ask for (1) the spoken language, (2) ONE sentence written exactly how they want captions
  to look, with their real English terms (e.g. `خد الـprompt ده وابعته لـChatGPT`), (3) names and terms they say often.
  Save as `"language"`, `"styleExample"`, `"vocabulary"`. This is the biggest Whisper accuracy win.

### 1. Transcribe: ElevenLabs first, Whisper as the fallback
`transcribe.py "<file>"`. It always tries ElevenLabs first (unless the user set `"engine": "whisper"` on purpose).
If ElevenLabs can't be used, it prints a box `ELEVENLABS NOT USED: <reason>` and runs Whisper by itself. **Tell the
user the reason and the fix in plain words, then that Whisper was used and may need fixes:**

| Reason | Tell the user |
| --- | --- |
| NO KEY | Add an ElevenLabs API key for the best captions: elevenlabs.io > Developers > API keys, Speech to Text allowed, paste it yourself into `~/.claude-captions/.env` as `ELEVENLABS_API_KEY=...` |
| NO CREDITS | The ElevenLabs account is out of credits: add credits / upgrade, or wait for the monthly renewal |
| BAD KEY | The key was rejected: check it was pasted completely, or create a new one |
| NO PERMISSION | The key isn't allowed to use Speech to Text: turn it on for the key |
| BUSY / OFFLINE | Rate limit or no connection: try again in a minute |

Always add: *"So I used Whisper on your computer (free, most accurate settings). It's less accurate than ElevenLabs,
so some words may need fixing: please check the transcript."* Once the problem is fixed, offer to run it again with
ElevenLabs. `words.json` also records it (`elevenlabsProblem`, `note`).

The script prints the engine, the text and the low-confidence words.
- Show the user the text in short lines and the words to check. Ask what's wrong.
- Fix wrong words directly in `<name> captions/words.json` (keep the timings). A word they say often and Whisper keeps
  getting wrong goes into `"spellings"` (and `"vocabulary"`) in config, so it's fixed next time too.

### 2. Build the files
`build.py "<file>"` (`--preset video` for landscape / YouTube, 2 lines). Tell the user where the files are and which to
use: `.srt` for editors and platforms, `.words.json` for word-by-word highlight styles, `.txt` for the description.

## Best practices this skill follows (keep them when changing anything)

**Getting the words right**
1. ElevenLabs first when available (scribe_v2, word timings). It handles mixed languages best.
2. Clean audio before any engine: 16 kHz mono, low rumble cut (80 Hz), loudness evened out. Quiet audio makes Whisper
   invent text.
3. Set the language instead of auto-detect when known (mixed Egyptian Arabic + English is often misdetected).
4. Whisper settings: beam search 5, silence skipped (VAD), no carry-over between pieces (stops repeated or invented
   lines), repetition penalty 1.2 + no repeated 3-word runs (stops loops like "اي اي اي اي"), word timestamps on.
5b. The vocabulary must include THIS video's names and terms (tested: adding "application, Lovable, Replit" turned
   "أبليكيشن, لفابل, ربلت" into English). When review finds a term written in Arabic letters, add it and run again.
5. Whisper prompt = a style example + vocabulary. Whisper copies how that sentence is written, so English terms stay in
   English letters and spelling follows the user's style. Tested on Egyptian Arabic: "البرومت" -> "الـprompt",
   "الويبسايت" -> "لـwebsite".
6. `large-v3-turbo` is the default: the best balance in testing on Egyptian Arabic (it sometimes turns casual words
   formal, e.g. "عشان" -> "لكي": check for that in review). `large-v3` got slightly fewer words wrong on a 37 s reel but
   was 2.4x slower (71 s vs ~29 s), a 3 GB download, and put foreign letters inside Arabic words ("هنšوف", "الفيڈيو"):
   only for users who accept that. `medium` for slow computers.
7. Fix recurring mistakes with `spellings`, never by hand every time.
8. Human review of low-confidence words before publishing.

**Making them readable**
9. Vertical reels: one short line, at most ~5 words / 24 characters. Landscape: up to 2 lines of ~42 characters.
10. Break at punctuation and natural pauses, never in the middle of a name; never one word alone on a line.
11. Keep an Arabic prefix with its English word as one unit (`الـAI`, `للـHR`), and never start an Arabic line with an
    English word (editors flip the line left to right).
12. Each caption stays at least ~0.7 s when there's room, ends ~0.3 s after the last word, and never overlaps the next.
13. On vertical videos keep captions in the platform safe zone (not the bottom ~25%, where buttons and the description
    sit). The skill doesn't place them; say this when the user imports the SRT.
