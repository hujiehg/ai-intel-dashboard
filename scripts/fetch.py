"""拉取 5 家公司的近 7 天精选动态，缓存到 cache/YYYY-MM-DD/<Company>.json"""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    COMPANIES, API_ITEMS, UA, WINDOW_DAYS, TAKE, CACHE_DIR
)


def fetch_all():
    since = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).isoformat().replace("+00:00", "Z")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_dir = CACHE_DIR / today
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"[fetch] since={since}  take={TAKE}  cache={cache_dir}")
    results = {}
    for kw in COMPANIES:
        out_file = cache_dir / f"{kw}.json"
        url = f"{API_ITEMS}?mode=selected&q={kw}&since={since}&take={TAKE}"
        # 用 curl 带 UA 调 API（aihot /api/public/* 必须 UA，否则 403）
        try:
            subprocess.run(
                ["curl", "-sH", f"User-Agent: {UA}", url, "-o", str(out_file)],
                check=True, timeout=60
            )
            with open(out_file, "r", encoding="utf-8") as f:
                d = json.load(f)
            n = len(d.get("items", []))
            print(f"  {kw:10s} → {n} items  ({out_file.name})")
            results[kw] = d
        except Exception as e:
            print(f"  {kw:10s} → FAIL: {e}", file=sys.stderr)
            results[kw] = {"items": [], "error": str(e)}
    return results, cache_dir


if __name__ == "__main__":
    fetch_all()
