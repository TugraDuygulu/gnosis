-- Parameter: :offering_id (INTEGER).
-- Equal-student mean of available-evidence LO scores for ACTIVE enrollments.
-- Include provisional students; exclude no-data students from score AVG only.
-- Mean coverage includes every active enrollment; no-data coverage is zero.
WITH selected_offering AS (
    SELECT id AS offering_id, curriculum_id
    FROM core_courseoffering WHERE id = :offering_id
), offering_mappings AS (
    SELECT m.id AS mapping_id, m.learning_outcome_id, m.weight,
           a.id AS assessment_id, a.max_score
    FROM core_assessmentlomapping AS m
    JOIN core_assessment AS a ON a.id = m.assessment_id
    WHERE a.offering_id = :offering_id
), student_evidence AS (
    SELECT o.offering_id, lo.id AS lo_id, lo.code AS lo_code,
           e.id AS enrollment_id,
           COUNT(m.mapping_id) AS mapped_assessment_count,
           COUNT(g.score) AS graded_assessment_count,
           COALESCE(SUM(CAST(m.weight AS REAL)), 0.0) AS total_mapping_weight,
           COALESCE(SUM(CASE WHEN g.score IS NOT NULL
                             THEN CAST(m.weight AS REAL) ELSE 0.0 END), 0.0)
               AS graded_mapping_weight,
           SUM(CASE WHEN g.score IS NOT NULL
                    THEN (100.0 * CAST(g.score AS REAL) / m.max_score) * m.weight
                    ELSE NULL END) AS weighted_score_total
    FROM selected_offering AS o
    JOIN core_learningoutcome AS lo ON lo.curriculum_id = o.curriculum_id
    JOIN core_enrollment AS e ON e.offering_id = o.offering_id AND e.status = 'active'
    LEFT JOIN offering_mappings AS m ON m.learning_outcome_id = lo.id
    LEFT JOIN core_grade AS g
        ON g.enrollment_id = e.id AND g.assessment_id = m.assessment_id
    GROUP BY o.offering_id, lo.id, lo.code, e.id
), student_results AS (
    SELECT *, weighted_score_total / NULLIF(graded_mapping_weight, 0.0)
                  AS attainment_percent,
           CASE WHEN total_mapping_weight > 0.0
                THEN 100.0 * graded_mapping_weight / total_mapping_weight
                ELSE 0.0 END AS coverage_percent,
           CASE WHEN graded_assessment_count = 0 THEN 'no_data'
                WHEN graded_assessment_count = mapped_assessment_count THEN 'complete'
                ELSE 'provisional' END AS evidence_status
    FROM student_evidence
)
SELECT o.offering_id, lo.id AS lo_id, lo.code AS lo_code,
       COUNT(r.enrollment_id) AS active_students,
       COUNT(r.attainment_percent) AS students_with_evidence,
       COALESCE(SUM(CASE WHEN r.evidence_status = 'complete' THEN 1 ELSE 0 END), 0)
           AS complete_students,
       COALESCE(SUM(CASE WHEN r.evidence_status = 'provisional' THEN 1 ELSE 0 END), 0)
           AS provisional_students,
       COALESCE(SUM(CASE WHEN r.evidence_status = 'no_data' THEN 1 ELSE 0 END), 0)
           AS no_data_students,
       AVG(r.attainment_percent) AS mean_attainment_percent,
       AVG(r.coverage_percent) AS mean_coverage_percent
FROM selected_offering AS o
JOIN core_learningoutcome AS lo ON lo.curriculum_id = o.curriculum_id
LEFT JOIN student_results AS r ON r.offering_id = o.offering_id AND r.lo_id = lo.id
GROUP BY o.offering_id, lo.id, lo.code
ORDER BY lo.id;
