#!/usr/bin/env python3
"""Countdown party game server using stdlib http.server + jinja2."""

import json
import os
import random
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from jinja2 import Environment, FileSystemLoader

from game_engine import (
    create_consonant_pool, create_vowel_pool, draw_letter, draw_numbers,
    create_number_pools, generate_target, verify_expression,
    score_letters_round, score_numbers_round, score_conundrum,
    generate_anagram,
)
from word_list import load_dictionary, is_valid_word, can_make_word, get_conundrum_words

BASE = Path(__file__).parent
TEMPLATES = BASE / 'templates'
STATIC = BASE / 'static'

env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
dictionary: set[str] = set()
conundrum_words: list[str] = []

# --- Game state (single-server, in-memory) ---
game_state: dict = {}


def reset_game(teams: list[str], settings: dict) -> dict:
    global game_state
    vowel_pool = create_vowel_pool()
    consonant_pool = create_consonant_pool()
    large_pool, small_pool = create_number_pools()
    game_state = {
        'teams': teams,
        'scores': {t: 0 for t in teams},
        'settings': settings,
        'round_sequence': settings.get('round_sequence', []),
        'current_round_index': 0,
        'current_round': None,
        'vowel_pool': vowel_pool,
        'consonant_pool': consonant_pool,
        'large_pool': large_pool,
        'small_pool': small_pool,
        'round_history': [],
    }
    return game_state


def init_dictionary():
    global dictionary, conundrum_words
    print("Loading dictionary...")
    dictionary = load_dictionary()
    conundrum_words = get_conundrum_words(dictionary, 9)
    print(f"Loaded {len(dictionary)} words, {len(conundrum_words)} conundrum candidates")


class GameHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '' or path == '/':
            self._serve_template('setup.html', {})
        elif path == '/host':
            self._serve_template('host.html', {'state': game_state})
        elif path.startswith('/static/'):
            self._serve_static(path[8:])
        elif path == '/api/state':
            safe = {k: v for k, v in game_state.items()
                    if k not in ('vowel_pool', 'consonant_pool', 'large_pool', 'small_pool')}
            # Strip conundrum answer from current round
            if safe.get('current_round') and safe['current_round'].get('word'):
                r = dict(safe['current_round'])
                r.pop('word', None)
                safe['current_round'] = r
            self._json_response(safe)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        body = self._read_body()

        if path == '/api/setup':
            self._handle_setup(body)
        elif path == '/api/start_round':
            self._handle_start_round(body)
        elif path == '/api/draw_letter':
            self._handle_draw_letter(body)
        elif path == '/api/draw_numbers':
            self._handle_draw_numbers(body)
        elif path == '/api/submit_letters':
            self._handle_submit_letters(body)
        elif path == '/api/submit_numbers':
            self._handle_submit_numbers(body)
        elif path == '/api/submit_conundrum':
            self._handle_submit_conundrum(body)
        elif path == '/api/validate_word':
            self._handle_validate_word(body)
        elif path == '/api/next_round':
            self._handle_next_round(body)
        else:
            self.send_error(404)

    # --- API handlers ---

    def _handle_setup(self, body: dict):
        teams = body.get('teams', [])
        settings = body.get('settings', {})
        if not teams:
            self._json_response({'error': 'No teams provided'}, 400)
            return
        state = reset_game(teams, settings)
        self._json_response({'ok': True, 'state': state})

    def _handle_start_round(self, body: dict):
        rtype = body.get('type', 'letters')
        if rtype == 'letters':
            game_state['current_round'] = {
                'type': 'letters', 'letters': [], 'phase': 'picking',
            }
        elif rtype == 'numbers':
            game_state['current_round'] = {
                'type': 'numbers', 'numbers': [], 'target': None,
                'large_count': 0, 'phase': 'picking',
            }
        elif rtype == 'conundrum':
            length = game_state['settings'].get('conundrum_length', 9)
            candidates = get_conundrum_words(dictionary, length)
            if not candidates:
                candidates = conundrum_words
            word = random.choice(candidates)
            anagram = generate_anagram(word)
            game_state['current_round'] = {
                'type': 'conundrum', 'word': word, 'anagram': anagram,
                'phase': 'playing', 'solved_by': None,
            }
        self._json_response({'ok': True, 'round': game_state['current_round']})

    def _handle_draw_letter(self, body: dict):
        kind = body.get('kind', 'consonant')
        rnd = game_state.get('current_round')
        if not rnd or rnd['type'] != 'letters':
            self._json_response({'error': 'No letters round active'}, 400)
            return
        if len(rnd['letters']) >= 9:
            self._json_response({'error': 'Already have 9 letters'}, 400)
            return
        if kind == 'vowel':
            letter, game_state['vowel_pool'] = draw_letter(game_state['vowel_pool'])
        else:
            letter, game_state['consonant_pool'] = draw_letter(game_state['consonant_pool'])
        rnd['letters'].append(letter)
        if len(rnd['letters']) == 9:
            rnd['phase'] = 'playing'
        self._json_response({'letter': letter, 'letters': rnd['letters'], 'phase': rnd['phase']})

    def _handle_draw_numbers(self, body: dict):
        large_count = body.get('large_count', 1)
        rnd = game_state.get('current_round')
        if not rnd or rnd['type'] != 'numbers':
            self._json_response({'error': 'No numbers round active'}, 400)
            return
        selected, game_state['large_pool'], game_state['small_pool'] = draw_numbers(
            large_count, game_state['large_pool'], game_state['small_pool']
        )
        target = generate_target()
        rnd['numbers'] = selected
        rnd['target'] = target
        rnd['large_count'] = large_count
        rnd['phase'] = 'playing'
        self._json_response({'numbers': selected, 'target': target})

    def _handle_submit_letters(self, body: dict):
        submissions = body.get('submissions', {})
        rnd = game_state.get('current_round')
        if not rnd or rnd['type'] != 'letters':
            self._json_response({'error': 'No letters round active'}, 400)
            return

        auto_check = game_state['settings'].get('auto_dictionary', True)
        available = rnd['letters']

        valid_submissions = {}
        for team, word in submissions.items():
            word_lower = word.strip().lower()
            if not word_lower:
                valid_submissions[team] = ''
                continue
            makeable = can_make_word(word_lower, available)
            if not makeable:
                valid_submissions[team] = ''
            else:
                valid_submissions[team] = word_lower

        if auto_check:
            valid_words = {w for w in valid_submissions.values() if w and is_valid_word(w, dictionary)}
        else:
            valid_words = None

        results = score_letters_round(valid_submissions, valid_words)

        # Mark unmakeable words
        for team, word in submissions.items():
            word_lower = word.strip().lower()
            if valid_submissions.get(team) == '' and word_lower:
                results.setdefault(team, {
                    'word': word_lower, 'valid': False,
                    'base_score': 0, 'bonus': 0, 'total': 0,
                })
                results[team]['error'] = 'Cannot be made from available letters'

        for team, r in results.items():
            game_state['scores'][team] = game_state['scores'].get(team, 0) + r['total']

        rnd['results'] = results
        rnd['phase'] = 'scored'
        game_state['round_history'].append(dict(rnd))
        self._json_response({'results': results, 'scores': game_state['scores']})

    def _handle_submit_numbers(self, body: dict):
        submissions = body.get('submissions', {})
        rnd = game_state.get('current_round')
        if not rnd or rnd['type'] != 'numbers':
            self._json_response({'error': 'No numbers round active'}, 400)
            return

        target = rnd['target']
        available = rnd['numbers']
        results = {}

        for team, expr_str in submissions.items():
            expr_str = expr_str.strip()
            if not expr_str:
                results[team] = {'expression': '', 'result': None, 'diff': None, 'score': 0, 'error': 'No answer'}
                continue
            verification = verify_expression(expr_str, available)
            if verification['valid']:
                diff = abs(verification['result'] - target)
                if diff == 0:
                    pts = 10
                elif diff <= 5:
                    pts = 7
                elif diff <= 10:
                    pts = 5
                else:
                    pts = 0
                results[team] = {
                    'expression': expr_str, 'result': verification['result'],
                    'diff': diff, 'score': pts, 'error': None,
                }
            else:
                results[team] = {
                    'expression': expr_str, 'result': None,
                    'diff': None, 'score': 0, 'error': verification['error'],
                }

        for team, r in results.items():
            game_state['scores'][team] = game_state['scores'].get(team, 0) + r['score']

        rnd['results'] = results
        rnd['phase'] = 'scored'
        game_state['round_history'].append(dict(rnd))
        self._json_response({'results': results, 'scores': game_state['scores']})

    def _handle_submit_conundrum(self, body: dict):
        winning_team = body.get('team')
        rnd = game_state.get('current_round')
        if not rnd or rnd['type'] != 'conundrum':
            self._json_response({'error': 'No conundrum round active'}, 400)
            return

        rnd['solved_by'] = winning_team
        results = score_conundrum(winning_team, game_state['teams'])

        for team, pts in results.items():
            game_state['scores'][team] = game_state['scores'].get(team, 0) + pts

        rnd['results'] = results
        rnd['phase'] = 'scored'
        game_state['round_history'].append(dict(rnd))
        self._json_response({
            'results': results, 'scores': game_state['scores'],
            'answer': rnd['word'],
        })

    def _handle_validate_word(self, body: dict):
        word = body.get('word', '').strip().lower()
        valid = is_valid_word(word, dictionary) if word else False
        self._json_response({'word': word, 'valid': valid})

    def _handle_next_round(self, body: dict):
        seq = game_state.get('round_sequence', [])
        idx = game_state.get('current_round_index', 0)
        if idx < len(seq):
            game_state['current_round_index'] = idx + 1
        game_state['current_round'] = None
        self._json_response({
            'round_index': game_state['current_round_index'],
            'total_rounds': len(seq),
            'scores': game_state['scores'],
            'finished': game_state['current_round_index'] >= len(seq) if seq else False,
        })

    # --- Helpers ---

    def _read_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}

    def _json_response(self, data: dict, code: int = 200):
        body = json.dumps(data, default=str).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_template(self, name: str, context: dict):
        tmpl = env.get_template(name)
        html = tmpl.render(**context).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def _serve_static(self, filepath: str):
        full = STATIC / filepath
        if not full.is_file():
            self.send_error(404)
            return
        ext = full.suffix.lower()
        ctypes = {
            '.css': 'text/css', '.js': 'application/javascript',
            '.html': 'text/html', '.json': 'application/json',
            '.png': 'image/png', '.jpg': 'image/jpeg',
            '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
            '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
            '.woff2': 'font/woff2', '.woff': 'font/woff',
            '.ttf': 'font/ttf',
        }
        ctype = ctypes.get(ext, 'application/octet-stream')
        data = full.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # suppress request logs


def main():
    os.chdir(BASE)
    init_dictionary()
    port = 5000
    server = HTTPServer(('0.0.0.0', port), GameHandler)
    print(f"Countdown Party running at http://localhost:{port}")
    print(f"  Setup: http://localhost:{port}/")
    print(f"  Host:  http://localhost:{port}/host")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == '__main__':
    main()
