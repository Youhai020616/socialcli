"""
Platform base class — unified interface for all social platforms.

Every platform adapter must implement this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Content:
    """Unified content model for cross-platform publishing."""

    title: str = ""
    text: str = ""
    images: List[str] = field(default_factory=list)
    video: str = ""
    link: str = ""
    tags: List[str] = field(default_factory=list)
    visibility: str = "public"  # public / private / friends
    schedule_time: str = ""  # ISO 8601
    # Platform-specific extras (e.g. subreddit for Reddit, cover for Douyin)
    extras: dict = field(default_factory=dict)


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    platform: str
    post_id: str = ""
    url: str = ""
    error: str = ""


@dataclass
class SearchResult:
    """A single search result."""

    title: str = ""
    url: str = ""
    author: str = ""
    likes: int = 0
    comments: int = 0
    snippet: str = ""
    thumbnail: str = ""
    created_at: str = ""


@dataclass
class TrendingItem:
    """A trending topic or post."""

    rank: int = 0
    title: str = ""
    url: str = ""
    hot_value: str = ""
    category: str = ""


@dataclass
class AccountInfo:
    """Logged-in account information."""

    platform: str = ""
    account: str = "default"
    nickname: str = ""
    user_id: str = ""
    is_logged_in: bool = False


DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class Platform(ABC):
    """
    Abstract base for all platform adapters.

    Required: login, check_login, publish, search
    Optional: trending, like, comment, follow, download, analytics

    Subclasses can override `default_ua` and `base_referer` to customize
    the default headers built by `_get_headers()`.
    """

    name: str = ""
    display_name: str = ""
    icon: str = ""
    default_ua: str = DEFAULT_UA
    base_referer: str = ""

    # --- Common helpers ---

    def _get_headers(self, account: str = "default") -> dict:
        """Build HTTP headers with UA, optional cookie, optional referer.

        Subclasses that need extra headers (CSRF tokens, etc.) should
        override this and call ``super()._get_headers(account)`` first.
        """
        from socialcli.auth.cookie_store import cookie_string

        headers: dict[str, str] = {"User-Agent": self.default_ua}
        cookie = cookie_string(self.name, account)
        if cookie:
            headers["Cookie"] = cookie
        if self.base_referer:
            headers["Referer"] = self.base_referer
        return headers

    def me(self, account: str = "default") -> AccountInfo:
        """Get logged-in user info from stored account data."""
        from socialcli.auth.cookie_store import load_account_info

        info = load_account_info(self.name, account)
        if not info:
            return AccountInfo(platform=self.name, account=account, is_logged_in=False)
        return AccountInfo(
            platform=self.name,
            account=account,
            nickname=info.get("nickname", ""),
            user_id=info.get("user_id", ""),
            is_logged_in=True,
        )

    # --- Required methods ---

    @abstractmethod
    def login(self, account: str = "default", **kwargs) -> bool:
        """Login to platform (opens browser for QR scan or password)."""
        ...

    @abstractmethod
    def check_login(self, account: str = "default") -> bool:
        """Check if currently logged in (validate stored cookie)."""
        ...

    @abstractmethod
    def publish(self, content: Content, account: str = "default") -> PublishResult:
        """Publish content to this platform."""
        ...

    @abstractmethod
    def search(self, query: str, account: str = "default", **kwargs) -> List[SearchResult]:
        """Search for content."""
        ...

    # --- Optional methods ---

    def trending(self, account: str = "default", **kwargs) -> List[TrendingItem]:
        """Get trending topics / hot list."""
        raise NotImplementedError(f"{self.display_name} does not support trending")

    def like(self, target_id: str, account: str = "default", **kwargs) -> bool:
        """Like a post."""
        raise NotImplementedError(f"{self.display_name} does not support like")

    def comment(self, target_id: str, text: str, account: str = "default", **kwargs) -> bool:
        """Comment on a post."""
        raise NotImplementedError(f"{self.display_name} does not support comment")

    def follow(self, user_id: str, account: str = "default", **kwargs) -> bool:
        """Follow a user."""
        raise NotImplementedError(f"{self.display_name} does not support follow")

    def download(self, url: str, output: str = "", **kwargs) -> str:
        """Download content (video/image)."""
        raise NotImplementedError(f"{self.display_name} does not support download")

    def analytics(self, account: str = "default", **kwargs) -> dict:
        """Get analytics/dashboard data."""
        raise NotImplementedError(f"{self.display_name} does not support analytics")
