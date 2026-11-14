# Requests to the quality chain

<!-- Written by scripts/tables.py from the requests in qcr/. Edit nothing but the answers: write an answer after "Answer:" under a request, and the next design run records it in the request. The fingerprints on the last line tell the script what was edited by hand. -->

The design chain never changes the quality chain (`docs/quality/`). When the design shows that a requirement should change, or that one it needs is missing, it writes a request; every request that is open or answered is here. Write an answer after "Answer:" under a request when you know it: the next design run records it. Then hand this document to the quality-chain stages listed under "What to do in each quality-chain stage", and re-run them. On their next run, the design stages follow what changed in `docs/quality/`, and drop the requests applied there.

## List

| QCR | Request | Chain items | Quality-chain stages | Impact | Status | Raised in |
|---|---|---|---|---|---|---|
| QCR-01 | What NFR-06 measures | NFR-06 | 4 | low | open | stage 3 |

## Requests and answers

### QCR-01 What NFR-06 measures

- Status: open · Raised in: stage 3
- Impact: low. Only one hop of the budget would change
- Chain items: NFR-06 · Quality-chain stages: 4
- Origin: IFC-01, IFC-03 · Items that depend on it: —
- Issue: NFR-06's 3 seconds do not say whether they include the PUT of the file to the storage
- Suggested change: Say that NFR-06's measured span leaves out the PUT to the storage

Answer: —

## What to do in each quality-chain stage

Re-run each stage below with this document. It applies the answers and decides with you the requests that have none; the later quality-chain stages follow its changes on their own re-run.

### Stage 4 (`product-quality-to-slo`)

- NFR-06: QCR-01 What NFR-06 measures (open)

<!-- fingerprints: rest 88e892bd18, QCR-01 2030a467c7 -->
