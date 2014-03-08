import os

import bugimporters.main
from mock import Mock


HERE = os.path.dirname(os.path.abspath(__file__))

# Create a global variable that can be referenced both from inside tests
# and from module level functions functions.

bug_data_transit = {
    'get_fresh_urls': None,
    'update': None,
    'delete_by_url': None,
}

trac_data_transit = {
    'get_bug_times': lambda url: (None, None),
    'get_timeline_url': Mock(),
    'update_timeline': Mock()
}

importer_data_transits = {'bug': bug_data_transit, 'trac': trac_data_transit}


class TestBaseSpider(object):

    def setup_class(cls):
        cls.spider = bugimporters.main.BugImportSpider()
        # This is sample input data that has an invalid special
        # bug parser name.
        cls.spider.input_data = [
            {'as_appears_in_distribution': u'',
             'documentation_type': u'',
             'existing_bug_urls': [],
             'bug_project_name_format': u'FEL',
             'base_url': u'https://fedorahosted.org/fedora-electronic-lab/report/1',
             'custom_parser': u'fedora-electronic-lab',
             'documentation_text': u'',
             'bitesized_text': u'',
             'bitesized_type': u'',
             'queries': [u'https://fedorahosted.org/fedora-electronic-lab'],
             'get_older_bug_data': None,
             'tracker_name': u'fedora-electronic-lab',
             'bugimporter': u'trac'},
            ]

    def test_get_bugimporters(self):
        # We should get no bugimporters out.

        # In the past, what happened was a crash.
        assert([] == list(self.spider.get_bugimporters()))
