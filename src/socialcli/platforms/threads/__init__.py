"""Threads platform adapter."""
from socialcli.platforms.threads.client import ThreadsPlatform
from socialcli.platforms import registry
_platform = ThreadsPlatform()
registry.register(_platform)
