# brc-count-game

A browser-based Countdown party game (inspired by the British TV show). Host projects the game screen; players compete on paper. Vaporwave neon aesthetic.

## Install

Requires Python 3.10+ and `jinja2`.

```bash
git clone https://github.com/johnrobertlawson/brc-count-game.git
cd brc-count-game
pip3 install jinja2
```

On Ubuntu, `jinja2` may already be installed as a system package (`python3-jinja2`).

## Quick start

```bash
python3 server.py
```

Open `http://localhost:8000` in a browser. Set up teams, pick a difficulty, and start playing.

Use `--port` to pick a different port if needed: `python3 server.py --port 9000`

For projector use: go fullscreen (F11) on the `/host` page.

## How it works

1. **Setup** — Enter team names, choose difficulty (Easy/Medium/Hard/Custom), pick preset or freestyle round mode
2. **Letters round** — Pick 9 vowels/consonants. Everyone writes the longest word they can. Timer runs down. Host enters words; auto-validated against dictionary.
3. **Numbers round** — Pick 6 numbers. Hit a random target using +, -, *, /. Host enters each team's arithmetic expression; auto-verified.
4. **Conundrum** — Unscramble a 9-letter anagram. First to buzz wins.
5. **Scoring** — Cumulative across rounds. Highest score wins.

## More detail

See [CHEAT-SHEET.md](CHEAT-SHEET.md) for scoring rules, difficulty settings, expression syntax, and other details.
