# Actual SQL results — fictional pilot

Source `1106cd01d572b1a73af433ab30e7bf7ab3854db1`. Fresh migrate + seed_pilot once. All 17 SQL verification cases passed.

Decimal references and full SQL rows are retained in actual_results.json. Numeric display below uses at most nine decimals; SQL itself does not round.

## PILOT001.PILOT311

Parameters: `{"offering_id": 1, "student_number": "PILOT001"}`

Query 1

| assessment_name | raw_score | max_score | normalized_percent | grade_state |
| --- | --- | --- | --- | --- |
| Midterm | 90 | 100 | 90 | recorded |
| Project | 40 | 50 | 80 | recorded |

Query 2

| lo_code | total_mapping_weight | graded_mapping_weight | attainment_percent | coverage_percent | evidence_status |
| --- | --- | --- | --- | --- | --- |
| LO1 | 100 | 100 | 86 | 100 | complete |
| LO2 | 140 | 140 | 82.857142857 | 100 | complete |

## PILOT002.PILOT311

Parameters: `{"offering_id": 1, "student_number": "PILOT002"}`

Query 1

| assessment_name | raw_score | max_score | normalized_percent | grade_state |
| --- | --- | --- | --- | --- |
| Midterm | 70 | 100 | 70 | recorded |
| Project | NULL | 50 | NULL | null_score |

Query 2

| lo_code | total_mapping_weight | graded_mapping_weight | attainment_percent | coverage_percent | evidence_status |
| --- | --- | --- | --- | --- | --- |
| LO1 | 100 | 60 | 70 | 60 | provisional |
| LO2 | 140 | 40 | 70 | 28.571428571 | provisional |

## PILOT311.summary

Parameters: `{"offering_id": 1}`

Query 3

| lo_code | active_students | students_with_evidence | complete_students | provisional_students | no_data_students | mean_attainment_percent | mean_coverage_percent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LO1 | 2 | 2 | 1 | 1 | 0 | 78 | 80 |
| LO2 | 2 | 2 | 1 | 1 | 0 | 76.428571429 | 64.285714286 |

## PILOT001.PILOT321

Parameters: `{"offering_id": 2, "student_number": "PILOT001"}`

Query 1

| assessment_name | raw_score | max_score | normalized_percent | grade_state |
| --- | --- | --- | --- | --- |
| Midterm | 0 | 100 | 0 | recorded |
| Lab | NULL | 50 | NULL | null_score |

Query 2

| lo_code | total_mapping_weight | graded_mapping_weight | attainment_percent | coverage_percent | evidence_status |
| --- | --- | --- | --- | --- | --- |
| LO1 | 100 | 100 | 0 | 100 | complete |
| LO2 | 100 | 0 | NULL | 0 | no_data |

## PILOT002.PILOT321

Parameters: `{"offering_id": 2, "student_number": "PILOT002"}`

Query 1

| assessment_name | raw_score | max_score | normalized_percent | grade_state |
| --- | --- | --- | --- | --- |
| Midterm | 80 | 100 | 80 | recorded |
| Lab | 40 | 50 | 80 | recorded |

Query 2

| lo_code | total_mapping_weight | graded_mapping_weight | attainment_percent | coverage_percent | evidence_status |
| --- | --- | --- | --- | --- | --- |
| LO1 | 100 | 100 | 80 | 100 | complete |
| LO2 | 100 | 100 | 80 | 100 | complete |

## PILOT321.summary

Parameters: `{"offering_id": 2}`

Query 3

| lo_code | active_students | students_with_evidence | complete_students | provisional_students | no_data_students | mean_attainment_percent | mean_coverage_percent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LO1 | 2 | 2 | 2 | 0 | 0 | 40 | 100 |
| LO2 | 2 | 1 | 1 | 0 | 1 | 80 | 50 |
