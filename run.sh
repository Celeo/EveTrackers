#!/bin/sh

gunicorn -w 9 -b 127.0.0.1:5000 trackers:app &
gunicorn -w 1 -b 127.0.0.1:5001 --worker-class socketio.sgunicorn.GeventSocketIOWorker trackers:app
