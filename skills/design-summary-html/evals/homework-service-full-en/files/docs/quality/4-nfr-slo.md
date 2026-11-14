# Non-functional requirements, SLIs and SLOs: Homework submission service

Status: answers applied · Updated: 2026-09-12 · Inputs as of: b52e8c1 · Stage 4 of 4

## Allocation

| QR | Handling | Supporting function | NFRs | Kind | Out of scope |
|---|---|---|---|---|---|
| QR-01 Submission availability | Emphasized | — | NFR-01 | SLO | |
| QR-02 Submission response time | Minimum line | — | NFR-06 | Monitor | |
| QR-03 Correct receipts | Emphasized | — | NFR-03 | Gate | |
| QR-05 Automated tests of submission processing | Minimum line | — | NFR-04 | Gate | |
| QR-06 Tolerance of storage failures | Emphasized | FR-06 | NFR-01 | SLO | |
| QR-07 Completeness of submission records | Emphasized | — | NFR-07 | Monitor | |
| QR-08 Currentness of the report | Minimum line | — | NFR-02, NFR-05 | SLO, monitor | |
| QR-09 Confidentiality of students' personal information | Emphasized | — | NFR-08 | Audit | |
| QR-10 Traceable failures | Minimum line | FR-04 | NFR-09 | Gate | |
| QR-12 Correct grading | Emphasized | — | NFR-10 | Gate | |
| QR-13 Restoring submissions | Minimum line | — | NFR-11 | Audit | Failures of the storage provider itself |
