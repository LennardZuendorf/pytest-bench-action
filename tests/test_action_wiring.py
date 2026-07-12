"""Contract tests for action.yml wiring.

These guard the declarative glue that has no Python entry point but is exactly
where the two regression bugs lived: the node-mismatch skip path
(enforce-same-node) and the per-PR regression override (override-label). A full
check needs a GitHub runner; here we assert the wiring exists and stays
connected, so an accidental removal fails fast in unit CI.

action.yml is read as plain text (CI installs only pytest + pytest-benchmark,
so PyYAML is not importable here).
"""

import re
from pathlib import Path

import pytest

ACTION_YML = Path(__file__).resolve().parent.parent / "action.yml"


@pytest.fixture(scope="module")
def action_text() -> str:
    return ACTION_YML.read_text(encoding="utf-8")


class TestSanitizedTargetBranchOutput:
    def test_sanitized_target_branch_exported(self, action_text):
        assert "sanitized_target_branch=${SANITIZED_TARGET}" in action_text


class TestCheckoutRefForPRs:
    def test_checkout_uses_conditional_ref(self, action_text):
        assert (
            "ref: ${{ github.event_name == 'pull_request' && "
            "(github.event.pull_request.head.repo.full_name == github.repository && "
            "github.head_ref || github.event.pull_request.head.sha) || github.ref }}"
        ) in action_text


class TestCheckUpdateAgainstTargetBaseline:
    def _step_block(self, action_text):
        block = re.search(
            r"- name: Check whether baseline needs updating\n(?:.*\n)+?\n    - name:",
            action_text,
        )
        assert block, "step block not found"
        return block.group(0)

    def test_gated_on_pull_request(self, action_text):
        assert "if: github.event_name == 'pull_request'" in self._step_block(action_text)

    def test_compares_against_main_baseline_path(self, action_text):
        block = self._step_block(action_text)
        assert "steps.load-main-baseline.outputs.main_baseline_exists" in block
        assert "steps.load-main-baseline.outputs.main_baseline_path" in block


class TestNewInputs:
    def test_enforce_same_node_declared(self, action_text):
        assert re.search(r"^\s{2}enforce-same-node:$", action_text, re.MULTILINE)

    def test_enforce_same_node_defaults_to_false(self, action_text):
        # Opt-in safety: must default to hosted-runner-friendly skip, not fail.
        block = re.search(r"^\s{2}enforce-same-node:\n(?:\s{4}.*\n)+", action_text, re.MULTILINE)
        assert block and re.search(r'default:\s*"false"', block.group(0))

    def test_override_label_declared_with_default(self, action_text):
        block = re.search(r"^\s{2}override-label:\n(?:\s{4}.*\n)+", action_text, re.MULTILINE)
        assert block and re.search(r"default:\s*benchmark-override", block.group(0))


class TestNewOutputs:
    def test_comparison_skipped_output(self, action_text):
        assert re.search(r"^\s{2}comparison-skipped:$", action_text, re.MULTILINE)
        assert "steps.set-outputs.outputs.comparison-skipped" in action_text

    def test_regression_overridden_output(self, action_text):
        assert re.search(r"^\s{2}regression-overridden:$", action_text, re.MULTILINE)
        assert "steps.set-outputs.outputs.regression-overridden" in action_text


class TestNodeMismatchSkipPath:
    def test_both_compare_steps_handle_exit_3(self, action_text):
        # exit 3 (NODE_MISMATCH_EXIT) is branched on in each compare step.
        assert action_text.count('"$EXIT_CODE" -eq 3') == 2

    def test_skip_is_gated_on_enforce_same_node(self, action_text):
        assert '[ "${{ inputs.enforce-same-node }}" != "true" ]' in action_text

    def test_skip_emits_warning_and_sets_skip_flags(self, action_text):
        assert action_text.count("::warning::") >= 2
        assert "main_comparison_skipped=true" in action_text
        assert "prev_comparison_skipped=true" in action_text

    def test_skip_is_not_a_regression(self, action_text):
        # In the skip branch, regression must be forced false.
        skip_branch = re.search(r"-eq 3.*?main_comparison_skipped=true", action_text, re.DOTALL)
        assert skip_branch and "main_regression=false" in skip_branch.group(0)


class TestRegressionOverridePath:
    def test_override_reads_pr_labels(self, action_text):
        assert (
            "contains(github.event.pull_request.labels.*.name, inputs.override-label)"
            in action_text
        )

    def test_override_only_active_on_pull_request(self, action_text):
        assert "github.event_name == 'pull_request' && contains(" in action_text

    def test_fail_step_is_gated_on_override(self, action_text):
        # The final fail step must NOT fire when the regression is overridden.
        assert "steps.set-outputs.outputs.regression-detected == 'true'" in action_text
        assert "steps.set-outputs.outputs.regression-overridden != 'true'" in action_text

    def test_override_still_reports_but_does_not_fail(self, action_text):
        # Visible-but-non-blocking: the PR comment gets the override state.
        assert "REGRESSION_OVERRIDDEN:" in action_text
        assert "overridden" in action_text.lower()


class TestSinglePrComment:
    def test_dedup_marker_and_delete_then_create(self, action_text):
        # Exactly one comment per run: delete prior bot comment, then create.
        assert "## 📊 Performance Benchmark Results" in action_text
        assert "deleteComment" in action_text
        assert "createComment" in action_text
        # delete must come before create in the script.
        assert action_text.index("deleteComment") < action_text.index("createComment")
