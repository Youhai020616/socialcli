"""Weibo (微博) platform adapter."""
from socialcli.platforms.weibo.client import WeiboPlatform
from socialcli.platforms import registry

_platform = WeiboPlatform()
registry.register(_platform)
