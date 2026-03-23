"""
AWS-specific checks. Part of the cloud_enum package available at
github.com/initstring/cloud_enum
"""

from urllib.parse import urlparse
import requests
from enum_tools import utils

BANNER = '''
++++++++++++++++++++++++++
      amazon checks
++++++++++++++++++++++++++
'''

# Known S3 domain names
S3_URL = 's3.amazonaws.com'
APPS_URL = 'awsapps.com'

# Known AWS region names. This global will be used unless the user passes
# in a specific region name. (NOT YET IMPLEMENTED)
AWS_REGIONS = ['amazonaws.com',
               'ap-east-1.amazonaws.com',
               'us-east-2.amazonaws.com',
               'us-west-1.amazonaws.com',
               'us-west-2.amazonaws.com',
               'ap-south-1.amazonaws.com',
               'ap-northeast-1.amazonaws.com',
               'ap-northeast-2.amazonaws.com',
               'ap-northeast-3.amazonaws.com',
               'ap-southeast-1.amazonaws.com',
               'ap-southeast-2.amazonaws.com',
               'ca-central-1.amazonaws.com',
               'cn-north-1.amazonaws.com.cn',
               'cn-northwest-1.amazonaws.com.cn',
               'eu-central-1.amazonaws.com',
               'eu-west-1.amazonaws.com',
               'eu-west-2.amazonaws.com',
               'eu-west-3.amazonaws.com',
               'eu-north-1.amazonaws.com',
               'sa-east-1.amazonaws.com']


def get_s3_bucket_name(bucket_url):
    """
    Extract the bucket name from a virtual-hosted-style S3 URL.
    """
    hostname = urlparse(bucket_url).netloc.split(':', 1)[0]

    if hostname.endswith(f'.{S3_URL}'):
        return hostname[:-len(f'.{S3_URL}')]

    if '.s3.' in hostname:
        return hostname.split('.s3.', 1)[0]

    return hostname.split('.', 1)[0]


def get_s3_regional_host(bucket_name, region):
    """
    Build a region-specific S3 hostname for a bucket.
    """
    domain_suffix = 'amazonaws.com.cn' if region.startswith('cn-') else 'amazonaws.com'
    return f'{bucket_name}.s3.{region}.{domain_suffix}'


def probe_s3_bucket(bucket_name, region=None):
    """
    Send a bucket-level HEAD request to S3 and return the response.
    """
    if region:
        bucket_host = get_s3_regional_host(bucket_name, region)
    else:
        bucket_host = f'{bucket_name}.{S3_URL}'

    return requests.head(f'http://{bucket_host}', allow_redirects=True,
                         timeout=utils.DEFAULT_HTTP_TIMEOUT)


def analyze_s3_response(reply, allow_region_retry=True):
    """
    Classify an S3 response into a printable result.
    """
    data = {'platform': 'aws', 'msg': '', 'target': '', 'access': ''}
    reason = reply.reason or ''

    if reply.status_code == 404:
        return None

    if reply.status_code == 200:
        data['msg'] = 'OPEN S3 BUCKET'
        data['target'] = reply.url
        data['access'] = 'public'
        return {'data': data, 'list_contents': True}

    if reply.status_code == 403:
        data['msg'] = 'Protected S3 Bucket'
        data['target'] = reply.url
        data['access'] = 'protected'
        return {'data': data, 'list_contents': False}

    region = reply.headers.get('x-amz-bucket-region')
    if reply.status_code == 400 and region:
        bucket_name = get_s3_bucket_name(reply.url)
        if allow_region_retry:
            try:
                regional_reply = probe_s3_bucket(bucket_name, region=region)
            except requests.exceptions.RequestException as error_msg:
                print(f"    [!] Error probing regional S3 endpoint for {bucket_name}:")
                print(error_msg)
            else:
                regional_result = analyze_s3_response(regional_reply,
                                                     allow_region_retry=False)
                if regional_result:
                    return regional_result

        data['msg'] = f'S3 Bucket Found ({region})'
        data['target'] = f'http://{get_s3_regional_host(bucket_name, region)}'
        data['access'] = 'exists'
        return {'data': data, 'list_contents': False}

    if reply.status_code == 503 and 'Slow Down' in reason:
        print(f"    [!] AWS rate limited the probe for {reply.url}, continuing...")
        return None

    if reply.status_code == 400 and 'Bad Request' in reason:
        return None

    print(f"    Unknown status codes being received from {reply.url}:\n"
          f"       {reply.status_code}: {reason}")
    return None


def print_s3_response(reply):
    """
    Parses the HTTP reply of a brute-force attempt

    This function is passed into the class object so we can view results
    in real-time.
    """
    result = analyze_s3_response(reply)
    if not result:
        return None

    utils.fmt_output(result['data'])
    if result['list_contents']:
        utils.list_bucket_contents(result['data']['target'])

    return None


def check_s3_buckets(names, threads):
    """
    Checks for open and restricted Amazon S3 buckets
    """
    print("[+] Checking for S3 buckets")

    # Start a counter to report on elapsed time
    start_time = utils.start_timer()

    # Initialize the list of correctly formatted urls
    candidates = []

    # Take each mutated keyword craft a url with the correct format
    for name in names:
        candidates.append(f'{name}.{S3_URL}')

    # Send the valid names to the batch HTTP processor
    utils.get_url_batch(candidates, use_ssl=False,
                        callback=print_s3_response,
                        threads=threads,
                        method='head')

    # Stop the time
    utils.stop_timer(start_time)


def check_awsapps(names, threads, nameserver, nameserverfile=False):
    """
    Checks for existence of AWS Apps
    (ie. WorkDocs, WorkMail, Connect, etc.)
    """
    data = {'platform': 'aws', 'msg': 'AWS App Found:', 'target': '', 'access': ''}

    print("[+] Checking for AWS Apps")

    # Start a counter to report on elapsed time
    start_time = utils.start_timer()

    # Initialize the list of domain names to look up
    candidates = []

    # Initialize the list of valid hostnames
    valid_names = []

    # Take each mutated keyword craft a domain name to lookup.
    for name in names:
        candidates.append(f'{name}.{APPS_URL}')

    # AWS Apps use DNS sub-domains. First, see which are valid.
    valid_names = utils.fast_dns_lookup(candidates, nameserver,
                                        nameserverfile, threads=threads)

    for name in valid_names:
        data['target'] = f'https://{name}'
        data['access'] = 'protected'
        utils.fmt_output(data)

    # Stop the timer
    utils.stop_timer(start_time)


def run_all(names, args):
    """
    Function is called by main program
    """
    print(BANNER)

    # Use user-supplied AWS region if provided
    # if not regions:
    #    regions = AWS_REGIONS
    check_s3_buckets(names, args.threads)
    check_awsapps(names, args.threads, args.nameserver, args.nameserverfile)
