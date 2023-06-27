#!/bin/bash

../core/schemas/generate_openapi.sh
../schema/schemas/generate_openapi.sh
../endpoint/schemas/generate_openapi.sh
../message/schemas/generate_openapi.sh