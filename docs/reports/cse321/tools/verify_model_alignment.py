#!/usr/bin/env python3
"""Verify issue #3 against a fresh migrated pilot, never the development DB."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output-dir', type=Path, required=True)
p.add_argument('--source-ref')
a = p.parse_args()
if a.output_dir.exists():
    p.error('Choose a new directory; existing evidence is never overwritten.')
ref = a.source_ref or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
subprocess.run([sys.executable, str(ROOT/'docs/tools/measure_schema.py'),
                '--output-dir', str(a.output_dir/'fresh_schema'), '--source-ref', ref], check=True)
fresh = json.loads((a.output_dir/'fresh_schema/schema_inventory.json').read_text())
old = json.loads((ROOT/'docs/data/pilot_2026-11-01/schema_inventory.json').read_text())
actual = {t['model']: t for t in fresh['tables'] if t['model']}
expected = {t['model']: t for t in old['tables'] if t['model']}
assert actual.keys() == expected.keys() and len(actual) == 15
mermaid = (ROOT/'docs/diagrams/gnosis-erd.mmd').read_text()
blocks = dict(re.findall(r'^    (\w+) \{\n(.*?)^    \}', mermaid, re.M | re.S))
assert blocks.keys() == actual.keys()
dictionary = (ROOT/'docs/data/pilot_2026-11-01/field_dictionary.md').read_text()
sections = dict(re.findall(r'^## (\w+) — `[^`]+`\n(.*?)(?=^## |\Z)', dictionary, re.M | re.S))
assert sections.keys() == actual.keys()
edges = set(re.findall(r'^    (\w+) (\|\||\|o)--o\{ (\w+) : "(\w+)"$', mermaid, re.M))
expected_edges = set()
by_table = {t['table']: name for name, t in actual.items()}
for name, table in actual.items():
    for key in ('fields', 'columns', 'foreign_keys', 'ddl'):
        assert table[key] == expected[name][key], (name, key)
    def indexes(t):
        return sorted((i['name'], i['unique'], tuple(c['name'] for c in i['columns'])) for i in t['indexes'])
    assert indexes(table) == indexes(expected[name]), name
    columns = {f['column'] for f in table['fields']}
    assert set(re.findall(r'^        \S+ (\w+)', blocks[name], re.M)) == columns, name
    assert set(re.findall(r'^\| `(\w+)` \|', sections[name], re.M)) == columns, name
    for field in table['fields']:
        column = field['column']
        line = next(line for line in blocks[name].splitlines() if line.split()[1] == column)
        if field['primary_key']:
            assert ' PK' in line
        if field['related_table']:
            assert ' FK' in line and field['on_delete'] == 'PROTECT'
            expected_edges.add((by_table[field['related_table']], '|o' if field['null'] else '||', name, column))
        assert ('"nullable"' in line) == field['null'], (name, column)
assert edges == expected_edges and len(edges) == 20
core = list(actual.values())
unique = sum(i['unique'] for t in core for i in t['indexes'])
assert unique == 14
assert sum(len(t['indexes']) for t in core) == 34
assert sum(t['column_count'] for t in core) == 64
assert sum(t['row_count'] for t in core) == 60
nulls = sorted(f"{t['model']}.{f['column']}" for t in core for f in t['fields'] if f['null'])
assert nulls == ['CourseOffering.po_framework_id', 'Grade.score']
assert len(fresh['applied_core_migrations']) == 9
for file, digest in old['source_sha256'].items():
    assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest() == digest, file
summary = {'source_revision': ref, 'scope': 'isolated migrate + seed_pilot once; no development DB',
    'application_models': 15, 'application_columns': 64, 'foreign_keys': 20,
    'unique_secondary_indexes': unique, 'all_secondary_indexes': 34, 'pilot_rows': 60,
    'nullable_columns': nulls, 'applied_core_migrations': fresh['applied_core_migrations'],
    'model_migration_state_agreement': True, 'fresh_ddl_matches_documented_inventory': True,
    'all_erd_entities_columns_fk_cardinalities_match': True, 'field_dictionary_column_coverage': True,
    'integrity_check': fresh['integrity_check'], 'foreign_key_check': fresh['foreign_key_check'],
    'source_hashes_match_reviewed_inventory': True,
    'formal_team_or_instructor_signoff': 'not established; owner review remains separate',
    'remaining_policy_limits': ['retake/equivalence', 'publication/version immutability',
        'historical configuration edits', 'institution-wide required-course coverage',
        'raw/bulk writes bypass application validation']}
(a.output_dir/'alignment_verification.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
