import sys
import os

# Minimal WSGI application for testing
def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b"Hello World from Git-Deployed Script!"]
