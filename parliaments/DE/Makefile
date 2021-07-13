MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
BASEDIR := $(dir $(MAKEFILE_PATH))

DATADIR := $(BASEDIR)/data/examples

MEDIA_SOURCE := $(wildcard $(DATADIR)/media/*.xml)
TRANSCRIPT_SOURCE := $(wildcard $(DATADIR)/proceedings/*.xml)

# MEDIA_DEST := $(patsubst %.xml,%.json,$(MEDIA_SOURCE))
TRANSCRIPT_DEST := $(patsubst %.xml,%.json,$(TRANSCRIPT_SOURCE))
NEWMEDIA_DEST := $(wildcard $(DATADIR)/nmedia/*-media.json)

MERGE_DEST := $(patsubst %-data.json,%-merged.json,$(TRANSCRIPT_DEST))

# all: ;echo $(MEDIA_SOURCE)
all: $(NEWMEDIA_DEST) $(TRANSCRIPT_DEST) $(MERGE_DEST)
	;echo $(MERGE_DEST)

download:
	$(BASEDIR)/scraper/fetch_proceedings.py $(DATADIR)/proceedings
	# Fetch media files corresponding to proceedings files
	$(BASEDIR)/scraper/update_media --from-proceedings $(DATADIR)/proceedings $(DATADIR)/nmedia --save-raw-data

update: download all

%-merged.json: %-data.json ../nmedia/%-media.json
	$(BASEDIR)/merger/merge_session.py --output=$(DATADIR)/merged $^

%-media.json: %-media.xml
	$(BASEDIR)/parsers/media2json.py $< > $@

%-data.json: %-data.xml
	$(BASEDIR)/parsers/proceedings2json.py $< > $@

clean:
	$(RM) $(DATADIR)/media/*.json
	$(RM) $(DATADIR)/proceedings/*.json
