#!/usr/bin/env python
import argparse
import sys
import yaml
import itertools
import importlib
import scrapy.spider
import logging
import scrapy.cmdline

def dict2obj(d):
    class Trivial(object):
        def get_base_url(self):
            ### HACK: If base_url doesn't end with a slash, let's make it
            ### end with a slash.
            ret = self.base_url
            if not ret.endswith('/'):
                ret += '/'
            return ret
    ret = Trivial()
    for thing in d:
        setattr(ret, thing, d[thing])
    ret.as_appears_in_distribution = ''# FIXME, hack
    return ret

def main(raw_arguments):
    parser = argparse.ArgumentParser(description='Simple oh-bugimporters crawl program')

    parser.add_argument('-i', action="store", dest="input")
    parser.add_argument('-o', action="store", dest="output")
    args = parser.parse_args(raw_arguments)

    args_for_scrapy = ['scrapy',
                       'runspider',
                       'bugimporters/main.py',
                       '-a', 'input_filename=%s' % (args.input,),
                       '-s', 'TELNETCONSOLE_ENABLED=0',
                       '-s', 'WEBSERVICE_ENABLED=0',
                       '-s', 'FEED_FORMAT=jsonlines',
                       '-s', 'FEED_URI=%s' % (args.output,),
                       '-s', 'CONCURRENT_REQUESTS_PER_DOMAIN=1',
                       '-s', 'CONCURRENT_REQUESTS=200',
                       '-s', 'DEPTH_PRIORITY=1',
                       '-s', 'SCHEDULER_DISK_QUEUE=scrapy.squeue.PickleFifoDiskQueue',
                       '-s', 'SCHEDULER_MEMORY_QUEUE=scrapy.squeue.FifoMemoryQueue',
                       ]
    return scrapy.cmdline.execute(args_for_scrapy)

def grab_bugimporter_attribute_via_string(s):
    module, class_name = s.split('.', 1)
    bug_import_module = importlib.import_module('bugimporters.%s' % (
            module,))
    found_class = getattr(bug_import_module, class_name)
    return found_class

def sliding_window_roundrobin(iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis at
    # http://docs.python.org/2/library/itertools.html#itertools.chain
    # but then modified.
    SLICE_SIZE = 20
    current_iterables = itertools.islice(iterables, 0, SLICE_SIZE)
    pending = len(list(itertools.islice(iterables, 0, SLICE_SIZE)))
    rest = itertools.islice(iterables, SLICE_SIZE, None)
    nexts = itertools.cycle(iter(it).next for it in current_iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts_before_cycle = []
            for i in range(pending):
                nexts_before_cycle.append(nexts.next())
            try:
                one_more = rest.next()
            except StopIteration:
                pass
            else:
                nexts_before_cycle.append(iter(one_more).next)
                pending += 1

            nexts = itertools.cycle(nexts_before_cycle)

class BugImportSpider(scrapy.spider.BaseSpider):
    name = "Spider for importing using oh-bugimporters"

    def get_bugimporters(self):
        '''This method gets called after __init__() because sometimes
        we set the .input_data parameter after __init__() time.'''
        objs = []
        for d in self.input_data:
            objs.append(dict2obj(d))

        for obj in objs:
            bugimporter_aliases = {
                'trac': 'trac.TracBugImporter',
                'roundup': 'roundup.RoundupBugImporter',
                'github': 'github.GitHubBugImporter',
                'google': 'google.GoogleBugImporter',
                'launchpad': 'launchpad.LaunchpadBugImporter',
                'bugzilla': 'bugzilla.BugzillaBugImporter',
                }

            raw_bug_importer = obj.bugimporter
            if '.' not in raw_bug_importer:
                raw_bug_importer = bugimporter_aliases[raw_bug_importer]

            bug_import_class = grab_bugimporter_attribute_via_string(
                raw_bug_importer)

            # The configuration may ask us to use a specific bug parser
            special_bug_parser_name = getattr(obj, 'custom_parser', None)
            if special_bug_parser_name:
                bug_parser_class = grab_bugimporter_attribute_via_string(
                    special_bug_parser_name)
            else:
                bug_parser_class = None
                # By passing None here, we ask the
                # BugImporter object to use its default.

            bug_importer = bug_import_class(
                obj, reactor_manager=None,
                bug_parser=bug_parser_class,
                data_transits=None)
            yield (obj, bug_importer)

    def requests_for_bugimporter(self, obj, bug_importer):
        for request in bug_importer.process_queries(obj.queries):
            yield request

        older_bug_data_url = getattr(
            obj, 'get_older_bug_data', '')
        if older_bug_data_url:
            kwargs = {'older_bug_data_url': older_bug_data_url}
        else:
            kwargs = {}

        bug_urls = getattr(obj, 'existing_bug_urls', [])
        if hasattr(bug_importer, 'process_bugs'):
            if bug_urls:
                for request in bug_importer.process_bugs(
                    [(url, None) for url in bug_urls],
                    **kwargs):
                    yield request
        else:
            logging.error("FYI, this bug importer does not support "
                          "process_bugs(). Fix it.")


    def start_requests(self):
        iterable_of_iterables = (
            self.requests_for_bugimporter(obj, bug_importer)
            for (obj, bug_importer) in self.get_bugimporters())

        # The following function call lets us blend the different
        # bugimporters.
        for request in sliding_window_roundrobin(iterable_of_iterables):
            yield request

    def __init__(self, input_filename=None):
        if input_filename is None:
            return

        with open(input_filename) as f:
            self.input_data = yaml.load(f)

        # Sometimes, the data we are given is wrapped in {'objects': data}
        # Detect that, and work around it.
        if 'objects' in self.input_data:
            self.input_data = self.input_data['objects']

if __name__ == '__main__':
    main(sys.argv[1:])
