accessibilityAnalyzer
=====================

## Purpose:
This script was built to aid in research of accessibility standards in the top research libraries in the U.S. and Canada. It harnesses both the WAVE and W3c website accessibility APIs.

## How It Works:
Run through a command-line environment, this Python-based script takes a list of URLs as input, runs both APIs against each URL, returns the JSON data back, parses both responses--interleaving the results to a single response for the URL--and inserts the results into an Apache Solr search engine for easy querying and analysis. Results are saved for each URL as JSON file on disk.

## Technical Environment:
Server with command-line access.
Python (with a variety of packages).
Apache Solr
