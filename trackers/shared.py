import time


from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask.ext.socketio import SocketIO
socketio = SocketIO()


app_settings = {}


class InGameBrowser(dict):
    """ Helper object for getting information from the EVE in-game browser """

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        return self.request.headers[str(key)]

    def is_igb(self):
        return 'Eve-Trusted' in self.request.headers and self.request.headers['Eve-Trusted'] in ['No', 'Yes']

    def is_trusted(self):
        return 'Eve-Trusted' in self.request.headers and self.request.headers['Eve-Trusted'] == 'Yes'

    def is_valid(self):
        return self.is_trusted() and 'Eve-Alliancename' in self.request.headers and self.request.headers['Eve-Alliancename'] == app_settings['ALLIANCE']

    def all(self):
        ret = {}
        for key, value in self.request.headers:
            if not key.startswith('Eve-'):
                continue
            ret[key] = value
        return ret

    def __repr__(self):
        return '<InGameBrowser {} {} {}>'.format(self.is_igb(), self.is_trusted(), self.is_valid())


class EVEAPICache(object):
    """ Memory-only implementation of a cache for eveapi. """

    def __init__(self):
        self.cache = {}

    def retrieve(self, host, path, params):
        """
            Called when eveapi wants to fetch a document.
            `host` is the address of the server, `path` is the full path to
            the requested document, and `params` is a dict containing the
            parameters passed to this api call (keyID, vCode, etc).
            The method MUST return one of the following types:
                None - if your cache did not contain this entry
                str/unicode - eveapi will parse this as XML
                Element - previously stored object as provided to store()
                file-like object - eveapi will read() XML from the stream.
        """
        print('Retrieve attempt at host={}, path={}, params={}'.format(host, path, params))
        key = hash((host, path, frozenset(params.items())))
        in_memory = self.cache.get(key, None)
        if not in_memory:
            print('Retrieve attempt failed - data not in memory')
            return None
        if time() < in_memory[0]:
            print('Returning valid in-memory data')
            return in_memory[1]
        else:
            print('Deleting old data and returning None to get fresh data')
            del self.cache[key]
            return None

    def store(self, host, path, params, doc, obj):
        """
            Called when eveapi wants you to cache this item.
            You can use `obj` to get the info about the object (cachedUntil
            and currentTime, etc). `doc` is the XML document the object was
            generated from. It's generally best to cache the XML, not the object,
            unless you pickle the object. Note that this method will only
            be called if you returned None in the retrieve() for this object.
        """
        print('Storing data of host={}, path={}, params={}'.format(host, path, params))
        self.cache[hash((host, path, frozenset(params.items())))] = (obj.cachedUntil, doc)
        print('Data stored in memory and is valid until ' + time.ctime(obj.cachedUntil))


    def __repr__(self):
        return '<EveAPICache>'
