# Working Drafts

<!-- words: opc opcua readme ua -->

The specifications in this directory are under active development and can
change independently of released xRegistry specifications. They are included
for discussion and review and are not part of a released xRegistry
specification.

## Federation Specification Family

The federation drafts define read-only resolution across independently
administered Registries. Start with the domain and shared contract, then
select a transport binding.

| Specification | Scope |
| --- | --- |
| [Registry of Registries](models/registry/spec.md) | Hub-compatible catalog model, advertisements and relationships. |
| [Federation](federation/spec.md) | Registry contexts, selection, references, representations and conformance. |
| [Document-tree format](bindings/document-format.md) | Portable records shared by Git and File. |
| [OCI](bindings/oci.md) | Bounded descriptor graphs, publication and native snapshot resolution. |
| [HTTP federation](bindings/http-federation.md) | Federation using the existing xRegistry HTTP API. |
| [Git](bindings/git.md) | Commit-pinned document-tree access. |
| [File](bindings/file.md) | Local document-tree and OCI-layout access. |
| [OPC UA](bindings/opcua.md) | Native OPC UA API and federation integration. |

The [Registry model artifacts](models/registry/README.md) and
[conformance examples](federation/samples/README.md) accompany these drafts.
Core `xref` remains a same-Registry, same-Resource-model-type mechanism.
Federation does not redefine it as a remote URL.
