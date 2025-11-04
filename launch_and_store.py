import argparse
import hashlib
import json
import mimetypes
import os
import sys
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse
import uuid
from io import BytesIO

from scraper import scrape_instagram_profile


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return val


def build_headers(token_override: str | None = None) -> Dict[str, str]:
    service_role = token_override or os.getenv("SUPABASE_SERVICE_ROLE")
    if not service_role:
        print("Missing SUPABASE_SERVICE_ROLE for authorization", file=sys.stderr)
        sys.exit(2)
    token = service_role.strip()
    return {
        "Authorization": f"Bearer {token}",
        "apikey": token,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def upload_to_storage(
    base_url: str,
    headers: Dict[str, str],
    bucket: str,
    object_name: str,
    content_bytes: bytes,
    content_type: str = "application/octet-stream",
) -> Dict[str, Any]:
    try:
        import requests  # type: ignore
    except ImportError:
        print(
            "The 'requests' package is required. Please install dependencies.",
            file=sys.stderr,
        )
        sys.exit(2)

    object_name = object_name.lstrip("/")
    url = base_url.rstrip("/") + f"/storage/v1/object/{bucket}/{object_name}"
    hdrs = dict(headers)
    hdrs["Content-Type"] = content_type
    hdrs["x-upsert"] = "true"
    resp = requests.post(url, headers=hdrs, data=content_bytes, timeout=120)
    if resp.status_code not in (200, 201, 204):
        print(
            f"Failed to upload to storage {bucket}/{object_name}: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return resp.json()
    except ValueError:
        return {"status": "uploaded"}


def insert_asset_row(
    base_url: str,
    headers: Dict[str, str],
    row: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        import requests  # type: ignore
    except ImportError:
        print(
            "The 'requests' package is required. Please install dependencies.",
            file=sys.stderr,
        )
        sys.exit(2)

    url = base_url.rstrip("/") + "/rest/v1/assets"
    hdrs = dict(headers)
    hdrs.setdefault("Content-Type", "application/json")
    hdrs.setdefault("Accept", "application/json")
    resp = requests.post(url, headers=hdrs, data=json.dumps(row), timeout=60)
    if resp.status_code not in (200, 201):
        print(
            f"Failed to insert assets row: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        sys.exit(1)
    return (
        resp.json()[0]
        if resp.headers.get("Content-Range") or resp.text.startswith("[")
        else resp.json()
    )


def guess_extension(content_type: str | None, source_url: str) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    parsed = urlparse(source_url)
    path = parsed.path or ""
    if "." in path:
        ext = path.split(".")[-1].lower()
        if ext and all(c.isalnum() for c in ext):
            return "." + ext
    return ".jpg"


def download_bytes(url: str) -> Tuple[bytes, str]:
    try:
        import requests  # type: ignore
    except ImportError:
        print(
            "The 'requests' package is required. Please install dependencies.",
            file=sys.stderr,
        )
        sys.exit(2)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.instagram.com/",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=60)
    if resp.status_code != 200:
        print(f"Failed to download image: {resp.status_code} {url}", file=sys.stderr)
        sys.exit(1)
    ctype = resp.headers.get("Content-Type", "image/jpeg")
    return resp.content, ctype


def convert_image_to_webp(image_bytes: bytes) -> bytes:
    try:
        import importlib

        pil_image = importlib.import_module("PIL.Image")
    except ImportError:
        print(
            "Pillow is required for --convert-webp. Please install dependencies.",
            file=sys.stderr,
        )
        sys.exit(2)
    img = pil_image.open(BytesIO(image_bytes))
    out = BytesIO()
    img.save(out, format="WEBP", quality=85, method=6)
    return out.getvalue()


def derive_object_name(project_id: str, sha1: str, ext: str) -> str:
    return f"{project_id}/{sha1}{ext}"


def serialize_items(items: List[Dict[str, Any]]) -> bytes:
    return json.dumps(items, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Instagram and upload images to assets bucket; insert rows into assets table"
    )
    parser.add_argument(
        "--file-name",
        required=False,
        default=None,
        help="Deprecated and ignored",
    )
    parser.add_argument(
        "--project-id",
        "-p",
        required=True,
        help="Project UUID to set on inserted assets rows",
    )
    parser.add_argument("--username", "-u", required=True, help="Instagram username")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--proxy", help="Proxy URL (http(s) or socks5), auth supported")
    parser.add_argument(
        "--convert-webp",
        action="store_true",
        help="Convert downloaded images to WebP before upload",
    )
    parser.add_argument(
        "--run-id",
        required=False,
        default=None,
        help="Optional UUID to tag this run; generated if omitted",
    )
    parser.add_argument(
        "--supabase-url",
        required=False,
        default=None,
        help="Override SUPABASE_URL environment variable",
    )
    parser.add_argument(
        "--supabase-service-role",
        required=False,
        default=None,
        help="Override SUPABASE_SERVICE_ROLE environment variable",
    )
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument("--headless", dest="headless", action="store_true")
    headless_group.add_argument("--no-headless", dest="headless", action="store_false")
    parser.set_defaults(headless=True)
    args = parser.parse_args()

    base_url = args.supabase_url or _require_env("SUPABASE_URL")
    headers = build_headers(args.supabase_service_role)
    headers.setdefault("Accept", "application/json")

    proxy_url = args.proxy or os.getenv("PROXY_URL")

    data = scrape_instagram_profile(
        args.username,
        headless=args.headless,
        timeout=args.timeout,
        debug=args.debug,
        proxy=proxy_url,
    )

    run_id = args.run_id or str(uuid.uuid4())

    uploaded_count = 0
    for p in data.get("posts", []):
        img_url = p.get("img_src")
        caption = p.get("img_caption") or ""
        if not img_url:
            continue
        content_bytes, content_type = download_bytes(img_url)
        # Optional convert to WebP before hashing/naming
        if args.convert_webp:
            content_bytes = convert_image_to_webp(content_bytes)
            content_type = "image/webp"
            ext = ".webp"
        else:
            ext = guess_extension(content_type, img_url)
        # Derive stable filename from content hash and extension
        sha1 = hashlib.sha1(content_bytes).hexdigest()[:16]
        object_name = derive_object_name(args.project_id, sha1, ext)

        upload_to_storage(
            base_url,
            headers,
            "assets",
            object_name,
            content_bytes,
            content_type=content_type,
        )

        row = {
            "project_id": args.project_id,
            "filename": object_name,
            "type": "image",
            "metadata": {
                "source": "instagram",
                "instagram": args.username,
                "run_id": run_id,
            },
            "description": caption,
        }
        insert_asset_row(base_url, headers, row)
        uploaded_count += 1

    print(
        json.dumps(
            {
                "status": "ok",
                "username": args.username,
                "added": uploaded_count,
                "bucket": "assets",
                "run_id": run_id,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
