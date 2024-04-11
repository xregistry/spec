all: verify

verify: spellcheck tabcheck test_tools
	@python tools/verify.py .

spellcheck:
	@echo Spell-checking
	@# Words from: https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt
	@ sed "s/\([a-z0-9]\+\)/\n\1\n/gI" < core/spec.md | sort -iu | \
		grep "^[a-z]" | grep -v "[0-9]" > specwords
	@ sort -u tools/words tools/dict > words
	@ comm -23 specwords words > extra
	@ wc -l extra | grep "^0 extra" > /dev/null || \
		( echo "\nMISSPELLED:" ; cat extra ; exit 1 )
	@ rm specwords words extra

tabcheck:
	@echo Checking for tabs
	@if grep -P '\t' core/spec.md > /dev/null ; then \
	  echo "spec.md contains tabs" ; \
	  exit 1 ; \
	else \
	  exit 0 ; \
	fi
	@if grep "  *$$" core/spec.md > /dev/null ; then \
	  echo "spec.md contains lines with extra spaces at the end" ; \
	  exit 1 ; \
	else \
	  exit 0 ; \
	fi

deps:
	@echo Loading python deps
	@python -m pip install -qq -r tools/requirements.txt

schema:
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
	    make -f tools/Makefile verify
