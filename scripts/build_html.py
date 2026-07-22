"""根据合并后的数据生成单文件 HTML 看板 — Dark Editorial Intelligence 风格

设计方向：深色 editorial 情报终端，衬线标题 + 无衬线正文，
单一琥珀金强调色，避开 glassmorphism/彩色光斑/渐变文字等 AI slop。
"""
import html
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

# 深色主题下的分类色（muted，适配深色背景）
CATEGORY_COLOR_DARK = {
    "模型发布/更新": "#a78bfa",  # 紫
    "产品发布/更新": "#60a5fa",  # 蓝
    "行业动态":     "#f59e0b",  # 琥珀
    "论文研究":     "#34d399",  # 翡翠
    "技巧与观点":   "#f472b6",  # 粉
}


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
        return f"{secs}秒前"
    if secs < 3600:
        return f"{secs // 60}分钟前"
    if secs < 86400:
        return f"{secs // 3600}小时前"
    if secs < 86400 * 2:
        return f"昨天 {bj.strftime('%H:%M')}"
    if secs < 86400 * 7:
        return f"{secs // 86400}天前"
    return bj.strftime("%m-%d")


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
    window_start_bj = (now_utc - timedelta(days=WINDOW_DAYS)).astimezone(BJ_TZ).strftime("%m/%d %H:%M")
    now_bj = now_utc.astimezone(BJ_TZ).strftime("%m/%d %H:%M")

    # --- 分类色映射（深色版） ---
    def cat_color(label):
        return CATEGORY_COLOR_DARK.get(label, "#d4a574")

    # --- sections ---
    sections_html = []
    for s in data["sections"]:
        label = s["label"]
        color = cat_color(label)
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
                f'<span class="hit">{html.escape(h)}</span>' for h in hits
            )
            cat = it.get("category") or "industry"
            items_html.append(f"""        <article class="entry reveal" data-category="{cat}" data-hits="{','.join(hits)}" style="--c:{color}">
          <span class="seq">{seq:02d}</span>
          <div class="entry-body">
            <div class="entry-head">
              <a class="entry-title" href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>
              <div class="entry-hits">{hits_html}</div>
            </div>
            <div class="entry-meta">
              <span class="src" title="{source}">{source}</span>
              <span class="sep">/</span>
              <time class="when" title="{abs_t} 北京时间">{rel}</time>
            </div>
            {f'<p class="entry-summary">{summary}</p>' if summary else ''}
          </div>
          <a class="entry-arrow" href="{url}" target="_blank" rel="noopener noreferrer" aria-label="阅读原文">→</a>
        </article>""")
        sections_html.append(f"""    <section class="cat-section" id="cat-{s['category']}" data-cat="{s['category']}">
      <div class="cat-header" style="--c:{color}">
        <span class="cat-label">{label}</span>
        <span class="cat-count">{len(s['items'])}</span>
      </div>
      <div class="cat-entries">
        {''.join(items_html)}
      </div>
    </section>""")

    # --- 顶部内联统计（替代 KPI 卡片网格） ---
    cat_counts = data["category_counts"]
    total = data["total"]
    stat_parts = [f'<span class="stat-num" data-count="{total}">0</span><span class="stat-unit"> 条动态</span>']
    stat_parts.append(f'<span class="stat-sep">·</span><span>{WINDOW_DAYS}天窗口</span>')
    stat_parts.append(f'<span class="stat-sep">·</span><span>{len(COMPANIES)}家公司</span>')
    stat_parts.append(f'<span class="stat-sep">·</span><span class="stat-window">{window_start_bj} → {now_bj}</span>')
    stats_html = '<div class="stats">' + ''.join(stat_parts) + '</div>'

    # --- 分类分布内联条 ---
    max_cat = max(cat_counts.values()) if cat_counts else 1
    dist_html = '<div class="dist">'
    for k, v in cat_counts.items():
        c = cat_color(k)
        dist_html += f'<span class="dist-item" style="--c:{c}" title="{k}: {v}"><span class="dist-bar" style="width:{v/max_cat*100:.0f}%"></span><span class="dist-label">{k}</span><span class="dist-num">{v}</span></span>'
    dist_html += '</div>'

    # --- 关键词 ---
    keywords_html = "".join(
        f'<span class="kw">{html.escape(kw)}</span>' for kw in data["keywords"]
    )

    # --- 筛选 chips ---
    filter_chips = f'<button class="chip active" data-filter="all">全部<span>{total}</span></button>'
    for s in data["sections"]:
        c = cat_color(s["label"])
        filter_chips += f'<button class="chip" data-filter="{s["category"]}" style="--c:{c}">{s["label"]}<span>{len(s["items"])}</span></button>'

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>顶尖 AI 公司动态情报看板 · 近 7 天</title>
<style>
  :root {{
    --bg: #0d1117;
    --bg-2: #161b22;
    --bg-3: #1c2128;
    --border: #30363d;
    --border-2: #21262d;
    --text: #e6edf3;
    --text-2: #8b949e;
    --text-3: #6e7681;
    --accent: #d4a574;
    --accent-dim: rgba(212,165,116,0.12);
    --serif: ui-serif, Georgia, "Times New Roman", "Songti SC", "SimSun", serif;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
    --mono: ui-monospace, "SF Mono", "Cascadia Code", "Consolas", monospace;
    --ease: cubic-bezier(0.25, 1, 0.5, 1);
    --ease-out: cubic-bezier(0, 0, 0.2, 1);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    font-size: 15px;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
  }}

  /* 极淡网格背景纹理（替代彩色光斑） */
  body::before {{
    content: ''; position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
      linear-gradient(rgba(48,54,61,0.25) 1px, transparent 1px),
      linear-gradient(90deg, rgba(48,54,61,0.25) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 80%);
    -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 80%);
  }}

  /* 顶部进度条 */
  .progress {{ position: fixed; top: 0; left: 0; height: 2px; width: 0%; background: var(--accent); z-index: 100; transition: width 0.1s linear; }}

  .wrap {{ position: relative; z-index: 1; max-width: 920px; margin: 0 auto; padding: 48px 24px 80px; }}

  /* --- Hero（editorial 风格，不用卡片网格） --- */
  .hero {{ margin-bottom: 40px; }}
  .hero-eyebrow {{
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--accent); margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }}
  .hero-eyebrow::before {{ content: ''; width: 24px; height: 1px; background: var(--accent); }}
  .hero h1 {{
    font-family: var(--serif); font-size: clamp(32px, 5vw, 48px); font-weight: 400;
    line-height: 1.15; letter-spacing: -0.02em; margin-bottom: 16px; color: var(--text);
  }}
  .hero h1 em {{ font-style: italic; color: var(--accent); font-weight: 400; }}
  .hero-sub {{ font-size: 15px; color: var(--text-2); max-width: 580px; line-height: 1.7; margin-bottom: 24px; }}
  .hero-kw {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 28px; }}
  .kw {{
    font-family: var(--mono); font-size: 12px; padding: 4px 10px;
    border: 1px solid var(--border); border-radius: 4px; color: var(--text-2);
    background: var(--bg-2); transition: border-color 0.2s, color 0.2s;
  }}
  .kw:hover {{ border-color: var(--accent); color: var(--accent); }}

  /* 内联统计行 */
  .stats {{
    font-family: var(--mono); font-size: 13px; color: var(--text-2);
    display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px;
    padding: 16px 0; border-top: 1px solid var(--border-2); border-bottom: 1px solid var(--border-2);
  }}
  .stat-num {{ font-size: 28px; font-weight: 600; color: var(--text); font-variant-numeric: tabular-nums; }}
  .stat-unit {{ color: var(--text-2); }}
  .stat-sep {{ color: var(--text-3); }}
  .stat-window {{ color: var(--text-3); font-size: 12px; }}

  /* 分类分布内联条 */
  .dist {{ display: flex; flex-wrap: wrap; gap: 16px 24px; margin-top: 20px; }}
  .dist-item {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
  .dist-bar {{
    height: 3px; min-width: 24px; max-width: 80px; border-radius: 2px;
    background: var(--c); transition: width 0.8s var(--ease-out);
  }}
  .dist-label {{ color: var(--text-3); }}
  .dist-num {{ color: var(--c); font-weight: 600; font-variant-numeric: tabular-nums; }}

  /* --- 控制栏（唯一用 blur 的地方） --- */
  .controls {{
    position: sticky; top: 0; z-index: 50;
    background: rgba(13,17,23,0.82); backdrop-filter: blur(16px) saturate(140%);
    -webkit-backdrop-filter: blur(16px) saturate(140%);
    border-bottom: 1px solid var(--border);
    margin: 0 -24px 32px; padding: 14px 24px;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }}
  .search {{ flex: 1; min-width: 180px; position: relative; }}
  .search input {{
    width: 100%; background: var(--bg-2); border: 1px solid var(--border);
    color: var(--text); padding: 8px 12px 8px 32px; border-radius: 6px;
    font-family: var(--sans); font-size: 13px; outline: none;
    transition: border-color 0.2s;
  }}
  .search input:focus {{ border-color: var(--accent); }}
  .search input::placeholder {{ color: var(--text-3); }}
  .search::before {{
    content: ''; position: absolute; left: 11px; top: 50%; transform: translateY(-50%);
    width: 12px; height: 12px;
    border: 1.5px solid var(--text-3); border-radius: 50%;
    box-shadow: 4px 4px 0 -1px var(--text-3);
  }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{
    font-family: var(--sans); font-size: 12px; font-weight: 500;
    padding: 6px 12px; border-radius: 999px;
    border: 1px solid var(--border); background: var(--bg-2); color: var(--text-2);
    cursor: pointer; transition: all 0.2s var(--ease);
    display: inline-flex; align-items: center; gap: 6px;
    --c: var(--text-2);
  }}
  .chip span {{ font-size: 10px; opacity: 0.7; font-variant-numeric: tabular-nums; }}
  .chip:hover {{ border-color: var(--c); color: var(--text); }}
  .chip.active {{ background: var(--c); border-color: var(--c); color: #0d1117; }}
  .chip.active span {{ opacity: 0.6; }}

  /* --- 分类 section --- */
  .cat-section {{ margin-bottom: 48px; }}
  .cat-header {{
    display: flex; align-items: baseline; gap: 12px;
    margin-bottom: 20px; padding-bottom: 12px;
    border-bottom: 1px solid var(--border-2);
  }}
  .cat-label {{
    font-family: var(--serif); font-size: 22px; font-weight: 400;
    color: var(--text); letter-spacing: -0.01em;
  }}
  .cat-label::before {{ content: ''; display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--c); margin-right: 10px; vertical-align: middle; }}
  .cat-count {{
    font-family: var(--mono); font-size: 12px; color: var(--c);
    font-variant-numeric: tabular-nums;
  }}

  /* --- 条目（不用卡片套卡片，用编辑式列表） --- */
  .cat-entries {{ display: flex; flex-direction: column; }}
  .entry {{
    display: flex; align-items: flex-start; gap: 16px;
    padding: 18px 0; border-bottom: 1px solid var(--border-2);
    transition: background 0.2s var(--ease);
    position: relative;
  }}
  .entry:last-child {{ border-bottom: none; }}
  .entry::before {{
    content: ''; position: absolute; left: -24px; top: 0; bottom: 0; width: 2px;
    background: var(--c); transform: scaleY(0); transform-origin: top;
    transition: transform 0.3s var(--ease);
  }}
  .entry:hover {{ background: rgba(255,255,255,0.015); }}
  .entry:hover::before {{ transform: scaleY(1); }}

  .seq {{
    font-family: var(--mono); font-size: 13px; font-weight: 500;
    color: var(--text-3); min-width: 32px; padding-top: 1px;
    font-variant-numeric: tabular-nums; transition: color 0.2s;
  }}
  .entry:hover .seq {{ color: var(--c); }}

  .entry-body {{ flex: 1; min-width: 0; }}
  .entry-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 6px; }}
  .entry-title {{
    font-size: 16px; font-weight: 500; color: var(--text); text-decoration: none;
    line-height: 1.5; transition: color 0.2s;
  }}
  .entry-title:hover {{ color: var(--c); }}
  .entry-hits {{ display: flex; gap: 4px; flex-shrink: 0; flex-wrap: wrap; }}
  .hit {{
    font-family: var(--mono); font-size: 10px; font-weight: 500;
    padding: 2px 6px; border-radius: 3px;
    background: var(--accent-dim); color: var(--accent);
    border: 1px solid rgba(212,165,116,0.2);
  }}
  .entry-meta {{
    font-family: var(--mono); font-size: 12px; color: var(--text-3);
    display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
  }}
  .src {{ color: var(--text-2); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .sep {{ color: var(--text-3); opacity: 0.5; }}
  .when {{ font-variant-numeric: tabular-nums; }}
  .entry-summary {{
    font-size: 14px; color: var(--text-2); line-height: 1.7;
    max-width: 680px;
  }}
  .entry-arrow {{
    flex-shrink: 0; font-size: 18px; color: var(--text-3); text-decoration: none;
    padding: 4px 8px; transition: color 0.2s, transform 0.2s var(--ease);
    align-self: center;
  }}
  .entry:hover .entry-arrow {{ color: var(--c); transform: translateX(3px); }}

  mark {{ background: rgba(212,165,116,0.18); color: var(--accent); padding: 0 3px; border-radius: 2px; font-weight: 600; }}

  /* 滚动揭示 */
  .reveal {{ opacity: 0; transform: translateY(16px); transition: opacity 0.5s var(--ease-out), transform 0.5s var(--ease-out); }}
  .reveal.visible {{ opacity: 1; transform: translateY(0); }}

  /* 空状态 */
  .empty {{ text-align: center; padding: 60px 20px; color: var(--text-3); font-family: var(--serif); font-size: 18px; font-style: italic; }}

  /* Footer */
  .footer {{
    margin-top: 60px; padding-top: 24px; border-top: 1px solid var(--border-2);
    font-family: var(--mono); font-size: 11px; color: var(--text-3);
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px;
  }}
  .footer a {{ color: var(--accent); text-decoration: none; }}

  /* 响应式 */
  @media (max-width: 768px) {{
    .wrap {{ padding: 32px 16px 60px; }}
    .hero h1 {{ font-size: 28px; }}
    .controls {{ margin: 0 -16px 24px; padding: 12px 16px; }}
    .entry {{ gap: 12px; }}
    .entry-title {{ font-size: 15px; }}
    .seq {{ min-width: 28px; font-size: 12px; }}
    .entry-arrow {{ display: none; }}
    .src {{ max-width: 200px; }}
  }}
  @media (max-width: 480px) {{
    .entry-head {{ flex-direction: column; align-items: flex-start; }}
    .entry-hits {{ margin-top: 4px; }}
    .stats {{ font-size: 12px; }}
    .stat-num {{ font-size: 22px; }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .reveal {{ opacity: 1; transform: none; transition: none; }}
    * {{ scroll-behavior: auto; }}
  }}
</style>
</head>
<body>

<div class="progress" id="progress"></div>

<div class="wrap">

  <header class="hero">
    <div class="hero-eyebrow">AI Intelligence Brief · Daily</div>
    <h1>顶尖 AI 公司<br>近七日<em>动态情报</em></h1>
    <p class="hero-sub">追踪 Anthropic、OpenAI、DeepSeek、Kimi、Qwen 五家头部 AI 公司的模型发布、产品更新、行业动态、论文研究与技巧观点。数据来自 aihot.virxact.com，每日 09:00 自动刷新。</p>
    <div class="hero-kw">{keywords_html}</div>
    {stats_html}
    {dist_html}
  </header>

  <div class="controls">
    <div class="search">
      <input type="text" id="searchInput" placeholder="搜索标题、来源、摘要…" autocomplete="off">
    </div>
    <div class="chips" id="chips">
      {filter_chips}
    </div>
  </div>

  {''.join(sections_html)}

  <div class="empty" id="empty" style="display:none;">没有匹配的动态</div>

  <footer class="footer">
    <span>生成于 {now_bj} 北京时间</span>
    <span>数据源 <a href="https://aihot.virxact.com" target="_blank" rel="noopener noreferrer">aihot.virxact.com</a> · 仅供情报参考</span>
  </footer>

</div>

<script>
(function() {{
  // 滚动进度
  const p = document.getElementById('progress');
  const update = () => {{
    const h = document.documentElement;
    p.style.width = (h.scrollTop / (h.scrollHeight - h.clientHeight) * 100) + '%';
  }};
  window.addEventListener('scroll', update, {{ passive: true }});
  update();

  // 滚动揭示
  const io = new IntersectionObserver((entries) => {{
    entries.forEach((e, i) => {{
      if (e.isIntersecting) {{
        setTimeout(() => e.target.classList.add('visible'), Math.min(i * 30, 240));
        io.unobserve(e.target);
      }}
    }});
  }}, {{ threshold: 0.06, rootMargin: '0px 0px -30px 0px' }});
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));

  // count-up
  document.querySelectorAll('.stat-num[data-count]').forEach(el => {{
    const target = parseInt(el.dataset.count, 10);
    if (!target) return;
    let cur = 0; const step = Math.max(1, Math.ceil(target / 28));
    const tick = () => {{
      cur = Math.min(target, cur + step);
      el.textContent = cur;
      if (cur < target) requestAnimationFrame(tick);
    }};
    setTimeout(tick, 250);
  }});

  // 分布条动画
  setTimeout(() => {{
    document.querySelectorAll('.dist-bar').forEach(el => {{
      const w = el.style.width; el.style.width = '0';
      requestAnimationFrame(() => {{ el.style.width = w; }});
    }});
  }}, 400);

  // 筛选 + 搜索
  const chips = document.querySelectorAll('.chip');
  const searchInput = document.getElementById('searchInput');
  const entries = document.querySelectorAll('.entry');
  const sections = document.querySelectorAll('.cat-section');
  const empty = document.getElementById('empty');
  let filter = 'all', term = '';

  function apply() {{
    let vis = 0;
    entries.forEach(e => {{
      const cat = e.dataset.category;
      const hits = (e.dataset.hits || '').toLowerCase();
      const title = e.querySelector('.entry-title').textContent.toLowerCase();
      const src = e.querySelector('.src').textContent.toLowerCase();
      const sum = (e.querySelector('.entry-summary')?.textContent || '').toLowerCase();
      const t = term.toLowerCase();
      const ok = (filter === 'all' || cat === filter) &&
                 (!t || title.includes(t) || src.includes(t) || sum.includes(t) || hits.includes(t));
      e.style.display = ok ? '' : 'none';
      if (ok) vis++;
    }});
    sections.forEach(s => {{
      const v = s.querySelectorAll('.entry:not([style*="display: none"])').length;
      s.style.display = v > 0 ? '' : 'none';
    }});
    empty.style.display = vis === 0 ? 'block' : 'none';
  }}

  chips.forEach(c => c.addEventListener('click', () => {{
    chips.forEach(x => x.classList.remove('active'));
    c.classList.add('active');
    filter = c.dataset.filter;
    apply();
  }}));

  let timer;
  searchInput.addEventListener('input', e => {{
    clearTimeout(timer);
    timer = setTimeout(() => {{ term = e.target.value.trim(); apply(); }}, 120);
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
