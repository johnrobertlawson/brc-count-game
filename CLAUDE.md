# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Browser-based Countdown party game (inspired by the British TV show). Host projects the game on screen; players compete on paper. Three round types: letters, numbers, and conundrum. Vaporwave neon aesthetic.

## Development

**Requirements:** Python 3.10+, jinja2

```bash
pip3 install jinja2
python3 server.py              # starts on http://localhost:8000
python3 server.py --port 9000  # custom port
```

No build step, no test suite, no linter. The only external dependency is jinja2.

## Architecture

**Three Python modules + two Jinja2 templates + one CSS file.**

- `server.py` — HTTP server using stdlib `http.server`. Handles all routing and API endpoints. Manages game state in a single global dict (in-memory, lost on restart). Renders templates with Jinja2.
- `game_engine.py` — Pure game logic: letter/number pool management, expression verification (safe AST-based evaluation, not `eval()`), scoring functions, anagram generation, and a recursive numbers solver.
- `word_list.py` — Loads `words/english.txt` (~360k words, filtered to 2-15 chars). Provides word validation, letter-availability checking, conundrum word selection, and post-round reveal finders (best word, rarest word by Scrabble score).
- `templates/setup.html` — Team/settings configuration page.
- `templates/host.html` — Main game display (projector view). All frontend logic is vanilla JavaScript within this template.
- `static/css/style.css` — All styling.
- `words/english.txt` — Dictionary file (~3.7 MB).

## API Pattern

All endpoints are in `server.py` within the `GameHandler` class. GET routes serve pages and state; POST routes under `/api/` mutate game state and return JSON. Request bodies are JSON; responses are JSON.

Key flow: `/api/setup` → `/api/start_round` → draw letters/numbers → `/api/submit_*` → `/api/next_round` (repeat). Conundrum has both instant-win (`/api/submit_conundrum`) and lives-based (`/api/buzz_conundrum`) modes.

## Game State

Single global `game_state` dict in `server.py` holds everything: teams, scores, settings, current round data, pool state (vowels, consonants, large/small numbers), and round history. The `/api/state` endpoint returns a sanitized copy (hides conundrum answer).

## Key Implementation Details

- **Expression parser** (`game_engine.py:verify_expression`): Uses Python's `ast` module to safely parse and evaluate arithmetic expressions. Validates operator whitelist, number availability via Counter, and exact division.
- **Numbers solver** (`game_engine.py:solve_numbers`): Recursive pair-combination brute force. Picks any two numbers, combines with +/-/*/÷, recurses on reduced pool. Early-exits on exact match.
- **Conundrum generation**: `generate_anagram()` fully shuffles; `generate_easy_anagram()` keeps 2-3 letters in place. Easy mode uses 8-letter common words; medium/hard use 9-letter words.
- **Scoring**: Letters = word length + bonus for longest. Numbers = distance-based (10/7/5/3/0 pts). Conundrum = 10 pts for winner.
- **Word override**: Host can manually accept words rejected by the dictionary via `/api/override_word`, which recalculates bonuses.
