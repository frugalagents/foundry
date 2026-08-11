"""Deterministic HTTP and RSS collection for approved source entries."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from pydantic import Field, field_validator, model_validator

from .models import FrozenModel, StableId
from .source_registry import CollectorType, ParserType, SourceRegistryEntry


DEFAULT_MAX_BODY_BYTES = 10 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 30.0
USER_AGENT = "PlatformAdvisorKnowledgeCollector/1.0"


class CollectionError(RuntimeError):
    pass


class ResponseHeader(FrozenModel):
    name: str = Field(pattern=r"^[a-z0-9-]+$")
    value: str


class CollectedDocument(FrozenModel):
    snapshot_id: StableId
    source_id: StableId
    requested_uri: str = Field(min_length=1)
    final_uri: str = Field(min_length=1)
    status_code: int = Field(ge=200, le=299)
    retrieved_at: datetime
    headers: tuple[ResponseHeader, ...]
    media_type: str = Field(min_length=1)
    raw_body: bytes
    normalized_body: str = Field(min_length=1)
    raw_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("headers")
    @classmethod
    def sorted_headers(
        cls,
        headers: tuple[ResponseHeader, ...],
    ) -> tuple[ResponseHeader, ...]:
        return tuple(sorted(headers, key=lambda item: (item.name, item.value)))

    @model_validator(mode="after")
    def content_hashes_match_payloads(self) -> "CollectedDocument":
        if self.raw_content_hash != _sha256(self.raw_body):
            raise ValueError("raw_content_hash does not match raw_body")
        normalized_hash = _sha256(self.normalized_body.encode("utf-8"))
        if self.normalized_content_hash != normalized_hash:
            raise ValueError(
                "normalized_content_hash does not match normalized_body"
            )
        return self


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _normalize_text(value: str) -> str:
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    return "\n".join(line for line in lines if line)


def _normalize_html(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(value)
    parser.close()
    return _normalize_text("\n".join(parser.parts))


def _normalize_xml(value: str) -> str:
    root = ElementTree.fromstring(value)
    parts: list[str] = []

    def visit(element) -> None:
        tag = element.tag.rsplit("}", 1)[-1]
        text = _normalize_text(element.text or "")
        attributes = " ".join(
            f"{name}={json.dumps(attribute, ensure_ascii=True)}"
            for name, attribute in sorted(element.attrib.items())
        )
        descriptor = " ".join(item for item in (tag, attributes, text) if item)
        if descriptor:
            parts.append(descriptor)
        for child in element:
            visit(child)

    visit(root)
    return "\n".join(parts)


def normalize_body(
    raw_body: bytes,
    *,
    parser: ParserType | str,
    charset: str = "utf-8",
) -> str:
    """Normalize a collected body without discarding the original bytes."""

    parser = ParserType(parser)
    text = raw_body.decode(charset, errors="replace")
    if parser is ParserType.HTML:
        normalized = _normalize_html(text)
    elif parser is ParserType.JSON:
        normalized = json.dumps(
            json.loads(text),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    elif parser in {ParserType.XML, ParserType.RSS}:
        normalized = _normalize_xml(text)
    else:
        normalized = _normalize_text(text)
    if not normalized:
        raise CollectionError("collected document normalized to empty content")
    return normalized


def _response_headers(response) -> tuple[ResponseHeader, ...]:
    return tuple(
        ResponseHeader(name=name.lower().strip(), value=value.strip())
        for name, value in response.headers.items()
    )


def _content_type(
    headers: tuple[ResponseHeader, ...],
) -> tuple[str, str]:
    value = next(
        (
            header.value
            for header in headers
            if header.name == "content-type"
        ),
        "application/octet-stream",
    )
    segments = [segment.strip() for segment in value.split(";")]
    media_type = segments[0].lower()
    charset = "utf-8"
    for segment in segments[1:]:
        if segment.lower().startswith("charset="):
            charset = segment.split("=", 1)[1].strip("\"'")
    return media_type, charset


def collect_http(
    source: SourceRegistryEntry,
    *,
    retrieved_at: datetime,
    fetcher: Callable[..., object] = urlopen,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> CollectedDocument:
    """Collect one enabled HTTP/RSS source into a content-addressed document."""

    if not source.enabled:
        raise CollectionError("source collection is disabled")
    if source.collector not in {CollectorType.HTTP, CollectorType.RSS}:
        raise CollectionError(
            f"collector {source.collector.value} is not HTTP-compatible"
        )

    request = Request(
        str(source.base_uri),
        headers={
            "Accept": (
                "application/rss+xml, application/xml, text/xml"
                if source.collector is CollectorType.RSS
                else "*/*"
            ),
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with fetcher(request, timeout=timeout_seconds) as response:
            status_code = int(response.status)
            if status_code < 200 or status_code > 299:
                raise CollectionError(
                    f"source returned HTTP status {status_code}"
                )
            raw_body = response.read(max_body_bytes + 1)
            if len(raw_body) > max_body_bytes:
                raise CollectionError(
                    f"source body exceeds {max_body_bytes} bytes"
                )
            headers = _response_headers(response)
            media_type, charset = _content_type(headers)
            final_uri = response.geturl()
    except CollectionError:
        raise
    except (HTTPError, URLError, OSError) as error:
        raise CollectionError(f"source request failed: {error}") from error

    normalized_body = normalize_body(
        raw_body,
        parser=source.parser,
        charset=charset,
    )
    raw_hash = _sha256(raw_body)
    normalized_hash = _sha256(normalized_body.encode("utf-8"))
    source_slug = source.id.split(":", 1)[1]
    snapshot_id = f"snapshot:{source_slug}-{raw_hash[7:19]}"
    return CollectedDocument(
        snapshot_id=snapshot_id,
        source_id=source.id,
        requested_uri=str(source.base_uri),
        final_uri=final_uri,
        status_code=status_code,
        retrieved_at=retrieved_at,
        headers=headers,
        media_type=media_type,
        raw_body=raw_body,
        normalized_body=normalized_body,
        raw_content_hash=raw_hash,
        normalized_content_hash=normalized_hash,
    )
