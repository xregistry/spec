#!/bin/bash

# Variables for file names
input_file="$(dirname "$0")/../../core/schemas/xregistry_openapi_template.json"
output_file="$(dirname "$0")/xregistry_openapi_generic.json"
model_file="$(dirname "$0")/xregistry_generic_model.json"


# Variables for replacement values
# BEGIN: 8f7a2d7d3c4a
group_plural=$(jq -r '.groups[0].plural' "$model_file")
resource_plural=$(jq -r '.groups[0].resources[0].plural' "$model_file")
resource_type_ref=$(jq -r '.groups[0].resources[0].schema' "$model_file")
resource_version_type_ref=$(jq -r '.groups[0].resources[0].versionSchema' "$model_file")
group_type_ref=$(jq -r '.groups[0].schema' "$model_file")
document_type_ref=$(jq -r '.schema' "$model_file")

# END: 8f7a2d7d3c4a

# Escape the variable values
group_plural=$(echo "$group_plural" | sed 's/\//\\\//g')
resource_plural=$(echo "$resource_plural" | sed 's/\//\\\//g')
resource_type_ref=$(echo "$resource_type_ref" | sed 's/\//\\\//g')
resource_version_type_ref=$(echo "$resource_version_type_ref" | sed 's/\//\\\//g')
group_type_ref=$(echo "$group_type_ref" | sed 's/\//\\\//g')
document_type_ref=$(echo "$document_type_ref" | sed 's/\//\\\//g')

# Perform the replacements using sed
sed -e "s/{%-groupNamePlural-%}/$group_plural/g" \
    -e "s/{%-resourceNamePlural-%}/$resource_plural/g" \
    -e "s/{%-resourceTypeReference-%}/$resource_type_ref/g" \
    -e "s/{%-resourceVersionTypeReference-%}/$resource_version_type_ref/g" \
    -e "s/{%-groupTypeReference-%}/$group_type_ref/g" \
    -e "s/{%-documentTypeReference-%}/$document_type_ref/g" \
    "$input_file" > "$output_file"

