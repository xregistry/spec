# Federation Example Source

<!-- words: opc py ua -->

The federation and binding examples share the Registry content in
[`examples.json`](examples.json). The
[generator](../tools/generate_examples.py) produces File, Git and OCI
representations from that source. HTTP and OPC UA observations remain in
the binding tests; the generator does not start servers for those bindings.

See the [federation specification](../spec.md) and the
[example generation instructions](../../README.md#generating-and-reading-examples).
