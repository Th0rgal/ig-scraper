## 📸 Instagram Profile Scraper (Headless, Proxy-ready)

Scrapes public Instagram profiles without logging in and prints post images + captions as JSON.

### Features
- Headless Chrome (Selenium + Selenium Manager)
- Optional HTTP/HTTPS or SOCKS5 proxies (headless via selenium-wire)
- Rotation-ready (session id in proxy username)
- Debug prints outbound IP and can dump HTML/screenshot/logs

---

## Quickstart (Local with uv)
```bash
uv venv
source .venv/bin/activate
uv pip install --upgrade --requirements requirements.txt

# No proxy
python launch.py -u casamorati_dal_1888 --headless --timeout 60

# HTTP CONNECT proxy (example)
python launch.py -u casamorati_dal_1888 --headless --timeout 60 --debug \
  --proxy "http://USERNAME-res-us:PASSWORD@proxy-us.proxy-cheap.com:5959"

# Rotate per run (random session id)
python launch.py -u casamorati_dal_1888 --headless --timeout 60 --debug \
  --proxy "http://USERNAME-res-us-sid-$(python - <<<'import secrets;print(secrets.token_hex(4))'):PASSWORD@proxy-us.proxy-cheap.com:5959"

# SOCKS5 with remote DNS (if supported)
python launch.py -u casamorati_dal_1888 --headless --timeout 60 --debug \
  --proxy "socks5h://USERNAME-res-us:PASSWORD@proxy-us.proxy-cheap.com:9595"
```

Output is printed to stdout as JSON. See `output.json` for a sample.

---

## Docker
Build (native arch):
```bash
docker build -t ig-scraper:latest .
```

Build for x86_64 on Apple Silicon:
```bash
docker buildx build --platform linux/amd64 -t ig-scraper:latest .
```

Run without proxy:
```bash
docker run --rm -it ig-scraper:latest \
  python3 launch.py -u casamorati_dal_1888 --headless --timeout 60
```

Run with proxy:
```bash
docker run --rm -it ig-scraper:latest \
  python3 launch.py -u casamorati_dal_1888 --headless --timeout 60 \
  --proxy "http://USERNAME-res-us:PASSWORD@proxy-us.proxy-cheap.com:5959"
```

---

## Fly.io deploy (outline)
```bash
fly auth login
fly launch --no-deploy --copy-config --name your-unique-app
# Optional: proxy secret
fly secrets set PROXY_URL="http://USERNAME-res-us:PASSWORD@proxy-us.proxy-cheap.com:5959"
# In fly.toml set command like:
# [experimental]
#  cmd = ["python3","launch.py","-u","casamorati_dal_1888","--headless","--timeout","60","--debug","--proxy","${PROXY_URL}"]
fly deploy
```

---

## Requirements
- Python 3.12+
- Google Chrome (Docker image installs it for you)

## Project Layout
```
├── launch.py            # CLI entrypoint
├── scraper.py           # Core logic (Selenium/selenium-wire)
├── utils/               # Helpers (debug, proxy extension)
├── requirements.txt
├── Dockerfile
└── README.md
```

## Legal
Accesses only publicly available data. You are responsible for complying with Instagram’s Terms and applicable laws.
