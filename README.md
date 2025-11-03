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

### Supabase mode (uploads to Storage + inserts DB rows)
```bash
# Required env
export SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
export SUPABASE_SERVICE_ROLE="YOUR_SERVICE_ROLE_JWT"

# Run (no proxy)
python launch_and_store.py -u casamorati_dal_1888 -p 5074c6a6-8826-4838-8473-27898b4b6f2e \
  --headless --timeout 60

# Optional: force WebP
python launch_and_store.py -u casamorati_dal_1888 -p 5074c6a6-8826-4838-8473-27898b4b6f2e \
  --convert-webp --headless --timeout 60

# Optional: proxy
python launch_and_store.py -u casamorati_dal_1888 -p 5074c6a6-8826-4838-8473-27898b4b6f2e \
  --headless --timeout 60 \
  --proxy "http://USERNAME-res-us:PASSWORD@proxy-us.proxy-cheap.com:5959"
```

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
  python3 launch_and_store.py \
    -u casamorati_dal_1888 -p 5074c6a6-8826-4838-8473-27898b4b6f2e \
    --headless --timeout 60
```

Run with proxy:
```bash
docker run --rm -it ig-scraper:latest \
  python3 launch_and_store.py \
    -u casamorati_dal_1888 -p 5074c6a6-8826-4838-8473-27898b4b6f2e \
    --headless --timeout 60 \
    --proxy "http://USERNAME-res-us:PASSWORD@proxy-us.proxy-cheap.com:5959"
```

---

## Fly.io deploy (outline)
```bash
fly auth login
fly launch --no-deploy --copy-config --name your-unique-app
# Optional: proxy secret
fly secrets set PROXY_URL="http://USERNAME-res-us:PASSWORD@proxy-us.proxy-cheap.com:5959"
# In fly.toml you can set command like (or via Machines config.init.cmd):
# [experimental]
#  cmd = [
#    "python3","launch_and_store.py",
#    "-u","${USERNAME}","-p","${PROJECT_ID}",
#    "--headless","--timeout","${TIMEOUT}","--debug",
#    "--convert-webp",
#    "--proxy","${PROXY_URL}"
#  ]
fly deploy
```

---

## Requirements
- Python 3.12+
- Google Chrome (Docker image installs it for you)

## Project Layout
```
├── launch.py            # CLI for printing JSON to stdout
├── launch_and_store.py  # Entrypoint (uploads images to Storage and inserts DB rows)
├── scraper.py           # Core logic (Selenium/selenium-wire)
├── utils/               # Helpers (debug, proxy extension)
├── requirements.txt
├── Dockerfile
└── README.md
```

## Legal
Accesses only publicly available data. You are responsible for complying with Instagram’s Terms and applicable laws.

---

### Attribution
Based on and adapted from [mr-teslaa/instagram_user_post_scraper](https://github.com/mr-teslaa/instagram_user_post_scraper).

### License
Licensed under the "Don't Be A Dick" Public License (DBAD) v1.1. See `LICENSE` for the full text. Learn more at [dbad-license.org](https://dbad-license.org/).

### Supabase storage details
- Bucket: `assets`
- Object key format: `<project_id>/<sha1>.<ext>`
  - With `--convert-webp`, images are converted before upload and saved as `.webp` (`Content-Type: image/webp`).
  - Without conversion, extension is inferred from the response content type or URL.
- Table: `assets` (one row per image)
  - `project_id`: UUID, provided at runtime
  - `filename`: Storage key (same as object path)
  - `type`: `image`
  - `metadata`: `{ "source": "instagram", "instagram": "<username>", "run_id": "<uuid>" }`
  - `description`: caption text (may be empty)

Example object key:
```
5074c6a6-8826-4838-8473-27898b4b6f2e/8e016b834aa09258.webp
```

Example `assets` row:
```json
{
  "project_id": "5074c6a6-8826-4838-8473-27898b4b6f2e",
  "filename": "5074c6a6-8826-4838-8473-27898b4b6f2e/8e016b834aa09258.webp",
  "type": "image",
  "metadata": {
    "source": "instagram",
    "instagram": "casamorati_dal_1888",
    "run_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  "description": "caption text"
}
```

Secrets required: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE`. Optional `PROXY_URL`.
