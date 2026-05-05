#!/usr/bin/env python3
"""
主页自动更新工具 - 通过 GitHub API 更新 index.html
使用方式：
  python3 update_homepage.py news "05/2026 - 新内容在这里"
  python3 update_homepage.py upload-image /path/to/image.png "images/new-image.png"
"""

import os
import sys
import json
import base64
import requests

# GitHub 配置（从环境变量读取 token）
TOKEN = os.environ.get('UPDATE_TOKEN', '')
REPO = "tyshiwo/tyshiwo.github.io"
BRANCH = "master"
BASE_URL = f"https://api.github.com/repos/{REPO}/contents"

headers = {
    "Authorization": f"token {TOKEN}",
    "Content-Type": "application/json"
}

def get_file(path):
    """获取文件内容和 SHA"""
    url = f"{BASE_URL}/{path}?ref={BRANCH}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data['content']).decode('utf-8')
    return content, data['sha']

def update_file(path, content, sha, message):
    """更新文件"""
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    url = f"{BASE_URL}/{path}"
    data = {
        "message": message,
        "content": content_b64,
        "sha": sha,
        "branch": BRANCH
    }
    resp = requests.put(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()

def add_news(news_text):
    """添加新闻到 index.html 的 News 部分"""
    print(f"正在添加新闻: {news_text}")
    
    # 读取当前内容
    content, sha = get_file("index.html")
    
    # 构造新条目
    new_item = f'  <li><p style="text-align:left">{news_text} </p></li>\n'
    
    # 找到 News 部分的 <ul> 并插入
    lines = content.split('\n')
    new_lines = []
    in_news = False
    ul_inserted = False
    
    for line in lines:
        new_lines.append(line)
        if '<h2>News</h2>' in line:
            in_news = True
        if in_news and '<ul>' in line and not ul_inserted:
            # 在 <ul> 后插入新条目（添加到列表开头，保持时间倒序）
            new_lines.append(new_item)
            ul_inserted = True
    
    new_content = '\n'.join(new_lines)
    
    # 提交更新
    result = update_file("index.html", new_content, sha, f"Add news: {news_text[:50]}")
    print("✅ 新闻已添加！主页将在 1-2 分钟内更新。")
    print(f"   查看: https://tyshiwo.github.io/")
    return result

def upload_image(local_path, repo_path):
    """上传图片到仓库"""
    print(f"正在上传图片: {local_path} -> {repo_path}")
    
    # 读取图片
    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    
    # 检查文件是否已存在
    try:
        old_content, sha = get_file(repo_path)
        # 更新现有文件
        data = {
            "message": f"Update image: {repo_path}",
            "content": content,
            "sha": sha,
            "branch": BRANCH
        }
        url = f"{BASE_URL}/{repo_path}"
        resp = requests.put(url, headers=headers, json=data)
    except:
        # 创建新文件
        data = {
            "message": f"Upload image: {repo_path}",
            "content": content,
            "branch": BRANCH
        }
        url = f"{BASE_URL}/{repo_path}"
        resp = requests.put(url, headers=headers, json=data)
    
    resp.raise_for_status()
    result = resp.json()
    print("✅ 图片已上传！")
    print(f"   访问地址: https://raw.githubusercontent.com/{REPO}/{BRANCH}/{repo_path}")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方式:")
        print("  python3 update_homepage.py news '05/2026 - 新内容'")
        print("  python3 update_homepage.py upload-image /local/path.png images/new.png")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "news":
        if len(sys.argv) < 3:
            print("错误: 请提供新闻内容")
            sys.exit(1)
        news_text = ' '.join(sys.argv[2:])
        add_news(news_text)
    
    elif command == "upload-image":
        if len(sys.argv) < 4:
            print("错误: 请提供本地路径和仓库路径")
            sys.exit(1)
        local_path = sys.argv[2]
        repo_path = sys.argv[3]
        upload_image(local_path, repo_path)
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
