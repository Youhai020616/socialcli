"""LinkedIn platform adapter."""
from socialcli.platforms.linkedin.client import LinkedinPlatform
from socialcli.platforms import registry

_platform = LinkedinPlatform()
registry.register(_platform)
