# 微信公众号 / 发布踩坑清单

实战中踩过的坑与确定可用的解法。按主题分组。

## 一、微信 HTML 渲染

微信用自有渲染引擎，标准 CSS 很多被剥离，尤其移动端。

### 列表：不要用 `<ul>/<li>`
移动端常渲染成空心点或丢失。改用自定义段落：

```html
<p style="margin:8px 0;padding-left:1.4em;text-indent:-1.4em;">
  <span style="color:#e74c3c;">●</span> 这是一条要点文字……
</p>
```

### 并排图：不要用 `display:flex`
flex 在微信里易换行错位、图下文字乱跑。用 `<table>` 布局，单元格内 `<img>` 与文字都设 `display:block`：

```html
<table style="width:100%;border-spacing:8px;">
  <tr>
    <td style="width:50%;text-align:center;vertical-align:top;">
      <img src="bird_standing_normal.jpg" style="display:block;width:100%;border-radius:8px;"/>
      <span style="display:block;margin-top:6px;">常态：空气良好</span>
    </td>
    <td style="width:50%;text-align:center;vertical-align:top;">
      <img src="bird_dropped_dead.jpg" style="display:block;width:100%;border-radius:8px;"/>
      <span style="display:block;margin-top:6px;">死态：CO₂ 超标，快开窗</span>
    </td>
  </tr>
</table>
```

### 竞品对比：不要靠横向滚动
`overflow-x:auto` 的滚动样式在移动端被微信剥离，宽表格被截断看不全。改成**竖向卡片**，每个对比维度一张卡，本品高亮：

```html
<section style="border:1px solid #eee;border-radius:10px;padding:12px;margin:10px 0;">
  <p style="font-weight:bold;margin:0 0 8px;">显示方式</p>
  <p style="margin:4px 0;background:#fff7e6;padding:6px;border-radius:6px;">🏆 本品：纯物理动态</p>
  <p style="margin:4px 0;">竞品A：LED/App</p>
  <p style="margin:4px 0;">竞品B：数字折线图</p>
</section>
```

### 成对图易摆反
站立/倒下、前/后这类成对图，改完务必让用户在**手机端**预览核对。文件名语义化能减少出错。

## 二、API

### access_token
`GET /cgi-bin/token?grant_type=client_credential&appid=..&secret=..`，有效期约 2 小时，按需重取。

### 中文编码导致 `45003 title size out of limit`
`requests.post(json=...)` 默认 ASCII 转义中文，字节数翻倍超限。必须手动 UTF-8：

```python
headers = {"Content-Type": "application/json; charset=utf-8"}
data = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
requests.post(url, params={"access_token": token}, data=data, headers=headers)
```

### 草稿：add vs update
- 新建：`POST /cgi-bin/draft/add`，body `{"articles":[article]}`，返回 `media_id`。
- 更新（避免草稿堆积）：`POST /cgi-bin/draft/update`，body `{"media_id":id,"index":0,"articles":article}`（注意 update 的 `articles` 是单对象，不是数组）。

### 封面与正文图
- 封面：`POST /cgi-bin/material/add_material?type=image`（永久素材），拿 `thumb_media_id`。
- 正文外链图微信不显示，必须 `POST /cgi-bin/media/uploadimg` 转成微信 CDN URL（`*.qpic.cn`）后替换正文 `src`。脚本已自动扫描 `<img>` 并处理；已是 `qpic.cn` 的跳过。

### 常见错误码
| 码 | 含义 | 解法 |
|---|---|---|
| 40013 | invalid appid | AppID 错/没被 .env 覆盖（用 `os.environ[k]=v`）|
| 40001 | invalid credential | AppSecret 错或 token 失效 |
| 40164 | invalid ip | 加服务器公网 IP 到白名单，等缓存 |
| 45003 | title size out of limit | 用 `ensure_ascii=False` UTF-8 编码 |
| 45009 | 频率上限 | 稍后重试 |
| 48001 | 无接口权限 | 确认账号类型/认证 |

## 三、IP 白名单

调 API 的机器公网 IP 必须在「公众号后台 → 设置与开发 → 基本配置 → IP 白名单」。
- 改完有**几分钟缓存延迟**，期间仍可能 `40164`，需重试。
- 后台改白名单可能触发管理员扫码安全验证。
- 用浏览器自动化操作后台时，元素易 stale，必要时重新 snapshot 或用 `Runtime.evaluate` 直接 JS 点击。

## 四、.env 加载
覆盖式写入，避免历史环境变量里的错误值不被更新：

```python
for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip().strip('"').strip("'")  # 不要用 setdefault
```

## 五、Windows / PowerShell 执行
- 中文命令行参数在 PowerShell 易乱码/解析失败 → 用一个 `run_once.py` 内部覆盖 `sys.argv` 后调 `main()`，并用基于 `__file__` 的**绝对路径**，从项目根目录执行。
- `2>nul` 是 cmd 语法，PowerShell 里会当成写文件 `nul` 报错；PowerShell 用 `2>$null`，或直接 `cmd /c "..."`。
- 列目录/中文路径输出乱码时先 `chcp 65001`。

## 六、大文件（GIF）下载超时
流式下载 + 长超时 + 分块写：

```python
with requests.get(url, stream=True, timeout=120) as r:
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
```
