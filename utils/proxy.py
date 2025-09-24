import json
import os
import tempfile
import zipfile


def build_proxy_auth_extension(
    scheme: str, host: str, port: int, username: str, password: str
) -> str:
    """Create a temporary Chrome extension that sets a fixed proxy and handles auth.

    Returns the path to the created .zip file.
    """
    manifest = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking",
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "22.0.0",
    }

    scheme_for_ext = "socks5" if scheme.startswith("socks") else "http"
    background_js = f"""
var config = {{
  mode: "fixed_servers",
  rules: {{
    singleProxy: {{
      scheme: "{scheme_for_ext}",
      host: "{host}",
      port: parseInt({port})
    }},
    bypassList: ["localhost"]
  }}
}};

chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

function callbackFn(details) {{
  return {{ authCredentials: {{ username: "{username}", password: "{password}" }} }};
}}

chrome.webRequest.onAuthRequired.addListener(
  callbackFn,
  {{ urls: ["<all_urls>"] }},
  ['blocking']
);
"""

    tmp_dir = tempfile.mkdtemp(prefix="proxy_ext_")
    ext_zip_path = os.path.join(tmp_dir, "proxy_auth_plugin.zip")
    manifest_path = os.path.join(tmp_dir, "manifest.json")
    background_path = os.path.join(tmp_dir, "background.js")

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest))
    with open(background_path, "w", encoding="utf-8") as f:
        f.write(background_js)

    with zipfile.ZipFile(ext_zip_path, "w") as zp:
        zp.write(manifest_path, arcname="manifest.json")
        zp.write(background_path, arcname="background.js")

    return ext_zip_path
