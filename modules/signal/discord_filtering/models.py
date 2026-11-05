from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


def compact_json(value: Any) -> str:
    """Serialize audit fields deterministically for JSON/Parquet compatibility."""

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True, slots=True)
class WeightedRule:
    rule_id: str
    label: str
    pattern: str
    weight: float
    group: str


@dataclass(frozen=True, slots=True)
class ServerSelectionPolicy:
    min_positive_score: float
    min_score_margin: float
    max_negative_score: float | None
    blocked_negative_labels: tuple[str, ...]
    required_positive_labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceConfirmationPolicy:
    bonus_per_additional_field: float
    max_bonus_per_group: float


@dataclass(frozen=True, slots=True)
class ServerPolicy:
    fields: tuple[str, ...]
    field_weights: dict[str, float]
    positive_rules: tuple[WeightedRule, ...]
    negative_rules: tuple[WeightedRule, ...]
    overlap_policy: str
    selection: ServerSelectionPolicy | None
    confirmation: EvidenceConfirmationPolicy | None = None
    positive_score_field: str = "positive_score"
    negative_score_field: str = "negative_score"
    affinity_score_field: str = "score_margin"


@dataclass(frozen=True, slots=True)
class ContentSignal:
    signal_id: str
    label: str
    pattern: str
    count_field: str
    lexical_weight: float
    lexical_saturation_ratio: float
    domain_weight: float
    domain_saturation_ratio: float


@dataclass(frozen=True, slots=True)
class ComponentWeights:
    metadata: float
    lexical: float
    domain: float


@dataclass(frozen=True, slots=True)
class ChannelClassificationPolicy:
    high_confidence_score: float
    review_score: float
    high_min_lexical_score: float
    fallback_min_lexical_score: float
    fallback_min_domain_score: float
    admin_max_lexical_score: float
    admin_max_domain_score: float
    social_max_lexical_score: float
    admin_negative_labels: tuple[str, ...]
    social_negative_labels: tuple[str, ...]
    class_high: str
    class_review: str
    class_social: str
    class_admin: str
    include_classes: tuple[str, ...]
    manual_review_classes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConversationSuitabilityPolicy:
    min_human_users: int
    min_interaction_ratio: float
    min_author_transition_ratio: float
    max_dominant_author_ratio: float
    max_bot_message_ratio: float


@dataclass(frozen=True, slots=True)
class ChannelPolicy:
    metadata_fields: tuple[str, ...]
    positive_rules: tuple[WeightedRule, ...]
    negative_rules: tuple[WeightedRule, ...]
    overlap_policy: str
    metadata_normalization: float
    signals: tuple[ContentSignal, ...]
    component_weights: ComponentWeights
    classification: ChannelClassificationPolicy
    conversation_suitability: ConversationSuitabilityPolicy
    exclude_bot_messages: bool
    max_evidence_examples: int
    score_field: str
    domain_score_field: str


@dataclass(frozen=True, slots=True)
class FilterProfile:
    schema_version: int
    profile_id: str
    profile_version: str
    domain: str
    description: str
    server: ServerPolicy
    channel: ChannelPolicy | None


@dataclass(frozen=True, slots=True)
class RuleEvidence:
    rule_id: str
    label: str
    group: str
    field: str
    value_index: int
    matched_text: str
    start: int
    end: int
    weight: float
    credited_weight: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "label": self.label,
            "group": self.group,
            "field": self.field,
            "value_index": self.value_index,
            "matched_text": self.matched_text,
            "span": [self.start, self.end],
            "weight": self.weight,
            "credited_weight": self.credited_weight,
        }


@dataclass(frozen=True, slots=True)
class SignalEvidence:
    signal_id: str
    field: str
    record_id: str | None
    matched_text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "field": self.field,
            "record_id": self.record_id,
            "matched_text": self.matched_text,
        }


@dataclass(frozen=True, slots=True)
class SignalScore:
    signal_id: str
    label: str
    count_field: str
    count: int
    lexical_contribution: float
    domain_contribution: float
    evidence: tuple[SignalEvidence, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "label": self.label,
            "count_field": self.count_field,
            "count": self.count,
            "lexical_contribution": self.lexical_contribution,
            "domain_contribution": self.domain_contribution,
            "evidence": [item.as_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class ServerClassification:
    profile_id: str
    profile_version: str
    domain: str
    guild_id: str
    slug: str | None
    name: str | None
    description: str | None
    about: str | None
    reasons_to_join: tuple[str, ...]
    preferred_locale: str | None
    primary_category_id: str | None
    approximate_member_count: int | None
    approximate_presence_count: int | None
    vanity_url_code: str | None
    keywords: tuple[str, ...]
    positive_score: float
    negative_score: float
    score_margin: float
    positive_score_field: str
    negative_score_field: str
    affinity_score_field: str
    metadata_available: dict[str, bool]
    metadata_completeness: float
    positive_groups: tuple[str, ...]
    negative_groups: tuple[str, ...]
    positive_group_scores: dict[str, float]
    negative_group_scores: dict[str, float]
    positive_evidence: tuple[RuleEvidence, ...]
    negative_evidence: tuple[RuleEvidence, ...]
    blocked_negative_terms: tuple[str, ...]
    is_selected: bool | None

    def to_record(self) -> dict[str, Any]:
        positive_terms = list(dict.fromkeys(item.label for item in self.positive_evidence))
        negative_terms = list(dict.fromkeys(item.label for item in self.negative_evidence))
        evidence_by_field: dict[str, list[dict[str, Any]]] = {}
        for polarity, evidence in (
            ("positive", self.positive_evidence),
            ("negative", self.negative_evidence),
        ):
            for item in evidence:
                detail = item.as_dict()
                detail["polarity"] = polarity
                evidence_by_field.setdefault(item.field, []).append(detail)

        record = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "domain": self.domain,
            "guild_id": self.guild_id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "about": self.about,
            "reasons_to_join_json": compact_json(list(self.reasons_to_join)),
            "preferred_locale": self.preferred_locale,
            "primary_category_id": self.primary_category_id,
            "approximate_member_count": self.approximate_member_count,
            "approximate_presence_count": self.approximate_presence_count,
            "vanity_url_code": self.vanity_url_code,
            "keywords_json": compact_json(list(self.keywords)),
            "positive_score": self.positive_score,
            "negative_score": self.negative_score,
            "score_margin": self.score_margin,
            "metadata_available_json": compact_json(self.metadata_available),
            "metadata_completeness": self.metadata_completeness,
            "positive_group_count": len(self.positive_groups),
            "negative_group_count": len(self.negative_groups),
            "positive_groups": compact_json(list(self.positive_groups)),
            "negative_groups": compact_json(list(self.negative_groups)),
            "positive_group_scores": compact_json(self.positive_group_scores),
            "negative_group_scores": compact_json(self.negative_group_scores),
            "matched_positive_terms": compact_json(positive_terms),
            "matched_negative_terms": compact_json(negative_terms),
            "blocked_negative_terms": compact_json(list(self.blocked_negative_terms)),
            "server_evidence_json": compact_json(evidence_by_field),
            "is_selected": self.is_selected,
        }
        record[self.positive_score_field] = self.positive_score
        record[self.negative_score_field] = self.negative_score
        record[self.affinity_score_field] = self.score_margin
        return record


@dataclass(frozen=True, slots=True)
class ChannelClassification:
    profile_id: str
    profile_version: str
    domain: str
    guild_id: str
    guild_name: str | None
    channel_id: str
    channel_name: str | None
    n_messages: int
    n_users: int
    n_bot_messages: int
    total_messages: int
    interaction_message_count: int
    valid_native_reply_message_count: int
    mention_interaction_message_count: int
    interaction_ratio: float
    author_transition_ratio: float
    dominant_author_ratio: float
    bot_message_ratio: float
    conversation_score: float
    conversation_suitable: bool
    conversation_exclusion_reasons: tuple[str, ...]
    metadata_positive_score: float
    metadata_negative_score: float
    metadata_score: float
    lexical_evidence_score: float
    domain_evidence_score: float
    channel_score: float
    channel_class: str
    include_in_main_analysis: bool
    manual_review_required: bool
    positive_evidence: tuple[RuleEvidence, ...]
    negative_evidence: tuple[RuleEvidence, ...]
    signal_scores: tuple[SignalScore, ...]
    score_field: str
    domain_score_field: str

    def to_record(self) -> dict[str, Any]:
        positive_terms = list(dict.fromkeys(item.label for item in self.positive_evidence))
        negative_terms = list(dict.fromkeys(item.label for item in self.negative_evidence))
        metadata_evidence: dict[str, list[dict[str, Any]]] = {}
        for polarity, evidence in (
            ("positive", self.positive_evidence),
            ("negative", self.negative_evidence),
        ):
            for item in evidence:
                detail = item.as_dict()
                detail["polarity"] = polarity
                metadata_evidence.setdefault(item.field, []).append(detail)

        signal_records = [signal.as_dict() for signal in self.signal_scores]
        record: dict[str, Any] = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "domain": self.domain,
            "guild_id": self.guild_id,
            "guild_name": self.guild_name,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "n_messages": self.n_messages,
            "n_users": self.n_users,
            "n_bot_messages": self.n_bot_messages,
            "total_messages": self.total_messages,
            "interaction_message_count": self.interaction_message_count,
            "valid_native_reply_message_count": self.valid_native_reply_message_count,
            "mention_interaction_message_count": self.mention_interaction_message_count,
            "interaction_ratio": self.interaction_ratio,
            "author_transition_ratio": self.author_transition_ratio,
            "dominant_author_ratio": self.dominant_author_ratio,
            "bot_message_ratio": self.bot_message_ratio,
            "conversation_score": self.conversation_score,
            "conversation_suitable": self.conversation_suitable,
            "conversation_exclusion_reasons": compact_json(
                list(self.conversation_exclusion_reasons)
            ),
            "metadata_positive_score": self.metadata_positive_score,
            "metadata_negative_score": self.metadata_negative_score,
            "metadata_score": self.metadata_score,
            "matched_channel_positive_terms": compact_json(positive_terms),
            "matched_channel_negative_terms": compact_json(negative_terms),
            "channel_metadata_evidence_json": compact_json(metadata_evidence),
            "signal_evidence_json": compact_json(signal_records),
            "lexical_evidence_score": self.lexical_evidence_score,
            "domain_evidence_score": self.domain_evidence_score,
            "channel_score": self.channel_score,
            "channel_class": self.channel_class,
            "include_in_main_analysis": self.include_in_main_analysis,
            "manual_review_required": self.manual_review_required,
        }
        # Profile-defined aliases preserve the vocabulary of existing exports
        # (for example software_channel_score and oss_evidence_score) while the
        # engine remains domain-neutral.
        record[self.score_field] = self.channel_score
        record[self.domain_score_field] = self.domain_evidence_score
        for signal in self.signal_scores:
            record[signal.count_field] = signal.count
        return record
