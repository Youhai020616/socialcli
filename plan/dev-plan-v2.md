# SocialCLI 开发计划 v2

> 基于 2026-03-18 的实际运行验证制定，替代原始 socialcli-plan.md 中的执行计划部分。

---

## 当前状态：Pre-Alpha（脚手架已生成，核心路径不可用）

### 实际验证结果

```
命令层面：
  social --help / --version / accounts     ✅ 正常
  social trending -p bilibili              ✅ 返回数据
  social trending -p reddit                ✅ 返回数据（需修 UA）
  social trending -p douyin/twitter/weibo  ❌ 空数据（API 不可达或需认证）
  social <任何平台> <任何子命令>              💥 全部 NameError crash

API 层面（裸 HTTP 验证）：
  Bilibili 排行榜 API     ✅ 公开可用，无需认证
  Bilibili 搜索 API       ⚠️ 需 wbi 签名（412）
  Reddit .json API        ✅ 公开可用，需合法 UA
  YouTube HTML 抓取       ✅ 可行（需解析 ytInitialData）
  Douyin API              ❌ 需 cookie + a_bogus 签名
  Twitter GraphQL         ❌ 需 OAuth cookie
  Weibo Ajax API          ❌ 需 cookie（403）
  小红书 API              ❌ 需 cookie + xs签名
  TikTok API              ❌ 需 cookie + 签名
  LinkedIn Voyager API    ❌ 需 li_at cookie

模块层面（直接 Python 调用）：
  cookie_store            ✅ save/load/list/delete 全部正常
  content_adapter         ✅ 13 平台规则正常
  scheduler               ✅ add/list/due/remove 正常
  batch (JSON loader)     ✅ 解析正常
  RedditPlatform          ✅ trending() 直接调用返回 25 条
  BilibiliPlatform        ⚠️ search() 正常，trending() 因空 Cookie header 触发风控
```

### 致命 Bug

**`_platform` 作用域错误**：变量在 `__init__.py` 定义，在 `client.py` 的 `cli_group` 闭包中引用，导致所有 13 个平台的子命令（`social <platform> search/trending/publish`）全部 `NameError` 崩溃。

---

## 开发策略

### 核心原则

1. **纵向打通优先于横向扩展** — 先让 2 个平台完全可用，再扩展到更多平台
2. **公开 API 平台优先** — Reddit、Bilibili 的 API 无需登录即可使用搜索和热榜，是最快能验证的路径
3. **每个任务必须有可运行的验证命令** — 不接受"代码写了但没跑过"
4. **砍掉不可交付的承诺** — Phase 2 的 6 个扩展平台暂时冻结，聚焦核心

### 平台优先级重新排序

```
Tier 1（公开 API，无需登录即可验证搜索/热榜）：
  🟢 Reddit     — .json API 公开可用，搜索/热榜/发帖都有明确 endpoint
  🟢 Bilibili   — 公开 API 丰富，搜索/排行/热搜都能用

Tier 2（需要登录才能操作，但 API 模式已知）：
  🟡 Twitter    — GraphQL API 逆向成熟（开源参考多），但需 cookie
  🟡 抖音       — 需要 a_bogus 签名（复杂），依赖 cookie

Tier 3（重度浏览器依赖）：
  🟠 小红书     — API 签名复杂，几乎必须走 Playwright
  🟠 TikTok    — 类似抖音但更严格的反爬
  🟠 LinkedIn  — Voyager API 未验证

Tier 4（冻结，不在本轮计划内）：
  ⚪ Weibo / Kuaishou / YouTube / Facebook / Instagram / Threads
```

---

## Sprint 计划

### Sprint 0：急救（让项目能跑起来）

**目标**：修复致命 Bug，让所有已有代码不再崩溃。

**预计时间**：0.5 天

#### 任务

**S0-1. 修复 `_platform` 作用域 Bug**

所有 13 个 `client.py` 的 `cli_group` 闭包中引用了 `_platform`，但该变量定义在 `__init__.py`，不在 `client.py` 作用域内。

修复方案：在每个 `cli_group` 属性方法内通过 `self` 引用实例。

```python
# 修复前（所有 client.py 中）
@property
def cli_group(self):
    @xxx_group.command()
    def search(...):
        results = _platform.search(...)   # ❌ NameError

# 修复后
@property
def cli_group(self):
    platform = self  # 捕获 self 到闭包
    @xxx_group.command()
    def search(...):
        results = platform.search(...)    # ✅
```

涉及文件（13个）：
- `platforms/douyin/client.py`
- `platforms/xiaohongshu/client.py`
- `platforms/twitter/client.py`
- `platforms/reddit/client.py`
- `platforms/tiktok/client.py`
- `platforms/linkedin/client.py`
- `platforms/bilibili/client.py`
- `platforms/weibo/client.py`
- `platforms/kuaishou/client.py`
- `platforms/youtube/client.py`
- `platforms/facebook/client.py`
- `platforms/instagram/client.py`
- `platforms/threads/client.py`

**S0-2. 修复 Bilibili 空 Cookie header 触发风控**

`_get_headers()` 在无 cookie 时返回 `Cookie: ""`（空字符串），B站 API 返回 code `-352`（风控）。

修复：cookie 为空时不发送 Cookie header。

涉及文件：所有有 `_get_headers()` 方法的 client.py。

**S0-3. 修复 Reddit User-Agent**

当前使用 Chrome UA 被 Reddit .json API 返回 403。Reddit 要求使用标识性 UA（如 `socialcli/0.1.0`）。

涉及文件：`platforms/reddit/client.py`

#### 验证命令

```bash
# 修复后必须全部通过：
social bilibili trending --json          # 返回数据，不崩溃
social bilibili search "编程" --json      # 返回数据
social reddit trending --json            # 返回数据
social reddit search "python" --json     # 返回数据
social douyin trending --json            # 可以返回空，但不能崩溃
social twitter trending --json           # 可以返回空，但不能崩溃
```

---

### Sprint 1：让 Reddit + Bilibili 完全可用

**目标**：两个平台的搜索、热榜、登录、发帖全链路可用。这是整个项目的 MVP。

**预计时间**：2-3 天

#### 任务

**S1-1. Reddit 全链路验证**

Reddit 的 .json API 最简单、最稳定。

- [ ] `social login reddit` — 验证 Playwright 打开浏览器、登录后 cookie 保存
- [ ] `social reddit search "python" -r programming` — 验证搜索（公开API，不需登录）
- [ ] `social reddit trending` — 验证热门获取（公开API）
- [ ] `social reddit publish -t "Test" -c "Body" -r test` — 验证发帖（需要登录）
- [ ] `social reddit upvote <id>` — 验证互动（需要登录）

已知需要修复：
- UA 改为 `socialcli/0.1.0 (Python; +https://github.com/xxx/socialcli)`
- `_modhash()` 获取可能需要验证（Reddit 的 CSRF 机制）

```bash
# 验证命令：
social reddit search "python" -r programming --json
social reddit trending -n 5 --json
social login reddit
social reddit publish -t "SocialCLI Test" -c "Testing publish from CLI" -r test
```

**S1-2. Bilibili 全链路验证**

- [ ] `social login bilibili` — QR 扫码登录
- [ ] `social bilibili search "编程"` — 搜索（公开 API，需处理 412 → 加 wbi 签名或换 endpoint）
- [ ] `social bilibili trending` — 热门排行（修复空 cookie 问题后应该工作）
- [ ] `social bilibili publish -t "测试" -v video.mp4` — 视频发布（Playwright）

已知需要修复：
- 搜索 API 可能需要 wbi 签名（`/x/web-interface/search/type` 在无 cookie 时返回 412）
- 备选方案：改用 `/x/web-interface/wbi/search/all/v2` 或移动端 API
- `browser.py` 的 Playwright 发布流程需要实际测试

```bash
# 验证命令：
social bilibili trending -n 5 --json
social bilibili search "编程" -n 5 --json
social login bilibili
social bilibili publish -t "测试视频" -v test.mp4
```

**S1-3. 错误处理改善（仅 Reddit + Bilibili）**

将这两个平台的静默 `except Exception: return []` 改为有意义的错误报告：

```python
import logging
logger = logging.getLogger(__name__)

# 替换所有：
except Exception:
    return []

# 改为：
except httpx.HTTPStatusError as e:
    logger.warning("%s API error: %s %s", self.name, e.response.status_code, e.response.text[:100])
    return []
except httpx.RequestError as e:
    logger.error("%s request failed: %s", self.name, e)
    return []
```

添加 `--verbose` / `-v` 全局 flag 控制日志级别。

涉及文件：
- `platforms/reddit/client.py`
- `platforms/bilibili/client.py`
- `main.py`（添加 `--verbose` flag）

**S1-4. 为 Reddit + Bilibili 写 Smoke Test**

```python
# tests/test_reddit_smoke.py
def test_reddit_trending_returns_data():
    """Reddit trending should return items from public API."""
    from socialcli.platforms.reddit.client import RedditPlatform
    p = RedditPlatform()
    items = p.trending()
    assert len(items) > 0
    assert items[0].title
    assert items[0].url

def test_reddit_search_returns_data():
    from socialcli.platforms.reddit.client import RedditPlatform
    p = RedditPlatform()
    results = p.search("python")
    assert len(results) > 0

# tests/test_bilibili_smoke.py
def test_bilibili_search_returns_data():
    from socialcli.platforms.bilibili.client import BilibiliPlatform
    p = BilibiliPlatform()
    results = p.search("编程")
    assert len(results) > 0
```

#### Sprint 1 交付标准

- [ ] `social reddit search/trending/publish` 全部可用
- [ ] `social bilibili search/trending` 可用
- [ ] `social bilibili publish` 至少有明确的错误信息（如无视频时）
- [ ] 6 个 smoke test 通过
- [ ] `--verbose` flag 可用

---

### Sprint 2：纯逻辑模块测试 + 基础设施

**目标**：为不依赖网络的模块补充测试，建立质量基线。

**预计时间**：1-2 天

#### 任务

**S2-1. content_adapter 单元测试**

```python
# tests/test_content_adapter.py
- test_twitter_truncates_to_280_chars
- test_twitter_merges_title_to_text
- test_reddit_warns_missing_subreddit
- test_tiktok_warns_missing_video
- test_tags_appended_with_correct_format
- test_empty_content_validates_with_warning
- test_unknown_platform_uses_defaults
```

**S2-2. cookie_store 单元测试**

```python
# tests/test_cookie_store.py（使用 tmp_path fixture）
- test_save_and_load_cookies
- test_cookie_string_format
- test_load_nonexistent_returns_none
- test_list_accounts
- test_delete_account
- test_corrupted_json_returns_none
```

**S2-3. scheduler 单元测试**

```python
# tests/test_scheduler.py（使用 monkeypatch 重定向 SCHEDULE_FILE）
- test_add_and_list_tasks
- test_remove_task
- test_get_due_tasks_past_time
- test_get_due_tasks_future_time_not_due
- test_mark_task_status
```

**S2-4. batch loader 单元测试**

```python
# tests/test_batch.py
- test_load_from_csv
- test_load_from_json
- test_load_from_directory
- test_csv_with_multiple_platforms
```

**S2-5. 提取 `_get_headers()` 公共方法到基类**

所有 platform client 都有重复的 `_get_headers()` 方法。提取到 `Platform` 基类：

```python
# platforms/base.py
class Platform(ABC):
    ...
    default_ua: str = "Mozilla/5.0 ..."
    base_referer: str = ""

    def _get_headers(self, account: str = "default") -> dict:
        headers = {"User-Agent": self.default_ua}
        cookie = cookie_string(self.name, account)
        if cookie:  # 不发送空 Cookie header
            headers["Cookie"] = cookie
        if self.base_referer:
            headers["Referer"] = self.base_referer
        return headers
```

涉及文件：
- `platforms/base.py`
- 所有 13 个 `client.py`（删除重复的 `_get_headers`，需要特殊 header 的平台 override）

**S2-6. 提取 `me()` 公共方法到基类**

所有平台的 `me()` 方法几乎一模一样，提取到基类。

#### Sprint 2 交付标准

- [ ] `pytest` 通过 20+ 个测试用例
- [ ] 代码重复减少（`_get_headers` 和 `me()` 只在基类定义一次）
- [ ] 空 Cookie 不再发送 `Cookie: ""` header

---

### Sprint 3：登录流程 + 跨平台发布验证

**目标**：验证核心卖点 —— `social publish -p reddit,bilibili`

**预计时间**：2-3 天

#### 任务

**S3-1. 验证 browser_login 流程**

手动测试：
- [ ] `social login reddit` — Playwright 打开浏览器，登录后 cookie 保存到 `~/.socialcli/accounts/reddit/default.json`
- [ ] `social login bilibili` — QR 扫码登录
- [ ] `social accounts` — 显示已登录账号

如有问题修复：
- success_url_pattern 匹配可能不精确
- cookie 过滤（有些平台会返回大量无用 cookie）

**S3-2. 验证跨平台发布**

```bash
# 文字发布到 Reddit
social publish "Test post from SocialCLI" -p reddit -r test -t "CLI Test"

# 视频发布到 Bilibili
social publish -t "测试" -v test.mp4 -p bilibili

# 多平台 dry-run
social publish "Hello world" -p reddit,bilibili --dry-run

# 从 Markdown 文件发布
echo "# Test\n\nHello from SocialCLI" > /tmp/test_post.md
social publish -f /tmp/test_post.md -p reddit -r test
```

**S3-3. publisher.py 添加结果持久化**

目前发布结果只打印到终端，没有记录。添加简单的 JSON 日志：

```python
# 发布后追加到 ~/.socialcli/history.jsonl
{"time": "...", "platform": "reddit", "success": true, "url": "...", "title": "..."}
```

**S3-4. 定时发布端到端验证**

```bash
# 创建定时任务
social publish "Scheduled test" -p reddit -r test --schedule "2026-03-19T10:00:00"

# 查看
social schedule list

# 手动触发
social schedule run
```

#### Sprint 3 交付标准

- [ ] 至少一个平台（Reddit）完成 login → publish 全链路
- [ ] `social publish -p reddit,bilibili --dry-run` 正确适配内容
- [ ] `social schedule` 全套命令可用
- [ ] 发布历史持久化到 `~/.socialcli/history.jsonl`

---

### Sprint 4：扩展到 Twitter（需要登录的平台模板）

**目标**：让第一个需要登录才能操作的国际平台可用，建立模式。

**预计时间**：3-5 天

#### 任务

**S4-1. Twitter 登录验证**

```bash
social login twitter  # 打开浏览器，用户登录 x.com
social accounts       # 应显示 twitter 账号
```

验证 cookie 中包含 `auth_token` 和 `ct0`。

**S4-2. Twitter 搜索验证**

当前代码使用 `SearchTimeline` GraphQL endpoint，queryId 硬编码。

需要研究：
- queryId 是否会变化（大概率会）
- 如果变化，实现动态获取（从 x.com 的 main.js bundle 中提取）
- 参考 `github/` 目录下的参考项目

```bash
social twitter search "AI tools" -n 5 --json
```

**S4-3. Twitter 发推验证**

`CreateTweet` mutation 的 queryId 也是硬编码的。

```bash
social twitter publish "Hello from SocialCLI!"
```

**S4-4. Twitter 热搜验证**

```bash
social twitter trending -n 10 --json
```

#### Sprint 4 交付标准

- [ ] Twitter login/search/trending 至少 2 个可用
- [ ] publish 在登录后可用
- [ ] `social publish -p reddit,twitter --dry-run` 正常工作
- [ ] 有明确的错误信息告知 token 过期/queryId 失效

---

### Sprint 5：抖音 + 小红书（中国平台，复杂反爬）

**目标**：让计划文档中的 Phase 1 原始目标可用。

**预计时间**：5-7 天（反爬签名是主要工作量）

#### 任务

**S5-1. 抖音签名研究**

抖音 API 需要 `a_bogus` 和 `msToken` 参数。

方案选择：
- A：用现有开源库（如 `douyin-tiktok-api`）的签名算法
- B：所有读操作走 Playwright 浏览器（慢但可靠）
- C：混合方案（热搜走 Playwright，搜索走 API + 签名）

**S5-2. 抖音全链路**

```bash
social login douyin          # QR 扫码
social douyin trending       # 热搜
social douyin search "美食"   # 搜索
social douyin publish -t "测试" -v video.mp4  # 发布
```

**S5-3. 小红书全链路**

小红书的 API 签名（xs, xt）更复杂。

```bash
social login xhs
social xhs search "咖啡"
social xhs publish -t "测试" -i photo.jpg
```

#### Sprint 5 交付标准

- [ ] 抖音热搜可用
- [ ] 至少一个中国平台（抖音或小红书）的搜索可用
- [ ] `social publish -p reddit,bilibili,douyin --dry-run` 不崩溃

---

## 冻结项

以下功能/平台在 Sprint 0-5 期间**不开发**，避免分散精力：

| 冻结项 | 原因 |
|--------|------|
| 6 个扩展平台（weibo/kuaishou/youtube/facebook/instagram/threads） | API 不可达，代码是纯骨架 |
| AI 内容生成 (`ai_writer.py`) | 功能完整但非核心路径，依赖用户自备 API key |
| 关键词监控 (`monitor.py`) | 依赖搜索功能先可用 |
| Cookie 加密存储 | 等核心功能稳定后再加 |
| 并行发布 | 等串行发布验证完毕后优化 |
| CI/CD | 等有足够测试后再配置 |
| PyPI 发布 | 等 Sprint 3 完成后评估 |

---

## 里程碑重定义

```
M0 (Sprint 0 完成):  代码不崩溃 — 所有命令至少不报 NameError
M1 (Sprint 1 完成):  2 平台可用 — Reddit + Bilibili 搜索/热榜/发帖
M2 (Sprint 2 完成):  质量基线 — 20+ 测试通过，代码去重
M3 (Sprint 3 完成):  核心卖点可用 — social publish -p reddit,bilibili 全链路
M4 (Sprint 4 完成):  3 平台 — + Twitter
M5 (Sprint 5 完成):  5 平台 — + 抖音 + 小红书 → 可以考虑 PyPI 发布
```

---

## 每日工作流

```bash
# 1. 跑测试
cd /Users/xyh/Desktop/socialcli
.venv/bin/pytest -v

# 2. 手动 smoke test（修改后必跑）
.venv/bin/social --help
.venv/bin/social bilibili trending -n 3 --json
.venv/bin/social reddit search "test" -n 3 --json

# 3. 提交前
.venv/bin/pytest -v && echo "✅ All tests pass"
```
