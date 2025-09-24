import argparse
import json

from scraper import scrape_instagram_profile


def main():
    parser = argparse.ArgumentParser(description="Instagram profile scraper")
    parser.add_argument("--username", "-u", required=True, help="Instagram username")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout seconds")
    parser.add_argument(
        "--debug", action="store_true", help="Enable verbose debug and dumps"
    )
    parser.add_argument("--proxy", help="Proxy URL (http(s) or socks5), auth supported")
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        help="Run headless (default)",
    )
    headless_group.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Run with browser UI",
    )
    parser.set_defaults(headless=True)
    args = parser.parse_args()

    data = scrape_instagram_profile(
        args.username,
        headless=args.headless,
        timeout=args.timeout,
        debug=args.debug,
        proxy=args.proxy,
    )
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
