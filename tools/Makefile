all: models docker
	@git diff --name-status --exit-code */schemas > /dev/null 2>&1 || \
		( echo "schema files have been updated, make sure you commit them" ; \
		  exit 1 )

verify: spellcheck ticks badhrefs tabcheck errorcheck samplescheck \
	testpython links website

spellcheck:
	@echo "Checking for spelling mistakes"
	tools/spellcheck */README.md */spec.md core/*.md \
		docs/share/README.md */samples/README.md */samples/*/README.md
	@echo

tabcheck:
	@echo "Checking for tabs and extra spaces"
	tools/tabcheck `find . -name "*.md" -o -name "*.json"`
	@echo

ticks:
	@echo "Checking for uneven back-ticks"
	@(! grep '^[^`]*`[^`]*$$' core/*.md)
	@echo

badhrefs:
	@echo "Checking for hrefs that have /#"
	@(! grep -e '/#' -r --include="*.md")
	@echo

errorcheck:
	@echo "Look for unused errors in the specs"
	tools/errorcheck core/spec.md core/model.md core/http.md
	@echo

samplescheck:
	@echo "Check for too verbose samples"
	tools/samplescheck */model.json */samples/*json */samples/*/*json
	@echo

loadpython:
	@echo Loading python deps
	@python -m pip install -qq -r tools/requirements.txt

testpython: loadpython
	@echo Testing our python tools
	@pytest tools/

links: loadpython
	@echo Verifying links in our docs
	@python tools/verify.py .
	@echo

models:
	@echo "Verifying the models are valid"
	@# Note this will use a local 'xr' if available so that local build/test
	@# of 'xr' can be done
	if which xr ; then \
	  echo Using local xr ; \
	  xr model verify */model.json -v ; \
	else \
	  echo Using docker ghcr.io/xregistry/xr ; \
	  docker run -t -v $$PWD:/xreg -w /xreg --entrypoint /bin/sh \
		ghcr.io/xregistry/xr -c "/xr model verify */model.json -v" ; \
	fi
	@echo

website:
	@echo If available, verify the website generation code works too
	@if test -f `pwd -P`/../xregistry.github.io/tools/buildsite ; then \
	  XR_SPEC=`pwd -P` `pwd -P`/../xregistry.github.io/tools/buildsite && \
	    rm -rf xreg ; \
	else \
	  echo "> Website dir (../xregistry.github.io) can't be found" ; \
	fi
	@echo

makeschema: loadpython
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

docker:
	@docker run -t -v $(PWD):/tmp/spec -w /tmp/spec python:3.11 \
	    make -f tools/Makefile verify makeschema
