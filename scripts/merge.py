"""合并 5 份检索结果，按 id 去重，按 category 分组，全局连续编号"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    COMPANIES, ALIAS_HIGHLIGHT, CATEGORY_ORDER, CATEGORY_LABEL,
    CATEGORY_NULL_FALLBACK, CACHE_DIR
)


def _parse_dt(s):
    if not s:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def merge_from_cache(cache_dir: Path):
    """从指定 cache 目录读取 5 份 JSON 并合并"""
    merged = {}  # id -> item with extra "hits" list
    for kw in COMPANIES:
        p = cache_dir / f"{kw}.json"
        if not p.exists():
            print(f"[merge] WARN: {p} not found, skip", file=sys.stderr)
            continue
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        for it in d.get("items", []):
            iid = it["id"]
            if iid not in merged:
                it["hits"] = [kw]
                merged[iid] = it
            else:
                if kw not in merged[iid]["hits"]:
                    merged[iid]["hits"].append(kw)
    return list(merged.values())


def build_dashboard_data(all_items):
    """构造分组结构 + 全局连续编号"""
    # 统计 category 分布
    cat_count = {c: 0 for c in CATEGORY_ORDER}
    for it in all_items:
        c = it.get("category") or CATEGORY_NULL_FALLBACK
        if c in cat_count:
            cat_count[c] += 1
        else:
            cat_count[CATEGORY_NULL_FALLBACK] += 1

    # 按 category 分组 + 每组内按 publishedAt 倒序
    groups = {c: [] for c in CATEGORY_ORDER}
    for it in all_items:
        c = it.get("category") or CATEGORY_NULL_FALLBACK
        if c not in groups:
            c = CATEGORY_NULL_FALLBACK
        groups[c].append(it)
    for c in groups:
        groups[c].sort(key=lambda x: _parse_dt(x.get("publishedAt")), reverse=True)

    # 全局连续编号：按 CATEGORY_ORDER 顺序，每组内按时间倒序
    seq = 0
    sections = []
    for c in CATEGORY_ORDER:
        items = groups.get(c, [])
        if not items:
            continue
        for it in items:
            seq += 1
            it["seq"] = seq
        sections.append({
            "category": c,
            "label": CATEGORY_LABEL[c],
            "items": items,
        })

    now_utc = datetime.now(timezone.utc)
    return {
        "generated_at_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "keywords": COMPANIES,
        "highlight_terms": COMPANIES + ALIAS_HIGHLIGHT,
        "total": len(all_items),
        "category_counts": {CATEGORY_LABEL[c]: cat_count[c] for c in CATEGORY_ORDER},
        "sections": sections,
    }


if __name__ == "__main__":
    # 默认用今天的 cache
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_dir = CACHE_DIR / today
    items = merge_from_cache(cache_dir)
    data = build_dashboard_data(items)
    print(f"[merge] {len(items)} unique items, {len(data['sections'])} sections")
    for s in data["sections"]:
        print(f"  {s['label']}: {len(s['items'])}")
