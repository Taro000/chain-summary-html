# Functional requirements: Homework submission service

Status: answers applied · Updated: 2026-09-03 · Inputs as of: 3f1c2ab · Stage 2 of 4

## Functions by CUJ step

| CUJ | Step | FRs | Note |
|---|---|---|---|
| CUJ-01 Submit homework | Open the assignment | | The current screen is enough |
| CUJ-01 | Attach a file | FR-06 | |
| CUJ-01 | Submit | FR-01, FR-02 | |
| CUJ-02 Grade and return | Open the submission | | |
| CUJ-02 | Grade | | |
| CUJ-02 | Return | FR-03, FR-08 | |
| CUJ-03 Investigate a failed submission | Get notified | | |
| CUJ-03 | Trace the logs | FR-04 | |
| CUJ-03 | Fix the cause | | Developers fix it outside the system |
| CUJ-04 Check monthly submissions | Open the report | FR-05 | |
| CUJ-04 | Find the students who have not submitted | | The office and the teachers read the report |

FR-09 acts across CUJs, so it is on no step.

## Quality-in-use coverage

| QIU | How it is covered | FRs | Note |
|---|---|---|---|
| QIU-01 Submission finishes by the deadline | an FR carries it as quality only | FR-01 | |
| QIU-01 | new function | FR-06, FR-09 | FR-06 comes from FRP-01 |
| QIU-02 Can confirm the submission | new function | FR-02 | |
| QIU-03 Returned within 3 days | an FR carries it as quality only | FR-03 | |
| QIU-04 Find the cause of a failure in 30 minutes | new function | FR-04 | |
| QIU-04 | data comes from elsewhere | | When the cause was found is counted from the developers' incident records |
| QIU-05 Monthly numbers match the submissions | an FR carries it as quality only | FR-05 | |
| QIU-05 | new function | FR-09 | |

## Functions considered and not added

| Candidate | For | Reason |
|---|---|---|
| Extend the deadline automatically | QIU-01 | Teachers set the deadlines (CON-01). |
| Share grading drafts | QIU-03 | Each teacher grades alone. |
