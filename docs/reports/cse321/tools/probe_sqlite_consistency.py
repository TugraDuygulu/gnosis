#!/usr/bin/env python3
"""Non-destructive report experiment: always use a new temporary SQLite DB."""
import argparse
import hashlib
import importlib
import json
import platform
import sqlite3
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--source-ref')
a = p.parse_args()
if a.output.exists():
    p.error('Choose a new output file.')
ref = a.source_ref or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
sys.path.insert(0, str(ROOT))
import django
from django.conf import settings
base = importlib.import_module('config.settings')
config = {n: getattr(base, n) for n in dir(base) if n.isupper()}
with tempfile.TemporaryDirectory(prefix='gnosis-consistency-') as temporary:
    path = Path(temporary)/'fictional.sqlite3'
    config['DATABASES'] = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(path)}}
    settings.configure(**config)
    django.setup()
    from django.core.management import call_command
    from django.db import connection, transaction
    from core.models import Enrollment
    call_command('migrate', verbosity=0, stdout=StringIO())
    connection.ensure_connection()
    raw = connection.connection
    pragmas = {n: raw.execute(f'PRAGMA {n}').fetchone()[0] for n in
               ('journal_mode', 'read_uncommitted', 'foreign_keys', 'busy_timeout', 'synchronous')}
    assert pragmas['journal_mode']=='delete' and pragmas['read_uncommitted']==0
    raw.execute('CREATE TABLE report_probe (id INTEGER PRIMARY KEY, value INTEGER NOT NULL)')
    raw.execute('INSERT INTO report_probe VALUES (1, 10)')
    # Separate private-cache, file-backed connections, not a shared in-memory test DB.
    x = sqlite3.connect(path, isolation_level=None, timeout=0)
    y = sqlite3.connect(path, isolation_level=None, timeout=0)
    for c in (x, y):
        c.execute('PRAGMA foreign_keys=ON')
    def read(c):
        return c.execute('SELECT value FROM report_probe WHERE id=1').fetchone()[0]
    observations = {}
    x.execute('BEGIN IMMEDIATE')
    x.execute('UPDATE report_probe SET value=20 WHERE id=1')
    observations['reader_during_uncommitted_update'] = read(y)
    assert observations['reader_during_uncommitted_update']==10
    try:
        y.execute('BEGIN IMMEDIATE')
    except sqlite3.OperationalError as e:
        observations['competing_writer']={'error':str(e), 'code':e.sqlite_errorname}
        assert e.sqlite_errorname=='SQLITE_BUSY'
    else:
        raise AssertionError('Unexpected concurrent writers')
    x.commit()
    observations['reader_after_commit']=read(y)
    assert observations['reader_after_commit']==20
    x.execute('BEGIN')
    x.execute('UPDATE report_probe SET value=30 WHERE id=1')
    x.rollback()
    observations['reader_after_rollback']=read(y)
    assert observations['reader_after_rollback']==20
    x.execute('BEGIN')
    assert read(x)==20  # Acquire rollback-journal shared read lock.
    y.execute('BEGIN IMMEDIATE')
    y.execute('UPDATE report_probe SET value=40 WHERE id=1')
    try:
        y.commit()
    except sqlite3.OperationalError as e:
        observations['writer_commit_while_reader_active']={'error':str(e), 'code':e.sqlite_errorname}
        assert e.sqlite_errorname=='SQLITE_BUSY'
    else:
        raise AssertionError('Expected active reader to block writer commit')
    y.rollback()
    x.commit()
    assert read(x)==20
    trace = []
    raw.set_trace_callback(trace.append)
    with transaction.atomic():
        raw.execute('UPDATE report_probe SET value=50 WHERE id=1')
        try:
            with transaction.atomic():
                raw.execute('UPDATE report_probe SET value=60 WHERE id=1')
                raise ValueError('Rollback inner savepoint only')
        except ValueError:
            pass
    raw.set_trace_callback(None)
    observations['nested_atomic_result']=read(y)
    assert observations['nested_atomic_result']==50
    observations['atomic_control_sql']=[s for s in trace if s.startswith(('BEGIN','COMMIT','SAVEPOINT','ROLLBACK','RELEASE'))]
    assert observations['atomic_control_sql'][0]=='BEGIN'
    observations['select_for_update_sql']=str(Enrollment.objects.select_for_update().query)
    assert 'FOR UPDATE' not in observations['select_for_update_sql']
    assert connection.features.has_select_for_update is False
    assert raw.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    result={'source_revision':ref, 'database':'fresh temporary file; removed after probe',
        'runtime':{'python':platform.python_version(),'django':django.get_version(),'sqlite':sqlite3.sqlite_version},
        'django_autocommit':connection.get_autocommit(), 'driver_isolation_level':raw.isolation_level,
        'django_transaction_mode':connection.transaction_mode,
        'has_select_for_update':connection.features.has_select_for_update,
        'pragmas':pragmas,'probe_connection_timeout_seconds':0,'shared_cache_requested':False,
        'observations':observations, 'integrity_check':'ok',
        'limits':['Generic engine/atomic behavior, not simultaneous HTTP-client stress testing.',
                  'No development database inspected or changed; its journal mode is not inferred.',
                  'No WAL/alternate-engine or crash/power-loss experiment performed.'],
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    x.close();y.close();connection.close()
