"""根据合并后的数据生成单文件 HTML 看板"""
import html
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    PROJECT_ROOT, COMPANIES, ALIAS_HIGHLIGHT, CATEGORY_STYLE,
    SUMMARY_MAX_CHARS, LATEST_HTML, WINDOW_DAYS
)

BJ_TZ = timezone(timedelta(hours=8))


def _truncate(s, n=SUMMARY_MAX_CHARS):
    if not s:
        return ""
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "…"


def _highlight(text, terms):
    """HTML 转义后高亮关键词（case-insensitive）"""
    if not text:
        return ""
    safe = html.escape(text)
    sorted_terms = sorted(set(terms), key=len, reverse=True)
    if not sorted_terms:
        return safe
    pattern = re.compile("(" + "|".join(re.escape(t) for t in sorted_terms) + ")", re.IGNORECASE)
    return pattern.sub(lambda m: f'<mark>{html.escape(m.group(0))}</mark>', safe)


def _relative_time(iso_str, now_utc):
    if not iso_str:
        return "时间未知"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return "时间未知"
    bj = dt.astimezone(BJ_TZ)
    diff = now_utc - dt
    secs = int(diff.total_seconds())
    if secs < 0:
        return "刚刚"
    if secs < 60:
        return f"{secs} 秒前"
    if secs < 3600:
        return f"{secs // 60} 分钟前"
    if secs < 86400:
        return f"{secs // 3600} 小时前 · {bj.strftime('%H:%M')}"
    if secs < 86400 * 2:
        return f"昨天 {bj.strftime('%H:%M')}"
    if secs < 86400 * 7:
        return f"{secs // 86400} 天前 · {bj.strftime('%m-%d %H:%M')}"
    return bj.strftime("%m-%d %H:%M")


def _absolute_time(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except Exception:
        return ""
    return dt.astimezone(BJ_TZ).strftime("%Y-%m-%d %H:%M")


def build_html(data, out_path=LATEST_HTML):
    now_utc = datetime.now(timezone.utc)
    highlight_terms = data["highlight_terms"]

    # 时间窗
    window_start_bj = (now_utc - timedelta(days=WINDOW_DAYS)).astimezone(BJ_TZ).strftime("%Y-%m-%d %H:%M")
    now_bj = now_utc.astimezone(BJ_TZ).strftime("%Y-%m-%d %H:%M")

    # sections
    sections_html = []
    for s in data["sections"]:
        label = s["label"]
        style = CATEGORY_STYLE[label]
        items_html = []
        for it in s["items"]:
            seq = it["seq"]
            title = _highlight(it.get("title") or "", highlight_terms)
            source = html.escape(it.get("source") or "")
            rel = _relative_time(it.get("publishedAt"), now_utc)
            abs_t = _absolute_time(it.get("publishedAt"))
            summary = _highlight(_truncate(it.get("summary")), highlight_terms)
            url = html.escape(it.get("url") or "")
            hits = it.get("hits", [])
            hits_html = "".join(
                f'<span class="hit-tag">{html.escape(h)}</span>' for h in hits
            )
            items_html.append(f"""
        <article class="item">
          <div class="seq">{seq}</div>
          <div class="item-body">
            <div class="item-head">
              <a class="item-title" href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>
              <div class="item-hits">{hits_html}</div>
            </div>
            <div class="item-meta">
              <span class="source" title="{source}">{source}</span>
              <span class="dot">·</span>
              <span class="time" title="{abs_t} 北京时间">{rel}</span>
            </div>
            {f'<p class="item-summary">{summary}</p>' if summary else ''}
            <a class="item-link" href="{url}" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a>
          </div>
        </article>""")
        sections_html.append(f"""
    <section class="cat-section" id="cat-{s['category']}">
      <header class="cat-header" style="--cat-color:{style['color']};--cat-bg:{style['bg']}">
        <span class="cat-icon">{style['icon']}</span>
        <h2 class="cat-title">{label}</h2>
        <span class="cat-count">{len(s['items'])}</span>
      </header>
      <div class="cat-items">
        {''.join(items_html)}
      </div>
    </section>""")

    # KPI
    cat_counts = data["category_counts"]
    total = data["total"]
    max_cat = max(cat_counts.values()) if cat_counts else 1
    cat_dist_html = "".join(
        f"""<div class="cat-bar-row">
      <span class="cat-bar-label" style="color:{CATEGORY_STYLE[k]['color']}">{k}</span>
      <div class="cat-bar-track"><div class="cat-bar-fill" style="width:{(v/max_cat*100):.0f}%;background:{CATEGORY_STYLE[k]['color']}"></div></div>
      <span class="cat-bar-num">{v}</span>
    </div>"""
        for k, v in cat_counts.items()
    )
    keywords_html = "".join(
        f'<span class="kw-chip">{html.escape(kw)}</span>' for kw in data["keywords"]
    )

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>顶尖 AI 公司动态情报看板 · 近 7 天</title>
<style>
  :root {{
    --bg: #f5f6f8;
    --card: #ffffff;
    --border: #e5e7eb;
    --text: #1f2937;
    --text-muted: #6b7280;
    --text-light: #9ca3af;
    --primary: #1a56db;
    --primary-light: #eff6ff;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-hover: 0 4px 12px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04);
    --radius: 12px;
    --radius-sm: 8px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 24px 20px 60px; }}
  .header {{
    background: linear-gradient(135deg, #1e3a8a 0%, #1a56db 50%, #6366f1 100%);
    color: #fff;
    border-radius: var(--radius);
    padding: 28px 28px 24px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
  }}
  .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }}
  .header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.3px; }}
  .header .subtitle {{ font-size: 13px; opacity: 0.9; }}
  .header .badge {{
    background: rgba(255,255,255,0.18);
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
    backdrop-filter: blur(4px);
  }}
  .header-kw {{ margin-top: 14px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .header-kw .kw-chip {{
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 24px;
  }}
  .kpi-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    box-shadow: var(--shadow);
  }}
  .kpi-label {{
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }}
  .kpi-value {{ font-size: 24px; font-weight: 700; color: var(--text); line-height: 1.2; }}
  .kpi-sub {{ font-size: 12px; color: var(--text-light); margin-top: 4px; }}
  .kpi-card.keywords .kw-chips {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }}
  .kpi-card.keywords .kw-chip {{
    background: var(--primary-light);
    color: var(--primary);
    padding: 3px 8px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: 500;
  }}
  .kpi-card.distribution .cat-bar-row {{
    display: grid;
    grid-template-columns: 80px 1fr 28px;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    font-size: 12px;
  }}
  .cat-bar-label {{ font-weight: 500; }}
  .cat-bar-track {{ background: #f3f4f6; border-radius: 4px; height: 8px; overflow: hidden; }}
  .cat-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s ease; }}
  .cat-bar-num {{ text-align: right; color: var(--text-muted); font-variant-numeric: tabular-nums; }}
  .cat-section {{ margin-bottom: 28px; }}
  .cat-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: var(--cat-bg);
    border-left: 4px solid var(--cat-color);
    border-radius: var(--radius-sm);
    margin-bottom: 12px;
  }}
  .cat-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px; height: 26px;
    border-radius: 6px;
    background: var(--cat-color);
    color: #fff;
    font-size: 13px;
    font-weight: 700;
  }}
  .cat-title {{ font-size: 16px; font-weight: 700; color: var(--text); flex: 1; }}
  .cat-count {{
    background: var(--cat-color);
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 999px;
    font-variant-numeric: tabular-nums;
  }}
  .cat-items {{ display: flex; flex-direction: column; gap: 10px; }}
  .item {{
    display: flex;
    gap: 14px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    transition: box-shadow 0.15s, transform 0.15s;
  }}
  .item:hover {{ box-shadow: var(--shadow-hover); transform: translateY(-1px); }}
  .seq {{
    flex-shrink: 0;
    width: 28px; height: 28px;
    border-radius: 6px;
    background: #f3f4f6;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }}
  .item-body {{ flex: 1; min-width: 0; }}
  .item-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }}
  .item-title {{
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    text-decoration: none;
    line-height: 1.4;
    flex: 1;
    min-width: 0;
  }}
  .item-title:hover {{ color: var(--primary); }}
  .item-hits {{ display: flex; gap: 4px; flex-shrink: 0; flex-wrap: wrap; }}
  .hit-tag {{
    background: #fef3c7;
    color: #92400e;
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    border: 1px solid #fde68a;
  }}
  .item-meta {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 6px;
    flex-wrap: wrap;
  }}
  .source {{ font-weight: 500; color: var(--text); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .dot {{ color: var(--text-light); }}
  .time {{ font-variant-numeric: tabular-nums; }}
  .item-summary {{
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.6;
    margin-top: 8px;
  }}
  .item-link {{
    display: inline-block;
    margin-top: 8px;
    font-size: 12px;
    color: var(--primary);
    text-decoration: none;
    font-weight: 500;
  }}
  .item-link:hover {{ text-decoration: underline; }}
  mark {{
    background: #fef08a;
    color: #713f12;
    padding: 0 2px;
    border-radius: 3px;
    font-weight: 600;
  }}
  .footer {{
    text-align: center;
    font-size: 12px;
    color: var(--text-light);
    padding: 24px 0 0;
    border-top: 1px solid var(--border);
    margin-top: 20px;
  }}
  .footer a {{ color: var(--primary); text-decoration: none; }}
  .toc {{
    position: sticky;
    top: 12px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    z-index: 10;
  }}
  .toc-label {{ font-size: 12px; color: var(--text-muted); font-weight: 600; margin-right: 4px; }}
  .toc a {{
    font-size: 12px;
    padding: 3px 9px;
    border-radius: 5px;
    text-decoration: none;
    background: #f3f4f6;
    color: var(--text);
    font-weight: 500;
    transition: background 0.15s;
  }}
  .toc a:hover {{ background: var(--primary-light); color: var(--primary); }}
  @media (max-width: 768px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .header h1 {{ font-size: 19px; }}
    .item {{ padding: 12px; gap: 10px; }}
    .item-title {{ font-size: 14px; }}
    .seq {{ width: 24px; height: 24px; font-size: 12px; }}
    .container {{ padding: 16px 12px 40px; }}
  }}
  @media (max-width: 480px) {{
    .kpi-grid {{ grid-template-columns: 1fr; }}
    .item-head {{ flex-direction: column; align-items: flex-start; }}
    .item-hits {{ margin-top: 4px; }}
  }}
</style>
</head>
<body>
<div class="container">

  <header class="header">
    <div class="header-top">
      <div>
        <h1>顶尖 AI 公司动态情报看板</h1>
        <div class="subtitle">追踪 Anthropic · OpenAI · DeepSeek · Kimi · Qwen 近 7 天关键动态</div>
      </div>
      <span class="badge">数据来自 aihot.virxact.com</span>
    </div>
    <div class="header-kw">
      {keywords_html}
    </div>
  </header>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">时间窗</div>
      <div class="kpi-value">{WINDOW_DAYS} 天</div>
      <div class="kpi-sub">{window_start_bj} ~ {now_bj}（北京时间）</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">命中总数</div>
      <div class="kpi-value">{total}</div>
      <div class="kpi-sub">条去重后的精选动态</div>
    </div>
    <div class="kpi-card keywords">
      <div class="kpi-label">追踪关键词</div>
      <div class="kw-chips">
        {keywords_html}
      </div>
    </div>
    <div class="kpi-card distribution">
      <div class="kpi-label">分类分布</div>
      {cat_dist_html}
    </div>
  </div>

  <nav class="toc">
    <span class="toc-label">跳转：</span>
    {''.join(f'<a href="#cat-{s["category"]}">{s["label"]} ({len(s["items"])})</a>' for s in data["sections"])}
  </nav>

  {''.join(sections_html)}

  <footer class="footer">
    生成时间 {now_bj}（北京时间）· 数据源 <a href="https://aihot.virxact.com" target="_blank" rel="noopener noreferrer">aihot.virxact.com</a> · 仅供内部情报参考
  </footer>

</div>
</body>
</html>
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    return out_path


if __name__ == "__main__":
    # 从 stdin 或默认 merge 输出读取
    import json as _json
    data_path = PROJECT_ROOT / "cache" / "_dashboard-data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = _json.load(f)
    out = build_html(data)
    print(f"[build_html] wrote {out}  ({out.stat().st_size} bytes)")
