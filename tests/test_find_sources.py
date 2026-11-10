import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock

_agent_tmp = Path("D:/agent-cache/SRC2/tmp")
try:
    _agent_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = str(_agent_tmp)
    os.environ["TEMP"] = str(_agent_tmp)
    tempfile.tempdir = str(_agent_tmp)
except Exception:
    pass

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import find_sources as fs
import comfy_image


@pytest.fixture
def need():
    return dict(id="whoosh", scene="S1", kind="sfx", query_en="whoosh", query_vi="vút", n=5)


def reply(data):
    r = Mock()
    r.json.return_value = data
    return r


def test_ranking_priority_duration_orientation(need):
    need.update(max_dur=3, orientation="portrait")
    items = [fs.candidate("pexels", "whoosh", "https://p", width=100, height=200),
             fs.candidate("openverse", "whoosh", "https://o", width=200, height=100),
             fs.candidate("local_audio", "whoosh", "local", duration=2),
             fs.candidate("local_audio", "long", "long", duration=4),
             fs.candidate("openverse", "whoosh", "https://o")]
    ranked = fs.rank_candidates(items, need)
    assert [x["source"] for x in ranked] == ["local_audio", "openverse", "pexels"]
    assert [x["rank"] for x in ranked] == [1, 2, 3]


def test_openverse_commercial_filter(monkeypatch, need):
    mock = Mock(return_value=reply({"results": [
        dict(title="yes", url="https://a", license="by", duration=1500),
        dict(title="no", url="https://b", license="by-nc"),
        dict(title="unknown", url="https://c", license="")]}))
    monkeypatch.setattr(fs.requests, "get", mock)
    hits = fs.openverse(need)
    assert len(hits) == 1 and hits[0]["duration"] == 1.5
    assert mock.call_args.kwargs["params"]["license_type"] == "commercial"
    assert mock.call_args.kwargs["timeout"] == fs.TIMEOUT
    assert "User-Agent" in mock.call_args.kwargs["headers"]


def test_empty_keys_skip_http(monkeypatch, need):
    mock = Mock(side_effect=AssertionError("HTTP không được gọi"))
    monkeypatch.setattr(fs.requests, "get", mock)
    for kind in ("sfx", "broll_video", "broll_image"):
        need["kind"] = kind
        assert list(fs.keyed(need, dict(pexels_api_key="", pixabay_api_key="", freesound_api_key=""))) == []
    mock.assert_not_called()


def test_fetch_download_and_local_credits(tmp_path, monkeypatch):
    (tmp_path / "sources").mkdir()
    local = tmp_path / "original.wav"
    local.write_bytes(b"local")
    groups = [dict(id="local", candidates=[dict(fs.candidate("local_audio", "Local", str(local),
              license="CC0", attribution="Creator", local_path=str(local)), rank=1)]),
              dict(id="web", candidates=[dict(fs.candidate("openverse", "Web", "https://example.org/a.mp3",
              "https://example.org/page", license="CC BY", attribution="Author"), rank=2)])]
    (tmp_path / "sources/candidates.json").write_text(json.dumps(groups))
    response = reply({})
    response.iter_content.return_value = [b"audio", b"data"]
    monkeypatch.setattr(fs.requests, "get", Mock(return_value=response))
    fs.fetch(tmp_path, ["local:1", "web:2"])
    assert (tmp_path / "assets/src/local.wav").read_bytes() == b"local"
    assert (tmp_path / "assets/src/web.mp3").read_bytes() == b"audiodata"
    credits = (tmp_path / "sources/credits.md").read_text(encoding="utf-8")
    assert all(t in credits for t in ("CC0", "Creator", "CC BY", "Author", "https://example.org/page"))
    assert local.read_bytes() == b"local"
    response.close.assert_called_once()
    with pytest.raises(ValueError):
        fs.fetch(tmp_path, ["../escape:1"])


def test_wikimedia_video_mime_metadata(monkeypatch, need):
    need.update(kind="broll_video", query_en="container ship")
    mock = Mock(return_value=reply({"query": {"pages": {"1": {"title": "File:Ship.webm", "imageinfo": [{
        "mime": "video/webm", "url": "https://example.org/ship.webm", "width": 1920, "height": 1080,
        "extmetadata": {"LicenseShortName": {"value": "CC BY-SA"}, "Artist": {"value": "<b>Sailor</b>"}}}]},
        "2": {"title": "File:Ship.jpg", "imageinfo": [{"mime": "image/jpeg"}]}}}}))
    monkeypatch.setattr(fs.requests, "get", mock)
    hits = fs.wikimedia(need)
    assert len(hits) == 1 and hits[0]["orientation"] == "landscape"
    assert "Sailor" in hits[0]["attribution"]
    assert "filetype:video" in mock.call_args.kwargs["params"]["gsrsearch"]


def test_local_bilingual_search(tmp_path, need):
    lib = tmp_path / "audio-library"
    lib.mkdir()
    (lib / "whoosh.wav").write_bytes(b"a")
    (lib / "catalog.json").write_text(json.dumps([dict(path="whoosh.wav", kind="sfx", license="CC0", duration=1)]))
    assert fs.local_search(need, tmp_path)[0]["local_path"] == str(lib / "whoosh.wav")


def test_provider_failure_persists_candidates(tmp_path, monkeypatch, need):
    (tmp_path / "sources.json").write_text(json.dumps([need]))
    monkeypatch.setattr(fs.requests, "get", Mock(side_effect=requests.Timeout()))
    groups = fs.find(tmp_path, {}, kit=tmp_path)
    assert groups[0]["errors"] and not groups[0]["candidates"]
    assert (tmp_path / "sources/candidates.json").exists()


def test_comfy_workflow_poll_view(tmp_path, monkeypatch):
    workflow = tmp_path / "workflow.json"
    workflow.write_text(json.dumps({"1": {"class_type": "QwenImage", "inputs": {
        "text": "{{prompt}}", "width": "{{width}}", "height": "{{height}}", "seed": "{{seed}}"}}}))
    post = Mock(return_value=reply({"prompt_id": "abc"}))
    monkeypatch.setattr(comfy_image.requests, "post", post)
    view = Mock(content=b"png")
    get = Mock(side_effect=[reply({"abc": {"outputs": {"2": {"images": [{"filename": "a.png", "type": "output"}]}}}}), view])
    monkeypatch.setattr(comfy_image, "get", get)
    out = tmp_path / "out.png"
    comfy_image.render('pepper "close up"', out, dict(comfyui_url="http://localhost:8188", comfyui_workflow=str(workflow)), seed=7)
    inputs = post.call_args.kwargs["json"]["prompt"]["1"]["inputs"]
    assert inputs == dict(text='pepper "close up"', width=1344, height=768, seed=7)
    assert out.read_bytes() == b"png"


@pytest.mark.parametrize("provider,kind,config,payload", [
    ("pexels", "broll_video", {"pexels_api_key": "test"}, {"videos": [{
        "url": "https://pexels.com/video/1", "image": "https://poster", "duration": 4,
        "video_files": [{"file_type": "video/mp4", "link": "https://clip.mp4", "width": 1280, "height": 720}]}]}),
    ("pixabay", "broll_video", {"pixabay_api_key": "test"}, {"hits": [{
        "pageURL": "https://pixabay.com/video/1", "videos": {
            "large": {"url": "", "size": 0},
            "medium": {"url": "https://clip.mp4", "width": 1920, "height": 1080, "thumbnail": "https://poster"}}}]}),
    ("freesound", "sfx", {"freesound_api_key": "test"}, {"results": [{
        "name": "whoosh", "url": "https://freesound.org/1", "license": "CC0", "username": "Creator",
        "duration": 1, "previews": {"preview-hq-mp3": "https://clip.mp3"}}]})])
def test_keyed_provider_shapes(monkeypatch, need, provider, kind, config, payload):
    need["kind"] = kind
    monkeypatch.setattr(fs.requests, "get", Mock(return_value=reply(payload)))
    name, search = next(fs.keyed(need, config))
    hits = search()
    assert name == provider and len(hits) == 1
    assert hits[0]["source"] == provider and hits[0]["file_url"].startswith("https://clip")
    if kind == "broll_video":
        assert hits[0]["preview_url"] == "https://poster"
        assert hits[0]["orientation"] == "landscape"


def test_visual_sheet_downloads_preview(tmp_path, monkeypatch):
    import io
    from PIL import Image
    raw = io.BytesIO()
    Image.new("RGB", (20, 10), "red").save(raw, format="PNG")
    response = reply({})
    response.content = raw.getvalue()
    http = Mock(return_value=response)
    monkeypatch.setattr(fs.requests, "get", http)
    (tmp_path / "sources").mkdir()
    item = dict(fs.candidate("wikimedia", "Ship", "https://original.webm", preview_url="https://poster.jpg"), rank=1)
    fs.contact_sheet(tmp_path, [dict(id="ship", kind="broll_video", candidates=[item])])
    with Image.open(tmp_path / "sources/contact-sheet.jpg") as sheet:
        assert sheet.size == (960, 220)
        assert sheet.getpixel((5, 5))[0] > 200
    assert http.call_args.args[0] == "https://poster.jpg"


def test_meme_searches_only_kit_library(tmp_path, monkeypatch):
    lib = tmp_path / "meme-library"
    lib.mkdir()
    (lib / "catalog.json").write_text(json.dumps({
        "items": [{"id": "noto/alarm", "file": "noto/alarm.webm", "poster": "noto/alarm.png", "tags": ["báo thức", "alarm"]}]
    }), encoding="utf-8")
    (lib / "web.json").write_text(json.dumps({
        "items": [{"id": "cat-shocked", "url": "https://example.org/cat.mp4", "tags": ["cat", "mèo"]}]
    }), encoding="utf-8")

    meme_need = dict(id="m1", scene="S1", kind="meme", query_en="alarm", query_vi="báo thức", n=5)

    assert fs.openverse(meme_need) == []
    assert fs.wikimedia(meme_need) == []
    assert list(fs.keyed(meme_need, {"pexels_api_key": "k1", "pixabay_api_key": "k2"})) == []

    http_get = Mock(side_effect=AssertionError("External HTTP should not be called for kind=meme"))
    monkeypatch.setattr(fs.requests, "get", http_get)

    project = tmp_path / "project"
    project.mkdir()
    (project / "sources.json").write_text(json.dumps([meme_need]), encoding="utf-8")

    groups = fs.find(project, {"pexels_api_key": "k1", "pixabay_api_key": "k2"}, kit=tmp_path)
    assert len(groups) == 1
    assert all(c["source"] == "local_meme" for c in groups[0]["candidates"])
    assert groups[0]["errors"] == []


def test_get_font_fallback(tmp_path):
    import shutil
    from PIL import ImageFont
    font_file = tmp_path / "assets/fonts/custom.ttf"
    font_file.parent.mkdir(parents=True)
    real_font = Path("C:/Windows/Fonts/arial.ttf")
    if real_font.is_file():
        shutil.copy2(real_font, font_file)
        f = fs.get_font(size=12, kit=tmp_path, font_candidates=[Path("nonexistent.ttf"), font_file])
        assert isinstance(f, ImageFont.FreeTypeFont)

    f_def = fs.get_font(size=12, kit=tmp_path, font_candidates=[Path("nonexistent.ttf")])
    assert f_def is not None


def test_vietnamese_contact_sheet_text(tmp_path):
    from PIL import Image
    (tmp_path / "sources").mkdir(parents=True, exist_ok=True)
    item = dict(fs.candidate("local_meme", "Đúng này, tất cả đều đúng, hợp lý", ""), rank=1)
    fs.contact_sheet(tmp_path, [dict(id="meme", kind="meme", candidates=[item])])
    sheet_path = tmp_path / "sources/contact-sheet.jpg"
    assert sheet_path.is_file()
    with Image.open(sheet_path) as img:
        assert img.size[0] == 960


def test_broll_video_hint_printed(tmp_path, capsys):
    need = dict(id="ship", scene="S1", kind="broll_video", query_en="ship", query_vi="tàu", n=1)
    (tmp_path / "sources.json").write_text(json.dumps([need]), encoding="utf-8")
    fs.find(tmp_path, {}, kit=tmp_path)
    captured = capsys.readouterr()
    assert "pexels_api_key hoặc pixabay_api_key" in captured.out


def test_meme_preview_caching(tmp_path, monkeypatch):
    import io
    from PIL import Image
    lib = tmp_path / "meme-library"
    lib.mkdir()
    (lib / "catalog.json").write_text(json.dumps({"items": []}), encoding="utf-8")
    (lib / "web.json").write_text(json.dumps({
        "items": [{"id": "thumb-meme", "url": "https://example.org/video.mp4", "thumbnail": "https://example.org/thumb.jpg", "tags": ["thumb"]}]
    }), encoding="utf-8")
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "sources.json").write_text(json.dumps([
        {"id": "m_thumb", "scene": "S1", "kind": "meme", "query_en": "thumb", "query_vi": "thumb", "n": 1}
    ]), encoding="utf-8")

    raw = io.BytesIO()
    Image.new("RGB", (50, 50), "blue").save(raw, format="JPEG")
    res = Mock(status_code=200, content=raw.getvalue())
    monkeypatch.setattr(fs.requests, "get", Mock(return_value=res))

    groups = fs.find(proj, {}, kit=tmp_path)
    preview_file = proj / "sources/previews/thumb-meme.jpg"
    assert preview_file.is_file()
    assert groups[0]["candidates"][0]["preview_url"] == str(preview_file)
