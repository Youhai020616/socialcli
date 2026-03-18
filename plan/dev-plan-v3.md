# SocialCLI 开发计划 v3

> 基于 v0.1.0 实际验证结果制定。v2 计划（Sprint 0-4）已完成。

---

## 当前状态

```
完全可用（login + search + trending + publish 全部验证）：
  ✅ Reddit      — cookie auth + modhash, .json API
  ✅ Twitter/X   — curl_cffi + x-client-transaction-id, GraphQL API

搜索/热榜可用，发布待验证：
  ✅ Bilibili    — 公开 API search/trending, Playwright publish 代码已写

登录可用，API 部分打通：
  🟡 小红书      — xhshow 签名集成，search 返回 0（需 session prewarm）
  🟡 LinkedIn   — Voyager me() 通过，search 端点变更

需要反爬签名：
  🔴 Douyin     — 需要 a_bogus + msToken
  🔴 TikTok     — 需要签名
  
骨架代码：
  ⚪ Weibo / Kuaishou / YouTube / Facebook / Instagram / Threads

基础设施：
  ✅ 112 tests | ✅ 并行发布 | ✅ browser-cookie3 秒登录
  ✅ history | ✅ config | ✅ schedule | ✅ batch
  ❌ CI/CD | ❌ PyPI | ❌ Cookie 过期检测
```

---

## 战略选择

### 两条路线

**路线 A：横向扩平台（打通更多中国平台）**
- 目标用户：中国内容创作者，多平台分发
- 重点：抖音 + 小红书 + B站发布
- 难点：反爬签名复杂，维护成本高

**路线 B：纵向做深度（把已有平台做到极致，发布 PyPI）**
- 目标用户：开发者 / 技术运营，先在国际平台验证
- 重点：发布质量、CI/CD、PyPI、文档、第一批用户
- 优势：Reddit + Twitter 已完全可用，可以先发布

**建议：先 B 后 A** — 先发布 MVP（Reddit + Twitter + Bilibili），获取用户反馈，再扩展中国平台。

---

## Phase 1：发布准备（可以 PyPI 发布的状态）

### Sprint 5：CI/CD + 发布基础设施

**目标**：GitHub Actions CI + PyPI 可发布

**预计时间**：1 天

#### 任务

**S5-1. GitHub Actions CI**

```yaml
# .github/workflows/ci.yml
- Python 3.10 / 3.11 / 3.12 矩阵测试
- pytest -m "not flaky_network" （不跑网络依赖测试）
- 可选：flaky_network 测试在 schedule 里跑
```

**S5-2. PyPI 发布配置**

```yaml
# .github/workflows/publish.yml
- 触发条件：push tag v*
- 构建 sdist + wheel
- 发布到 PyPI
```

**S5-3. 版本管理**

- 当前 `__init__.py` 硬编码 `0.1.0`
- 考虑用 `setuptools-scm` 或保持手动管理
- 打 tag `v0.1.0` 触发首次发布

**S5-4. .gitignore 清理**

- 确认 `github/` 参考项目目录不在发布包中
- `MANIFEST.in` 或 `pyproject.toml` 排除 `github/`, `plan/`, `tests/`

#### 验证

```bash
pip install build
python -m build                    # 构建 wheel
pip install dist/socialcli-*.whl   # 本地安装验证
social --version                   # 0.1.0
social reddit trending -n 3        # 正常工作
```

---

### Sprint 6：用户体验打磨

**目标**：首次使用体验流畅

**预计时间**：1-2 天

#### 任务

**S6-1. 首次运行引导**

当用户第一次运行 `social` 且没有任何账号时，显示友好的引导：

```
📱 Welcome to SocialCLI!

No accounts found. Get started:

  social login reddit      Extract cookies from Chrome (instant)
  social login twitter     Extract cookies from Chrome (instant)

After login:
  social reddit search "python" -n 5
  social publish "Hello!" -p reddit,twitter --dry-run
```

**S6-2. Cookie 过期自动检测**

在 `publish` 和 `search` 操作前，检测 cookie 文件的 `login_time`：
- 超过 7 天：显示黄色警告 `⚠ Reddit cookies are 7+ days old, consider re-login`
- 超过 30 天：显示红色警告
- 操作失败时：提示 `Cookie may have expired. Run: social login reddit`

**S6-3. `social status` 命令**

一个命令看到所有状态：

```bash
$ social status

📱 SocialCLI v0.1.0

Accounts:
  ✅ reddit    (default) — logged in 2h ago
  ✅ twitter   (default) — logged in 2h ago
  ✅ bilibili  (default) — logged in 2h ago
  ⚠️  xhs      (default) — logged in 3d ago (may be expired)

Last publish:
  2026-03-18 09:08 → reddit ✔, twitter ✔

Scheduled: 0 pending tasks
```

**S6-4. 错误消息改善**

把常见错误映射为用户友好的消息：

```python
# 常见错误 → 用户友好消息
"USER_REQUIRED"     → "Cookie expired. Run: social login reddit"
"RATELIMIT"         → "Rate limited. Wait 5 minutes and try again."
"403 Forbidden"     → "Access denied. Your cookie may have expired."
"Connection refused" → "Network error. Check your internet connection."
```

---

### Sprint 7：Bilibili 发布验证 + 小红书搜索修复

**目标**：第 3 个完全可用平台

**预计时间**：2-3 天

#### 任务

**S7-1. Bilibili Playwright 发布验证**

browser.py 代码已存在，需要：
- [ ] 准备测试视频文件
- [ ] 手动运行 `social bilibili publish -t "测试" -v test.mp4`
- [ ] 修复 Playwright 选择器（B站前端可能已更新）
- [ ] 验证标题、描述、标签都正确填写

**S7-2. 小红书 search 调试**

当前状态：API 签名通过（200 + code 0），但返回 0 结果。

调查方向：
- [ ] 对比 xiaohongshu-cli 参考项目的完整请求流程
- [ ] 检查是否需要先调用 onebox + filter prewarm 端点
- [ ] 检查 cookie 中是否缺少必要字段（webBuild, gid 等）
- [ ] 尝试用 curl_cffi 替代 httpx（TLS 指纹）

**S7-3. 小红书 Playwright 发布**

browser.py 代码已存在：
- [ ] 通过 creator.xiaohongshu.com 上传图文
- [ ] 验证标题、描述、标签

---

## Phase 2：中国平台扩展

### Sprint 8：抖音热搜 + 搜索

**目标**：抖音至少热搜可用

**预计时间**：3-5 天

#### 方案选择

**方案 A：Playwright 浏览器模式（慢但可靠）**
- 用 Playwright 打开 douyin.com，在页面中执行搜索
- 解析页面 DOM 获取结果
- 优点：不需要逆向签名
- 缺点：慢（每次请求要启动浏览器）

**方案 B：参考项目 dy-cli 的签名方案**
- 研究 `github/douyin/` 参考项目
- 移植 a_bogus 签名算法
- 优点：快
- 缺点：签名算法可能随时失效

**方案 C：混合模式**
- 热搜用 Playwright（数据量小，可接受慢）
- 搜索用 API + 签名（需要速度）
- 发布用 Playwright（必须浏览器上传）

**建议：方案 C**

#### 任务

- [ ] 研究 `github/douyin/` 参考项目的签名实现
- [ ] 实现 Playwright 热搜抓取（兜底方案）
- [ ] 尝试移植 a_bogus 签名
- [ ] 验证 `social douyin trending`
- [ ] 验证 `social douyin search "美食"`

---

### Sprint 9：微博热搜

**目标**：微博热搜可用（中国最重要的热搜平台）

**预计时间**：1-2 天

微博热搜 API (`weibo.com/ajax/side/hotSearch`) 返回 403，但：
- 参考项目 `github/weibo-cli/` 可能有解决方案
- 可能只需要正确的 cookie 或 Referer
- 微博热搜是公开数据，应该有办法获取

---

## Phase 3：产品化

### Sprint 10：高级发布功能

- [ ] 图片上传（Twitter media upload API）
- [ ] 视频发布（Twitter、Bilibili）
- [ ] 发布模板（`social publish --template marketing`）
- [ ] 发布预览（在终端中渲染内容预览）

### Sprint 11：数据分析

- [ ] `social analytics` — 聚合各平台数据
- [ ] 发布效果追踪（likes/comments/views over time）
- [ ] 最佳发布时间建议

### Sprint 12：Web Dashboard（可选）

- 简单的本地 Web 界面查看 history / analytics
- FastAPI + Jinja2 模板
- `social web` 启动本地服务器

---

## 里程碑

```
M5 ✅ 已完成   — Reddit + Twitter 全链路 + 112 tests + 并行发布
M6 → Sprint 5  — CI/CD + PyPI 发布 v0.1.0
M7 → Sprint 6  — 用户体验打磨（首次引导、cookie 检测、status 命令）
M8 → Sprint 7  — Bilibili 发布验证 + 小红书搜索修复 → 3 平台完全可用
M9 → Sprint 8  — 抖音热搜/搜索 → 中国平台突破
M10 → Sprint 9 — 微博热搜
M11 → Sprint 10 — 图片/视频发布
```

---

## 优先级矩阵

| 任务 | 影响 | 难度 | 优先级 |
|------|:----:|:----:|:------:|
| CI/CD + PyPI 发布 | 高 | 低 | **P0** |
| 首次运行引导 | 中 | 低 | **P0** |
| Cookie 过期检测 | 中 | 低 | **P1** |
| `social status` 命令 | 中 | 低 | **P1** |
| Bilibili Playwright 发布 | 高 | 中 | **P1** |
| 小红书搜索修复 | 高 | 高 | **P2** |
| 抖音热搜/搜索 | 高 | 高 | **P2** |
| 微博热搜 | 中 | 中 | **P2** |
| 图片上传（Twitter） | 中 | 中 | **P3** |
| Web Dashboard | 低 | 高 | **P3** |

---

## 技术债务清理

在上述开发之间穿插：

- [ ] `github/` 参考项目从发布包中排除
- [ ] 移除未使用的 `import re` 内联导入
- [ ] 统一所有平台 client 的 `cli_group` 模板（减少样板代码）
- [ ] 为 Twitter GraphQL 响应添加更多 mock 测试
- [ ] `publisher.py` 添加发布重试机制（失败后自动重试 1 次）
- [ ] Cookie 文件权限设为 600（macOS/Linux）
