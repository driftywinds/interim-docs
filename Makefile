.PHONY: serve build clean

PY ?= python

serve:
	$(PY) -m properdocs serve

build:
	$(PY) -m properdocs build --strict

clean:
	rm -rf site
