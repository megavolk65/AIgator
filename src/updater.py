"""
Проверка обновлений через GitHub Releases API
"""

import requests
from typing import Optional, Tuple
from packaging import version

from version import __version__, GITHUB_API_RELEASES, GITHUB_RELEASES_URL


def check_for_updates() -> Optional[Tuple[str, str]]:
    """
    Проверить наличие обновлений на GitHub.
    
    Returns:
        (new_version, release_url) если есть обновление, иначе None
    """
    try:
        response = requests.get(
            GITHUB_API_RELEASES,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=5
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        latest_tag = data.get("tag_name", "")
        
        # Убираем 'v' из тега если есть (v1.0.0 -> 1.0.0)
        latest_version = latest_tag.lstrip("v")
        
        # Сравниваем версии
        if latest_version and version.parse(latest_version) > version.parse(__version__):
            release_url = data.get("html_url", GITHUB_RELEASES_URL)
            return (latest_version, release_url)
        
        return None
        
    except Exception:
        return None


def get_current_version() -> str:
    """Получить текущую версию"""
    return __version__


def get_releases_url() -> str:
    """Получить URL страницы релизов"""
    return GITHUB_RELEASES_URL
