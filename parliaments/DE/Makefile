MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
BASEDIR := $(dir $(MAKEFILE_PATH))

DATADIR := $(BASEDIR)/data/examples

MEDIA_SOURCE := $(wildcard $(DATADIR)/media/*.xml)
TRANSCRIPT_SOURCE := $(wildcard $(DATADIR)/proceedings/*.xml)

# MEDIA_DEST := $(patsubst %.xml,%.json,$(MEDIA_SOURCE))
TRANSCRIPT_DEST := $(patsubst %.xml,%.json,$(TRANSCRIPT_SOURCE))
NEWMEDIA_DEST := $(patsubst data.json,media.json,$(TRANSCRIPT_DEST))

# all: ;echo $(MEDIA_SOURCE)
all: $(MEDIA_DEST) $(TRANSCRIPT_DEST)

download:
	$(BASEDIR)/scraper/fetch_proceedings.py $(DATADIR)/proceedings
	# Fetch media files corresponding to proceedings files
	$(BASEDIR)/scraper/update_media $(DATADIR)/proceedings $(DATADIR)/nmedia

update: download all

%-media.json: %-media.xml
	$(BASEDIR)/parsers/media2json.py $< > $@

%-data.json: %-data.xml
	$(BASEDIR)/parsers/proceedings2json.py $< > $@

clean:
	$(RM) $(DATADIR)/media/*.json
	$(RM) $(DATADIR)/proceedings/*.json
