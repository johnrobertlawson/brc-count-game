"""Dictionary loader and word validator for Countdown."""

import random
from collections import Counter
from pathlib import Path


def load_dictionary(path: str = "words/english.txt") -> set[str]:
    words = set()
    filepath = Path(__file__).parent / path
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            w = line.strip().lower()
            if 2 <= len(w) <= 15 and w.isalpha():
                words.add(w)
    return words


def is_valid_word(word: str, dictionary: set[str]) -> bool:
    return word.strip().lower() in dictionary


def can_make_word(word: str, available_letters: list[str]) -> bool:
    available = Counter(ch.lower() for ch in available_letters)
    needed = Counter(word.strip().lower())
    for ch, count in needed.items():
        if available.get(ch, 0) < count:
            return False
    return True


def get_conundrum_words(dictionary: set[str], length: int = 9) -> list[str]:
    return [w for w in dictionary if len(w) == length]


# Letters that appear frequently in common English words
_COMMON_LETTERS = set('abcdefghilmnoprstuw')


def get_easy_conundrum_words(dictionary: set[str], length: int = 9) -> list[str]:
    """Filter for common, recognisable words: only common letters, no rare chars."""
    return [w for w in dictionary
            if len(w) == length and set(w) <= _COMMON_LETTERS]


# --- Reveal helpers ---

SCRABBLE_VALUES = {
    'a': 1, 'b': 3, 'c': 3, 'd': 2, 'e': 1, 'f': 4, 'g': 2, 'h': 4,
    'i': 1, 'j': 8, 'k': 5, 'l': 1, 'm': 3, 'n': 1, 'o': 1, 'p': 3,
    'q': 10, 'r': 1, 's': 1, 't': 1, 'u': 1, 'v': 4, 'w': 4, 'x': 8,
    'y': 4, 'z': 10,
}


def scrabble_score(word: str) -> int:
    return sum(SCRABBLE_VALUES.get(ch, 0) for ch in word.lower())


def find_best_words(available_letters: list[str], dictionary: set[str]) -> dict:
    """Find the longest valid word(s) makeable from available letters."""
    available = Counter(ch.lower() for ch in available_letters)
    max_len = len(available_letters)
    best_length = 0
    best_words = []

    for word in dictionary:
        wlen = len(word)
        if wlen > max_len or wlen < best_length:
            continue
        needed = Counter(word)
        if all(available.get(ch, 0) >= count for ch, count in needed.items()):
            if wlen > best_length:
                best_length = wlen
                best_words = [word]
            elif wlen == best_length:
                best_words.append(word)

    chosen = random.choice(best_words) if best_words else None
    return {
        'word': chosen,
        'length': best_length,
        'alternatives_count': len(best_words),
        'letters_used': list(chosen) if chosen else [],
    }


def find_rarest_word(available_letters: list[str], dictionary: set[str],
                     exclude_word: str | None = None) -> dict:
    """Find the valid word with the highest Scrabble letter score."""
    available = Counter(ch.lower() for ch in available_letters)
    max_len = len(available_letters)
    best_score = 0
    best_word = None

    for word in dictionary:
        wlen = len(word)
        if wlen < 3 or wlen > max_len:
            continue
        if word == exclude_word:
            continue
        needed = Counter(word)
        if all(available.get(ch, 0) >= count for ch, count in needed.items()):
            sc = scrabble_score(word)
            if sc > best_score:
                best_score = sc
                best_word = word

    return {
        'word': best_word,
        'scrabble_score': best_score,
        'letters_used': list(best_word) if best_word else [],
    }
