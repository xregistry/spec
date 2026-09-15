"""Validate the domain constraints that Core's usage string array cannot express."""


_ROLES = frozenset({"subscriber", "consumer", "producer"})
_COMBINED_PROTOCOLS = frozenset({"AMQP/1.0", "MQTT/3.1.1", "MQTT/5.0", "NATS"})


def validate_usage(endpoint):
    if not isinstance(endpoint, dict):
        raise ValueError("an Endpoint declaration must be an object")
    if "usage" not in endpoint:
        raise ValueError("Endpoint usage is required")
    usage = endpoint["usage"]
    if not isinstance(usage, list) or not usage:
        raise ValueError("Endpoint usage must be a nonempty array")
    if any(not isinstance(role, str) or role not in _ROLES for role in usage):
        raise ValueError("Endpoint usage must contain only defined role strings")
    roles = set(usage)
    if len(roles) != len(usage):
        raise ValueError("Endpoint usage must not repeat a role")
    if len(roles) == 1:
        return
    if roles != {"subscriber", "consumer"}:
        raise ValueError("producer must not be combined with other roles")
    protocol = endpoint.get("protocol")
    if not isinstance(protocol, str) or protocol not in _COMBINED_PROTOCOLS:
        raise ValueError("the protocol does not permit combined subscriber and consumer")
