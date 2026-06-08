---
name: kickstarter-wechat-post
description: >-
  Turn a Kickstarter (or similar) product writeup into a polished WeChat
  official-account draft and a Xiaohongshu (小红书) markdown post, including
  cover/inline image handling and pushing to the WeChat draft box via API. Use
  when the user wants to generate 公众号推文 / 小红书文案 from product material,
  publish to a WeChat draft, or asks about WeChat HTML rendering, draft/add vs
  draft/update, inline image upload, access_token, or IP whitelist issues.
disable-model-invocation: true
---

# Kickstarter → 公众号 + 小红书 推文

把一段产品介绍（Gemini/Kickstarter 推送的好物）改写成两份成品：
- **小红书**：markdown 文案（含配图说明），保存并在对话里输出。
- **公众号**：内联样式 HTML，自动上传图片到微信 CDN，推送到草稿箱。

## 工作流

复制此清单跟踪进度：

```
- [ ] 1. 收集素材：拿到产品文案 + 图片/GIF 来源链接
- [ ] 2. 下载图片到本地素材目录
- [ ] 3. 写小红书 markdown（见 content-style.md 风格）
- [ ] 4. 写公众号 HTML（见 content-style.md + wechat-pitfalls.md）
- [ ] 5. 配置 .env（AppID/AppSecret/封面/作者）
- [ ] 6. 跑 publish 脚本推到草稿箱
- [ ] 7. 让用户在公众号后台预览（含手机端）确认
```

### 1-2. 素材与图片

- 图片**必须是产品实物**。封面与正文配图都要和真机一致：优先从官方/媒体页下载原图，文生图只在拿不到实物时用且要尽量还原。
- 大文件（GIF）用流式下载 + 长超时（120s），见 `wechat-pitfalls.md`。
- 把图片下到一个固定本地目录（如用户指定的 `E:\公众号\...`），文件名语义化：`bird_standing_normal.jpg` / `bird_dropped_dead.jpg` / `lifestyle_*.jpg` / `transition_*.gif`。

### 3. 小红书 markdown

风格、结构、配图说明、标签规范见 [content-style.md](content-style.md)。
要点：口语化、emoji、`(配图 N: 说明)` 占位、结尾加垂直领域标签 + 固定标签如 `#本周好物推荐`。**公众号改了什么，小红书要同步改。**

### 4. 公众号 HTML

风格见 [content-style.md](content-style.md)；微信渲染/排版的坑见 [wechat-pitfalls.md](wechat-pitfalls.md)（**务必先读**）。
高频坑速记：
- 不要用 `<ul>/<li>`，改成带 `●` span 的自定义 `<p>`。
- 并排图不要 `display:flex`，用 `<table>` 布局。
- 竞品对比不要靠 `overflow-x:auto` 横向滚动（移动端被剥离），改成**竖向卡片**每个维度一张卡。
- 标题用统一前缀，如 `本周好物推荐：xxx`。
- 观察员点评署名按用户约定（如「"本周好物"观察员阿熊」）。

### 5. 配置 .env

```
WECHAT_APPID=...
WECHAT_APPSECRET=...
WECHAT_AUTHOR=...
WECHAT_DEFAULT_COVER=assets/default-cover.jpg
WECHAT_CONTENT_SOURCE_URL=
WECHAT_DRAFT_MEDIA_ID=          # 可选：填了则更新该草稿而非新建
```

### 6. 推送到草稿箱

用打包的脚本 `scripts/publish_wechat.py`（复制到目标项目，依赖 `requests`）。它会：取 access_token → 扫描正文 `<img>` 自动下载并上传到微信 CDN 替换链接 → 上传封面拿 `thumb_media_id` → 写草稿。

```bash
# 新建草稿
python scripts/publish_wechat.py output/wechat/xxx.html \
  --title "本周好物推荐：xxx" --digest "50-120字摘要"

# 覆盖更新已有草稿（避免草稿箱堆积）
python scripts/publish_wechat.py output/wechat/xxx.html \
  --title "..." --digest "..." --update-media-id <已有草稿 media_id>

# 只校验不发
python scripts/publish_wechat.py output/wechat/xxx.html --title t --digest d --dry-run
```

Windows 下中文参数易被 PowerShell 解析出错时，用一个 `run_once.py` 覆盖 `sys.argv` 内部调用 `main()`，并用绝对路径。详见 `wechat-pitfalls.md`。

### 7. 验收

让用户在公众号后台预览，**重点查手机端**：图片是否显示、竖向卡片是否完整、并排图文字是否正确堆叠、站立/倒下等成对图片是否摆反。按反馈改 HTML 后**重新跑脚本覆盖更新**。

## 关键技术约束（细节见 wechat-pitfalls.md）

- **API 中文编码**：`draft/add` / `draft/update` 必须 `json.dumps(..., ensure_ascii=False).encode('utf-8')` + `Content-Type: application/json; charset=utf-8`，否则中文被 ASCII 转义字节翻倍触发 `45003 title size out of limit`。
- **.env 加载**：用 `os.environ[key]=value` 覆盖，不要 `setdefault`（否则旧的错误 AppID 不会被覆盖，报 `40013/40001`）。
- **IP 白名单**：服务器公网 IP 必须加入公众号后台白名单，否则 `40164 invalid ip`；改完有几分钟缓存延迟需重试。
- **外链图片不显示**：微信屏蔽外部图片，必须经 `media/uploadimg` 转成微信 CDN URL（脚本已自动处理）。

## 资源

- [content-style.md](content-style.md)：小红书 + 公众号 写作风格与结构模板。
- [wechat-pitfalls.md](wechat-pitfalls.md)：微信 HTML 渲染、API、IP 白名单、Windows 执行等踩坑清单。
- [scripts/publish_wechat.py](scripts/publish_wechat.py)：可直接复用的发布脚本（支持 add / update）。
