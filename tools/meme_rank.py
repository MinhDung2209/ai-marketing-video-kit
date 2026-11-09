"""Offline meme shortlist with existing kit IDs and untouched asset metadata.

Independent adaptation of relevance/trend concepts in ghost-editor's
scripts/meme_find.py (ce172726c36293722b08eb57b5b307d4f06389e8).
No engines, imports of fetch/search scripts, network calls or file writes.
Trend is caller-maintained metadata, never a claim about live popularity.

rank_memes(query, items, used_ids=(), limit=5, emotion='') returns scored
entries containing the original asset under 'asset'. Items use the existing
catalog.json/web.json shape. Optional fields: emotion (string/list),
trigger_phrases (string/list), use_case/use and trend_status.

Relevance = 3*tag/emotion token overlaps + 2*trigger token overlaps
             + use/title/ID token overlaps + 4 for a whole trigger phrase.
Trend bonus: hot=1, evergreen=0.5, dying=-1, missing/unknown=0.
Score = relevance + trend bonus - 10*uses in the CURRENT clip. Repetition
is a penalty, not an exclusion; callers still choose whether to reuse.
Nonempty queries omit assets with no relevance. Ties use relevance then
the unchanged ID, independent of catalog order. Empty queries browse all.
Matching accepts accented, unaccented and decomposed Vietnamese; only
comparison keys are folded. Input text, IDs and metadata remain unchanged.

CLI emits UTF-8 JSON to stdout only; repeat --catalog to combine local
catalogs, and --used to record uses in one clip (duplicates count):
  python -B tools/meme_rank.py "tiền" --used noto/money -n 3
  python -B tools/meme_rank.py "tiền" --catalog meme-library/catalog.json
  python -B tools/meme_rank.py "bất ngờ" --catalog meme-library/web.json --used cat-shocked
--used-file accepts a JSON ID list or {ID: nonnegative_integer_count}.
Default catalog: meme-library/catalog.json. Missing catalog: unavailable,
exit 2; invalid data: failed, exit 2. No download or installation fallback.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterable, Mapping
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import unicodedata


TREND = {"hot": 1.0, "evergreen": 0.5, "dying": -1.0}
REPEAT_PENALTY = 10.0
DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "meme-library" / "catalog.json"


def words(text: str) -> list[str]:
    """Unicode tokens retaining accents, with canonical case normalization."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold())


def _key(word: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", word)
        if unicodedata.category(ch) != "Mn"
    ).replace("đ", "d")


def _keys(text: str) -> list[str]:
    return [_key(word) for word in words(text)]


def _texts(item: Mapping, field: str) -> list[str]:
    value = item.get(field, [])
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"{item['id']}: {field} must be a string or string array")
    return value


def _tokens(texts: Iterable[str]) -> set[str]:
    return {token for text in texts for token in _keys(text)}


def _phrase_in(phrase: list[str], text: list[str]) -> bool:
    return bool(phrase) and any(
        text[i:i + len(phrase)] == phrase
        for i in range(len(text) - len(phrase) + 1)
    )


def _uses(used_ids: Iterable[str] | Mapping[str, int]) -> Counter:
    if used_ids is None or isinstance(used_ids, (str, bytes)):
        raise ValueError("used_ids must be an ID list or ID/count mapping, not a string")
    try:
        counts = Counter(used_ids)
    except TypeError as exc:
        raise ValueError("used_ids must contain string IDs") from exc
    for asset_id, count in counts.items():
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError("used IDs must be nonempty strings")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("used counts must be nonnegative integers")
    return counts


def rank_memes(
    query: str,
    items: Iterable[Mapping],
    *,
    used_ids: Iterable[str] | Mapping[str, int] = (),
    limit: int = 5,
    emotion: str = "",
) -> list[dict]:
    """Return deterministic scores; pure function, with no usage history saved.

    Pass used_ids from the current clip on EVERY call. Unknown used IDs are
    harmless; IDs are compared exactly, never normalized or renamed. Duplicate
    candidate IDs are rejected so collection merges cannot silently lose data.
    Emotion filters whole tag/emotion phrases (accent/case insensitive).
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a nonnegative integer")
    query_tokens = _keys(query)
    emotion_tokens = _keys(emotion)
    query_set = set(query_tokens + emotion_tokens)
    used = _uses(used_ids)
    seen = set()
    scored = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("each asset must be an object")
        asset_id = item.get("id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError("each asset needs a nonempty string id")
        if asset_id in seen:
            raise ValueError(f"duplicate asset id: {asset_id}")
        seen.add(asset_id)
        tags = _texts(item, "tags") + _texts(item, "emotion")
        triggers = _texts(item, "trigger_phrases")
        context = [asset_id]
        for field in ("use_case", "use", "title", "name", "description"):
            context.extend(_texts(item, field))
        trend_status = item.get("trend_status", "")
        if not isinstance(trend_status, str):
            raise ValueError(f"{asset_id}: trend_status must be a string")
        if emotion_tokens and not any(_keys(tag) == emotion_tokens for tag in tags):
            continue
        tag_hits = query_set & _tokens(tags)
        trigger_hits = query_set & _tokens(triggers)
        context_hits = query_set & _tokens(context)
        phrase_hit = any(_phrase_in(_keys(t), query_tokens) for t in triggers)
        relevance = 3 * len(tag_hits) + 2 * len(trigger_hits) + len(context_hits)
        relevance += 4 if phrase_hit else 0
        if query_set and not relevance:
            continue
        trend_bonus = TREND.get(trend_status.casefold().strip(), 0.0)
        used_count = used[asset_id]
        repeat_penalty = REPEAT_PENALTY * used_count
        scored.append({
            "id": asset_id,
            "score": relevance + trend_bonus - repeat_penalty,
            "relevance": relevance,
            "trend_bonus": trend_bonus,
            "used_count": used_count,
            "repeat_penalty": repeat_penalty,
            "matches": {
                "tags": sorted({w for w in words(query + " " + emotion) if _key(w) in tag_hits}),
                "triggers": sorted({w for w in words(query + " " + emotion) if _key(w) in trigger_hits}),
                "context": sorted({w for w in words(query + " " + emotion) if _key(w) in context_hits}),
                "trigger_phrase": phrase_hit,
            },
            "asset": deepcopy(dict(item)),
        })
    scored.sort(key=lambda row: (-row["score"], -row["relevance"], row["id"]))
    return scored[:limit]


def load_catalog(path: str | Path) -> list[dict]:
    """Read local UTF-8 JSON list or kit {items:[...]} without opening media."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError(f"{path}: expected an asset array or {{items: [...]}}")
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="*", help="Vietnamese/English line or keywords")
    parser.add_argument("--catalog", action="append", type=Path, help="local JSON; repeat to combine")
    parser.add_argument("--used", "--used-id", action="append", default=[], metavar="ID",
                        help="ID already used in this clip; repeat for each use")
    parser.add_argument("--used-file", type=Path, help="local JSON ID list or ID/count mapping")
    parser.add_argument("--emotion", default="", help="filter a complete tag/emotion phrase")
    parser.add_argument("-n", "--limit", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        items = []
        for path in args.catalog or [DEFAULT_CATALOG]:
            items.extend(load_catalog(path))
        used = _uses(args.used)
        if args.used_file:
            data = json.loads(args.used_file.read_text(encoding="utf-8-sig"))
            if not isinstance(data, (list, dict)):
                raise ValueError("used-file must contain an ID list or ID/count mapping")
            used.update(_uses(data))
        query = " ".join(args.query)
        ranked = rank_memes(query, items, used_ids=used, limit=args.limit, emotion=args.emotion)
        result = {"status": "ok", "query": query, "emotion": args.emotion, "ranked": ranked}
        exit_code = 0
    except FileNotFoundError as exc:
        result = {"status": "unavailable", "error": str(exc),
                  "remediation": "Supply existing local --catalog/--used-file JSON. No download was attempted."}
        exit_code = 2
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        result = {"status": "failed", "error": str(exc)}
        exit_code = 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
