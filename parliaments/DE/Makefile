MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
BASEDIR := $(dir $(MAKEFILE_PATH))

DATADIR := $(BASEDIR)data

TRANSCRIPT_SOURCE := $(wildcard $(DATADIR)/proceedings/*.xml)
# MEDIA_SOURCE filelist will be updated by download
MEDIA_SOURCE := $(wildcard $(DATADIR)/media/raw-*-media.json)

TRANSCRIPT_DEST := $(patsubst %.xml,%.json,$(TRANSCRIPT_SOURCE))
# MEDIA_DEST filelist is build using MEDIA_SOURCE
MEDIA_DEST := $(subst raw-,,$(MEDIA_SOURCE))

# The following line requires that each media file has a corresponding proceedings file
#MERGE_DEST := $(subst /media/,/merged/,$(patsubst %-data.json,%-merged.json,$(MEDIA_DEST)))

# The following line uses proceedings as reference
MERGE_DEST := $(subst /proceedings/,/merged/,$(patsubst %-data.json,%-merged.json,$(TRANSCRIPT_DEST)))

all: $(MEDIA_DEST) $(TRANSCRIPT_DEST) $(MERGE_DEST)

download:
	$(BASEDIR)/scraper/fetch_proceedings.py $(DATADIR)/proceedings
	# Fetch media files from period
	$(BASEDIR)/scraper/update_media --from-period 20 $(DATADIR)/media --save-raw-data
	# Fetch media files corresponding to proceedings files
	# $(BASEDIR)/scraper/update_media --from-proceedings $(DATADIR)/proceedings $(DATADIR)/media --save-raw-data

forcemerge:
	$(BASEDIR)/merger/merge_session.py --include-all-proceedings --second-stage-matching --advanced-rematch --output=$(DATADIR)/merged $(DATADIR)/proceedings $(DATADIR)/media

update: download all

debug:
	-echo "MEDIA_DEST"
	-echo $(MEDIA_DEST)
	-echo "MERGE DEST"
	-echo $(MERGE_DEST)

%-merged.json: ../proceedings/%-data.json ../media/%-media.json
	$(BASEDIR)/merger/merge_session.py --output=$(DATADIR)/merged $^

%-media.json: %-media.xml
	$(BASEDIR)/parsers/media2json.py $< > $@

%-media.json: raw-%-media.json
	$(BASEDIR)/parsers/media2json.py $< > $@

%-data.json: %-data.xml
	$(BASEDIR)/parsers/proceedings2json.py --include-nas $< > $@

clean:
	$(RM) $(DATADIR)/media/[0-9]*.json
	$(RM) $(DATADIR)/proceedings/*.json
	$(RM) $(DATADIR)/merged/*.json
