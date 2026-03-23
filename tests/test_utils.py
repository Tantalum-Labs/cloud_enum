from types import SimpleNamespace

import dns.exception
import dns.resolver

from enum_tools import utils


class FakeResolver:
    def __init__(self):
        self.timeout = None
        self.lifetime = None
        self.nameservers = []
        self.calls = []
        self._response = None

    def resolve(self, name, search=False):
        self.calls.append({'name': name, 'search': search})
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def test_dns_lookup_uses_absolute_resolution_without_search_suffix(monkeypatch):
    resolver = FakeResolver()
    resolver._response = SimpleNamespace()

    monkeypatch.setattr(dns.resolver, 'Resolver', lambda: resolver)

    result = utils.dns_lookup('1.1.1.1', 'furnishedfinder.0.awsapps.com')

    assert result == 'furnishedfinder.0.awsapps.com'
    assert resolver.timeout == 3
    assert resolver.lifetime == 3
    assert resolver.nameservers == ['1.1.1.1']
    assert resolver.calls == [{
        'name': 'furnishedfinder.0.awsapps.com',
        'search': False,
    }]


def test_dns_lookup_treats_noanswer_as_miss(monkeypatch):
    resolver = FakeResolver()
    resolver._response = dns.resolver.NoAnswer()

    monkeypatch.setattr(dns.resolver, 'Resolver', lambda: resolver)

    result = utils.dns_lookup('1.1.1.1', 'furnishedfinder.0.awsapps.com')

    assert result == ''


def test_dns_lookup_retries_timeouts_then_returns_empty(monkeypatch):
    resolver = FakeResolver()
    resolver._response = dns.exception.Timeout()

    monkeypatch.setattr(dns.resolver, 'Resolver', lambda: resolver)
    monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)

    result = utils.dns_lookup('1.1.1.1', 'furnishedfinder.0.awsapps.com')

    assert result == ''
    assert len(resolver.calls) == 3
