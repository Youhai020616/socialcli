"""Kuaishou (快手) platform adapter."""
from socialcli.platforms.kuaishou.client import KuaishouPlatform
from socialcli.platforms import registry

_platform = KuaishouPlatform()
registry.register(_platform)
