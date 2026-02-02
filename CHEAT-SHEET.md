# Cheat Sheet

## Scoring

### Letters round
- Every valid word scores its length in points (e.g., 5-letter word = 5 pts)
- Words must use only the 9 available letters (each at most once)
- Auto dictionary check can be toggled off in setup
- **Winner bonus**: The team(s) with the longest valid word get a bonus of `max(3, 3 * gap)`, where gap = winner length minus runner-up length. If everyone ties, all get 3.

### Numbers round
- Exact match to target: **10 pts**
- Within 5: **7 pts**
- Within 10: **5 pts**
- Within 20: **3 pts**
- Further than 20: **0 pts**

### Conundrum
- First team to solve: **10 pts**

## Expression syntax (Numbers round)

Host enters each team's arithmetic expression exactly as written on paper.

- Operators: `+`, `-`, `*`, `/`
- Parentheses: `(` and `)`
- Division must be exact (no remainders)
- Each drawn number used at most once
- Example: `(75 + 50) * 8 + 2`

The server verifies the expression is valid and computes the result.

## Difficulty macros

| Setting | Easy | Medium | Hard |
|---------|------|--------|------|
| Timer | 60s | 45s | 30s |
| Letters rounds | 4 | 5 | 6 |
| Numbers rounds | 1 | 2 | 2 |
| Conundrum rounds | 1 | 1 | 1 |

Custom mode: set each parameter individually.

## Round modes

- **Preset**: Rounds auto-sequence (letters and numbers interleaved, conundrum last)
- **Freestyle**: Host picks each round type manually. Click "End Game" when done.

## Letter distribution

Standard Countdown frequencies. Vowels: A(15), E(21), I(13), O(13), U(5). Consonants weighted similarly to the show.

## Number pools

- **Large**: 25, 50, 75, 100
- **Small**: 1-10 (each appears twice)
- Host picks how many large numbers (0-4); rest are small. Total always 6.

## Conundrum

A random 9-letter word scrambled into an anagram. Default length 9; adjustable in custom settings.

On **Easy** mode, conundrum words are filtered to common, recognisable words (no rare letters) and the scramble keeps a few letters in place. On **Hard**, any word and a fully random scramble.

## Tips for hosting

- Go fullscreen (F11) on the `/host` page for projector display
- The rules sidebar is always available — click "Rules" on the right edge
- For expression entry, the host can type `*` for multiply and `/` for divide
- If a word isn't in the dictionary but the group agrees it's valid, click the **Override** button next to it in the results. Or toggle auto-check off in setup.
- Sound effects (tick + buzzer) are off by default. Click the music note icon in the bottom-left to toggle.
- During numbers expression entry, a live distance readout shows how close each expression is to the target as you type.
