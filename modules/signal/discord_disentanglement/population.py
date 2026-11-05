from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from discord_filtering.storage import atomic_write_bytes, sha256_file
from discord_filtering.channel_selection import DEFAULT_OUTPUT as DEFAULT_SELECTION


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = DEFAULT_SELECTION / "messages.parquet"
DEFAULT_OUTPUT = ROOT / "data/processed/disentanglement/population_participants_v2"
REQUIRED_COLUMNS = {
    "guild_id", "guild_name", "channel_id", "channel_name", "message_id",
    "author_id", "timestamp", "is_bot", "message_type", "content",
    "attachment_count", "embed_count", "sticker_count", "referenced_message_id",
}


def characterize_population(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    memory_limit: str = "2GB",
) -> dict:
    source = Path(input_path).resolve()
    output = Path(output_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)
    filenames = [
        "channels.csv", "servers.csv", "temporal_activity.csv",
        "reply_distances.csv", "concentration.csv", "summary.json", "manifest.json",
    ]
    for filename in filenames:
        if (output / filename).exists():
            raise FileExistsError(f"output already exists: {output / filename}")

    with tempfile.TemporaryDirectory(prefix=".population-", dir=output) as temporary:
        with duckdb.connect(str(Path(temporary) / "analysis.duckdb")) as connection:
            connection.execute("SET memory_limit = ?", [memory_limit])
            connection.execute("SET TimeZone = 'UTC'")
            connection.execute("SET temp_directory = ?", [temporary])
            connection.execute("SET threads = 2")
            connection.execute("SET preserve_insertion_order = false")
            connection.from_parquet(str(source)).create_view("source")
            columns = {row[0] for row in connection.execute("DESCRIBE source").fetchall()}
            missing = REQUIRED_COLUMNS - columns
            if missing:
                raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
            reference_guild = (
                "nullif(trim(cast(referenced_guild_id AS VARCHAR)), '')"
                if "referenced_guild_id" in columns else "NULL::VARCHAR"
            )
            connection.execute(f"""
                CREATE TABLE normalized AS
                SELECT nullif(trim(cast(guild_id AS VARCHAR)), '') AS guild_id,
                       guild_name,
                       nullif(trim(cast(channel_id AS VARCHAR)), '') AS channel_id,
                       channel_name,
                       nullif(trim(cast(message_id AS VARCHAR)), '') AS message_id,
                       nullif(trim(cast(author_id AS VARCHAR)), '') AS author_id,
                       try_cast(timestamp AS TIMESTAMPTZ) AS sent_at,
                       is_bot, message_type,
                       nullif(trim(content), '') IS NULL AS empty_text,
                       coalesce(attachment_count, 0) + coalesce(embed_count, 0)
                           + coalesce(sticker_count, 0) > 0 AS has_media,
                       nullif(trim(cast(referenced_message_id AS VARCHAR)), '') AS parent_id,
                       {reference_guild} AS parent_guild_id
                FROM source
            """)
            connection.execute("""
                CREATE TABLE records AS
                WITH marked AS (
                    SELECT *, count(*) OVER (PARTITION BY guild_id, message_id) > 1
                        AND message_id IS NOT NULL AS duplicate_id
                    FROM normalized
                )
                  SELECT *, is_bot = false AND (NOT empty_text OR has_media) AS usable,
                      guild_id IS NOT NULL AND channel_id IS NOT NULL
                       AND message_id IS NOT NULL AND author_id IS NOT NULL
                       AND sent_at IS NOT NULL AND NOT duplicate_id
                      AS structurally_identifiable,
                       message_type = 19 AND parent_id IS NOT NULL AS native_reply
                FROM marked
            """)
            connection.execute("DROP TABLE normalized")
            connection.execute("""
                CREATE TABLE ordered AS
                SELECT *, row_number() OVER (
                    PARTITION BY guild_id, channel_id ORDER BY sent_at, message_id
                ) AS position,
                sum(cast(coalesce(usable, false) AS INTEGER)) OVER (
                    PARTITION BY guild_id, channel_id ORDER BY sent_at, message_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS usable_position
                FROM records
                WHERE guild_id IS NOT NULL AND channel_id IS NOT NULL
                  AND message_id IS NOT NULL AND sent_at IS NOT NULL AND NOT duplicate_id
            """)
            connection.execute("""
                CREATE TABLE replies AS
                SELECT child.guild_id, child.channel_id, child.author_id,
                       coalesce(child.usable, false) AS usable,
                       CASE WHEN parent.message_id IS NULL THEN 'parent_not_found'
                            WHEN parent.channel_id IS DISTINCT FROM child.channel_id
                                THEN 'different_channel'
                            WHEN parent.sent_at > child.sent_at OR parent.position >= child.position
                                THEN 'not_preceding'
                            ELSE 'resolved' END AS status,
                       child.position - parent.position AS position_distance,
                       epoch(child.sent_at - parent.sent_at) AS seconds_distance,
                       CASE WHEN child.usable AND parent.usable
                            THEN child.usable_position - parent.usable_position END
                            AS usable_position_distance
                FROM ordered child
                LEFT JOIN ordered parent ON parent.message_id = child.parent_id
                    AND parent.guild_id = coalesce(child.parent_guild_id, child.guild_id)
                WHERE child.native_reply
            """)

            metrics = """
                count(*) AS total_records,
                count(*) FILTER (WHERE is_bot = false) AS human_records,
                count(DISTINCT author_id) FILTER (WHERE is_bot = false) AS distinct_human_authors,
                count(DISTINCT author_id) FILTER (WHERE usable) AS distinct_usable_human_authors,
                count(*) FILTER (WHERE usable) AS usable_human_messages,
                count(*) FILTER (WHERE NOT empty_text OR has_media) AS usable_records,
                count(*) FILTER (WHERE empty_text AND NOT has_media) AS unusable_records,
                count(*) FILTER (WHERE usable AND NOT structurally_identifiable) AS human_messages_with_structural_issues,
                count(*) FILTER (WHERE usable AND sent_at IS NULL) AS usable_messages_without_valid_timestamp,
                count(*) FILTER (WHERE is_bot = true) AS bot_records,
                count(*) FILTER (WHERE is_bot IS NULL) AS unknown_bot_status,
                count(*) FILTER (WHERE message_id IS NULL) AS missing_message_id,
                count(*) FILTER (WHERE author_id IS NULL) AS missing_author_id,
                count(*) FILTER (WHERE guild_id IS NULL OR channel_id IS NULL) AS missing_scope,
                count(*) FILTER (WHERE sent_at IS NULL) AS missing_or_invalid_timestamp,
                count(*) FILTER (WHERE duplicate_id) AS duplicate_id_records,
                count(*) FILTER (WHERE empty_text) AS empty_text_records,
                count(*) FILTER (WHERE empty_text AND NOT has_media) AS missing_payload_records,
                count(*) FILTER (WHERE message_type IS NULL OR message_type NOT IN (0, 19)) AS other_or_unknown_type_records,
                count(*) FILTER (WHERE parent_id IS NOT NULL) AS reference_records,
                count(*) FILTER (WHERE native_reply) AS native_reply_records,
                count(*) FILTER (WHERE message_type = 19 AND parent_id IS NULL) AS replies_without_parent_id,
                count(*) FILTER (WHERE usable AND native_reply) AS usable_native_replies,
                count(*) FILTER (WHERE is_bot = true) * 1.0 / count(*) AS bot_ratio,
                count(*) FILTER (WHERE empty_text AND NOT has_media) * 1.0 / count(*) AS unusable_ratio,
                count(*) FILTER (WHERE native_reply) * 1.0 / count(*) AS native_reply_ratio_all,
                count(*) FILTER (WHERE usable AND native_reply) * 1.0 /
                    nullif(count(*) FILTER (WHERE usable), 0) AS native_reply_ratio_usable,
                cast(min(sent_at) AS VARCHAR) AS first_timestamp_utc,
                cast(max(sent_at) AS VARCHAR) AS last_timestamp_utc,
                cast(min(sent_at) FILTER (WHERE usable) AS VARCHAR) AS first_usable_timestamp_utc,
                cast(max(sent_at) FILTER (WHERE usable) AS VARCHAR) AS last_usable_timestamp_utc,
                count(DISTINCT cast(sent_at AS DATE)) AS active_days,
                count(DISTINCT cast(sent_at AS DATE)) FILTER (WHERE usable) AS usable_active_days
            """
            connection.execute(f"""
                CREATE TABLE channel_metrics AS
                SELECT guild_id, channel_id, min(guild_name) AS guild_name,
                       min(channel_name) AS channel_name, {metrics}
                FROM records GROUP BY guild_id, channel_id
            """)
            queries = {
                "channels.csv": "SELECT * FROM channel_metrics ORDER BY total_records DESC, guild_id, channel_id",
                "servers.csv": f"SELECT guild_id, min(guild_name) AS guild_name, count(DISTINCT channel_id) AS channels, {metrics} FROM records GROUP BY guild_id ORDER BY total_records DESC, guild_id",
                "temporal_activity.csv": """
                    SELECT guild_id, channel_id, 'month' AS temporal_unit,
                           strftime(sent_at, '%Y-%m') AS period_utc,
                           count(*) AS total_records,
                           count(*) FILTER (WHERE usable) AS usable_human_messages
                    FROM records WHERE sent_at IS NOT NULL GROUP BY guild_id, channel_id, period_utc
                    UNION ALL
                    SELECT guild_id, channel_id, 'weekday', cast(isodow(sent_at) AS VARCHAR),
                           count(*), count(*) FILTER (WHERE usable)
                    FROM records WHERE sent_at IS NOT NULL GROUP BY guild_id, channel_id, isodow(sent_at)
                    UNION ALL
                    SELECT guild_id, channel_id, 'hour', cast(hour(sent_at) AS VARCHAR),
                           count(*), count(*) FILTER (WHERE usable)
                    FROM records WHERE sent_at IS NOT NULL GROUP BY guild_id, channel_id, hour(sent_at)
                    ORDER BY guild_id, channel_id, temporal_unit, period_utc
                """,
                "reply_distances.csv": """
                    SELECT guild_id, channel_id, usable AS source_usable, status,
                           count(*) AS replies,
                           count(usable_position_distance) FILTER (WHERE status = 'resolved') AS usable_parent_pairs,
                           min(position_distance) FILTER (WHERE status = 'resolved') AS min_position_distance,
                           quantile_cont(position_distance, [0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
                               FILTER (WHERE status = 'resolved') AS position_quantiles,
                           max(position_distance) FILTER (WHERE status = 'resolved') AS max_position_distance,
                           quantile_cont(seconds_distance, [0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
                               FILTER (WHERE status = 'resolved') AS seconds_quantiles,
                           quantile_cont(usable_position_distance, [0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
                               FILTER (WHERE status = 'resolved') AS usable_position_quantiles,
                           count(*) FILTER (WHERE status = 'resolved' AND position_distance <= 10) AS within_10_records,
                           count(*) FILTER (WHERE status = 'resolved' AND position_distance <= 100) AS within_100_records,
                           count(*) FILTER (WHERE status = 'resolved' AND position_distance <= 200) AS within_200_records
                    FROM replies GROUP BY guild_id, channel_id, usable, status
                    ORDER BY guild_id, channel_id, usable, status
                """,
                "concentration.csv": """
                    WITH volumes AS (
                        SELECT 'channel' AS scope, guild_id, channel_id, 'all_records' AS population,
                               total_records AS messages FROM channel_metrics
                        UNION ALL
                        SELECT 'channel', guild_id, channel_id, 'usable_human', usable_human_messages FROM channel_metrics
                        UNION ALL
                        SELECT 'server', guild_id, NULL, 'all_records', sum(total_records) FROM channel_metrics GROUP BY guild_id
                        UNION ALL
                        SELECT 'server', guild_id, NULL, 'usable_human', sum(usable_human_messages) FROM channel_metrics GROUP BY guild_id
                    ), ranked AS (
                        SELECT *, row_number() OVER ordering AS volume_rank,
                               messages * 1.0 / nullif(sum(messages) OVER (PARTITION BY scope, population), 0) AS message_share,
                               sum(messages) OVER ordering * 1.0 /
                                   nullif(sum(messages) OVER (PARTITION BY scope, population), 0) AS cumulative_share
                        FROM volumes WINDOW ordering AS (
                            PARTITION BY scope, population ORDER BY messages DESC, guild_id, channel_id
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                    ) SELECT * FROM ranked ORDER BY scope, population, volume_rank
                """,
            }
            for filename, query in queries.items():
                target = str(Path(temporary) / filename).replace("'", "''")
                connection.execute(f"COPY ({query}) TO '{target}' (HEADER, DELIMITER ',')")
            cursor = connection.execute(f"SELECT {metrics} FROM records HAVING count(*) > 0")
            values = cursor.fetchone()
            summary = dict(zip([column[0] for column in cursor.description], values)) if values else {"total_records": 0}
            summary["reply_status_counts"] = [
                {"status": status, "replies": count}
                for status, count in connection.execute("SELECT status, count(*) FROM replies GROUP BY status ORDER BY status").fetchall()
            ]
            summary["native_replies_without_orderable_source"] = connection.execute("""
                SELECT coalesce(count(*) FILTER (WHERE native_reply), 0) - (SELECT count(*) FROM replies) FROM records
            """).fetchone()[0]
            concentration = connection.execute(f"SELECT * FROM ({queries['concentration.csv']})").fetchdf()
            summary["concentration_80_percent"] = []
            for (scope, population), group in concentration.groupby(["scope", "population"]):
                reached = group.loc[group["cumulative_share"] >= 0.8]
                summary["concentration_80_percent"].append({
                    "scope": scope, "population": population, "units": len(group),
                    "units_for_80_percent": int(reached.iloc[0]["volume_rank"]) if len(reached) else None,
                    "top_unit_share": float(group.iloc[0]["message_share"]) if group["messages"].sum() else None,
                })

        summary_payload = json.dumps(summary, default=str, indent=2, allow_nan=False).encode() + b"\n"
        atomic_write_bytes(Path(temporary) / "summary.json", summary_payload)
        source_manifest = source.with_name(f"{source.name}.manifest.json")
        manifest = {
            "manifest_schema_version": 1,
            "command": "characterize-population",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": [{"path": str(source), "sha256": sha256_file(source), "immutable_source": True}],
            "source_data_policy": "read_only_immutable",
            "implementation_sha256": sha256_file(Path(__file__)),
            "input_manifest_sha256": sha256_file(source_manifest) if source_manifest.exists() else None,
            "parameters": {"memory_limit": memory_limit, "timezone": "UTC", "threads": 2},
            "usability_definition_version": "payload_v2",
            "definitions": {
                "human": "is_bot is explicitly false; unknown status is not assumed human",
                "usable": "nonblank text or at least one recorded attachment/embed/sticker, regardless of message type or structural flags",
                "usable_human_messages": "is_bot is explicitly false and payload is present",
                "unusable_records": "empty/blank text with no recorded attachment, embed or sticker; the only unusability criterion",
                "human_messages_with_structural_issues": "human messages with payload but missing guild/channel/message/author ID, invalid timestamp or duplicate (guild_id,message_id); separate from unusability",
                "native_reply": "message_type=19 and nonempty referenced_message_id; other references are counted separately",
                "participants": "distinct nonblank author_id among messages with is_bot explicitly false, without requiring replies or mentions",
                "distance": "source minus parent: seconds and positions in valid uniquely identified timestamped channel records; separate usable-only positions for pairs of usable messages; UTC order then lexical message_id ties",
                "missing_parent": "not found among uniquely identified timestamped records in this export; not proof of deletion",
                "missing_payload": "empty/blank text with no attachment, embed or sticker; empty text alone is not unusable",
                "quality_counts": "overlapping descriptive flags; bots, structural issues and other message types do not imply absent payload or unusability",
                "temporal_activity": "observed nonzero buckets only; ISO weekday 1=Monday,7=Sunday; absent periods are not evidence of missing exports",
                "native_reply_absence": "unknown semantic response, not a negative label",
            },
            "outputs": [
                {"path": str(output / filename), "sha256": sha256_file(Path(temporary) / filename)}
                for filename in [*queries, "summary.json"]
            ],
        }
        for filename in queries:
            atomic_write_bytes(output / filename, (Path(temporary) / filename).read_bytes())
        atomic_write_bytes(output / "summary.json", summary_payload)
        atomic_write_bytes(output / "manifest.json", json.dumps(manifest, indent=2).encode() + b"\n")
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Characterize retained Discord channels before sampling windows.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--memory-limit", default="2GB")
    arguments = parser.parse_args(argv)
    summary = characterize_population(arguments.input, arguments.output, memory_limit=arguments.memory_limit)
    print(json.dumps(summary, default=str, indent=2))
    print(f"Reports: {arguments.output.resolve()}")


if __name__ == "__main__":
    main()