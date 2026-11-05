"""Resilient remote download of the dataset hosted on Hugging Face."""

from __future__ import annotations

import io
import re
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import httpx

REPOSITORY_ID = "SaisExperiments/Discord-Unveiled-Compressed"
METADATA_REMOTE_PATH = "server_metadata/servers_metadata.txt"
DATASET_REMOTE_PATH = "dataset.zst"
DOWNLOAD_HEADERS = {"Accept-Encoding": "identity"}
MAX_RETRIES = 5


def build_hf_url(remote_path: str) -> str:
    return (
        f"https://huggingface.co/datasets/{REPOSITORY_ID}/resolve/main/"
        f"{remote_path}?download=true"
    )


def parse_remote_total_bytes(response: httpx.Response) -> int | None:
    content_range = response.headers.get("content-range")
    if content_range:
        match = re.fullmatch(r"bytes \d+-\d+/(\d+|\*)", content_range.strip())
        if match is not None and match.group(1) != "*":
            return int(match.group(1))

    content_length = response.headers.get("content-length")
    return int(content_length) if content_length else None


def probe_remote_total_bytes(client: httpx.Client, url: str) -> int | None:
    try:
        with client.stream(
            "GET",
            url,
            headers={**DOWNLOAD_HEADERS, "Range": "bytes=0-0"},
        ) as response:
            response.raise_for_status()
            return parse_remote_total_bytes(response)
    except httpx.HTTPError:
        return None


def iter_resumable_remote_bytes(
    client: httpx.Client,
    url: str,
    *,
    chunk_size: int,
    max_retries: int = MAX_RETRIES,
    on_retry: Callable[[int, int], None] | None = None,
) -> Iterator[bytes]:
    """Yield sequential bytes and resume after transport failures."""
    downloaded_bytes = 0
    retry_count = 0

    while True:
        headers = dict(DOWNLOAD_HEADERS)
        if downloaded_bytes:
            headers["Range"] = f"bytes={downloaded_bytes}-"

        try:
            with client.stream("GET", url, headers=headers) as response:
                if not downloaded_bytes:
                    response.raise_for_status()
                else:
                    if response.status_code != httpx.codes.PARTIAL_CONTENT:
                        response.raise_for_status()
                        raise RuntimeError("The remote server refused to resume the download.")
                    content_range = response.headers.get("content-range")
                    if not content_range or not content_range.startswith(
                        f"bytes {downloaded_bytes}-"
                    ):
                        raise RuntimeError("The server returned an unexpected byte range.")

                for chunk in response.iter_raw(chunk_size=chunk_size):
                    if chunk:
                        downloaded_bytes += len(chunk)
                        yield chunk
                return
        except httpx.TransportError as error:
            retry_count += 1
            if retry_count > max_retries:
                raise RuntimeError(
                    "Download failed after all resume attempts."
                ) from error
            if on_retry is not None:
                on_retry(retry_count, downloaded_bytes)


def download_file(remote_path: str, output_path: Path, *, chunk_size: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    url = build_hf_url(remote_path)
    timeout = httpx.Timeout(connect=60.0, read=60.0, write=60.0, pool=60.0)
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        with output_path.open("wb") as target:
            for chunk in iter_resumable_remote_bytes(
                client,
                url,
                chunk_size=chunk_size,
            ):
                target.write(chunk)


class IteratorReader(io.RawIOBase):
    """Adapt a byte iterator for APIs expecting a binary file."""

    def __init__(
        self,
        iterator: Iterable[bytes],
        on_chunk: Callable[[int], None] | None = None,
    ) -> None:
        self._iterator = iter(iterator)
        self._buffer = bytearray()
        self._on_chunk = on_chunk

    def readable(self) -> bool:
        return True

    def readinto(self, target: bytearray) -> int:
        if self.closed:
            return 0
        target_view = memoryview(target)
        while len(self._buffer) < len(target_view):
            try:
                chunk = next(self._iterator)
            except StopIteration:
                break
            if not chunk:
                continue
            if self._on_chunk is not None:
                self._on_chunk(len(chunk))
            self._buffer.extend(chunk)

        output_size = min(len(target_view), len(self._buffer))
        if output_size:
            target_view[:output_size] = self._buffer[:output_size]
            del self._buffer[:output_size]
        return output_size
