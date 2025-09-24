all: docker
	@git diff --name-status --exit-code */schemas > /dev/null 2>&1 || \
		( echo "schema files have been updated, make sure you commit them" ; \
		  exit 1 )

verify: spellcheck tabcheck errorcheck samplescheck links

spellcheck:
	tools/spellcheck */README.md */spec.md core/*.md \
		docs/share/README.md */samples/README.md */samples/*/README.md
	@echo

tabcheck:
	tools/tabcheck `find . -name "*.md" -o -name "*.json"`
	@echo

errorcheck:
	tools/errorcheck core/spec.md core/model.md core/http.md
	@echo

samplescheck:
	tools/samplescheck */model.json */samples/*json */samples/*/*json
	@echo

links: test_tools
	@python tools/verify.py .
	@echo

models:
	@# Note this will use a local 'xr' if available so that local build/test
	@# of 'xr' can be done
	(which xr && xr model verify */model.json -v) || \
	(docker run -v $$PWD:/xreg -w /xreg --entrypoint /bin/sh \
		ghcr.io/xregistry/xr -c "/xr model verify */model.json -v")
	@echo

makeschema:
	@echo Rebuilding the schemas...
	@python tools/schema-generator.py --type json-schema --schema-id https://xregistry.io/xreg/xregistryspecs/schema-v1/schemas/document-schema.json --output schema/schemas/document-schema.json schema/model.json
	@python tools/schema-generator.py --type avro-schema --output schema/schemas/document-schema.avsc schema/model.json
	@python tools/schema-generator.py --type openapi --output schema/schemas/openapi.json schema/model.json
	@python tools/schema-generator.py --type json-schema --schema-id https://xregistry.io/xreg/xregistryspecs/message-v1/schemas/document-schema.json --output message/schemas/document-schema.json message/model.json
	@python tools/schema-generator.py --type avro-schema --output message/schemas/document-schema.avsc message/model.json
	@python tools/schema-generator.py --type openapi --output message/schemas/openapi.json message/model.json
	@python tools/schema-generator.py --type json-schema --schema-id https://xregistry.io/xreg/xregistryspecs/endpoint-v1/schemas/document-schema.json --output endpoint/schemas/document-schema.json endpoint/model.json
	@python tools/schema-generator.py --type avro-schema --output endpoint/schemas/document-schema.avsc endpoint/model.json
	@python tools/schema-generator.py --type openapi --output endpoint/schemas/openapi.json endpoint/model.json
	@python tools/schema-generator.py --type json-schema --schema-id https://xregistry.io/xreg/xregistryspecs/cloudevents-v1/schemas/document-schema.json --output cloudevents/schemas/document-schema.json endpoint/model.json message/model.json schema/model.json
	@python tools/schema-generator.py --type avro-schema --output cloudevents/schemas/document-schema.avsc endpoint/model.json message/model.json schema/model.json
	@python tools/schema-generator.py --type openapi --output cloudevents/schemas/openapi.json endpoint/model.json message/model.json schema/model.json

deps:
	@echo Loading python deps
	@python -m pip install -qq -r tools/requirements.txt

test_tools: deps
	@pytest tools/

docker: models
	@docker run -ti -v $(PWD):/tmp/spec -w /tmp/spec python:3.11 \
	    make -f tools/Makefile verify makeschema
