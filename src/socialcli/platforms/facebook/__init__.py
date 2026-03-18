"""Facebook platform adapter."""
from socialcli.platforms.facebook.client import FacebookPlatform
from socialcli.platforms import registry
_platform = FacebookPlatform()
registry.register(_platform)
