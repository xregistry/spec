# Endpoint Registry Service - Version 1.0-rc4

<!-- no verify-specs -->
<!-- words: hostnames py pytest -->

## Declaration checks

[Kafka bootstrap checks](kafka_bootstrap.py) illustrate the resolved client
address contract in the [Endpoint specification](spec.md#kafka-options).
They check nonempty string arrays, host/port syntax, bracketed IPv6 literals
and the numeric port range. They do not resolve hostnames, acquire endpoints,
configure credentials, connect to brokers or qualify a Kafka client library.

Placeholder resolution happens outside the checker. Authoring declarations
retain their original strings; pass the resolved strings to the checker only
when a client is ready to interpret the metadata. A listener URL is rejected,
not converted into a client address or a security configuration. Security
configuration remains a separate declaration.

The [focused regressions](../tools/test_issue_625_kafka_bootstrap.py) exercise
the real Contoso sample, the specification's address example, and generated
Endpoint and CloudEvents schemas. Run them from the repository root:

```console
python -B -m pytest tools/test_issue_625_kafka_bootstrap.py -q
```
