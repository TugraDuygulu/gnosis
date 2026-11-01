#!/usr/bin/env python3
"""Execute and verify the three saved SQL statements in a fresh fictional DB only.

Usage: .venv/bin/python sql/verify_queries.py --output-dir /tmp/gnosis-sql-review
No database-path argument is accepted. The temporary DB is always deleted.
"""
import argparse
import hashlib
import importlib
import json
import math
import platform
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = Path(__file__).resolve().parent
TOLERANCE = 1e-9  # absolute percentage points; counts/status/NULL must match exactly.
FILES = {1: '01_student_assessment_grades.sql', 2: '02_student_lo_attainment.sql',
         3: '03_offering_lo_summary.sql'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-ref', help='Explicit source revision for a source-only copy.')
    args = parser.parse_args()
    # Fail rather than silently overwrite reviewed evidence or another directory.
    if args.output_dir.exists():
        parser.error('Choose a new output directory; existing output is never overwritten.')
    revision = args.source_ref or subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    sys.path.insert(0, str(ROOT))
    import django
    from django.conf import settings
    base = importlib.import_module('config.settings')
    config = {name: getattr(base, name) for name in dir(base) if name.isupper()}
    with tempfile.TemporaryDirectory(prefix='gnosis-sql-issue4-') as temporary:
        config['DATABASES'] = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                                          'NAME': str(Path(temporary) / 'fictional.sqlite3')}}
        settings.configure(**config)
        django.setup()
        from django.core.management import call_command
        from django.db import connection, transaction
        from core.models import Assessment, AssessmentLOMapping, CourseOffering, Enrollment, Grade, LearningOutcome, Student
        from core.services.lo_calculator import calculate_lo_achievement
        call_command('migrate', verbosity=0, stdout=StringIO())
        call_command('seed_pilot', stdout=StringIO())
        sql = {number: (SQL_DIR / filename).read_text() for number, filename in FILES.items()}

        def query(number, student='PILOT001', offering=None):
            if offering is None:
                offering = offerings['PILOT311']
            # Raw sqlite3 cursor accepts named bindings; shares Django's transaction.
            cursor = connection.connection.execute(sql[number], {
                'student_number': student, 'offering_id': offering})
            return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

        def reference(student, offering):
            enrollment = Enrollment.objects.get(student__student_number=student, offering_id=offering)
            return {lo.pk: calculate_lo_achievement(enrollment, lo) for lo in
                    LearningOutcome.objects.filter(curriculum=enrollment.offering.curriculum)}

        differences = []

        def close(actual, expected):
            if expected is None:
                assert actual is None, (actual, expected)
            else:
                assert actual is not None and math.isfinite(actual), actual
                delta = abs(Decimal(str(actual)) - Decimal(str(expected)))
                differences.append(float(delta))
                assert delta <= Decimal(str(TOLERANCE)), (actual, str(expected), str(delta))

        def check_services(student, offering):
            refs = reference(student, offering)
            rows = query(2, student, offering)
            assert set(refs) == {row['lo_id'] for row in rows}
            for row in rows:
                expected = refs[row['lo_id']]
                close(row['attainment_percent'], expected['score'])
                close(row['coverage_percent'], expected['coverage'])
                assert row['evidence_status'] == expected['status']
            return rows

        def check_summary(offering):
            students = list(Enrollment.objects.filter(offering_id=offering, status='active')
                            .select_related('student', 'offering'))
            for row in query(3, offering=offering):
                lo = LearningOutcome.objects.get(pk=row['lo_id'])
                refs = [calculate_lo_achievement(e, lo) for e in students]
                scored = [r['score'] for r in refs if r['score'] is not None]
                close(row['mean_attainment_percent'], sum(scored) / len(scored) if scored else None)
                close(row['mean_coverage_percent'], sum(r['coverage'] for r in refs) / len(refs) if refs else None)
                assert row['active_students'] == len(refs)
                assert row['students_with_evidence'] == len(scored)
                for status in ('complete', 'provisional', 'no_data'):
                    assert row[status + '_students'] == sum(r['status'] == status for r in refs)

        offerings = {code: CourseOffering.objects.get(course__code=code).pk
                     for code in ('PILOT311', 'PILOT321')}
        # Capture baseline BEFORE edge-case test mutations, which are rolled back.
        observed = {}
        for code, offering in offerings.items():
            for student in ('PILOT001', 'PILOT002'):
                key = f'{student}.{code}'
                observed[key] = {'parameters': {'student_number': student, 'offering_id': offering},
                                 'query1': query(1, student, offering), 'query2': query(2, student, offering),
                                 'django_lo_reference': {str(k): {f: str(v) if v is not None else None
                                                               for f, v in result.items()}
                                                         for k, result in reference(student, offering).items()}}
            observed[code + '.summary'] = {'parameters': {'offering_id': offering},
                                           'query3': query(3, offering=offering)}

        # Independent hand calculations, not generated from SQL/service outputs.
        manual = {
            'PILOT001.PILOT311': [(86, 100, 'complete'), (Fraction(580, 7), 100, 'complete')],
            'PILOT002.PILOT311': [(70, 60, 'provisional'), (70, Fraction(200, 7), 'provisional')],
            'PILOT001.PILOT321': [(0, 100, 'complete'), (None, 0, 'no_data')],
            'PILOT002.PILOT321': [(80, 100, 'complete'), (80, 100, 'complete')],
        }
        summary_manual = {'PILOT311': [(78, 80), (Fraction(535, 7), Fraction(450, 7))],
                          'PILOT321': [(40, 100), (80, 50)]}

        def decimal_value(value):
            return Decimal(value.numerator) / Decimal(value.denominator) if isinstance(value, Fraction) else value

        class SQLVerification(unittest.TestCase):
            def setUp(self):
                self.atomic = transaction.atomic()
                self.atomic.__enter__()
                self.offering = CourseOffering.objects.get(pk=offerings['PILOT311'])
                self.enrollment = Enrollment.objects.get(student__student_number='PILOT001', offering=self.offering)

            def tearDown(self):
                transaction.set_rollback(True)
                self.atomic.__exit__(None, None, None)

            def test_baseline_grades_normalize_raw_maximum(self):
                for key, case in observed.items():
                    if 'query1' not in case:
                        continue
                    for row in case['query1']:
                        expected = None if row['raw_score'] is None else (
                            Decimal(str(row['raw_score'])) / Decimal(str(row['max_score'])) * 100)
                        close(row['normalized_percent'], expected)
                        self.assertEqual(row['student_number'], case['parameters']['student_number'])
                        self.assertEqual(row['offering_id'], case['parameters']['offering_id'])
                rows = query(1)
                self.assertEqual([(r['raw_score'], r['max_score']) for r in rows], [(90, 100), (40, 50)])
                self.assertEqual([r['normalized_percent'] for r in rows], [90, 80])

            def test_baseline_lo_matches_manual_and_decimal_services(self):
                for key, expected in manual.items():
                    student, code = key.split('.')
                    rows = check_services(student, offerings[code])
                    for row, (score, coverage, status) in zip(rows, expected, strict=True):
                        close(row['attainment_percent'], decimal_value(score))
                        close(row['coverage_percent'], decimal_value(coverage))
                        self.assertEqual(row['evidence_status'], status)

            def test_baseline_summary_matches_manual_and_service_mean(self):
                for code, expected in summary_manual.items():
                    check_summary(offerings[code])
                    for row, (score, coverage) in zip(query(3, offering=offerings[code]), expected, strict=True):
                        close(row['mean_attainment_percent'], decimal_value(score))
                        close(row['mean_coverage_percent'], decimal_value(coverage))

            def test_grade_row_absence_null_and_zero_are_distinct(self):
                rows = query(1, offering=offerings['PILOT321'])
                self.assertEqual([(r['grade_state'], r['normalized_percent']) for r in rows],
                                 [('recorded', 0), ('null_score', None)])
                project = self.offering.assessments.get(name='Project')
                Grade.objects.filter(enrollment=self.enrollment, assessment=project).delete()
                self.assertEqual(query(1)[1]['grade_state'], 'missing_grade')
                Grade.objects.create(enrollment=self.enrollment, assessment=project, score=None)
                self.assertEqual(query(1)[1]['grade_state'], 'null_score')
                check_services('PILOT001', self.offering.pk)

            def test_all_missing_and_explicit_null_produce_same_lo(self):
                Grade.objects.filter(enrollment=self.enrollment).delete()
                missing = query(2)
                for a in self.offering.assessments.all():
                    Grade.objects.create(enrollment=self.enrollment, assessment=a, score=None)
                self.assertEqual(missing, query(2))
                self.assertTrue(all(r['attainment_percent'] is None and r['coverage_percent'] == 0
                                    and r['evidence_status'] == 'no_data' for r in missing))
                check_services('PILOT001', self.offering.pk)

            def test_all_recorded_zero_is_complete_evidence(self):
                for grade in Grade.objects.filter(enrollment=self.enrollment):
                    grade.score = 0
                    grade.save()
                for row in check_services('PILOT001', self.offering.pk):
                    self.assertEqual((row['attainment_percent'], row['coverage_percent'], row['evidence_status']),
                                     (0, 100, 'complete'))
                check_summary(self.offering.pk)

            def test_instructor_examples_both_assessments_out_of_100(self):
                project = self.offering.assessments.get(name='Project')
                project.max_score = 100
                project.save()
                grade = Grade.objects.get(enrollment=self.enrollment, assessment=project)
                grade.score = 80
                grade.save()
                rows = check_services('PILOT001', self.offering.pk)
                close(rows[0]['attainment_percent'], 86)
                close(rows[1]['attainment_percent'], Decimal(580) / Decimal(7))
                self.assertEqual(rows[1]['total_mapping_weight'], 140)

            def test_other_student_changes_do_not_leak_into_individual_queries(self):
                before = (query(1), query(2))
                for grade in Grade.objects.filter(enrollment__student__student_number='PILOT002'):
                    grade.score = 0
                    grade.save()
                self.assertEqual(before, (query(1), query(2)))

            def test_same_curriculum_other_offering_is_isolated(self):
                before = (query(1), query(2), query(3))
                other = CourseOffering.objects.create(course=self.offering.course, curriculum=self.offering.curriculum,
                    instructor=self.offering.instructor, po_framework=self.offering.po_framework,
                    year=2027, term='Fall', section='ISOLATED')
                enrollment = Enrollment.objects.create(student=self.enrollment.student, offering=other)
                assessment = Assessment.objects.create(offering=other, name='Midterm', max_score=100)
                Grade.objects.create(enrollment=enrollment, assessment=assessment, score=1)
                for lo in self.offering.curriculum.learning_outcomes.all():
                    AssessmentLOMapping.objects.create(assessment=assessment, learning_outcome=lo, weight=999)
                self.assertEqual(before, (query(1), query(2), query(3)))
                check_services('PILOT001', other.pk)
                check_summary(other.pk)

            def test_unmapped_lo_is_retained_with_no_data(self):
                LearningOutcome.objects.create(curriculum=self.offering.curriculum, code='UNMAPPED', description='Test only')
                row = check_services('PILOT001', self.offering.pk)[-1]
                self.assertEqual((row['mapped_assessment_count'], row['total_mapping_weight'],
                                  row['attainment_percent'], row['evidence_status']), (0, 0, None, 'no_data'))
                check_summary(self.offering.pk)

            def test_no_evidence_student_changes_coverage_not_mean_score(self):
                before = query(3)
                student = Student.objects.create(program=self.enrollment.student.program,
                    student_number='SQL_NO_DATA', full_name='Fictional SQL no-data student')
                Enrollment.objects.create(student=student, offering=self.offering)
                for old, new in zip(before, query(3), strict=True):
                    self.assertEqual(new['active_students'], 3)
                    self.assertEqual(new['no_data_students'], 1)
                    close(new['mean_attainment_percent'], old['mean_attainment_percent'])
                    close(new['mean_coverage_percent'], Decimal(str(old['mean_coverage_percent'])) * 2 / 3)
                check_summary(self.offering.pk)

            def test_all_students_ungraded_summary_has_null_mean(self):
                Grade.objects.filter(enrollment__offering=self.offering).delete()
                check_summary(self.offering.pk)
                for row in query(3):
                    self.assertEqual((row['active_students'], row['students_with_evidence'], row['no_data_students'],
                                      row['mean_attainment_percent'], row['mean_coverage_percent']), (2, 0, 2, None, 0))

            def test_inactive_excluded_from_summary_but_individual_history_retained(self):
                Enrollment.objects.filter(student__student_number='PILOT002', offering=self.offering).update(status='withdrawn')
                self.assertTrue(query(1, 'PILOT002'))
                check_services('PILOT002', self.offering.pk)
                check_summary(self.offering.pk)
                for row in query(3):
                    self.assertEqual((row['active_students'], row['complete_students']), (1, 1))

            def test_empty_roster_preserves_los_and_null_averages(self):
                Enrollment.objects.filter(offering=self.offering).update(status='withdrawn')
                for row in query(3):
                    self.assertEqual((row['active_students'], row['students_with_evidence'], row['no_data_students'],
                                      row['mean_attainment_percent'], row['mean_coverage_percent']), (0, 0, 0, None, None))
                check_summary(self.offering.pk)

            def test_nonexistent_student_offering_and_unenrolled_student_return_no_rows(self):
                for number in (1, 2):
                    self.assertEqual(query(number, 'NOT_ENROLLED'), [])
                    self.assertEqual(query(number, offering=-1), [])
                self.assertEqual(query(3, offering=-1), [])
                outsider = Student.objects.create(program=self.enrollment.student.program,
                    student_number='SQL_OUTSIDER', full_name='Fictional unenrolled student')
                for number in (1, 2):
                    self.assertEqual(query(number, outsider.student_number), [])

            def test_fractional_weights_do_not_round_coverage_into_completeness(self):
                lo = self.offering.curriculum.learning_outcomes.get(code='LO1')
                for mapping in AssessmentLOMapping.objects.filter(learning_outcome=lo):
                    mapping.weight = Decimal('999.99') if mapping.assessment.name == 'Midterm' else Decimal('0.01')
                    mapping.save()
                grade = Grade.objects.get(enrollment=self.enrollment, assessment__name='Project')
                grade.score = None
                grade.save()
                row = check_services('PILOT001', self.offering.pk)[0]
                close(row['coverage_percent'], Decimal('99.999'))
                self.assertEqual(row['evidence_status'], 'provisional')

            def test_fractional_normalized_grade_uses_real_division(self):
                assessment = self.offering.assessments.get(name='Midterm')
                # Keep every affected grade valid before reducing the maximum.
                for grade in Grade.objects.filter(assessment=assessment):
                    grade.score = 1
                    grade.save()
                assessment.max_score = 3
                assessment.save()
                close(query(1)[0]['normalized_percent'], Decimal(100) / 3)
                check_services('PILOT001', self.offering.pk)
                check_summary(self.offering.pk)

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SQLVerification)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful():
            raise SystemExit(1)
        assert connection.connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert connection.connection.execute('PRAGMA foreign_key_check').fetchall() == []
        # Ensure baseline test edits were all rolled back before emitting evidence.
        for code, offering in offerings.items():
            assert query(3, offering=offering) == observed[code + '.summary']['query3']
        sources = [*SQL_DIR.glob('*.sql'), Path(__file__), ROOT/'core/models.py',
                   *sorted((ROOT/'core/migrations').glob('*.py')),
                   *sorted((ROOT/'core/services').glob('*.py')),
                   ROOT/'core/management/commands/seed_pilot.py']
        metadata = {'source_revision': revision, 'recipe': ['migrate', 'seed_pilot once'],
            'database': 'fresh temporary SQLite; deleted after run; no development DB connection',
            'runtime': {'python': platform.python_version(), 'django': django.get_version(), 'sqlite': sqlite3.sqlite_version},
            'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'absolute_tolerance_percentage_points': TOLERANCE,
            'maximum_observed_absolute_difference': max(differences, default=0),
            'comparison_count': len(differences),
            'passed_cases': [name for name in unittest.defaultTestLoader.getTestCaseNames(SQLVerification)],
            'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
        args.output_dir.mkdir(parents=True)
        (args.output_dir/'actual_results.json').write_text(json.dumps(observed, indent=2)+'\n')
        (args.output_dir/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
        manual_text = {key: [[str(score) if score is not None else None, str(coverage), status]
                            for score, coverage, status in rows] for key, rows in manual.items()}
        (args.output_dir/'manual_expectations.json').write_text(json.dumps({
            'columns': ['attainment_percent', 'coverage_percent', 'status'], 'student_lo': manual_text,
            'summary_columns': ['mean_attainment_percent', 'mean_coverage_percent'],
            'summary': {key: [[str(a), str(b)] for a, b in rows] for key, rows in summary_manual.items()}
        }, indent=2)+'\n')
        # Compact, report-ready baseline output tables; JSON retains every SQL column.
        def fmt(value):
            return 'NULL' if value is None else (f'{value:.9f}'.rstrip('0').rstrip('.') if isinstance(value, float) else str(value))
        report = ['# Actual SQL results — fictional pilot', '',
                  f'Source `{revision}`. Fresh migrate + seed_pilot once. All {result.testsRun} SQL verification cases passed.', '',
                  'Decimal references and full SQL rows are retained in actual_results.json. Numeric display below uses at most nine decimals; SQL itself does not round.', '']
        for key, case in observed.items():
            report += [f'## {key}', '', f"Parameters: `{json.dumps(case['parameters'], sort_keys=True)}`", '']
            for query_number, columns in [(1, ['assessment_name', 'raw_score', 'max_score', 'normalized_percent', 'grade_state']),
                (2, ['lo_code', 'total_mapping_weight', 'graded_mapping_weight', 'attainment_percent', 'coverage_percent', 'evidence_status']),
                (3, ['lo_code', 'active_students', 'students_with_evidence', 'complete_students', 'provisional_students', 'no_data_students', 'mean_attainment_percent', 'mean_coverage_percent'])]:
                if 'query'+str(query_number) not in case:
                    continue
                report += [f'Query {query_number}', '', '| '+' | '.join(columns)+' |', '| '+' | '.join('---' for _ in columns)+' |']
                for row in case['query'+str(query_number)]:
                    report.append('| '+' | '.join(fmt(row[c]) for c in columns)+' |')
                report.append('')
        (args.output_dir/'actual_results.md').write_text('\n'.join(report))
        print(json.dumps({key: metadata[key] for key in ('tests_run', 'comparison_count', 'maximum_observed_absolute_difference')}, indent=2))
        print('Evidence:', args.output_dir)
        connection.close()


if __name__ == '__main__':
    main()
