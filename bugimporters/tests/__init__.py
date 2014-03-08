import twisted

from mock import Mock


class TrackerModel(Mock):
    """This is a Mock, rather than a regular object,
    because oh-bugimporters calls some methods on the
    object. Those method calls are not essential."""

    max_connections = 5
    tracker_name = 'Twisted',
    base_url = 'http://twistedmatrix.com/trac/'
    bug_project_name_format = '{tracker_name}'
    bitesized_type = 'keywords'
    bitesized_text = 'easy'
    documentation_type = 'keywords'
    documentation_text = 'documentation'
    as_appears_in_distribution = ''
    old_trac = False

    def get_base_url(self):
        return self.base_url

class HaskellTrackerModel(TrackerModel):
    """This is a Mock for the Haskell(GHC) tracker. Since it uses Trac we
    just need to extend TrackerModel and overwrite it's specific bitesized
    indentifiers"""

    bitesized_type = 'difficulty'
    bitesized_text = 'Easy (less than 1 hour)'


class Bug(object):

    def __init__(self, data):
        for key, value in data.items():
            self.__setattr__(key, value)


class ReactorManager(Mock):
    """This is a Mock, rather than a pure object,
    because the code calls some methods on this
    object. We don't really care though."""

    running_deferreds = 0


class FakeGetPage(object):

    def get404(self, url):
        d = twisted.internet.defer.Deferred()
        d.errback(twisted.python.failure.Failure(
                twisted.web.error.Error(
                404, 'File Not Found', None)))
        return d

class ObjectFromDict(object):
    def __init__(self, data, recursive = False):
        for key in data:
            if recursive:
                if type(data[key]) == type({}):
                    data[key] = ObjectFromDict(data[key], recursive=recursive)
                elif type(data[key]) == type([]):
                    data[key] = [ObjectFromDict(item, recursive=recursive) for item in data[key]]
            setattr(self, key, data[key])
