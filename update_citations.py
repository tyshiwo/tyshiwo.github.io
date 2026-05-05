#!/usr/bin/env python3
"""
Google Scholar 引用数自动更新脚本
从 Google Scholar 爬取引用数，并更新到 index.html
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
    """爬取 Google Scholar 引用数"""
    print("正在获取 Google Scholar 数据...")
    url = f"https://scholar.google.com/citations?user={USER_ID}&hl=en"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', id='gsc_rsb_st')
        
        if not table:
            print("未找到引用数据表格")
            return None
            
        rows = table.find_all('tr')
        citations = 0
        
        for row in rows[1:]:  # 跳过表头
            cols = row.find_all('td')
            if len(cols) >= 2:
                label = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True).replace(',', '')
                if 'Cited by' in label and value.isdigit():
                    citations = int(value)
                    break
        
        print(f"总引用数: {citations:,}")
        return citations
        
    except Exception as e:
        print(f"爬取失败: {e}")
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
        print(f"提交失败: {update_resp.status_code} {update_resp.text}")
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
