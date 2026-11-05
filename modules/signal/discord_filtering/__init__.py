"""Profile-driven, auditable Discord server/channel filtering.

The public functions are pure: callers supply records, messages and a validated
profile, and receive immutable result objects. File I/O is isolated in the CLI
and storage modules so source datasets (especially validated Parquet corpora)
remain immutable.
"""

from .engine import classify_server, normalize_keywords, score_channel
from .models import ChannelClassification, FilterProfile, ServerClassification
from .profile import ProfileValidationError, load_profile, profile_from_dict
from .service import (
    ChannelScoringRun,
    ServerFilteringRun,
    filter_servers,
    score_channels,
    write_channel_scoring_run,
    write_server_filtering_run,
)

__all__ = [
    "ChannelClassification",
    "ChannelScoringRun",
    "FilterProfile",
    "ProfileValidationError",
    "ServerClassification",
    "ServerFilteringRun",
    "classify_server",
    "filter_servers",
    "load_profile",
    "normalize_keywords",
    "profile_from_dict",
    "score_channel",
    "score_channels",
    "write_channel_scoring_run",
    "write_server_filtering_run",
]
