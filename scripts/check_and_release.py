#!/usr/bin/env python3
"""
PJSK (初音未来：缤纷舞台) 国服官服与B服版本检测与下载脚本
用于 GitHub Actions 自动检查更新、下载 APK、记录版本并在 GitHub Release 中合并发布
"""

import os
import sys
import json
import time
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

OFFICIAL_REDIRECT_URL = "https://pjskyy.ugurl.cn/d9WHL"
BILIGAME_API_URL = "https://line1-h5-pc-api.biligame.com/game/detail/gameinfo?game_base_id=111995"
BILIGAME_REFERER = "https://www.biligame.com/detail/?id=111995"

VERSIONS_FILE = "versions.json"


def get_current_versions():
    """读取本地存储的版本记录"""
    if os.path.exists(VERSIONS_FILE):
        try:
            with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[警告] 读取 {VERSIONS_FILE} 失败: {e}，将初始化空记录")
    return {
        "official": {"filename": "", "url": "", "size_mb": 0, "version": ""},
        "bilibili": {"filename": "", "url": "", "size_mb": 0, "version_code": 0, "version_name": ""},
        "last_updated": ""
    }


def save_versions(data):
    """保存版本记录"""
    with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_official_info():
    """检测官服最新安装包信息 (通过 302 重定向解析)"""
    print("[检测] 正在检查官服最新版本...")
    req = urllib.request.Request(
        OFFICIAL_REDIRECT_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        final_url = resp.geturl()
        filename = final_url.split("?")[0].split("/")[-1]
        size_bytes = int(resp.headers.get("Content-Length", 0))
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        # 尝试从文件名或 URL 提取版本标识 (例如 pjsk_51199071a_v23509_3746_0919_1773014796.apk)
        ver_match = re.search(r'_v?(\d+_\d+)', filename)
        version_tag = ver_match.group(1) if ver_match else filename

        return {
            "channel": "官方官服",
            "url": final_url,
            "filename": filename,
            "size_mb": size_mb,
            "version": version_tag,
            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        }


def fetch_bilibili_info():
    """检测 Bilibili 服最新安装包信息 (通过 biligame API)"""
    print("[检测] 正在检查 Bilibili 服最新版本...")
    req = urllib.request.Request(
        BILIGAME_API_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        data = body.get("data", {})
        download_url = data.get("android_download_link", "")
        filename = download_url.split("?")[0].split("/")[-1]
        size_bytes = data.get("android_pkg_size", 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        version_code = data.get("android_pkg_ver", 0)

        # 从文件名解析版本名，如 cywlbfwt_6.0.0_20260225_024313_cdb4e.apk
        ver_match = re.search(r'_(\d+\.\d+\.\d+)_', filename)
        version_name = ver_match.group(1) if ver_match else f"code-{version_code}"

        return {
            "channel": "Bilibili服",
            "package_name": data.get("android_pkg_name", ""),
            "version_code": version_code,
            "version_name": version_name,
            "url": download_url,
            "filename": filename,
            "size_mb": size_mb,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": BILIGAME_REFERER
            }
        }


def download_apk(info, output_dir="."):
    """带进度指示的文件下载"""
    dest_path = os.path.join(output_dir, info["filename"])
    print(f"\n[下载] 开始下载 [{info['channel']}]: {info['filename']}")
    print(f"       目标大小: {info['size_mb']} MB")
    print(f"       下载地址: {info['url']}")

    req = urllib.request.Request(info["url"], headers=info["headers"])
    start_time = time.time()
    
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_path, "wb") as f:
        downloaded = 0
        total = int(resp.headers.get("Content-Length", 0))
        chunk_size = 2 * 1024 * 1024  # 2MB 缓冲
        last_print = 0

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)

            # 每 50MB 或完成时打印一次进度
            if downloaded - last_print >= 50 * 1024 * 1024 or downloaded == total:
                elapsed = time.time() - start_time
                speed = (downloaded / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                pct = (downloaded / total * 100) if total > 0 else 0
                print(f"       已下载: {downloaded / (1024 * 1024):.1f} MB / {total / (1024 * 1024):.1f} MB ({pct:.1f}%) - {speed:.2f} MB/s")
                last_print = downloaded

    print(f"[下载完成] 已保存至: {dest_path}\n")
    return dest_path


def main():
    check_only = "--check-only" in sys.argv
    force_download = "--force" in sys.argv

    recorded = get_current_versions()
    official_info = fetch_official_info()
    bili_info = fetch_bilibili_info()

    official_updated = (official_info["filename"] != recorded.get("official", {}).get("filename"))
    bili_updated = (bili_info["filename"] != recorded.get("bilibili", {}).get("filename"))

    print("\n--- 版本检测结果 ---")
    print(f"官服线上文件: {official_info['filename']} | 已记录: {recorded.get('official', {}).get('filename')}")
    print(f"B 服线上文件: {bili_info['filename']} | 已记录: {recorded.get('bilibili', {}).get('filename')}")
    print(f"官服是否有更新: {official_updated}")
    print(f"B 服是否有更新: {bili_updated}")
    print("--------------------\n")

    has_update = official_updated or bili_updated or force_download

    # 设置 GitHub Actions 输出变量
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"has_update={'true' if has_update else 'false'}\n")
            f.write(f"official_updated={'true' if official_updated else 'false'}\n")
            f.write(f"bili_updated={'true' if bili_updated else 'false'}\n")

    if not has_update:
        print("[完成] 双服均无新版本发布。")
        return

    # 生成本次 Release 标签与标题
    cst_time = datetime.now(timezone(timedelta(hours=8)))
    timestamp_tag = cst_time.strftime("%Y%m%d-%H%M")
    release_tag = f"release-{timestamp_tag}"
    release_title = f"《初音未来：缤纷舞台》国服安装包更新 ({cst_time.strftime('%Y-%m-%d')})"

    release_body = f"""### 《初音未来：缤纷舞台》国服双渠道客户端合并发布

发布时间：{cst_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)

#### 包含渠道与文件信息

1. **官方官服**
   * 文件名：`{official_info['filename']}`
   * 文件大小：`{official_info['size_mb']} MB`
   * 构建标识：`{official_info['version']}`
   * 更新状态：{'新版本' if official_updated else '保持当前最新'}

2. **Bilibili 服（B服）**
   * 文件名：`{bili_info['filename']}`
   * 文件大小：`{bili_info['size_mb']} MB`
   * 客户端版本：`{bili_info['version_name']}` (内部版本号: `{bili_info['version_code']}`)
   * 更新状态：{'新版本' if bili_updated else '保持当前最新'}

> **提示**：国服支持“官B同服”游玩。B服账号登录请选择带 bilibili 标识的安装包。
"""

    # 额外将 release notes 写到独立文件，保证工作流创建 release 时万无一失
    with open("release_notes.md", "w", encoding="utf-8") as f:
        f.write(release_body)

    if github_output:
        # 在 GitHub Actions 输出中输出 release_tag, release_title 等
        delimiter = "EOF_DELIMITER_PJSK"
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"release_tag={release_tag}\n")
            f.write(f"release_title={release_title}\n")
            f.write(f"official_filename={official_info['filename']}\n")
            f.write(f"bili_filename={bili_info['filename']}\n")
            f.write(f"release_body<<{delimiter}\n{release_body}\n{delimiter}\n")

    if check_only:
        print("[Check-Only 模式] 发现新版本，退出不执行下载。")
        return

    # 下载双服 APK 以供上传到同一个 Release
    print("[执行] 开始下载双服最新安装包...")
    official_apk = download_apk(official_info)
    bili_apk = download_apk(bili_info)

    # 更新本地 versions.json
    recorded["official"] = {
        "filename": official_info["filename"],
        "url": official_info["url"],
        "size_mb": official_info["size_mb"],
        "version": official_info["version"]
    }
    recorded["bilibili"] = {
        "filename": bili_info["filename"],
        "url": bili_info["url"],
        "size_mb": bili_info["size_mb"],
        "version_code": bili_info["version_code"],
        "version_name": bili_info["version_name"]
    }
    recorded["last_updated"] = cst_time.strftime("%Y-%m-%d %H:%M:%S")

    save_versions(recorded)
    print(f"[完成] 已更新本地 {VERSIONS_FILE}")


if __name__ == "__main__":
    main()
