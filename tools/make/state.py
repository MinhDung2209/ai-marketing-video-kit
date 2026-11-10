"""Quản lý trạng thái thực thi và khả năng resume qua run.json."""
import datetime
import json
import pathlib
from typing import Any, Dict, List, Optional

ALL_STAGES = [
    "discover",
    "brief",
    "shots",
    "record",
    "voice",
    "sources",
    "story",
    "build",
    "render",
    "studio",
]


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class RunState:
    def __init__(self, clip_dir: pathlib.Path):
        self.clip_dir = pathlib.Path(clip_dir).resolve()
        self.run_file = self.clip_dir / "run.json"
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if self.run_file.exists():
            try:
                self.data = json.loads(self.run_file.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}
        else:
            self.data = {}

    def save(self):
        self.clip_dir.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = now_iso()
        self.run_file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def init_if_new(
        self,
        url: str,
        goal: str,
        profile: str = "stradevn",
        len_sec: int = 90,
        loop: bool = False,
        model: str = "agy:gemini-3.8-flash-high",
    ):
        if not self.data:
            self.data = {
                "url": url,
                "goal": goal,
                "profile": profile,
                "len": len_sec,
                "loop": loop,
                "model": model,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "stages": {},
                "history": [],
            }
            self.save()
        else:
            # Cập nhật thông tin nếu có truyền vào mới
            if url: self.data["url"] = url
            if goal: self.data["goal"] = goal
            if profile: self.data["profile"] = profile
            if model: self.data["model"] = model
            if loop is not None: self.data["loop"] = loop
            self.save()

    def get_stage_status(self, stage: str) -> str:
        return self.data.get("stages", {}).get(stage, {}).get("status", "pending")

    def is_done(self, stage: str) -> bool:
        return self.get_stage_status(stage) == "done"

    def start_stage(self, stage: str):
        self.data.setdefault("stages", {})
        st = self.data["stages"].setdefault(stage, {})
        st["status"] = "running"
        st["started_at"] = now_iso()
        self.data["current_stage"] = stage
        self.save()

    def finish_stage(self, stage: str, details: Optional[Dict[str, Any]] = None):
        self.data.setdefault("stages", {})
        st = self.data["stages"].setdefault(stage, {})
        st["status"] = "done"
        st["finished_at"] = now_iso()
        if details:
            st["details"] = details
        self.data.setdefault("history", []).append(
            {"stage": stage, "status": "done", "at": now_iso()}
        )
        self.save()

    def fail_stage(self, stage: str, error: str, retries: int = 0):
        self.data.setdefault("stages", {})
        st = self.data["stages"].setdefault(stage, {})
        st["status"] = "failed"
        st["error"] = error
        st["retries"] = retries
        st["failed_at"] = now_iso()
        self.data.setdefault("history", []).append(
            {"stage": stage, "status": "failed", "error": error, "at": now_iso()}
        )
        self.save()

    def determine_stages_to_run(
        self, from_stage: Optional[str] = None, only_stage: Optional[str] = None
    ) -> List[str]:
        """Xác định danh sách các stage cần chạy dựa theo trạng thái và tham số."""
        if only_stage:
            if only_stage not in ALL_STAGES:
                raise ValueError(f"Stage không hợp lệ: {only_stage}. Các stage: {ALL_STAGES}")
            return [only_stage]

        start_idx = 0
        if from_stage:
            if from_stage not in ALL_STAGES:
                raise ValueError(f"Stage không hợp lệ: {from_stage}. Các stage: {ALL_STAGES}")
            start_idx = ALL_STAGES.index(from_stage)
        else:
            # Tìm stage đầu tiên chưa done
            for idx, stg in enumerate(ALL_STAGES):
                if not self.is_done(stg):
                    start_idx = idx
                    break
            else:
                return []  # Đã hoàn thành mọi stage

        return ALL_STAGES[start_idx:]
