#!/usr/bin/env python
# This is a modified version of the health check code available via:
# $ gsutil cp gs://nat-gw-template/startup.sh .
from __future__ import print_function

import argparse
import os
import subprocess
import sys
import time

from threading import Thread
from wsgiref.simple_server import make_server


PORT = 8192
PING_HOST = 'www.google.com'
_HERE = os.path.dirname(os.path.abspath(__file__))


class GesundApp(object):

    def __init__(self, **check_opts):
        self._check_opts = check_opts
        self._checks = (
            self._can_ping_host,
        )

    def __call__(self, environ, start_response):
        resp = self._build_resp(start_response)

        if environ['PATH_INFO'] != '/health-check':
            return resp('404 Not Found', 'what\n')

        successes = []
        for check in self._checks:
            successes.append(check())

        if all(successes):
            return resp('200 OK', 'ok\n')
        else:
            return resp('503 Internal Server Error', 'oh no\n')

    def _can_ping_host(self):
        job = subprocess.Popen(
            ['ping', '-c', '1', self._check_opts['ping_host']],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = job.communicate()
        if job.returncode != 0:
            print(stderr, file=sys.stderr)
            return False, ''
        return True, stdout.decode('utf-8')

    def _build_resp(self, start_response):
        def resp(status, body):
            body = body.encode('utf-8')
            start_response(status, [
                ('content-type', 'text/plain; charset=utf-8'),
                ('content-length', str(len(body))),
            ])
            return [body]
        return resp


def main(sysargs=sys.argv[:]):
    flusher_thread = Thread(
        target=_stream_flusher, args=(sys.stdout, sys.stderr)
    )
    flusher_thread.daemon = True
    flusher_thread.start()

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-p', '--port', type=int,
        default=int(os.environ.get(
            'GESUND_PORT',
            os.environ.get('PORT', PORT)
        )),
        help='port number on which to listen'
    )
    parser.add_argument(
        '-H', '--ping-host',
        default=os.environ.get(
            'GESUND_PING_HOST',
            os.environ.get('PING_HOST', PING_HOST)
        ),
        help='host to ping when checking health'
    )
    parser.add_argument(
        '--print-service',
        action='store_true', default=False,
        help='print the systemd service definition and exit'
    )
    parser.add_argument(
        '--print-wrapper',
        action='store_true', default=False,
        help='print the service wrapper script and exit'
    )

    args = parser.parse_args(sysargs[1:])

    if args.print_service:
        _print_misc_file('gesund.service')
        return 0

    if args.print_wrapper:
        _print_misc_file('gesund-wrapper')
        return 0

    httpd = make_server(
        '', args.port,
        GesundApp(ping_host=args.ping_host)
    )

    print('Serving health check app on port {}...'.format(args.port))
    httpd.serve_forever()


def _print_misc_file(filename, here=_HERE):
    with open(os.path.join(here, 'misc', filename)) as fp:
        print(fp.read())


def _stream_flusher(*streams):
    while True:
        for stream in streams:
            stream.flush()
        time.sleep(0.1)


if __name__ == '__main__':
    sys.exit(main())
