# kickstarter-wechat-post (Cursor Agent Skill)

把一段产品介绍（Kickstarter/Gemini 推送的好物）一键改写成 **公众号草稿** + **小红书文案**，并自动处理封面/正文配图、推送到微信草稿箱。

这是一个 [Cursor Agent Skill](https://docs.cursor.com)。沉淀了实战中的写作风格、微信 HTML 渲染坑、公众号 API 编码/IP 白名单/草稿 add-vs-update 等经验，并附带可直接复用的发布脚本。

## 内容

```
kickstarter-wechat-post/
├── SKILL.md              # 7 步主流程 + 关键约束
├── content-style.md      # 小红书/公众号写作风格与结构模板
├── wechat-pitfalls.md    # 微信渲染/API/IP白名单/Windows 踩坑清单
└── scripts/
    └── publish_wechat.py # 发布脚本（支持 draft/add 与 draft/update）
```

## 安装

把 `kickstarter-wechat-post/` 目录放到任意一处：

- 个人（所有项目可用）：`~/.cursor/skills/kickstarter-wechat-post/`
- 项目（随仓库分享）：`<repo>/.cursor/skills/kickstarter-wechat-post/`

一行安装（个人，macOS/Linux）：

```bash
git clone https://github.com/ositoakabear/kickstarter-wechat-post-skill.git /tmp/kwp \
  && mkdir -p ~/.cursor/skills \
  && cp -r /tmp/kwp/kickstarter-wechat-post ~/.cursor/skills/
```

Windows PowerShell：

```powershell
git clone https://github.com/ositoakabear/kickstarter-wechat-post-skill.git $env:TEMP\kwp
New-Item -ItemType Directory -Force "$HOME\.cursor\skills" | Out-Null
Copy-Item -Recurse "$env:TEMP\kwp\kickstarter-wechat-post" "$HOME\.cursor\skills\"
```

## 使用

在 Cursor 里让 agent「用 kickstarter-wechat-post」或直接给它产品素材让它生成公众号/小红书推文，skill 会被加载并按流程执行。

发布脚本依赖 `requests`：

```bash
pip install requests
```

需配置微信公众号 `.env`（AppID/AppSecret/封面/作者，详见 SKILL.md）。

## License

MIT
