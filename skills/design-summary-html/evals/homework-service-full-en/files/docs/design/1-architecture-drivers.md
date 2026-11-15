# Architecture drivers: Homework submission service

Status: answers applied · Updated: 2026-09-15 · Inputs as of: none · Stage 1 of 4

## Summary

Four primary drivers (the deadline rush, receipts matching records, the external storage, fast confirmation). Feasible with this budget and team.

## Inputs
| Source | What it gave |
|---|---|
| docs/quality/ | Users, CUJs, FRs, QRs, NFRs, SLIs |
| User input (2026-09-15) | Technology and project constraints |

## Boundary and the outside
| Outside | Kind | Exchanges with the system through |
|---|---|---|
| USR-01 Students | User | Screens (FR-01, FR-02, FR-06) |
| USR-02 Teachers | User | Screens (FR-03, FR-05, FR-08) |
| EXT-01 External storage | External system | Files (FR-01) |

## Current structure

Built from scratch; there is no code yet.

## Design context
<!-- generated: design-context -->
| ID | Label | Kind | Source | Basis |
|---|---|---|---|---|
| TC-01 | TypeScript | mandated | User input | stated |
| TC-02 | External storage | external service | context.yaml EXT-01 | stated |
| TC-03 | The school's cloud | platform | User input, question 2 | confirmed |
| TC-04 | Web apps | platform | context.yaml DIN-01 | stated |
| PC-01 | Monthly cost | budget | User input | stated |
| PC-02 | New school year | deadline | User input | stated |
| PC-03 | Two developers | team | User input | stated |
| TEAM-01 | Development team | team structure | — | stated |
| CHG-01 | Parents' screens | anticipated change | User input | stated |
| STK-01 | Owner | stakeholder | User input | inferred |
<!-- /generated -->

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
<!-- generated: drivers -->
| DRV | Title | Kind | Negotiable | Sources | Premises | Basis |
|---|---|---|---|---|---|---|
| DRV-01 | Keep accepting submissions in the rush before a deadline | quality | — | QR-01, NFR-01, SLI-01, TC-02 | TC-02 | inferred |
| DRV-02 | Confirm submissions without keeping students waiting | quality | — | QR-02, NFR-06 | — | inferred |
| DRV-03 | Receipts match the submission records | quality | — | QR-03, QR-07, NFR-03, NFR-07 | — | inferred |
| DRV-04 | Screens for parents can be added | change | — | CHG-01 | CHG-01 | inferred |
| DRV-05 | Submitted files are kept in the external storage | constraint | no | TC-02 | TC-02 | inferred |
| DRV-06 | Built and run by two developers within 30,000 yen a month | constraint | no | PC-01, PC-03 | PC-01, PC-03 | inferred |
| DRV-07 | Trace a failed submission with one trace ID | observability | — | QR-10, FR-04, NFR-09 | — | inferred |
| DRV-08 | Protect students' answers and personal information | security | — | QR-09, NFR-08 | — | inferred |
| DRV-09 | Write the record before showing the receipt | principle | no | QR-07 | — | inferred |
<!-- /generated -->

## Ranking table
<!-- generated: ranking -->
| Rank | DRV | Business priority | Design difficulty | Primary |
|---|---|---|---|---|
| 1 | DRV-01 | high | high | yes |
| 2 | DRV-03 | high | medium | yes |
| 3 | DRV-05 | high | medium | yes |
| 4 | DRV-02 | medium | medium | yes |
| 5 | DRV-06 | high | low | no |
| 6 | DRV-04 | medium | low | no |
| 7 | DRV-07 | medium | low | no |
| 8 | DRV-08 | high | low | no |
<!-- /generated -->

The first four are primary.

## Conflicts
<!-- generated: conflicts -->
| Drivers | Resolved by |
|---|---|
| DRV-01, DRV-02 | Stage 2 (DEC-03) |
<!-- /generated -->

## Feasibility
| DRV | Known way with this budget, deadline and team | Why |
|---|---|---|
| DRV-01 | Yes | One server is enough if files do not pass through it |
| DRV-03 | Yes | Written in one transaction |
| DRV-05 | Yes | With ObjectStore's signed URLs |
| DRV-02 | Likely | Checked with the hop budgets of confirmation |

## Findings
<!-- generated: findings -->
| FND | Title | Severity | Raised by | To | Status | Items changed |
|---|---|---|---|---|---|---|
<!-- /generated -->

## Hand-offs
<!-- generated: handoffs -->
| HND | Title | From | To | Component | Status | Decided in |
|---|---|---|---|---|---|---|
| HND-01 | How fast the storage answers a PUT | requirements-to-architecture-drivers | architecture-to-high-level-design | — | decided | IFC-03 |
<!-- /generated -->

## Decisions
| # | Question | Answer | Items |
|---|---|---|---|
| 1 | The peak number of submissions before a deadline? | 300 a minute (as drafted) | DRV-01 |

## Open assumptions
<!-- generated: assumptions -->
| ID | Title | Kind | Breadth | Severity | Items that depend on it |
|---|---|---|---|---|---|
<!-- /generated -->

## Placeholders

None.

## Open gaps

None.

## Out of scope

The content of the parents' screens (CHG-01).

## Next

Run architecture-drivers-to-architecture.
