"""TikTok platform adapter."""
from socialcli.platforms.tiktok.client import TiktokPlatform
from socialcli.platforms import registry

_platform = TiktokPlatform()
registry.register(_platform)
