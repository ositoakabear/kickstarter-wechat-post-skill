"""Publish a WeChat official account draft from a prepared HTML file."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import requests


API_BASE = "https://api.weixin.qq.com/cgi-bin"


COMMON_ERRORS = {
    40001: "AppSecret 可能错误, 或 access_token 已失效。",
    40164: "调用接口的 IP 不在公众号后台 IP 白名单中。",
    45009: "接口调用频率达到上限, 稍后再试。",
    48001: "公众号未获得该接口权限, 请确认账号类型和认证状态。",
}


class WeChatApiError(RuntimeError):
    def __init__(self, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise WeChatApiError(f"缺少环境变量 {name}, 请先复制 .env.example 为 .env 并填写。")
    return value


def check_wechat_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise WeChatApiError(f"微信接口返回了非 JSON 内容: HTTP {response.status_code}") from exc

    errcode = payload.get("errcode", 0)
    if errcode:
        hint = COMMON_ERRORS.get(errcode, "请查看微信公众平台接口文档。")
        message = payload.get("errmsg", "unknown error")
        raise WeChatApiError(f"微信接口错误 {errcode}: {message}\n提示: {hint}", payload)

    return payload


def get_access_token(appid: str, appsecret: str) -> str:
    response = requests.get(
        f"{API_BASE}/token",
        params={
            "grant_type": "client_credential",
            "appid": appid,
            "secret": appsecret,
        },
        timeout=20,
    )
    payload = check_wechat_response(response)
    token = payload.get("access_token")
    if not token:
        raise WeChatApiError("微信接口未返回 access_token。", payload)
    return token


def upload_thumb_media(access_token: str, cover_path: Path) -> str:
    if not cover_path.exists():
        raise WeChatApiError(f"封面图不存在: {cover_path}")

    mime_type = mimetypes.guess_type(cover_path.name)[0] or "image/jpeg"
    with cover_path.open("rb") as file_obj:
        response = requests.post(
            f"{API_BASE}/material/add_material",
            params={"access_token": access_token, "type": "image"},
            files={"media": (cover_path.name, file_obj, mime_type)},
            timeout=60,
        )

    payload = check_wechat_response(response)
    media_id = payload.get("media_id")
    if not media_id:
        raise WeChatApiError("封面上传成功但微信未返回 media_id。", payload)
    return media_id


def upload_inline_images(access_token: str, content: str) -> str:
    """Scan HTML content for inline images and upload them to WeChat CDN."""
    srcs = re.findall(r'<img[^>]+src=["\'](.*?)["\']', content, re.IGNORECASE)
    if not srcs:
        return content

    print(f"检测到正文中包含 {len(srcs)} 个插图，准备自动上传到微信 CDN...")
    
    # 去重
    unique_srcs = list(set(srcs))
    for src in unique_srcs:
        # 跳过已经是微信 CDN 的链接
        if "qpic.cn" in src:
            continue
            
        try:
            # 下载或读取图片
            if src.startswith(("http://", "https://")):
                print(f"正在从网络下载插图: {src}")
                img_res = requests.get(src, timeout=30)
                img_res.raise_for_status()
                img_bytes = img_res.content
                filename = Path(urllib.parse.urlparse(src).path).name or "image.jpg"
            else:
                local_path = Path(src)
                if not local_path.is_absolute():
                    # 以项目根目录为基准
                    project_root = Path(__file__).resolve().parents[1]
                    local_path = project_root / local_path
                if not local_path.exists():
                    print(f"警告: 本地插图未找到: {local_path}，跳过上传。")
                    continue
                img_bytes = local_path.read_bytes()
                filename = local_path.name

            # 猜测 mime type
            mime_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
            
            # 上传到微信
            print(f"正在上传到微信 CDN: {filename} ({len(img_bytes)} 字节)...")
            response = requests.post(
                f"{API_BASE}/media/uploadimg",
                params={"access_token": access_token},
                files={"media": (filename, img_bytes, mime_type)},
                timeout=60,
            )
            payload = check_wechat_response(response)
            wechat_url = payload.get("url")
            if not wechat_url:
                print(f"警告: 微信未返回上传图片的 URL", payload)
                continue
                
            print(f"插图上传成功！微信 CDN URL: {wechat_url}")
            # 替换正文中所有的旧链接为微信 CDN 链接
            content = content.replace(src, wechat_url)
            
        except Exception as e:
            print(f"警告: 插图 {src} 上传微信 CDN 失败: {e}，跳过替换。", file=sys.stderr)
            
    return content


def add_draft(
    access_token: str,
    *,
    title: str,
    author: str,
    digest: str,
    content: str,
    content_source_url: str,
    thumb_media_id: str,
) -> str:
    article = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": content,
        "content_source_url": content_source_url,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    # 显式使用 UTF-8 进行 JSON 序列化，避免 python requests 默认使用 ascii 转义 unicode，
    # 从而导致中文字符串在传输中字节数成倍膨胀（触发字数超限 45003 错误）
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data_bytes = json.dumps({"articles": [article]}, ensure_ascii=False).encode('utf-8')
    response = requests.post(
        f"{API_BASE}/draft/add",
        params={"access_token": access_token},
        data=data_bytes,
        headers=headers,
        timeout=60,
    )
    payload = check_wechat_response(response)
    media_id = payload.get("media_id")
    if not media_id:
        raise WeChatApiError("草稿创建成功但微信未返回 media_id。", payload)
    return media_id


def update_draft(
    access_token: str,
    *,
    media_id: str,
    index: int,
    title: str,
    author: str,
    digest: str,
    content: str,
    content_source_url: str,
    thumb_media_id: str,
) -> str:
    """覆盖更新已存在的草稿，而不是新建一条。"""
    article = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": content,
        "content_source_url": content_source_url,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    # 与 add_draft 相同，显式 UTF-8 序列化避免中文被 ascii 转义导致字节膨胀
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data_bytes = json.dumps(
        {"media_id": media_id, "index": index, "articles": article},
        ensure_ascii=False,
    ).encode("utf-8")
    response = requests.post(
        f"{API_BASE}/draft/update",
        params={"access_token": access_token},
        data=data_bytes,
        headers=headers,
        timeout=60,
    )
    check_wechat_response(response)
    return media_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload a prepared WeChat article HTML file to the official account draft box.")
    parser.add_argument("html_file", type=Path, help="公众号正文 HTML 文件路径")
    parser.add_argument("--title", required=True, help="草稿标题")
    parser.add_argument("--digest", required=True, help="草稿摘要, 建议 50-120 字")
    parser.add_argument("--cover", type=Path, help="封面图路径。不传则使用 WECHAT_DEFAULT_COVER")
    parser.add_argument("--author", help="作者。不传则使用 WECHAT_AUTHOR")
    parser.add_argument("--source-url", help="原文链接。不传则使用 WECHAT_CONTENT_SOURCE_URL")
    parser.add_argument(
        "--update-media-id",
        help="已存在草稿的 media_id。传入则覆盖更新该草稿(draft/update), 不传则新建(draft/add)。不传时也可用环境变量 WECHAT_DRAFT_MEDIA_ID。",
    )
    parser.add_argument("--index", type=int, default=0, help="多图文草稿中要更新的文章序号, 默认 0(单图文)。")
    parser.add_argument("--dry-run", action="store_true", help="只校验文件和配置, 不调用微信 API")
    return parser.parse_args()


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    args = parse_args()
    html_path = args.html_file
    if not html_path.exists():
        raise WeChatApiError(f"HTML 文件不存在: {html_path}")

    content = html_path.read_text(encoding="utf-8")
    appid = require_env("WECHAT_APPID")
    appsecret = require_env("WECHAT_APPSECRET")
    author = args.author or os.environ.get("WECHAT_AUTHOR", "").strip()
    cover = args.cover or Path(os.environ.get("WECHAT_DEFAULT_COVER", "assets/default-cover.jpg"))
    source_url = args.source_url or os.environ.get("WECHAT_CONTENT_SOURCE_URL", "").strip()

    if not author:
        raise WeChatApiError("缺少作者, 请设置 WECHAT_AUTHOR 或传入 --author。")
    if not cover.is_absolute():
        cover = project_root / cover

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "dry-run",
                    "html_file": str(html_path),
                    "title": args.title,
                    "digest": args.digest,
                    "author": author,
                    "cover": str(cover),
                    "source_url": source_url,
                    "content_chars": len(content),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    update_media_id = args.update_media_id or os.environ.get("WECHAT_DRAFT_MEDIA_ID", "").strip()

    access_token = get_access_token(appid, appsecret)
    # 自动上传正文插图到微信 CDN 并替换链接
    content = upload_inline_images(access_token, content)

    thumb_media_id = upload_thumb_media(access_token, cover)

    if update_media_id:
        draft_media_id = update_draft(
            access_token,
            media_id=update_media_id,
            index=args.index,
            title=args.title,
            author=author,
            digest=args.digest,
            content=content,
            content_source_url=source_url,
            thumb_media_id=thumb_media_id,
        )
        print(json.dumps({"ok": True, "mode": "update", "draft_media_id": draft_media_id}, ensure_ascii=False, indent=2))
    else:
        draft_media_id = add_draft(
            access_token,
            title=args.title,
            author=author,
            digest=args.digest,
            content=content,
            content_source_url=source_url,
            thumb_media_id=thumb_media_id,
        )
        print(json.dumps({"ok": True, "mode": "add", "draft_media_id": draft_media_id}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WeChatApiError as exc:
        print(f"发布失败: {exc}", file=sys.stderr)
        if exc.payload:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
