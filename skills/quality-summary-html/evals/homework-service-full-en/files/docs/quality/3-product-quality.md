# Product quality and data quality: Homework submission service

Updated: 2026-09-08

## Coverage checklist

### CUJ-01 Submit homework

| Model | Characteristic > sub-characteristic | Candidate (QR) or reason not targeted |
|---|---|---|
| Product | Reliability > availability | QR-01 |
| Data | Completeness | QR-07 |

Main data: submission records, submitted files, scores and comments, the monthly submission report.

Data producers: students (submitted files), teachers (scores and comments), and the external storage (stored files).

## Internal quality derived from external quality

| External QR | Internal QR | How it supports the external one |
|---|---|---|
| QR-01, QR-03 | QR-05 | Automated tests check submission and receipt processing, so broken changes do not reach production. |
