# SocialCLI 开发计划 v4

> 基于 v3 全量实测结果。7 次真实发帖验证通过，21 项功能测试全 ✅。

---

## 当前位置

```
已验证 ✅（可对外展示）：
  Reddit    — login/search/trending/publish 全链路
  Twitter   — login/search/trending/publish 全链路
  Bilibili  — login/search/trending（publish 等上游修复）

已打通但受限：
  小红书    — login ✅, homefeed ✅, search 被反爬
  LinkedIn  — login ✅, me() ✅, search API 变更

未打通：
  抖音/TikTok — 需要反爬签名
  微博       — 需要 cookie 认证

基础设施 ✅：
  113 tests | CI/CD | 并行发布 | 历史记录 | 定时发布 | config
```

**核心判断**：Reddit + Twitter 已完全可用，是可以对外推广的产品。下一步有两个方向可以并行。

---

## 方向 A：深度打磨已有平台（让 3 个平台做到极致）

### Sprint A1：Twitter 图片发布

**价值**：Twitter 是最常用的平台，纯文字发推太单调，图片是刚需。

**技术方案**：
- Twitter media upload API：`POST upload.twitter.com/1.1/media/upload.json`
- 分片上传流程：INIT → APPEND → FINALIZE → 获取 media_id
- 发推时 `media.media_entities` 带上 media_id

**参考**：github/twitter-cli 有完整的 media upload 实现

**预计时间**：1-2 天

```bash
# 目标
social twitter publish "Check out this image!" -i photo.jpg
social publish "Cross post with image" -i photo.jpg -p twitter,reddit
```

---

### Sprint A2：Reddit 图片发布

**价值**：Reddit 帖子带图片比纯文字互动率高很多。

**技术方案**：
- Reddit 图片上传到 `i.redd.it`
- 用 `/api/media/asset` 获取上传凭证
- 上传图片后拿到 URL，作为 link post 发布

**预计时间**：1-2 天

```bash
social reddit publish -t "Check this out" -i photo.jpg -r pics
```

---

### Sprint A3：发布重试 + 限速

**价值**：网络不稳定时发布失败，用户需要重新输命令。自动重试能大幅改善体验。

**技术方案**：
```python
# publisher.py
for attempt in range(max_retries):
    result = platform.publish(adapted, account)
    if result.success:
        break
    if "rate limit" in result.error.lower():
        time.sleep(backoff * (2 ** attempt))
    else:
        break  # Non-retryable error
```

**预计时间**：0.5 天

---

## 方向 B：扩展中国平台

### Sprint B1：抖音热搜（Playwright 方案）

**价值**：抖音是中国最大的短视频平台，热搜数据有巨大需求。

**技术方案**（不逆向签名，用浏览器兜底）：
1. Playwright 打开 douyin.com/hot
2. 等待页面加载
3. 提取 DOM 中的热搜列表
4. 返回 TrendingItem 列表

**优点**：不需要 a_bogus 签名，100% 可靠
**缺点**：需要 Playwright（已安装过）

**预计时间**：1 天

```bash
social douyin trending -n 10
```

---

### Sprint B2：抖音搜索（Playwright 方案）

同理，用 Playwright 打开搜索页：
1. 导航到 `douyin.com/search/关键词`
2. 等待结果加载
3. 提取视频卡片信息

**预计时间**：1 天

```bash
social douyin search "美食" -n 5
```

---

### Sprint B3：微博热搜

**价值**：微博热搜是中国最重要的舆情数据源。

**技术方案**：
- 参考 github/weibo-cli 的实现
- `weibo.com/ajax/side/hotSearch` 需要 cookie
- 先试 browser-cookie3 提取微博 cookie
- 如果用户登录了微博，API 应该直接可用

**预计时间**：1 天

```bash
social weibo trending -n 20
```

---

### Sprint B4：小红书搜索（Playwright 方案）

API 签名路线受阻，改用浏览器方案：
1. Playwright 打开 xiaohongshu.com/search_result?keyword=xxx
2. 等待加载
3. 提取笔记卡片

**预计时间**：1-2 天

---

## 方向 C：产品化

### Sprint C1：PyPI 发布

- 注册新 PyPI 账号
- 配置 Trusted Publisher
- `git tag v0.1.0 && git push --tags`
- 验证 `pip install socialcli`

### Sprint C2：GitHub Release

- 写 CHANGELOG.md
- 创建 GitHub Release with notes
- 添加 badges（CI status, PyPI version）

### Sprint C3：产品推广

- ProductHunt 发布
- Reddit r/commandline, r/Python 发帖
- Hacker News Show HN
- Twitter/X 发推

---

## 推荐执行顺序

### 第一优先级：让 Twitter 更好用（方向 A）

| Sprint | 内容 | 时间 | 用户价值 |
|--------|------|------|---------|
| **A1** | Twitter 图片发布 | 1-2天 | 高——图文推比纯文字互动 10x |
| **A3** | 发布重试 + 限速 | 0.5天 | 中——稳定性 |

### 第二优先级：中国平台突破（方向 B）

| Sprint | 内容 | 时间 | 用户价值 |
|--------|------|------|---------|
| **B1** | 抖音热搜 (Playwright) | 1天 | 高——中国用户刚需 |
| **B3** | 微博热搜 | 1天 | 高——中国舆情数据 |
| **B2** | 抖音搜索 (Playwright) | 1天 | 中 |
| **B4** | 小红书搜索 (Playwright) | 1-2天 | 中 |

### 第三优先级：发布（方向 C）

| Sprint | 内容 | 时间 | 用户价值 |
|--------|------|------|---------|
| **C1** | PyPI 发布 | 0.5天 | 高——让别人用上 |
| **C2** | GitHub Release | 0.5天 | 中 |

---

## 里程碑

```
当前 ✅  — Reddit + Twitter 全链路, Bilibili search/trending, 113 tests
M6 → A1  — Twitter 图片发布 → 发推带图
M7 → B1  — 抖音热搜 → 中国平台突破
M8 → B3  — 微博热搜 → 舆情数据
M9 → C1  — PyPI v0.1.0 → 公开发布
M10 → B2+B4 — 抖音/小红书搜索 → 中国平台搜索可用
```
