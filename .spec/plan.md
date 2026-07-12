---
type: entrypoint
scope: implementation
covers: current focus, release status, downstream follow-up
children: []
updated: 2026-07-11
---

# pytest-bench-action — Implementation Plan

**Parent specs:** [product.md](product.md), [tech.md](tech.md)

Current-only roadmap. Delivered work is a one-line note, not a task list — code
is the source of truth (see [tech.md](tech.md) Implementation Map).

---

## Status

- **Core action** — shipped. Composite `action.yml` (20 steps): baseline
  save/load/list, dual comparison, deduplicated PR comment, `[skip ci]`
  auto-commit, artifact upload, `threshold-map`.
- **Tests + dogfood** — shipped. `tests/` (unit + real-output + action-wiring),
  `scripts/selftest.sh`, `bench/`, `.github/workflows/{ci,benchmark}.yml`.
- **Release automation** — shipped. `.github/workflows/release.yml` +
  `docs/RELEASING.md` (manual, test-gated, floating-major tag).
- **Regression-bug fixes (2026-07-11, this branch):**
  - Hardware-fingerprint gate — comparability is keyed on the CPU/system
    fingerprint (`cpu.brand_raw` + arch + cores + system), not the hostname, so
    hosted runners compare on the same CPU model instead of skipping every run
    (falls back to `node` when no `cpu` block). `enforce-same-node` (default
    `"false"`) skips a genuine hardware mismatch with a `::warning::` or
    hard-fails when `"true"`; `benchmark_compare.py` signals it with exit code
    `3` so "cannot compare" is never conflated with "regressed" (`1`).
  - `override-label` input — a per-PR waiver for an accepted regression (still
    reported, non-blocking). New outputs: `comparison-skipped`,
    `regression-overridden`.

---

## Decided (durable)

- **Composite action, no Docker.** Python stdlib only in `scripts/`.
- **Baselines in-repo.** Git-committed, versioned, auditable. No external state.
- **Never compare across machines; gate on hardware, not hostname.** Comparability
  is keyed on a CPU/system fingerprint, so hosted runners compare on the same CPU;
  a cross-machine comparison is never emitted, and `enforce-same-node` chooses fail
  vs skip-with-warning. *(Supersedes the earlier hostname-based hard-fail — the
  hostname is randomized per hosted job, which broke the feature there.)*
- **Accepted regressions waived per-PR, not repo-wide** via `override-label`.
- **`[skip ci]` on baseline commits.** Prevents infinite CI loops — non-negotiable.
- **Dual tolerance inputs.** `cross-branch-tolerance` (20%) gates both regression
  comparisons; `update-tolerance` (5%) only triggers baseline updates.

---

## Open — v1 release + Marketplace (human-gated)

The release is cut by the human-gated Release workflow (needs 2FA + the
Marketplace Developer Agreement); it cannot be automated from a branch. See
[RELEASING.md](../docs/RELEASING.md).

- [ ] **Human:** date the top `CHANGELOG.md` section, then run Actions →
  *Release* from `main` with `version: vX.Y.Z` → creates `vX.Y.Z` + floating
  `v1` and drafts the Release.
- [ ] **Human:** publish the draft Release; tick "Publish this Action to the
  GitHub Marketplace"; category CI / Testing.
- [ ] **Human:** verify `uses: lennardzuendorf/pytest-bench-action@v1` resolves.

> Docs pin `@v1` — the floating-major tag the Release workflow creates. The only
> tag that currently exists is the pre-release `v0.0.1`, which predates these
> features, so docs are intentionally **not** repointed to it. `@v1` resolves
> once the human release runs.

---

## Downstream follow-up (not in this repo)

After the new tag ships, the `indexed` consumer must: bump its
`pytest-bench-action` pin, set `enforce-same-node` (`"false"` hosted /
`"true"` self-hosted), use the `benchmark-override` label to waive a known
regression, and resolve its `.spec/tech.md` Open Technical Question #7. **Do not
edit `indexed` from this repo.**

---

## Spec layout

Root layer only: `product.md`, `tech.md`, `plan.md`, `lessons.md`. The
`features/` folders were collapsed into root once shipped (cross-cutting
decisions promoted to root; code is truth) — no feature-scoped specs remain.
