"""一键执行：fetch → merge → build_html → archive

用法：
    python scripts/run.py            # 完整流程，归档到 dashboard-history/
    python scripts/run.py --no-fetch # 跳过拉取，用今天已有 cache 重新生成
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    PROJECT_ROOT, LATEST_HTML, HISTORY_DIR, CACHE_DIR, DIST_DIR, DIST_INDEX,
)
from fetch import fetch_all
from merge import merge_from_cache, build_dashboard_data
from build_html import build_html

BJ_TZ = timezone(timedelta(hours=8))


def main():
    args = sys.argv[1:]
    no_fetch = "--no-fetch" in args

    if no_fetch:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cache_dir = CACHE_DIR / today
        if not cache_dir.exists():
            print(f"[run] ERROR: cache dir {cache_dir} not found, cannot --no-fetch", file=sys.stderr)
            sys.exit(1)
        print(f"[run] --no-fetch: reuse {cache_dir}")
    else:
        _, cache_dir = fetch_all()

    # merge
    items = merge_from_cache(cache_dir)
    data = build_dashboard_data(items)
    # 暂存合并数据（便于 build_html 独立运行调试）
    data_path = CACHE_DIR / "_dashboard-data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[run] merged {len(items)} items → {data_path}")

    # build latest
    out = build_html(data, LATEST_HTML)
    print(f"[run] latest → {out}")

    # archive to dashboard-history/dashboard-YYYY-MM-DD.html
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    bj_today = datetime.now(BJ_TZ).strftime("%Y-%m-%d")
    archive_path = HISTORY_DIR / f"dashboard-{bj_today}.html"
    # 复制最新版内容到归档
    with open(LATEST_HTML, "r", encoding="utf-8") as f:
        content = f.read()
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[run] archived → {archive_path}")

    # 同步到 dist/index.html（用于云端部署）
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with open(DIST_INDEX, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[run] dist sync → {DIST_INDEX}")

    # 简要摘要
    print("\n=== 摘要 ===")
    print(f"生成时间: {datetime.now(BJ_TZ).strftime('%Y-%m-%d %H:%M')} 北京时间")
    print(f"命中总数: {data['total']}")
    for label, n in data["category_counts"].items():
        print(f"  {label}: {n}")


if __name__ == "__main__":
    main()
