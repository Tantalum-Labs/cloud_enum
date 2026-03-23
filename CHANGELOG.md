# Changelog

All notable changes to this fork are documented in this file.

## 0.8.1 - 2026-03-23

This release tightens keyword mutation behavior so scans spend fewer requests on low-value dotted-name candidates.

### Added

- `--include-domain-suffixes` flag to opt into full dotted-keyword mutations

### Changed

- dotted keywords now keep their original full value as direct candidates, but mutations are built from the leftmost label by default
- documentation and manpages now describe the new dotted-keyword mutation default and the opt-in flag
- package version updated to `0.8.1`
- DNS lookups now resolve candidate names with search suffix expansion disabled, avoiding local resolver domains from being appended to brute-force candidates

### Why It Matters

- names such as `portal.example.com-dev` and `dev.portal.example.com` are rarely useful for most operators
- reducing those mutations keeps the scan focused on higher-value candidates while preserving the old behavior for users who explicitly want it
- local resolver suffixes such as internal corporate domains no longer contaminate `awsapps.com` lookups or crash the scan with `NoAnswer`

## 0.8.0 - 2026-03-23

This release focuses on enumeration accuracy and operational effectiveness.

### Added

- unit tests for AWS S3 response classification
- unit tests for de-duplicated name generation
- formal version tracking for the maintained fork

### Changed

- documented this repository as the Tantalum Security maintained fork of the original `cloud_enum`
- updated package metadata and manpages for version `0.8.0`
- improved README guidance around current S3 detection behavior and why the updated logic is necessary

### Fixed

- switched AWS S3 bucket probing from object-style assumptions to bucket-root `HEAD` requests
- recognized `400 Bad Request` responses with `x-amz-bucket-region` as evidence that the bucket exists in another region, then retried the regional endpoint
- preserved `403` responses on bucket roots as protected-bucket findings instead of treating them as inconclusive
- added request timeouts and broader request-exception handling to reduce hangs and brittle scan behavior
- de-duplicated generated candidate names so repeated or colliding mutations do not waste requests

### Why It Matters

- older S3 logic could miss valid buckets in newer AWS regions
- object probes such as `/index.html` are ambiguous for existence testing because missing objects can still return `403` when bucket listing is denied
- the updated logic asks the correct question for enumeration: whether the bucket endpoint itself exists, and whether it is public or protected
