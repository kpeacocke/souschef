"""Lightweight REST API and webhook surface for SousChef."""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from http import HTTPStatus
from pathlib import Path
from typing import Any
from wsgiref.simple_server import make_server

from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
)
from souschef.core.url_validation import validate_user_provided_url
from souschef.orchestration import (
    orchestrate_generate_playbook_from_recipe as generate_playbook_from_recipe,
)
from souschef.server import (
    assess_chef_migration_complexity,
    convert_puppet_manifest_to_ansible,
    generate_migration_plan,
    import_puppet_catalog_to_ir,
    list_puppet_server_nodes,
    parse_recipe,
    validate_conversion,
)
from souschef.webhooks import send_webhook_notification

JsonObject = dict[str, Any]
RouteResponse = tuple[HTTPStatus, JsonObject]
LOGGER = logging.getLogger(__name__)

ROUTE_RUN = "/api/v1/run"
ROUTE_MIGRATION_ANALYSE = "/api/v1/migration/analyse"
ROUTE_MIGRATION_PLAN = "/api/v1/migration/plan"
ROUTE_MIGRATION_GENERATE_PLAYBOOK = "/api/v1/migration/generate-playbook"
ROUTE_VALIDATION_PROFILE = "/api/v1/validation/profile"
ROUTE_VALIDATION_PROFILE_STREAM = "/api/v1/validation/profile/stream"
ROUTE_CONTEXT_QUERY = "/api/v1/context/query"
ROUTE_CONTEXT_QUERY_STREAM = "/api/v1/context/query/stream"
ROUTE_WEBHOOK_NOTIFY = "/api/v1/webhooks/notify"

TOKEN_SPLIT_PATTERN = r"[^a-z0-9]+"

MAX_BODY_BYTES_DEFAULT = 50 * 1024
MAX_BODY_BYTES_BY_ROUTE: dict[tuple[str, str], int] = {
    ("POST", ROUTE_VALIDATION_PROFILE): 50 * 1024,
    ("POST", ROUTE_VALIDATION_PROFILE_STREAM): 50 * 1024,
    ("POST", ROUTE_CONTEXT_QUERY): 100 * 1024,
    ("POST", ROUTE_CONTEXT_QUERY_STREAM): 100 * 1024,
    ("POST", ROUTE_MIGRATION_ANALYSE): 200 * 1024,
    ("POST", ROUTE_MIGRATION_PLAN): 200 * 1024,
    ("POST", ROUTE_MIGRATION_GENERATE_PLAYBOOK): 100 * 1024,
    ("POST", ROUTE_RUN): 100 * 1024,
    ("POST", ROUTE_WEBHOOK_NOTIFY): 50 * 1024,
}

TIMEOUT_SECONDS_BY_OPERATION: dict[str, float] = {
    "assess_chef_migration_complexity": 180.0,
    "generate_migration_plan": 180.0,
    "generate_playbook_from_recipe": 120.0,
    "validate_conversion": 120.0,
    "context_query": 30.0,
    "run_operation": 120.0,
    "webhook_notify": 30.0,
}


def _supported_operations() -> dict[str, Any]:
    """Return the REST-exposed operation map."""
    return {
        "parse_recipe": parse_recipe,
        "validate_conversion": validate_conversion,
        "convert_puppet_manifest_to_ansible": convert_puppet_manifest_to_ansible,
        "list_puppet_server_nodes": list_puppet_server_nodes,
        "import_puppet_catalog_to_ir": import_puppet_catalog_to_ir,
    }


def _decode_json_body(body: bytes) -> JsonObject:
    """Decode a JSON body into a dictionary."""
    if not body:
        return {}

    decoded = json.loads(body.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Request body must decode to a JSON object")
    return decoded


def _coerce_result(result: Any) -> Any:
    """Coerce server return values into structured JSON when possible."""
    if not isinstance(result, str):
        return result

    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return result


def _format_timeout_seconds(timeout: float) -> str:
    """Return a readable timeout representation for API responses."""
    if timeout < 1:
        return f"{timeout:.2f}".rstrip("0").rstrip(".")
    if timeout.is_integer():
        return str(int(timeout))
    return f"{timeout:.1f}".rstrip("0").rstrip(".")


def _route_health() -> RouteResponse:
    """Return a basic health-check response."""
    return HTTPStatus.OK, {"status": "ok", "service": "souschef-rest-api"}


def _route_operations() -> RouteResponse:
    """Return supported REST operations."""
    return HTTPStatus.OK, {"operations": sorted(_supported_operations())}


def _invoke_operation(
    operation: str,
    callable_operation: Any,
    arguments: JsonObject,
    timeout_seconds: float | None = None,
) -> RouteResponse:
    """Run an operation and map known error types to HTTP responses."""
    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else TIMEOUT_SECONDS_BY_OPERATION.get(operation, 120.0)
    )

    executor = ThreadPoolExecutor(max_workers=1)
    future: Any | None = None
    try:
        future = executor.submit(callable_operation, **arguments)
        result = future.result(timeout=timeout)
    except FutureTimeoutError:
        cancel_succeeded = future.cancel() if future is not None else False
        LOGGER.warning(
            "REST operation timeout",
            extra={
                "operation": operation,
                "timeout_seconds": timeout,
                "cancel_requested": True,
                "cancel_succeeded": cancel_succeeded,
            },
        )
        return HTTPStatus.REQUEST_TIMEOUT, {
            "error": (
                f"Operation timed out after {_format_timeout_seconds(timeout)} seconds"
            )
        }
    except TypeError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": f"Invalid arguments: {exc}"}
    except RuntimeError as exc:
        return HTTPStatus.BAD_GATEWAY, {"error": str(exc)}
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": f"Invalid arguments: {exc}"}
    finally:
        # Avoid blocking request teardown on timed-out worker completion.
        executor.shutdown(wait=False, cancel_futures=True)

    return HTTPStatus.OK, {
        "status": "success",
        "operation": operation,
        "result": _coerce_result(result),
    }


def _route_run(request: JsonObject) -> RouteResponse:
    """Run a named SousChef operation via JSON request."""
    operation = request.get("operation", "")
    arguments = request.get("arguments", {})

    if not isinstance(operation, str) or not operation:
        return HTTPStatus.BAD_REQUEST, {"error": "Operation name is required"}
    if not isinstance(arguments, dict):
        return HTTPStatus.BAD_REQUEST, {"error": "Arguments must be a JSON object"}

    operations = _supported_operations()
    if operation not in operations:
        return HTTPStatus.NOT_FOUND, {"error": f"Unknown operation: {operation}"}

    status, response = _invoke_operation(operation, operations[operation], arguments)
    if status != HTTPStatus.OK:
        return status, response

    webhook_url = request.get("webhook_url", "")
    webhook_secret = request.get("webhook_secret", "")
    if isinstance(webhook_url, str) and webhook_url:
        try:
            webhook_url = validate_user_provided_url(webhook_url)
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": f"Invalid webhook URL: {exc}"}
        webhook_result = send_webhook_notification(
            webhook_url,
            "operation.completed",
            response,
            secret=webhook_secret if isinstance(webhook_secret, str) else "",
        )
        response["webhook"] = webhook_result

    return HTTPStatus.OK, response


def _route_migration_analyse(request: JsonObject) -> RouteResponse:
    """Analyse cookbook migration complexity via a dedicated endpoint."""
    cookbook_paths = request.get("cookbook_paths", "")
    migration_scope = request.get("migration_scope", "full")
    target_platform = request.get("target_platform", "ansible_awx")

    if isinstance(cookbook_paths, list):
        if not all(isinstance(path, str) and path for path in cookbook_paths):
            return HTTPStatus.BAD_REQUEST, {
                "error": "cookbook_paths list must contain non-empty strings"
            }
        cookbook_paths = ",".join(cookbook_paths)

    if not isinstance(cookbook_paths, str) or not cookbook_paths:
        return HTTPStatus.BAD_REQUEST, {"error": "cookbook_paths is required"}
    if not isinstance(migration_scope, str) or not migration_scope:
        return HTTPStatus.BAD_REQUEST, {"error": "migration_scope must be a string"}
    if not isinstance(target_platform, str) or not target_platform:
        return HTTPStatus.BAD_REQUEST, {"error": "target_platform must be a string"}

    return _invoke_operation(
        "assess_chef_migration_complexity",
        assess_chef_migration_complexity,
        {
            "cookbook_paths": cookbook_paths,
            "migration_scope": migration_scope,
            "target_platform": target_platform,
        },
    )


def _route_migration_generate_playbook(request: JsonObject) -> RouteResponse:
    """Generate an Ansible playbook for a Chef recipe via REST."""
    recipe_path = request.get("recipe_path", "")
    cookbook_path = request.get("cookbook_path", "")

    if not isinstance(recipe_path, str) or not recipe_path:
        return HTTPStatus.BAD_REQUEST, {"error": "recipe_path is required"}
    if not isinstance(cookbook_path, str):
        return HTTPStatus.BAD_REQUEST, {"error": "cookbook_path must be a string"}

    arguments: JsonObject = {"recipe_path": recipe_path}
    if cookbook_path:
        arguments["cookbook_path"] = cookbook_path

    return _invoke_operation(
        "generate_playbook_from_recipe",
        generate_playbook_from_recipe,
        arguments,
    )


def _route_migration_plan(request: JsonObject) -> RouteResponse:
    """Generate migration plan output via a dedicated endpoint."""
    cookbook_paths = request.get("cookbook_paths", "")
    migration_strategy = request.get("migration_strategy", "phased")
    timeline_weeks = request.get("timeline_weeks", 12)

    if isinstance(cookbook_paths, list):
        if not all(isinstance(path, str) and path for path in cookbook_paths):
            return HTTPStatus.BAD_REQUEST, {
                "error": "cookbook_paths list must contain non-empty strings"
            }
        cookbook_paths = ",".join(cookbook_paths)

    if not isinstance(cookbook_paths, str) or not cookbook_paths:
        return HTTPStatus.BAD_REQUEST, {"error": "cookbook_paths is required"}
    if not isinstance(migration_strategy, str) or not migration_strategy:
        return HTTPStatus.BAD_REQUEST, {"error": "migration_strategy must be a string"}
    if not isinstance(timeline_weeks, int) or timeline_weeks <= 0:
        return HTTPStatus.BAD_REQUEST, {
            "error": "timeline_weeks must be a positive integer"
        }

    return _invoke_operation(
        "generate_migration_plan",
        generate_migration_plan,
        {
            "cookbook_paths": cookbook_paths,
            "migration_strategy": migration_strategy,
            "timeline_weeks": timeline_weeks,
        },
    )


def _build_context_documents() -> list[JsonObject]:
    """Build a lightweight searchable context corpus for API capabilities."""
    operation_docs = [
        {
            "id": "operation.parse_recipe",
            "kind": "operation",
            "title": "Parse Chef recipe",
            "description": "Parse recipe files into structured migration context.",
            "route": ROUTE_RUN,
            "operation": "parse_recipe",
            "keywords": ["chef", "recipe", "parse", "analysis"],
        },
        {
            "id": "operation.validate_conversion",
            "kind": "operation",
            "title": "Validate conversion",
            "description": "Validate conversion output with syntax and "
            "semantic checks.",
            "route": ROUTE_RUN,
            "operation": "validate_conversion",
            "keywords": ["validate", "conversion", "syntax", "quality"],
        },
        {
            "id": "endpoint.migration.analyse",
            "kind": "endpoint",
            "title": "Migration complexity analysis",
            "description": "Assess migration complexity for one or more cookbooks.",
            "route": ROUTE_MIGRATION_ANALYSE,
            "keywords": ["migration", "analyse", "assessment", "complexity"],
        },
        {
            "id": "endpoint.migration.plan",
            "kind": "endpoint",
            "title": "Migration planning",
            "description": "Generate a phased or parallel migration plan "
            "with timeline.",
            "route": ROUTE_MIGRATION_PLAN,
            "keywords": ["migration", "plan", "timeline", "strategy"],
        },
        {
            "id": "endpoint.migration.generate_playbook",
            "kind": "endpoint",
            "title": "Generate playbook from recipe",
            "description": "Generate Ansible playbook content from Chef recipe input.",
            "route": ROUTE_MIGRATION_GENERATE_PLAYBOOK,
            "keywords": ["playbook", "recipe", "convert", "ansible"],
        },
        {
            "id": "endpoint.validation.profile",
            "kind": "endpoint",
            "title": "Validation profile filtering",
            "description": "Filter validation results by operational profile.",
            "route": ROUTE_VALIDATION_PROFILE,
            "keywords": ["validation", "profile", "safety", "production"],
        },
        {
            "id": "endpoint.webhook.notify",
            "kind": "endpoint",
            "title": "Webhook notifications",
            "description": "Send operation result notifications to external systems.",
            "route": ROUTE_WEBHOOK_NOTIFY,
            "keywords": ["webhook", "notify", "integration", "event"],
        },
    ]
    return operation_docs


def _build_cookbook_context_documents(cookbook_path: str) -> list[JsonObject]:
    """Build context documents from a cookbook path on disk."""
    workspace_root = _get_workspace_root()
    candidate_path = _ensure_within_base_path(
        _normalize_path(cookbook_path),
        workspace_root,
    )

    if not candidate_path.exists() or not candidate_path.is_dir():
        raise ValueError("cookbook_path must point to an existing directory")

    recipes_count = len(list((candidate_path / "recipes").glob("*.rb")))
    templates_count = len(list((candidate_path / "templates").rglob("*")))
    attributes_count = len(list((candidate_path / "attributes").glob("*.rb")))
    metadata_present = (candidate_path / "metadata.rb").exists()

    cookbook_name = Path(candidate_path).name
    summary = (
        f"Cookbook {cookbook_name}: "
        f"{recipes_count} recipes, "
        f"{attributes_count} attributes files, "
        f"{templates_count} templates entries"
    )

    live_docs: list[JsonObject] = [
        {
            "id": "cookbook.summary",
            "kind": "cookbook_signal",
            "title": "Cookbook structure summary",
            "description": summary,
            "route": ROUTE_CONTEXT_QUERY,
            "keywords": [
                "cookbook",
                "structure",
                "recipes",
                "templates",
                "attributes",
                cookbook_name.lower(),
            ],
        }
    ]

    if recipes_count > 0:
        live_docs.append(
            {
                "id": "cookbook.recipe_conversion_hint",
                "kind": "cookbook_signal",
                "title": "Recipe conversion signal",
                "description": (
                    f"Cookbook contains {recipes_count} recipes suitable for "
                    "playbook generation workflows."
                ),
                "route": ROUTE_MIGRATION_GENERATE_PLAYBOOK,
                "keywords": ["recipes", "playbook", "conversion", "generate"],
            }
        )

    if metadata_present:
        live_docs.append(
            {
                "id": "cookbook.metadata_signal",
                "kind": "cookbook_signal",
                "title": "Metadata present",
                "description": "metadata.rb exists and can improve planning context.",
                "route": ROUTE_MIGRATION_ANALYSE,
                "keywords": ["metadata", "analyse", "planning", "chef"],
            }
        )

    return live_docs


def _validate_context_query_request(request: JsonObject) -> RouteResponse | None:
    """Validate context query inputs before retrieval scoring."""
    query = request.get("query", "")
    top_k = request.get("top_k", 5)
    cookbook_path = request.get("cookbook_path", "")
    retrieval_mode = request.get("retrieval_mode", "hybrid")

    if not isinstance(query, str) or not query.strip():
        return HTTPStatus.BAD_REQUEST, {"error": "query is required"}
    if not isinstance(top_k, int) or top_k <= 0 or top_k > 20:
        return HTTPStatus.BAD_REQUEST, {
            "error": "top_k must be a positive integer between 1 and 20"
        }
    if not isinstance(cookbook_path, str):
        return HTTPStatus.BAD_REQUEST, {"error": "cookbook_path must be a string"}
    if not isinstance(retrieval_mode, str) or retrieval_mode not in {
        "keyword",
        "vector",
        "hybrid",
    }:
        return HTTPStatus.BAD_REQUEST, {
            "error": "retrieval_mode must be one of: keyword, vector, hybrid"
        }

    query_tokens = {
        token
        for token in re.split(TOKEN_SPLIT_PATTERN, query.lower())
        if len(token) >= 2
    }
    if not query_tokens:
        return HTTPStatus.BAD_REQUEST, {
            "error": "query must contain alphanumeric content"
        }

    return None


def _context_document_score(query: str, doc: JsonObject, retrieval_mode: str) -> float:
    """Score a context document for the given query and retrieval mode."""
    searchable_text = " ".join(
        [
            str(doc.get("title", "")).lower(),
            str(doc.get("description", "")).lower(),
            " ".join(str(keyword).lower() for keyword in doc.get("keywords", [])),
            str(doc.get("operation", "")).lower(),
            str(doc.get("route", "")).lower(),
        ]
    )
    query_tokens = {
        token
        for token in re.split(TOKEN_SPLIT_PATTERN, query.lower())
        if len(token) >= 2
    }
    doc_tokens = {
        token
        for token in re.split(TOKEN_SPLIT_PATTERN, searchable_text)
        if len(token) >= 2
    }
    keyword_score = float(len(query_tokens.intersection(doc_tokens)))
    vector_score = _vector_similarity(query, searchable_text)

    if retrieval_mode == "keyword":
        return keyword_score
    if retrieval_mode == "vector":
        return vector_score * 10.0
    return keyword_score + (vector_score * 5.0)


def _route_context_query(request: JsonObject) -> RouteResponse:
    """Query local migration capability context with ranked retrieval modes."""
    validation_error = _validate_context_query_request(request)
    if validation_error is not None:
        return validation_error

    query = str(request.get("query", ""))
    top_k = int(request.get("top_k", 5))
    cookbook_path = str(request.get("cookbook_path", ""))
    retrieval_mode = str(request.get("retrieval_mode", "hybrid"))

    context_docs = _build_context_documents()
    if cookbook_path:
        try:
            context_docs.extend(_build_cookbook_context_documents(cookbook_path))
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": f"Invalid cookbook_path: {exc}"}

    scored: list[tuple[float, JsonObject]] = []
    for doc in context_docs:
        score = _context_document_score(query, doc, retrieval_mode)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    matches = [
        {
            "score": round(score, 3),
            "id": match["id"],
            "kind": match["kind"],
            "title": match["title"],
            "description": match["description"],
            "route": match["route"],
            **({"operation": match["operation"]} if "operation" in match else {}),
        }
        for score, match in scored[:top_k]
    ]

    return HTTPStatus.OK, {
        "status": "success",
        "operation": "context_query",
        "query": query,
        "top_k": top_k,
        "cookbook_path": cookbook_path,
        "retrieval_mode": retrieval_mode,
        "match_count": len(matches),
        "matches": matches,
    }


def _route_context_query_stream(request: JsonObject) -> RouteResponse:
    """Return a stream-compatible response for context query."""
    status, response = _route_context_query(request)
    if status != HTTPStatus.OK:
        return status, response

    matches = response.get("matches", [])
    if not isinstance(matches, list):
        matches = []

    events: list[JsonObject] = [
        {
            "event": "start",
            "data": {
                "query": response.get("query", ""),
                "top_k": response.get("top_k", 0),
            },
        }
    ]
    for index, match in enumerate(matches, start=1):
        events.append(
            {
                "event": "match",
                "data": {
                    "index": index,
                    "id": match.get("id", ""),
                    "route": match.get("route", ""),
                    "score": match.get("score", 0),
                },
            }
        )
    events.append(
        {
            "event": "done",
            "data": {
                "match_count": response.get("match_count", 0),
                "status": "success",
            },
        }
    )

    return HTTPStatus.OK, {
        "status": "success",
        "operation": "context_query_stream",
        "events": events,
    }


def _tokenise_for_vector(text: str) -> list[str]:
    """Tokenise text into sparse unigrams and lightweight bigrams."""
    tokens = [
        token
        for token in re.split(TOKEN_SPLIT_PATTERN, text.lower())
        if len(token) >= 2
    ]
    bigrams = [
        f"{tokens[index]}_{tokens[index + 1]}" for index in range(len(tokens) - 1)
    ]
    return tokens + bigrams


def _vector_similarity(query: str, document: str) -> float:
    """Compute sparse cosine similarity across token vectors."""
    query_tokens = _tokenise_for_vector(query)
    document_tokens = _tokenise_for_vector(document)

    if not query_tokens or not document_tokens:
        return 0.0

    query_vector = Counter(query_tokens)
    document_vector = Counter(document_tokens)

    common = set(query_vector).intersection(document_vector)
    dot_product = sum(query_vector[token] * document_vector[token] for token in common)
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    document_norm = math.sqrt(sum(value * value for value in document_vector.values()))
    if math.isclose(query_norm, 0.0) or math.isclose(document_norm, 0.0):
        return 0.0

    return dot_product / (query_norm * document_norm)


def _validate_payload_size(method: str, path: str, body: bytes) -> RouteResponse | None:
    """Validate request body size against per-endpoint payload limits."""
    limit = MAX_BODY_BYTES_BY_ROUTE.get((method, path), MAX_BODY_BYTES_DEFAULT)
    if len(body) <= limit:
        return None

    return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
        "error": f"Payload too large: maximum {limit} bytes for {method} {path}",
    }


def _select_validation_results_for_profile(
    results: list[JsonObject],
    profile: str,
) -> list[JsonObject]:
    """Filter validation results according to a named profile."""
    profile_rules: dict[str, dict[str, set[str]]] = {
        "basic": {
            "levels": {"error"},
            "categories": {"syntax", "semantic"},
        },
        "moderate": {
            "levels": {"error", "warning"},
            "categories": {
                "syntax",
                "semantic",
                "best_practice",
                "security",
            },
        },
        "safety": {
            "levels": {"error", "warning"},
            "categories": {"security", "syntax", "semantic"},
        },
        "shared": {
            "levels": {"error", "warning", "info"},
            "categories": {"syntax", "best_practice", "performance"},
        },
        "production": {
            "levels": {"error", "warning", "info"},
            "categories": {
                "syntax",
                "semantic",
                "best_practice",
                "security",
                "performance",
            },
        },
    }

    if profile not in profile_rules:
        raise ValueError(
            "validation_profile must be one of: basic, moderate, "
            "safety, shared, production"
        )

    levels = profile_rules[profile]["levels"]
    categories = profile_rules[profile]["categories"]
    return [
        result
        for result in results
        if isinstance(result, dict)
        and isinstance(result.get("level"), str)
        and isinstance(result.get("category"), str)
        and result["level"] in levels
        and result["category"] in categories
    ]


def _route_validation_profile(request: JsonObject) -> RouteResponse:
    """Validate conversion output using profile-specific result filtering."""
    conversion_type = request.get("conversion_type", "")
    result_content = request.get("result_content", "")
    validation_profile = request.get("validation_profile", "moderate")

    if not isinstance(conversion_type, str) or not conversion_type:
        return HTTPStatus.BAD_REQUEST, {"error": "conversion_type is required"}
    if not isinstance(result_content, str) or not result_content:
        return HTTPStatus.BAD_REQUEST, {"error": "result_content is required"}
    if not isinstance(validation_profile, str) or not validation_profile:
        return HTTPStatus.BAD_REQUEST, {"error": "validation_profile must be a string"}

    status, response = _invoke_operation(
        "validate_conversion",
        validate_conversion,
        {
            "conversion_type": conversion_type,
            "result_content": result_content,
            "output_format": "json",
        },
    )
    if status != HTTPStatus.OK:
        return status, response

    result_payload = response.get("result")
    if not isinstance(result_payload, dict):
        return HTTPStatus.BAD_GATEWAY, {
            "error": "Validation engine returned an unexpected payload"
        }

    summary = result_payload.get("summary", {})
    raw_results = result_payload.get("results", [])
    if not isinstance(summary, dict) or not isinstance(raw_results, list):
        return HTTPStatus.BAD_GATEWAY, {
            "error": "Validation engine returned an invalid result structure"
        }

    try:
        filtered_results = _select_validation_results_for_profile(
            [result for result in raw_results if isinstance(result, dict)],
            validation_profile,
        )
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

    has_error = any(result.get("level") == "error" for result in filtered_results)
    has_warning = any(result.get("level") == "warning" for result in filtered_results)

    return HTTPStatus.OK, {
        "status": "success",
        "operation": "validate_conversion_with_profile",
        "profile": validation_profile,
        "conversion_type": conversion_type,
        "passed": not has_error
        and not (validation_profile == "production" and has_warning),
        "summary": summary,
        "result_count": len(filtered_results),
        "results": filtered_results,
    }


def _route_validation_profile_stream(request: JsonObject) -> RouteResponse:
    """Return a stream-compatible response for validation profile checks."""
    status, response = _route_validation_profile(request)
    if status != HTTPStatus.OK:
        return status, response

    results = response.get("results", [])
    if not isinstance(results, list):
        results = []

    events: list[JsonObject] = [
        {
            "event": "start",
            "data": {
                "profile": response.get("profile", ""),
                "conversion_type": response.get("conversion_type", ""),
            },
        }
    ]
    for index, result in enumerate(results, start=1):
        events.append(
            {
                "event": "result",
                "data": {
                    "index": index,
                    "level": result.get("level", ""),
                    "category": result.get("category", ""),
                    "message": result.get("message", ""),
                },
            }
        )
    events.append(
        {
            "event": "done",
            "data": {
                "passed": response.get("passed", False),
                "result_count": response.get("result_count", 0),
            },
        }
    )

    return HTTPStatus.OK, {
        "status": "success",
        "operation": "validate_conversion_with_profile_stream",
        "events": events,
    }


def _route_webhook_notify(request: JsonObject) -> RouteResponse:
    """Deliver a webhook notification from the REST surface."""
    url = request.get("url", "")
    event = request.get("event", "")
    payload = request.get("payload", {})
    secret = request.get("secret", "")

    if not isinstance(url, str) or not url:
        return HTTPStatus.BAD_REQUEST, {"error": "Webhook URL is required"}
    if not isinstance(event, str) or not event:
        return HTTPStatus.BAD_REQUEST, {"error": "Webhook event is required"}
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {
            "error": "Webhook payload must be a JSON object"
        }

    try:
        safe_url = validate_user_provided_url(url, strip_path=False)
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": f"Invalid webhook URL: {exc}"}

    result = send_webhook_notification(
        safe_url,
        event,
        payload,
        secret=secret if isinstance(secret, str) else "",
    )
    status = HTTPStatus.OK if result["status"] == "success" else HTTPStatus.BAD_GATEWAY
    return status, result


def handle_rest_request(method: str, path: str, body: bytes = b"") -> RouteResponse:
    """Handle a REST request in a testable, framework-free manner."""
    route_handlers: dict[tuple[str, str], Callable[[JsonObject], RouteResponse]] = {
        ("GET", "/health"): lambda _request: _route_health(),
        ("GET", "/api/v1/operations"): lambda _request: _route_operations(),
        ("POST", ROUTE_RUN): _route_run,
        ("POST", ROUTE_MIGRATION_ANALYSE): _route_migration_analyse,
        (
            "POST",
            ROUTE_MIGRATION_GENERATE_PLAYBOOK,
        ): _route_migration_generate_playbook,
        ("POST", ROUTE_MIGRATION_PLAN): _route_migration_plan,
        ("POST", ROUTE_VALIDATION_PROFILE): _route_validation_profile,
        ("POST", ROUTE_VALIDATION_PROFILE_STREAM): _route_validation_profile_stream,
        ("POST", ROUTE_CONTEXT_QUERY): _route_context_query,
        ("POST", ROUTE_CONTEXT_QUERY_STREAM): _route_context_query_stream,
        ("POST", ROUTE_WEBHOOK_NOTIFY): _route_webhook_notify,
    }

    handler: Callable[[JsonObject], RouteResponse] | None = route_handlers.get(
        (method, path)
    )
    if handler is None:
        return HTTPStatus.NOT_FOUND, {"error": f"Unknown route: {method} {path}"}

    payload_error = _validate_payload_size(method, path, body)
    if payload_error is not None:
        return payload_error

    try:
        request = _decode_json_body(body)
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

    return handler(request)


class SousChefRestApi:
    """WSGI wrapper around the lightweight REST handlers."""

    def __call__(self, environ: dict[str, Any], start_response: Any) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        body_length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(body_length) if body_length else b""
        status, payload = handle_rest_request(method, path, body)
        content_type = "application/json"
        if path.endswith("/stream") and status == HTTPStatus.OK:
            content_type = "text/event-stream"

        if content_type == "text/event-stream":
            events = payload.get("events", []) if isinstance(payload, dict) else []
            if not isinstance(events, list):
                events = []
            sse_lines: list[str] = []
            for event in events:
                if not isinstance(event, dict):
                    continue
                event_name = event.get("event", "message")
                event_data = json.dumps(event.get("data", {}), separators=(",", ":"))
                sse_lines.append(f"event: {event_name}\ndata: {event_data}\n")
            response_bytes = ("\n".join(sse_lines) + "\n").encode("utf-8")
        else:
            response_bytes = json.dumps(payload, indent=2).encode("utf-8")

        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(response_bytes))),
        ]
        start_response(f"{status.value} {status.phrase}", headers)
        return [response_bytes]


def run_api_server(
    host: str = ".".join(["127", "0", "0", "1"]), port: int = 8081
) -> None:
    """Run the SousChef REST API using the standard library server."""
    app = SousChefRestApi()
    with make_server(host, port, app) as httpd:
        LOGGER.info("SousChef REST API listening on http://%s:%s", host, port)
        httpd.serve_forever()
