# cloud_enum

Maintained fork of initstring's popular `cloud_enum` OSS reconnaissance tool.

This fork is maintained by Tantalum Security to keep the original standalone workflow usable, accurate, and operationally effective as cloud provider behavior changes.

## Fork Status

- Original project by [initstring](https://github.com/initstring/cloud_enum)
- Current maintained fork: Tantalum Security
- Current version: `0.8.1`
- Changelog: [CHANGELOG.md](CHANGELOG.md)

The upstream project was widely adopted and remains useful, but cloud enumeration heuristics need periodic maintenance to stay accurate. This fork focuses on keeping the classic CLI working well for operators who still rely on it.

## Why This Fork Exists

Tool effectiveness depends on correctly interpreting provider-specific responses. That is especially true for AWS S3, where older detection assumptions now produce false negatives or ambiguous results in real environments.

Recent work in this fork focuses on:

- keeping S3 bucket detection reliable across newer AWS regions
- reducing wasted requests during brute-force expansion
- avoiding low-value mutations built from full dotted keywords by default
- handling network failures and slow responses more predictably
- adding regression tests around provider-specific detection logic

## Overview

Multi-cloud OSINT tool. Enumerate public resources in AWS, Azure, and Google Cloud.

Currently enumerates the following:

**Amazon Web Services**:
- Open / Protected S3 Buckets
- awsapps (WorkMail, WorkDocs, Connect, etc.)

**Microsoft Azure**:
- Storage Accounts
- Open Blob Storage Containers
- Hosted Databases
- Virtual Machines
- Web Apps

**Google Cloud Platform**
- Open / Protected GCP Buckets
- Open / Protected Firebase Realtime Databases
- Google App Engine sites
- Cloud Functions (enumerates project/regions with existing functions, then brute forces actual function names)
- Open Firebase Apps

See it in action in [Codingo](https://github.com/codingo)'s video demo [here](https://www.youtube.com/embed/pTUDJhWJ1m0).

<img src="https://initstring.keybase.pub/host/images/cloud_enum.png" align="center"/>

## Recent Improvements

Recent releases improve the parts of the tool that directly affect hit rate and scan quality.

- Dotted keywords now mutate from the leftmost label by default. For example, `portal.example.com` still gets probed directly, but mutations are built from `portal` unless `--include-domain-suffixes` is set.
- AWS S3 detection now uses `HEAD` requests against the bucket root instead of relying on object-path guesses.
- The S3 check now understands `400 Bad Request` responses that include `x-amz-bucket-region` and retries the regional endpoint before classifying the bucket.
- The tool continues to treat `403` on the bucket root as strong evidence that the bucket exists but is not publicly listable.
- HTTP probes now use real request timeouts and broader request-exception handling, which makes large scans less fragile.
- Candidate generation now de-duplicates colliding names so brute-force lists do not waste requests on repeated inputs.
- Unit tests now cover the S3 response classifier and name de-duplication behavior.

### Why These Improvements Are Required for Effectiveness

Without the S3 changes, the tool can miss real buckets.

- AWS now returns `400 Bad Request` from the global S3 endpoint for some buckets in newer regions when the probe lands on the wrong endpoint. Older logic that discarded those responses silently dropped valid findings.
- Testing `GET /index.html` is not a reliable existence check. A missing object can still produce `403` when listing is denied, so object-path probing can blur the line between "bucket exists" and "this specific object exists".
- Bucket-root `HEAD` requests are a better primitive for enumeration because they ask the question the tool actually cares about: does the bucket endpoint exist, and if so is it public or protected?
- Full dotted-keyword mutations often produce low-value candidates such as `portal.example.com-dev` or `dev.portal.example.com`. The new default avoids spending requests on those unless the operator explicitly wants them.

## Origin

The original upstream README explained that long-term maintenance would likely shift elsewhere. This fork takes the opposite approach for the standalone CLI: continue maintaining the existing tool where provider behavior changes would otherwise reduce detection accuracy.

## Usage

### Setup
Several non-standard libraries are required to support threaded HTTP requests and DNS lookups. You'll need to install the requirements as follows:

```sh
pip3 install -r ./requirements.txt
```

### Running
The only required argument is at least one keyword. You can use the built-in fuzzing strings, but you will get better results if you supply your own with `-m` and/or `-b`.

You can provide multiple keywords by specifying the `-k` argument multiple times.

Keywords are mutated automatically using strings from `enum_tools/fuzz.txt` or a file you provide with the `-m` flag. Services that require a second-level of brute forcing (Azure Containers and GCP Functions) will also use `fuzz.txt` by default or a file you provide with the `-b` flag.

By default, if a keyword contains dots, the tool keeps the original dotted keyword as a direct candidate but builds mutations from the leftmost label only. Use `--include-domain-suffixes` if you want the old behavior and want mutations built from the full dotted keyword.

Let's say you were researching "somecompany" whose website is "somecompany.io" that makes a product called "blockchaindoohickey". You could run the tool like this:

```sh
./cloud_enum.py -k somecompany -k somecompany.io -k blockchaindoohickey
```

HTTP scraping and DNS lookups use 5 threads each by default. You can try increasing this, but eventually the cloud providers will rate limit you. Here is an example to increase to 10.

```sh
./cloud_enum.py -k keyword -t 10
```

### Effectiveness Notes

- AWS S3 enumeration now uses bucket-root `HEAD` requests, then follows the region hint when AWS returns `x-amz-bucket-region`.
- Public S3 buckets are confirmed by `200`, protected buckets by `403`, and region-mismatch conditions by `400` plus a bucket-region header.
- This is intentionally different from object probes such as `/index.html`, which can return misleading `403` responses when object existence and bucket-list permissions are mixed together.
- Dotted keywords are mutated from the leftmost label by default to avoid spending time on low-value suffix-heavy candidates. Use `--include-domain-suffixes` to restore full dotted-keyword mutations.

**IMPORTANT**: Some resources (Azure Containers, GCP Functions) are discovered per-region. To save time scanning, there is a "REGIONS" variable defined in `cloudenum/azure_regions.py and cloudenum/gcp_regions.py` that is set by default to use only 1 region. You may want to look at these files and edit them to be relevant to your own work.

**Complete Usage Details**
```
usage: cloud_enum.py [-h] -k KEYWORD [-m MUTATIONS] [-b BRUTE]

Multi-cloud enumeration utility. All hail OSINT!

optional arguments:
  -h, --help            show this help message and exit
  -k KEYWORD, --keyword KEYWORD
                        Keyword. Can use argument multiple times.
  -kf KEYFILE, --keyfile KEYFILE
                        Input file with a single keyword per line.
  -m MUTATIONS, --mutations MUTATIONS
                        Mutations. Default: enum_tools/fuzz.txt
  -b BRUTE, --brute BRUTE
                        List to brute-force Azure container names. Default: enum_tools/fuzz.txt
  -t THREADS, --threads THREADS
                        Threads for HTTP brute-force. Default = 5
  -ns NAMESERVER, --nameserver NAMESERVER
                        DNS server to use in brute-force.
  -l LOGFILE, --logfile LOGFILE
                        Will APPEND found items to specified file.
  -f FORMAT, --format FORMAT
                        Format for log file (text,json,csv - defaults to text)
  --include-domain-suffixes
                        When mutating dotted keywords, keep the full dotted
                        suffix instead of mutating only the leftmost label.
  --disable-aws         Disable Amazon checks.
  --disable-azure       Disable Azure checks.
  --disable-gcp         Disable Google checks.
  -qs, --quickscan      Disable all mutations and second-level scans
```

## Attribution

Original tool by initstring. This maintained fork continues development under Tantalum Security.
