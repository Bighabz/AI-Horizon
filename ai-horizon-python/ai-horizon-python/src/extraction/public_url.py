"""Fetch public research pages without allowing access to internal services."""

import http.client
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit


class UnsafeURLError(ValueError):
    pass


def public_target(url):
    """Resolve once and reject any non-public address before opening a socket."""
    try:
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == 'https' else 80)
    except ValueError as exc:
        raise UnsafeURLError('Invalid research URL') from exc
    if (parts.scheme not in {'http', 'https'} or not parts.hostname
            or parts.username is not None or parts.password is not None
            or port not in {80, 443} or any(ord(c) < 32 for c in url)):
        raise UnsafeURLError('Use a public HTTP or HTTPS URL without credentials')
    host = parts.hostname.rstrip('.').encode('idna').decode('ascii')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '%' in host:
        raise UnsafeURLError('Internal addresses are not supported')
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise UnsafeURLError('The hostname did not resolve')
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global or ip.is_multicast or (ip.version == 6 and ip.ipv4_mapped is not None):
            raise UnsafeURLError('Internal or reserved addresses are not supported')
    path = parts.path or '/'
    if parts.query:
        path += '?' + parts.query
    return parts.scheme, host, port, addresses[0][4][0], path


class _HTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, timeout):
        super().__init__(host, port, timeout=timeout)
        self.address = address

    def connect(self):
        # Connect to the already-checked address, preventing a second DNS lookup.
        self.sock = socket.create_connection((self.address, self.port), self.timeout)


class _HTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, address, timeout):
        super().__init__(host, port, timeout=timeout)
        self.address = address

    def connect(self):
        connection = socket.create_connection((self.address, self.port), self.timeout)
        try:
            # Preserve certificate verification and SNI for the original hostname.
            self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
        except Exception:
            connection.close()
            raise


def fetch_public_page(url, timeout=20, max_bytes=5 * 1024 * 1024, max_redirects=5):
    """Fetch bounded content, checking every redirect and pinning the resolved IP."""
    for hop in range(max_redirects + 1):
        scheme, host, port, address, path = public_target(url)
        factory = _HTTPSConnection if scheme == 'https' else _HTTPConnection
        connection = factory(host, port, address, timeout)
        try:
            connection.request('GET', path, headers={
                'User-Agent': 'AIHorizonResearch/1.0',
                'Accept': 'text/html,application/xhtml+xml,text/plain,application/xml',
                'Accept-Encoding': 'identity',
            })
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader('Location')
                if not location or hop == max_redirects:
                    raise UnsafeURLError('Too many redirects or a missing redirect location')
                url = urljoin(url, location)
                continue
            if response.status < 200 or response.status >= 300:
                raise ValueError(f'Research page returned HTTP {response.status}')
            encoding = (response.getheader('Content-Encoding') or 'identity').lower()
            if encoding not in {'identity', ''}:
                raise ValueError('Unexpected compressed response from research page')
            content = response.read(max_bytes + 1)
            if len(content) > max_bytes:
                raise ValueError('Research page exceeds the download size limit')
            return content
        finally:
            connection.close()
    raise UnsafeURLError('Too many redirects')
