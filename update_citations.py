#!/usr/bin/env python3
"""Refresh homepage citation and public organization star counts."""
import base64
import os
import re
import sys
import requests
from bs4 import BeautifulSoup

USER_ID = 'NKaiUasAAAAJ'
ORG_NAME = 'NJU-PCALab'
REPO = os.environ.get('GITHUB_REPOSITORY', 'tyshiwo/tyshiwo.github.io')
BRANCH = 'master'
TOKEN = os.environ.get('TOKEN', '')
API = 'https://api.github.com'

def github_headers():
    headers = {'Accept': 'application/vnd.github+json'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    return headers

def fetch_citations():
    try:
        response = requests.get(
            f'https://scholar.google.com/citations?user={USER_ID}&hl=en',
            headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        profile = soup.select_one('#gsc_prf_in')
        if not profile or 'Ying Tai' not in profile.get_text():
            raise ValueError('Expected scholar profile not found')
        for row in soup.select('#gsc_rsb_st tr'):
            cells = row.find_all('td')
            if len(cells) >= 2 and cells[0].get_text(strip=True) in ('Citations', 'Cited by'):
                value = cells[1].get_text(strip=True).replace(',', '')
                if value.isdigit() and int(value) > 0:
                    return int(value)
        raise ValueError('Citation total not found')
    except (requests.RequestException, ValueError) as exc:
        print(f'Citation fetch failed; keeping existing value: {exc}')
        return None

def fetch_org_stars(org_name):
    total = 0
    seen = set()
    page = 1
    try:
        while True:
            response = requests.get(f'{API}/orgs/{org_name}/repos',
                params={'type': 'public', 'per_page': 100, 'page': page},
                headers=github_headers(), timeout=30)
            response.raise_for_status()
            repos = response.json()
            if not isinstance(repos, list):
                raise ValueError('Invalid repository response')
            for repo in repos:
                if repo['id'] in seen:
                    continue
                seen.add(repo['id'])
                stars = repo['stargazers_count']
                if not isinstance(stars, int) or stars < 0:
                    raise ValueError('Invalid star count')
                total += stars
            if len(repos) < 100:
                if not seen:
                    raise ValueError('Empty organization repository list')
                return total
            page += 1
    except (requests.RequestException, ValueError, KeyError) as exc:
        print(f'Star fetch failed; keeping existing value: {exc}')
        return None

def update_content(content, citations, org_stars):
    original = content
    if citations is not None:
        content, matches = re.subn(
            r'>Google Scholar(?:\s*\([\d,]+ citations\))?</a>',
            f'>Google Scholar ({citations:,} citations)</a>', content)
        if matches != 1:
            raise ValueError(f'Expected one homepage Scholar link, found {matches}')
    if org_stars is not None:
        content, matches = re.subn(
            r'>Github \(Group(?:, [\d,]+ stars)?\)(?:, [\d,]+ stars)?</a>',
            f'>Github (Group, {org_stars:,} stars)</a>', content)
        if matches != 1:
            raise ValueError(f'Expected one group GitHub link, found {matches}')
    return content, content != original

def main():
    citations = fetch_citations()
    stars = fetch_org_stars(ORG_NAME)
    if citations is None and stars is None:
        print('Neither statistic could be verified; homepage left unchanged.')
        return 1
    url = f'{API}/repos/{REPO}/contents/index.html'
    response = requests.get(url, params={'ref': BRANCH}, headers=github_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    content = base64.b64decode(data['content']).decode('utf-8')
    updated, changed = update_content(content, citations, stars)
    if changed:
        response = requests.put(url, headers=github_headers(), json={
            'message': 'Refresh verified citation and organization star counts',
            'content': base64.b64encode(updated.encode('utf-8')).decode('ascii'),
            'sha': data['sha'], 'branch': BRANCH}, timeout=30)
        response.raise_for_status()
        print('Homepage statistics updated.')
    else:
        print('Homepage statistics are already current.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
