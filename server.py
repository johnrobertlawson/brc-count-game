#!/usr/bin/env python3
"""Countdown party game server using stdlib http.server + jinja2."""

import argparse
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
    generate_anagram, generate_easy_anagram, solve_numbers,
)
from word_list import (
    load_dictionary, is_valid_word, can_make_word,
    get_conundrum_words, get_easy_conundrum_words,
    find_best_words, find_rarest_word,
)

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
        elif path == '/api/buzz_conundrum':
            self._handle_buzz_conundrum(body)
        elif path == '/api/override_word':
            self._handle_override_word(body)
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
            macro = game_state['settings'].get('macro', 'medium')
            if macro == 'easy':
                candidates = get_easy_conundrum_words(dictionary, length)
            else:
                candidates = get_conundrum_words(dictionary, length)
            if not candidates:
                candidates = conundrum_words
            word = random.choice(candidates)
            if macro == 'easy':
                anagram = generate_easy_anagram(word)
            elif macro == 'medium':
                anagram = generate_easy_anagram(word)
            else:
                anagram = generate_anagram(word)
            lives_mode = game_state['settings'].get('conundrum_lives', False)
            lives = {t: 5 for t in game_state['teams']} if lives_mode else {}
            game_state['current_round'] = {
                'type': 'conundrum', 'word': word, 'anagram': anagram,
                'phase': 'playing', 'solved_by': None,
                'lives_mode': lives_mode, 'lives': lives,
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

        # Dictionary Geeks Club: find best and rarest words
        best_word_info = find_best_words(available, dictionary)
        rarest_word_info = find_rarest_word(
            available, dictionary,
            exclude_word=best_word_info.get('word'),
        )
        reveal = {
            'best_word': best_word_info,
            'rarest_word': rarest_word_info,
            'available_letters': [l.lower() for l in available],
        }
        rnd['reveal'] = reveal

        rnd['results'] = results
        rnd['phase'] = 'scored'
        game_state['round_history'].append(dict(rnd))
        self._json_response({
            'results': results,
            'scores': game_state['scores'],
            'reveal': reveal,
        })

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
                elif diff <= 20:
                    pts = 3
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

        # Compute best possible solution
        best_solution = solve_numbers(available, target)
        rnd['best_solution'] = best_solution

        rnd['results'] = results
        rnd['phase'] = 'scored'
        game_state['round_history'].append(dict(rnd))
        self._json_response({
            'results': results,
            'scores': game_state['scores'],
            'best_solution': best_solution,
        })

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

    def _handle_buzz_conundrum(self, body: dict):
        team = body.get('team', '')
        guess = body.get('guess', '').strip().lower()
        rnd = game_state.get('current_round')
        if not rnd or rnd['type'] != 'conundrum':
            self._json_response({'error': 'No conundrum round active'}, 400)
            return
        if not rnd.get('lives_mode'):
            self._json_response({'error': 'Lives mode not enabled'}, 400)
            return
        lives = rnd.get('lives', {})
        if lives.get(team, 0) <= 0:
            self._json_response({'error': 'No lives remaining', 'correct': False, 'lives': lives})
            return
        if guess == rnd['word']:
            # Correct!
            rnd['solved_by'] = team
            results = score_conundrum(team, game_state['teams'])
            for t, pts in results.items():
                game_state['scores'][t] = game_state['scores'].get(t, 0) + pts
            rnd['results'] = results
            rnd['phase'] = 'scored'
            game_state['round_history'].append(dict(rnd))
            self._json_response({
                'correct': True, 'answer': rnd['word'],
                'results': results, 'scores': game_state['scores'],
            })
        else:
            lives[team] = lives.get(team, 0) - 1
            rnd['lives'] = lives
            self._json_response({
                'correct': False, 'lives': lives,
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

    def _handle_override_word(self, body: dict):
        team = body.get('team')
        if not team:
            self._json_response({'error': 'No team specified'}, 400)
            return
        history = game_state.get('round_history', [])
        # Find the most recent letters round
        rnd = None
        for r in reversed(history):
            if r.get('type') == 'letters':
                rnd = r
                break
        if not rnd or 'results' not in rnd:
            self._json_response({'error': 'No letters round to override'}, 400)
            return
        results = rnd['results']
        if team not in results:
            self._json_response({'error': f'Team {team} not found'}, 400)
            return
        entry = results[team]
        if entry.get('valid'):
            self._json_response({'error': 'Word already valid'}, 400)
            return
        # Override: award base score for word length
        old_total = entry['total']
        entry['valid'] = True
        entry['base_score'] = len(entry['word'])
        entry.pop('error', None)
        # Recalculate bonuses for all teams in this round
        all_bases = {t: r['base_score'] for t, r in results.items()}
        top = max(all_bases.values()) if all_bases else 0
        runner_up = 0
        for s in sorted(all_bases.values(), reverse=True):
            if s < top:
                runner_up = s
                break
        bonus = max(3, 3 * (top - runner_up)) if top > 0 else 0
        for t, r in results.items():
            r['bonus'] = bonus if r['base_score'] == top and top > 0 else 0
            r['total'] = r['base_score'] + r['bonus']
        # Update cumulative scores
        diff = entry['total'] - old_total
        game_state['scores'][team] = game_state['scores'].get(team, 0) + diff
        # Recalc other teams whose bonus may have changed
        for t, r in results.items():
            if t != team:
                old_t = all_bases[t] + (bonus if all_bases[t] == top else 0)
                # Just recompute from scratch for safety
                pass
        # Simpler: recompute all team scores from round history
        scores = {t: 0 for t in game_state['teams']}
        for past_rnd in history:
            if 'results' in past_rnd:
                for t, r in past_rnd['results'].items():
                    if isinstance(r, dict) and 'total' in r:
                        scores[t] = scores.get(t, 0) + r['total']
                    elif isinstance(r, dict) and 'score' in r:
                        scores[t] = scores.get(t, 0) + r['score']
                    elif isinstance(r, int):
                        scores[t] = scores.get(t, 0) + r
        game_state['scores'] = scores
        self._json_response({'results': results, 'scores': scores})

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
    parser = argparse.ArgumentParser(description='Countdown Party Game')
    parser.add_argument('-p', '--port', type=int, default=8000,
                        help='Port to run on (default: 8000)')
    args = parser.parse_args()

    os.chdir(BASE)
    init_dictionary()
    port = args.port
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
