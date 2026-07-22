"""根据合并后的数据生成单文件 HTML 看板 — Fluent Design + Glassmorphism 风格"""
import html
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    PROJECT_ROOT, COMPANIES, ALIAS_HIGHLIGHT, CATEGORY_STYLE,
    SUMMARY_MAX_CHARS, LATEST_HTML, WINDOW_DAYS,
)

BJ_TZ = timezone(timedelta(hours=8))


def _truncate(s, n=SUMMARY_MAX_CHARS):
    if not s:
        return ""
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "…"


def _highlight(text, terms):
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
    window_start_bj = (now_utc - timedelta(days=WINDOW_DAYS)).astimezone(BJ_TZ).strftime("%Y-%m-%d %H:%M")
    now_bj = now_utc.astimezone(BJ_TZ).strftime("%Y-%m-%d %H:%M")

    # --- sections HTML ---
    sections_html = []
    items_json_list = []  # 完整条目数据，供 modal 详情使用
    idx = 0
    for s in data["sections"]:
        label = s["label"]
        style = CATEGORY_STYLE[label]
        items_html = []
        for it in s["items"]:
            idx += 1
            seq = it["seq"]
            raw_title = it.get("title") or ""
            raw_title_en = it.get("title_en") or ""
            raw_summary = it.get("summary") or ""
            title = _highlight(raw_title, highlight_terms)
            source = html.escape(it.get("source") or "")
            rel = _relative_time(it.get("publishedAt"), now_utc)
            abs_t = _absolute_time(it.get("publishedAt"))
            summary = _highlight(_truncate(raw_summary), highlight_terms)
            url = html.escape(it.get("url") or "")
            hits = it.get("hits", [])
            hits_html = "".join(
                f'<span class="hit-tag" data-hit="{html.escape(h)}">{html.escape(h)}</span>' for h in hits
            )
            cat = it.get("category") or "industry"
            # 收集完整数据供 modal 用
            items_json_list.append({
                "seq": seq, "title": raw_title, "title_en": raw_title_en,
                "summary": raw_summary, "source": it.get("source") or "",
                "url": it.get("url") or "", "time_rel": rel, "time_abs": abs_t,
                "category": cat, "category_label": label,
                "category_color": style['color'], "hits": hits,
            })
            items_html.append(f"""        <article class="card reveal" data-idx="{idx-1}" data-category="{cat}" data-hits="{','.join(hits)}" style="--cat-color:{style['color']}" tabindex="0" role="button" aria-label="查看详情">
          <div class="card-shine"></div>
          <div class="seq-badge">{seq}</div>
          <div class="card-body">
            <div class="card-head">
              <h3 class="card-title">{title}</h3>
              <div class="card-hits">{hits_html}</div>
            </div>
            <div class="card-meta">
              <span class="source" title="{source}">{source}</span>
              <span class="dot">·</span>
              <span class="time" title="{abs_t} 北京时间">{rel}</span>
              <span class="dot">·</span>
              <span class="card-expand">详情</span>
            </div>
            {f'<p class="card-summary">{summary}</p>' if summary else ''}
          </div>
        </article>""")
        sections_html.append(f"""    <section class="cat-section" id="cat-{s['category']}" data-cat="{s['category']}">
      <header class="cat-header" style="--cat-color:{style['color']};--cat-bg:{style['bg']}">
        <span class="cat-dot"></span>
        <h2 class="cat-title">{label}</h2>
        <span class="cat-count">{len(s['items'])}</span>
      </header>
      <div class="cat-items">
        {''.join(items_html)}
      </div>
    </section>""")

    # --- KPI ---
    cat_counts = data["category_counts"]
    total = data["total"]
    max_cat = max(cat_counts.values()) if cat_counts else 1
    cat_dist_html = "".join(
        f"""<div class="cat-bar-row">
      <span class="cat-bar-label" style="color:{CATEGORY_STYLE[k]['color']}">{k}</span>
      <div class="cat-bar-track"><div class="cat-bar-fill" data-target="{v/max_cat*100:.0f}" style="--fill-color:{CATEGORY_STYLE[k]['color']}"></div></div>
      <span class="cat-bar-num">{v}</span>
    </div>"""
        for k, v in cat_counts.items()
    )
    keywords_html = "".join(
        f'<span class="kw-chip">{html.escape(kw)}</span>' for kw in data["keywords"]
    )

    # --- category filter chips ---
    filter_chips_html = '<button class="filter-chip active" data-filter="all">全部 <span class="chip-count">' + str(total) + '</span></button>'
    for s in data["sections"]:
        st = CATEGORY_STYLE[s["label"]]
        filter_chips_html += f'<button class="filter-chip" data-filter="{s["category"]}" style="--chip-color:{st["color"]}">{s["label"]} <span class="chip-count">{len(s["items"])}</span></button>'

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>顶尖 AI 公司动态情报看板 · 近 7 天</title>
<style>
  :root {{
    --bg-base: #f0f2f5;
    --text: #1a1a2e;
    --text-2: #4a4a6a;
    --text-3: #8a8aa0;
    --glass-bg: rgba(255,255,255,0.55);
    --glass-bg-strong: rgba(255,255,255,0.72);
    --glass-border: rgba(255,255,255,0.6);
    --glass-border-hover: rgba(255,255,255,0.9);
    --shadow-sm: 0 1px 2px rgba(20,20,50,0.04), 0 2px 8px rgba(20,20,50,0.04);
    --shadow-md: 0 4px 16px rgba(20,20,50,0.06), 0 8px 32px rgba(20,20,50,0.04);
    --shadow-lg: 0 8px 32px rgba(20,20,50,0.08), 0 16px 48px rgba(20,20,50,0.06);
    --radius: 16px;
    --radius-sm: 10px;
    --ease: cubic-bezier(0.4, 0, 0.2, 1);
    --ease-out: cubic-bezier(0, 0, 0.2, 1);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg-base);
    color: var(--text);
    line-height: 1.6;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    overflow-x: hidden;
  }}

  /* --- 流动背景光斑 --- */
  .bg-orbs {{
    position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none;
  }}
  .orb {{
    position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.35;
    animation: orb-float 28s var(--ease) infinite;
  }}
  .orb-1 {{ width: 520px; height: 520px; background: radial-gradient(circle, #a78bfa, transparent 70%); top: -120px; left: -80px; animation-delay: 0s; }}
  .orb-2 {{ width: 460px; height: 460px; background: radial-gradient(circle, #60a5fa, transparent 70%); top: 30%; right: -100px; animation-delay: -7s; }}
  .orb-3 {{ width: 400px; height: 400px; background: radial-gradient(circle, #f9a8d4, transparent 70%); bottom: -100px; left: 25%; animation-delay: -14s; }}
  .orb-4 {{ width: 340px; height: 340px; background: radial-gradient(circle, #fbbf24, transparent 70%); top: 55%; left: 10%; animation-delay: -21s; opacity: 0.25; }}
  @keyframes orb-float {{
    0%, 100% {{ transform: translate(0,0) scale(1); }}
    25% {{ transform: translate(60px,-40px) scale(1.08); }}
    50% {{ transform: translate(-30px,50px) scale(0.95); }}
    75% {{ transform: translate(40px,30px) scale(1.05); }}
  }}

  /* --- 顶部进度条 --- */
  .scroll-progress {{
    position: fixed; top: 0; left: 0; height: 3px; width: 0%;
    background: linear-gradient(90deg, #7c3aed, #2563eb, #db2777);
    z-index: 100; transition: width 0.1s linear;
    box-shadow: 0 0 8px rgba(124,58,237,0.4);
  }}

  .container {{ position: relative; z-index: 1; max-width: 1120px; margin: 0 auto; padding: 28px 20px 80px; }}

  /* --- Hero --- */
  .hero {{
    position: relative;
    border-radius: 24px;
    padding: 40px 36px 32px;
    margin-bottom: 20px;
    background: var(--glass-bg-strong);
    backdrop-filter: blur(40px) saturate(180%);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
    border: 1px solid var(--glass-border);
    box-shadow: var(--shadow-md);
    overflow: hidden;
  }}
  .hero::before {{
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(135deg, rgba(124,58,237,0.06), rgba(37,99,235,0.04) 50%, rgba(219,39,119,0.05));
    pointer-events: none;
  }}
  .hero-top {{ position: relative; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }}
  .hero h1 {{
    font-size: 28px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 8px;
    background: linear-gradient(135deg, #1a1a2e 0%, #4c1d95 50%, #1e40af 100%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .hero .subtitle {{ font-size: 14px; color: var(--text-2); }}
  .hero .badge {{
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.5); border: 1px solid var(--glass-border);
    padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 500; color: var(--text-2);
    backdrop-filter: blur(8px);
  }}
  .hero .badge::before {{ content: ''; width: 6px; height: 6px; border-radius: 50%; background: #10b981; box-shadow: 0 0 6px #10b981; }}
  .hero-kw {{ position: relative; margin-top: 18px; display: flex; flex-wrap: wrap; gap: 8px; }}
  .hero-kw .kw-chip {{
    background: rgba(255,255,255,0.4); border: 1px solid var(--glass-border);
    padding: 5px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; color: var(--text);
    backdrop-filter: blur(8px); transition: transform 0.2s var(--ease), background 0.2s;
  }}
  .hero-kw .kw-chip:hover {{ transform: translateY(-2px); background: rgba(255,255,255,0.7); }}

  /* --- KPI grid --- */
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px;
  }}
  .kpi-card {{
    background: var(--glass-bg); backdrop-filter: blur(24px) saturate(160%);
    -webkit-backdrop-filter: blur(24px) saturate(160%);
    border: 1px solid var(--glass-border); border-radius: var(--radius);
    padding: 18px 20px; box-shadow: var(--shadow-sm);
    transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease);
    position: relative; overflow: hidden;
  }}
  .kpi-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-md); }}
  .kpi-label {{ font-size: 11px; color: var(--text-3); font-weight: 600; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.6px; }}
  .kpi-value {{ font-size: 28px; font-weight: 800; color: var(--text); line-height: 1; letter-spacing: -0.5px; font-variant-numeric: tabular-nums; }}
  .kpi-sub {{ font-size: 11px; color: var(--text-3); margin-top: 6px; }}
  .kpi-card.keywords .kw-chips {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }}
  .kpi-card.keywords .kw-chip {{
    background: rgba(124,58,237,0.08); color: #6d28d9;
    padding: 3px 9px; border-radius: 6px; font-size: 11px; font-weight: 600;
  }}
  .kpi-card.distribution .cat-bar-row {{
    display: grid; grid-template-columns: 76px 1fr 24px; align-items: center; gap: 8px; margin-top: 7px; font-size: 11px;
  }}
  .cat-bar-label {{ font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .cat-bar-track {{ background: rgba(0,0,0,0.05); border-radius: 4px; height: 6px; overflow: hidden; }}
  .cat-bar-fill {{ height: 100%; width: 0%; border-radius: 4px; background: var(--fill-color); transition: width 1s var(--ease-out); }}
  .cat-bar-num {{ text-align: right; color: var(--text-3); font-variant-numeric: tabular-nums; font-weight: 600; }}

  /* --- 控制栏（sticky glass） --- */
  .control-bar {{
    position: sticky; top: 10px; z-index: 50;
    background: var(--glass-bg-strong); backdrop-filter: blur(32px) saturate(180%);
    -webkit-backdrop-filter: blur(32px) saturate(180%);
    border: 1px solid var(--glass-border); border-radius: var(--radius);
    padding: 12px 16px; box-shadow: var(--shadow-md); margin-bottom: 24px;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }}
  .search-box {{
    flex: 1; min-width: 200px; position: relative;
  }}
  .search-box input {{
    width: 100%; padding: 8px 12px 8px 34px; border: 1px solid var(--glass-border);
    border-radius: 10px; background: rgba(255,255,255,0.5); font-size: 13px; color: var(--text);
    font-family: inherit; outline: none; transition: border-color 0.2s, background 0.2s;
  }}
  .search-box input:focus {{ border-color: #7c3aed; background: rgba(255,255,255,0.85); }}
  .search-box input::placeholder {{ color: var(--text-3); }}
  .search-box::before {{
    content: '🔍'; position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
    font-size: 13px; opacity: 0.5;
  }}
  .filter-chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .filter-chip {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: 6px 12px; border-radius: 8px; border: 1px solid var(--glass-border);
    background: rgba(255,255,255,0.4); font-size: 12px; font-weight: 600; color: var(--text-2);
    cursor: pointer; font-family: inherit; transition: all 0.2s var(--ease);
    --chip-color: var(--text-2);
  }}
  .filter-chip:hover {{ background: rgba(255,255,255,0.7); transform: translateY(-1px); }}
  .filter-chip.active {{ background: var(--chip-color); color: #fff; border-color: var(--chip-color); }}
  .filter-chip.active .chip-count {{ background: rgba(255,255,255,0.25); color: #fff; }}
  .chip-count {{ background: rgba(0,0,0,0.08); padding: 1px 6px; border-radius: 999px; font-size: 10px; font-variant-numeric: tabular-nums; }}

  /* --- 分类 section --- */
  .cat-section {{ margin-bottom: 32px; scroll-margin-top: 80px; }}
  .cat-header {{
    display: flex; align-items: center; gap: 10px;
    padding: 12px 18px; margin-bottom: 14px;
    background: var(--glass-bg); backdrop-filter: blur(20px) saturate(160%);
    -webkit-backdrop-filter: blur(20px) saturate(160%);
    border: 1px solid var(--glass-border); border-radius: var(--radius-sm);
    border-left: 4px solid var(--cat-color);
    box-shadow: var(--shadow-sm);
  }}
  .cat-dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--cat-color); box-shadow: 0 0 8px var(--cat-color);
  }}
  .cat-title {{ font-size: 17px; font-weight: 700; color: var(--text); flex: 1; letter-spacing: -0.2px; }}
  .cat-count {{
    background: var(--cat-color); color: #fff; font-size: 12px; font-weight: 700;
    padding: 3px 10px; border-radius: 999px; font-variant-numeric: tabular-nums;
  }}

  /* --- 卡片 --- */
  .cat-items {{ display: flex; flex-direction: column; gap: 12px; }}
  .card {{
    position: relative; display: flex; gap: 16px;
    background: var(--glass-bg); backdrop-filter: blur(24px) saturate(160%);
    -webkit-backdrop-filter: blur(24px) saturate(160%);
    border: 1px solid var(--glass-border); border-radius: var(--radius);
    padding: 18px 20px; box-shadow: var(--shadow-sm);
    transition: transform 0.3s var(--ease), box-shadow 0.3s var(--ease), border-color 0.3s;
    overflow: hidden;
  }}
  .card:hover {{
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);
    border-color: var(--cat-color);
  }}
  /* Reveal 光效（鼠标跟随） */
  .card-shine {{
    position: absolute; inset: 0; border-radius: var(--radius); pointer-events: none;
    background: radial-gradient(400px circle at var(--mx,50%) var(--my,50%), rgba(255,255,255,0.18), transparent 40%);
    opacity: 0; transition: opacity 0.3s;
  }}
  .card:hover .card-shine {{ opacity: 1; }}

  .seq-badge {{
    flex-shrink: 0; width: 32px; height: 32px; border-radius: 10px;
    background: linear-gradient(135deg, var(--cat-color), color-mix(in srgb, var(--cat-color) 60%, #000));
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums;
    box-shadow: 0 2px 8px color-mix(in srgb, var(--cat-color) 40%, transparent);
  }}
  .card-body {{ flex: 1; min-width: 0; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }}
  .card-title {{
    font-size: 15px; font-weight: 600; color: var(--text); text-decoration: none;
    line-height: 1.45; flex: 1; min-width: 0; transition: color 0.2s;
  }}
  .card-title:hover {{ color: var(--cat-color); }}
  .card-hits {{ display: flex; gap: 4px; flex-shrink: 0; flex-wrap: wrap; }}
  .hit-tag {{
    background: rgba(251,191,36,0.12); color: #92400e;
    padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: 600;
    border: 1px solid rgba(251,191,36,0.3);
  }}
  .card-meta {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-3); margin-top: 8px; flex-wrap: wrap; }}
  .source {{ font-weight: 600; color: var(--text-2); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .dot {{ color: var(--text-3); }}
  .time {{ font-variant-numeric: tabular-nums; }}
  .card-summary {{ font-size: 13px; color: var(--text-2); line-height: 1.65; margin-top: 10px; }}
  .card-link {{
    display: inline-block; margin-top: 10px; font-size: 12px; color: var(--cat-color);
    text-decoration: none; font-weight: 600; transition: opacity 0.2s;
  }}
  .card-link:hover {{ opacity: 0.7; }}

  mark {{ background: rgba(251,191,36,0.35); color: #78350f; padding: 0 3px; border-radius: 3px; font-weight: 700; }}

  /* --- 滚动揭示动画 --- */
  .reveal {{ opacity: 0; transform: translateY(20px); transition: opacity 0.6s var(--ease-out), transform 0.6s var(--ease-out); }}
  .reveal.visible {{ opacity: 1; transform: translateY(0); }}

  /* --- 空状态 --- */
  .empty-state {{
    text-align: center; padding: 40px 20px; color: var(--text-3);
    background: var(--glass-bg); border-radius: var(--radius); border: 1px dashed var(--glass-border);
  }}

  /* --- Footer --- */
  .footer {{
    text-align: center; font-size: 12px; color: var(--text-3);
    padding: 32px 0 0; border-top: 1px solid var(--glass-border); margin-top: 24px;
  }}
  .footer a {{ color: #6d28d9; text-decoration: none; font-weight: 600; }}

  /* --- 响应式 --- */
  @media (max-width: 768px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .hero {{ padding: 28px 22px 24px; }}
    .hero h1 {{ font-size: 22px; }}
    .card {{ padding: 14px 16px; gap: 12px; }}
    .card-title {{ font-size: 14px; }}
    .seq-badge {{ width: 28px; height: 28px; font-size: 12px; }}
    .container {{ padding: 18px 14px 50px; }}
    .control-bar {{ padding: 10px 12px; }}
  }}
  @media (max-width: 480px) {{
    .kpi-grid {{ grid-template-columns: 1fr; }}
    .card-head {{ flex-direction: column; align-items: flex-start; }}
    .card-hits {{ margin-top: 6px; }}
    .hero h1 {{ font-size: 20px; }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .orb {{ animation: none; }}
    .reveal {{ opacity: 1; transform: none; transition: none; }}
    * {{ scroll-behavior: auto; }}
  }}

  /* --- 详情 Modal（毛玻璃 + 渐变） --- */
  .modal-overlay {{
    position: fixed; inset: 0; z-index: 200;
    background: rgba(15,15,30,0.45);
    backdrop-filter: blur(8px) saturate(140%);
    -webkit-backdrop-filter: blur(8px) saturate(140%);
    display: flex; align-items: center; justify-content: center;
    padding: 20px;
    opacity: 0; visibility: hidden;
    transition: opacity 0.3s var(--ease), visibility 0.3s;
  }}
  .modal-overlay.open {{ opacity: 1; visibility: visible; }}
  .modal {{
    position: relative;
    background: var(--glass-bg-strong);
    backdrop-filter: blur(40px) saturate(180%);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
    border: 1px solid var(--glass-border-hover);
    border-radius: 20px;
    box-shadow: 0 24px 64px rgba(20,20,50,0.2), 0 8px 24px rgba(20,20,50,0.1);
    max-width: 680px; width: 100%; max-height: 85vh; overflow-y: auto;
    padding: 32px 36px 28px;
    transform: scale(0.94) translateY(12px); opacity: 0;
    transition: transform 0.35s var(--ease-out), opacity 0.35s var(--ease-out);
  }}
  .modal-overlay.open .modal {{ transform: scale(1) translateY(0); opacity: 1; }}
  .modal::before {{
    content: ''; position: absolute; inset: 0; border-radius: 20px; pointer-events: none;
    background: linear-gradient(135deg, var(--m-cat-color, rgba(124,58,237,0.08)), transparent 60%);
  }}
  .modal-close {{
    position: absolute; top: 16px; right: 16px; z-index: 2;
    width: 36px; height: 36px; border-radius: 10px;
    border: 1px solid var(--glass-border); background: rgba(255,255,255,0.4);
    color: var(--text-2); font-size: 20px; cursor: pointer; line-height: 1;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s var(--ease); font-family: inherit;
  }}
  .modal-close:hover {{ background: rgba(255,255,255,0.7); color: var(--text); transform: rotate(90deg); }}
  .modal-cat {{
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 12px; font-weight: 600; color: var(--m-cat-color, #7c3aed);
    margin-bottom: 14px; position: relative;
  }}
  .modal-cat::before {{ content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--m-cat-color, #7c3aed); box-shadow: 0 0 8px var(--m-cat-color, #7c3aed); }}
  .modal-title {{
    font-size: 22px; font-weight: 700; color: var(--text); line-height: 1.4;
    margin-bottom: 8px; letter-spacing: -0.3px; position: relative;
  }}
  .modal-title-en {{
    font-size: 14px; color: var(--text-3); font-style: italic;
    margin-bottom: 18px; position: relative; line-height: 1.5;
  }}
  .modal-meta {{
    display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
    font-size: 12px; color: var(--text-3); margin-bottom: 20px;
    padding: 10px 14px; background: rgba(255,255,255,0.35); border-radius: 10px;
    border: 1px solid var(--glass-border); position: relative;
  }}
  .modal-meta .m-src {{ color: var(--text-2); font-weight: 500; }}
  .modal-meta .m-seq {{ font-variant-numeric: tabular-nums; font-weight: 600; color: var(--m-cat-color, #7c3aed); }}
  .modal-meta .m-sep {{ opacity: 0.4; }}
  .modal-summary {{
    font-size: 15px; color: var(--text); line-height: 1.8; margin-bottom: 20px;
    position: relative;
  }}
  .modal-hits {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; position: relative; }}
  .modal-hits .hit-tag {{ font-size: 12px; padding: 3px 10px; }}
  .modal-link {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 12px 24px; border-radius: 12px;
    background: linear-gradient(135deg, var(--m-cat-color, #7c3aed), color-mix(in srgb, var(--m-cat-color, #7c3aed) 65%, #000));
    color: #fff; text-decoration: none; font-size: 14px; font-weight: 600;
    box-shadow: 0 4px 14px color-mix(in srgb, var(--m-cat-color, #7c3aed) 35%, transparent);
    transition: transform 0.2s var(--ease), box-shadow 0.2s var(--ease);
    position: relative;
  }}
  .modal-link:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px color-mix(in srgb, var(--m-cat-color, #7c3aed) 45%, transparent); }}
  .card {{ cursor: pointer; }}
  .card-title {{ cursor: pointer; }}
  .card-expand {{
    font-size: 11px; color: var(--cat-color); font-weight: 600;
    padding: 2px 8px; border-radius: 4px; background: color-mix(in srgb, var(--cat-color) 12%, transparent);
  }}
</style>
</head>
<body>

<div class="scroll-progress" id="scrollProgress"></div>
<div class="bg-orbs">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
  <div class="orb orb-4"></div>
</div>

<div class="container">

  <header class="hero">
    <div class="hero-top">
      <div>
        <h1>顶尖 AI 公司动态情报看板</h1>
        <div class="subtitle">追踪 Anthropic · OpenAI · DeepSeek · Kimi · Qwen 近 7 天关键动态</div>
      </div>
      <span class="badge">数据来自 aihot.virxact.com</span>
    </div>
    <div class="hero-kw">{keywords_html}</div>
  </header>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">时间窗</div>
      <div class="kpi-value" data-count="{WINDOW_DAYS}">{WINDOW_DAYS}</div>
      <div class="kpi-sub">天 · {window_start_bj} ~ {now_bj}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">命中总数</div>
      <div class="kpi-value" data-count="{total}">0</div>
      <div class="kpi-sub">条去重后的精选动态</div>
    </div>
    <div class="kpi-card keywords">
      <div class="kpi-label">追踪关键词</div>
      <div class="kw-chips">{keywords_html}</div>
    </div>
    <div class="kpi-card distribution">
      <div class="kpi-label">分类分布</div>
      {cat_dist_html}
    </div>
  </div>

  <div class="control-bar">
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="搜索标题、来源、摘要…" autocomplete="off">
    </div>
    <div class="filter-chips" id="filterChips">
      {filter_chips_html}
    </div>
  </div>

  {''.join(sections_html)}

  <div class="empty-state" id="emptyState" style="display:none;">
    没有匹配的动态。试试换一个关键词或清除筛选。
  </div>

  <footer class="footer">
    生成时间 {now_bj}（北京时间）· 数据源 <a href="https://aihot.virxact.com" target="_blank" rel="noopener noreferrer">aihot.virxact.com</a> · 仅供内部情报参考
  </footer>

</div>

<!-- 详情 Modal -->
<div class="modal-overlay" id="modalOverlay" aria-hidden="true">
  <div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
    <button class="modal-close" id="modalClose" aria-label="关闭">×</button>
    <div class="modal-cat" id="modalCat"></div>
    <h2 class="modal-title" id="modalTitle"></h2>
    <div class="modal-title-en" id="modalTitleEn"></div>
    <div class="modal-meta" id="modalMeta"></div>
    <div class="modal-summary" id="modalSummary"></div>
    <div class="modal-hits" id="modalHits"></div>
    <a class="modal-link" id="modalLink" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a>
  </div>
</div>

<!-- 完整条目数据（供 modal 读取，避免截断） -->
<script id="items-data" type="application/json">{json.dumps(items_json_list, ensure_ascii=False)}</script>

<script>
(function() {{
  // --- 滚动进度条 ---
  const progress = document.getElementById('scrollProgress');
  function updateProgress() {{
    const h = document.documentElement;
    const scrolled = h.scrollTop / (h.scrollHeight - h.clientHeight);
    progress.style.width = (scrolled * 100) + '%';
  }}
  window.addEventListener('scroll', updateProgress, {{ passive: true }});
  updateProgress();

  // --- 滚动揭示动画 ---
  const io = new IntersectionObserver((entries) => {{
    entries.forEach((e, i) => {{
      if (e.isIntersecting) {{
        setTimeout(() => e.target.classList.add('visible'), i * 40);
        io.unobserve(e.target);
      }}
    }});
  }}, {{ threshold: 0.08, rootMargin: '0px 0px -40px 0px' }});
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));

  // --- KPI 数字 count-up ---
  document.querySelectorAll('.kpi-value[data-count]').forEach(el => {{
    const target = parseInt(el.dataset.count, 10);
    if (target <= 0) return;
    let cur = 0;
    const step = Math.max(1, Math.ceil(target / 30));
    const tick = () => {{
      cur = Math.min(target, cur + step);
      el.textContent = cur;
      if (cur < target) requestAnimationFrame(tick);
    }};
    // 延迟启动，等页面渲染
    setTimeout(tick, 200);
  }});

  // --- 分类分布条形图动画 ---
  setTimeout(() => {{
    document.querySelectorAll('.cat-bar-fill').forEach(el => {{
      el.style.width = el.dataset.target + '%';
    }});
  }}, 300);

  // --- 卡片鼠标跟随光效 ---
  document.querySelectorAll('.card').forEach(card => {{
    card.addEventListener('mousemove', (e) => {{
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      card.style.setProperty('--my', (e.clientY - r.top) + 'px');
    }});
  }});

  // --- 分类筛选 + 关键词搜索 ---
  const chips = document.querySelectorAll('.filter-chip');
  const searchInput = document.getElementById('searchInput');
  const cards = document.querySelectorAll('.card');
  const sections = document.querySelectorAll('.cat-section');
  const emptyState = document.getElementById('emptyState');
  let activeFilter = 'all';
  let searchTerm = '';

  function applyFilters() {{
    let visibleTotal = 0;
    cards.forEach(card => {{
      const cat = card.dataset.category;
      const hits = card.dataset.hits || '';
      const title = card.querySelector('.card-title').textContent.toLowerCase();
      const source = card.querySelector('.source').textContent.toLowerCase();
      const summary = (card.querySelector('.card-summary')?.textContent || '').toLowerCase();
      const term = searchTerm.toLowerCase();

      const catMatch = (activeFilter === 'all') || (cat === activeFilter);
      const searchMatch = !term || title.includes(term) || source.includes(term) || summary.includes(term) || hits.toLowerCase().includes(term);

      if (catMatch && searchMatch) {{
        card.style.display = '';
        visibleTotal++;
      }} else {{
        card.style.display = 'none';
      }}
    }});

    // 隐藏没有可见卡片的 section
    sections.forEach(sec => {{
      const visible = sec.querySelectorAll('.card:not([style*="display: none"])').length;
      sec.style.display = visible > 0 ? '' : 'none';
    }});

    emptyState.style.display = visibleTotal === 0 ? 'block' : 'none';
  }}

  chips.forEach(chip => {{
    chip.addEventListener('click', () => {{
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeFilter = chip.dataset.filter;
      applyFilters();
      // 滚动到目标 section（考虑 sticky 控制栏高度），"全部" 不滚动
      if (activeFilter !== 'all') {{
        const target = document.getElementById('cat-' + activeFilter);
        if (target) {{
          setTimeout(() => target.scrollIntoView({{ behavior: 'smooth', block: 'start' }}), 60);
        }}
      }}
    }});
  }});

  let searchTimer;
  searchInput.addEventListener('input', (e) => {{
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {{
      searchTerm = e.target.value.trim();
      applyFilters();
    }}, 120);
  }});

  // --- 详情 Modal ---
  const itemsData = JSON.parse(document.getElementById('items-data').textContent);
  const overlay = document.getElementById('modalOverlay');
  const mCat = document.getElementById('modalCat');
  const mTitle = document.getElementById('modalTitle');
  const mTitleEn = document.getElementById('modalTitleEn');
  const mMeta = document.getElementById('modalMeta');
  const mSummary = document.getElementById('modalSummary');
  const mHits = document.getElementById('modalHits');
  const mLink = document.getElementById('modalLink');
  const mClose = document.getElementById('modalClose');
  const highlightTerms = {json.dumps(highlight_terms)};

  // 高亮函数（JS 版，转义 + 正则替换）
  function esc(s) {{
    const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML;
  }}
  function hl(text) {{
    if (!text) return '';
    const safe = esc(text);
    const terms = [...new Set(highlightTerms)].sort((a,b) => b.length - a.length);
    if (!terms.length) return safe;
    const re = new RegExp('(' + terms.map(t => t.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&')).join('|') + ')', 'gi');
    return safe.replace(re, m => '<mark>' + m + '</mark>');
  }}

  function openModal(idx) {{
    const it = itemsData[idx];
    if (!it) return;
    overlay.style.setProperty('--m-cat-color', it.category_color);
    mCat.textContent = it.category_label;
    mTitle.innerHTML = hl(it.title);
    mTitleEn.textContent = it.title_en || '';
    mTitleEn.style.display = it.title_en ? '' : 'none';
    mMeta.innerHTML = '<span class="m-seq">#' + it.seq + '</span>' +
                      '<span class="m-sep">/</span><span class="m-src">' + esc(it.source) + '</span>' +
                      '<span class="m-sep">/</span><span>' + it.time_abs + ' 北京时间</span>' +
                      '<span class="m-sep">/</span><span>' + it.time_rel + '</span>';
    mSummary.innerHTML = hl(it.summary);
    mHits.innerHTML = it.hits.map(h => '<span class="hit-tag">' + esc(h) + '</span>').join('');
    mLink.href = it.url;
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }}
  function closeModal() {{
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }}

  // 点击卡片打开 modal
  document.querySelectorAll('.card').forEach(card => {{
    card.addEventListener('click', (e) => openModal(parseInt(card.dataset.idx, 10)));
    card.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); openModal(parseInt(card.dataset.idx, 10)); }}
    }});
  }});
  mClose.addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => {{ if (e.target === overlay) closeModal(); }});
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'Escape' && overlay.classList.contains('open')) closeModal();
  }});
}})();
</script>
</body>
</html>
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    return out_path


if __name__ == "__main__":
    import json as _json
    data_path = PROJECT_ROOT / "cache" / "_dashboard-data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = _json.load(f)
    out = build_html(data)
    print(f"[build_html] wrote {out}  ({out.stat().st_size} bytes)")
