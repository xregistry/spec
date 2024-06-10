<img src="https://github.com/cncf/artwork/raw/main/projects/xregistry/horizontal/color/xregistry-horizontal-color.svg" alt="xRegistry"></img><br>
<span style="font-size:3px">(<a href="https://github.com/cncf/artwork/tree/main/projects/xregistry">more logos</a>)</span>

<!-- no verify-specs -->

[![CLOMonitor](https://img.shields.io/endpoint?url=https://clomonitor.io/api/projects/cncf/cloudevents/badge)](https://clomonitor.io/projects/cncf/cloudevents)
[![OpenSSF Best Practices](https://bestpractices.coreinfrastructure.org/projects/7295/badge)](https://bestpractices.coreinfrastructure.org/projects/7295)

The xRegistry project (short for "extensible registry") defines an abstract
model for how to manage metadata about resources and provide a REST-based
interface for creating, modifying, deleting and discovering of those resources.
The project includes a "core" specification that defines the basic model and
APIs of a Registry and a set of domain specific specifications that extend that
core for particular use cases. By leveraging the same "core" model/APIs,
generic tooling and common patterns of Registry access can be developed which
help create an interoperable (and standard) interface.

It is expected that that further specifications will be developed, both as
part of the xRegistry project as well as outside of the project, that will
leverage this framework for additional purposes.

xRegistry was first developed under the [CloudEvents](https://cloudevents.io)
project, and in April 2023 it was split into its own project but continues
so share many organizational resources with the CloudEvents and CNCF Serverless
Working Group (such as the weekly meetings).

The name `xRegistry` is meant to be written with a lowercase `x`, even when
the first word in a sentence.

## xRegistry Documents

|                               |                                 Latest Release                                  |                                      Working Draft                                       |
| :---------------------------- | :-----------------------------------------------------------------------------: | :--------------------------------------------------------------------------------------: |
| **Core xRegistry Specification:**    |
| xRegistry                     | n/a | [WIP](core/spec.md) |
|                               |
| **Domain Specific Specifications:**  |
| Endpoint Registry             | n/a | [WIP](endpoint/spec.md)                         |
| Message Definitions Registry  | n/a | [WIP](message/spec.md)                         |
| Schema Registry               | n/a | [WIP](schema/spec.md)                         |
|                               |
| **Additional Documentation:** |
| xRegistry Primer              | n/a | [WIP](core/primer.md)                          |
| Pagination Specification      | n/a | [WIP](pagination/spec.md)                          |

Additional release related information:
  [Historical releases and changelogs](docs/RELEASES.md)

If you are new to the family of xRegistry specifications, it is recommended
that you start by reading the [xRegistry Primer](core/primer.md) for an
overview of the specification's goals and design decisions, and then move on
to the [core specification](core/spec.md).

## Community and Docs

Learn more about the people and organizations who are creating a dynamic cloud
native ecosystem by making our systems interoperable with xRegistry.

- Our [Governance](docs/GOVERNANCE.md) documentation.
- [Contributing](docs/CONTRIBUTING.md) guidance.
- [Roadmap](docs/ROADMAP.md)
- [Contributors](docs/contributors.md): people and organizations who helped
  us get started or are actively working on the xRegistry specifications.
- [Presentations, notes and other misc shared
  docs](https://drive.google.com/drive/folders/1DjeazDhtUsWP0mQIzu4XOzNxF2EiGNvN?usp=sharing)
- [Demos & open source](docs/README.md) -- if you have something to share
  about your use of xRegistry, please submit a PR!
- [Code of Conduct](https://github.com/cncf/foundation/blob/master/code-of-conduct.md)

### Security Concerns

If there is a security concern with one of the specifications in this
repository please [open an issue](https://github.com/xregistry/spec/issues).

### Communications

The main mailing list for e-mail communications:

- Send emails to: [cncf-xregistry](mailto:cncf-xregistry@lists.cncf.io)
- To subscribe see: https://lists.cncf.io/g/cncf-xregistry
- Archives are at: https://lists.cncf.io/g/cncf-xregistry/topics

And a #xregistry Slack channel under
[CNCF's Slack workspace](http://slack.cncf.io/).

### Meeting Time

See the [CNCF public events calendar](https://www.cncf.io/community/calendar/).
This specification is being developed by the
[CNCF Serverless Working Group](https://github.com/cncf/wg-serverless). This
working group meets every Thursday at 9AM PT (USA Pacific)
([World Time Zone Converter](http://www.thetimezoneconverter.com/?t=9:00%20am&tz=San%20Francisco&)):

Please see the
[meeting minutes doc](https://docs.google.com/document/d/1OVF68rpuPK5shIHILK9JOqlZBbfe91RNzQ7u_P7YCDE/edit#)
for the latest information on how to join the calls.

Recording from our calls are available
[here](https://www.youtube.com/playlist?list=PLO-qzjSpLN1BEyKjOVX_nMg7ziHXUYwec), and
older ones are
[here](https://www.youtube.com/playlist?list=PLj6h78yzYM2Ph7YoBIgsZNW_RGJvNlFOt).

Periodically, the group may have in-person meetings that coincide with a major
conference. Please see the
[meeting minutes doc](https://docs.google.com/document/d/1OVF68rpuPK5shIHILK9JOqlZBbfe91RNzQ7u_P7YCDE/edit#)
for any future plans.
