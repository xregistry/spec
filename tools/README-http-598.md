# Group POST example checks

<!-- no spellcheck -->
<!-- no verify specs -->

`test_http_group_post_598.py` reads the actual Group POST request and response
from `core/http.md`, each containing both Message and Schema Resources. The
pinned source has one concrete request/response pair in this section. Both
blocks need the two Resource-ID map layers.

The parser removes only the two explicitly designated omitted-field lines
and their introducing commas in each block. All remaining punctuation is
parsed as JSON. Checks compare collection names, map keys and visible body IDs,
and the child-only response with its request. Mutations of these source bodies
cover multiple IDs, collapsed scalar values, mismatched IDs and Group attributes.

Run from the repository root:

```console
python -B -m pytest tools/test_http_group_post_598.py -q -p no:cacheprovider
```

The small checker validates these partial example shapes, not the full protocol.
It does not fill in omitted metadata, run an HTTP server, or establish
interoperability or runtime update behavior.
