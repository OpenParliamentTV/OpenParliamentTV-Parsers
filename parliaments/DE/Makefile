MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
BASEDIR := $(dir $(MAKEFILE_PATH))

DATADIR := $(BASEDIR)data

TRANSCRIPT_SOURCE := $(wildcard $(DATADIR)/proceedings/*.xml)

# MEDIA_DEST := $(patsubst %.xml,%.json,$(MEDIA_SOURCE))
TRANSCRIPT_DEST := $(patsubst %.xml,%.json,$(TRANSCRIPT_SOURCE))
MEDIA_DEST := $(wildcard $(DATADIR)/media/*-media.json)

MERGE_DEST := $(subst /proceedings/,/merged/,$(patsubst %-data.xml,%-merged.json,$(TRANSCRIPT_SOURCE)))

all: $(MEDIA_DEST) $(TRANSCRIPT_DEST) $(MERGE_DEST)

download:
	$(BASEDIR)/scraper/fetch_proceedings.py $(DATADIR)/proceedings
	# Fetch media files from period
	$(BASEDIR)/scraper/update_media --from-period 19 $(DATADIR)/media --save-raw-data
	# Fetch media files corresponding to proceedings files
	# $(BASEDIR)/scraper/update_media --from-proceedings $(DATADIR)/proceedings $(DATADIR)/media --save-raw-data

update: download all

%-merged.json: ../proceedings/%-data.json ../media/%-media.json
	$(BASEDIR)/merger/merge_session.py --output=$(DATADIR)/merged $^

%-media.json: %-media.xml
	$(BASEDIR)/parsers/media2json.py $< > $@

%-data.json: %-data.xml
	$(BASEDIR)/parsers/proceedings2json.py $< > $@

clean:
	$(RM) $(DATADIR)/media/[0-9]*.json
	$(RM) $(DATADIR)/proceedings/*.json
	$(RM) $(DATADIR)/merged/*.json
