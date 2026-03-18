"""Instagram platform adapter."""
from socialcli.platforms.instagram.client import InstagramPlatform
from socialcli.platforms import registry
_platform = InstagramPlatform()
registry.register(_platform)
