import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from chunk_common import Block, MediaCollector, check_dispositions, manifest_media

MEDIA = [{"id": "media-0001"}, {"id": "media-0002"}]
READ = {"id": "media-0001", "disposition": "read", "tool": "vision", "summary": "a chart"}
NOT_READ = {"id": "media-0002", "disposition": "not_read", "reason": "decorative"}


@pytest.mark.parametrize(
    ("dispositions", "code", "detail"),
    [
        pytest.param([READ], "media.disposition.missing", "media-0002", id="missing"),
        pytest.param([READ, NOT_READ, {**NOT_READ, "id": "media-0009"}], "media.disposition.unknown", "media-0009", id="unknown"),
        pytest.param([READ, NOT_READ, dict(READ)], "media.disposition.duplicate", "media-0001", id="duplicate"),
        pytest.param([READ, {**NOT_READ, "reason": " "}], "media.disposition.invalid", "media-0002", id="invalid-reason"),
        pytest.param([{**READ, "summary": ""}, NOT_READ], "media.disposition.invalid", "media-0001", id="invalid-read"),
        pytest.param([{**READ, "tool": ""}, NOT_READ], "media.disposition.invalid", "media-0001", id="invalid-read-empty-tool"),
        pytest.param([{**READ, "tool": " "}, NOT_READ], "media.disposition.invalid", "media-0001", id="invalid-read-blank-tool"),
        pytest.param(
            [{k: v for k, v in READ.items() if k != "tool"}, NOT_READ],
            "media.disposition.invalid",
            "media-0001",
            id="invalid-read-missing-tool",
        ),
        pytest.param([READ, {**NOT_READ, "disposition": "skipped"}], "media.disposition.invalid", "media-0002", id="invalid-value"),
        pytest.param([READ, NOT_READ, "text"], "media.disposition.invalid", "media[2]", id="invalid-not-object"),
        pytest.param({"media-0001": READ}, "media.disposition.invalid", "media", id="invalid-not-list"),
        pytest.param([READ, NOT_READ, {"disposition": "read"}], "media.disposition.unknown", "media[2]", id="no-id"),
    ],
)
def test_check_dispositions_reports_each_problem_with_its_code(dispositions, code, detail):
    problems = check_dispositions(MEDIA, dispositions)
    assert [(item[0], item[2]) for item in problems] == [(code, detail)]


def test_complete_dispositions_pass_and_no_media_needs_none():
    assert check_dispositions(MEDIA, [READ, NOT_READ]) == []
    assert check_dispositions([], []) == []


def test_dispositions_against_a_manifest_without_media_are_unknown():
    problems = check_dispositions([], [READ])
    assert [(item[0], item[2]) for item in problems] == [("media.disposition.unknown", "media-0001")]


def test_manifest_media_is_empty_when_absent():
    assert manifest_media({"chunks": []}) == []
    assert manifest_media({"media": MEDIA}) == MEDIA


@pytest.mark.parametrize(
    ("texts", "positions", "expected"),
    [
        (["a", "b", "c"], [1], {1: [1]}),
        (["a", "b", "c"], [3, 9], {2: [3, 9]}),
        (["a", "", "", "d", ""], [1, 2, 3], {3: [1, 2, 3]}),
        (["a", "", "c"], [0, 1, 2], {0: [0], 2: [1, 2]}),
        (["a", "b", ""], [2], {1: [2]}),
    ],
)
def test_apply_attaches_each_reference_to_the_next_textual_block_or_the_last(
    texts, positions, expected
):
    blocks = [Block(text, {}) for text in texts]
    collector = MediaCollector()
    for position in positions:
        collector.add(position, "image", "markdown", ref=str(position))
    collector.apply(blocks)
    attached = {
        index: [int(entry["ref"]) for entry in block.locator["media"]]
        for index, block in enumerate(blocks)
        if "media" in block.locator
    }
    assert attached == expected


def test_apply_stays_fast_for_sixty_thousand_blocks_and_references():
    count = 60_000
    blocks = [Block("t", {}) for _ in range(count)]
    collector = MediaCollector()
    for position in range(count):
        collector.add(position, "image", "markdown", ref=str(position))
    started = time.perf_counter()
    collector.apply(blocks)
    assert time.perf_counter() - started < 2
    assert all(len(block.locator["media"]) == 1 for block in blocks)
