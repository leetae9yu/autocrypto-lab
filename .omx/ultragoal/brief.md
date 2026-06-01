# Ultragoal Brief: Autocrypto Lab

Implement the approved RALPLAN PRD and test-spec:

- `.omx/plans/prd-crypto-quant-research-pipeline.md`
- `.omx/plans/test-spec-crypto-quant-research-pipeline.md`
- requirements source: `.omx/specs/deep-interview-crypto-quant-research-pipeline.md`

Hard constraints:

- Commit per implementation story is mandatory.
- No live order endpoints in v1.
- Public/free data first.
- Minimum cadence is 1h; no sub-hour scalping.
- Config-only autonomy through DSL/registries; autonomous loop must not mutate Python runtime code.
- Every autonomous loop decision must be ledgered with rationale and evidence.
- Final output must be pushed to `https://github.com/leetae9yu/autocrypto-lab`.

Use the PRD's G001-G013 story order and final test-spec quality gate.
