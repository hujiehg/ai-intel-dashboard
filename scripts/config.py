"""配置：追踪的公司、关键词、API 端点、分类映射等"""
from pathlib import Path

# 项目根目录（scripts/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 追踪的 AI 公司（关键词即用作 q 参数，也用作高亮词）
COMPANIES = ["Anthropic", "OpenAI", "DeepSeek", "Kimi", "Qwen"]

# 中文别名（同义高亮，不参与 API 查询）
ALIAS_HIGHLIGHT = ["通义千问", "千问", "月之暗面", "深度求索"]

# aihot API
API_BASE = "https://aihot.virxact.com"
API_ITEMS = f"{API_BASE}/api/public/items"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# 时间窗（天）
WINDOW_DAYS = 7
# 每次每公司拉取条数上限（API 上限 100）
TAKE = 30

# 5 个固定 category 顺序
CATEGORY_ORDER = ["ai-models", "ai-products", "industry", "paper", "tip"]
CATEGORY_LABEL = {
    "ai-models": "模型发布/更新",
    "ai-products": "产品发布/更新",
    "industry": "行业动态",
    "paper": "论文研究",
    "tip": "技巧与观点",
}
# category 为 null 时的兜底归属
CATEGORY_NULL_FALLBACK = "industry"

# 分类视觉风格（color / bg / icon）
CATEGORY_STYLE = {
    "模型发布/更新": {"color": "#7c3aed", "bg": "#f5f3ff", "icon": "M"},
    "产品发布/更新": {"color": "#2563eb", "bg": "#eff6ff", "icon": "P"},
    "行业动态":     {"color": "#ea580c", "bg": "#fff7ed", "icon": "I"},
    "论文研究":     {"color": "#059669", "bg": "#ecfdf5", "icon": "R"},
    "技巧与观点":   {"color": "#db2777", "bg": "#fdf2f8", "icon": "T"},
}

# 摘要最大字符数
SUMMARY_MAX_CHARS = 160

# 输出路径
LATEST_HTML = PROJECT_ROOT / "ai-companies-intel-dashboard.html"
HISTORY_DIR = PROJECT_ROOT / "dashboard-history"
CACHE_DIR = PROJECT_ROOT / "cache"
DIST_DIR = PROJECT_ROOT / "dist"
DIST_INDEX = DIST_DIR / "index.html"
