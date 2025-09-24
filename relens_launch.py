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
    # Require service role for simplicity
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


def fetch_job(base_url: str, headers: Dict[str, str], job_id: str) -> Dict[str, Any]:
    try:
        import requests  # type: ignore
    except ImportError:
        print(
            "The 'requests' package is required. Please install dependencies.",
            file=sys.stderr,
        )
        sys.exit(2)
    # Using PostgREST RPC style: /rest/v1/jobs?id=eq.<job_id>
    url = base_url.rstrip("/") + "/rest/v1/jobs"
    params = {"id": f"eq.{job_id}", "select": "*"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        print(
            f"Failed to fetch job {job_id}: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        sys.exit(1)
    rows = resp.json()
    if not rows:
        print(f"Job not found: {job_id}", file=sys.stderr)
        sys.exit(1)
    return rows[0]


def append_content_to_context(
    context_value: Any, additions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    # Accepts either a dict (jsonb) or a JSON string, returns a dict
    if isinstance(context_value, dict):
        obj = context_value
    else:
        try:
            obj = json.loads(context_value) if context_value else {}
        except ValueError:
            obj = {}

    if not isinstance(obj, dict):
        obj = {}

    # Ensure a list exists to append into. Prefer key "content", fallback to " ".
    if "content" in obj and isinstance(obj["content"], list):
        obj["content"].extend(additions)
    elif " " in obj and isinstance(obj[" "], list):
        obj[" "].extend(additions)
    else:
        existing = []
        if isinstance(obj.get("content"), list):
            existing = obj["content"]
        elif isinstance(obj.get(" "), list):
            existing = obj[" "]
        obj["content"] = existing + additions

    return obj


def update_job_context(
    base_url: str, headers: Dict[str, str], job_id: str, new_context_obj: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        import requests  # type: ignore
    except ImportError:
        print(
            "The 'requests' package is required. Please install dependencies.",
            file=sys.stderr,
        )
        sys.exit(2)
    url = base_url.rstrip("/") + "/rest/v1/jobs"
    params = {"id": f"eq.{job_id}"}
    payload = {"context": new_context_obj}
    resp = requests.patch(url, headers=headers, params=params, json=payload, timeout=30)
    if resp.status_code not in (200, 204):
        print(
            f"Failed to update job {job_id}: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        data = resp.json()
        return data[0] if isinstance(data, list) and data else data
    except ValueError:
        return {"status": "updated"}


def main():
    parser = argparse.ArgumentParser(
        description="Relens launch to scrape and store into Supabase job context"
    )
    parser.add_argument("--job-id", required=True, help="Supabase job id (UUID)")
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

    job_row = fetch_job(base_url, headers, args.job_id)
    context_value = job_row.get("context")

    # Prefer CLI --proxy, else fall back to PROXY_URL env (if set)
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

    if not additions:
        print(
            json.dumps(
                {"status": "no_posts", "username": args.username}, ensure_ascii=False
            )
        )
        return

    new_context_obj = append_content_to_context(context_value, additions)
    update_job_context(base_url, headers, args.job_id, new_context_obj)

    print(
        json.dumps(
            {
                "status": "ok",
                "job_id": args.job_id,
                "username": args.username,
                "added": len(additions),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
