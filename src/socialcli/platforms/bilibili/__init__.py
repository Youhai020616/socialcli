"""Bilibili (B站) platform adapter."""
from socialcli.platforms.bilibili.client import BilibiliPlatform
from socialcli.platforms import registry

_platform = BilibiliPlatform()
registry.register(_platform)
