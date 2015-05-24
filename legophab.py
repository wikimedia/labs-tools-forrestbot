#!/usr/bin/env python

import hashlib
import json
import requests
import time
import logging

logger = logging.getLogger('legophab')

class PhabricatorException(Exception):
    def __init__(self, code, description):
        super(PhabricatorException, self).__init__("%s: %s" % (code, description))
        self.code = code

class Phabricator(object):
    def __init__(self, host, user, cert):
        self.host = host
        self.user = user
        self.cert = cert
        self.session = {}
        self.token = int(time.time())
        self.signature = hashlib.sha1((str(self.token) + self.cert).encode('utf-8')).hexdigest()

    @property
    def connect_params(self):
        return {
            'client': 'phab-bz',
            'clientVersion': 0,
            'clientDescription': 'A script for importing Bugzilla bugs into Phabricator',
            'user': self.user,
            'host': self.host,
            'authToken': self.token,
            'authSignature': self.signature,
        }

    def connect(self):
        logger.debug('Logging in to %s' % self.host)
        req = requests.post('%s/api/conduit.connect' % self.host, data={
            'params': json.dumps(self.connect_params),
            'output': 'json',
            '__conduit__': True,
        })

        # Parse out the response (error handling ommitted)
        result = req.json()['result']
        self.session = {
            'sessionKey': result['sessionKey'],
            'connectionID': result['connectionID'],
        }

    def request(self, method, params):
        logger.debug('Requesting %s -> %s with parameters %r' % (self.host, method, params))
        if not self.session:
            self.connect()
        url = '%s/api/%s' % (self.host, method)
        params['__conduit__'] = self.session
        req = requests.post(url, data={
            'params': json.dumps(params),
            'output': 'json',
        })
        res = req.json()
        logger.debug('Received %r' % res)
        if res['error_code']:
            raise PhabricatorException(res['error_code'], res['error_info'])
        return res['result']