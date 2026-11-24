# Federation Example Source

<!-- words: opc py ua -->

The federation and binding examples share the Registry content in
[`examples.json`](examples.json). The
[generator](../tools/generate_examples.py) produces File, Git and OCI
representations from that source. The
[HTTP](../../bindings/tools/test_http_examples.py) and
[OPC UA](../../bindings/tools/test_opcua_examples.py) binding tests supply
synthetic protocol exchanges and expected outcomes. The generator does not
start servers for those bindings.

See the [federation specification](../spec.md) and the
[example generation instructions](../../README.md#generating-and-reading-examples).
