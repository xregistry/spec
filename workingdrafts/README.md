# Working Drafts

<!-- words: opc opcua readme ua -->
<!-- words: namespace validators -->

The specifications in this directory are under active development and can
change independently of released xRegistry specifications. They are included
for discussion and review and are not part of a released xRegistry
specification.

## Federation Specification Family

The federation drafts define read-only resolution across independently
administered Registries. Start with the domain and shared contract, then
select a transport binding.

For a first reading, use the domain specification to understand catalog
entries, then the federation specification to understand hosting and source
selection. The comparison below helps choose a binding. Each binding's
reference sections contain the detailed implementation rules.

| Specification | Scope |
| --- | --- |
| [Registry of Registries](models/registry/spec.md) | Hub-compatible catalog model, advertisements and relationships. |
| [Federation](federation/spec.md) | Registry contexts, selection, references, representations and conformance. |
| [Directory mapping](bindings/mapping.md) | Map existing directory contents to a Registry through Git or File. |
| [OCI](bindings/oci.md) | Bounded descriptor graphs, publication and native snapshot resolution. |
| [HTTP federation](bindings/http-federation.md) | Federation using the existing xRegistry HTTP API. |
| [Git](bindings/git.md) | Commit-pinned document-tree access. |
| [File](bindings/file.md) | Local document-tree and OCI-layout access. |
| [OPC UA](bindings/opcua.md) | Native OPC UA API and federation integration. |

### Choosing a Binding

| Binding | Service and storage preparation | Revision and consistency | Implementation prerequisites |
| --- | --- | --- | --- |
| HTTP | An existing xRegistry HTTP endpoint. No new storage format is needed. | Reads usually observe live state. Per-response validators do not provide a Registry-wide snapshot. | Core HTTP requests, pagination and authentication. |
| OCI | An OCI artifact service, or a local layout. Package the Registry as the specified descriptor graph. | Resolve a tag once and retain the root digest. Descendant digests identify the selected bytes. | An artifact client supporting nested indexes, the format's roles and digest checks. A container runtime alone is insufficient. |
| Git | A repository containing a directory mapping. Remote acquisition uses HTTPS. | Resolve a ref or annotated tag once and retain the commit. Read Git objects rather than checkout files. | Git object access and the directory mapping reader. |
| File | No xRegistry service. Use local storage or an OS-mounted file share containing a directory mapping or OCI layout. | Root hashes and descriptors detect inconsistent content. A mutable directory is not automatically an immutable snapshot. | Filesystem access, containment checks and the reader for the chosen format. |
| OPC UA | An OPC UA server exposing the Registry nodes and document access described by the binding. | Reads usually observe live state. Session handles and per-node timestamps are not snapshot identifiers. | OPC UA Services, Registry-root selection and namespace remapping. Check the binding's explicit domain-mapping and companion-draft dependencies. |

These choices describe access to a source Registry. A consumer-facing API
server can use a different binding to read that source. For example, it can
serve HTTP clients from a local File mapping or an OCI snapshot.

The [resolution-owner capability](federation/spec.md#signaling-who-performs-resolution)
distinguishes views combined by their producer from views that consumers
combine themselves. The default is `consumer`. With `producer`, the consumer
reads the supplied view without repeating its catalog traversal.

The [Registry model artifacts](models/registry/README.md) and
[conformance examples](federation/samples/README.md) accompany these drafts.
Core `xref` remains a same-Registry, same-Resource-model-type mechanism.
Federation does not redefine it as a remote URL.
