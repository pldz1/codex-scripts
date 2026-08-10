#!/usr/bin/env python3
"""Generate images with an Azure OpenAI GPT-Image-2 deployment.

Uses only the Python standard library. Credentials are read from environment
variables and are never accepted as command-line arguments.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import json
import os
import pathlib
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_API_VERSION = "preview"
DEFAULT_TIMEOUT_SECONDS = 240
DEFAULT_RETRIES = 3


class ConfigurationError(RuntimeError):
    pass


class AzureImageError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


def env_first(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def load_config() -> dict[str, str]:
    endpoint = env_first("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_BASE_URL")
    api_key = env_first("AZURE_OPENAI_API_KEY")
    deployment = env_first(
        "AZURE_OPENAI_IMAGE_DEPLOYMENT",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
    )
    api_version = env_first("AZURE_OPENAI_IMAGE_API_VERSION") or DEFAULT_API_VERSION

    missing: list[str] = []
    if not endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT (or AZURE_OPENAI_BASE_URL)")
    if not api_key:
        missing.append("AZURE_OPENAI_API_KEY")
    if not deployment:
        missing.append("AZURE_OPENAI_IMAGE_DEPLOYMENT (or AZURE_OPENAI_DEPLOYMENT_NAME)")
    if missing:
        raise ConfigurationError("Missing environment variable(s): " + ", ".join(missing))

    return {
        "endpoint": endpoint,
        "api_key": api_key,
        "deployment": deployment,
        "api_version": api_version,
    }


def build_generation_url(endpoint: str, api_version: str) -> str:
    raw = endpoint.strip().rstrip("/")
    if not re.match(r"^https?://", raw, flags=re.IGNORECASE):
        raise ConfigurationError("Azure endpoint/base URL must start with http:// or https://")

    parsed = urllib.parse.urlsplit(raw)
    path = parsed.path.rstrip("/")

    if path.endswith("/images/generations"):
        final_path = path
    elif "/openai/v1" in path:
        prefix = path.split("/openai/v1", 1)[0]
        final_path = prefix + "/openai/v1/images/generations"
    else:
        # Normalize resource endpoints and legacy deployment URLs to Azure's v1 image route.
        final_path = "/openai/v1/images/generations"

    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if "api-version" not in query:
        query["api-version"] = [api_version]
    encoded_query = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, final_path, encoded_query, ""))


def validate_size(size: str) -> None:
    if size == "auto":
        return
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if not match:
        raise ValueError("size must be 'auto' or WIDTHxHEIGHT, for example 1024x1024")
    width, height = (int(match.group(1)), int(match.group(2)))
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    if width % 16 or height % 16:
        raise ValueError("GPT-Image-2 requires both image edges to be multiples of 16")
    long_edge, short_edge = max(width, height), min(width, height)
    if long_edge > 3840:
        raise ValueError("GPT-Image-2 supports a maximum long edge of 3840 pixels")
    if long_edge / short_edge > 3:
        raise ValueError("GPT-Image-2 supports a maximum aspect ratio of 3:1")
    pixels = width * height
    if not 655_360 <= pixels <= 8_294_400:
        raise ValueError(
            "GPT-Image-2 total pixels must be between 655360 and 8294400"
        )


def parse_error_payload(raw: bytes) -> tuple[str | None, str]:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None, "Azure OpenAI returned an empty error response"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None, text[:2000]

    error: Any = payload.get("error", payload) if isinstance(payload, dict) else payload
    if isinstance(error, dict):
        code = error.get("code") or error.get("type")
        message = error.get("message") or error.get("detail") or json.dumps(error, ensure_ascii=False)
        return str(code) if code else None, str(message)
    return None, str(error)


def request_json(
    url: str,
    api_key: str,
    body: dict[str, Any],
    *,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "codex-azure-image-gen-skill/1.0",
    }

    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=encoded, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise AzureImageError("Azure OpenAI returned a non-object JSON response")
                return payload
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            code, message = parse_error_payload(raw)
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if retryable and attempt < retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = float(retry_after) if retry_after else min(2 ** attempt + random.random(), 12)
                except ValueError:
                    delay = min(2 ** attempt + random.random(), 12)
                print(
                    f"Azure request failed with HTTP {exc.code}; retrying in {delay:.1f}s...",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            raise AzureImageError(message, status=exc.code, code=code) from exc
        except urllib.error.URLError as exc:
            if attempt < retries:
                delay = min(2 ** attempt + random.random(), 12)
                print(f"Network error; retrying in {delay:.1f}s: {exc.reason}", file=sys.stderr)
                time.sleep(delay)
                continue
            raise AzureImageError(f"Network error calling Azure OpenAI: {exc.reason}") from exc
        except TimeoutError as exc:
            if attempt < retries:
                delay = min(2 ** attempt + random.random(), 12)
                print(f"Request timed out; retrying in {delay:.1f}s...", file=sys.stderr)
                time.sleep(delay)
                continue
            raise AzureImageError("Azure OpenAI image request timed out") from exc

    raise AzureImageError("Azure OpenAI request failed after retries")


def read_prompt(value: str | None) -> str:
    if value is not None:
        prompt = value
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read()
    else:
        raise ValueError("Provide --prompt or pipe the image prompt on stdin")
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Image prompt cannot be empty")
    return prompt


def safe_stem(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return value[:80] or "azure-image"


def output_paths(output_dir: pathlib.Path, stem: str, fmt: str, count: int) -> list[pathlib.Path]:
    extension = "jpg" if fmt == "jpeg" else fmt
    if count == 1:
        return [output_dir / f"{stem}.{extension}"]
    return [output_dir / f"{stem}-{index + 1}.{extension}" for index in range(count)]


def save_images(payload: dict[str, Any], paths: list[pathlib.Path]) -> list[pathlib.Path]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        code, message = parse_error_payload(json.dumps(payload).encode("utf-8"))
        raise AzureImageError(message, code=code)
    if len(data) != len(paths):
        paths = output_paths(paths[0].parent, paths[0].stem, paths[0].suffix.lstrip("."), len(data))

    saved: list[pathlib.Path] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict) or not item.get("b64_json"):
            raise AzureImageError(f"Image result {index + 1} did not contain b64_json")
        try:
            image_bytes = base64.b64decode(item["b64_json"], validate=True)
        except (binascii.Error, ValueError, TypeError) as exc:
            raise AzureImageError(f"Image result {index + 1} contained invalid base64 data") from exc
        path = paths[index]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        saved.append(path.resolve())
    return saved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate images using an Azure OpenAI GPT-Image-2 deployment."
    )
    parser.add_argument("--prompt", help="Image prompt. If omitted, read UTF-8 text from stdin.")
    parser.add_argument("--size", default="1024x1024", help="WIDTHxHEIGHT or auto")
    parser.add_argument("--quality", choices=("low", "medium", "high"), default="high")
    parser.add_argument("--n", type=int, default=1, help="Number of images, 1-10")
    parser.add_argument("--format", choices=("png", "jpeg"), default="png", dest="output_format")
    parser.add_argument("--background", choices=("auto", "transparent"))
    parser.add_argument("--compression", type=int, help="JPEG compression level, 0-100")
    parser.add_argument("--user", help="Optional end-user identifier sent to Azure")
    parser.add_argument("--output-dir", default="generated-images")
    parser.add_argument("--name", help="Output filename stem")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--check", action="store_true", help="Validate configuration without calling Azure")
    parser.add_argument("--dry-run", action="store_true", help="Print sanitized request details without calling Azure")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = load_config()
        url = build_generation_url(config["endpoint"], config["api_version"])

        if args.check:
            parsed = urllib.parse.urlsplit(url)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "api_key": "set",
                        "endpoint_host": parsed.netloc,
                        "generation_path": parsed.path,
                        "api_version": urllib.parse.parse_qs(parsed.query).get("api-version", [None])[0],
                        "deployment": config["deployment"],
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        prompt = read_prompt(args.prompt)
        validate_size(args.size)
        if not 1 <= args.n <= 10:
            raise ValueError("n must be between 1 and 10")
        if args.timeout <= 0:
            raise ValueError("timeout must be positive")
        if args.retries < 0:
            raise ValueError("retries cannot be negative")
        if args.compression is not None:
            if not 0 <= args.compression <= 100:
                raise ValueError("compression must be between 0 and 100")
            if args.output_format != "jpeg":
                raise ValueError("compression is supported only with --format jpeg")
        if args.background == "transparent" and args.output_format != "png":
            raise ValueError("transparent background requires --format png")

        body: dict[str, Any] = {
            "model": config["deployment"],
            "prompt": prompt,
            "size": args.size,
            "quality": args.quality,
            "n": args.n,
            "output_format": args.output_format,
        }
        if args.background:
            body["background"] = args.background
        if args.compression is not None:
            body["output_compression"] = args.compression
        if args.user:
            body["user"] = args.user

        if args.dry_run:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "dry_run": True,
                        "url": url,
                        "body": body,
                        "api_key": "redacted",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = safe_stem(args.name or f"azure-image-{timestamp}")
        output_dir = pathlib.Path(args.output_dir).expanduser()
        paths = output_paths(output_dir, stem, args.output_format, args.n)

        payload = request_json(
            url,
            config["api_key"],
            body,
            timeout=args.timeout,
            retries=args.retries,
        )
        saved = save_images(payload, paths)

        result = {
            "ok": True,
            "files": [str(path) for path in saved],
            "count": len(saved),
            "deployment": config["deployment"],
            "size": args.size,
            "quality": args.quality,
            "format": args.output_format,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    except ConfigurationError as exc:
        print(json.dumps({"ok": False, "error": "configuration", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": "invalid_argument", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except AzureImageError as exc:
        error = {
            "ok": False,
            "error": "azure_openai",
            "message": str(exc),
        }
        if exc.status is not None:
            error["status"] = exc.status
        if exc.code:
            error["code"] = exc.code
        print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
        return 1
    except (json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": "runtime", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
