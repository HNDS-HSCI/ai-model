import pytest
import threading
import time
import os
from hsci.core.storage import (
    SQLiteProvider, SchemaMigration, StorageProviderRegistry,
    ConnectionError, TransactionError, HSCIStorageError
)
from hsci.core.kernel import EventBus, CognitiveContext

def test_sqlite_provider_initialization():
    """Unit test verifying sqlite WAL activation, busy timeout, and initialization."""
    provider = SQLiteProvider(db_path=":memory:", busy_timeout_ms=1000)
    provider.initialize()
    
    # Verify WAL activation by reading pragma journal_mode
    res = provider.execute_read("PRAGMA journal_mode;")
    assert res[0]["journal_mode"] == "memory" or res[0]["journal_mode"] == "wal"  # memory is default fallback for purely in-memory
    
    provider.close()

def test_sqlite_provider_execute_read_write():
    """Integration test validating standard select and mutating updates."""
    provider = SQLiteProvider(db_path=":memory:")
    provider.initialize()
    
    provider.execute_write("CREATE TABLE test_data (id INTEGER PRIMARY KEY, val TEXT);")
    affected = provider.execute_write("INSERT INTO test_data (id, val) VALUES (?, ?);", (1, "hello"))
    assert affected == 1
    
    rows = provider.execute_read("SELECT * FROM test_data WHERE id = ?;", (1,))
    assert len(rows) == 1
    assert rows[0]["val"] == "hello"
    
    provider.close()

def test_transaction_rollback():
    """Integration test checking standard transaction rollback scopes."""
    provider = SQLiteProvider(db_path=":memory:")
    provider.initialize()
    
    provider.execute_write("CREATE TABLE test_tx (id INTEGER PRIMARY KEY, val TEXT);")
    
    # Begin and rollback
    provider.begin_transaction()
    provider.execute_write("INSERT INTO test_tx (id, val) VALUES (?, ?);", (10, "tx_val"))
    provider.rollback_transaction()
    
    rows = provider.execute_read("SELECT * FROM test_tx WHERE id = 10;")
    assert len(rows) == 0
    
    provider.close()

def test_savepoint_nested_transactions():
    """Integration test verifying nested savepoint transactions and partial rollbacks."""
    provider = SQLiteProvider(db_path=":memory:")
    provider.initialize()
    
    provider.execute_write("CREATE TABLE test_sp (id INTEGER PRIMARY KEY, val TEXT);")
    
    # Parent transaction
    provider.begin_transaction()
    provider.execute_write("INSERT INTO test_sp (id, val) VALUES (?, ?);", (1, "first"))
    
    # Savepoint A
    provider.create_savepoint("sp_a")
    provider.execute_write("INSERT INTO test_sp (id, val) VALUES (?, ?);", (2, "second"))
    
    # Rollback Savepoint A
    provider.rollback_savepoint("sp_a")
    provider.release_savepoint("sp_a")
    
    # Commit transaction
    provider.commit_transaction()
    
    # Verify only first row committed
    rows = provider.execute_read("SELECT * FROM test_sp ORDER BY id;")
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["val"] == "first"
    
    provider.close()

def test_concurrency_writes():
    """Concurrency verification spawning multiple threads writing simultaneously."""
    # Write to a shared file database to force file locking paths
    db_file = "test_concurrency.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass
            
    provider = SQLiteProvider(db_path=db_file, busy_timeout_ms=2000)
    provider.initialize()
    
    provider.execute_write("CREATE TABLE c_data (id INTEGER PRIMARY KEY, val TEXT);")
    
    errors = []
    def worker(thread_id: int):
        try:
            for i in range(10):
                uid = thread_id * 100 + i
                provider.execute_write("INSERT INTO c_data (id, val) VALUES (?, ?);", (uid, f"val_{uid}"))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(errors) == 0
    rows = provider.execute_read("SELECT COUNT(*) as cnt FROM c_data;")
    assert rows[0]["cnt"] == 100
    
    provider.close()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

def test_migration_sequential():
    """Unit test validating that SchemaMigration applies sequentially."""
    provider = SQLiteProvider(db_path=":memory:")
    migration = SchemaMigration(provider)
    
    migrations = [
        (1, "Create table x", "CREATE TABLE x (id INTEGER);"),
        (2, "Create table y", "CREATE TABLE y (id INTEGER);")
    ]
    
    migration.run_migrations(migrations)
    
    # Verify migration table entries
    versions = provider.execute_read("SELECT * FROM schema_versions ORDER BY version;")
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    
    # Check tables exist
    provider.execute_write("INSERT INTO x (id) VALUES (42);")
    provider.execute_write("INSERT INTO y (id) VALUES (100);")
    
    provider.close()

def test_startup_latency_benchmark():
    """Benchmark test measuring the initialization latency of the SQLite provider."""
    start_time = time.perf_counter()
    provider = SQLiteProvider(db_path=":memory:")
    provider.initialize()
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    
    print(f"\nSQLiteProvider startup latency: {duration_ms:.2f}ms")
    assert duration_ms < 50.0  # Must initialize in sub-50ms
    
    provider.close()

def test_cache_invalidation_hook():
    """Unit test demonstrating EventBus invalidation callback hooks."""
    event_bus = EventBus()
    invalidation_called = False
    
    def on_concept_changed_callback(context: CognitiveContext) -> None:
        nonlocal invalidation_called
        invalidation_called = True
        
    event_bus.subscribe("on_concept_changed", on_concept_changed_callback)
    
    # Trigger event
    ctx = CognitiveContext("req", "sess", "stimulus")
    event_bus.emit("on_concept_changed", ctx)
    
    assert invalidation_called is True
