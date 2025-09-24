import json
import os
from datetime import datetime


def dump_debug_artifacts(driver, prefix: str) -> None:
    try:
        os.makedirs("debug", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join("debug", f"{prefix}_{ts}")
        try:
            with open(base + ".html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"[DEBUG] Saved HTML to {base}.html")
        except Exception as e:
            print(f"[DEBUG] Failed to save HTML: {e}")
        try:
            driver.save_screenshot(base + ".png")
            print(f"[DEBUG] Saved screenshot to {base}.png")
        except Exception as e:
            print(f"[DEBUG] Failed to save screenshot: {e}")
        try:
            logs = driver.get_log("browser") or []
            with open(base + ".log", "w", encoding="utf-8") as f:
                for entry in logs:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"[DEBUG] Saved console log to {base}.log")
        except Exception as e:
            print(f"[DEBUG] Failed to collect console logs: {e}")
    except Exception as e:
        print(f"[DEBUG] Unexpected error while writing debug artifacts: {e}")
