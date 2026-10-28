# Federation Example Source

[`examples.json`](examples.json) holds the shared Registry content for the
federation and binding examples. The
[generator](../tools/generate_examples.py) reads it to produce File, Git and
OCI representations. It does not start HTTP or OPC UA servers; those
observations remain in the binding tests.

See the [federation specification](../spec.md) and the
[example generation instructions](../../README.md#generating-and-reading-examples).
