Command line interface
======================

(Status: Vaporware)

The oh-bugimporters package has the capability to crawl remote bug
trackers and store the parsed data in JSON files. To use this
functionality, you must create a JSON file with information about the
remote bug trackers you want to crawl.

This document steps you through that.

In order to do a bug crawl, you'll need to follow these steps:

Configure some Tracker Model data
---------------------------------

Create a JSON file in, for example, /tmp/configuration.json, that is a
list of dictionaries.

The dictionaries must have the following keys:

 * tracker_name (string)
 * base_url (string)

The following key is optional, and if present, is used when annotating
the the bug data with the project name. By default, this is the same
as the tracker_name.

 * bug_project_name_format (string)

The following keys are optional, and are used during bug data
processing to annotate the bug data with information like if the bug
is good for first-time contributors, or if the bug is oriented
entirely around documentation.

 * bitesized_type (string)
 * bitesized_text (string)
 * documentation_type (string)
 * documentation_text (string)

A sample valid JSON file can be found in examples/sample_configuration.json.

Run the command line interface
------------------------------

Run this command::

 ./env/bin/python bugimporters/main.py -i /tmp/configuration.json -o /tmp/output.json

This will read the configuration JSON file you have named, and go off
and download bugs. When it exits, /tmp/output.json will have the
parsed bug data.

