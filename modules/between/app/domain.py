"""Rules independent of HTTP, SQLite, and the frontend. Edges: reply -> antecedent."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

STATUSES = {"pending", "complete", "no_reply", "outside_context", "ambiguous", "new_conversation"}
CONFIDENCES = {"high", "medium", "low"}


class Invalid(ValueError):
    pass


class Conflict(Invalid):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def signature(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def empty_decision():
    return {"source_status": "pending", "edges": [], "notes": "", "confidence": "high",
            "unresolved_additional_relation": False, "unresolved_reason": ""}


def validate_decision(messages, source_id, data):
    by_id = {m["message_id"]: m for m in messages}
    source = by_id.get(source_id)
    if not source or not source["requires_reply_annotation"]:
        raise Invalid("The source must be a target message in this window.")
    status = data.get("source_status")
    if status not in STATUSES:
        raise Invalid("Invalid decision status.")
    confidence = data.get("confidence", "high")
    if confidence not in CONFIDENCES:
        raise Invalid("Invalid confidence value.")
    edges, seen = [], set()
    if not isinstance(data.get("edges", []), list):
        raise Invalid("Links must be provided as a list.")
    for edge in data.get("edges", []):
        target_id = edge.get("target_message_id")
        target = by_id.get(target_id)
        if not target:
            raise Invalid("The antecedent must be visible in this window.")
        if target["sequence"] >= source["sequence"]:
            raise Invalid("The antecedent must occur strictly before the source.")
        if (target["channel_id"], target["guild_id"]) != (source["channel_id"], source["guild_id"]):
            raise Invalid("A link cannot cross channels or servers.")
        if target_id in seen:
            raise Invalid("Duplicate link.")
        if edge.get("relation", "reply") != "reply":
            raise Invalid("The relation must be reply.")
        ambiguous = edge.get("ambiguous", False)
        if not isinstance(ambiguous, bool):
            raise Invalid("The link ambiguity value must be boolean.")
        edge_confidence = edge.get("confidence", confidence)
        if edge_confidence not in CONFIDENCES:
            raise Invalid("Invalid link confidence value.")
        edges.append({"target_message_id": target_id, "relation": "reply", "ambiguous": ambiguous,
                      "confidence": edge_confidence, "notes": str(edge.get("notes", ""))})
        seen.add(target_id)
    if edges and status != "complete":
        raise Invalid("Decisions with links require status complete. Remove the links or keep this status.")
    edges.sort(key=lambda e: by_id[e["target_message_id"]]["sequence"])
    return {"source_status": status, "edges": edges, "notes": str(data.get("notes", "")),
            "confidence": confidence,
            "unresolved_additional_relation": bool(data.get("unresolved_additional_relation", False)),
            "unresolved_reason": str(data.get("unresolved_reason", ""))}


def derive(messages, decisions):
    """Same connectivity and IDs as annotation_bundle.py, isolated by session/window."""
    by_id = {m["message_id"]: m for m in messages}
    parent, edges = {}, []

    def find(item):
        parent.setdefault(item, item)
        if parent[item] != item:
            parent[item] = find(parent[item])
        return parent[item]

    for source, decision in decisions.items():
        if decision["source_status"] == "new_conversation":
            find(source)
        if decision["source_status"] != "complete":
            continue
        for edge in decision["edges"]:
            if edge["ambiguous"]:
                continue
            target = edge["target_message_id"]
            parent[find(source)] = find(target)
            edges.append({"source_message_id": source, **edge})
    groups = {}
    for node in sorted(parent):
        groups.setdefault(find(node), []).append(node)
    components = []
    for nodes in groups.values():
        members = sorted(nodes, key=lambda n: by_id[n]["sequence"])
        channel = by_id[members[0]]["channel_id"]
        identifier = (channel + "\0" + "\0".join(sorted(nodes))).encode("utf-8")
        component_edges = [e for e in edges if e["source_message_id"] in nodes]
        relevant = {n: decisions[n] for n in sorted(nodes) if n in decisions}
        sig = signature({"codebook": "1.1", "nodes": sorted(nodes), "edges": component_edges,
                         "decisions": relevant})
        components.append({"conversation_id": "HUMAN_" + hashlib.sha1(identifier).hexdigest()[:12],
                           "signature": sig, "message_ids": members, "edges": component_edges,
                           "participants": len({by_id[n].get("author_id") for n in nodes}),
                           "start": by_id[members[0]].get("timestamp"),
                           "end": by_id[members[-1]].get("timestamp"),
                           "includes_context": any(not by_id[n]["requires_reply_annotation"] for n in nodes),
                           "boundary_status": "unverified"})
    components.sort(key=lambda c: by_id[c["message_ids"][0]]["sequence"])
    return components


def compare_annotations(messages, left, right):
    rows, common, union, both_complete = [], 0, 0, 0
    comparable = []
    for m in messages:
        if not m["requires_reply_annotation"]:
            continue
        mid = m["message_id"]
        a, b = left.get(mid, empty_decision()), right.get(mid, empty_decision())
        eligible = all(d["source_status"] not in {"pending", "ambiguous", "outside_context"} and
                       not d.get("unresolved_additional_relation") and
                       not any(e["ambiguous"] for e in d["edges"]) for d in (a, b))
        def edge_set(d):
            return {(e["target_message_id"], e["ambiguous"]) for e in d["edges"]}
        agree = a["source_status"] == b["source_status"] and edge_set(a) == edge_set(b)
        if eligible:
            comparable.append(mid)
            ea = {e[0] for e in edge_set(a) if not e[1]}
            eb = {e[0] for e in edge_set(b) if not e[1]}
            common += len(ea & eb)
            union += len(ea | eb)
            both_complete += agree
        rows.append({"message_id": mid, "left": a, "right": b, "comparable": eligible, "agree": agree})
    # Pairwise grouping agreement for messages present in both graphs.
    ca, cb = derive(messages, left), derive(messages, right)
    ia = {n: c["conversation_id"] for c in ca for n in c["message_ids"]}
    ib = {n: c["conversation_id"] for c in cb for n in c["message_ids"]}
    nodes = sorted(set(comparable) & ia.keys() & ib.keys())
    counts = Counter((ia[n], ib[n]) for n in nodes)
    choose = lambda n: n * (n - 1) // 2
    paired = sum(choose(n) for n in counts.values())
    pa = sum(choose(n) for n in Counter(ia[n] for n in nodes).values())
    pb = sum(choose(n) for n in Counter(ib[n] for n in nodes).values())
    return {"rows": rows, "comparable_sources": len(comparable),
            "exact_decision_agreement": both_complete / len(comparable) if comparable else None,
            "link_jaccard": common / union if union else None,
            "component_pair_jaccard": paired / (pa + pb - paired) if pa + pb - paired else None,
            "component_comparable_nodes": len(nodes)}
