"""Create DuckDB views for local exploratory analysis."""

from pathlib import Path

import duckdb


def create_database(
    *,
    messages_path: Path,
    servers_path: Path,
    channels_path: Path | None,
    database_path: Path,
    overwrite: bool = False,
) -> list[str]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists() and not overwrite:
        raise FileExistsError(f"Database already exists: {database_path}")
    if database_path.exists():
        database_path.unlink()

    views = ["software_servers", "software_messages", "server_message_stats"]
    with duckdb.connect(str(database_path)) as connection:
        messages = str(messages_path.resolve()).replace("\\", "/")
        servers = str(servers_path.resolve()).replace("\\", "/")
        connection.execute(
            f"CREATE VIEW software_servers AS SELECT * FROM read_parquet('{servers}')"
        )
        connection.execute(
            f"CREATE VIEW software_messages AS SELECT * FROM read_parquet('{messages}')"
        )
        connection.execute(
            """
            CREATE VIEW server_message_stats AS
            SELECT guild_id, guild_name, COUNT(*) AS message_count,
                   COUNT(DISTINCT author_id) AS unique_authors,
                   MIN(timestamp) AS first_message_at, MAX(timestamp) AS last_message_at
            FROM software_messages
            GROUP BY 1, 2
            """
        )
        if channels_path is not None and channels_path.exists():
            channels = str(channels_path.resolve()).replace("\\", "/")
            connection.execute(
                f"CREATE VIEW software_channels AS SELECT * FROM read_parquet('{channels}')"
            )
            views.append("software_channels")
    return views
