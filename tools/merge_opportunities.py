#!/usr/bin/env python3
"""Offline, fail-closed merger for Diane's five research outboxes.

No network, credentials, eval, git mutation, or deployment. Publication remains
an independently authorized native connector action. Review mode is the default.
"""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

PROTOCOL = "diane-publish-v3"
STATES = {"READY", "NEEDS_RESEARCH", "BLOCKED_SAFETY", "BLOCKED_AUTH", "APPROVAL_REQUIRED"}
FINAL = {"INTEGRATED_MAIN", "DEPLOYED_PAGES", "LIVE_VERIFIED"}
REQUIRED = "name url priority type location deadline value fee simplicity career eligibility maxWorks lifetime action verified".split()


class Invalid(ValueError):
    pass


def require(test, message):
    if not test:
        raise Invalid(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate object key: " + key)
        result[key] = value
    return result


def bad_constant(value):
    raise Invalid("non-finite constant: " + value)


DECODER = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=bad_constant)


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(stable(value).encode("utf-8")).hexdigest()


def blob_sha(text):
    raw = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def url_key(value):
    require(isinstance(value, str), "URL must be text")
    u = urlsplit(value)
    require(u.scheme == "https" and u.hostname and not u.username and not u.password,
            "a public HTTPS source URL without credentials is required")
    return urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/"), u.query, ""))


def identity(record):
    require(isinstance(record, dict), "record/key must be an object")
    name = record.get("name")
    require(isinstance(name, str) and name.strip(), "missing name")
    return (" ".join(name.split()).casefold(), url_key(record.get("url")))


class LiteralParser:
    """Accept only data literals, never execute JavaScript. Retain source spans."""
    def __init__(self, text):
        require(len(text.encode("utf-8")) <= 16_000_000, "data file too large")
        self.text, self.i = text, 0

    def ws(self):
        while self.i < len(self.text):
            if self.text[self.i].isspace():
                self.i += 1
            elif self.text.startswith("//", self.i):
                end = self.text.find("\n", self.i + 2)
                self.i = len(self.text) if end < 0 else end + 1
            elif self.text.startswith("/*", self.i):
                end = self.text.find("*/", self.i + 2)
                require(end >= 0, "unterminated comment")
                self.i = end + 2
            else:
                break

    def take(self, token):
        self.ws()
        require(self.text.startswith(token, self.i), "expected " + token)
        self.i += len(token)

    def peek(self):
        self.ws()
        return self.text[self.i:self.i + 1]

    def value(self, depth=0):
        require(depth < 48, "literal nesting too deep")
        c = self.peek()
        if c == "{":
            self.take("{")
            pairs = []
            if self.peek() != "}":
                while True:
                    if self.peek() == '"':
                        key = self.value(depth + 1)
                    else:
                        m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", self.text[self.i:])
                        require(m is not None, "expected an object key")
                        key = m.group(0)
                        self.i += len(key)
                    require(key not in {"__proto__", "constructor", "prototype"}, "unsafe object key")
                    self.take(":")
                    pairs.append((key, self.value(depth + 1)))
                    if self.peek() != ",":
                        break
                    self.take(",")
                    if self.peek() == "}":
                        break
            self.take("}")
            return unique_object(pairs)
        if c == "[":
            self.take("[")
            values = []
            if self.peek() != "]":
                while True:
                    values.append(self.value(depth + 1))
                    if self.peek() != ",":
                        break
                    self.take(",")
                    if self.peek() == "]":
                        break
            self.take("]")
            return values
        require(c in '"-0123456789tfn' and c != "", "only JSON-compatible literals are supported")
        try:
            result, end = DECODER.raw_decode(self.text, self.i)
        except (ValueError, json.JSONDecodeError) as exc:
            raise Invalid("invalid literal") from exc
        require(not isinstance(result, (dict, list)), "unexpected compound literal")
        require(not isinstance(result, float) or math.isfinite(result), "non-finite number")
        self.i = end
        return result

    def records(self):
        self.take("window.DIANE_OPPORTUNITIES")
        self.take("=")
        self.take("[")
        records, spans = [], []
        last_comma = False
        if self.peek() != "]":
            while True:
                self.ws()
                start = self.i
                record = self.value()
                require(isinstance(record, dict), "every opportunity must be an object")
                records.append(record)
                spans.append((start, self.i))
                last_comma = self.peek() == ","
                if not last_comma:
                    break
                self.take(",")
                if self.peek() == "]":
                    break
        self.ws()
        close = self.i
        self.take("]")
        if self.peek() == ";":
            self.take(";")
        self.ws()
        require(self.i == len(self.text), "executable/trailing content is forbidden")
        keys = [identity(x) for x in records]
        require(len(keys) == len(set(keys)), "duplicate opportunity identity")
        return records, spans, close, last_comma


def validate_record(record):
    identity(record)
    for field in REQUIRED:
        require(isinstance(record.get(field), str) and record[field].strip(), "missing text field: " + field)
    require(record["priority"] in {"A1", "A2", "B", "C", "Écarté"}, "invalid priority")
    for field in ("tags", "discipline"):
        values = record.get(field)
        require(isinstance(values, list) and values and all(isinstance(x, str) and x.strip() for x in values),
                "nonempty string array required: " + field)
        require(len(values) == len(set(values)), "duplicate " + field)
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["verified"]) is not None, "invalid verification date")
    stable(record)


def operation_hash(item):
    return digest({k: item[k] for k in ("axis", "op", "key", "edition", "record", "changes", "addTags", "evidence") if k in item})


def plan(text, queue, expected_blob, mode="review"):
    require(mode in {"review", "authorized"}, "invalid mode")
    require(blob_sha(text) == expected_blob, "base blob mismatch; refetch main")
    require(isinstance(queue, dict) and queue.get("protocol") == PROTOCOL, "wrong queue protocol")
    require(queue.get("publicationGate") in {"HOLD_UNRESOLVED_SAFETY", "AUTHORIZED"}, "missing publication gate")
    if mode == "authorized":
        require(queue["publicationGate"] == "AUTHORIZED", "publication gate is held")
        require(isinstance(queue.get("authorizationEvidence"), str) and queue["authorizationEvidence"].strip(),
                "observable, independently checked authorization evidence is required")
    items = queue.get("items")
    require(isinstance(items, list), "items must be an array")
    records, spans, close, trailing = LiteralParser(text).records()
    original = copy.deepcopy(records)
    index = {identity(r): n for n, r in enumerate(records)}
    held_keys, held_names, held_urls = set(), set(), set()
    for held in queue.get("quarantine", []):
        key = identity(held["key"])
        held_keys.add(key)
        held_names.add(key[0])
        held_urls.add(key[1])
    for item in items:
        if item.get("state") in {"BLOCKED_SAFETY", "BLOCKED_AUTH", "APPROVAL_REQUIRED"}:
            key = identity(item["key"])
            held_keys.add(key)
            held_names.add(key[0])
            held_urls.add(key[1])
    receipts = {}
    for receipt in queue.get("receipts", []):
        require(receipt.get("status") in FINAL, "only verified publication receipts are trusted")
        require(receipt["id"] not in receipts, "duplicate receipt ID")
        receipts[receipt["id"]] = receipt
    seen, results, additions, changed, errors = {}, [], [], set(), False
    for item in items:
        item_id = item.get("id")
        require(isinstance(item_id, str) and re.fullmatch(r"[a-zA-Z0-9._:-]{1,160}", item_id), "invalid proposal ID")
        payload_hash = operation_hash(item)
        result = {"id": item_id, "payloadHash": payload_hash}
        if item_id in seen:
            require(seen[item_id] == digest(item), "proposal ID reused with different content")
            continue
        seen[item_id] = digest(item)
        try:
            require(item.get("axis") in {1, 2, 3, 4, 5} and type(item["axis"]) is int, "invalid axis")
            require(item.get("state") in STATES, "unknown proposal state")
            key = identity(item["key"])
            if key in held_keys or key[0] in held_names or key[1] in held_urls:
                result["status"] = "QUARANTINED"
            elif item["state"] != "READY":
                result["status"] = item["state"]
            elif item_id in receipts:
                require(receipts[item_id]["payloadHash"] == payload_hash, "receipt hash mismatch")
                result["status"] = "ALREADY_RECEIPTED"
            else:
                evidence = item.get("evidence")
                require(isinstance(evidence, list) and evidence and all(isinstance(e, dict) for e in evidence), "missing primary evidence")
                for e in evidence:
                    url_key(e.get("url"))
                    require(isinstance(e.get("checkedAt"), str) and e["checkedAt"] and e.get("supports"), "incomplete evidence")
                if item["op"] == "insert":
                    proposed = copy.deepcopy(item["record"])
                    validate_record(proposed)
                    require(identity(proposed) == key, "record/key mismatch")
                    if key in index:
                        require(records[index[key]] == proposed, "insert conflicts with existing record; propose a field patch")
                        result["status"] = "ALREADY_APPLIED"
                    else:
                        require(not any(key[0] == k[0] or key[1] == k[1] for k in index), "ambiguous name/URL duplicate needs review")
                        index[key] = len(records)
                        records.append(proposed)
                        additions.append(len(records) - 1)
                        result["status"] = "PLANNED_INSERT"
                elif item["op"] == "patch":
                    require(key in index, "patch target absent")
                    n = index[key]
                    current = copy.deepcopy(records[n])
                    changes = item.get("changes", {})
                    require(isinstance(changes, dict), "changes must be an object")
                    for field, change in changes.items():
                        require(field not in {"name", "url", "tags", "__proto__", "constructor", "prototype"}, "identity/tag replacement or unsafe patch forbidden")
                        require(isinstance(change, dict) and type(change.get("beforePresent")) is bool and "after" in change, "invalid field precondition")
                        require("before" in change or not change["beforePresent"], "missing previous value")
                        if field in current and current[field] == change["after"]:
                            continue
                        require((field in current) == change["beforePresent"] and (not change["beforePresent"] or current[field] == change["before"]), "field conflict: " + field)
                        current[field] = copy.deepcopy(change["after"])
                    add_tags = item.get("addTags", [])
                    require(isinstance(add_tags, list) and all(isinstance(t, str) and t.strip() for t in add_tags), "invalid added tags")
                    if add_tags:
                        current["tags"] = list(dict.fromkeys(current.get("tags", []) + add_tags))
                    validate_record(current)
                    if current == records[n]:
                        result["status"] = "ALREADY_APPLIED"
                    else:
                        records[n] = current
                        changed.add(n)
                        result["status"] = "PLANNED_PATCH"
                else:
                    raise Invalid("unsupported operation; deletion is forbidden")
        except (Invalid, KeyError, TypeError, ValueError) as exc:
            result.update(status="NEEDS_REVIEW", reason=str(exc))
            errors = True
        results.append(result)
    can_emit = mode == "authorized" and not errors
    output = text
    if can_emit:
        edits = []
        for n in changed:
            if n < len(spans):
                edits.append((*spans[n], json.dumps(records[n], ensure_ascii=False, separators=(",", ":"))))
        if additions:
            appended = ",\n  ".join(json.dumps(records[n], ensure_ascii=False, separators=(",", ":")) for n in additions)
            prefix = ""
            if spans and not trailing:
                if spans[-1][1] == close:
                    prefix = ","
                else:
                    edits.append((spans[-1][1], spans[-1][1], ","))
            edits.append((close, close, prefix + "\n  " + appended + "\n"))
        for start, end, replacement in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
            output = output[:start] + replacement + output[end:]
        parsed, _, _, _ = LiteralParser(output).records()
        require(parsed == records, "round-trip mismatch")
        require(all(parsed[n] == original[n] for n in range(len(original)) if n not in changed), "neighbor modified")
    report = {
        "protocol": PROTOCOL, "mode": mode, "publicationGate": queue["publicationGate"],
        "baseBlobSha": expected_blob, "outputBlobSha": blob_sha(output),
        "inputCount": len(original), "plannedCount": len(records),
        "outputCount": len(records) if can_emit else len(original),
        "candidateChanged": output != text, "validationErrors": errors,
        "results": results, "published": False,
        "note": "Offline plan only. Review/hold/error outputs preserve input exactly. Connector authorization, CAS write and live verification are separate."
    }
    return output, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--queue", required=True, type=Path)
    p.add_argument("--expected-blob", required=True)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--mode", choices=("review", "authorized"), default="review")
    args = p.parse_args()
    paths = [args.data.resolve(), args.queue.resolve(), args.output.resolve(), args.report.resolve()]
    require(len(set(paths)) == 4, "input/output/report paths must be distinct")
    raw = args.data.read_bytes().decode("utf-8")
    queue = DECODER.decode(args.queue.read_bytes().decode("utf-8"))
    output, report = plan(raw, queue, args.expected_blob, args.mode)
    args.output.write_bytes(output.encode("utf-8"))
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(stable(report))
    return 2 if report["validationErrors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
