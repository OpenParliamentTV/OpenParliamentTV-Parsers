# Parsers for Bundestag data

## Requirements

The rss2json script depends on the feedparser module. Install it first with

  python3 -m pip install -r requirements.txt

## Usage

rss2json expects XML files as input. You can specify multiple files as parameter, e.g.

  rss2json.py ../data/examples/1*.xml


