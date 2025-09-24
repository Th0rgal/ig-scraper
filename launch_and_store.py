import argparse
import json
import os
import sys
from typing import Any, Dict, List

from scraper import scrape_instagram_profile


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return val


def build_headers() -> Dict[str, str]:
    service_role = os.getenv("SUPABASE_SERVICE_ROLE")
    if not service_role:
        print("Missing SUPABASE_SERVICE_ROLE for authorization", file=sys.stderr)
        sys.exit(2)
    token = service_role.strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def upload_to_storage(
    base_url: str,
    headers: Dict[str, str],
    bucket: str,
    object_name: str,
    content_bytes: bytes,
    content_type: str = "application/json",
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
    resp = requests.post(url, headers=hdrs, data=content_bytes, timeout=60)
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


def serialize_items(items: List[Dict[str, Any]]) -> bytes:
    return json.dumps(items, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Instagram and store results to Supabase Storage"
    )
    parser.add_argument(
        "--file-name",
        required=True,
        help="Destination file name in 'ig-scraper' bucket (e.g., results.json)",
    )
    parser.add_argument("--username", "-u", required=True, help="Instagram username")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--proxy", help="Proxy URL (http(s) or socks5), auth supported")
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument("--headless", dest="headless", action="store_true")
    headless_group.add_argument("--no-headless", dest="headless", action="store_false")
    parser.set_defaults(headless=True)
    args = parser.parse_args()

    base_url = _require_env("SUPABASE_URL")
    headers = build_headers()
    headers.setdefault("Accept", "application/json")

    proxy_url = args.proxy or os.getenv("PROXY_URL")

    data = scrape_instagram_profile(
        args.username,
        headless=args.headless,
        timeout=args.timeout,
        debug=args.debug,
        proxy=proxy_url,
    )

    additions: List[Dict[str, Any]] = []
    for p in data.get("posts", []):
        url = p.get("img_src")
        caption = p.get("img_caption") or ""
        if url:
            additions.append(
                {
                    "kind": "image",
                    "url": url,
                    "content": caption,
                    "source": "instagram",
                }
            )

    payload_bytes = serialize_items(additions)
    upload_to_storage(
        base_url,
        headers,
        "ig-scraper",
        args.file_name,
        payload_bytes,
        content_type="application/json",
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "username": args.username,
                "added": len(additions),
                "bucket": "ig-scraper",
                "file": args.file_name,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
