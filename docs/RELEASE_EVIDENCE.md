# Release evidence for the extracted client

This branch prepares a contribution to the existing `michull/pyelternportal` library. It is not a published release. The development version `0.0.29.dev0` is a local placeholder, not a promise of the upstream maintainer's next version.

The original files remain Unlicense. The extracted extensions, counts client and ported tests are MIT (copyright 2026 FabusMingAI and contributors); see `LICENSE.extensions` and `NOTICE.extensions`.

## What is implemented

- `pyelternportal.client.PortalClient`: the complete portal extensions previously in the custom integration, including timetable, teacher/course and substitution parsing, stable items and attachments.
- `pyelternportal.registrations`: optional course-page parsing.
- `pyelternportal.counts.MessageCountClient`: a small Core-facing snapshot API. It returns per-child counts of currently listed teacher messages. It does not claim unread status or count letters/blackboard notices.
- The counts path requests only login/base pages, authentication, active-child selection, message list and logout. It never calls message detail, attachment, booking, sick-note submission or receipt-confirmation endpoints. Authentication and child selection still alter the portal session. This is a tested request contract, not a guarantee about undocumented server internals.
- Unknown/malformed message tables and incomplete child fetches fail instead of reporting zero/partial success. The demo uses only the bundled synthetic HTML.
- CI tests Python 3.13/3.14 with external network disabled, builds the wheel/sdist and checks archive/source/license correspondence.
- The tag-only publication workflow checks tag/version agreement, tests, builds, validates, attests artifacts and publishes through a PyPI trusted publisher.

## Before any actual publication

The package owner must review and accept this contribution, choose the release version, and configure the PyPI trusted publisher with the actual repository owner/name, workflow `publish.yml`, and environment `pypi`. Repository/environment protection should ensure only reviewed release tags are published. Do not configure a publisher for a repository you do not control, and do not put PyPI tokens in source files.

A workflow file alone is not publication evidence. For the chosen public version, record and verify all of:

| Evidence | Status in this preparation |
|---|---|
| Public source tag and exact commit | Pending upstream acceptance/version choice |
| Successful public test/build/publish run | Pending |
| PyPI version and project source links | Pending |
| PyPI artifact hashes match the tested CI distributions | Pending |
| Artifact provenance/attestation verifies against that repository and commit | Pending |
| Core manifest uses that exact, published version | Pending |

Only after those checks may the integration development requirement be replaced by the real published version. No upstream PR, message or package release has been submitted from this branch.
