# Contributing to xRegistry

<!-- no verify-specs -->
<!-- words: configs conventionalcommits dco developercertificate feb readme -->

This page explains how to report issues, propose changes and format documents.

## Table of Contents

- [Contributing to xRegistry](#contributing-to-xregistry)
  - [Table of Contents](#table-of-contents)
  - [Reporting an Issue](#reporting-an-issue)
  - [Suggesting a Change](#suggesting-a-change)
    - [Assigning and Owning work](#assigning-and-owning-work)
    - [Sign your work](#sign-your-work)
  - [Spec Formatting Conventions](#spec-formatting-conventions)

## Reporting an Issue

If you have an idea but have not had time to write it up, open an
[issue](https://github.com/xregistry/spec/issues). First check the existing
[issues](https://github.com/xregistry/spec/issues) for a similar discussion.

## Suggesting a Change

To propose a change, open a
[pull request](https://github.com/xregistry/spec/pulls) with the complete
changes. Follow the
[Spec Formatting Conventions](#spec-formatting-conventions).

Please use [conventional commits](https://conventionalcommits.org) when writing
commit messages.

Sign each pull request as described in the Sign your work section.

### Assigning and Owning work

To take responsibility for an issue, comment on it with “#dibs” and ask to own
the work. A maintainer will then add the Assigned label and add
`Assigned to: @person` to the issue's first comment.

### Sign your work

The sign-off is a simple line at the end of the explanation for the patch. Your
signature certifies that you wrote the patch or otherwise have the right to pass
it on as an open-source patch. If you can certify the following, add this line
to every commit message (see
[developercertificate.org](http://developercertificate.org/)):

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
1 Letterman Drive
Suite D4700
San Francisco, CA, 94129

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

    Signed-off-by: Joe Smith <joe.smith@email.com>

Use your real name (sorry, no pseudonyms or anonymous contributions.)

If you set your `user.name` and `user.email` git configs, you can sign your
commit automatically with `git commit -s`.

When `user.name` and `user.email` are configured, `git log` shows the author and
sign-off:

```
Author: Joe Smith <joe.smith@email.com>
Date:   Thu Feb 2 11:41:15 2018 -0800

    Update README

    Signed-off-by: Joe Smith <joe.smith@email.com>
```

In the example above, the `Author` and `Signed-off-by` lines match. If they do
not, the automated DCO check rejects the pull request.

## Spec Formatting Conventions

Documents in this repository will adhere to the following rules:

- Wrap lines at 80 columns when practical.
- Use [RFC 2119](https://tools.ietf.org/html/rfc2119)
  keywords to indicate normative requirements.

## Testing Changes Locally

CI checks each pull request for:

- Working links.
- No spelling errors.
- No tabs in Markdown files.
- Uppercase RFC 2119 keywords.

Run the same checks locally with either:

- Python and Bash: `make -f tools/Makefile`
- Docker: `make -f tools/Makefile docker`

If a link requires authentication, mark its HTML anchor with
`data-link-check="authenticated"` and explain the access restriction in the
document. Verify the exact target with authorized access first. Both link
checkers report the marked URL without probing it anonymously. They still check
all other links, local paths and fragments on marked anchors. Do not disable
link checking for the whole document.
