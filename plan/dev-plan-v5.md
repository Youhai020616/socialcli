# SocialCLI 开发计划 v5

> 6 平台热榜 + 2 平台发帖已完成。聚焦高 ROI 功能。

---

## 当前位置

```
热榜 (6/13): Reddit ✅  Twitter ✅  Bilibili ✅  抖音 ✅  微博 ✅  小红书 ✅
搜索 (3/13): Reddit ✅  Twitter ✅  Bilibili ✅
发帖 (2/13): Reddit ✅  Twitter ✅
登录 (5/13): Reddit ✅  Twitter ✅  Bilibili ✅  小红书 ✅  LinkedIn ✅
```

## 策略

硬问题（抖音搜索/小红书搜索/B站发布）都是平台反爬或上游依赖问题，短期无法突破。
**聚焦已通的平台做深**，让 Reddit + Twitter 达到日常使用级别。

---

## Sprint 计划

### Sprint 10：Twitter 图片发布

**价值**：带图推文互动率 10x，是日常使用最缺的功能。

**技术方案**（来自 twitter-cli 参考项目，完整实现可搬）：
1. INIT: `POST upload.twitter.com/i/media/upload.json` → 获取 media_id
2. APPEND: 上传 base64 编码的图片
3. FINALIZE: 确认上传
4. 发推时 `media.media_entities = [{media_id}]`

```bash
# 目标命令
social twitter publish "Check this out!" -i photo.jpg
social publish "Cross post" -i photo.jpg -p twitter,reddit
```

**预计**：1 天

---

### Sprint 11：Reddit 图片发布

**技术方案**：
- Reddit 图片帖 = link post + 图片 URL
- 上传到 Reddit 自有图床：`POST reddit.com/api/media/asset`
- 或直接用 imgur 等外部图床 URL

```bash
social reddit publish -t "My photo" -i photo.jpg -r pics
```

**预计**：1 天

---

### Sprint 12：发布重试 + 错误恢复

```python
# 失败自动重试 1 次，rate limit 自动等待
result = platform.publish(content, account)
if not result.success and is_retryable(result.error):
    time.sleep(backoff)
    result = platform.publish(content, account)
```

**预计**：0.5 天

---

### Sprint 13：微博登录 + 搜索

微博 Chrome 里没有 cookie（用户未登录微博网页版）。
两个选项：
- A: 微博搜索走 Playwright（公开搜索不需要登录）
- B: 提示用户先在 Chrome 登录 weibo.com

```bash
social weibo search "AI" -n 10
```

**预计**：1 天

---

### Sprint 14：Monitor 功能增强

`social monitor` 已有基础代码，现在 3 个平台有搜索能力。
增强：
- 新结果推送到终端（已有）
- 导出到 JSON 文件
- Webhook 通知（可选）

```bash
social monitor -k "socialcli,AI tools" -p reddit,twitter -i 60 --output results.json
```

**预计**：1 天

---

### Sprint 15：AI 内容生成验证

`ai_writer.py` 已有完整代码，只需验证端到端：
- 设置 API key: `social config set ai_api_key sk-xxx`
- 生成内容: `social ai generate "AI tools" -p twitter,reddit`
- 适配内容: `social ai adapt "long article" -p twitter`

**预计**：0.5 天（主要是测试）

---

## 优先级排序

| 优先级 | Sprint | 内容 | 时间 | ROI |
|:------:|--------|------|:----:|:---:|
| **P0** | 10 | Twitter 图片发布 | 1天 | 🔥🔥🔥 |
| **P0** | 12 | 发布重试机制 | 0.5天 | 🔥🔥 |
| **P1** | 11 | Reddit 图片发布 | 1天 | 🔥🔥 |
| **P1** | 15 | AI 内容生成验证 | 0.5天 | 🔥🔥 |
| **P2** | 13 | 微博搜索 | 1天 | 🔥 |
| **P2** | 14 | Monitor 增强 | 1天 | 🔥 |

---

## 里程碑

```
当前 ✅  — 6 平台热榜 + 3 平台搜索 + 2 平台发帖
M11 → Sprint 10+12  — Twitter 图片发布 + 重试 → 日常使用级
M12 → Sprint 11+15  — Reddit 图片 + AI 生成 → 内容创作工作流
M13 → Sprint 13+14  — 微博搜索 + Monitor → 舆情监控
M14 → PyPI 发布     — v0.2.0 正式发布
```
