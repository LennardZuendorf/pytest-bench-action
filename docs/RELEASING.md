# Releasing pytest-bench-action

The mechanical steps are automated by [`.github/workflows/release.yml`](../.github/workflows/release.yml).
A release takes one workflow run plus two clicks.

## Prerequisites

- The release PR is merged to `main` and CI is green.
- `CHANGELOG.md`'s top section describes the version you're about to release.
- **First release only:** the publishing account has two-factor authentication
  enabled and has accepted the GitHub Marketplace Developer Agreement —
  otherwise the Marketplace checkbox on the release form is greyed out. The
  action name must also be unique on the Marketplace (`branding:` is already
  in `action.yml`).

## Steps

1. **Date the changelog.** Change the top heading from
   `## [X.Y.Z] — Unreleased` to `## [X.Y.Z] — YYYY-MM-DD` (commit to `main`).
   The workflow publishes this section verbatim as the release notes.

2. **Run the Release workflow.** Actions → *Release* → *Run workflow* →
   branch `main`, `version: vX.Y.Z` (e.g. `v1.0.0`). The workflow:
   - refuses to run from any ref other than `main`;
   - re-runs the unit tests and the end-to-end self-test as a release gate;
   - creates the annotated `vX.Y.Z` tag and force-moves the floating major tag
     (`v1`) to it — this is what makes `uses: ...@v1` track releases;
   - drafts a GitHub Release titled `vX.Y.Z` with the top CHANGELOG section as
     notes.

3. **Publish (manual, by design).** Open the draft Release:
   - tick **"Publish this Action to the GitHub Marketplace"**
     (category: **CI / Testing** — first release only; remembered afterwards);
   - click **Publish release**.

4. **Verify.**
   - Marketplace listing is live;
   - `uses: lennardzuendorf/pytest-bench-action@v1` resolves in a scratch repo
     workflow.

## Patch / minor releases

Same flow with the new `version`. The floating `v1` tag moves automatically;
consumers pinned to `@v1` pick the release up, consumers pinned to `@v1.0.0`
stay put. For a new major (`v2.0.0`), the workflow derives and moves `v2` —
never retarget `v1` to a breaking release.
