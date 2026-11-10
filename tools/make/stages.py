"""Định nghĩa và thực thi 10 công đoạn (stages) của kit make."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .gate import run_gate, run_stage_with_gate_loop
from .llm import generate_json
from .safety import check_forbidden_steps
from .schema import validate_data

KIT = pathlib.Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = KIT / "prompts" / "make"


def scaffold_clip(clip_dir: pathlib.Path, profile: str = "stradevn", goal: str = "", slug: Optional[str] = None):
    """Khởi tạo cấu trúc thư mục clip ban đầu tương tự new_clip.py."""
    clip_dir = pathlib.Path(clip_dir).resolve()
    clip_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fonts và CSS
    tpl = KIT / "templates" / "video-project"
    if (tpl / "fonts.css.part").exists() and not (clip_dir / "fonts.css.part").exists():
        shutil.copy2(tpl / "fonts.css.part", clip_dir / "fonts.css.part")
    if (KIT / "templates" / "fonts").exists():
        shutil.copytree(KIT / "templates" / "fonts", clip_dir / "assets" / "fonts", dirs_exist_ok=True)

    # 2. Hồ sơ doanh nghiệp
    prof_file = KIT / "profiles" / profile / "profile.json"
    prof_data = json.loads(prof_file.read_text(encoding="utf-8")) if prof_file.exists() else {}

    # 3. Logo
    logo_name = prof_data.get("brand", {}).get("logo", "logo.jpg")
    src_logo = KIT / "profiles" / profile / logo_name
    dst_logo = clip_dir / "assets" / ("logo" + pathlib.Path(logo_name).suffix)
    dst_logo.parent.mkdir(parents=True, exist_ok=True)
    if src_logo.exists() and not dst_logo.exists():
        shutil.copy2(src_logo, dst_logo)

    # 4. .videokit pointer
    (clip_dir / ".videokit").write_text(str(KIT / "tools"), encoding="utf-8")

    # 5. clip.json
    clip_json = clip_dir / "clip.json"
    if not clip_json.exists():
        c = {
            "slug": slug or clip_dir.name,
            "title": goal or f"Video marketing {profile}",
            "profile": profile,
            "genre": "ma-hs",
            "variants": {"full": "full"},
            "brand": prof_data.get("brand", {}),
            "vars": prof_data.get("vars", {}),
        }
        clip_json.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- STAGE 1: DISCOVER
def stage_discover(clip_dir: pathlib.Path, url: str, cdp_port: int = 9333):
    """Công đoạn khảo sát giao diện ứng dụng web qua discover.py."""
    print(f"\n=== [STAGE 1] DISCOVER: Khảo sát {url} ===")
    inv_file = clip_dir / "inventory.json"
    if inv_file.exists() and inv_file.stat().st_size > 10:
        print(f"  Đã có inventory.json ({inv_file.stat().st_size} bytes) → tiếp tục sử dụng.")
        return

    disc_script = KIT / "screendemo" / "discover.py"
    if not disc_script.exists():
        print(f"  [DISCOVER] ⚠ Chưa có screendemo/discover.py → tạo inventory.json mẫu tối thiểu.", file=sys.stderr)
        minimal_inv = {
            "url": url,
            "title": "Marketing Demo Target App",
            "facts": [
                {"key": "APP_NAME", "value": "StradeVn", "selector": ".brand-logo"},
                {"key": "TAGLINE", "value": "Tìm khách xuất khẩu bằng dữ liệu thật", "selector": ".tagline"},
                {"key": "R_ROW", "value": "24000 KGS", "selector": "tr:has-text('24000 KGS')"},
                {"key": "R_PORT", "value": "CHICAGO", "selector": "td:has-text('CHICAGO')"},
                {"key": "R_BUYER", "value": "HARRIS SPICE", "selector": "td:has-text('HARRIS SPICE')"},
                {"key": "R_19", "value": "19 công ty tiềm năng", "selector": ".count"},
                {"key": "R_COMP", "value": "18 nhà cung cấp", "selector": ".suppliers"},
                {"key": "R_PRICE", "value": "$6,64 / KG", "selector": ".price"},
                {"key": "R_EMAIL", "value": "12/20 công ty có email", "selector": ".email-stat"}
            ],
            "selectors": {
                "raw_data_tab": ":is(a,button,[role=tab]):visible:has-text('Dữ liệu tờ khai thô')",
                "search_input": "input[placeholder*='mã HS']",
                "excel_export": "button:has-text('Xuất Excel')"
            }
        }
        inv_file.write_text(json.dumps(minimal_inv, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    cmd = [sys.executable, "-X", "utf8", str(disc_script), url, "--out", str(inv_file), "--cdp", str(cdp_port)]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- STAGE 2: BRIEF
def stage_brief(clip_dir: pathlib.Path, model_spec: str, goal: str, loop: bool = False, len_sec: int = 90):
    """Công đoạn biên kịch: LLM tạo brief.json, voice.json và cập nhật clip.json vars từ inventory facts."""
    print("\n=== [STAGE 2] BRIEF: Biên kịch kịch bản và đạo diễn giọng nói ===")
    prompt_file = PROMPTS_DIR / "brief.md"
    brief_file = clip_dir / "brief.json"
    voice_file = clip_dir / "voice.json"
    clip_file = clip_dir / "clip.json"
    inv_file = clip_dir / "inventory.json"

    def llm_step(feedback):
        data = generate_json(
            model_spec=model_spec,
            prompt_file=prompt_file,
            target_file=brief_file,
            schema_name="brief",
            context_files=[inv_file, clip_file],
            feedback=feedback,
            cwd=clip_dir,
        )

        # Cập nhật clip.json vars từ brief nếu có
        if "vars" in data and clip_file.exists():
            c = json.loads(clip_file.read_text(encoding="utf-8"))
            c.setdefault("vars", {}).update(data["vars"])
            clip_file.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")

        # Sinh hoặc đồng bộ voice.json
        if not voice_file.exists() or feedback:
            # Tạo voice.json từ scenes trong brief
            lines = []
            for sc in data.get("scenes", []):
                vl = sc.get("voice_line", {})
                if vl:
                    lines.append({
                        "id": vl.get("id"),
                        "text": vl.get("text"),
                        "direction": vl.get("direction"),
                        "caption": vl.get("caption", vl.get("text"))
                    })
            v_data = {
                "model": "gemini-3.1-flash-tts-preview",
                "voice": "Puck",
                "language": "vi-VN",
                "gap_seconds": 0.3,
                "profile": (
                    "Bạn là anh chàng Sales xuất khẩu người Hà Nội, khoảng 28 tuổi, đang giới thiệu một công cụ "
                    "mình dùng hằng ngày cho người xem. Giọng nam miền Bắc trẻ, ấm, tự tin, hơi bí ẩn ở câu hỏi, "
                    "chắc chắn ở con số; không đọc kiểu MC quảng cáo, không đều đều như máy. Nhịp nhanh, gọn, có nhấn nhá "
                    "lên xuống. CHỈ đọc đúng nguyên văn lời thoại được giao, không thêm, không bớt, không đọc phần trong ngoặc vuông. "
                    "Tên thương hiệu StradeVn luôn đọc theo tiếng Anh: 'Strade' như từ trade thêm âm s phía trước, rồi đánh vần "
                    "hai chữ cái tiếng Anh V, N là 'vi en' — tuyệt đối không đọc 'vờ nờ'."
                ),
                "profile_fallback": (
                    "Anh chàng Sales người Hà Nội nói với người xem. Giọng nam miền Bắc trẻ, ấm, tự tin, nhịp nhanh. "
                    "Chỉ đọc đúng nguyên văn. StradeVn đọc 'Strade vi en', không đọc 'vờ nờ'."
                ),
                "lines": lines
            }
            voice_file.write_text(json.dumps(v_data, ensure_ascii=False, indent=2), encoding="utf-8")

        return data

    def gate_step():
        return run_gate("tools/vqa/run.py", [str(clip_dir), "--stage", "brief", "--json"], stage_name="brief")

    run_stage_with_gate_loop("brief", llm_step, gate_step, max_retries=3)


# ---------------------------------------------------------------- STAGE 3: SHOTS
def stage_shots(clip_dir: pathlib.Path, model_spec: str):
    """Công đoạn kịch bản quay: LLM tạo shots.json chọn mục tiêu từ inventory và kiểm tra an toàn."""
    print("\n=== [STAGE 3] SHOTS: Thiết lập kịch bản quay thao tác ===")
    prompt_file = PROMPTS_DIR / "shots.md"
    shots_file = clip_dir / "shots.json"
    brief_file = clip_dir / "brief.json"
    inv_file = clip_dir / "inventory.json"
    clip_file = clip_dir / "clip.json"

    # Đọc hồ sơ an toàn
    prof_name = "stradevn"
    if clip_file.exists():
        prof_name = json.loads(clip_file.read_text(encoding="utf-8")).get("profile", "stradevn")
    prof_file = KIT / "profiles" / prof_name / "profile.json"
    prof_data = json.loads(prof_file.read_text(encoding="utf-8")) if prof_file.exists() else {}

    def llm_step(feedback):
        data = generate_json(
            model_spec=model_spec,
            prompt_file=prompt_file,
            target_file=shots_file,
            schema_name="shots",
            context_files=[inv_file, brief_file, clip_file],
            feedback=feedback,
            cwd=clip_dir,
        )
        return data

    def gate_step():
        # 1. Kiểm tra an toàn bắt buộc (forbidden clicks)
        if shots_file.exists():
            shots_data = json.loads(shots_file.read_text(encoding="utf-8"))
            safe_ok, safe_errors = check_forbidden_steps(shots_data, prof_data)
            if not safe_ok:
                return {"ok": False, "errors": safe_errors, "warnings": []}

        # 2. Chạy dryrun gate script
        return run_gate("screendemo/dryrun.py", [str(clip_dir), "--json"], stage_name="shots_dryrun")

    run_stage_with_gate_loop("shots", llm_step, gate_step, max_retries=3)


# ---------------------------------------------------------------- STAGE 4: RECORD
def stage_record(clip_dir: pathlib.Path):
    """Công đoạn ghi hình màn hình: screendemo/shoot.py."""
    print("\n=== [STAGE 4] RECORD: Quay thao tác màn hình thật ===")
    shots_file = clip_dir / "shots.json"
    if not shots_file.exists():
        raise FileNotFoundError("Thiếu shots.json để quay hình.")

    shots_data = json.loads(shots_file.read_text(encoding="utf-8"))
    # Kiểm tra an toàn trước khi bấm máy
    safe_ok, safe_errors = check_forbidden_steps(shots_data)
    if not safe_ok:
        raise RuntimeError(f"Cấm quay: Vi phạm an toàn trong kịch bản thao tác:\n{safe_errors}")

    shoot_script = KIT / "screendemo" / "shoot.py"
    cmd = [sys.executable, "-X", "utf8", str(shoot_script), str(clip_dir)]
    print(f"  Thực thi: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    # Gate shots
    gate_res = run_gate("tools/vqa/run.py", [str(clip_dir), "--stage", "shots", "--json"], stage_name="record_vqa")
    if not gate_res.get("ok"):
        raise RuntimeError(f"Gate kiểm tra bản quay thất bại: {gate_res.get('errors')}")


# ---------------------------------------------------------------- STAGE 5: VOICE
def stage_voice(clip_dir: pathlib.Path):
    """Công đoạn giọng nói AI (Gemini TTS): 2 takes cho Hook và CTA, QA re-read max 2 lần."""
    print("\n=== [STAGE 5] VOICE: Đạo diễn và thu âm giọng nói Gemini TTS ===")
    voice_file = clip_dir / "voice.json"
    if not voice_file.exists():
        raise FileNotFoundError(f"Không tìm thấy {voice_file}")

    audio_dir = clip_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    tts_script = KIT / "tools" / "tts_script.py"
    tts_qa_script = KIT / "tools" / "tts_qa.py"

    sys.path.insert(0, str(KIT / "tools"))
    import tts_qa

    voice_data = json.loads(voice_file.read_text(encoding="utf-8"))
    lines = voice_data.get("lines", [])
    if not lines:
        raise ValueError("voice.json không có câu thoại nào.")

    # 1. Đọc thử take đầu tiên cho toàn bộ bài
    print("  Đọc toàn bộ kịch bản giọng (Take 1)...")
    cmd_all = [sys.executable, "-X", "utf8", str(tts_script), str(voice_file), str(audio_dir)]
    subprocess.run(cmd_all, check=True)

    # 2. Xử lý 2 Takes cho Hook (V1) và CTA (câu cuối/áp chót)
    hook_id = "V1"
    cta_id = lines[-2]["id"] if len(lines) > 2 else lines[-1]["id"]
    special_lines = [hook_id, cta_id]

    for line_id in special_lines:
        line_item = next((x for x in lines if x["id"] == line_id), None)
        if not line_item:
            continue

        print(f"  Thu âm 2 Takes cho câu mấu chốt {line_id}...")
        orig_mp3 = audio_dir / f"{line_id}.mp3"
        take1_mp3 = audio_dir / f"{line_id}_take1.mp3"
        take2_mp3 = audio_dir / f"{line_id}_take2.mp3"

        if orig_mp3.exists():
            shutil.copy2(orig_mp3, take1_mp3)

        # Đánh giá take 1
        qa_take1 = tts_qa.check(line_item, audio_dir)

        # Chuẩn bị Take 2 với direction biến thể cảm xúc cao hơn
        orig_dir = line_item.get("direction", "")
        line_item["direction"] = (
            orig_dir + " Hãy tăng độ kịch tính, dồn dập và tự nhiên hơn nữa, tạo điểm nhấn sâu sắc."
        )
        voice_file.write_text(json.dumps(voice_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Thu Take 2
        subprocess.run([sys.executable, "-X", "utf8", str(tts_script), str(voice_file), str(audio_dir), "--only", line_id], check=True)
        if orig_mp3.exists():
            shutil.copy2(orig_mp3, take2_mp3)
        qa_take2 = tts_qa.check(line_item, audio_dir)

        # Chấm điểm chọn take tốt hơn (ít cờ hơn, nhịp chuẩn hơn)
        score1 = len(qa_take1.get("flags", [])) + len(qa_take1.get("diffs", [])) * 0.5
        score2 = len(qa_take2.get("flags", [])) + len(qa_take2.get("diffs", [])) * 0.5

        if score2 < score1:
            print(f"  ✓ {line_id}: Chọn Take 2 (tốt hơn take 1)")
            shutil.copy2(take2_mp3, orig_mp3)
        else:
            print(f"  ✓ {line_id}: Giữ Take 1")
            shutil.copy2(take1_mp3, orig_mp3)
            line_item["direction"] = orig_dir
            voice_file.write_text(json.dumps(voice_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. QA soát lỗi phát âm và nhịp điệu toàn bài (re-read max 2 lần cho câu lỗi)
    print("  Soát lại QA toàn bộ bài (tts_qa --redo 2)...")
    cmd_qa = [sys.executable, "-X", "utf8", str(tts_qa_script), str(voice_file), str(audio_dir), "--redo", "2"]
    subprocess.run(cmd_qa, check=True)

    # Đảm bảo narration.mp3 và timing.json được ghép hoàn chỉnh
    subprocess.run(cmd_all, check=True)


# ---------------------------------------------------------------- STAGE 6: SOURCES
def stage_sources(clip_dir: pathlib.Path, model_spec: str):
    """Công đoạn tìm kiếm âm thanh/nguồn tư liệu: tự động qua audio_web, web catalog, Lyria."""
    print("\n=== [STAGE 6] SOURCES: Tìm và tải SFX, BGM, Logo ===")
    sources_file = clip_dir / "sources.json"
    brief_file = clip_dir / "brief.json"

    sys.path.insert(0, str(KIT / "tools"))
    import audio_web

    # Nếu chưa có sources.json, tạo từ brief
    if not sources_file.exists():
        src_list = [
            {"id": "sfx-impact", "scene": "C1,C9", "kind": "sfx", "query_en": "cinematic impact bass hit", "query_vi": "impact bass", "max_dur": 3},
            {"id": "sfx-ping", "scene": "C1,C4,C6", "kind": "sfx", "query_en": "ping highlight ui", "query_vi": "ping", "max_dur": 1.5},
            {"id": "sfx-riser", "scene": "C2", "kind": "sfx", "query_en": "riser short build up", "query_vi": "riser", "max_dur": 3},
            {"id": "sfx-whoosh", "scene": "C2,C4,C6", "kind": "sfx", "query_en": "whoosh transition", "query_vi": "whoosh", "max_dur": 1.5},
            {"id": "sfx-typing", "scene": "C3", "kind": "sfx", "query_en": "keyboard typing", "query_vi": "typing", "max_dur": 4},
            {"id": "sfx-pop", "scene": "C3,C8", "kind": "sfx", "query_en": "pop ui", "query_vi": "pop", "max_dur": 1},
            {"id": "sfx-click", "scene": "C5,C7", "kind": "sfx", "query_en": "mouse click", "query_vi": "click", "max_dur": 0.6},
            {"id": "sfx-chime", "scene": "C5", "kind": "sfx", "query_en": "success chime", "query_vi": "chime", "max_dur": 2.5},
            {"id": "sfx-sparkle", "scene": "C7", "kind": "sfx", "query_en": "sparkle magic", "query_vi": "sparkle", "max_dur": 2},
            {"id": "bgm", "scene": "all", "kind": "bgm", "query_en": "upbeat modern tech corporate confident drums 112 bpm loop", "query_vi": "nhạc tech sôi động"}
        ]
        sources_file.write_text(json.dumps(src_list, ensure_ascii=False, indent=2), encoding="utf-8")

    sources_data = json.loads(sources_file.read_text(encoding="utf-8"))
    assets_src = clip_dir / "assets" / "src"
    assets_src.mkdir(parents=True, exist_ok=True)
    credits_file = clip_dir / "sources" / "credits.md"
    credits_file.parent.mkdir(parents=True, exist_ok=True)

    for item in sources_data:
        need_id = item["id"]
        kind = item.get("kind", "sfx")
        q_en = item.get("query_en", need_id)
        max_dur = item.get("max_dur")
        min_dur = item.get("min_dur")
        dst_file = assets_src / f"{need_id}.mp3"
        if dst_file.exists() and dst_file.stat().st_size > 100:
            continue

        print(f"  Tìm nguồn cho: {need_id} ({kind}: '{q_en}')...")
        top_match = None

        # 1. Tìm trong web catalog sẵn có
        cat_matches = audio_web.catalog(q_en, kind, max_dur, min_dur, 5)
        if cat_matches:
            top_match = cat_matches[0]

        # 2. Nếu là BGM và chưa có: tìm trong thư viện nhạc AI (Lyria)
        if not top_match and kind == "bgm":
            ai_matches = audio_web.ai_search(q_en, 5)
            if ai_matches:
                top_match = ai_matches[0]

        # 3. Tìm qua Web API (Freesound / Jamendo / Openverse)
        if not top_match:
            try:
                web_matches = audio_web.search(kind, q_en, max_dur, min_dur, n=5)
                if web_matches:
                    top_match = web_matches[0]
            except Exception:
                pass

        # 4. Nếu vẫn chưa có và là BGM: dùng Lyria gen
        if not top_match and kind == "bgm":
            try:
                gen_res = audio_web.lyria(clip_dir / "sources" / "audio", q_en, k=1)
                if gen_res:
                    top_match = gen_res[0]
            except Exception:
                pass

        # Tải / chép file
        if top_match:
            if top_match.get("local") and pathlib.Path(top_match["local"]).exists():
                shutil.copy2(top_match["local"], dst_file)
            elif top_match.get("file_url"):
                try:
                    import requests
                    r = requests.get(top_match["file_url"], timeout=30)
                    if r.ok:
                        dst_file.write_bytes(r.content)
                except Exception:
                    pass

            # Ghi nguồn
            with open(credits_file, "a", encoding="utf-8") as cf:
                cf.write(
                    f"- {need_id}: \"{top_match.get('title')}\" — {top_match.get('creator')} · {top_match.get('source')} · {top_match.get('license')}\n"
                )
        else:
            print(f"  ⚠ Không tìm thấy âm thanh phù hợp cho {need_id}, tạo file dự phòng im lặng.", file=sys.stderr)
            # Tạo file mp3 giả bằng ffmpeg nếu thiếu
            subprocess.run(
                ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "1.0", "-q:a", "9", "-y", str(dst_file)],
                capture_output=True,
            )


# ---------------------------------------------------------------- STAGE 7: STORY
def stage_story(clip_dir: pathlib.Path, model_spec: str):
    """Công đoạn kịch bản dựng: LLM tạo story.json từ marks.json và chunk timing."""
    print("\n=== [STAGE 7] STORY: Lập kịch bản dựng khai báo (story.json) ===")
    prompt_file = PROMPTS_DIR / "story.md"
    story_file = clip_dir / "story.json"
    brief_file = clip_dir / "brief.json"
    voice_file = clip_dir / "voice.json"
    timing_file = clip_dir / "audio" / "timing.json"

    # Tập hợp các file marks.json đã ghi hình
    marks_files = list(clip_dir.glob("assets/screen/*/marks.json"))

    def llm_step(feedback):
        data = generate_json(
            model_spec=model_spec,
            prompt_file=prompt_file,
            target_file=story_file,
            schema_name="story",
            context_files=[brief_file, voice_file, timing_file, *marks_files[:5]],
            feedback=feedback,
            cwd=clip_dir,
        )
        return data

    def gate_step():
        # Kiểm tra tính hợp lệ cơ bản của story.json
        if not story_file.exists():
            return {"ok": False, "errors": [{"check": "missing_file", "where": "story", "msg": "story.json chưa được tạo", "fix_hint": "Ghi file story.json"}]}
        story_data = json.loads(story_file.read_text(encoding="utf-8"))
        ok, err = validate_data(story_data, "story")
        if not ok:
            return {"ok": False, "errors": [{"check": "schema_invalid", "where": "story.json", "msg": err, "fix_hint": "Sửa lại theo story.schema.json"}]}
        return {"ok": True, "errors": [], "warnings": []}

    run_stage_with_gate_loop("story", llm_step, gate_step, max_retries=3)


# ---------------------------------------------------------------- STAGE 8: BUILD
def stage_build(clip_dir: pathlib.Path):
    """Công đoạn dựng index.html và cues.json: story_json.py + produce.py --build."""
    print("\n=== [STAGE 8] BUILD: Dựng Timeline HTML và cues.json ===")
    sys.path.insert(0, str(KIT / "screendemo"))
    import story_json

    dur = story_json.build(clip_dir, emit_py=True)
    print(f"  story_json build hoàn tất: thời lượng ước tính = {dur:.2f}s")

    produce_script = KIT / "screendemo" / "produce.py"
    cmd = [sys.executable, "-X", "utf8", str(produce_script), str(clip_dir), "--build"]
    subprocess.run(cmd, check=True)

    # Gate build
    gate_res = run_gate("tools/vqa/run.py", [str(clip_dir), "--stage", "build", "--json"], stage_name="build_vqa")
    if not gate_res.get("ok"):
        raise RuntimeError(f"Gate build VQA thất bại: {gate_res.get('errors')}")


# ---------------------------------------------------------------- STAGE 9: RENDER
def stage_render(clip_dir: pathlib.Path):
    """Công đoạn xuất video hoàn chỉnh: produce.py --only full."""
    print("\n=== [STAGE 9] RENDER: Xuất file MP4 chất lượng cao ===")
    produce_script = KIT / "screendemo" / "produce.py"
    cmd = [sys.executable, "-X", "utf8", str(produce_script), str(clip_dir), "--only", "full"]
    subprocess.run(cmd, check=True)

    # Gate render
    gate_res = run_gate("tools/vqa/run.py", [str(clip_dir), "--stage", "render", "--json"], stage_name="render_vqa")
    if not gate_res.get("ok"):
        raise RuntimeError(f"Gate render VQA thất bại: {gate_res.get('errors')}")


# ---------------------------------------------------------------- STAGE 10: STUDIO
def stage_studio(clip_dir: pathlib.Path, studio_out: Optional[pathlib.Path] = None):
    """Công đoạn chuyển giao dự án HyperFrames Studio: tools/to_studio.py."""
    print("\n=== [STAGE 10] STUDIO: Chuyển đổi sang project HyperFrames Studio ===")
    clip_file = clip_dir / "clip.json"
    profile = "stradevn"
    slug = clip_dir.name
    if clip_file.exists():
        c = json.loads(clip_file.read_text(encoding="utf-8"))
        profile = c.get("profile", profile)
        slug = c.get("slug", slug)

    if studio_out:
        out_path = pathlib.Path(studio_out).resolve()
    else:
        out_path = pathlib.Path(f"D:/Projects/video-studio/{profile}/{slug}-full")

    to_studio_script = KIT / "tools" / "to_studio.py"
    cmd = [sys.executable, "-X", "utf8", str(to_studio_script), str(clip_dir), str(out_path)]
    print(f"  Thực thi: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"✅ Hoàn tất chuyển giao sang Studio: {out_path}")
