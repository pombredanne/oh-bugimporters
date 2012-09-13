# This file is part of OpenHatch.
# Copyright (C) 2012 John Morrissey
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import importlib
import json
import scrapy.http
import scrapy.spider

import bugimporters.items
from bugimporters.base import BugImporter, printable_datetime
from bugimporters.helpers import string2naive_datetime

class GitHubBugImporter(BugImporter):
    def process_queries(self, queries):
        for query in queries:
            url = query.get_query_url()

            yield scrapy.http.Request(
                url=url,
                callback=self.handle_bug_list_response)

    def handle_bug_list_response(self, response):
        issue_list = json.loads(response.body)

        bugs = []
        for bug in issue_list:
            bugs.append(self.handle_bug(bug))
        return bugs

    def process_bugs(self, bug_list):
        for bug_url, bug_data in bug_list:
            r = scrapy.http.Request(
                url=bug_url,
                callback=self.handle_bug_show_response)
            yield r

    def handle_bug_show_response(self, response):
        bug_data = json.loads(response.body)
        return self.handle_bug(bug_data)

    def handle_bug(self, bug_data):
        gbp = GitHubBugParser(self.tm, self.tm.github_name,
            self.tm.github_repo)
        return gbp.parse(bug_data)

class GitHubBugParser(object):
    def __init__(self, tm, github_name, github_repo):
        self.tm = tm
        self.github_name = github_name
        self.github_repo = github_repo

    @staticmethod
    def github_count_people_involved(issue):
        # The reporter counts as a person.
        people = 1

        if (issue['assignee'] and
            issue['assignee']['login'] != issue['user']['login']):
            people += 1

        if issue['comments'] > 0:
            # FIXME: pull comments to get an accurate count; for now,
            # we'll just bump the involved people count even though
            # the commenter might be the reporting user.
            people += 1

        return people

    def parse(self, issue):
        parsed = bugimporters.items.ParsedBug({
            'title': issue['title'],
            'description': issue['body'],
            'status': issue['state'],
            'people_involved': self.github_count_people_involved(issue),
            'date_reported': printable_datetime(string2naive_datetime(issue['created_at'])),
            'last_touched': printable_datetime(string2naive_datetime(issue['updated_at'])),
            'submitter_username': issue['user']['login'],
            'submitter_realname': '', # FIXME: can get this from ['user']['url']
            'canonical_bug_link': issue['url'],
            'looks_closed': (issue['state'] == 'closed'),
            'last_polled': printable_datetime(),
            '_project_name': self.tm.tracker_name,
        })

        issue_labels = [l['name'] for l in issue['labels']]

        b_list = self.tm.bitesized_tag.split(',')
        parsed['good_for_newcomers'] = any(b in issue_labels for b in b_list)

        d_list = self.tm.documentation_tag.split(',')
        parsed['concerns_just_documentation'] = any(d in issue_labels for d in d_list)

        return parsed

class GitHubSpider(scrapy.spider.BaseSpider):
    name = "All GitHub repos"

    def __init__(self, input_filename=None):
        if input_filename is not None:
            with open(input_filename) as f:
                self.input_data = yaml.load(f)

    def start_requests(self):
        objs = []
        for d in self.input_data:
            objs.append(bugimporters.main.dict2obj(d))

        for obj in objs:
            module, class_name = obj.bugimporter.split('.', 1)
            bug_import_module = importlib.import_module(
                'bugimporters.%s' % module)
            bug_import_class = getattr(bug_import_module, class_name)
            bug_importer = bug_import_class(
                obj, bugimporters.main.FakeReactorManager())

            class StupidQuery(object):
                def __init__(self, url):
                    self.url = url
                def get_query_url(self):
                    return self.url

            queries = [StupidQuery(q) for q in obj.queries]
            for request in bug_importer.process_queries(queries):
                yield request
