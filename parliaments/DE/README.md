# Scraper/parser architecture

The `scraper` package holds modules/scripts aimed at scraping data
from websites.

The `parser` package holds modules/scripts that extract information
from the scraped files, and converts them into a unified JSON format.

The `merger` package holds modules/scripts for merging information
from transformed files.

# Environment setup

Some modules have external dependencies (for RSS parsing, sentence
splitting...). The command `python3 -m pip install -r
parsers/requirements.txt` will install the necessary requirements.

# Scraping data

For operational reference, see the `download` target of the Makefile.
Running `make download` will execute the 2 steps involved.

There are for the moment 2 data sources: proceedings and media.

Proceedings are fetched by the `scraper/fetch_proceedings.py` script,
into the `data/examples/proceedings` directory.

Media data can be fetched by the `scraper/fetch_media.py` script, by
providing period and meeting numbers - it will handle feed
pagination. This script is used by the `update_media` script, which
will use the `proceedings` directory content to determine the
appropriate period and meeting numbers, and download the corresponding
media data, directly in json format.

The Bundestag media server regularly has trouble downloading specified
period/meeting data (it looks like some kind of timeout in building
data). The `update_media` script will by default only try to download
files that are not already existing. It can thus be necessary to run
it multiple times, in order to go over the 503 errors from the
webserver.
