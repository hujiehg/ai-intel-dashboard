# 顶尖 AI 公司动态情报看板

追踪 **Anthropic / OpenAI / DeepSeek / Kimi / Qwen** 近 7 天关键动态，自动生成单文件 HTML 商业情报看板。

🔗 **在线访问**：发布到 GitHub Pages 后，URL 形如 `https://<username>.github.io/ai-intel-dashboard/`

## 看板特性

- **5 个固定分类**：模型发布/更新 → 产品发布/更新 → 行业动态 → 论文研究 → 技巧与观点
- **全局连续编号**：1 到 N 贯穿所有版块
- **顶部 KPI**：时间窗、命中总数、关键词、分类分布条形图
- **每条动态**：序号 / 标题 / 来源 / 北京时间相对时间 / ≤160 字摘要 / 原文链接
- **关键词高亮**：5 个公司名 + 中文别名（通义千问/千问/月之暗面/深度求索）
- **响应式布局**：桌面 4 列 → 平板 2 列 → 手机 1 列
- **纯单文件 HTML**：内联样式与脚本，0 外部资源

## 目录结构

```
.
├── .github/workflows/deploy.yml   # GitHub Actions 自动部署
├── dist/
│   └── index.html                 # 部署入口（看板 HTML）
├── scripts/
│   ├── config.py                  # 集中配置
│   ├── fetch.py                   # 拉取 aihot API
│   ├── merge.py                   # 去重 + 分组 + 编号
│   ├── build_html.py              # 生成 HTML
│   └── run.py                     # 一键 orchestrator
└── README.md
```

## 数据源

[aihot.virxact.com](https://aihot.virxact.com) — 公开匿名可访，无需 token。

API：`GET /api/public/items?mode=selected&q={公司名}&since={7天前}&take=30`

## 本地刷新

```bash
python scripts/run.py            # 完整流程：拉取 → 合并 → 生成 → 归档 → 同步 dist
python scripts/run.py --no-fetch # 复用当日 cache，仅重新生成 HTML
```

## 自动化

通过 WorkBuddy automation 每日 09:00（北京时间）自动刷新：
1. 调用 aihot API 拉取最新动态
2. 生成 HTML 并覆盖 `dist/index.html`
3. 推送到 main 分支
4. GitHub Actions 自动部署到 GitHub Pages

## 技术栈

- Python 3.13（脚本）
- 纯 HTML/CSS/JS（看板，无框架）
- GitHub Actions（CI/CD）
- aihot API（数据源）

---

仅供内部情报参考。
