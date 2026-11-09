# Claude Captions

A Claude Code skill that turns any video or audio into **accurate, well-timed captions**: SRT, VTT, word-by-word
timings, and a plain transcript. Made for reels, shorts and YouTube, including **Arabic mixed with English**.

Say **"caption this video"** and give the file. Claude checks your setup, transcribes, shows you the text to check,
then makes the caption files.

## Two engines

| | ElevenLabs (recommended) | Whisper (free fallback) |
| --- | --- | --- |
| Where | Online | On your computer |
| Speed | Seconds | Slower: the model downloads once, then roughly the length of the video on a laptop |
| Accuracy | Best, especially mixed languages | Good, with the skill's tuning (below) |
| Cost | ElevenLabs credits (the free plan has monthly credits) | Free |
| Setup | Account + API key | `python -m pip install faster-whisper` |

**No ElevenLabs key?** The skill tells you and uses Whisper. **ElevenLabs fails** (no credits, wrong key, no
internet)? It tells you why and uses Whisper.

### How the skill makes Whisper more accurate
- Cleans the audio first (removes low rumble, evens out loudness). Quiet audio makes Whisper invent words.
- Uses the language you set instead of guessing.
- Careful decoding: beam search, skips silence, doesn't carry mistakes from one piece to the next.
- **Your style example**: you give one sentence written exactly how captions should look, plus your common terms.
  Whisper copies that style. Tested on Egyptian Arabic: "البرومت" became "الـprompt" and "الويبسايت" became "لـwebsite".
- Lists the words it's unsure about, so you check those before publishing.
- Remembers your fixes (`spellings`), so the same mistake is fixed automatically next time.

## Readable captions
- Vertical reels: one short line (up to ~5 words). Landscape (`video` preset): up to 2 lines.
- Breaks at punctuation and pauses, never leaves one word alone on a line.
- Arabic: keeps `الـAI`-style words together and never starts a line with an English word (editors scramble it).
- No overlaps, no flashing captions: each stays on screen long enough to read.

## What you need
- **Claude Code** (needs a Claude Pro or Max plan): [install guide](https://code.claude.com/docs)
- **Python 3.9+** and **ffmpeg** (Windows: `winget install Gyan.FFmpeg`, Mac: `brew install ffmpeg`)
- One engine: an **ElevenLabs** API key (recommended) and/or **faster-whisper** (`python -m pip install faster-whisper`)

Tested on Windows. The scripts are plain Python and should also run on Mac and Linux.

## Install
1. Download [`claude-captions.zip`](https://github.com/YoussefFathy88/Youssef-Fathy-Skills/raw/main/downloads/claude-captions.zip).
2. Unzip it into your Claude Code skills folder, so you get `~/.claude/skills/claude-captions/SKILL.md`
   (Windows: `C:\Users\<you>\.claude\skills\claude-captions\SKILL.md`).
3. In Claude Code, say **"caption this video"** and give the file path.

**To use ElevenLabs:** create an account at [elevenlabs.io](https://elevenlabs.io), create an API key with
**Speech to Text** allowed, and paste it yourself into `~/.claude-captions/.env`:
```
ELEVENLABS_API_KEY=your-key-here
```
Never paste your key into the chat.

## Output
Next to your video, in a folder called `<video name> captions`:

| File | Use it for |
| --- | --- |
| `<name>.srt` | Importing captions into CapCut, Premiere, DaVinci, YouTube... |
| `<name>.vtt` | Web players |
| `<name>.words.json` | Word-by-word highlight styles (each word has its own timing) |
| `<name>.txt` | The plain transcript (descriptions, blog posts) |

Settings: `~/.claude-captions/config.json` (example: `config.example.json` in this folder).

## Related
- [CapCut Claude Montage](../capcut-claude-montage): puts word-by-word captions straight into your CapCut project.
- [Real Logos](../real-logos): official logos for the products you mention.

Made by [Youssef Fathy](https://github.com/YoussefFathy88). Free to use (MIT license). Not affiliated with ElevenLabs,
OpenAI or Anthropic.
