"""Check resolved Kafka client bootstrap declarations without network access."""

import ipaddress
import re


_HOST_PORT = re.compile(r"([^\s:/?#@\[\]{}]+):([0-9]+)\Z")
_IPV6_PORT = re.compile(r"\[([^\[\]{}]+)\]:([0-9]+)\Z")


def validate_bootstrap_servers(servers):
    """Return resolved host/port pairs; reject noncanonical client addresses."""
    if not isinstance(servers, list) or not servers:
        raise ValueError("bootstrap.servers must be a nonempty array")

    addresses = []
    for server in servers:
        if not isinstance(server, str):
            raise ValueError("bootstrap.servers entries must be strings")
        match = (_IPV6_PORT if server.startswith("[") else _HOST_PORT).fullmatch(
            server
        )
        if match is None:
            raise ValueError("a resolved bootstrap address must use host:port")
        host, port_text = match.groups()
        if server.startswith("["):
            ipaddress.IPv6Address(host)
        port = int(port_text)
        if port > 65535:
            raise ValueError("bootstrap port must fit an unsigned 16-bit value")
        addresses.append((host, port))
    return addresses
