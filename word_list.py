"""Dictionary loader and word validator for Countdown."""

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
