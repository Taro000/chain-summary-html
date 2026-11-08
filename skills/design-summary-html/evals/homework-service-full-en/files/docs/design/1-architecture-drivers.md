# Architecture drivers: Homework submission service

Status: answers applied · Updated: 2026-09-15 · Stage 1 of 4

## Summary

Four primary drivers (the deadline rush, receipts matching records, the external storage, fast confirmation). Feasible with this budget and team.

## Design inputs and stakeholders

| ID | Kind | Statement | Source | Basis |
|---|---|---|---|---|
| TC-01 | Technology constraint: Mandated | Written in TypeScript | User input | Stated |
| TC-02 | Technology constraint: External service | Submitted files are kept in an external storage service (ObjectStore) | context.yaml constraints | Stated |
| TC-03 | Technology constraint: Platform | Runs in one region of the school's existing cloud account | User input, question 2 | Confirmed |
| PC-01 | Budget | Within 30,000 yen a month | User input | Stated |
| PC-02 | Deadline | Release before the new school year (April) | User input | Stated |
| PC-03 | Team | Two developers; no dedicated operations engineer | User input | Stated |
| TEAM-01 | Team | Development team | — | Stated |
| CHG-01 | Anticipated change | Add screens for parents | User input | Stated |
| STK-01 | Stakeholder | The cram school's owner | User input | Inferred |

## Concern inventory

| Input item | Kind | Whose concern | Became |
|---|---|---|---|
| QR-01 | Quality | USR-01 | DRV-01 |
| QR-02 | Quality | USR-01 | DRV-02 |
| QR-03, QR-07 | Quality | USR-01, USR-04 | DRV-03 |
| QR-09 | Quality | USR-01 | DRV-08 |
| QR-10 | Quality | USR-03 | DRV-07 |
| TC-02 | Constraint | STK-01 | DRV-05 |
| PC-01, PC-03 | Constraint | STK-01 | DRV-06 |
| CHG-01 | Change | STK-01 | DRV-04 |
| QR-04 | Quality | USR-02 | set aside: excluded this cycle |

## Architecture drivers

### Quality and change scenarios

| DRV | Source | Stimulus | Artifact | Environment | Response | Measure | Basis |
|---|---|---|---|---|---|---|---|
| DRV-01 Keep accepting submissions in the rush before a deadline | Students (USR-01) | Submit in the hour before a deadline | FR-01 | The rush before a deadline (300 submissions a minute) | The submission is accepted and the receipt is shown | 99.5% of valid submissions succeed over a rolling 28 days (NFR-01) | Inferred |
| DRV-02 Confirm submissions without keeping students waiting | Students (USR-01) | Submit | FR-01, FR-02 | The rush before a deadline | The receipt is shown | The 95th percentile of submission confirmation is within 3 seconds (NFR-06) | Inferred |
| DRV-03 Receipts match the submission records | Students (USR-01) | Submit | FR-02 | Normal operation and the rush before a deadline | The receipt matches the record | No receipt without a record (NFR-07 version 2) | Inferred |
| DRV-04 Screens for parents can be added | Development team | Add the parents' screens | The web apps and the API | After release | Added without changing the existing screens and APIs | Within 4 weeks for two developers | Inferred |

### Constraints

| DRV | Constraint | Negotiable | Source | Basis |
|---|---|---|---|---|
| DRV-05 Submitted files are kept in the external storage | Submitted files go to the external storage (ObjectStore), never to our servers | Non-negotiable | TC-02 | Stated |
| DRV-06 Built and run by two developers within 30,000 yen a month | Two developers build and run it, for at most 30,000 yen a month | Non-negotiable | PC-01, PC-03 | Stated |
| DRV-10 (retired) | Merged into DRV-05 | — | — | — |

### Functional, observability and security drivers

| DRV | Kind | Statement | Sources | Basis |
|---|---|---|---|---|
| DRV-07 Trace a failed submission with one trace ID | Observability | A failed submission can be traced from the browser to the storage with one trace ID | QR-10, FR-04, NFR-09 | Inferred |
| DRV-08 Protect students' answers and personal information | Security | Only the student and their teacher can open a submission and its grade | QR-09, NFR-08 | Inferred |

### Principles

| DRV | Principle | Derived from | Basis |
|---|---|---|---|
| DRV-09 Write the record before showing the receipt | A submission shows its receipt only after its record is written, never before | DRV-03, DRV-01 | Inferred |

## Ranking table

| Rank | DRV | Business priority | Reason | Design difficulty | Reason | Primary |
|---|---|---|---|---|---|---|
| 1 | DRV-01 | High | QR-01 is emphasized (CUJ-01) | High | Submissions peak before deadlines and rely on the external storage | Yes |
| 2 | DRV-03 | High | QR-03 and QR-07 are emphasized (CUJ-01, 04) | Medium | The files and the records are kept in different places | Yes |
| 3 | DRV-05 | High | A non-negotiable constraint | Medium | A storage outage can stop submissions | Yes |
| 4 | DRV-02 | Medium | QR-02 is a minimum line | Medium | Writing the record first adds time (DRV-09) | Yes |
| 5 | DRV-06 | High | A non-negotiable constraint | Low | Met by keeping the structure small | No |
| 6 | DRV-04 | Medium | An anticipated change (CHG-01) | Low | Adding a role is expected to be enough | No |
| 7 | DRV-07 | Medium | QR-10 is a minimum line | Low | Consistent log fields are enough | No |
| 8 | DRV-08 | High | QR-09 is emphasized (a law) | Low | Checking the role and the class is enough | No |

The first four are primary.

## Conflicts

| Drivers | Conflict | Resolved by |
|---|---|---|
| DRV-01 and DRV-02 | Writing the record before the receipt slows the confirmation | Stage 2 |

## Feasibility

| Primary driver | Verdict |
|---|---|
| DRV-01 | Yes: one server is enough if files do not pass through it |
| DRV-03 | Yes: written in one transaction |
| DRV-05 | Yes: with ObjectStore's signed URLs |
| DRV-02 | Likely: checked with the hop budgets of confirmation |

## Questions and answers

| # | Question | Drafted answer | Answer | What changed |
|---|---|---|---|---|
| 1 | The peak number of submissions before a deadline? | 300 a minute | As drafted | Nothing |
