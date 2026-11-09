"""Offline caption data layout; no ASR, providers, rendering or file mutation.

layout(words, timing='aligned', aspect='9:16') accepts ordered {text,start,end}
words in seconds. Callers MUST declare timing='aligned' or 'estimated'; this
module cannot establish alignment quality. Width means Unicode display columns,
not font pixels (combining accents take no extra column; wide glyphs take two).
The 16:9/9:16 defaults are 42/28 columns, with at most two lines.

Manual overrides are {word_start,word_end,text}, inclusive source-word ranges.
They reserve whole cues, preserve text EXACTLY, and never regenerate corrected
text from the aligned transcript. Explicit newlines are preserved; otherwise
lines are balanced. Unfitting manual text stays intact with diagnostic warnings.
Corrected display tokens have estimated timing; source-word times remain intact.

Result: {status,aspect,timing,rules,words,cues,warnings}. Each cue has text, lines,
start/end, inclusive word_start/end, timing and manual. Ranges cover every input
word exactly once, even when a manual correction replaces several spoken words.
Warnings expose impossible reading speed, long single words or manual overflow.
No word is shortened, case-folded, normalized, silently dropped or repeated.

Reference concepts: lonthq/overtone-captions at
9fad13e25d59869ebed41f5979120f09b95abea0, segment/{rules,splitter}.ts and
segment/rulesets/1.ts: balanced lines, pause cuts, reading time and bounded holds.
This is an independent neutral implementation, without its non-Vietnamese
grammar packs or provider defaults. It does not integrate tools/captions.py.

CLI (JSON only on stdout):
  python -B tools/caption_layout.py words.json --timing aligned --aspect 9:16
Input may be an array or {words:[...],timing:'aligned',overrides:[...],duration:9}.
--overrides accepts a JSON file containing the override array. Output goes to
stdout; callers own output paths. Validation errors are JSON with exit code 2.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path
import sys
import unicodedata


@dataclass(frozen=True)
class LayoutRules:
    max_chars_per_line: int = 42
    max_lines: int = 2
    min_duration: float = 0.7
    max_duration: float = 6.0
    max_cps: float = 20.0
    pause_break: float = 1.0
    max_hold: float = 1.5
    min_blank: float = 0.4


def display_width(text: str) -> int:
    """Count NFC display columns without changing the returned source text."""
    return sum(0 if unicodedata.category(ch) in {'Mn', 'Me', 'Cf'} else
               2 if unicodedata.east_asian_width(ch) in {'W', 'F'} else 1
               for ch in unicodedata.normalize('NFC', text))


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f'{label} must be a finite number')
    if not math.isfinite(value):
        raise ValueError(f'{label} must be finite')
    return float(value)


def _rules(aspect: str, rules: LayoutRules | None) -> LayoutRules:
    if aspect not in {'16:9', '9:16'}:
        raise ValueError('aspect must be 16:9 or 9:16')
    result = rules if rules is not None else replace(
        LayoutRules(), max_chars_per_line=42 if aspect == '16:9' else 28)
    if not isinstance(result, LayoutRules):
        raise ValueError('rules must be LayoutRules')
    for key in ('max_chars_per_line', 'max_lines'):
        value = getattr(result, key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f'{key} must be a positive integer')
    if result.max_lines > 2:
        raise ValueError('max_lines cannot exceed two')
    for key in ('min_duration', 'max_duration', 'max_cps', 'pause_break',
                'max_hold', 'min_blank'):
        value = _number(getattr(result, key), key)
        if value < 0 or (key in {'max_duration', 'max_cps', 'pause_break'} and value == 0):
            raise ValueError(f'{key} is outside its valid range')
    if result.min_duration > result.max_duration:
        raise ValueError('min_duration exceeds max_duration')
    return result


def _validate_words(words: object) -> list[dict]:
    if not isinstance(words, list):
        raise ValueError('words must be an array of {text,start,end}')
    out = []
    previous_end = 0.0
    for i, word in enumerate(words):
        if not isinstance(word, dict):
            raise ValueError(f'word {i} must be an object')
        text = word.get('text')
        if (not isinstance(text, str) or not text or any(c.isspace() for c in text)
                or any(unicodedata.category(c) == 'Cc' for c in text)):
            raise ValueError(f'word {i} text must be a nonempty single token')
        start = _number(word.get('start'), f'word {i} start')
        end = _number(word.get('end'), f'word {i} end')
        if not previous_end <= start < end:
            raise ValueError(f'word {i} must be ordered, positive-duration and nonoverlapping')
        out.append(dict(word, start=start, end=end))
        previous_end = end
    return out


def _line_layout(texts: list[str], rules: LayoutRules) -> tuple[list[str], float] | None:
    """Find a balanced one/two-line layout, allowing isolated overlong tokens."""
    joined = ' '.join(texts)
    if display_width(joined) <= rules.max_chars_per_line or len(texts) == 1:
        return [joined], 0.0
    if rules.max_lines == 1:
        return None
    best = None
    widths = [display_width(text) for text in texts]
    prefix = [0]
    for width in widths:
        prefix.append(prefix[-1] + width + 1)
    for cut in range(1, len(texts)):
        left, right = prefix[cut] - 1, prefix[-1] - prefix[cut] - 1
        if left > rules.max_chars_per_line and cut != 1:
            continue
        if right > rules.max_chars_per_line and cut != len(texts) - 1:
            continue
        punctuation = texts[cut - 1].rstrip('\"\u201d\u2019\')').endswith((',', ';', ':', '.', '?', '!', '…'))
        cost = 1 + abs(left - right) * 0.08 + max(0, left - right) * 0.04
        cost += 1.5 if min(cut, len(texts) - cut) == 1 else 0
        cost -= 0.5 if punctuation else 0
        if best is None or cost < best[1]:
            best = ([' '.join(texts[:cut]), ' '.join(texts[cut:])], cost)
    return best


def _split(words: list[dict], start: int, stop: int, rules: LayoutRules) -> list[dict]:
    """DP over word boundaries, with width and pause as hard constraints."""
    best = {stop: 0.0}
    choices = {}
    # A fitting two-line cue cannot contain more than 2*width one-column words.
    for first in range(stop - 1, start - 1, -1):
        choice = None
        texts = []
        for last in range(first, min(stop, first + rules.max_chars_per_line * 2 + 2)):
            if last > first and (
                words[last]['start'] - words[last - 1]['end'] >= rules.pause_break
                or words[last].get('speaker') != words[first].get('speaker')
                or words[last].get('break_before', False)
            ):
                break
            texts.append(words[last]['text'])
            elapsed = words[last]['end'] - words[first]['start']
            if elapsed > rules.max_duration and last > first:
                break
            candidate = _line_layout(texts, rules)
            if candidate is None:
                break
            lines, balance_cost = candidate
            next_start = words[last + 1]['start'] if last + 1 < len(words) else words[last]['end'] + rules.max_hold
            available = min(next_start, words[last]['end'] + rules.max_hold) - words[first]['start']
            needed = max(rules.min_duration, display_width(' '.join(texts)) / rules.max_cps)
            cost = 3 + balance_cost + 6 * max(0, needed - available)
            if len(texts) == 1 and stop - start > 1:
                cost += 5
            if last + 1 < stop:
                gap = words[last + 1]['start'] - words[last]['end']
                cost += 0 if texts[-1].rstrip('\"\u201d\u2019\')').endswith(('.', '?', '!', '…')) else 2
                cost -= min(1.0, gap / rules.pause_break)
            total = cost + best[last + 1]
            if choice is None or total < choice[0]:
                choice = (total, {'word_start': first, 'word_end': last, 'lines': lines,
                                  'text': '\n'.join(lines), 'manual': False})
        # A single token is always representable, including one exceeding width/duration.
        best[first], choices[first] = choice
    result = []
    cursor = start
    while cursor < stop:
        cue = choices[cursor]
        result.append(cue)
        cursor = cue['word_end'] + 1
    return result


def layout(words: list[dict], *, timing: str, aspect: str = '16:9',
           duration: float | None = None, overrides: list[dict] | None = None,
           rules: LayoutRules | None = None) -> dict:
    """Return JSON-compatible caption data; raise ValueError on invalid input.

    ``duration`` caps holds and must include every word. Omit it to end at the
    final word. Explicit ``break_before: true`` forces a cue at a supplied word;
    speaker changes and >=pause_break gaps also force automatic cue boundaries.
    Manual ranges take priority; conflicting pause/width rules are reported.
    """
    if timing not in {'aligned', 'estimated'}:
        raise ValueError('timing must explicitly be aligned or estimated')
    rules = _rules(aspect, rules)
    words = _validate_words(words)
    last_end = words[-1]['end'] if words else 0.0
    duration = last_end if duration is None else _number(duration, 'duration')
    if duration < last_end or duration < 0:
        raise ValueError('duration must include all words')
    overrides = [] if overrides is None else overrides
    if not isinstance(overrides, list):
        raise ValueError('overrides must be an array')
    manual = []
    for i, override in enumerate(overrides):
        if not isinstance(override, dict):
            raise ValueError(f'override {i} must be an object')
        first, last = override.get('word_start'), override.get('word_end')
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (first, last)):
            raise ValueError(f'override {i} requires inclusive integer word_start/word_end')
        if not 0 <= first <= last < len(words):
            raise ValueError(f'override {i} range is outside words')
        text = override.get('text')
        if not isinstance(text, str) or not text.strip() or '\r' in text or any(
                unicodedata.category(c) == 'Cc' and c != '\n' for c in text):
            raise ValueError(f'override {i} requires nonempty text (LF newlines allowed)')
        lines = text.split('\n')
        if len(lines) > rules.max_lines or any(not line.strip() for line in lines):
            raise ValueError(f'override {i} must have at most {rules.max_lines} nonempty lines')
        if len(lines) == 1:
            candidate = _line_layout(text.split(), rules)
            if candidate is not None:
                lines = candidate[0]
        manual.append({'word_start': first, 'word_end': last, 'text': text,
                       'lines': lines, 'manual': True})
    manual.sort(key=lambda cue: cue['word_start'])
    cues = []
    cursor = 0
    for cue in manual:
        if cue['word_start'] < cursor:
            raise ValueError('manual override ranges overlap')
        cues.extend(_split(words, cursor, cue['word_start'], rules))
        cues.append(cue)
        cursor = cue['word_end'] + 1
    cues.extend(_split(words, cursor, len(words), rules))
    warnings = []
    for index, cue in enumerate(cues):
        first, last = cue['word_start'], cue['word_end']
        start, end = words[first]['start'], words[last]['end']
        next_start = words[cues[index + 1]['word_start']]['start'] if index + 1 < len(cues) else duration
        room = next_start
        if index + 1 < len(cues) and next_start - end >= rules.pause_break:
            room -= rules.min_blank
        chars = display_width(' '.join(cue['lines']))
        needed = max(rules.min_duration, chars / rules.max_cps)
        end = max(end, min(start + needed, end + rules.max_hold, room, duration,
                           start + rules.max_duration))
        cue.update(start=start, end=end,
                   timing='estimated' if cue['manual'] else timing)
        if any(display_width(line) > rules.max_chars_per_line for line in cue['lines']):
            warnings.append({'cue': index, 'rule': 'max_chars_per_line',
                             'detail': 'Manual text or an indivisible token exceeds the column budget'})
        if end - start > rules.max_duration + 1e-9:
            warnings.append({'cue': index, 'rule': 'max_duration'})
        if end - start < rules.min_duration - 1e-9:
            warnings.append({'cue': index, 'rule': 'min_duration'})
        if chars / (end - start) > rules.max_cps + 1e-9:
            warnings.append({'cue': index, 'rule': 'max_cps'})
        if any(words[k + 1]['start'] - words[k]['end'] >= rules.pause_break
               for k in range(first, last)):
            warnings.append({'cue': index, 'rule': 'pause', 'detail': 'Manual override spans a pause'})
    return {'status': 'ok', 'aspect': aspect, 'timing': timing,
            'rules': asdict(rules), 'words': words, 'cues': cues, 'warnings': warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='UTF-8 JSON words array or object; - reads stdin')
    parser.add_argument('--timing', choices=['aligned', 'estimated'])
    parser.add_argument('--aspect', choices=['16:9', '9:16'], default='16:9')
    parser.add_argument('--duration', type=float)
    parser.add_argument('--overrides', type=Path)
    args = parser.parse_args(argv)
    try:
        raw = json.load(sys.stdin) if args.input == '-' else json.loads(
            Path(args.input).read_text(encoding='utf-8-sig'))
        payload = raw if isinstance(raw, dict) else {'words': raw}
        overrides = json.loads(args.overrides.read_text(encoding='utf-8-sig')) if args.overrides else payload.get('overrides')
        result = layout(payload.get('words'), timing=args.timing or payload.get('timing'),
                        aspect=args.aspect, overrides=overrides,
                        duration=args.duration if args.duration is not None else payload.get('duration'))
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == '__main__':
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
