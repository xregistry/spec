all: verify makeschema
	@git diff --name-status --exit-code */schemas > /dev/null 2>&1 || \
		( echo "schema files have been updated, make sure you commit them" ; \
		  exit 1 )

verify: spellcheck tabcheck test_tools
	@python tools/verify.py .
	@echo

spellcheck:
	tools/spellcheck */spec.md core/primer.md
	@echo

tabcheck:
	tools/tabcheck */*.md  */*.json
	@echo

deps:
	@echo Loading python deps
	@python -m pip install -qq -r tools/requirements.txt

makeschema:
	@echo Rebuilding the schemas...
	@python tools/schema-generator.py --type json-schema --output schema/schemas/document-schema.json schema/model.json
	@python tools/schema-generator.py --type avro-schema --output schema/schemas/document-schema.avsc schema/model.json
	@python tools/schema-generator.py --type openapi --output schema/schemas/openapi.json schema/model.json
	@python tools/schema-generator.py --type json-schema --output message/schemas/document-schema.json message/model.json
	@python tools/schema-generator.py --type avro-schema --output message/schemas/document-schema.avsc message/model.json
	@python tools/schema-generator.py --type openapi --output message/schemas/openapi.json message/model.json
	@python tools/schema-generator.py --type json-schema --output endpoint/schemas/document-schema.json endpoint/model.json
	@python tools/schema-generator.py --type avro-schema --output endpoint/schemas/document-schema.avsc endpoint/model.json
	@python tools/schema-generator.py --type openapi --output message/schemas/openapi.json message/model.json
	@python tools/schema-generator.py --type json-schema --output cloudevents/schemas/document-schema.json endpoint/model.json message/model.json schema/model.json
	@python tools/schema-generator.py --type avro-schema --output cloudevents/schemas/document-schema.avsc endpoint/model.json message/model.json schema/model.json
	@python tools/schema-generator.py --type openapi --output cloudevents/schemas/openapi.json endpoint/model.json message/model.json schema/model.json

test_tools: deps
	@pytest tools/

docker:
	@docker run -ti -v $(PWD):/tmp/spec -w /tmp/spec python:3.11 \
	    make -f tools/Makefile
