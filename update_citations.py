#!/usr/bin/env python3
"""
Google Scholar 引用数自动更新脚本
从 defineabc.com (Google Scholar 镜像) 爬取引用数，并更新到 index.html
"""

import re
import json
import base64
import os
import sys
import requests
from bs4 import BeautifulSoup

# 配置
USER_ID = "NKaiUasAAAAJ"
REPO = os.environ.get('GITHUB_REPOSITORY', 'tyshiwo/tyshiwo.github.io')
FILE_PATH = "index.html"
BRANCH = "master"
TOKEN = os.environ.get('TOKEN', '')

def fetch_citations():
    """从 defineabc.com 爬取 Google Scholar 引用数"""
    print("正在从 defineabc.com 获取 Google Scholar 数据...")
    # 使用 defineabc.com 镜像站
    url = f"https://www.defineabc.com/citations?user={USER_ID}&hl=zh-CN"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', id='gsc_rsb_st')
        
        if not table:
            print("未找到引用数据表格，尝试从页面描述提取...")
            # 从页面描述中提取（如 "17,458 次引用"）
            desc = soup.find('meta', attrs={'name': 'description'})
            if desc:
                match = re.search(r'([\d,]+)\s*次引用', desc.get('content', ''))
                if match:
                    citations = int(match.group(1).replace(',', ''))
                    print(f"从描述中提取到引用数: {citations:,}")
                    return citations
            print("无法获取引用数据")
            return None
            
        rows = table.find_all('tr')
        citations = 0
        
        for row in rows[1:]:  # 跳过表头
            cols = row.find_all('td')
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True).replace(',', '')
                if ('引用' in label or 'Cited' in label) and value.isdigit():
                    citations = int(value)
                    break
        
        print(f"总引用数: {citations:,}")
        return citations
        
    except Exception as e:
        print(f"从 defineabc.com 爬取失败: {e}")
        # 尝试官方 Google Scholar
        try:
            print("尝试官方 Google Scholar...")
            url2 = f"https://scholar.google.com/citations?user={USER_ID}&hl=en"
            resp2 = requests.get(url2, headers=headers, timeout=15)
            soup2 = BeautifulSoup(resp2.text, 'html.parser')
            table2 = soup2.find('table', id='gsc_rsb_st')
            if table2:
                rows2 = table2.find_all('tr')
                for row in rows2[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        label = cols[0].get_text(strip=True)
                        value = cols[1].get_text(strip=True).replace(',', '')
                        if 'Cited by' in label and value.isdigit():
                            return int(value)
        except Exception as e2:
            print(f"官方站也失败: {e2}")
        return None

def update_html(citations):
    """更新 index.html 中的引用数"""
    print("\n正在读取 index.html...")
    
    headers = {}
    if TOKEN:
        headers['Authorization'] = f"token {TOKEN}"
    
    # 获取当前文件内容和 SHA
    api_url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}?ref={BRANCH}"
    resp = requests.get(api_url, headers=headers)
    resp.raise_for_status()
    
    data = resp.json()
    sha = data['sha']
    content = base64.b64decode(data['content']).decode('utf-8')
    
    # 更新引用数
    # 格式：Google Scholar (XXX citations)
    pattern = r'>Google Scholar( \(\d+ citations\))?</a>'
    new_text = f'>Google Scholar ({citations:,} citations)</a>'
    
    new_content = re.sub(pattern, new_text, content)
    
    if new_content == content:
        print("内容未变化，无需更新")
        return False
    
    print(f"已更新引用数: {citations:,}")
    
    # 提交更新
    content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
    
    update_data = {
        "message": f"Auto update: Google Scholar citations ({citations:,})",
        "content": content_b64,
        "sha": sha,
        "branch": BRANCH
    }
    
    update_resp = requests.put(
        f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}",
        headers={**headers, 'Content-Type': 'application/json'},
        json=update_data
    )
    
    if update_resp.status_code in [200, 201]:
        print("✅ 已成功更新并提交！")
        return True
    else:
        print(f"提交失败: {update_resp.status_code} {update_resp.text[:200]}")
        return False

def main():
    citations = fetch_citations()
    
    if citations is None:
        print("未获取到引用数据，退出")
        sys.exit(1)
    
    success = update_html(citations)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
