"""FalkorDB connection handling with typed failures (task A1.3).

This is the only module that talks to the database driver. Typed operations in
tracefix.graph.query (Phase 2) call `execute` with parameterized Cypher; no
free-form Cypher reaches the application interface. Unit tests inject a stub
driver; live-server verification is a marker-gated integration test and cannot
be claimed while Docker is unavailable (Checkpoint 0, D6).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

_GRAPH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class GraphClientError(Exception):
    """Base class for database failures surfaced by the client."""


class GraphConnectionError(GraphClientError):
    """The server is unreachable or refused the connection."""


class GraphTimeoutError(GraphClientError):
    """The operation exceeded its time budget."""


class GraphQueryError(GraphClientError):
    """The server rejected or failed to execute a query."""


def _default_driver_factory(host: str, port: int, **kwargs: Any) -> Any:
    from falkordb import FalkorDB  # imported lazily so unit tests need no driver

    return FalkorDB(host=host, port=port, **kwargs)


class FalkorDBClient:
    """Single-graph client. Cross-graph queries are refused by construction:
    the client is bound to one graph name and every query runs on it."""

    def __init__(
        self,
        graph_name: str,
        host: str = "localhost",
        port: int = 6379,
        driver_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not _GRAPH_NAME_RE.match(graph_name):
            raise ValueError(
                f"invalid graph name {graph_name!r}: must match {_GRAPH_NAME_RE.pattern}"
            )
        self.graph_name = graph_name
        self.host = host
        self.port = port
        self._driver_factory = driver_factory or _default_driver_factory
        self._graph: Any | None = None

    def connect(self) -> None:
        if self._graph is not None:
            return
        try:
            driver = self._driver_factory(self.host, self.port)
            self._graph = driver.select_graph(self.graph_name)
        except GraphClientError:
            raise
        except Exception as exc:  # noqa: BLE001 - mapped to typed error by design
            raise GraphConnectionError(
                f"cannot connect to FalkorDB at {self.host}:{self.port}: {exc}"
            ) from exc

    def close(self) -> None:
        self._graph = None

    def execute(
        self, cypher: str, params: dict[str, Any] | None = None, timeout_ms: int | None = None
    ) -> list[dict[str, Any]]:
        """Internal: only typed query operations (Phase 2) call this."""
        if self._graph is None:
            raise GraphConnectionError("client is not connected; call connect() first")
        try:
            result = self._graph.query(cypher, params=params or {})
        except GraphClientError:
            raise
        except Exception as exc:  # noqa: BLE001 - mapped to typed error by design
            message = str(exc).lower()
            if "timeout" in message or "timed out" in message:
                raise GraphTimeoutError(f"query timed out after {timeout_ms}ms: {exc}") from exc
            if any(
                token in message
                for token in ("connection", "connect", "socket", "unreachable", "refused")
            ):
                raise GraphConnectionError(f"connection lost: {exc}") from exc
            raise GraphQueryError(f"query failed: {exc}") from exc
        return _rows(result)

    @property
    def connected(self) -> bool:
        return self._graph is not None


def _rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    if isinstance(result, list):
        if not result or isinstance(result[0], dict):
            return result
        return [{"value": r} if not isinstance(r, dict) else r for r in result]
    if hasattr(result, "result_set"):
        header = getattr(result, "header", None)
        if header and result.result_set:
            col_names = [
                col[1] if isinstance(col, (list, tuple)) and len(col) > 1 else str(col)
                for col in header
            ]
            return [dict(zip(col_names, row, strict=False)) for row in result.result_set]
        if not result.result_set:
            return []
    return list(result)
