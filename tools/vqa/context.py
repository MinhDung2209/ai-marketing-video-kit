"""Context container for VQA checks."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from tools.vqa.rules import load_rules


class VQAContext:
    def __init__(self, clip_dir: Path | str, rules: Optional[Dict[str, Any]] = None):
        self.clip_dir = Path(clip_dir).resolve()
        self.rules = rules if rules is not None else load_rules(self.clip_dir)
        self._clip_json = None
        self._voice_json = None
        self._brief_md = None
        self._shots_json = None
        self._cues_json = None
        self._index_html = None
        self._final_mp4 = None

    @property
    def clip_json(self) -> Dict[str, Any]:
        if self._clip_json is None:
            p = self.clip_dir / "clip.json"
            if p.exists():
                try:
                    self._clip_json = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    self._clip_json = {}
            else:
                self._clip_json = {}
        return self._clip_json

    @property
    def voice_json(self) -> Dict[str, Any]:
        if self._voice_json is None:
            p = self.clip_dir / "voice.json"
            if p.exists():
                try:
                    self._voice_json = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    self._voice_json = {}
            else:
                self._voice_json = {}
        return self._voice_json

    @property
    def brief_md(self) -> str:
        if self._brief_md is None:
            p = self.clip_dir / "BRIEF.md"
            if p.exists():
                try:
                    self._brief_md = p.read_text(encoding="utf-8")
                except Exception:
                    self._brief_md = ""
            else:
                self._brief_md = ""
        return self._brief_md

    @property
    def shots_json(self) -> Dict[str, Any]:
        if self._shots_json is None:
            p = self.clip_dir / "shots.json"
            if p.exists():
                try:
                    self._shots_json = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    self._shots_json = {}
            else:
                self._shots_json = {}
        return self._shots_json

    @property
    def cues_json(self) -> Dict[str, Any]:
        if self._cues_json is None:
            p = self.clip_dir / "cues.json"
            if p.exists():
                try:
                    self._cues_json = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    self._cues_json = {}
            else:
                self._cues_json = {}
        return self._cues_json

    @property
    def index_html(self) -> str:
        if self._index_html is None:
            p = self.clip_dir / "index.html"
            if p.exists():
                try:
                    self._index_html = p.read_text(encoding="utf-8")
                except Exception:
                    self._index_html = ""
            else:
                self._index_html = ""
        return self._index_html

    @property
    def final_mp4(self) -> Optional[Path]:
        if self._final_mp4 is None:
            final_dir = self.clip_dir / "final"
            if final_dir.is_dir():
                # find .mp4 files that are not .tmp.mp4
                candidates = [f for f in final_dir.glob("*.mp4") if not f.name.endswith(".tmp.mp4")]
                if candidates:
                    self._final_mp4 = candidates[0]
            if not self._final_mp4:
                # check renders/
                renders_dir = self.clip_dir / "renders"
                if renders_dir.is_dir():
                    candidates = [f for f in renders_dir.glob("*.mp4") if not f.name.endswith(".tmp.mp4")]
                    if candidates:
                        self._final_mp4 = candidates[0]
            if not self._final_mp4:
                # check clip root
                for f in self.clip_dir.glob("*.mp4"):
                    if not f.name.endswith(".tmp.mp4"):
                        self._final_mp4 = f
                        break
        return self._final_mp4

    def get_shot_marks(self, shot_id: str) -> List[Dict[str, Any]]:
        """Return list of marks from assets/screen/<shot_id>/marks.json."""
        marks_file = self.clip_dir / "assets" / "screen" / shot_id / "marks.json"
        if marks_file.exists():
            try:
                data = json.loads(marks_file.read_text(encoding="utf-8"))
                return data.get("marks", [])
            except Exception:
                pass
        return []

    def get_captured_dom_text(self, shot_id: str) -> str:
        """Collect all captured DOM text for a shot/scene."""
        chunks = []
        shot_dir = self.clip_dir / "assets" / "screen" / shot_id

        # 1. Look for _dom/*.txt snapshot files
        dom_dir = shot_dir / "_dom"
        if dom_dir.is_dir():
            for txt_file in dom_dir.glob("*.txt"):
                try:
                    chunks.append(txt_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

        # 2. Look for any other .txt in shot_dir
        for txt_file in shot_dir.glob("*.txt"):
            if txt_file.name != "marks.json":
                try:
                    chunks.append(txt_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

        # 3. Read element_text or page_text_path from marks.json
        for m in self.get_shot_marks(shot_id):
            if m.get("element_text"):
                chunks.append(m["element_text"])
            if m.get("page_text_path"):
                page_file = shot_dir / m["page_text_path"]
                if page_file.exists():
                    try:
                        chunks.append(page_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass

        # 4. Extract target/text from shots.json with vars substituted
        shots = self.shots_json.get("shots", {})
        if shot_id in shots:
            shot_def = shots[shot_id]
            vars_dict = self.clip_json.get("vars", {})
            if shot_def.get("note"):
                chunks.append(str(shot_def["note"]))
            for step in shot_def.get("steps", []):
                for k in ("text", "has_text", "url", "after_label"):
                    v = step.get(k)
                    if isinstance(v, str):
                        subbed = re.sub(r"\$\{(\w+)\}", lambda m: str(vars_dict.get(m.group(1), m.group(0))), v)
                        chunks.append(subbed)
                target = step.get("target")
                if isinstance(target, dict):
                    for tk in ("text", "has_text", "after_label"):
                        tv = target.get(tk)
                        if isinstance(tv, str):
                            subbed = re.sub(r"\$\{(\w+)\}", lambda m: str(vars_dict.get(m.group(1), m.group(0))), tv)
                            chunks.append(subbed)

        # 5. Include vars from clip.json
        for v in self.clip_json.get("vars", {}).values():
            if isinstance(v, str):
                chunks.append(v)

        # 6. Include badges from story.py / index.html
        for b in self.get_badges():
            chunks.append(b.get("text", ""))

        return "\n".join(chunks)

    def get_badges(self) -> List[Dict[str, str]]:
        """Collect all badges from index.html (.step) and story.py (badge=...)."""
        results = []
        if self.index_html:
            for match in re.finditer(r'<div class="step">([^<]+)</div>', self.index_html):
                results.append({"where": "index.html .step", "text": match.group(1).strip()})

        story_py = self.clip_dir / "story.py"
        if story_py.exists():
            try:
                content = story_py.read_text(encoding="utf-8")
                for match in re.finditer(r'badge=([\'"])([^\'"]+)\1', content):
                    results.append({"where": "story.py badge", "text": match.group(2).strip()})
            except Exception:
                pass
        return results
