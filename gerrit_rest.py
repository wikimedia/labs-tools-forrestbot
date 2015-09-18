import json
import requests

requests.adapters.DEFAULT_RETRIES = 5


class GerritREST(object):
    def __init__(self, url):
        """ Basic wrapper around the Gerrit REST API. Takes care of
            connections and JSON-decoding. Currently only GET requests
            are supported.

            Parameters:
              * URL - The base URL, e.g. https://gerrit.wikimedia.org/r
        """
        self._url = url.rstrip('/')
        self._session = requests.Session()
        self._session.headers.update({'Accept': 'application/json'})

    def _request(self, name, **kwargs):
        """ Make a request.

            Parameters:
            * name - The name of the REST endpoint. This will be appended to
              the base URL.
            * any parameters taken by the REST endpoint (via kwargs)
        """
        kwargs = {k: v for (k, v) in kwargs.items() if v is not None}
        r = self._session.get(self._url + '/%s/' % name, params=kwargs)
        realjson = r.text[5:]  # strips anti-XSS prefix
        return json.loads(realjson)

    def __getattr__(self, name):
        """ Provides access to any APIs not yet implemented """
        def wrapper(self, **kwargs):
            return self._request(name, **kwargs)
        wrapper.__name__ = name
        return wrapper

    def changes(self, q="", n=25, o=[]):
        """ Submits a request to the /changes/ REST API.

            Parameters:
            * q - the query string,
            * n - the maximum number of results to return - 25 by default,
            * o - the list of options to pass. CURRENT_REVISION and
              CURRENT_FILES by default.

            See https://gerrit-review.googlesource.com/Documentation/
            rest-api-changes.html for more details. """

        return self._request('changes', q=q, n=n, o=o)

    def branches(self, project, n=None, s=None, m=None, r=None):
        """ Submits a request to the /project/{name}/branches/ REST API.

            Parameters:
            * n - the maximum number of results to return - 25 by default.
            * s - Skip the given number of branches from the beginning of the
              list.
            * m - Limit the results to those projects that match the specified
              substring.
            * r - Limit the results to those branches that match the specified
              regex.

            See https://gerrit-review.googlesource.com/Documentation/
            rest-api-changes.html for more details. """

        return self._request(
            'projects/{project}/branches'.format(project=project),
            n=n,
            s=s,
            m=m,
            r=r
        )

    # def accounts, def groups, def projects, etc.
