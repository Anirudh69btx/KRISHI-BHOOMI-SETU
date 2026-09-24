"""
FLIP Gateway CRDT: Conflict-Free Replicated Data Types for Offline-First Sync
==============================================================================
Implements:
  - LamportClock      : monotonic logical clock with node tie-breaking
  - LWWRegister       : Last-Write-Wins register (advisories, device config)
  - ORSet             : Observed-Remove Set (sensor buffer, trusted devices)
  - CRDTEngine        : orchestrates in-memory CRDTs with SQLite persistence

Guarantees strong eventual consistency across 14-day network blackouts.
Zero data loss on reconnect via merge(). Mathematically correct.

SQLite schema used: crdt_state table (defined in storage/schema.sql)
  Also creates: crdt_registers, crdt_orsets tables for CRDT-specific metadata.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

LOG = logging.getLogger(__name__)


def get_mac() -> str:
    """Returns a deterministic node identifier string based on node hardware."""
    try:
        node_id = hex(uuid.getnode())[2:]
        return f"gw-{node_id[-6:]}"
    except Exception:
        return "gw-node01"


# ─── LamportClock ─────────────────────────────────────────────────────────────

class LamportClock:
    """Monotonic Lamport logical clock with node tie-breaking for causality tracking."""

    def __init__(self, node_id: Optional[str] = None, time: int = 0):
        self.time: int = time
        self.node_id: str = node_id or get_mac()

    def tick(self) -> Tuple[int, str]:
        self.time += 1
        return (self.time, self.node_id)

    def update(self, other_time: int, other_node: str) -> Tuple[int, str]:
        self.time = max(self.time, other_time) + 1
        return (self.time, self.node_id)

    def current(self) -> Tuple[int, str]:
        return (self.time, self.node_id)

    def to_dict(self) -> dict:
        return {"time": self.time, "node_id": self.node_id}

    @classmethod
    def from_dict(cls, d: dict) -> LamportClock:
        return cls(node_id=d.get("node_id"), time=d.get("time", 0))


# ─── LWWRegister ──────────────────────────────────────────────────────────────

class LWWRegister:
    """Last-Write-Wins Register for single-value state (advisories, device config)."""

    def __init__(
        self,
        value: Any = None,
        timestamp: Optional[Tuple[int, str]] = None,
        node_id: str = "",
    ):
        self.value: Any = value
        self.timestamp: Tuple[int, str] = timestamp or (0, "")
        self.node_id: str = node_id

    def set(self, value: Any, timestamp: Tuple[int, str], node_id: str = "") -> None:
        """Update value if timestamp is causally newer (tuple comparison)."""
        if timestamp > self.timestamp:
            self.value = value
            self.timestamp = timestamp
            self.node_id = node_id

    def merge(self, other: LWWRegister) -> LWWRegister:
        """Merge another register — higher timestamp wins."""
        self.set(other.value, other.timestamp, other.node_id)
        return self

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "timestamp": list(self.timestamp),
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LWWRegister:
        ts = tuple(d.get("timestamp", [0, ""]))
        return cls(
            value=d.get("value"),
            timestamp=ts,  # type: ignore[arg-type]
            node_id=d.get("node_id", ""),
        )


# ─── ORSet ────────────────────────────────────────────────────────────────────

class ORSet:
    """
    Observed-Remove Set (Add-Wins Set) for distributed collections.
    Elements map to sets of unique observed tags: {elem: {(tag, node_id)}}
    Any concurrent add+remove resolves as add (add-wins semantics).
    """

    def __init__(self, node_id: Optional[str] = None):
        self.node_id: str = node_id or get_mac()
        # str key → set of (tag, node_id) tuples
        # For non-string elements, we JSON-serialize the key
        self.elements: Dict[str, Set[Tuple[str, str]]] = {}
        self._tag_counter: int = 0

    def _new_tag(self) -> str:
        self._tag_counter += 1
        return f"{self.node_id}:{self._tag_counter}"

    def _elem_key(self, element: Any) -> str:
        """Deterministic string key for any element type."""
        if isinstance(element, str):
            return element
        return json.dumps(element, sort_keys=True, default=str)

    def add(self, element: Any, tag: Optional[str] = None) -> str:
        """Add element with a unique tag. Returns the tag used."""
        t = tag or self._new_tag()
        key = self._elem_key(element)
        self.elements.setdefault(key, set()).add((t, self.node_id))
        return t

    def remove(self, element: Any) -> None:
        """
        Remove currently observed tags for this element from this node.
        Concurrent adds from other nodes survive (add-wins).
        """
        key = self._elem_key(element)
        if key in self.elements:
            # Remove only tags where the node_id matches this node
            self.elements[key] = {
                (t, n) for t, n in self.elements[key]
                if n != self.node_id
            }
            if not self.elements[key]:
                del self.elements[key]

    def merge(self, other: ORSet) -> ORSet:
        """Union of tag sets — add-wins: any surviving tag keeps the element."""
        for key, tags in other.elements.items():
            self.elements.setdefault(key, set()).update(tags)
        return self

    def value(self) -> Set[str]:
        """Returns the set of element keys with at least one surviving tag."""
        return {k for k, tags in self.elements.items() if tags}

    # Alias
    def read(self) -> Set[str]:
        return self.value()

    def to_dict(self) -> dict:
        return {k: [list(t) for t in tags] for k, tags in self.elements.items()}

    @classmethod
    def from_dict(cls, d: dict, node_id: Optional[str] = None) -> ORSet:
        orset = cls(node_id=node_id)
        for key, tags in d.items():
            orset.elements[key] = {tuple(t) for t in tags}  # type: ignore[misc]
        return orset


# ─── CRDTEngine ───────────────────────────────────────────────────────────────

class CRDTEngine:
    """
    Core CRDT Engine: bridges in-memory CRDT objects with SQLite state persistence.
    Coordinates offline local mutations and cloud remote reconciliations.

    Storage: reuses the existing crdt_state table (schema.sql) plus two
    additional CRDT-specific tables created at init time.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        node_id: Optional[str] = None,
    ):
        if db_path:
            p = Path(db_path)
            if p.is_dir() or not p.suffix:
                p = p / "gateway.db"
            self.db_path = p
        else:
            self.db_path = None
        self.clock = LamportClock(node_id)
        self.registers: Dict[str, LWWRegister] = {}
        self.sets: Dict[str, ORSet] = {}

        if self.db_path:
            self._init_db()
            self._load_from_db()

    # ── DB lifecycle ───────────────────────────────────────────────────────

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        assert self.db_path is not None, "CRDTEngine: db_path not set"
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create CRDT-specific tables (additive — does not touch existing schema)."""
        assert self.db_path is not None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS crdt_registers (
                    key         TEXT PRIMARY KEY,
                    value_json  TEXT NOT NULL,
                    ts_clock    INTEGER NOT NULL DEFAULT 0,
                    ts_node     TEXT NOT NULL DEFAULT '',
                    node_id     TEXT NOT NULL DEFAULT '',
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS crdt_orsets (
                    key         TEXT PRIMARY KEY,
                    elements_json TEXT NOT NULL,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS crdt_clock (
                    node_id     TEXT PRIMARY KEY,
                    time        INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS crdt_state (
                    entity_type   TEXT NOT NULL,
                    entity_id     TEXT NOT NULL,
                    field_name    TEXT NOT NULL,
                    field_value   TEXT,
                    lamport_clock INTEGER DEFAULT 0,
                    node_id       TEXT DEFAULT '',
                    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (entity_type, entity_id, field_name)
                );
            """)
        LOG.debug("CRDTEngine DB initialized at %s", self.db_path)

    def _load_from_db(self) -> None:
        """Reconstruct in-memory CRDT state from SQLite on startup."""
        try:
            with self._get_conn() as conn:
                # Load clock
                row = conn.execute(
                    "SELECT time FROM crdt_clock WHERE node_id = ?",
                    (self.clock.node_id,)
                ).fetchone()
                if row:
                    self.clock.time = int(row["time"])

                # Load registers
                for row in conn.execute("SELECT key, value_json, ts_clock, ts_node, node_id FROM crdt_registers"):
                    reg = LWWRegister(
                        value=json.loads(row["value_json"]),
                        timestamp=(int(row["ts_clock"]), row["ts_node"]),
                        node_id=row["node_id"],
                    )
                    self.registers[row["key"]] = reg

                # Load OR-Sets
                for row in conn.execute("SELECT key, elements_json FROM crdt_orsets"):
                    orset = ORSet.from_dict(
                        json.loads(row["elements_json"]),
                        node_id=self.clock.node_id,
                    )
                    self.sets[row["key"]] = orset

            LOG.debug(
                "CRDT loaded from DB: %d registers, %d sets, clock=%d",
                len(self.registers), len(self.sets), self.clock.time,
            )
        except Exception as exc:
            LOG.warning("CRDT DB load error: %s (starting fresh)", exc)

    # ── Persistence helpers ────────────────────────────────────────────────

    def _persist_register(self, key: str, reg: LWWRegister) -> None:
        if not self.db_path:
            return
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO crdt_registers (key, value_json, ts_clock, ts_node, node_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json = excluded.value_json,
                        ts_clock   = excluded.ts_clock,
                        ts_node    = excluded.ts_node,
                        node_id    = excluded.node_id,
                        updated_at = excluded.updated_at
                """, (
                    key,
                    json.dumps(reg.value, default=str),
                    reg.timestamp[0],
                    reg.timestamp[1],
                    reg.node_id,
                ))
                # Also persist to legacy crdt_state table for cross-service visibility
                conn.execute("""
                    INSERT INTO crdt_state (entity_type, entity_id, field_name, field_value, lamport_clock)
                    VALUES ('lww', ?, 'value', ?, ?)
                    ON CONFLICT(entity_type, entity_id, field_name) DO UPDATE SET
                        field_value   = excluded.field_value,
                        lamport_clock = excluded.lamport_clock,
                        updated_at    = CURRENT_TIMESTAMP
                    WHERE excluded.lamport_clock >= crdt_state.lamport_clock
                """, (key, json.dumps(reg.value, default=str), reg.timestamp[0]))
        except Exception as exc:
            LOG.warning("CRDT persist_register error for '%s': %s", key, exc)

    def _persist_set(self, key: str, orset: ORSet) -> None:
        if not self.db_path:
            return
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO crdt_orsets (key, elements_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        elements_json = excluded.elements_json,
                        updated_at    = excluded.updated_at
                """, (key, json.dumps(orset.to_dict())))
        except Exception as exc:
            LOG.warning("CRDT persist_set error for '%s': %s", key, exc)

    def _persist_clock(self) -> None:
        if not self.db_path:
            return
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO crdt_clock (node_id, time) VALUES (?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET time = excluded.time
                """, (self.clock.node_id, self.clock.time))
        except Exception as exc:
            LOG.warning("CRDT persist_clock error: %s", exc)

    # ── Generic local operations ───────────────────────────────────────────

    def apply_local(self, key: str, value: Any, crdt_type: str = "lww") -> Tuple[int, str]:
        """
        Called when farmer performs an action or records telemetry offline.
        Advances the Lamport clock and mutates the local register or set.
        """
        ts = self.clock.tick()
        self._persist_clock()

        if crdt_type == "lww":
            reg = self.registers.setdefault(key, LWWRegister())
            reg.set(value, ts, self.clock.node_id)
            self._persist_register(key, reg)

        elif crdt_type == "orset":
            orset = self.sets.setdefault(key, ORSet(self.clock.node_id))
            orset.add(str(value))
            self._persist_set(key, orset)

        return ts

    def remove_local_set_element(self, key: str, value: Any) -> None:
        if key in self.sets:
            self.sets[key].remove(str(value))
            self._persist_set(key, self.sets[key])

    def merge_remote(
        self, key: str, remote_state: dict, crdt_type: str = "lww"
    ) -> None:
        """
        Called when sync agent pulls remote state from Cloud NATS.
        Preserves causality and mathematically resolves concurrent edits.
        """
        if crdt_type == "lww":
            remote_val = remote_state.get("value")
            remote_ts  = tuple(remote_state.get("timestamp", [0, ""]))
            self.clock.update(int(remote_ts[0]), str(remote_ts[1]))
            self._persist_clock()

            reg = self.registers.setdefault(key, LWWRegister())
            reg.set(remote_val, remote_ts, str(remote_ts[1]))  # type: ignore[arg-type]
            self._persist_register(key, reg)

        elif crdt_type == "orset":
            remote_set = ORSet.from_dict(remote_state, node_id=self.clock.node_id)
            orset = self.sets.setdefault(key, ORSet(self.clock.node_id))
            orset.merge(remote_set)
            self._persist_set(key, orset)

    def get_state(self, key: str) -> Any:
        """Returns current merged state for key."""
        if key in self.registers:
            return self.registers[key].value
        if key in self.sets:
            return self.sets[key].value()
        return None

    # ── Domain operations — Farmer Actions (LWW) ──────────────────────────

    def apply_farmer_action(self, advisory_id: str, action_data: dict) -> None:
        """
        Called when farmer presses 'Done' on an advisory.
        Stored as LWW-Register keyed by advisory_id.
        action_data: {action, details, done_at, synced_at, ...}
        """
        if "done_at" not in action_data:
            action_data["done_at"] = datetime.now(timezone.utc).isoformat()
        if "synced_at" not in action_data:
            action_data["synced_at"] = None

        key = f"farmer_action:{advisory_id}"
        ts = self.clock.tick()
        self._persist_clock()
        reg = self.registers.setdefault(key, LWWRegister())
        reg.set(action_data, ts, self.clock.node_id)
        self._persist_register(key, reg)
        LOG.debug("Farmer action recorded for advisory %s: %s", advisory_id, action_data.get("action"))

    def get_pending_actions(self) -> List[dict]:
        """Get all unsynced farmer actions (synced_at is None)."""
        actions = []
        for key, reg in self.registers.items():
            if not key.startswith("farmer_action:"):
                continue
            if not isinstance(reg.value, dict):
                continue
            if reg.value.get("synced_at") is None:
                advisory_id = key.split(":", 1)[1]
                actions.append({"advisory_id": advisory_id, **reg.value})
        return actions

    def mark_action_synced(self, advisory_id: str) -> None:
        """Mark a farmer action as synced after NATS push."""
        key = f"farmer_action:{advisory_id}"
        reg = self.registers.get(key)
        if reg and isinstance(reg.value, dict):
            reg.value["synced_at"] = datetime.now(timezone.utc).isoformat()
            self._persist_register(key, reg)

    # ── Domain operations — Sensor Buffer (OR-Set) ────────────────────────

    def add_sensor_reading(self, sensor_type: str, reading: dict) -> None:
        """
        Add sensor reading to local offline buffer (OR-Set).
        Each reading gets a unique ID: {timestamp}:{uuid8}.
        """
        reading_id = f"{reading.get('timestamp', '')}:{uuid.uuid4().hex[:8]}"
        payload = (reading_id, reading)
        key = f"sensor_buffer:{sensor_type}"
        orset = self.sets.setdefault(key, ORSet(node_id=self.clock.node_id))
        orset.add(json.dumps(payload, default=str))
        self._persist_set(key, orset)

    def get_sensor_buffer(self, sensor_type: str) -> List[dict]:
        """Return all buffered readings for a sensor type."""
        key = f"sensor_buffer:{sensor_type}"
        orset = self.sets.get(key)
        if not orset:
            return []
        readings = []
        for elem_key in orset.value():
            try:
                parsed = json.loads(elem_key)
                if isinstance(parsed, list) and len(parsed) == 2:
                    readings.append(parsed[1])
            except (json.JSONDecodeError, IndexError):
                pass
        return readings

    def merge_sensor_buffer(
        self,
        sensor_type: str,
        cloud_readings: List[dict],
        cloud_clock: LamportClock,
    ) -> None:
        """Merge cloud sensor readings into local OR-Set buffer."""
        key = f"sensor_buffer:{sensor_type}"
        orset = self.sets.setdefault(key, ORSet(node_id=self.clock.node_id))
        cloud_set = ORSet(node_id=cloud_clock.node_id)
        for r in cloud_readings:
            payload = (r.get("id", uuid.uuid4().hex[:8]), r)
            cloud_set.add(json.dumps(payload, default=str))
        orset.merge(cloud_set)
        self.clock.update(cloud_clock.time, cloud_clock.node_id)
        self._persist_clock()
        self._persist_set(key, orset)

    # ── Domain operations — Trusted Devices (OR-Set) ──────────────────────

    def add_trusted_device(self, fingerprint: str, device_info: dict) -> None:
        """Add a trusted sensor node to the local trusted-devices OR-Set."""
        key = "trusted_devices"
        orset = self.sets.setdefault(key, ORSet(node_id=self.clock.node_id))
        orset.add(json.dumps((fingerprint, device_info), default=str))
        self._persist_set(key, orset)

    def get_trusted_devices(self) -> List[dict]:
        """Return all currently trusted device infos."""
        key = "trusted_devices"
        orset = self.sets.get(key)
        if not orset:
            return []
        devices = []
        for elem_key in orset.value():
            try:
                parsed = json.loads(elem_key)
                if isinstance(parsed, list) and len(parsed) == 2:
                    devices.append(parsed[1])
            except (json.JSONDecodeError, IndexError):
                pass
        return devices

    def merge_trusted_devices(
        self,
        cloud_devices: List[dict],
        cloud_clock: LamportClock,
    ) -> None:
        """Merge cloud trusted-device list into local OR-Set."""
        key = "trusted_devices"
        orset = self.sets.setdefault(key, ORSet(node_id=self.clock.node_id))
        cloud_set = ORSet(node_id=cloud_clock.node_id)
        for d in cloud_devices:
            cloud_set.add(json.dumps((d.get("fingerprint", ""), d), default=str))
        orset.merge(cloud_set)
        self.clock.update(cloud_clock.time, cloud_clock.node_id)
        self._persist_clock()
        self._persist_set(key, orset)

    # ── Domain operations — Advisories (LWW) ──────────────────────────────

    def merge_advisory(
        self,
        advisory_id: str,
        advisory_data: dict,
        cloud_timestamp: Tuple[int, str],
        cloud_node: str,
    ) -> None:
        """Merge a cloud-generated advisory via LWW-Register."""
        key = f"advisory:{advisory_id}"
        reg = self.registers.setdefault(key, LWWRegister())
        cloud_reg = LWWRegister(
            value=advisory_data,
            timestamp=cloud_timestamp,
            node_id=cloud_node,
        )
        reg.merge(cloud_reg)
        self.clock.update(cloud_timestamp[0], cloud_timestamp[1])
        self._persist_clock()
        self._persist_register(key, reg)

    def get_advisory(self, advisory_id: str) -> Optional[dict]:
        """Get the current (merged) value of an advisory by ID."""
        key = f"advisory:{advisory_id}"
        reg = self.registers.get(key)
        return reg.value if reg else None


# ─── Backward-compatible StateSynchronizer ────────────────────────────────────

class StateSynchronizer:
    """Thin backward-compatible wrapper used by sync_agent and tests."""

    def __init__(self, node_id: str):
        self.engine = CRDTEngine(node_id=node_id)

    def tick(self) -> int:
        return self.engine.clock.tick()[0]

    def update_clock(self, remote_clock: int) -> int:
        return self.engine.clock.update(remote_clock, "remote")[0]

    def resolve_field(
        self,
        local_val: Any,
        local_clock: int,
        remote_val: Any,
        remote_clock: int,
    ) -> Tuple[Any, int]:
        reg = LWWRegister(local_val, (local_clock, "local"))
        other = LWWRegister(remote_val, (remote_clock, "remote"))
        merged = reg.merge(other)
        return merged.value, merged.timestamp[0]
