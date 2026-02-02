"""Countdown game engine: letter/number pools, scoring, expression parsing."""

import ast
import operator
import random
from collections import Counter

# --- Letter pools (standard Countdown distribution) ---

VOWEL_DIST = {'a': 15, 'e': 21, 'i': 13, 'o': 13, 'u': 5}
CONSONANT_DIST = {
    'b': 2, 'c': 3, 'd': 6, 'f': 2, 'g': 3, 'h': 2, 'j': 1, 'k': 1,
    'l': 5, 'm': 4, 'n': 8, 'p': 4, 'q': 1, 'r': 9, 's': 9, 't': 9,
    'v': 1, 'w': 1, 'x': 1, 'y': 1, 'z': 1,
}


def create_vowel_pool() -> list[str]:
    return [ch for ch, n in VOWEL_DIST.items() for _ in range(n)]


def create_consonant_pool() -> list[str]:
    return [ch for ch, n in CONSONANT_DIST.items() for _ in range(n)]


def draw_letter(pool: list[str]) -> tuple[str, list[str]]:
    idx = random.randrange(len(pool))
    letter = pool[idx]
    pool = pool[:idx] + pool[idx + 1:]
    return letter, pool


# --- Number pools ---

LARGE_NUMBERS = [25, 50, 75, 100]
SMALL_NUMBERS = [i for i in range(1, 11) for _ in range(2)]


def create_number_pools() -> tuple[list[int], list[int]]:
    return list(LARGE_NUMBERS), list(SMALL_NUMBERS)


def draw_numbers(large_count: int, large_pool: list[int],
                 small_pool: list[int]) -> tuple[list[int], list[int], list[int]]:
    large_count = max(0, min(4, large_count))
    small_count = 6 - large_count
    lp = list(large_pool)
    sp = list(small_pool)
    random.shuffle(lp)
    random.shuffle(sp)
    selected = lp[:large_count] + sp[:small_count]
    return selected, lp[large_count:], sp[small_count:]


def generate_target() -> int:
    return random.randint(100, 999)


# --- Safe expression parser ---

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.floordiv,
}


def _eval_node(node: ast.AST) -> int:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPS:
            raise ValueError(f"Operator not allowed: {ast.dump(node.op)}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if op_type is ast.Div:
            if right == 0:
                raise ValueError("Division by zero")
            if left % right != 0:
                raise ValueError(f"{left} / {right} is not an integer")
        return _OPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError(f"Invalid expression element: {ast.dump(node)}")


def _extract_numbers(node: ast.AST) -> list[int]:
    nums: list[int] = []
    if isinstance(node, ast.Expression):
        return _extract_numbers(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return [node.value]
    if isinstance(node, ast.BinOp):
        return _extract_numbers(node.left) + _extract_numbers(node.right)
    if isinstance(node, ast.UnaryOp):
        return _extract_numbers(node.operand)
    return nums


def verify_expression(expr_str: str, available: list[int]) -> dict:
    expr_str = expr_str.replace('×', '*').replace('÷', '/').strip()
    try:
        tree = ast.parse(expr_str, mode='eval')
    except SyntaxError as e:
        return {'valid': False, 'result': None, 'error': f"Syntax error: {e}"}

    try:
        used = _extract_numbers(tree)
    except ValueError as e:
        return {'valid': False, 'result': None, 'error': str(e)}

    avail_counter = Counter(available)
    used_counter = Counter(used)
    for num, count in used_counter.items():
        if avail_counter.get(num, 0) < count:
            return {
                'valid': False, 'result': None,
                'error': f"Number {num} used {count} time(s) but only {avail_counter.get(num, 0)} available"
            }

    try:
        result = _eval_node(tree)
    except ValueError as e:
        return {'valid': False, 'result': None, 'error': str(e)}

    return {'valid': True, 'result': int(result), 'error': None}


# --- Scoring ---

def score_letters_round(submissions: dict[str, str],
                        valid_words: set[str] | None = None) -> dict:
    results = {}
    for team, word in submissions.items():
        word_lower = word.strip().lower()
        is_valid = True if valid_words is None else (word_lower in valid_words)
        base = len(word_lower) if is_valid else 0
        results[team] = {
            'word': word_lower, 'valid': is_valid,
            'base_score': base, 'bonus': 0, 'total': 0,
        }

    scores = [(t, r['base_score']) for t, r in results.items()]
    if not scores:
        return results

    scores.sort(key=lambda x: -x[1])
    top = scores[0][1]
    if top == 0:
        for r in results.values():
            r['total'] = 0
        return results

    runner_up = 0
    for _, s in scores:
        if s < top:
            runner_up = s
            break

    gap = top - runner_up
    bonus = max(3, 3 * gap)

    for team, r in results.items():
        if r['base_score'] == top:
            r['bonus'] = bonus
        r['total'] = r['base_score'] + r['bonus']

    return results


def score_numbers_round(submissions: dict[str, int], target: int) -> dict:
    results = {}
    for team, result in submissions.items():
        diff = abs(result - target)
        if diff == 0:
            pts = 10
        elif diff <= 5:
            pts = 7
        elif diff <= 10:
            pts = 5
        elif diff <= 20:
            pts = 3
        else:
            pts = 0
        results[team] = {'result': result, 'diff': diff, 'score': pts}
    return results


def score_conundrum(winning_team: str | None, teams: list[str]) -> dict:
    return {t: (10 if t == winning_team else 0) for t in teams}


# --- Conundrum helpers ---

def generate_anagram(word: str) -> str:
    letters = list(word)
    for _ in range(100):
        random.shuffle(letters)
        anagram = ''.join(letters)
        if anagram != word:
            return anagram
    return ''.join(reversed(letters))


def generate_easy_anagram(word: str) -> str:
    """Kinder scramble: keeps 2-3 letters in their original position."""
    letters = list(word)
    n = len(letters)
    keep = random.sample(range(n), min(3, n))
    movable = [i for i in range(n) if i not in keep]
    movable_chars = [letters[i] for i in movable]
    for _ in range(100):
        random.shuffle(movable_chars)
        candidate = list(letters)
        for idx, ch in zip(movable, movable_chars):
            candidate[idx] = ch
        result = ''.join(candidate)
        if result != word:
            return result
    return generate_anagram(word)
