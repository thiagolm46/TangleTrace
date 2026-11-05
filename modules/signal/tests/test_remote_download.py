from __future__ import annotations

from collections.abc import Iterator
import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from discord_data.remote import iter_resumable_remote_bytes, probe_remote_total_bytes


class StaticByteStream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes], error: Exception | None = None) -> None:
        self._chunks = chunks
        self._error = error

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self._chunks:
            yield chunk
        if self._error is not None:
            raise self._error


def test_probe_remote_total_bytes_reads_content_range() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Range") == "bytes=0-0"
        return httpx.Response(
            206,
            headers={"Content-Range": "bytes 0-0/11"},
            stream=StaticByteStream([b"h"]),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert probe_remote_total_bytes(client, "https://example.test/file") == 11


def test_iter_resumable_remote_bytes_retries_from_last_offset() -> None:
    payload = b"hello world"
    requests: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        range_header = request.headers.get("Range")
        requests.append(range_header)

        if range_header is None:
            return httpx.Response(
                200,
                headers={"Content-Length": str(len(payload))},
                stream=StaticByteStream(
                    [payload[:5]],
                    error=httpx.RemoteProtocolError("peer closed connection"),
                ),
            )

        if range_header == "bytes=3-":
            return httpx.Response(
                206,
                headers={"Content-Range": f"bytes 3-{len(payload) - 1}/{len(payload)}"},
                stream=StaticByteStream([payload[3:]]),
            )

        raise AssertionError(f"unexpected range header: {range_header}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        received = b"".join(
            iter_resumable_remote_bytes(
                client,
                "https://example.test/file",
                chunk_size=3,
                max_retries=1,
            )
        )

    assert received == payload
    assert requests == [None, "bytes=3-"]


def test_iter_resumable_remote_bytes_does_not_retry_http_status_errors() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(404, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            next(
                iter(
                    iter_resumable_remote_bytes(
                        client,
                        "https://example.test/missing",
                        chunk_size=3,
                        max_retries=3,
                    )
                )
            )

    assert call_count == 1
