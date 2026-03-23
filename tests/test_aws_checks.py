from types import SimpleNamespace

import requests

from enum_tools import aws_checks


def make_reply(status_code, url='http://bucket.s3.amazonaws.com',
               reason='OK', headers=None):
    """
    Build a lightweight response object for S3 classification tests.
    """
    return SimpleNamespace(status_code=status_code, url=url, reason=reason,
                           headers=headers or {})


def test_analyze_s3_response_open_bucket():
    reply = make_reply(200)

    result = aws_checks.analyze_s3_response(reply)

    assert result['data']['msg'] == 'OPEN S3 BUCKET'
    assert result['data']['access'] == 'public'
    assert result['list_contents'] is True


def test_analyze_s3_response_protected_bucket():
    reply = make_reply(403, reason='Forbidden')

    result = aws_checks.analyze_s3_response(reply)

    assert result['data']['msg'] == 'Protected S3 Bucket'
    assert result['data']['access'] == 'protected'
    assert result['list_contents'] is False


def test_analyze_s3_response_missing_bucket():
    reply = make_reply(404, reason='Not Found')

    assert aws_checks.analyze_s3_response(reply) is None


def test_analyze_s3_response_retries_regional_endpoint(monkeypatch):
    reply = make_reply(400, reason='Bad Request',
                       headers={'x-amz-bucket-region': 'ap-south-2'})
    regional_reply = make_reply(
        403,
        url='http://bucket.s3.ap-south-2.amazonaws.com',
        reason='Forbidden'
    )
    captured = {}

    def fake_probe(bucket_name, region=None):
        captured['bucket_name'] = bucket_name
        captured['region'] = region
        return regional_reply

    monkeypatch.setattr(aws_checks, 'probe_s3_bucket', fake_probe)

    result = aws_checks.analyze_s3_response(reply)

    assert captured == {'bucket_name': 'bucket', 'region': 'ap-south-2'}
    assert result['data']['msg'] == 'Protected S3 Bucket'
    assert result['data']['target'] == regional_reply.url
    assert result['data']['access'] == 'protected'


def test_analyze_s3_response_region_hint_without_followup(monkeypatch):
    reply = make_reply(400, reason='Bad Request',
                       headers={'x-amz-bucket-region': 'eu-central-2'})

    def fake_probe(bucket_name, region=None):
        raise requests.exceptions.ConnectionError('network error')

    monkeypatch.setattr(aws_checks, 'probe_s3_bucket', fake_probe)
    monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)

    result = aws_checks.analyze_s3_response(reply)

    assert result['data']['msg'] == 'S3 Bucket Found (eu-central-2)'
    assert result['data']['target'] == 'http://bucket.s3.eu-central-2.amazonaws.com'
    assert result['data']['access'] == 'exists'
    assert result['list_contents'] is False
