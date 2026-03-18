"""Xiaohongshu (小红书) platform adapter."""
from socialcli.platforms.xiaohongshu.client import XiaohongshuPlatform
from socialcli.platforms import registry

_platform = XiaohongshuPlatform()
registry.register(_platform)
