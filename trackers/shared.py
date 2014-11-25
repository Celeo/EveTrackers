from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask.ext.socketio import SocketIO
socketio = SocketIO()


app_settings = {}


class InGameBrowser(dict):

    alliance_name = ''

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        return self.request.headers[str(key)]

    def is_igb(self):
        return 'Eve-Trusted' in self.request.headers and self.request.headers['Eve-Trusted'] in ['No', 'Yes']

    def is_trusted(self):
        return 'Eve-Trusted' in self.request.headers and self.request.headers['Eve-Trusted'] == 'Yes'

    def is_valid(self):
        return self.is_trusted() and 'Eve-Alliancename' in self.request.headers and \
            self.request.headers['Eve-Alliancename'] == self.alliance_name

    def all(self):
        ret = {}
        for key, value in self.request.headers:
            if not key.startswith('Eve-'):
                continue
            ret[key] = value
        return ret

    def __repr__(self):
        return '<InGameBrowser {} {} {}>'.format(self.is_igb(), self.is_trusted(), self.is_valid())
