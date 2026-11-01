#!/usr/bin/env python3
"""Measure a fresh fictional pilot DB; never connect to the development DB.

Run from any directory with the project's virtualenv Python. Outputs schema
metadata and aggregate sizes only, not student records or a database file.
"""

import argparse
import hashlib
import importlib
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-ref", help="Explicit source revision when using a source-only copy.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    revision = args.source_ref or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
    ).strip()
    if (args.output_dir / "schema_inventory.json").exists():
        parser.error("Choose a new output directory; existing measurements are not overwritten.")

    import django
    from django.conf import settings

    base = importlib.import_module("config.settings")
    config = {name: getattr(base, name) for name in dir(base) if name.isupper()}
    with tempfile.TemporaryDirectory(prefix="gnosis-schema-") as temporary:
        db = Path(temporary) / "pilot.sqlite3"
        config["DATABASES"] = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(db)}}
        settings.configure(**config)
        django.setup()
        from django.apps import apps
        from django.core.management import call_command
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        call_command("migrate", verbosity=0, stdout=StringIO())
        call_command("seed_pilot", stdout=StringIO())
        models = list(apps.get_app_config("core").get_models())
        assert len(models) == 15
        model_tables = {model._meta.db_table: model for model in models}
        executor = MigrationExecutor(connection)
        assert not executor.migration_plan(executor.loader.graph.leaf_nodes())
        migrated = executor.loader.project_state().apps
        for model in models:
            old = migrated.get_model("core", model.__name__)
            # Migration column order can differ from current class declaration order.
            assert {f.name: f.deconstruct()[1:] for f in old._meta.local_fields} == {
                f.name: f.deconstruct()[1:] for f in model._meta.local_fields
            }, model.__name__

        def rows(sql, params=()):
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                keys = [column[0] for column in cursor.description]
                return [dict(zip(keys, row)) for row in cursor.fetchall()]

        def scalar(sql):
            with connection.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchone()[0]

        def quote(name):
            return connection.ops.quote_name(name)

        page_size = scalar("PRAGMA page_size")
        dbstat_reader = {"engine": "Python sqlite3", "version": sqlite3.sqlite_version}
        python_dbstat_error = None
        try:
            stats = {row["name"]: row for row in rows(
                "SELECT name, COUNT(*) AS pages, SUM(pgsize) AS allocated_bytes, "
                "SUM(payload) AS payload_bytes, SUM(unused) AS unused_bytes "
                "FROM dbstat GROUP BY name"
            )}
            dbstat_available = True
        except Exception as error:
            stats = {}
            dbstat_available = False
            dbstat_error = str(error)
            python_dbstat_error = str(error)
            cli = shutil.which("sqlite3")
            if cli:
                try:
                    query = ("SELECT name, COUNT(*) AS pages, SUM(pgsize) AS allocated_bytes, "
                             "SUM(payload) AS payload_bytes, SUM(unused) AS unused_bytes "
                             "FROM dbstat GROUP BY name")
                    data = json.loads(subprocess.check_output(
                        [cli, "-readonly", "-json", str(db), query], text=True,
                    ))
                    stats = {row["name"]: row for row in data}
                    dbstat_reader = {"engine": "read-only SQLite CLI", "version": subprocess.check_output(
                        [cli, "-readonly", str(db), "SELECT sqlite_version()"], text=True,
                    ).strip()}
                    dbstat_available = True
                except (subprocess.SubprocessError, ValueError) as cli_error:
                    dbstat_error += "; CLI fallback: " + str(cli_error)

        tables = []
        for entry in rows("SELECT name, sql FROM sqlite_schema WHERE type='table' ORDER BY name"):
            name = entry["name"]
            columns = rows(f"PRAGMA table_info({quote(name)})")
            fks = rows(f"PRAGMA foreign_key_list({quote(name)})")
            indexes = []
            for index in rows(f"PRAGMA index_list({quote(name)})"):
                index["columns"] = rows(f"PRAGMA index_info({quote(index['name'])})")
                index["storage"] = stats.get(index["name"])
                indexes.append(index)
            model = model_tables.get(name)
            record = {
                "table": name, "model": model.__name__ if model else None,
                "scope": "application" if model else ("sqlite internal" if name.startswith("sqlite_") else "Django infrastructure"),
                "row_count": scalar(f"SELECT COUNT(*) FROM {quote(name)}"),
                "column_count": len(columns), "columns": columns,
                "foreign_keys": fks, "indexes": indexes, "ddl": entry["sql"],
                "storage": stats.get(name),
            }
            if model:
                assert {field.column for field in model._meta.concrete_fields} == {field["name"] for field in columns}
                record["fields"] = [{
                    "name": field.name, "column": field.column,
                    "django_type": type(field).__name__, "null": field.null,
                    "primary_key": field.primary_key, "unique": field.unique,
                    "db_index": field.db_index, "max_length": field.max_length,
                    "max_digits": getattr(field, "max_digits", None),
                    "decimal_places": getattr(field, "decimal_places", None),
                    "related_table": field.remote_field.model._meta.db_table if field.is_relation else None,
                    "on_delete": field.remote_field.on_delete.__name__ if field.is_relation else None,
                    "python_default": str(field.default) if field.has_default() else None,
                } for field in model._meta.concrete_fields]
            tables.append(record)

        from core.models import Student, ProgramOutcome, Enrollment, LearningOutcome
        from core.services.lo_calculator import calculate_lo_achievement
        from core.services.po_calculator import calculate_course_po_achievement
        from core.services.student_po_calculator import calculate_student_po_achievement
        student = Student.objects.get(student_number="PILOT001")
        po = ProgramOutcome.objects.get(code="PO2", framework__program=student.program)
        trace = {}
        for code in ("PILOT311", "PILOT321"):
            enrollment = Enrollment.objects.get(student=student, offering__course__code=code)
            for lo in LearningOutcome.objects.filter(curriculum=enrollment.offering.curriculum).order_by("code"):
                trace[f"{code}.{lo.code}"] = calculate_lo_achievement(enrollment, lo)
            trace[f"{code}.PO2"] = calculate_course_po_achievement(enrollment, po)
        aggregate = calculate_student_po_achievement(student, po)
        trace["student.PO2"] = {key: aggregate[key] for key in ("score", "coverage", "status")}
        trace = {label: {key: str(value) if value is not None else None for key, value in values.items()}
                 for label, values in trace.items()}

        files = [root / "core/models.py", *sorted((root / "core/migrations").glob("*.py")),
                 *sorted((root / "core/services").glob("*.py")), root / "core/management/commands/seed_pilot.py"]
        evidence = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
        result = {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(), "source_revision": revision,
            "recipe": ["migrate", "seed_pilot"], "seed_reruns": 0, "auth_users_created": 0,
            "runtime": {"python": platform.python_version(), "django": django.get_version(), "sqlite": sqlite3.sqlite_version, "os": platform.system()},
            "pragmas": {name: scalar(f"PRAGMA {name}") for name in ["foreign_keys", "page_size", "page_count", "freelist_count", "journal_mode", "read_uncommitted"]},
            "integrity_check": scalar("PRAGMA integrity_check"), "foreign_key_check": rows("PRAGMA foreign_key_check"),
            "applied_core_migrations": [row["name"] for row in rows("SELECT name FROM django_migrations WHERE app='core' ORDER BY name")],
            "database_file_bytes": db.stat().st_size, "dbstat_available": dbstat_available,
            "dbstat_reader": dbstat_reader, "python_dbstat_error": python_dbstat_error,
            "other_dbstat_objects": [value for key, value in stats.items() if key not in {t["table"] for t in tables} and key not in {i["name"] for t in tables for i in t["indexes"]}],
            "source_sha256": evidence, "calculation_trace": trace, "tables": tables,
        }
        if not dbstat_available:
            result["dbstat_error"] = dbstat_error
        assert result["integrity_check"] == "ok" and result["foreign_key_check"] == []
        assert result["pragmas"]["foreign_keys"] == 1
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "schema_inventory.json").write_text(json.dumps(result, indent=2) + "\n")
        header = ["# Measured SQLite inventory", "", f"Source: `{revision}`; recipe: migrate then seed_pilot once; fictional data only.", "",
                  "Payload is SQLite dbstat B-tree record payload; allocated bytes are full pages. Index allocations are separate. These are November 1 checkpoint measurements, not final-stage production sizes.", "",
                  "| Scope | Table | Columns | Rows | Record payload bytes | Table allocated bytes | Index allocated bytes |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
        for table in tables:
            storage = table["storage"] or {}
            index_bytes = sum((index["storage"] or {}).get("allocated_bytes", 0) for index in table["indexes"]) if dbstat_available else "unavailable"
            header.append(f"| {table['scope']} | {table['table']} | {table['column_count']} | {table['row_count']} | {storage.get('payload_bytes', 'unavailable')} | {storage.get('allocated_bytes', 'unavailable')} | {index_bytes} |")
        header += ["", f"File bytes: {result['database_file_bytes']}; page size: {page_size}; pages: {result['pragmas']['page_count']}; free pages: {result['pragmas']['freelist_count']}.", "",
                   "SQLite catalog allocation (sqlite_schema) is in other_dbstat_objects; it is not an application table. Exact index definitions, columns, FK actions and DDL are in schema_inventory.json. Infrastructure tables are included so the physical inventory is not confused with the 15 application models.", ""]
        (args.output_dir / "table_metrics.md").write_text("\n".join(header))
        print(json.dumps({"output": str(args.output_dir), "application_tables": len(models),
                          "application_rows": sum(t["row_count"] for t in tables if t["model"]),
                          "application_columns": sum(t["column_count"] for t in tables if t["model"]),
                          "dbstat": dbstat_available, "file_bytes": result["database_file_bytes"]}))
        connection.close()


if __name__ == "__main__":
    main()
