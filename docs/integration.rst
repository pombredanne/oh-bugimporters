How this integrates with the main OpenHatch site
================================================

In this section of the oh-bugimporters documentation, we discuss how
the OpenHatch web app integrates with this "oh-bugimporters"
project. (If you want to integrate your own project with
oh-bugimporters, you can use this to understand the architecture.)

To understand that, we'll go through a few elements at a time.


On the web: /customs/
=====================

Within the OpenHatch code, "customs" is the name for data "import" and
"export." (It's a pun.)

On the live OpenHatch website, there is a small bit of web code for
letting site administrators manage the list of bug trackers that we
download data from. This lives at https://openhatch.org/customs/

(A note about security: At the moment, there is no authorization; any
logged-in user of the OpenHatch site can visit the /customs/
management interface and change this configuration. Right now, we
consider this a good idea because it makes using the site a smooth
process -- whenever a project maintainer wants to add their project,
they don't need to wait to receive permission.)

The "Tracker type" drop-down is generated from data stored in
mysite/customs/core_bugimporters.py -- in particular, the all_trackers
object defined at the top of the file. As you choose options in the
drop-down, JavaScript on the page automatically submits the form and
shows you the list of bug trackers stored in the database that
correspond to that type of tracker.

By adjusting the information configured in this interface, project
maintainers alter the contents of the OpenHatch database (via models
and forms in mysite/customs/). Once per day, we run a periodic task
known as customs_twist to configure oh-bugimporters and perform the
downloading.


customs_twist
=============

The process of doing the downloading is, at the moment, performed by a
Django management command called "customs_twist." You can find its
implementation in mysite/customs/management/commands/customs_twist.py.

The high-level overview of customs_twist is that it prepares some
objects for bookkeeping of asynchronous downloading, and then looks at
the database for instances of the various TrackerModel subclasses. For
each such object, it configures a corresponding BugImporter object from
oh-bugimporters and asks it to perform an import.

Much more can be written about the complexities of customs_twist. I hope
that we throw it away quickly in a transition to usings scrapy to manage
Twisted.


TrackerModels and QueryModels
=============================

Recall that /customs/ adjusts data in the oh-mainline database, and that
these URLs interact with code in mysite/customs/models.py.

In those Django models, we have one model class to model each type of
tracker. (A "type" of tracker here refers to the software running the
remote bug tracker we are importing from -- for example, Bugzilla,
Trac, or Github Issues.)

We keep these different models (and corresponding data entry forms)
so that the web app can prompt for, and store, the different
configurable data about each tracker. You can see these models in
mysite/customs/models.py. (Implementation detail: these model classes
use object-oriented inheritance to permit us to shorten the code for
each tracker.)

It is the job of the BugImporter (within oh-bugimporters) to look at
the data in a TrackerModel instance and configure the BugImporter and
BugParser as needed.

Note also that for bug trackers, such as large Bugzilla bug trackers,
we want to refrain from downloading and processing every single bug in
the bug tracker. In that case, the web interface offers a form for
configuring "Queries" that yield a list of bugs that ought to be
imported. In the oh-mainline customs code, there is a QueryModel for
each bug tracker type that requires this. At bug import time, these
are converted to URL strings and passed to the BugImporter object, via
the BugImporter.handle_queries() method.


What becomes of customs_twist in a scrapy world
===============================================

The following is my (Asheesh's) recommendation for how oh-bugimporters
and oh-mainline should interact, once oh-bugimporters has been moved
to using scrapy.

First, oh-bugimporters should not have a management command that
executes any HTTP requests. Instead, it should have a management
command that outputs information from the TrackerModel objects and
QueryModel objects into a configuration file for oh-bugimporters. (The
configuration file could be a JSON file, if that is a convenient
format.)

There should be a command that one can run, based on scrapy, that
launches oh-bugimpoters and tells it download all the data that is
required by that configuration file. The result will be a series of
bugimporters.items.ParsedBug objects. With the help of scrapy, these
will be stored in a JSON data file.

(One advantage of this architecture is that it will become easy to run
the bug importers "by hand" while developing -- just keep a
configuration file around, and run the import process, and look at the
resulting JSON data.)

There should be a management command within oh-mainline that can
import this data file, a series of ParsedBug objects, into the Django
database.

It seems to me that this will result in a very clear set of boundaries
between the two bits of code. It will also mean removing the
data_transit callbacks.

(As a side note: This change will also permit us to remove the
TracTimeline model from the oh-mainline project. Instead, to implement
caching this sort of intermedaite data generated while scraping,
oh-bugimporters can have an optional filesystem cache. If this remark
makes no sense to you, I (Asheesh) can explain it more.)

