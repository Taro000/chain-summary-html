# Product quality and data quality: Homework submission service

Status: answers applied · Updated: 2026-09-08 · Inputs as of: 7d0e4b9 · Stage 3 of 4

## Coverage checklist

CUJ-01: FR-01, FR-02, FR-06, FR-09. CUJ-02: FR-03, FR-08. CUJ-03: FR-04. CUJ-04: FR-05, FR-09.

### Product quality

| Characteristic > sub-characteristic | CUJ-01 | CUJ-02 | CUJ-03 | CUJ-04 | Reason not targeted |
|---|---|---|---|---|---|
| Functional suitability > functional correctness | QR-03 | QR-12 | — | — | CUJ-03, 04: no function computes a result |
| Performance efficiency > time behaviour | QR-02 | — | — | — | CUJ-02–04: no wait harms an outcome |
| Usability > operability | — | QR-04 | — | — | CUJ-01, 03, 04: one screen does the task |
| Reliability > availability | QR-01 | — | — | — | CUJ-02–04: no deadline rush |
| Reliability > fault tolerance | QR-06 | — | — | — | CUJ-02–04: they do not go through the external storage |
| Maintainability > analysability | — | — | QR-10 | — | CUJ-01, 02, 04: no developer steps |

### Data quality

| Characteristic | CUJ-01 | CUJ-02 | CUJ-03 | CUJ-04 | Reason not targeted |
|---|---|---|---|---|---|
| Completeness | QR-07 | — | — | QR-07 | CUJ-02, 03: they do not count submission records |
| Currentness | — | — | — | QR-08 | CUJ-01–03: they do not read the summary up to the previous day |

## Internal quality derived from external quality

| External QR | Internal QR | How it supports the external one |
|---|---|---|
| QR-01, QR-03 | QR-05 | Automated tests check submission and receipt processing, so broken changes do not reach production. |
