import os
import sqlite3
import threading
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from abc import ABC, abstractmethod

# ─────────────────────────────────────────────
# CUSTOM STORAGE EXCEPTIONS
# ─────────────────────────────────────────────

class HSCIStorageError(Exception):
    """Base exception for all UKM storage failures."""
    pass

class ConnectionError(HSCIStorageError):
    """Raised when database connection pools or file locks fail."""
    pass

class TransactionError(HSCIStorageError):
    """Raised when an active transaction commit, rollback, or savepoint fails."""
    pass

class MigrationError(HSCIStorageError):
    """Raised when database schema migration scripts fail."""
    pass

# ─────────────────────────────────────────────
# STORAGE PROVIDER INTERFACES
# ─────────────────────────────────────────────

class IStorageProvider(ABC):
    """
    Abstract interface for all UKM physical storage engines.
    Ensures complete storage independence for upper cognitive layers.
    """
    @abstractmethod
    def initialize(self) -> None:
        """Establishes connections and runs initial migrations."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes connection pools and releases lock handles."""
        pass

    @abstractmethod
    def execute_read(self, query: str, params: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Executes a select query and returns standard dict list results."""
        pass

    @abstractmethod
    def execute_write(self, query: str, params: Optional[Any] = None) -> int:
        """Executes a mutating query and returns affected row count."""
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """Begins an atomic transaction scope."""
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        """Commits the active transaction scope."""
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        """Rolls back the active transaction scope."""
        pass

    @abstractmethod
    def create_savepoint(self, name: str) -> None:
        """Spawns a named SAVEPOINT inside the active transaction."""
        pass

    @abstractmethod
    def release_savepoint(self, name: str) -> None:
        """Releases/commits a named SAVEPOINT."""
        pass

    @abstractmethod
    def rollback_savepoint(self, name: str) -> None:
        """Rolls back state to a named SAVEPOINT."""
        pass

# ─────────────────────────────────────────────
# SQLITE PHYSICAL PERSISTENCE PROVIDER
# ─────────────────────────────────────────────

class SQLiteProvider(IStorageProvider):
    """
    Thread-safe SQLite persistence provider.
    Implements Write-Ahead Logging (WAL), transaction scopes, and savepoint hierarchies.
    """
    def __init__(self, db_path: str = ":memory:", busy_timeout_ms: int = 3000):
        self.db_path: str = db_path
        self.busy_timeout_ms: int = busy_timeout_ms
        self.logger: logging.Logger = logging.getLogger("HSCI.Storage.SQLite")
        
        # Thread isolation parameters
        self._local: threading.local = threading.local()
        self._write_lock: threading.Lock = threading.Lock()
        self._conn_init_lock: threading.Lock = threading.Lock()
        
        # Active connections tracker to support close operation
        self._active_connections: List[sqlite3.Connection] = []
        self._conn_list_lock: threading.Lock = threading.Lock()

        # Savepoint stacks per thread
        self._thread_savepoints: Dict[int, List[str]] = {}
        self._savepoint_lock: threading.Lock = threading.Lock()

    def _get_connection(self) -> sqlite3.Connection:
        """Retrieves or creates a thread-local SQLite connection handle."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            with self._conn_init_lock:
                # Double-check inside connection initialization lock
                if not hasattr(self._local, "connection") or self._local.connection is None:
                    try:
                        conn = sqlite3.connect(
                            self.db_path,
                            timeout=float(self.busy_timeout_ms) / 1000.0
                        )
                        conn.row_factory = sqlite3.Row
                        
                        # Activate Write-Ahead Logging (WAL) and synchronous modes
                        conn.execute("PRAGMA journal_mode=WAL;")
                        conn.execute("PRAGMA synchronous=NORMAL;")
                        
                        self._local.connection = conn
                        with self._conn_list_lock:
                            self._active_connections.append(conn)
                            
                    except Exception as e:
                        self.logger.error(f"Failed to establish SQLite connection to '{self.db_path}': {e}")
                        raise ConnectionError(f"Failed to connect to sqlite database: {e}")
                
        return self._local.connection

    def initialize(self) -> None:
        """Initializes database files, journals, and registers migrations table."""
        try:
            conn = self._get_connection()
            # Enforce foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON;")
            
            # Setup migrations tracker table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_versions (
                    version INTEGER PRIMARY KEY,
                    applied_at REAL NOT NULL,
                    description TEXT
                );
            """)
            conn.commit()
            self.logger.info("SQLite storage provider initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite storage provider: {e}")
            raise ConnectionError(f"Database initialization failure: {e}")

    def close(self) -> None:
        """Closes all active thread connections and clean up memory."""
        with self._conn_list_lock:
            for conn in self._active_connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._active_connections.clear()
        self._local.connection = None
        self._local.in_explicit_transaction = False
        with self._savepoint_lock:
            self._thread_savepoints.clear()
        self.logger.info("All SQLite storage provider connections closed.")

    @property
    def _in_transaction(self) -> bool:
        """Returns True if the current thread is in an active explicit transaction or savepoint."""
        if getattr(self._local, "in_explicit_transaction", False):
            return True
        thread_id = threading.get_ident()
        with self._savepoint_lock:
            if thread_id in self._thread_savepoints and len(self._thread_savepoints[thread_id]) > 0:
                return True
        return False

    def execute_read(self, query: str, params: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Executes a select query on the thread connection."""
        start_time = time.perf_counter()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.logger.debug(f"Read query executed in {duration_ms:.2f}ms: {query[:100]}")
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Read query failed: {query} with parameters {params}. Error: {e}")
            raise HSCIStorageError(f"Database read execution failure: {e}")

    def execute_write(self, query: str, params: Optional[Any] = None) -> int:
        """Executes a mutating query using global write locks to avoid lock contentions."""
        start_time = time.perf_counter()
        conn = self._get_connection()
        
        with self._write_lock:
            try:
                cursor = conn.cursor()
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # Automatic commit if we're not inside an active transaction scope
                if not self._in_transaction:
                    conn.commit()
                    
                affected = cursor.rowcount
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                self.logger.debug(f"Write query executed in {duration_ms:.2f}ms. Affected: {affected} rows: {query[:100]}")
                return affected
            except Exception as e:
                self.logger.error(f"Write query failed: {query}. Error: {e}")
                if self._in_transaction:
                    try:
                        conn.rollback()
                        self._local.in_explicit_transaction = False
                    except Exception:
                        pass
                raise HSCIStorageError(f"Database write execution failure: {e}")

    # ─────────────────────────────────────────────
    # TRANSACTION SCOPES & SAVEPOINTS
    # ─────────────────────────────────────────────

    def begin_transaction(self) -> None:
        conn = self._get_connection()
        try:
            # Enforce implicit write lock to hold thread writes during block transaction
            conn.execute("BEGIN TRANSACTION;")
            self._local.in_explicit_transaction = True
            self.logger.debug("Active SQLite transaction scope opened.")
        except Exception as e:
            raise TransactionError(f"Failed to begin sqlite transaction: {e}")

    def commit_transaction(self) -> None:
        conn = self._get_connection()
        try:
            conn.commit()
            self._local.in_explicit_transaction = False
            self.logger.debug("SQLite transaction scope committed.")
        except Exception as e:
            raise TransactionError(f"Failed to commit sqlite transaction: {e}")

    def rollback_transaction(self) -> None:
        conn = self._get_connection()
        try:
            conn.rollback()
            self._local.in_explicit_transaction = False
            self.logger.debug("SQLite transaction scope rolled back.")
        except Exception as e:
            raise TransactionError(f"Failed to roll back sqlite transaction: {e}")

    def create_savepoint(self, name: str) -> None:
        conn = self._get_connection()
        try:
            # SQLite savepoint command
            conn.execute(f"SAVEPOINT {name};")
            
            thread_id = threading.get_ident()
            with self._savepoint_lock:
                if thread_id not in self._thread_savepoints:
                    self._thread_savepoints[thread_id] = []
                self._thread_savepoints[thread_id].append(name)
                
            self.logger.debug(f"SQLite named SAVEPOINT '{name}' established.")
        except Exception as e:
            raise TransactionError(f"Failed to create SAVEPOINT '{name}': {e}")

    def release_savepoint(self, name: str) -> None:
        conn = self._get_connection()
        try:
            conn.execute(f"RELEASE SAVEPOINT {name};")
            
            thread_id = threading.get_ident()
            with self._savepoint_lock:
                if thread_id in self._thread_savepoints and name in self._thread_savepoints[thread_id]:
                    self._thread_savepoints[thread_id].remove(name)
                    
            self.logger.debug(f"SQLite named SAVEPOINT '{name}' released.")
        except Exception as e:
            raise TransactionError(f"Failed to release SAVEPOINT '{name}': {e}")

    def rollback_savepoint(self, name: str) -> None:
        conn = self._get_connection()
        try:
            conn.execute(f"ROLLBACK TO SAVEPOINT {name};")
            self.logger.debug(f"SQLite rolled back state to SAVEPOINT '{name}'.")
        except Exception as e:
            raise TransactionError(f"Failed to rollback to SAVEPOINT '{name}': {e}")

# ─────────────────────────────────────────────
# MIGRATION FRAMEWORK
# ─────────────────────────────────────────────

class SchemaMigration:
    """
    Applies schema migrations sequentially and registers versions in the database.
    """
    def __init__(self, provider: IStorageProvider):
        self.provider: IStorageProvider = provider
        self.logger: logging.Logger = logging.getLogger("HSCI.Storage.Migration")

    def run_migrations(self, migrations: List[Tuple[int, str, str]]) -> None:
        """
        Runs migrations sequentially.
        Each entry is (version_number, description, sql_statements).
        """
        # Ensure database tables initialized
        self.provider.initialize()
        
        # Query active schema version
        try:
            rows = self.provider.execute_read("SELECT MAX(version) as current_version FROM schema_versions;")
            current_version = rows[0]["current_version"] if rows and rows[0]["current_version"] is not None else 0
        except Exception as e:
            self.logger.error(f"Failed to fetch schema versions: {e}")
            current_version = 0

        self.logger.info(f"Checking schema migrations. Current version: {current_version}")
        
        for version, desc, sql in sorted(migrations, key=lambda x: x[0]):
            if version > current_version:
                self.logger.info(f"Applying migration version {version}: {desc}")
                try:
                    self.provider.begin_transaction()
                    
                    # Split script by semicolon if contains multiple commands
                    for statement in sql.split(";"):
                        cleaned = statement.strip()
                        if cleaned:
                            self.provider.execute_write(cleaned)
                            
                    self.provider.execute_write(
                        "INSERT INTO schema_versions (version, applied_at, description) VALUES (?, ?, ?);",
                        (version, time.time(), desc)
                    )
                    
                    self.provider.commit_transaction()
                    self.logger.info(f"Migration version {version} completed.")
                except Exception as e:
                    self.provider.rollback_transaction()
                    self.logger.error(f"Migration version {version} failed: {e}")
                    raise MigrationError(f"Migration failure on version {version}: {e}")

    def run_directory_migrations(self, migrations_dir: str) -> None:
        """
        Scans a directory for SQL migration files, orders them, and applies them sequentially.
        Files should follow the format: [0001-0999]_description.sql
        """
        if not os.path.exists(migrations_dir):
            self.logger.warning(f"Migrations directory does not exist: {migrations_dir}")
            return
            
        migrations = []
        for filename in os.listdir(migrations_dir):
            if filename.endswith(".sql"):
                # Parse version number from prefix (e.g., 0001_create_table.sql)
                parts = filename.split("_", 1)
                try:
                    version = int(parts[0])
                    desc = parts[1].rsplit(".", 1)[0].replace("_", " ")
                    filepath = os.path.join(migrations_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        sql = f.read()
                    migrations.append((version, desc, sql))
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Skipping migration file with invalid name format '{filename}': {e}")
                    
        if migrations:
            self.run_migrations(migrations)

# ─────────────────────────────────────────────
# PROVIDER REGISTRY
# ─────────────────────────────────────────────

class StorageProviderRegistry:
    """
    Dynamic registry holding the active persistence engine instance.
    """
    _provider: Optional[IStorageProvider] = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def register_provider(cls, provider: IStorageProvider) -> None:
        with cls._lock:
            cls._provider = provider

    @classmethod
    def get_provider(cls) -> IStorageProvider:
        with cls._lock:
            if cls._provider is None:
                raise ConnectionError("No storage provider registered in StorageProviderRegistry.")
            return cls._provider

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            if cls._provider is not None:
                cls._provider.close()
                cls._provider = None
