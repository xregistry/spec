all: verify

verify: spellcheck tabcheck test_tools
	@python tools/verify.py .

spellcheck:
	tools/spellcheck core/spec.md core/primer.md

tabcheck:
	tools/tabcheck core/spec.md core/primer.md

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
	    make -f tools/Makefile verify makeschema
	@git diff
	@git diff-index HEAD || \
		( echo "schema files need to be updated: make 'makeschema'" ; exit 1 )
