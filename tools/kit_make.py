"""kit make: Một lệnh tạo video marketing demo sản phẩm hoàn chỉnh từ web URL.

Cách dùng:
  python tools/kit_make.py <url> --goal "..." --out <clip_dir> [--profile stradevn] [--len 90] [--loop]
         [--model agy:gemini-3.8-flash-high|codex|claude:sonnet] [--from STAGE] [--only STAGE]
"""
import argparse
import pathlib
import sys

# Đảm bảo UTF-8 trên Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(KIT / "tools"))

from make.stages import (
    scaffold_clip,
    stage_discover,
    stage_brief,
    stage_shots,
    stage_record,
    stage_voice,
    stage_sources,
    stage_story,
    stage_build,
    stage_render,
    stage_studio,
)
from make.state import ALL_STAGES, RunState


def main():
    parser = argparse.ArgumentParser(
        description="Một lệnh tạo video demo marketing tự động bằng AI (kit make)."
    )
    parser.add_argument("url", nargs="?", default="", help="Địa chỉ webapp cần làm video demo")
    parser.add_argument("--goal", default="", help="Mục tiêu nội dung và thông điệp video")
    parser.add_argument("--out", required=True, help="Thư mục xuất dự án clip")
    parser.add_argument("--profile", default="stradevn", help="Hồ sơ thương hiệu (mặc định: stradevn)")
    parser.add_argument("--len", type=int, default=90, help="Thời lượng mục tiêu (giây, mặc định 90)")
    parser.add_argument("--loop", action="store_true", help="Kích hoạt loop hook (khung kết nối vòng vào khung đầu)")
    parser.add_argument(
        "--model",
        default="agy:gemini-3.8-flash-high",
        help="Mô hình LLM điều khiển: agy:gemini-3.8-flash-high | codex | claude:sonnet",
    )
    parser.add_argument("--from", dest="from_stage", choices=ALL_STAGES, help="Bắt đầu chạy từ công đoạn chỉ định")
    parser.add_argument("--only", dest="only_stage", choices=ALL_STAGES, help="Chỉ chạy duy nhất công đoạn chỉ định")
    parser.add_argument("--studio-out", default=None, help="Thư mục xuất cho dự án HyperFrames Studio")
    parser.add_argument("--cdp", type=int, default=9333, help="Cổng Chrome DevTools Protocol để khảo sát/quay")

    args = parser.parse_args()

    clip_dir = pathlib.Path(args.out).resolve()
    clip_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo hoặc nạp trạng thái thực thi run.json
    state = RunState(clip_dir)
    state.init_if_new(
        url=args.url,
        goal=args.goal,
        profile=args.profile,
        len_sec=args.len,
        loop=args.loop,
        model=args.model,
    )

    # Lấy thông tin cấu hình từ state nếu người dùng không truyền lại
    url = args.url or state.data.get("url", "")
    goal = args.goal or state.data.get("goal", "")
    profile = args.profile or state.data.get("profile", "stradevn")
    loop = args.loop if args.loop else state.data.get("loop", False)
    len_sec = args.len or state.data.get("len", 90)
    model_spec = args.model or state.data.get("model", "agy:gemini-3.8-flash-high")

    # Khởi tạo scaffold cơ bản cho clip
    scaffold_clip(clip_dir, profile=profile, goal=goal)

    # Xác định danh sách công đoạn cần chạy
    try:
        stages_to_run = state.determine_stages_to_run(
            from_stage=args.from_stage, only_stage=args.only_stage
        )
    except ValueError as e:
        print(f"❌ Lỗi tham số: {e}", file=sys.stderr)
        sys.exit(2)

    if not stages_to_run:
        print(f"✨ Toàn bộ các công đoạn của clip tại {clip_dir} đã hoàn thành (xem run.json).")
        return

    print("=" * 70)
    print("🎬 KIT MAKE: BẮT ĐẦU QUY TRÌNH SẢN XUẤT VIDEO DEMO")
    print(f"   URL:     {url or '(chưa cung cấp)'}")
    print(f"   Goal:    {goal}")
    print(f"   Profile: {profile} | Model: {model_spec} | Loop: {loop}")
    print(f"   Thư mục: {clip_dir}")
    print(f"   Công đoạn sẽ chạy: {' → '.join(stages_to_run)}")
    print("=" * 70)

    for stage in stages_to_run:
        state.start_stage(stage)
        try:
            if stage == "discover":
                stage_discover(clip_dir, url=url, cdp_port=args.cdp)
            elif stage == "brief":
                stage_brief(clip_dir, model_spec=model_spec, goal=goal, loop=loop, len_sec=len_sec)
            elif stage == "shots":
                stage_shots(clip_dir, model_spec=model_spec)
            elif stage == "record":
                stage_record(clip_dir)
            elif stage == "voice":
                stage_voice(clip_dir)
            elif stage == "sources":
                stage_sources(clip_dir, model_spec=model_spec)
            elif stage == "story":
                stage_story(clip_dir, model_spec=model_spec)
            elif stage == "build":
                stage_build(clip_dir)
            elif stage == "render":
                stage_render(clip_dir)
            elif stage == "studio":
                stage_studio(clip_dir, studio_out=args.studio_out)

            state.finish_stage(stage)
            print(f"✅ Hoàn tất công đoạn: {stage}")

        except Exception as e:
            state.fail_stage(stage, error=str(e))
            print("\n" + "!" * 70, file=sys.stderr)
            print(f"❌ DỪNG LẠI TẠI CÔNG ĐOẠN '{stage}': {e}", file=sys.stderr)
            print(f"   Xem trạng thái chi tiết tại: {clip_dir / 'run.json'}", file=sys.stderr)
            print("!" * 70 + "\n", file=sys.stderr)
            sys.exit(1)

    print("\n" + "=" * 70)
    print(f"🎉 TẤT CẢ CÔNG ĐOẠN ĐÃ HOÀN TẤT CHO CLIP: {clip_dir.name}")
    print(f"   Đường dẫn dự án: {clip_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
