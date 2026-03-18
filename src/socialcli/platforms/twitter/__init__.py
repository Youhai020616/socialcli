"""Twitter/X platform adapter."""
from socialcli.platforms.twitter.client import TwitterPlatform
from socialcli.platforms import registry

_platform = TwitterPlatform()
registry.register(_platform)
