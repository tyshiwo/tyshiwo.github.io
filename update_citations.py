#!/usr/bin/env python3
"""
主页自动更新脚本
1. 从 defineabc.com 爬取 Google Scholar 引用数
2. 从 GitHub API 获取 NJU-PCALab 组织的总 star 数
3. 更新 index.html 并提交
"""

import re
import json
import base64
import os
import sys
import time
import requests
from bs4 import BeautifulSoup

# 配置
USER_ID = "NKaiUasAAAAJ"
ORG_NAME = "NJU-PCALab"
REPO = os.environ.get('GITHUB_REPOSITORY', 'tyshiwo/tyshiwo.github.io')
FILE_PATH = "index.html"
BRANCH = "master"
TOKEN = os.environ.get('TOKEN', '')

def fetch_citations():
    """从 defineabc.com 爬取 Google Scholar 引用数"""
    print("正在从 defineabc.com 获取 Google Scholar 数据...")
    url = f"https://www.defineabc.com/citations?user={USER_ID}&hl=zh-CN"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', id='gsc_rsb_st')
        
        if not table:
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
        
        for row in rows[1:]:
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

def fetch_org_stars(org_name):
    """获取 GitHub 组织的总 star 数"""
    print(f"\n正在获取 {org_name} 组织的 star 总数...")
    
    headers = {}
    if TOKEN:
        headers['Authorization'] = f"token {TOKEN}"
    
    total_stars = 0
    page = 1
    
    while True:
        url = f"https://api.github.com/orgs/{org_name}/repos?page={page}&per_page=100"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            repos = resp.json()
            if not repos:
                break
            
            for repo in repos:
                stars = repo.get('stargazers_count', 0)
                total_stars += stars
                print(f"  {repo['name']}: {stars} stars")
            
            print(f"  当前总计: {total_stars:,} stars")
            page += 1
            time.sleep(0.1)  # 避免速率限制
            
        except Exception as e:
            print(f"获取仓库列表失败: {e}")
            break
    
    print(f"=== {org_name} 总 star 数: {total_stars:,} ===")
    return total_stars

def get_html_content():
    """从 GitHub 获取 index.html 的内容和 SHA"""
    print("\n正在读取 index.html...")
    
    headers = {}
    if TOKEN:
        headers['Authorization'] = f"token {TOKEN}"
    
    api_url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}?ref={BRANCH}"
    resp = requests.get(api_url, headers=headers)
    resp.raise_for_status()
    
    data = resp.json()
    sha = data['sha']
    content = base64.b64decode(data['content']).decode('utf-8')
    
    print(f"已获取文件 (SHA: {sha[:8]}...)")
    return content, sha

def update_content(content, citations, org_stars):
    """更新 HTML 内容中的引用数和 star 数"""
    updated = False
    
    # 1. 更新 Google Scholar 引用数
    # 格式：Google Scholar (XXX citations)
    pattern = r'>Google Scholar( \(\d+ citations\))?</a>'
    new_text = f'>Google Scholar ({citations:,} citations)</a>'
    
    new_content = re.sub(pattern, new_text, content)
    if new_content != content:
        print(f"✅ 已更新 Google Scholar 引用数: {citations:,}")
        updated = True
        content = new_content
    else:
        print("⚠️  Google Scholar 引用数未变化")
    
    # 2. 更新 GitHub 组织 star 数
    # 格式：Github (Group, X,xxx stars)
    # 注意 HTML 中的引号实体：&ldquo; 和 &rdquo;
    pattern2 = r'>Github \(Group\)(, [\d,]+ stars)?</a>'
    replacement2 = f'>Github (Group, {org_stars:,} stars)</a>'
    
    new_content2 = re.sub(pattern2, replacement2, content)
    if new_content2 != content:
        print(f"✅ 已更新组织 star 数: {org_stars:,}")
        updated = True
        content = new_content2
    else:
        # 如果没匹配到，可能是第一次添加，尝试另一种模式
        pattern2_alt = r'>Github \(Group\)</a>'
        replacement2_alt = f'>Github (Group, {org_stars:,} stars)</a>'
        new_content2_alt = re.sub(pattern2_alt, replacement2_alt, content)
        if new_content2_alt != content:
            print(f"✅ 已添加组织 star 数: {org_stars:,}")
            updated = True
            content = new_content2_alt
        else:
            print("⚠️  GitHub 组织链接未找到")
    
    return content, updated

def commit_html(content, sha):
    """提交更新后的 HTML 到 GitHub"""
    print("\n正在提交更新...")
    
    headers = {}
    if TOKEN:
        headers['Authorization'] = f"token {TOKEN}"
    
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    update_data = {
        "message": f"Auto update: citations and org stars",
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
        print("✅ 已成功提交更新！")
        return True
    else:
        print(f"❌ 提交失败: {update_resp.status_code} {update_resp.text[:200]}")
        return False

def main():
    # 1. 获取引用数
    citations = fetch_citations()
    if citations is None:
        print("未获取到引用数据，但仍会继续更新 star 数")
        citations = 0
    
    # 2. 获取组织 star 数
    org_stars = fetch_org_stars(ORG_NAME)
    
    # 3. 读取 HTML
    content, sha = get_html_content()
    
    # 4. 更新内容
    new_content, updated = update_content(content, citations, org_stars)
    
    if not updated:
        print("\n内容未变化，无需提交")
        sys.exit(0)
    
    # 5. 提交
    success = commit_html(new_content, sha)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
