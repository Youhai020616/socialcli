"""Reddit platform adapter."""
from socialcli.platforms.reddit.client import RedditPlatform
from socialcli.platforms import registry

_platform = RedditPlatform()
registry.register(_platform)
