#!/usr/bin/env python
# This is a modified version of the health check code available via:
# $ gsutil cp gs://nat-gw-template/startup.sh .
from __future__ import print_function

import argparse
import multiprocessing
import os
import subprocess
import sys
import time

import redis

from threading import Thread
from wsgiref.simple_server import make_server

MAX_LOAD = 2.0
PING_HOST = 'www.google.com'
PORT = 8192
REDIS_NAMESPACE = 'gesund-0'

_HERE = os.path.dirname(os.path.abspath(__file__))


class GesundApp:
    def __init__(self,
                 ping_host=PING_HOST,
                 redis_url=None,
                 redis_namespace=REDIS_NAMESPACE,
                 max_load=MAX_LOAD):
        self._ping_host = ping_host
        self._checks = (self._check_can_ping_host, self._check_loadavg,
                        self._check_redis_reports_healthy)
        self._redis_conn = None
        self._ns = redis_namespace
        self._max_load = max_load
        if redis_url is not None:
            print('setting up redis connection', file=sys.stderr)
            self._redis_conn = redis.from_url(redis_url, max_connections=2)

    def __call__(self, environ, start_response):
        resp = self._build_resp(start_response)

        if environ['PATH_INFO'] != '/health-check':
            return resp('404 Not Found', 'what\n')

        results = {}
        messages = {}

        for check in self._checks:
            ok, msg = check()
            results[check.__name__] = ok
            messages[check.__name__] = msg

        if all(results.values()):
            return resp('200 OK', 'ok\n')
        else:
            for func, message in messages.items():
                if not results[func]:
                    print(f'failed check {func}: {message}', file=sys.stderr)
            return resp('503 Internal Server Error', 'oh no\n')

    def _check_can_ping_host(self):
        res = subprocess.run(
            ['ping', '-c', '1', self._ping_host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5)
        if res.returncode != 0:
            print(res.stderr, file=sys.stderr)
            return False, ''
        return True, res.stdout.decode('utf-8')

    def _check_loadavg(self):
        load_15m = os.getloadavg()[2]
        if load_15m <= (self._max_load * multiprocessing.cpu_count()):
            return True, ''
        return False, f'overloaded max={self._max_load} load_15m={load_15m}'

    def _check_redis_reports_healthy(self):
        if self._redis_conn is None:
            return True, ''

        failures = []

        for key in self._redis_conn.smembers(f'{self._ns}:health-checks'):
            value = self._redis_conn.get(
                f'{self._ns}:health-check:{key}') or ''
            if value.strip() == '':
                failures.append(key)

        if len(failures) == 0:
            return True, ''

        return False, f'unhealthy: {", ".join(failures)}'

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
        target=_stream_flusher, args=(sys.stdout, sys.stderr))
    flusher_thread.daemon = True
    flusher_thread.start()

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-p',
        '--port',
        type=int,
        default=int(
            os.environ.get('GESUND_PORT', os.environ.get('PORT', PORT))),
        help='port number on which to listen')
    parser.add_argument(
        '-H',
        '--ping-host',
        default=os.environ.get('GESUND_PING_HOST',
                               os.environ.get('PING_HOST', PING_HOST)),
        help='host to ping when checking health')
    parser.add_argument(
        '-L',
        '--max-load',
        type=float,
        default=float(
            os.environ.get('GESUND_MAX_LOAD',
                           os.environ.get('MAX_LOAD', MAX_LOAD))),
        help='max load allowed')
    parser.add_argument(
        '-R',
        '--redis-url',
        default=os.environ.get(
            'GESUND_REDIS_URL',
            os.environ.get('REDIS_URL', 'redis://localhost:6379/0')),
        help='URL for redis to access for external checks, if available')
    parser.add_argument(
        '-N',
        '--redis-namespace',
        default=os.environ.get(
            'GESUND_REDIS_NAMESPACE',
            os.environ.get('REDIS_NAMESPACE', REDIS_NAMESPACE)),
        help='namespace to use in redis operations')

    args = parser.parse_args(sysargs[1:])

    httpd = make_server(
        '', args.port,
        GesundApp(
            ping_host=args.ping_host,
            redis_url=args.redis_url,
            redis_namespace=args.redis_namespace,
            max_load=args.max_load))

    print(f'serving health check app port={args.port}')
    httpd.serve_forever()


def _stream_flusher(*streams):
    while True:
        for stream in streams:
            stream.flush()
        time.sleep(0.1)


if __name__ == '__main__':
    sys.exit(main())
