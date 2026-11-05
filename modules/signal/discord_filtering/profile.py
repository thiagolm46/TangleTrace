from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

from .models import (
    ChannelClassificationPolicy,
    ChannelPolicy,
    ComponentWeights,
    ConversationSuitabilityPolicy,
    ContentSignal,
    EvidenceConfirmationPolicy,
    FilterProfile,
    ServerPolicy,
    ServerSelectionPolicy,
    WeightedRule,
)


class ProfileValidationError(ValueError):
    """Raised when a filtering profile is ambiguous or internally inconsistent."""


def _fail(path: str, message: str) -> NoReturn:
    raise ProfileValidationError(f"{path}: {message}")


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "expected a JSON object")
    return value


def _exact_keys(value: Mapping[str, Any], required: set[str], path: str) -> None:
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required)
    if missing:
        _fail(path, f"missing keys: {', '.join(missing)}")
    if unknown:
        _fail(path, f"unknown keys: {', '.join(unknown)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "expected a non-empty string")
    return value.strip()


def _identifier(value: Any, path: str) -> str:
    result = _string(value, path)
    if re.fullmatch(r"[a-z][a-z0-9_.-]*", result) is None:
        _fail(path, "must match [a-z][a-z0-9_.-]*")
    return result


def _number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "expected a number")
    result = float(value)
    if not math.isfinite(result):
        _fail(path, "must be finite")
    if minimum is not None and result < minimum:
        _fail(path, f"must be >= {minimum}")
    return result


def _ratio(value: Any, path: str, *, allow_zero: bool = True) -> float:
    result = _number(value, path, minimum=0.0)
    if result > 1.0 or (not allow_zero and result == 0.0):
        qualifier = "(0, 1]" if not allow_zero else "[0, 1]"
        _fail(path, f"must be in {qualifier}")
    return result


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(path, "expected an integer")
    if value < minimum:
        _fail(path, f"must be >= {minimum}")
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(path, "expected a boolean")
    return value


def _string_tuple(value: Any, path: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        _fail(path, "expected an array of strings")
    result = tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))
    if not allow_empty and not result:
        _fail(path, "must not be empty")
    if len(set(result)) != len(result):
        _fail(path, "must not contain duplicates")
    return result


def _compile_pattern(pattern: str, path: str) -> None:
    try:
        re.compile(pattern, re.IGNORECASE | re.UNICODE)
    except re.error as error:
        _fail(path, f"invalid regular expression ({error})")


def _weighted_rules(value: Any, path: str) -> tuple[WeightedRule, ...]:
    if not isinstance(value, list) or not value:
        _fail(path, "expected a non-empty array")
    rules: list[WeightedRule] = []
    ids: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _object(raw, item_path)
        _exact_keys(item, {"id", "label", "pattern", "weight", "group"}, item_path)
        rule_id = _identifier(item["id"], f"{item_path}.id")
        if rule_id in ids:
            _fail(f"{item_path}.id", f"duplicate rule id '{rule_id}'")
        ids.add(rule_id)
        pattern = _string(item["pattern"], f"{item_path}.pattern")
        _compile_pattern(pattern, f"{item_path}.pattern")
        rules.append(
            WeightedRule(
                rule_id=rule_id,
                label=_string(item["label"], f"{item_path}.label"),
                pattern=pattern,
                weight=_number(item["weight"], f"{item_path}.weight", minimum=0.000001),
                group=_identifier(item["group"], f"{item_path}.group"),
            )
        )
    return tuple(rules)


def _signals(value: Any, path: str) -> tuple[ContentSignal, ...]:
    if not isinstance(value, list) or not value:
        _fail(path, "expected a non-empty array")
    required = {
        "id",
        "label",
        "pattern",
        "count_field",
        "lexical_weight",
        "lexical_saturation_ratio",
        "domain_weight",
        "domain_saturation_ratio",
    }
    signals: list[ContentSignal] = []
    ids: set[str] = set()
    count_fields: set[str] = set()
    for index, raw in enumerate(value):
        item_path = f"{path}[{index}]"
        item = _object(raw, item_path)
        _exact_keys(item, required, item_path)
        signal_id = _identifier(item["id"], f"{item_path}.id")
        count_field = _identifier(item["count_field"], f"{item_path}.count_field")
        if signal_id in ids:
            _fail(f"{item_path}.id", f"duplicate signal id '{signal_id}'")
        if count_field in count_fields:
            _fail(f"{item_path}.count_field", f"duplicate count field '{count_field}'")
        ids.add(signal_id)
        count_fields.add(count_field)
        pattern = _string(item["pattern"], f"{item_path}.pattern")
        _compile_pattern(pattern, f"{item_path}.pattern")
        lexical_weight = _ratio(item["lexical_weight"], f"{item_path}.lexical_weight")
        domain_weight = _ratio(item["domain_weight"], f"{item_path}.domain_weight")
        lexical_saturation = _ratio(
            item["lexical_saturation_ratio"],
            f"{item_path}.lexical_saturation_ratio",
            allow_zero=False,
        )
        domain_saturation = _ratio(
            item["domain_saturation_ratio"],
            f"{item_path}.domain_saturation_ratio",
            allow_zero=False,
        )
        signals.append(
            ContentSignal(
                signal_id=signal_id,
                label=_string(item["label"], f"{item_path}.label"),
                pattern=pattern,
                count_field=count_field,
                lexical_weight=lexical_weight,
                lexical_saturation_ratio=lexical_saturation,
                domain_weight=domain_weight,
                domain_saturation_ratio=domain_saturation,
            )
        )
    return tuple(signals)


def _validate_weight_sum(values: list[float], path: str) -> None:
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-9):
        _fail(path, f"weights must sum to 1.0 (got {sum(values):.12g})")


def _server_scoring_policy(raw: Mapping[str, Any]) -> ServerPolicy:
    server_raw = _object(raw, "$profile.server")
    _exact_keys(
        server_raw,
        {
            "fields",
            "field_weights",
            "positive_rules",
            "negative_rules",
            "overlap_policy",
            "confirmation",
            "positive_score_field",
            "negative_score_field",
            "affinity_score_field",
        },
        "$profile.server",
    )
    overlap = _string(server_raw["overlap_policy"], "$profile.server.overlap_policy")
    if overlap != "max_per_group":
        _fail("$profile.server.overlap_policy", "only 'max_per_group' is supported")
    fields = _string_tuple(server_raw["fields"], "$profile.server.fields")
    field_weights_raw = _object(server_raw["field_weights"], "$profile.server.field_weights")
    if set(field_weights_raw) != set(fields):
        _fail("$profile.server.field_weights", "must define exactly the configured server fields")
    confirmation_raw = _object(server_raw["confirmation"], "$profile.server.confirmation")
    _exact_keys(
        confirmation_raw,
        {"bonus_per_additional_field", "max_bonus_per_group"},
        "$profile.server.confirmation",
    )
    score_fields = {
        "positive": _identifier(
            server_raw["positive_score_field"],
            "$profile.server.positive_score_field",
        ),
        "negative": _identifier(
            server_raw["negative_score_field"],
            "$profile.server.negative_score_field",
        ),
        "affinity": _identifier(
            server_raw["affinity_score_field"],
            "$profile.server.affinity_score_field",
        ),
    }
    if len(set(score_fields.values())) != len(score_fields):
        _fail("$profile.server", "score field aliases must be distinct")
    return ServerPolicy(
        fields=fields,
        field_weights={
            field: _number(
                field_weights_raw[field],
                f"$profile.server.field_weights.{field}",
                minimum=0.0,
            )
            for field in fields
        },
        positive_rules=_weighted_rules(server_raw["positive_rules"], "$profile.server.positive_rules"),
        negative_rules=_weighted_rules(server_raw["negative_rules"], "$profile.server.negative_rules"),
        overlap_policy=overlap,
        selection=None,
        confirmation=EvidenceConfirmationPolicy(
            bonus_per_additional_field=_number(
                confirmation_raw["bonus_per_additional_field"],
                "$profile.server.confirmation.bonus_per_additional_field",
                minimum=0.0,
            ),
            max_bonus_per_group=_number(
                confirmation_raw["max_bonus_per_group"],
                "$profile.server.confirmation.max_bonus_per_group",
                minimum=0.0,
            ),
        ),
        positive_score_field=score_fields["positive"],
        negative_score_field=score_fields["negative"],
        affinity_score_field=score_fields["affinity"],
    )


def profile_from_dict(raw: Mapping[str, Any]) -> FilterProfile:
    """Build an immutable profile from already parsed JSON with strict validation."""

    root = _object(dict(raw), "$profile")
    schema_version = _integer(root.get("schema_version"), "$profile.schema_version", minimum=1)
    if schema_version == 2:
        _exact_keys(
            root,
            {"schema_version", "profile_id", "profile_version", "domain", "description", "server"},
            "$profile",
        )
        return FilterProfile(
            schema_version=schema_version,
            profile_id=_identifier(root["profile_id"], "$profile.profile_id"),
            profile_version=_string(root["profile_version"], "$profile.profile_version"),
            domain=_identifier(root["domain"], "$profile.domain"),
            description=_string(root["description"], "$profile.description"),
            server=_server_scoring_policy(root["server"]),
            channel=None,
        )
    if schema_version != 1:
        _fail("$profile.schema_version", f"unsupported version {schema_version}; expected 1 or 2")
    _exact_keys(
        root,
        {"schema_version", "profile_id", "profile_version", "domain", "description", "server", "channel"},
        "$profile",
    )

    server_raw = _object(root["server"], "$profile.server")
    _exact_keys(
        server_raw,
        {"fields", "field_weights", "positive_rules", "negative_rules", "overlap_policy", "selection"},
        "$profile.server",
    )
    overlap = _string(server_raw["overlap_policy"], "$profile.server.overlap_policy")
    if overlap != "max_per_group":
        _fail("$profile.server.overlap_policy", "only 'max_per_group' is supported")
    server_positive = _weighted_rules(server_raw["positive_rules"], "$profile.server.positive_rules")
    server_negative = _weighted_rules(server_raw["negative_rules"], "$profile.server.negative_rules")
    server_fields = _string_tuple(server_raw["fields"], "$profile.server.fields")
    field_weights_raw = _object(server_raw["field_weights"], "$profile.server.field_weights")
    if set(field_weights_raw) != set(server_fields):
        _fail("$profile.server.field_weights", "must define exactly the configured server fields")
    field_weights = {
        field: _number(field_weights_raw[field], f"$profile.server.field_weights.{field}", minimum=0.0)
        for field in server_fields
    }
    selection_raw = _object(server_raw["selection"], "$profile.server.selection")
    _exact_keys(
        selection_raw,
        {
            "min_positive_score",
            "min_score_margin",
            "max_negative_score",
            "blocked_negative_labels",
            "required_positive_labels",
        },
        "$profile.server.selection",
    )
    max_negative_raw = selection_raw["max_negative_score"]
    max_negative = (
        None
        if max_negative_raw is None
        else _number(max_negative_raw, "$profile.server.selection.max_negative_score", minimum=0.0)
    )
    blocked_labels = _string_tuple(
        selection_raw["blocked_negative_labels"],
        "$profile.server.selection.blocked_negative_labels",
        allow_empty=True,
    )
    known_server_negative_labels = {rule.label for rule in server_negative}
    unknown_blocked = sorted(set(blocked_labels) - known_server_negative_labels)
    if unknown_blocked:
        _fail(
            "$profile.server.selection.blocked_negative_labels",
            f"unknown negative labels: {', '.join(unknown_blocked)}",
        )
    required_positive_labels = _string_tuple(
        selection_raw["required_positive_labels"],
        "$profile.server.selection.required_positive_labels",
        allow_empty=True,
    )
    known_server_positive_labels = {rule.label for rule in server_positive}
    unknown_required = sorted(set(required_positive_labels) - known_server_positive_labels)
    if unknown_required:
        _fail(
            "$profile.server.selection.required_positive_labels",
            f"unknown positive labels: {', '.join(unknown_required)}",
        )
    server_policy = ServerPolicy(
        fields=server_fields,
        field_weights=field_weights,
        positive_rules=server_positive,
        negative_rules=server_negative,
        overlap_policy=overlap,
        selection=ServerSelectionPolicy(
            min_positive_score=_number(
                selection_raw["min_positive_score"],
                "$profile.server.selection.min_positive_score",
                minimum=0.0,
            ),
            min_score_margin=_number(
                selection_raw["min_score_margin"],
                "$profile.server.selection.min_score_margin",
                minimum=0.0,
            ),
            max_negative_score=max_negative,
            blocked_negative_labels=blocked_labels,
            required_positive_labels=required_positive_labels,
        ),
    )

    channel_raw = _object(root["channel"], "$profile.channel")
    _exact_keys(
        channel_raw,
        {
            "metadata_fields",
            "positive_rules",
            "negative_rules",
            "overlap_policy",
            "metadata_normalization",
            "signals",
            "component_weights",
            "classification",
            "conversation_suitability",
            "exclude_bot_messages",
            "max_evidence_examples",
            "score_field",
            "domain_score_field",
        },
        "$profile.channel",
    )
    channel_overlap = _string(channel_raw["overlap_policy"], "$profile.channel.overlap_policy")
    if channel_overlap != "max_per_group":
        _fail("$profile.channel.overlap_policy", "only 'max_per_group' is supported")
    channel_positive = _weighted_rules(channel_raw["positive_rules"], "$profile.channel.positive_rules")
    channel_negative = _weighted_rules(channel_raw["negative_rules"], "$profile.channel.negative_rules")
    signals = _signals(channel_raw["signals"], "$profile.channel.signals")
    _validate_weight_sum(
        [signal.lexical_weight for signal in signals],
        "$profile.channel.signals[*].lexical_weight",
    )
    _validate_weight_sum(
        [signal.domain_weight for signal in signals],
        "$profile.channel.signals[*].domain_weight",
    )

    weights_raw = _object(channel_raw["component_weights"], "$profile.channel.component_weights")
    _exact_keys(weights_raw, {"metadata", "lexical", "domain"}, "$profile.channel.component_weights")
    component_weights = ComponentWeights(
        metadata=_ratio(weights_raw["metadata"], "$profile.channel.component_weights.metadata"),
        lexical=_ratio(weights_raw["lexical"], "$profile.channel.component_weights.lexical"),
        domain=_ratio(weights_raw["domain"], "$profile.channel.component_weights.domain"),
    )
    _validate_weight_sum(
        [component_weights.metadata, component_weights.lexical, component_weights.domain],
        "$profile.channel.component_weights",
    )

    classification_raw = _object(channel_raw["classification"], "$profile.channel.classification")
    classification_keys = {
        "high_confidence_score",
        "review_score",
        "high_min_lexical_score",
        "fallback_min_lexical_score",
        "fallback_min_domain_score",
        "admin_max_lexical_score",
        "admin_max_domain_score",
        "social_max_lexical_score",
        "admin_negative_labels",
        "social_negative_labels",
        "class_high",
        "class_review",
        "class_social",
        "class_admin",
        "include_classes",
        "manual_review_classes",
    }
    _exact_keys(classification_raw, classification_keys, "$profile.channel.classification")
    high_score = _ratio(
        classification_raw["high_confidence_score"],
        "$profile.channel.classification.high_confidence_score",
    )
    review_score = _ratio(
        classification_raw["review_score"],
        "$profile.channel.classification.review_score",
    )
    if review_score > high_score:
        _fail("$profile.channel.classification", "review_score must not exceed high_confidence_score")
    admin_labels = _string_tuple(
        classification_raw["admin_negative_labels"],
        "$profile.channel.classification.admin_negative_labels",
        allow_empty=True,
    )
    social_labels = _string_tuple(
        classification_raw["social_negative_labels"],
        "$profile.channel.classification.social_negative_labels",
        allow_empty=True,
    )
    known_channel_negative_labels = {rule.label for rule in channel_negative}
    unknown_class_labels = sorted((set(admin_labels) | set(social_labels)) - known_channel_negative_labels)
    if unknown_class_labels:
        _fail(
            "$profile.channel.classification",
            f"unknown channel negative labels: {', '.join(unknown_class_labels)}",
        )
    class_names = {
        key: _string(classification_raw[key], f"$profile.channel.classification.{key}")
        for key in ("class_high", "class_review", "class_social", "class_admin")
    }
    if len(set(class_names.values())) != 4:
        _fail("$profile.channel.classification", "class labels must be distinct")
    allowed_classes = set(class_names.values())
    include_classes = _string_tuple(
        classification_raw["include_classes"],
        "$profile.channel.classification.include_classes",
        allow_empty=True,
    )
    manual_review_classes = _string_tuple(
        classification_raw["manual_review_classes"],
        "$profile.channel.classification.manual_review_classes",
        allow_empty=True,
    )
    unknown_result_classes = sorted((set(include_classes) | set(manual_review_classes)) - allowed_classes)
    if unknown_result_classes:
        _fail(
            "$profile.channel.classification",
            f"unknown result classes: {', '.join(unknown_result_classes)}",
        )
    classification = ChannelClassificationPolicy(
        high_confidence_score=high_score,
        review_score=review_score,
        high_min_lexical_score=_ratio(
            classification_raw["high_min_lexical_score"],
            "$profile.channel.classification.high_min_lexical_score",
        ),
        fallback_min_lexical_score=_ratio(
            classification_raw["fallback_min_lexical_score"],
            "$profile.channel.classification.fallback_min_lexical_score",
        ),
        fallback_min_domain_score=_ratio(
            classification_raw["fallback_min_domain_score"],
            "$profile.channel.classification.fallback_min_domain_score",
        ),
        admin_max_lexical_score=_ratio(
            classification_raw["admin_max_lexical_score"],
            "$profile.channel.classification.admin_max_lexical_score",
        ),
        admin_max_domain_score=_ratio(
            classification_raw["admin_max_domain_score"],
            "$profile.channel.classification.admin_max_domain_score",
        ),
        social_max_lexical_score=_ratio(
            classification_raw["social_max_lexical_score"],
            "$profile.channel.classification.social_max_lexical_score",
        ),
        admin_negative_labels=admin_labels,
        social_negative_labels=social_labels,
        class_high=class_names["class_high"],
        class_review=class_names["class_review"],
        class_social=class_names["class_social"],
        class_admin=class_names["class_admin"],
        include_classes=include_classes,
        manual_review_classes=manual_review_classes,
    )
    conversation_raw = _object(
        channel_raw["conversation_suitability"],
        "$profile.channel.conversation_suitability",
    )
    _exact_keys(
        conversation_raw,
        {
            "min_human_users",
            "min_interaction_ratio",
            "min_author_transition_ratio",
            "max_dominant_author_ratio",
            "max_bot_message_ratio",
        },
        "$profile.channel.conversation_suitability",
    )
    conversation_suitability = ConversationSuitabilityPolicy(
        min_human_users=_integer(
            conversation_raw["min_human_users"],
            "$profile.channel.conversation_suitability.min_human_users",
            minimum=1,
        ),
        min_interaction_ratio=_ratio(
            conversation_raw["min_interaction_ratio"],
            "$profile.channel.conversation_suitability.min_interaction_ratio",
            allow_zero=False,
        ),
        min_author_transition_ratio=_ratio(
            conversation_raw["min_author_transition_ratio"],
            "$profile.channel.conversation_suitability.min_author_transition_ratio",
            allow_zero=False,
        ),
        max_dominant_author_ratio=_ratio(
            conversation_raw["max_dominant_author_ratio"],
            "$profile.channel.conversation_suitability.max_dominant_author_ratio",
            allow_zero=False,
        ),
        max_bot_message_ratio=_ratio(
            conversation_raw["max_bot_message_ratio"],
            "$profile.channel.conversation_suitability.max_bot_message_ratio",
            allow_zero=False,
        ),
    )
    channel_policy = ChannelPolicy(
        metadata_fields=_string_tuple(channel_raw["metadata_fields"], "$profile.channel.metadata_fields"),
        positive_rules=channel_positive,
        negative_rules=channel_negative,
        overlap_policy=channel_overlap,
        metadata_normalization=_number(
            channel_raw["metadata_normalization"],
            "$profile.channel.metadata_normalization",
            minimum=0.000001,
        ),
        signals=signals,
        component_weights=component_weights,
        classification=classification,
        conversation_suitability=conversation_suitability,
        exclude_bot_messages=_boolean(
            channel_raw["exclude_bot_messages"],
            "$profile.channel.exclude_bot_messages",
        ),
        max_evidence_examples=_integer(
            channel_raw["max_evidence_examples"],
            "$profile.channel.max_evidence_examples",
            minimum=0,
        ),
        score_field=_identifier(channel_raw["score_field"], "$profile.channel.score_field"),
        domain_score_field=_identifier(
            channel_raw["domain_score_field"],
            "$profile.channel.domain_score_field",
        ),
    )

    return FilterProfile(
        schema_version=schema_version,
        profile_id=_identifier(root["profile_id"], "$profile.profile_id"),
        profile_version=_string(root["profile_version"], "$profile.profile_version"),
        domain=_identifier(root["domain"], "$profile.domain"),
        description=_string(root["description"], "$profile.description"),
        server=server_policy,
        channel=channel_policy,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProfileValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_profile(path: str | Path) -> FilterProfile:
    """Load a versioned filtering profile using only Python's JSON library."""

    profile_path = Path(path)
    try:
        with profile_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise ProfileValidationError(
            f"{profile_path}: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    except OSError as error:
        raise ProfileValidationError(f"cannot read profile {profile_path}: {error}") from error
    if not isinstance(raw, dict):
        raise ProfileValidationError(f"{profile_path}: profile root must be a JSON object")
    return profile_from_dict(raw)
