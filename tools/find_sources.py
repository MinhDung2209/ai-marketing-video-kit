"""Tìm nguồn cho sources.json; chỉ tải bản gốc khi chọn --fetch ID:HẠNG."""
import argparse
import html
import io
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata
from urllib.parse import urlparse

import requests

KIT = Path(__file__).resolve().parents[1]
UA = "VideoKitSourceFinder/1.0 (asset research; Python requests)"
TIMEOUT = (10, 35)


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def get(url, **kwargs):
    response = requests.get(url, headers={"User-Agent": UA, **kwargs.pop("headers", {})},
                            timeout=TIMEOUT, **kwargs)
    response.raise_for_status()
    return response


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", str(text).lower())
                   if unicodedata.category(c) != "Mn").replace("đ", "d")


def clean(text):
    return html.unescape(re.sub(r"<[^>]+>", "", str(text or ""))).strip()


def candidate(source, title, file_url, page_url="", preview_url="", license="", attribution="",
              duration=None, width=None, height=None, size=None, local_path=None):
    return dict(source=source, title=clean(title), page_url=page_url, file_url=file_url,
                preview_url=preview_url, license=clean(license) or "Chưa rõ — kiểm tra trang nguồn",
                attribution=clean(attribution), duration=duration, width=width, height=height,
                size=size, orientation=("portrait" if height > width else "landscape")
                if width and height else None, local_path=local_path)


def local_search(need, kit=KIT, project=None):
    """Cùng phép khớp path/note (sfx_search) và id/tags bỏ dấu (meme_search)."""
    result = []
    queries = [fold(need.get(k, "")) for k in ("query_en", "query_vi") if need.get(k)]
    if need["kind"] in ("sfx", "bgm"):
        for item in read_json(kit / "audio-library/catalog.json", []):
            hay = fold(item["path"] + " " + (item.get("note") or ""))
            if item["kind"] == need["kind"] and any(all(t in hay for t in q.split()) for q in queries):
                path = kit / "audio-library" / item["path"]
                if path.is_file():
                    result.append(candidate("local_audio", item["path"], str(path),
                                            item.get("source_url", ""), license=item.get("license"),
                                            attribution=item.get("attribution") or item.get("source", ""),
                                            duration=item.get("duration"), size=path.stat().st_size,
                                            local_path=str(path)))
    if need["kind"] == "meme":
        previews_dir = (project / "sources/previews") if project is not None else None
        if previews_dir is not None:
            previews_dir.mkdir(parents=True, exist_ok=True)
        for name in ("catalog.json", "web.json"):
            for item in read_json(kit / "meme-library" / name, {}).get("items", []):
                hay = fold(item["id"] + " " + " ".join(item.get("tags", [])))
                if not any(q in hay for q in queries):
                    continue
                path = kit / "meme-library" / item.get("file", "__missing__")
                poster = kit / "meme-library" / item.get("poster", "__missing__")
                preview_url = str(poster) if poster.is_file() else item.get("thumbnail", "")
                if previews_dir is not None:
                    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", item["id"])
                    if name == "catalog.json":
                        preview_path = previews_dir / f"{safe_id}.png"
                        if not (preview_path.is_file() and preview_path.stat().st_size > 0):
                            if path.is_file():
                                subprocess.run(["ffmpeg", "-y", "-i", str(path), "-vframes", "1", str(preview_path)],
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                                if not (preview_path.is_file() and preview_path.stat().st_size > 0):
                                    subprocess.run(["ffmpeg", "-y", "-ss", "0.1", "-i", str(path), "-vframes", "1", str(preview_path)],
                                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                            if not (preview_path.is_file() and preview_path.stat().st_size > 0) and poster.is_file():
                                shutil.copy2(poster, preview_path)
                        if preview_path.is_file() and preview_path.stat().st_size > 0:
                            preview_url = str(preview_path)
                    else:  # web.json
                        preview_path = previews_dir / f"{safe_id}.jpg"
                        if not (preview_path.is_file() and preview_path.stat().st_size > 0):
                            thumb = item.get("thumbnail")
                            if thumb:
                                try:
                                    if thumb.startswith("http://") or thumb.startswith("https://"):
                                        res = requests.get(thumb, headers={"User-Agent": UA}, timeout=TIMEOUT)
                                        if res.status_code == 200:
                                            preview_path.write_bytes(res.content)
                                    elif Path(thumb).is_file():
                                        shutil.copy2(thumb, preview_path)
                                except Exception:
                                    pass
                            url = item.get("url", "")
                            if not (preview_path.is_file() and preview_path.stat().st_size > 0) and url:
                                try:
                                    subprocess.run(["ffmpeg", "-y", "-ss", "0.5", "-i", url, "-vframes", "1", str(preview_path)],
                                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                                except Exception:
                                    pass
                                if not (preview_path.is_file() and preview_path.stat().st_size > 0):
                                    try:
                                        subprocess.run(["ffmpeg", "-y", "-i", url, "-vframes", "1", str(preview_path)],
                                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                                    except Exception:
                                        pass
                                if not (preview_path.is_file() and preview_path.stat().st_size > 0):
                                    try:
                                        subprocess.run(["ffmpeg", "-y", "-i", url, "-filter_complex", "showwavespic=s=310x170:colors=0x4f46e5", "-frames:v", "1", str(preview_path)],
                                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                                    except Exception:
                                        pass
                        if preview_path.is_file() and preview_path.stat().st_size > 0:
                            preview_url = str(preview_path)
                result.append(candidate("local_meme", item.get("title", item["id"]),
                                        str(path) if path.is_file() else item.get("url", ""),
                                        item.get("page", item.get("source_url", "")),
                                        preview_url, item.get("license"),
                                        item.get("attribution", item.get("source", "")),
                                        item.get("duration", item.get("dur")),
                                        local_path=str(path) if path.is_file() else None))
    return result


def openverse(need):
    if need["kind"] in ("broll_video", "meme"):
        return []
    kind = "audio" if need["kind"] in ("sfx", "bgm") else "images"
    data = get(f"https://api.openverse.org/v1/{kind}/", params={
        "q": need["query_en"], "license_type": "commercial", "page_size": min(50, need.get("n", 5) * 3)}).json()
    result = []
    for item in data.get("results", []):
        lic = item.get("license", "").lower()
        # Defense in depth: do not trust cached/provider-side filtering of NC licenses.
        if not lic or "nc" in lic:
            continue
        result.append(candidate("openverse", item.get("title", ""), item["url"],
                                item.get("foreign_landing_url", ""), item.get("thumbnail", ""),
                                f"{lic} {item.get('license_version', '')} {item.get('license_url', '')}",
                                item.get("attribution") or item.get("creator", ""),
                                item.get("duration") / 1000 if item.get("duration") is not None else None,
                                item.get("width"), item.get("height"), item.get("filesize")))
    return result


def wikimedia(need):
    if need["kind"] in ("sfx", "bgm", "meme"):
        return []
    video = need["kind"] == "broll_video"
    data = get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": need["query_en"] + (" filetype:video" if video else " filetype:bitmap"),
        "gsrlimit": min(50, need.get("n", 5) * 3), "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 360}).json()
    result = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [{}])[0]
        if not info.get("mime", "").startswith("video/" if video else "image/"):
            continue
        meta = info.get("extmetadata", {})
        value = lambda k: clean(meta.get(k, {}).get("value", ""))
        result.append(candidate("wikimedia", page["title"], info["url"], info.get("descriptionurl", ""),
                                info.get("thumburl", ""), value("LicenseShortName") + " " + value("LicenseUrl"),
                                value("Artist") + " / " + value("Credit"), info.get("duration"),
                                info.get("width"), info.get("height"), info.get("size")))
    return result


def keyed(need, config):
    """Yield separate providers so one failed API does not suppress another."""
    video = need["kind"] == "broll_video"
    visual = need["kind"] in ("broll_video", "broll_image")
    q = need["query_en"]
    if visual and config.get("pexels_api_key"):
        def pexels():
            data = get("https://api.pexels.com/" + ("videos/search" if video else "v1/search"),
                       headers={"Authorization": config["pexels_api_key"]}, params={"query": q, "per_page": 15}).json()
            out = []
            for x in data.get("videos" if video else "photos", []):
                files = [f for f in x.get("video_files", []) if f.get("file_type") == "video/mp4"]
                if video and not files:
                    continue
                f = max(files, key=lambda f: (f.get("width") or 0)) if video else {}
                out.append(candidate("pexels", x.get("alt") or q, f.get("link") if video else x["src"]["original"],
                                     x["url"], x.get("image") if video else x["src"]["medium"],
                                     "Pexels License https://www.pexels.com/license/",
                                     x.get("user", {}).get("name", "") if video else x.get("photographer", ""),
                                     x.get("duration"), f.get("width", x.get("width")), f.get("height", x.get("height"))))
            return out
        yield "pexels", pexels
    if visual and config.get("pixabay_api_key"):
        def pixabay():
            data = get("https://pixabay.com/api/" + ("videos/" if video else ""),
                       params={"key": config["pixabay_api_key"], "q": q, "per_page": 15}).json()
            out = []
            for x in data.get("hits", []):
                renditions = [r for r in x.get("videos", {}).values() if r.get("url")]
                f = max(renditions, key=lambda r: r.get("width", 0), default={}) if video else {}
                out.append(candidate("pixabay", x.get("tags", q), f.get("url") if video else x.get("largeImageURL"),
                                     x["pageURL"], f.get("thumbnail", "") if video else x.get("previewURL", ""),
                                     "Pixabay Content License https://pixabay.com/service/license-summary/", x.get("user", ""),
                                     x.get("duration"), f.get("width", x.get("imageWidth")),
                                     f.get("height", x.get("imageHeight")), f.get("size", x.get("imageSize"))))
            return out
        yield "pixabay", pixabay
    if need["kind"] == "sfx" and config.get("freesound_api_key"):
        def freesound():
            data = get("https://freesound.org/apiv2/search/text/", headers={
                "Authorization": "Token " + config["freesound_api_key"]}, params={"query": q,
                "filter": 'license:("Creative Commons 0" OR "Attribution")',
                "fields": "id,name,url,previews,license,username,duration", "page_size": 15}).json()
            return [candidate("freesound", x["name"], x.get("previews", {}).get("preview-hq-mp3", ""),
                              x["url"], x.get("previews", {}).get("preview-lq-mp3", ""),
                              x["license"], x["username"], x.get("duration")) for x in data.get("results", [])]
        yield "freesound", freesound


def rank_candidates(items, need):
    priority = {"local_audio": 0, "local_meme": 0, "openverse": 1, "wikimedia": 1}
    filtered, seen = [], set()
    for item in items:
        if not item["file_url"] or item["file_url"] in seen:
            continue
        if need.get("max_dur") is not None and item.get("duration") is not None and item["duration"] > need["max_dur"]:
            continue
        seen.add(item["file_url"])
        filtered.append(item)
    terms = fold(need["query_en"]).split()
    filtered.sort(key=lambda x: (priority.get(x["source"], 2),
                                 bool(need.get("orientation") and x.get("orientation") != need["orientation"]),
                                 -sum(t in fold(x["title"]) for t in terms)))
    for i, item in enumerate(filtered[:need.get("n", 5)], 1):
        item["rank"] = i
    return filtered[:need.get("n", 5)]


def get_font(size=14, kit=KIT, font_candidates=None):
    from PIL import ImageFont
    if font_candidates is None:
        kit_fonts = list((kit / "assets/fonts").glob("*.ttf")) if (kit / "assets/fonts").is_dir() else []
        font_candidates = [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            *kit_fonts,
        ]
    for p in font_candidates:
        try:
            cand = Path(p)
            if cand.is_file():
                return ImageFont.truetype(str(cand), size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def contact_sheet(project, groups, kit=KIT):
    from PIL import Image, ImageDraw, ImageOps
    visuals = [(g["id"], x) for g in groups if g["kind"] not in ("sfx", "bgm") for x in g["candidates"]]
    if not visuals:
        return
    sheet = Image.new("RGB", (960, 220 * ((len(visuals) + 2) // 3)), "#eeeeee")
    draw = ImageDraw.Draw(sheet)
    font = get_font(size=13, kit=kit)
    for i, (ident, item) in enumerate(visuals):
        x, y = i % 3 * 320, i // 3 * 220
        preview = item.get("preview_url")
        try:
            if preview:
                raw = Path(preview).read_bytes() if Path(preview).is_file() else get(preview).content
                with Image.open(io.BytesIO(raw)) as img:
                    sheet.paste(ImageOps.contain(img.convert("RGB"), (310, 170)), (x, y))
        except (OSError, ValueError, requests.RequestException):
            pass
        label = f"{ident} #{item['rank']} {item['source']}\n{item['title'][:45]}"
        draw.text((x + 4, y + 175), label, fill="black", font=font)
    sheet.save(project / "sources/contact-sheet.jpg", quality=88)


def command(args):
    return subprocess.list2cmdline([str(a) for a in args])


def find(project, config, kit=KIT):
    needs = read_json(project / "sources.json")
    if not isinstance(needs, list):
        raise ValueError("sources.json phải là danh sách nhu cầu")
    ids = set()
    for need in needs:
        ident = need.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", ident) or ident in ids:
            raise ValueError("id phải duy nhất, chỉ gồm chữ ASCII, số, _ hoặc -")
        ids.add(ident)
        if need.get("kind") not in ("sfx", "bgm", "broll_video", "broll_image", "meme"):
            raise ValueError(f"{ident}: kind không hợp lệ")
        if not need.get("query_en") or not need.get("query_vi") or "scene" not in need:
            raise ValueError(f"{ident}: thiếu scene/query_en/query_vi")
        if not isinstance(need.get("n", 5), int) or not 1 <= need.get("n", 5) <= 50:
            raise ValueError("n phải từ 1 đến 50")
        if need.get("orientation") not in (None, "portrait", "landscape"):
            raise ValueError("orientation phải là portrait hoặc landscape")
        if need.get("max_dur") is not None and (not isinstance(need["max_dur"], (int, float)) or need["max_dur"] <= 0):
            raise ValueError("max_dur phải là số giây lớn hơn 0")
    groups = []
    for need in needs:
        items = local_search(need, kit, project=project)
        errors = []
        if need["kind"] == "meme":
            providers = []
        else:
            providers = [("openverse", lambda: openverse(need)), ("wikimedia", lambda: wikimedia(need)), *keyed(need, config)]
        for name, search in providers:
            try:
                hits = search()
                items.extend(hits)
                print(f"{need['id']}: {name} — {len(hits)} kết quả")
            except (requests.RequestException, ValueError, KeyError) as exc:
                # Do not print request URLs: optional API keys can occur in the query string.
                message = f"{name}: không truy cập được ({type(exc).__name__})"
                errors.append(message)
                print(f"{need['id']}: {message}")
        ranked = rank_candidates(items, need)
        group = {**need, "candidates": ranked, "errors": errors, "suggestions": []}
        dest = project / "assets/src" / need["id"]
        if need["kind"] == "bgm":
            group["suggestions"].append(command(["python", kit / "tools/lyria_bgm.py", need["query_en"], dest.with_suffix(".wav")]))
        if need["kind"] == "broll_image" and config.get("comfyui_url"):
            w, h = (768, 1344) if need.get("orientation") == "portrait" else (1344, 768)
            group["suggestions"].append(command(["python", kit / "tools/comfy_image.py", need["query_en"], dest.with_suffix(".png"), "--width", w, "--height", h, "--seed", 42]))
        print(f"{need['id']}: chọn {len(ranked)} ứng viên")
        for item in ranked:
            print(f"  #{item['rank']} [{item['source']}] {item['title']} | {item['license']}")
        for suggestion in group["suggestions"]:
            print("  Gợi ý tạo: " + suggestion)
        if need["kind"] == "broll_video" and not (config.get("pexels_api_key") or config.get("pixabay_api_key")):
            print("  Gợi ý: Điền pexels_api_key hoặc pixabay_api_key trong config.json để có video stock thật từ Pexels/Pixabay.")
        if need["kind"] in ("sfx", "bgm"):
            paths = [x["local_path"] for x in ranked if x.get("local_path")]
            print("  Nghe thử: " + command(["python", kit / "tools/sfx_audition.py", project / "sources" / (need["id"] + "-audition.mp3"), *(paths or [dest.with_suffix(".mp3")])]))
            print("  Nguồn mạng: --fetch ID:HẠNG trước, rồi dùng đường dẫn file đã tải để nghe thử.")
        groups.append(group)
    (project / "sources").mkdir(parents=True, exist_ok=True)
    (project / "assets/src").mkdir(parents=True, exist_ok=True)
    (project / "sources/candidates.json").write_text(json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8")
    contact_sheet(project, groups, kit=kit)
    return groups


def fetch(project, selections):
    groups = read_json(project / "sources/candidates.json", [])
    chosen = []
    for selection in selections:
        ident, rank = selection.rsplit(":", 1)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", ident):
            raise ValueError("id không hợp lệ")
        item = next((x for g in groups if g["id"] == ident for x in g["candidates"] if x["rank"] == int(rank)), None)
        if item is None:
            raise ValueError(f"Không có ứng viên {selection}")
        chosen.append((ident, item))
    dst = project / "assets/src"
    dst.mkdir(parents=True, exist_ok=True)
    (project / "sources").mkdir(parents=True, exist_ok=True)
    for ident, item in chosen:
        response = None
        if not item.get("local_path"):
            response = get(item["file_url"], stream=True)
        suffix = Path(urlparse(item["file_url"]).path).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{2,5}", suffix):
            suffix = mimetypes.guess_extension(response.headers.get("Content-Type", "").split(";")[0]) if response is not None else None
            suffix = suffix or ".bin"
        target = dst / (ident + suffix)
        partial = target.with_suffix(target.suffix + ".part")
        try:
            if item.get("local_path"):
                shutil.copy2(item["local_path"], partial)
            else:
                with partial.open("wb") as handle:
                    for chunk in response.iter_content(1024 * 256):
                        handle.write(chunk)
            partial.replace(target)
        finally:
            if response is not None:
                response.close()
            partial.unlink(missing_ok=True)
        with (project / "sources/credits.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\n- {ident}: {clean(item['title'])}\n  - File: assets/src/{target.name}\n"
                         f"  - Nguồn: {item['source']} — {item['page_url'] or item['file_url']}\n"
                         f"  - Giấy phép: {item['license']}\n  - Ghi công: {item['attribution']}\n")
        print(f"Đã lưu {target}; đã ghi sources/credits.md")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--fetch", nargs="+", metavar="ID:HẠNG")
    args = parser.parse_args(argv)
    try:
        if args.fetch:
            fetch(args.project.resolve(), args.fetch)
        else:
            find(args.project.resolve(), read_json(KIT / "config.json", {}))
    except (OSError, ValueError, requests.RequestException) as exc:
        print(f"Lỗi tìm nguồn: {type(exc).__name__}: kiểm tra dữ liệu / kết nối.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
