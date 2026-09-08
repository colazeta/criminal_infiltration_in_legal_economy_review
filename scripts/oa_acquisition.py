"""Anonymous, bounded PDF acquisition from reviewed primary-source origins.

Acquisition is evidence preparation, not identity, rights or scientific approval.
The caller must separately inspect the document and its source rights statement.
"""
import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

POLICY_PATH = Path(__file__).resolve().parents[1] / 'config/oa-acquisition.json'
MAX_BYTES = 32 * 1024 * 1024


def authorised_host(url):
    if not isinstance(url, str) or any(ord(c) < 33 for c in url) or '\\' in url:
        raise ValueError('invalid OA acquisition URL')
    parsed = urlsplit(url)
    hosts = json.loads(POLICY_PATH.read_text())['hosts']
    if (parsed.scheme != 'https' or parsed.hostname not in hosts
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.fragment):
        raise ValueError('OA evidence origin is not authorised for full-text/rights acquisition')
    return hosts[parsed.hostname]['host_type']


def request(url):
    """Pin the validated public DNS address; preserve TLS hostname verification."""
    authorised_host(url)
    parsed = urlsplit(url)
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('non-public acquisition address')
    connection = http.client.HTTPSConnection(parsed.hostname, timeout=30)
    raw = socket.create_connection((addresses[0][4][0], 443), timeout=30)
    try:
        connection.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname)
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        connection.request('GET', path, headers={'User-Agent': 'CILE-OA-verifier/1.0',
                           'Accept': 'application/pdf', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        if response.status != 200:
            return response.status, headers, b''
        declared = headers.get('content-length')
        if declared is not None and int(declared) > MAX_BYTES:
            raise ValueError('OA document exceeds byte limit')
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES or (declared is not None and len(content) != int(declared)):
            raise ValueError('oversized or incomplete OA response')
        return response.status, headers, content
    finally:
        connection.close()
        raw.close()


def acquire_pdf(url, *, transport=request):
    original = url
    seen = set()
    for _ in range(6):
        authorised_host(url)
        if url in seen:
            raise ValueError('OA redirect loop')
        seen.add(url)
        status, headers, content = transport(url)
        if status in (301, 302, 303, 307, 308):
            if not headers.get('location'):
                raise ValueError('OA redirect lacks location')
            url = urljoin(url, headers['location'])
            continue
        if status != 200:
            raise ValueError(f'OA acquisition HTTP {status}; no login, paid or challenge fallback')
        if (not isinstance(content, bytes) or len(content) > MAX_BYTES
                or not content.startswith(b'%PDF-') or b'%%EOF' not in content[-2048:]):
            raise ValueError('complete PDF response required; landing pages and challenges are not full text')
        return content, {'requested_url': original, 'full_text_url': url,
                         'host_type': authorised_host(url),
                         'full_text_sha256': hashlib.sha256(content).hexdigest(),
                         'verified_at': datetime.now(timezone.utc).isoformat(),
                         'byte_count': len(content)}
    raise ValueError('too many OA redirects')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True, type=Path,
                        help='Private scratch PDF; never a public export or repository path')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output.resolve().is_relative_to(root):
        raise SystemExit('Full text must be stored outside the repository')
    content, observation = acquire_pdf(args.url)
    with args.output.open('xb') as handle:
        handle.write(content)
    print(json.dumps(observation))
