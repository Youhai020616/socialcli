"""Douyin (抖音) platform adapter."""
from socialcli.platforms.douyin.client import DouyinPlatform
from socialcli.platforms import registry

# Register on import
_platform = DouyinPlatform()
registry.register(_platform)
