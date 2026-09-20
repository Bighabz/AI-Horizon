import socket
from unittest.mock import Mock

import pytest

from src.extraction import public_url as fetcher


def dns(address):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))]


@pytest.mark.parametrize('url', [
    'file:///etc/passwd', 'http://localhost/admin', 'http://service.internal/',
    'http://user:password@example.com/', 'https://example.com:22/',
])
def test_rejects_non_public_url_forms_before_dns(monkeypatch, url):
    resolve = Mock(side_effect=AssertionError('DNS should not be called'))
    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    with pytest.raises(fetcher.UnsafeURLError):
        fetcher.public_target(url)
    resolve.assert_not_called()


@pytest.mark.parametrize('addresses', [dns('127.0.0.1'), dns('169.254.169.254'), dns('8.8.8.8') + dns('10.0.0.1')])
def test_rejects_private_dns_results_including_mixed_answers(monkeypatch, addresses):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: addresses)
    with pytest.raises(fetcher.UnsafeURLError):
        fetcher.public_target('https://example.com/')


def test_redirect_cannot_reach_internal_service(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: dns('8.8.8.8'))
    response = Mock(status=302)
    response.getheader.return_value = 'http://localhost/admin'
    connection = Mock()
    connection.getresponse.return_value = response
    factory = Mock(return_value=connection)
    monkeypatch.setattr(fetcher, '_HTTPSConnection', factory)
    with pytest.raises(fetcher.UnsafeURLError):
        fetcher.fetch_public_page('https://example.com/')
    factory.assert_called_once()
    connection.close.assert_called_once()


def test_connection_uses_checked_ip_without_resolving_hostname_again(monkeypatch):
    connect = Mock()
    monkeypatch.setattr(socket, 'create_connection', connect)
    connection = fetcher._HTTPConnection('example.com', 80, '8.8.8.8', 20)
    connection.connect()
    connect.assert_called_once_with(('8.8.8.8', 80), 20)


def test_limits_response_size_and_closes_connection(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: dns('8.8.8.8'))
    response = Mock(status=200)
    response.getheader.return_value = None
    response.read.return_value = b'12345'
    connection = Mock()
    connection.getresponse.return_value = response
    monkeypatch.setattr(fetcher, '_HTTPSConnection', lambda *a: connection)
    with pytest.raises(ValueError, match='size limit'):
        fetcher.fetch_public_page('https://example.com/', max_bytes=4)
    response.read.assert_called_once_with(5)
    connection.close.assert_called_once()
