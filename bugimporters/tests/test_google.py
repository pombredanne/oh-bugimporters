import datetime
import os
import mock

from bugimporters.tests import Bug, ObjectFromDict
from bugimporters.google import GoogleBugParser
import bugimporters.trac
import bugimporters.main
import autoresponse
from mock import Mock


HERE = os.path.dirname(os.path.abspath(__file__))

# Create a global variable that can be referenced both from inside tests
# and from module level functions functions.
all_bugs = []


def delete_by_url(url):
    for index, bug in enumerate(all_bugs):
        if bug[0] == url:
            del all_bugs[index]
            break

bug_data_transit = {
    'get_fresh_urls': lambda *args: {},
    'update': lambda value: all_bugs.append(Bug(value)),
    'delete_by_url': delete_by_url,
}

trac_data_transit = {
    'get_bug_times': lambda url: (None, None),
    'get_timeline_url': Mock(),
    'update_timeline': Mock()
}

importer_data_transits = {'bug': bug_data_transit, 'trac': trac_data_transit}

class MockGoogleTrackerModel(mock.Mock):
    tracker_name='SymPy'
    google_name='sympy'
    bitesized_type='label'
    bitesized_text='EasyToFix'
    documentation_type='label'
    documentation_text='Documentation'

class TestGoogleBugImport(object):
    @staticmethod
    def assertEqual(x, y):
        assert x == y

    def test_top_to_bottom(self):
        spider = bugimporters.main.BugImportSpider()
        spider.input_data = [dict(
                    tracker_name='SymPy',
                    google_name='sympy',
                    bitesized_type='label',
                    bitesized_text='EasyToFix',
                    documentation_type='label',
                    documentation_text='Documentation',
                    bugimporter = 'google.GoogleBugImporter',
                    queries=[
                    'https://code.google.com/feeds/issues/p/sympy/issues/full?can=open&max-results=10000' +
                    '&label=EasyToFix']
                    )]
        url2filename = {
            'https://code.google.com/feeds/issues/p/sympy/issues/full?can=open&max-results=10000&label=EasyToFix':
                os.path.join(HERE, 'sample-data', 'google',
                             'label-easytofix.atom'),
            }
        ar = autoresponse.Autoresponder(url2filename=url2filename,
                                        url2errors={})
        items = ar.respond_recursively(spider.start_requests())
        assert len(items) == 74

    def test_top_to_bottom_with_bigger_project(self):
        # For this project, we found that some bugs from the past were not
        # getting refreshed.
        #
        # This is because of a subtlety of import from the Google Code bug
        # tracker.
        #
        # The get_older_bug_data query gives us all updates to bugs that have
        # taken place since that date. So if one of the bugs in
        # existing_bug_urls has been updated, we get notified of those updates.
        #
        # But if one of those bugs has *not* been updated, then Google Code
        # tells us nothing. The old behavior was that we would, therefore,
        # leave no information about that bug in the output of the crawl.
        # Therefore, consumers of the data would conclude that the bug has
        # not been polled. But actually, we *do* have some information we
        # can report. Namely, since there was no update to the bug since
        # its last_polled, it has stayed the same until now.
        #
        # Therefore, this test verifies that we report on existing_bug_urls
        # to indicate there is no change.
        spider = bugimporters.main.BugImportSpider()
        spider.input_data = [
            {'bitesized_text': u'Effort-Minimal,Effort-Easy,Effort-Fair',
             'bitesized_type': u'label',
             'bugimporter': 'google',
             'custom_parser': u'',
             'documentation_text': u'Component-Docs',
             'documentation_type': u'label',
             'existing_bug_urls': [
                    # No data in the feed
                    u'http://code.google.com/p/soc/issues/detail?id=1461',
                    # Has data in the feed
                    u'http://code.google.com/p/soc/issues/detail?id=1618',
                    ],
             'get_older_bug_data':
                 u'https://code.google.com/feeds/issues/p/soc/issues/full?max-results=10000&can=all&updated-min=2012-05-22T19%3A52%3A10',
             'google_name': u'soc',
             'queries': [],
             'tracker_name': u'Melange'},
            ]

        url2filename = {
            'https://code.google.com/feeds/issues/p/soc/issues/full?max-results=10000&can=all&updated-min=2012-05-22T19%3A52%3A10':
                os.path.join(HERE, 'sample-data', 'google', 'soc-date-query.atom'),
            }
        ar = autoresponse.Autoresponder(url2filename=url2filename,
                                        url2errors={})
        items = ar.respond_recursively(spider.start_requests())

        # Make sure bugs that actually have data come back, clear and true
        bug_with_data = [
            x for x in items
            if (x['canonical_bug_link'] ==
                'http://code.google.com/p/soc/issues/detail?id=1618')][0]
        assert bug_with_data['title']
        assert not bug_with_data.get('_no_update', False)

        # Verify (here's the new bit) that we report on bugs that are not
        # represented in the feed.
        bug_without_data = [
            x for x in items
            if (x['canonical_bug_link'] ==
                'http://code.google.com/p/soc/issues/detail?id=1461')][0]
        assert bug_without_data['_no_update']

        assert ('http://code.google.com/p/soc/issues/detail?id=1461' in [
            x['canonical_bug_link'] for x in items])

    def test_old_bug_data(self):
        spider = bugimporters.main.BugImportSpider()
        spider.input_data = [dict(
                    tracker_name='SymPy',
                    google_name='sympy',
                    bitesized_type='label',
                    bitesized_text='EasyToFix',
                    documentation_type='label',
                    documentation_text='Documentation',
                    bugimporter = 'google.GoogleBugImporter',
                    queries=[],
                    get_older_bug_data=('https://code.google.com/feeds/issues/p/sympy/issues/full' +
                                        '?max-results=10000&can=all&updated-min=2012-09-15T00:00:00'),
                    existing_bug_urls=[
                    'http://code.google.com/p/sympy/issues/detail?id=2371',
                    ],
                    )]
        url2filename = {
            ('https://code.google.com/feeds/issues/p/sympy/issues/full' +
             '?max-results=10000&can=all&updated-min=2012-09-15T00:00:00'):
                os.path.join(HERE, 'sample-data', 'google',
                             'issues-by-date.atom'),
            }
        ar = autoresponse.Autoresponder(url2filename=url2filename,
                                        url2errors={})
        items = ar.respond_recursively(spider.start_requests())
        assert len(items) == 1
        item = items[0]
        assert item['canonical_bug_link'] == 'http://code.google.com/p/sympy/issues/detail?id=2371'

    def test_create_google_data_dict_with_everything(self):
        atom_dict = {
                'id': {'text': 'http://code.google.com/feeds/issues/p/sympy/issues/full/1215'},
                'published': {'text': '2008-11-24T11:15:58.000Z'},
                'updated': {'text': '2009-12-06T23:01:11.000Z'},
                'title': {'text': 'fix html documentation'},
                'content': {'text': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module"""},
                'author': {'name': {'text': 'fabian.seoane'}},
                'cc': [
                    {'username': {'text': 'asmeurer'}}
                    ],
                'owner': {'username': {'text': 'Vinzent.Steinberg'}},
                'label': [
                    {'text': 'Type-Defect'},
                    {'text': 'Priority-Critical'},
                    {'text': 'Documentation'},
                    {'text': 'Milestone-Release0.6.6'}
                    ],
                'state': {'text': 'closed'},
                'status': {'text': 'Fixed'}
                }
        bug_atom = ObjectFromDict(atom_dict, recursive=True)
        gbp = GoogleBugParser(
                bug_url='http://code.google.com/p/sympy/issues/detail?id=1215')
        gbp.bug_atom = bug_atom

        got = gbp.get_parsed_data_dict(MockGoogleTrackerModel)
        wanted = {'title': 'fix html documentation',
                  'description': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module""",
                  'status': 'Fixed',
                  'importance': 'Critical',
                  'people_involved': 3,
                  'date_reported': (
                datetime.datetime(2008, 11, 24, 11, 15, 58).isoformat()),
                  'last_touched': (
                datetime.datetime(2009, 12, 06, 23, 01, 11).isoformat()),
                  'looks_closed': True,
                  'submitter_username': 'fabian.seoane',
                  'submitter_realname': '',
                  'canonical_bug_link': 'http://code.google.com/p/sympy/issues/detail?id=1215',
                  'good_for_newcomers': False,
                  'concerns_just_documentation': True,
                  '_project_name': 'SymPy',
                  }
        self.assertEqual(wanted, got)

    def test_create_google_data_dict_author_in_list(self):
        atom_dict = {
                'id': {'text': 'http://code.google.com/feeds/issues/p/sympy/issues/full/1215'},
                'published': {'text': '2008-11-24T11:15:58.000Z'},
                'updated': {'text': '2009-12-06T23:01:11.000Z'},
                'title': {'text': 'fix html documentation'},
                'content': {'text': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module"""},
                'author': [{'name': {'text': 'fabian.seoane'}}],
                'cc': [
                    {'username': {'text': 'asmeurer'}}
                    ],
                'owner': {'username': {'text': 'Vinzent.Steinberg'}},
                'label': [
                    {'text': 'Type-Defect'},
                    {'text': 'Priority-Critical'},
                    {'text': 'Documentation'},
                    {'text': 'Milestone-Release0.6.6'}
                    ],
                'state': {'text': 'closed'},
                'status': {'text': 'Fixed'}
                }
        bug_atom = ObjectFromDict(atom_dict, recursive=True)
        gbp = GoogleBugParser(
                bug_url='http://code.google.com/p/sympy/issues/detail?id=1215')
        gbp.bug_atom = bug_atom

        got = gbp.get_parsed_data_dict(MockGoogleTrackerModel)
        wanted = {'title': 'fix html documentation',
                  'description': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module""",
                  'status': 'Fixed',
                  'importance': 'Critical',
                  'people_involved': 3,
                  'date_reported': (
                datetime.datetime(2008, 11, 24, 11, 15, 58).isoformat()),
                  'last_touched': (
                datetime.datetime(2009, 12, 06, 23, 01, 11).isoformat()),
                  'looks_closed': True,
                  'submitter_username': 'fabian.seoane',
                  'submitter_realname': '',
                  'canonical_bug_link': 'http://code.google.com/p/sympy/issues/detail?id=1215',
                  'good_for_newcomers': False,
                  'concerns_just_documentation': True,
                  '_project_name': 'SymPy',
                  }
        self.assertEqual(wanted, got)

    def test_create_google_data_dict_owner_in_list(self):
        atom_dict = {
                'id': {'text': 'http://code.google.com/feeds/issues/p/sympy/issues/full/1215'},
                'published': {'text': '2008-11-24T11:15:58.000Z'},
                'updated': {'text': '2009-12-06T23:01:11.000Z'},
                'title': {'text': 'fix html documentation'},
                'content': {'text': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module"""},
                'author': {'name': {'text': 'fabian.seoane'}},
                'cc': [
                    {'username': {'text': 'asmeurer'}}
                    ],
                'owner': [{'username': {'text': 'Vinzent.Steinberg'}}],
                'label': [
                    {'text': 'Type-Defect'},
                    {'text': 'Priority-Critical'},
                    {'text': 'Documentation'},
                    {'text': 'Milestone-Release0.6.6'}
                    ],
                'state': {'text': 'closed'},
                'status': {'text': 'Fixed'}
                }
        bug_atom = ObjectFromDict(atom_dict, recursive=True)
        gbp = GoogleBugParser(
                bug_url='http://code.google.com/p/sympy/issues/detail?id=1215')
        gbp.bug_atom = bug_atom

        got = gbp.get_parsed_data_dict(MockGoogleTrackerModel)
        wanted = {'title': 'fix html documentation',
                  'description': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module""",
                  'status': 'Fixed',
                  'importance': 'Critical',
                  'people_involved': 3,
                  'date_reported': (
                datetime.datetime(2008, 11, 24, 11, 15, 58).isoformat()),
                  'last_touched': (
                datetime.datetime(2009, 12, 06, 23, 01, 11).isoformat()),
                  'looks_closed': True,
                  'submitter_username': 'fabian.seoane',
                  'submitter_realname': '',
                  'canonical_bug_link': 'http://code.google.com/p/sympy/issues/detail?id=1215',
                  'good_for_newcomers': False,
                  'concerns_just_documentation': True,
                  '_project_name': 'SymPy',
                  }
        self.assertEqual(wanted, got)

    def test_create_google_data_dict_without_status(self):
        atom_dict = {
                'id': {'text': 'http://code.google.com/feeds/issues/p/sympy/issues/full/1215'},
                'published': {'text': '2008-11-24T11:15:58.000Z'},
                'updated': {'text': '2009-12-06T23:01:11.000Z'},
                'title': {'text': 'fix html documentation'},
                'content': {'text': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module"""},
                'author': {'name': {'text': 'fabian.seoane'}},
                'cc': [
                    {'username': {'text': 'asmeurer'}}
                    ],
                'owner': {'username': {'text': 'Vinzent.Steinberg'}},
                'label': [
                    {'text': 'Type-Defect'},
                    {'text': 'Priority-Critical'},
                    {'text': 'Documentation'},
                    {'text': 'Milestone-Release0.6.6'}
                    ],
                'state': {'text': 'closed'},
                'status': None
                }
        bug_atom = ObjectFromDict(atom_dict, recursive=True)
        gbp = GoogleBugParser(
                bug_url='http://code.google.com/p/sympy/issues/detail?id=1215')
        gbp.bug_atom = bug_atom

        got = gbp.get_parsed_data_dict(MockGoogleTrackerModel)
        wanted = {'title': 'fix html documentation',
                  'description': """http://docs.sympy.org/modindex.html

I don't see for example the solvers module""",
                  'status': '',
                  'importance': 'Critical',
                  'people_involved': 3,
                  'date_reported': (
                datetime.datetime(2008, 11, 24, 11, 15, 58).isoformat()),
                  'last_touched': (
                datetime.datetime(2009, 12, 06, 23, 01, 11).isoformat()),
                  'looks_closed': True,
                  'submitter_username': 'fabian.seoane',
                  'submitter_realname': '',
                  'canonical_bug_link': 'http://code.google.com/p/sympy/issues/detail?id=1215',
                  'good_for_newcomers': False,
                  'concerns_just_documentation': True,
                  '_project_name': 'SymPy',
                  }
        self.assertEqual(wanted, got)

