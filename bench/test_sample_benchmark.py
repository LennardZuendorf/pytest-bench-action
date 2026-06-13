"""Sample pytest-benchmark suite used to dogfood pytest-bench-action.

These benchmarks exist purely to exercise the action's pipeline end-to-end
against real ``pytest-benchmark`` JSON output. Targets are stdlib-only,
deterministic, and fast so the suite runs on any runner in well under a second.

Run with:
    pytest bench/ --benchmark-only --benchmark-json=benchmark-results.json -q
"""


def _sum_range(n: int) -> int:
    return sum(range(n))


def _sort_list(values: list[int]) -> list[int]:
    return sorted(values)


def _str_join(parts: list[str]) -> str:
    return "-".join(parts)


def test_sum_range(benchmark):
    result = benchmark(_sum_range, 10_000)
    assert result == 49_995_000


def test_sort_list(benchmark):
    data = list(range(2_000, 0, -1))
    result = benchmark(_sort_list, data)
    assert result[0] == 1
    assert result[-1] == 2_000


def test_str_join(benchmark):
    parts = [str(i) for i in range(500)]
    result = benchmark(_str_join, parts)
    assert result.startswith("0-1-2")
