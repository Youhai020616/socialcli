"""YouTube platform adapter."""
from socialcli.platforms.youtube.client import YoutubePlatform
from socialcli.platforms import registry
_platform = YoutubePlatform()
registry.register(_platform)
