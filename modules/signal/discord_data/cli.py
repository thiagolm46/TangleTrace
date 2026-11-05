"""Command-line interface for data acquisition and extraction."""

from __future__ import annotations

import tarfile
from pathlib import Path

import httpx
import typer
import zstandard as zstd
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TaskProgressColumn, TextColumn

from .database import create_database
from .extraction import (
    compile_channel_filters,
    ensure_new_output,
    extract_archive,
    load_selected_servers,
)
from .remote import (
    DATASET_REMOTE_PATH,
    METADATA_REMOTE_PATH,
    IteratorReader,
    build_hf_url,
    download_file,
    iter_resumable_remote_bytes,
    probe_remote_total_bytes,
)

console = Console()
app = typer.Typer(
    add_completion=False,
    help="TangleTrace SIGNAL: acquisition, extraction and local database for the Discord Unveiled corpus.",
)


def _render(path: Path) -> str:
    return str(path.resolve())


def _print_stats(stats: dict[str, int], output_path: Path) -> None:
    console.print(f"[green]Servers processed:[/green] {stats['servers']:,}")
    console.print(f"[green]Messages written:[/green] {stats['messages']:,}")
    if stats["skipped_channels"]:
        console.print(
            "[green]Messages removed by channel filters:[/green] "
            f"{stats['skipped_channels']:,}"
        )
    if stats["invalid_json"]:
        console.print(
            f"[yellow]Invalid JSON lines skipped:[/yellow] {stats['invalid_json']:,}"
        )
    console.print(f"[green]Parquet:[/green] {_render(output_path)}")


@app.command("download-metadata")
def download_metadata(
    output_path: Path = typer.Option(
        Path("data/raw/server_metadata/servers_metadata.txt"),
        help="Destination for server metadata.",
    ),
) -> None:
    download_file(METADATA_REMOTE_PATH, output_path, chunk_size=8 * 1024 * 1024)
    console.print(f"[green]Metadata saved to:[/green] {_render(output_path)}")


@app.command("download-dataset")
def download_dataset(
    output_path: Path = typer.Option(
        Path("data/raw/dataset.zst"), help="Destination for the complete dataset."
    ),
) -> None:
    console.print("[yellow]The complete archive is approximately 118 GB.[/yellow]")
    download_file(DATASET_REMOTE_PATH, output_path, chunk_size=8 * 1024 * 1024)
    console.print(f"[green]Dataset saved to:[/green] {_render(output_path)}")


@app.command("extract-local")
def extract_local(
    dataset_path: Path = typer.Option(
        Path("data/raw/dataset.zst"), exists=True, dir_okay=False
    ),
    selected_servers_path: Path = typer.Option(
        ..., exists=True, dir_okay=False, help="Auditable selected-server Parquet."
    ),
    output_path: Path = typer.Option(..., help="New message Parquet."),
    exclude_bots: bool = typer.Option(True),
    batch_size: int = typer.Option(50_000, min=1_000),
    include_channel_regex: list[str] | None = typer.Option(None, "--include-channel-regex"),
    exclude_channel_regex: list[str] | None = typer.Option(None, "--exclude-channel-regex"),
) -> None:
    try:
        ensure_new_output(output_path)
        guild_lookup, _ = load_selected_servers(selected_servers_path)
        include, exclude = compile_channel_filters(
            include_channel_regex or [], exclude_channel_regex or []
        )
        with dataset_path.open("rb") as compressed:
            with zstd.ZstdDecompressor().stream_reader(compressed) as stream:
                with tarfile.open(fileobj=stream, mode="r|") as archive:
                    stats = extract_archive(
                        archive,
                        guild_lookup=guild_lookup,
                        output_path=output_path,
                        exclude_bots=exclude_bots,
                        batch_size=batch_size,
                        include_channel_patterns=include,
                        exclude_channel_patterns=exclude,
                    )
    except (FileExistsError, OSError, RuntimeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_stats(stats, output_path)


@app.command("extract-remote")
def extract_remote(
    selected_servers_path: Path = typer.Option(
        ..., exists=True, dir_okay=False, help="Auditable selected-server Parquet."
    ),
    output_path: Path = typer.Option(..., help="New message Parquet."),
    remote_path: str = typer.Option(DATASET_REMOTE_PATH),
    exclude_bots: bool = typer.Option(True),
    batch_size: int = typer.Option(50_000, min=1_000),
    download_chunk_mb: int = typer.Option(8, min=1, max=64),
    include_channel_regex: list[str] | None = typer.Option(None, "--include-channel-regex"),
    exclude_channel_regex: list[str] | None = typer.Option(None, "--exclude-channel-regex"),
) -> None:
    try:
        ensure_new_output(output_path)
        guild_lookup, _ = load_selected_servers(selected_servers_path)
        include, exclude = compile_channel_filters(
            include_channel_regex or [], exclude_channel_regex or []
        )
    except (FileExistsError, OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error

    url = build_hf_url(remote_path)
    timeout = httpx.Timeout(connect=60.0, read=60.0, write=60.0, pool=60.0)
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            total = probe_remote_total_bytes(client, url)
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                DownloadColumn(binary_units=True),
                console=console,
            ) as progress:
                download_task = progress.add_task("Download and decompression", total=total)
                server_task = progress.add_task("Servers", total=len(guild_lookup))
                byte_iterator = iter_resumable_remote_bytes(
                    client,
                    url,
                    chunk_size=download_chunk_mb * 1024 * 1024,
                    on_retry=lambda attempt, offset: console.print(
                        f"[yellow]Resume attempt {attempt} after {offset:,} bytes.[/yellow]"
                    ),
                )
                reader = IteratorReader(
                    byte_iterator,
                    on_chunk=lambda size: progress.update(download_task, advance=size),
                )
                with zstd.ZstdDecompressor().stream_reader(reader) as stream:
                    with tarfile.open(fileobj=stream, mode="r|") as archive:
                        stats = extract_archive(
                            archive,
                            guild_lookup=guild_lookup,
                            output_path=output_path,
                            exclude_bots=exclude_bots,
                            batch_size=batch_size,
                            include_channel_patterns=include,
                            exclude_channel_patterns=exclude,
                            on_server=lambda guild_id: progress.update(
                                server_task, advance=1, description=f"Server {guild_id}"
                            ),
                        )
    except (OSError, RuntimeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_stats(stats, output_path)


@app.command("init-duckdb")
def init_duckdb(
    messages_path: Path = typer.Option(..., exists=True, dir_okay=False),
    servers_path: Path = typer.Option(..., exists=True, dir_okay=False),
    channels_path: Path | None = typer.Option(None, dir_okay=False),
    database_path: Path = typer.Option(Path("data/duckdb/discord_unveiled.duckdb")),
    overwrite: bool = typer.Option(False),
) -> None:
    try:
        views = create_database(
            messages_path=messages_path,
            servers_path=servers_path,
            channels_path=channels_path,
            database_path=database_path,
            overwrite=overwrite,
        )
    except (FileExistsError, OSError, RuntimeError) as error:
        raise typer.BadParameter(str(error)) from error
    console.print(f"[green]DuckDB created at:[/green] {_render(database_path)}")
    console.print("[green]Views:[/green] " + ", ".join(views))


def main() -> None:
    app()
