#!/bin/bash

$(dirname "$0")/../../core/schemas/generate_openapi.sh
$(dirname "$0")/../../schema/schemas/generate_openapi.sh
$(dirname "$0")/../../endpoint/schemas/generate_openapi.sh
$(dirname "$0")/../../message/schemas/generate_openapi.sh