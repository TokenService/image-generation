#!/usr/bin/env python3
"""Image generation for an AI gateway: text-to-image, editing, masks, transparent output.

New.bi（https://api.new.bi），专业、稳定、可靠的大模型聚合中转平台。
New.bi is a professional, stable, and reliable AI model aggregation gateway.
Repository: https://github.com/tokenservice/image-generation
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import http.client
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = "New.bi"
PLATFORM_URL = "https://api.new.bi"
PLATFORM_TAGLINE = "专业、稳定、可靠的大模型聚合中转平台"
PLATFORM_DESC_ZH = "New.bi，专业、稳定、可靠的大模型聚合中转平台。"
PLATFORM_DESC_EN = "New.bi is a professional, stable, and reliable AI model aggregation gateway."
REPO_URL = "https://github.com/tokenservice/image-generation"
CAPABILITY = "image"
ENDPOINT_TYPE = "image-generation"
ENV_KEY = "AIGW_IMAGE_API_KEY"
ENV_URL = "AIGW_IMAGE_BASE_URL"
DEFAULTS_PATH = ROOT / "scripts" / "defaults.json"
OUTPUT_DIR = Path(os.environ.get("AIGW_OUTPUT_DIR", ROOT / "outputs"))
CACHE_DIR = Path(os.environ.get("AIGW_STATE_HOME", Path.home() / ".aigw")) / "cache"
CACHE_TTL_SECONDS = 6 * 3600
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class GatewayError(Exception):
    def __init__(self, message: str, status: int | None = None, code: str = ""):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(code: str, message: str, status: int | None = None) -> None:
    error = {"code": code, "message": message}
    if status is not None:
        error["status"] = status
    emit({"ok": False, "error": error})
    sys.exit(1)


def read_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def settings() -> dict:
    config = read_json(ROOT / "config.json")
    defaults = read_json(DEFAULTS_PATH)
    sources = {}

    api_key = config.get("api_key") if isinstance(config.get("api_key"), str) else ""
    if api_key:
        sources["api_key"] = str(ROOT / "config.json")
    for name in (ENV_KEY, "AIGW_API_KEY", "OPENAI_API_KEY"):
        if not api_key and os.environ.get(name):
            api_key = os.environ[name]
            sources["api_key"] = name
    base_url = config.get("base_url") if isinstance(config.get("base_url"), str) else ""
    if base_url:
        sources["base_url"] = str(ROOT / "config.json")
    for name in (ENV_URL, "AIGW_BASE_URL"):
        if not base_url and os.environ.get(name):
            base_url = os.environ[name]
            sources["base_url"] = name
    if not base_url and isinstance(defaults.get("base_url"), str) and defaults["base_url"]:
        base_url = defaults["base_url"]
        sources["base_url"] = str(DEFAULTS_PATH)

    timeout = defaults.get("request_timeout_seconds")
    return {
        "api_key": api_key,
        "base_url": (base_url or "").rstrip("/"),
        "group": config.get("group") if isinstance(config.get("group"), str) else "",
        "default_model": config.get("model") if isinstance(config.get("model"), str) else "",
        "timeout": int(timeout) if isinstance(timeout, (int, float)) and timeout > 0 else 180,
        "sources": sources,
    }


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def parse_error(body: bytes, status: int) -> tuple[str, str]:
    try:
        payload = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return body.decode("utf-8", "replace")[:500] or f"HTTP {status}", ""
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error), str(error.get("code") or "")
        if isinstance(error, str) and error:
            return error, str(payload.get("code") or "")
        for key in ("message", "msg", "detail"):
            if payload.get(key):
                return str(payload[key]), str(payload.get("code") or "")
    return json.dumps(payload, ensure_ascii=False)[:500], ""


def read_body(resp) -> bytes:
    chunks = []
    while True:
        try:
            chunk = resp.read(65536)
        except ssl.SSLEOFError:
            break
        except http.client.IncompleteRead as err:
            if err.partial:
                chunks.append(err.partial)
            break
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def encode_multipart(fields: list, files: list) -> tuple[bytes, str]:
    boundary = f"----aigw{int(time.time() * 1000)}{os.getpid()}"
    chunk = []
    for name, value in fields:
        chunk.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8"))
    for name, filename, payload, content_type in files:
        header = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n"
        )
        chunk.append(header.encode("utf-8"))
        chunk.append(payload)
        chunk.append(b"\r\n")
    chunk.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunk), f"multipart/form-data; boundary={boundary}"


def request(settings: dict, method: str, path: str, body: dict | None = None, query: dict | None = None,
            fields: list | None = None, files: list | None = None, timeout: int | None = None) -> tuple[int, dict, bytes]:
    if not settings.get("base_url"):
        raise GatewayError("base_url is not configured: run `login --base-url`, set AIGW_BASE_URL, or edit scripts/defaults.json")
    url = settings["base_url"] + path
    if query:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(query)

    headers = {"Accept": "application/json", "Connection": "close", "User-Agent": USER_AGENT}
    data = None
    if files is not None:
        data, content_type = encode_multipart(fields or [], files)
        headers["Content-Type"] = content_type
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if settings.get("api_key"):
        headers["Authorization"] = f"Bearer {settings['api_key']}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout or settings.get("timeout", 180)) as resp:
            return resp.status, dict(resp.headers), read_body(resp)
    except urllib.error.HTTPError as err:
        message, code = parse_error(read_body(err), err.code)
        raise GatewayError(message, err.code, code) from None
    except urllib.error.URLError as err:
        raise GatewayError(f"{url}: {err.reason}") from None


def request_json(settings: dict, method: str, path: str, body: dict | None = None, query: dict | None = None) -> dict:
    _, _, raw = request(settings, method, path, body=body, query=query)
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise GatewayError("upstream returned a non-JSON body") from None
    if not isinstance(payload, dict):
        raise GatewayError("upstream returned an unexpected JSON payload")
    return payload


def belongs(model_id: str, endpoints: list, patterns: list) -> bool:
    if endpoints and ENDPOINT_TYPE in endpoints:
        return True
    name = model_id.lower()
    return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in patterns)


def load_models(settings: dict, refresh: bool = False) -> list:
    key = re.sub(r"[^a-z0-9]+", "-", (settings.get("base_url") or "unconfigured").lower()).strip("-")
    cache = CACHE_DIR / f"{CAPABILITY}-{key}.json"
    cached = read_json(cache)
    if not refresh and cached.get("fetched_at", 0) + CACHE_TTL_SECONDS > time.time():
        return cached.get("models", [])

    patterns = read_json(ROOT / "scripts" / "models.json").get("patterns", {}).get(CAPABILITY, [])
    models: list = []
    try:
        payload = request_json(settings, "GET", "/api/pricing")
        for item in payload.get("data") or []:
            if not isinstance(item, dict) or not item.get("model_name"):
                continue
            endpoints = item.get("supported_endpoint_types") or []
            if not belongs(item["model_name"], endpoints, patterns):
                continue
            models.append({
                "id": item["model_name"],
                "endpoint_types": endpoints,
                "quota_type": item.get("quota_type"),
                "price": item.get("model_price"),
                "ratio": item.get("model_ratio"),
                "billing_mode": item.get("billing_mode"),
                "billing_expr": item.get("billing_expr"),
                "groups": item.get("enable_groups") or [],
            })
    except GatewayError:
        models = []

    known = {model["id"] for model in models}
    try:
        payload = request_json(settings, "GET", "/v1/models")
        for item in payload.get("data") or []:
            model_id = item.get("id") if isinstance(item, dict) else ""
            if model_id and model_id not in known and belongs(model_id, [], patterns):
                models.append({"id": model_id, "endpoint_types": [], "groups": []})
                known.add(model_id)
    except GatewayError:
        if not models:
            raise

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"fetched_at": int(time.time()), "models": models}, ensure_ascii=False), "utf-8")
    return models


def resolve_alias(alias: str, models: list) -> list:
    key = alias.lower().strip()
    for model in models:
        if model["id"].lower() == key:
            return [model]
    patterns = read_json(ROOT / "scripts" / "models.json").get("aliases", {}).get(key, [])
    matches = []
    for pattern in patterns:
        for model in models:
            if fnmatch.fnmatch(model["id"].lower(), pattern.lower()) and model not in matches:
                matches.append(model)
    return matches


def price_rank(model: dict) -> tuple:
    price = model.get("price")
    if isinstance(price, (int, float)) and price > 0:
        return (0, float(price))
    ratio = model.get("ratio")
    if isinstance(ratio, (int, float)) and ratio > 0:
        return (1, float(ratio))
    return (2, 0.0)


def pick_model(args, models: list, alias: str = "", default: str = "") -> tuple[str, str]:
    if getattr(args, "model", ""):
        return args.model, ""
    if default:
        return default, ""
    if alias:
        matches = resolve_alias(alias, models)
        if len(matches) == 1:
            return matches[0]["id"], ""
        if matches:
            chosen = min(matches, key=price_rank)
            return chosen["id"], f"auto-selected the cheapest of {len(matches)} '{alias}' matches; pass --model to choose"
    if len(models) == 1:
        return models[0]["id"], ""
    hint = f", alias '{alias}'" if alias else ""
    raise GatewayError(f"model is required: pass --model or set a default with `model set` ({CAPABILITY}{hint})")


def slug(text: str, limit: int = 40) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]+", "-", text or "").strip("-")
    return (cleaned[:limit] or "output").lower()


def sniff_extension(payload: bytes, fallback: str = "bin") -> str:
    if payload.startswith(b"\x89PNG"):
        return "png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "webp"
    if payload[:3] == b"GIF":
        return "gif"
    head = payload[:512].lstrip()
    if head.startswith(b"<svg") or head.startswith(b"<?xml"):
        return "svg"
    return fallback


def save_bytes(category: str, stem: str, payload: bytes, extension: str = "") -> Path:
    target = OUTPUT_DIR / category / date.today().isoformat()
    target.mkdir(parents=True, exist_ok=True)
    suffix = (extension or "").strip(".").lower() or sniff_extension(payload)
    path = target / f"{stem}-{time.strftime('%H%M%S')}.{suffix}"
    path.write_bytes(payload)
    return path


def download(settings: dict, url: str, timeout: int = 120) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return read_body(resp)
    except urllib.error.HTTPError as err:
        message, code = parse_error(read_body(err), err.code)
        raise GatewayError(f"download failed: {message}", err.code, code) from None
    except urllib.error.URLError as err:
        raise GatewayError(f"download failed: {url}: {err.reason}") from None


def handle_login(args, settings: dict) -> None:
    if not args.key:
        raise GatewayError("--key is required")
    if args.base_url and not args.base_url.startswith(("http://", "https://")):
        raise GatewayError("--base-url must start with http:// or https://")
    target = ROOT / "config.json"
    data = read_json(target)
    data["api_key"] = args.key
    if args.base_url:
        data["base_url"] = args.base_url.rstrip("/")
    if args.group:
        data["group"] = args.group
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    os.chmod(target, 0o600)
    emit({"ok": True, "config": str(target), "base_url": data.get("base_url") or settings["base_url"]})


def handle_model(args, settings: dict) -> None:
    if args.action == "set":
        target = ROOT / "config.json"
        data = read_json(target)
        data["model"] = args.model_id
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        os.chmod(target, 0o600)
        emit({"ok": True, "model": args.model_id, "config": str(target)})
        return
    configured = settings["default_model"]
    available = None
    if configured:
        try:
            available = configured in {model["id"] for model in load_models(settings)}
        except GatewayError:
            available = None
    emit({"ok": True, "model": configured, "configured": bool(configured), "available": available,
          "source": str(ROOT / "config.json") if configured else "none"})


def handle_config(args, settings: dict) -> None:
    emit({
        "ok": True,
        "capability": CAPABILITY,
        "platform": {"name": PLATFORM, "url": PLATFORM_URL, "tagline": PLATFORM_TAGLINE,
                     "description_zh": PLATFORM_DESC_ZH, "description_en": PLATFORM_DESC_EN,
                     "repository": REPO_URL},
        "config": str(ROOT / "config.json"),
        "base_url": settings["base_url"],
        "group": settings["group"],
        "model": settings["default_model"],
        "api_key": mask_secret(settings["api_key"]),
        "sources": settings["sources"],
        "defaults": str(DEFAULTS_PATH),
    })


def handle_models(args, settings: dict) -> None:
    models = load_models(settings, refresh=args.refresh)
    key = re.sub(r"[^a-z0-9]+", "-", (settings.get("base_url") or "unconfigured").lower()).strip("-")
    cached = read_json(CACHE_DIR / f"{CAPABILITY}-{key}.json")
    fetched_at = cached.get("fetched_at") or 0
    emit({"ok": True, "base_url": settings["base_url"], "count": len(models),
          "cached_at": fetched_at or None,
          "cache_age_seconds": int(time.time() - fetched_at) if fetched_at else None,
          "models": models})


def handle_resolve(args, settings: dict) -> None:
    matches = resolve_alias(args.alias, load_models(settings))
    if not matches:
        raise GatewayError(f"no model matches alias '{args.alias}'")
    emit({"ok": True, "alias": args.alias, "matches": matches})


def handle_doctor(args, settings: dict) -> None:
    report = {"ok": False, "base_url": settings["base_url"], "sources": settings["sources"],
              "api_key": mask_secret(settings["api_key"]), "api_key_configured": bool(settings["api_key"])}
    if not settings["api_key"]:
        report["error"] = {"message": "no API key configured"}
        emit(report)
        return
    try:
        payload = request_json(settings, "GET", "/v1/models")
        report["auth_ok"] = True
        report["models"] = len(payload.get("data") or [])
        report["ok"] = True
    except GatewayError as err:
        report["auth_ok"] = False
        report["error"] = {"message": err.message, "status": err.status}
    emit(report)


def image_dimensions(payload: bytes) -> str:
    if payload.startswith(b"\x89PNG") and len(payload) >= 24:
        width = int.from_bytes(payload[16:20], "big")
        height = int.from_bytes(payload[20:24], "big")
        return f"{width}x{height}"
    if payload[:6] in (b"GIF87a", b"GIF89a") and len(payload) >= 10:
        width = int.from_bytes(payload[6:8], "little")
        height = int.from_bytes(payload[8:10], "little")
        return f"{width}x{height}"
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        chunk = payload[12:16]
        if chunk == b"VP8X" and len(payload) >= 30:
            width = int.from_bytes(payload[24:27], "little") + 1
            height = int.from_bytes(payload[27:30], "little") + 1
            return f"{width}x{height}"
        if chunk == b"VP8 " and len(payload) >= 30:
            width = int.from_bytes(payload[26:28], "little") & 0x3FFF
            height = int.from_bytes(payload[28:30], "little") & 0x3FFF
            return f"{width}x{height}"
        if chunk == b"VP8L" and len(payload) >= 25:
            bits = int.from_bytes(payload[21:25], "little")
            return f"{(bits & 0x3FFF) + 1}x{((bits >> 14) & 0x3FFF) + 1}"
        return ""
    if payload.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(payload):
            if payload[index] != 0xFF:
                index += 1
                continue
            marker = payload[index + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                height = int.from_bytes(payload[index + 5:index + 7], "big")
                width = int.from_bytes(payload[index + 7:index + 9], "big")
                return f"{width}x{height}"
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            index += 2 + int.from_bytes(payload[index + 2:index + 4], "big")
    return ""


def estimate_cost(model: str, catalog: list):
    for entry in catalog:
        if entry.get("id") == model:
            price = entry.get("price")
            if isinstance(price, (int, float)) and price > 0:
                return price
            return None
    return None


def image_result(payload: dict, model: str, saved: list, sizes: list, urls: list, requested: str,
                 note: str, started: float, catalog: list) -> dict:
    result = {
        "ok": True,
        "model": model,
        "files": saved,
        "sizes": sizes,
        "requested_size": requested,
        "urls": urls,
        "created": payload.get("created"),
        "usage": payload.get("usage"),
        "est_cost": estimate_cost(model, catalog),
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }
    if note:
        result["model_note"] = note
    if requested and "x" in requested.lower() and sizes and any(size and size != requested for size in sizes):
        result["size_note"] = f"requested {requested}, got {sizes[0]}"
    return result


def persist_images(settings: dict, payload: dict, stem: str, fmt: str) -> tuple[list, list, list]:
    saved, urls, sizes = [], [], []
    items = payload.get("data")
    if not isinstance(items, list):
        return saved, urls, sizes
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        encoded = item.get("b64_json")
        url = str(item.get("url") or "").strip()
        raw = b""
        if encoded:
            raw = base64.b64decode(encoded.split(",", 1)[-1])
        elif url:
            try:
                raw = download(settings, url)
            except GatewayError:
                urls.append(url)
                continue
        if not raw:
            continue
        saved.append(str(save_bytes("image", f"{stem}-{index + 1}", raw, fmt)))
        sizes.append(image_dimensions(raw))
    return saved, urls, sizes


def build_body(args, fields: list) -> dict:
    body = {}
    for field in fields:
        value = getattr(args, field, None)
        if value is None or value == "":
            continue
        body[field] = value
    if getattr(args, "group", ""):
        body["group"] = args.group
    return body


def mime_for(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "application/octet-stream")


def save_native_images(payload: dict, stem: str) -> tuple[list, list]:
    saved, sizes = [], []
    for candidate in payload.get("candidates") or []:
        content = candidate.get("content") if isinstance(candidate, dict) else {}
        for part in (content or {}).get("parts") or []:
            inline = part.get("inlineData") if isinstance(part, dict) else None
            if not isinstance(inline, dict) or not inline.get("data"):
                continue
            raw = base64.b64decode(inline["data"])
            extension = str(inline.get("mimeType") or "").split("/")[-1].replace("jpeg", "jpg")
            saved.append(str(save_bytes("image", f"{stem}-{len(saved) + 1}", raw, extension)))
            sizes.append(image_dimensions(raw))
    return saved, sizes


def handle_image_native(args, settings: dict) -> None:
    started = time.monotonic()
    size = (args.size or "1K").upper()
    if size not in ("1K", "2K", "4K"):
        raise GatewayError("--size must be 1K, 2K, or 4K")
    catalog = load_models(settings)
    model, note = pick_model(args, catalog, "nano-banana", settings["default_model"])
    if "gemini" not in model.lower() or "image" not in model.lower():
        raise GatewayError(f"native mode needs a Gemini image model, got '{model}'")

    parts = [{"text": args.prompt}]
    for path in args.image:
        try:
            data = Path(path).read_bytes()
        except OSError as err:
            raise GatewayError(f"cannot read image {path}: {err.strerror or err}") from None
        parts.append({"inlineData": {"mimeType": mime_for(path), "data": base64.b64encode(data).decode()}})

    image_config = {"imageSize": size}
    if args.ratio:
        image_config["aspectRatio"] = args.ratio
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": image_config},
    }
    payload = request_json(settings, "POST", f"/v1beta/models/{model}:generateContent", body=body)
    saved, sizes = save_native_images(payload, slug(args.prompt))
    if not saved:
        raise GatewayError(f"response contained no inline image data: {json.dumps(payload, ensure_ascii=False)[:300]}")

    result = {
        "ok": True,
        "model": model,
        "files": saved,
        "sizes": sizes,
        "requested_size": f"{size} {args.ratio}".strip(),
        "usage": payload.get("usageMetadata"),
        "est_cost": estimate_cost(model, catalog),
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }
    if note:
        result["model_note"] = note
    emit(result)


def handle_image_generate(args, settings: dict) -> None:
    started = time.monotonic()
    if args.n is not None and not 1 <= args.n <= 128:
        raise GatewayError("--n must be between 1 and 128")
    catalog = load_models(settings)
    model, note = pick_model(args, catalog, "gpt-image", settings["default_model"])
    body = build_body(args, ["prompt", "size", "n", "quality", "output_format", "background", "moderation",
                             "complexity", "output_compression", "frame_count", "frame_duration_ms"])
    body["model"] = model
    _, _, raw = request(settings, "POST", "/v1/images/generations", body=body)
    payload = json.loads(raw.decode("utf-8", "replace"))
    saved, urls, sizes = persist_images(settings, payload, slug(args.prompt), body.get("output_format", ""))
    if not saved and not urls:
        raise GatewayError(f"response contained no image data: {json.dumps(payload, ensure_ascii=False)[:300]}")
    emit(image_result(payload, model, saved, sizes, urls, args.size, note, started, catalog))


def handle_image_edit(args, settings: dict) -> None:
    if not args.image:
        raise GatewayError("--image is required (repeatable)")
    if args.n is not None and not 1 <= args.n <= 128:
        raise GatewayError("--n must be between 1 and 128")
    started = time.monotonic()
    catalog = load_models(settings)
    model, note = pick_model(args, catalog, "gpt-image", settings["default_model"])
    fields = [("model", model), ("prompt", args.prompt)]
    for name in ("size", "quality", "output_format", "background", "moderation", "n", "output_compression", "complexity"):
        value = getattr(args, name, None)
        if value not in (None, ""):
            fields.append((name, str(value)))
    if args.group:
        fields.append(("group", args.group))
    files = []
    for path in args.image:
        try:
            data = Path(path).read_bytes()
        except OSError as err:
            raise GatewayError(f"cannot read image {path}: {err.strerror or err}") from None
        files.append(("image[]", Path(path).name, data, "application/octet-stream"))
    if args.mask:
        try:
            mask = Path(args.mask).read_bytes()
        except OSError as err:
            raise GatewayError(f"cannot read mask {args.mask}: {err.strerror or err}") from None
        files.append(("mask", Path(args.mask).name, mask, "application/octet-stream"))
    if args.markup:
        try:
            markup = Path(args.markup).read_bytes()
        except OSError as err:
            raise GatewayError(f"cannot read markup {args.markup}: {err.strerror or err}") from None
        files.append(("markup", Path(args.markup).name, markup, "application/octet-stream"))
    _, _, raw = request(settings, "POST", "/v1/images/edits", fields=fields, files=files)
    payload = json.loads(raw.decode("utf-8", "replace"))
    saved, urls, sizes = persist_images(settings, payload, slug(args.prompt), args.output_format or "")
    if not saved and not urls:
        raise GatewayError(f"response contained no image data: {json.dumps(payload, ensure_ascii=False)[:300]}")
    emit(image_result(payload, model, saved, sizes, urls, args.size, note, started, catalog))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gateway.py",
        description=f"Image generation skill for {PLATFORM} ({PLATFORM_URL})",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"{PLATFORM} · {PLATFORM_URL}\n"
            f"{PLATFORM_DESC_ZH}\n"
            f"{PLATFORM_DESC_EN}\n"
            f"Repository: {REPO_URL}"
        ),
    )
    parser.add_argument("--request-timeout", dest="request_timeout", type=int, default=0,
                        help="override the single-request timeout in seconds")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="store an API key")
    login.add_argument("--key", required=True)
    login.add_argument("--base-url", default="")
    login.add_argument("--group", default="")

    sub.add_parser("config", help="show resolved settings")

    models = sub.add_parser("models", help="list image models")
    models.add_argument("--refresh", action="store_true")

    model = sub.add_parser("model", help="show or set the default model")
    model_sub = model.add_subparsers(dest="action", required=True)
    model_sub.add_parser("show", help="show the configured default model")
    model_set = model_sub.add_parser("set", help="pin a default model in config.json")
    model_set.add_argument("model_id")

    resolve = sub.add_parser("resolve", help="map an alias to a model id")
    resolve.add_argument("alias")

    image = sub.add_parser("image", help="image generation and editing")
    image_sub = image.add_subparsers(dest="action", required=True)

    generate = image_sub.add_parser("generate")
    generate.add_argument("--prompt", required=True)
    generate.add_argument("--model", default="")
    generate.add_argument("--size", default="")
    generate.add_argument("--n", type=int, default=None)
    generate.add_argument("--quality", default="")
    generate.add_argument("--output-format", dest="output_format", default="")
    generate.add_argument("--background", default="")
    generate.add_argument("--moderation", default="")
    generate.add_argument("--complexity", default="")
    generate.add_argument("--output-compression", dest="output_compression", type=int, default=None)
    generate.add_argument("--frame-count", dest="frame_count", type=int, default=None)
    generate.add_argument("--frame-duration-ms", dest="frame_duration_ms", type=int, default=None)
    generate.add_argument("--group", default="")

    edit = image_sub.add_parser("edit")
    edit.add_argument("--prompt", required=True)
    edit.add_argument("--image", action="append", default=[])
    edit.add_argument("--mask", default="")
    edit.add_argument("--markup", default="")
    edit.add_argument("--model", default="")
    edit.add_argument("--size", default="")
    edit.add_argument("--n", type=int, default=None)
    edit.add_argument("--quality", default="")
    edit.add_argument("--output-format", dest="output_format", default="")
    edit.add_argument("--background", default="")
    edit.add_argument("--moderation", default="")
    edit.add_argument("--complexity", default="")
    edit.add_argument("--output-compression", dest="output_compression", type=int, default=None)
    edit.add_argument("--group", default="")

    native = image_sub.add_parser("native", help="Gemini native generateContent endpoint")
    native.add_argument("--prompt", required=True)
    native.add_argument("--model", default="")
    native.add_argument("--image", action="append", default=[], help="local reference image, repeatable")
    native.add_argument("--size", default="1K", help="1K, 2K, or 4K")
    native.add_argument("--ratio", default="", help="aspect ratio such as 16:9")

    sub.add_parser("doctor", help="verify credentials and connectivity")
    return parser


DISPATCH = {
    ("login", None): handle_login,
    ("config", None): handle_config,
    ("models", None): handle_models,
    ("model", "show"): handle_model,
    ("model", "set"): handle_model,
    ("resolve", None): handle_resolve,
    ("image", "generate"): handle_image_generate,
    ("image", "edit"): handle_image_edit,
    ("image", "native"): handle_image_native,
    ("doctor", None): handle_doctor,
}


def main(argv: list | None = None) -> None:
    args = build_parser().parse_args(argv)
    current = settings()
    if getattr(args, "request_timeout", 0) > 0:
        current["timeout"] = args.request_timeout
    try:
        DISPATCH[(args.command, getattr(args, "action", None))](args, current)
    except GatewayError as err:
        fail(err.code or "request_failed", err.message, err.status)
    except KeyboardInterrupt:
        fail("interrupted", "cancelled by user")
    except Exception as err:
        fail("internal_error", f"{type(err).__name__}: {err}")


if __name__ == "__main__":
    main()
