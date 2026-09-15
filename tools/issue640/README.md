# CloudEvents content layer checks

<!-- words: pytest py cacheprovider SDK serializer -->

`content_layers_640.py` is an offline admission model for payload, envelope,
and HTTP body media types. It compares only values that describe the same
layer and leaves unknown values unresolved instead of deriving them from a
schema language. `test_content_layers_640.py` reads the actual layer table and
structured XML body excerpt in the [Message specification](../../message/spec.md).
It also exercises JSON, XML, binary data, same-layer conflicts, and media type
comparison. Run from the repository root:

```shell
python -B -m pytest tools/issue640 -q -p no:cacheprovider
```

The helper supports explicit binary and structured modes only. It does not
select a mode, infer a schema's data encoding, acquire remote resources, or
implement a complete CloudEvents serializer or media type parser. The small
JSON/base64 exercises check representation boundaries, not live protocol
behavior. This is abstract/source evidence, not real server or SDK
interoperability.

The data/envelope distinction follows the CloudEvents
[data content type](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md#datacontenttype),
[HTTP binding](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/bindings/http-protocol-binding.md),
and [JSON event format](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/formats/json-format.md).
Inference policy and native metadata codecs are separate from these checks.
