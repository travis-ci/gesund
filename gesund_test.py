import gesund

import multiprocessing
import os
import subprocess

import pytest


@pytest.fixture
def app():
    return gesund.GesundApp(ping_host='bogus.example.com')


def test_unknown_url(app):
    start_response = {'status': '', 'headers': ()}

    def sr_func(status, headers):
        start_response['status'] = status
        start_response['headers'] = headers

    resp = app({'PATH_INFO': '/wat'}, sr_func)
    assert start_response['status'] == '404 Not Found'
    assert len(resp) > 0
    assert resp[0] == b'what\n'


def test_health_check_healthy(app, monkeypatch):
    start_response = {'status': '', 'headers': ()}

    def sr_func(status, headers):
        start_response['status'] = status
        start_response['headers'] = headers

    def mockrun(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b'oh hello', stderr=b'')

    monkeypatch.setattr(subprocess, 'run', mockrun)
    monkeypatch.setattr(multiprocessing, 'cpu_count', lambda: 1)
    monkeypatch.setattr(os, 'getloadavg', lambda: (0.1, 0.1, 0.1))

    resp = app({'PATH_INFO': '/health-check'}, sr_func)
    assert start_response['status'] == '200 OK'
    assert len(resp) > 0
    assert resp[0] == b'ok\n'


def test_health_check_unhealthy_ping(app, monkeypatch):
    start_response = {'status': '', 'headers': ()}

    def sr_func(status, headers):
        start_response['status'] = status
        start_response['headers'] = headers

    def mockrun(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=1, stdout=b'', stderr=b'ugh')

    monkeypatch.setattr(subprocess, 'run', mockrun)
    monkeypatch.setattr(multiprocessing, 'cpu_count', lambda: 1)
    monkeypatch.setattr(os, 'getloadavg', lambda: (0.1, 0.1, 0.1))

    resp = app({'PATH_INFO': '/health-check'}, sr_func)
    assert start_response['status'] == '503 Internal Server Error'
    assert len(resp) > 0
    assert resp[0] == b'oh no\n'


def test_health_check_unhealthy_load(app, monkeypatch):
    start_response = {'status': '', 'headers': ()}

    def sr_func(status, headers):
        start_response['status'] = status
        start_response['headers'] = headers

    def mockrun(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b'oh hello', stderr=b'')

    monkeypatch.setattr(subprocess, 'run', mockrun)
    monkeypatch.setattr(multiprocessing, 'cpu_count', lambda: 1)
    monkeypatch.setattr(os, 'getloadavg', lambda: (9.9, 9.9, 9.9))

    resp = app({'PATH_INFO': '/health-check'}, sr_func)
    assert start_response['status'] == '503 Internal Server Error'
    assert len(resp) > 0
    assert resp[0] == b'oh no\n'
