-- Parameters: :student_number (TEXT), :offering_id (INTEGER).
-- All curriculum LOs are returned, even when they have no configured evidence.
-- As in calculate_lo_achievement(), an individual enrollment is not status-filtered.
WITH selected_enrollment AS (
    SELECT e.id AS enrollment_id, s.student_number,
           o.id AS offering_id, o.curriculum_id
    FROM core_student AS s
    JOIN core_enrollment AS e ON e.student_id = s.id
    JOIN core_courseoffering AS o ON o.id = e.offering_id
    WHERE s.student_number = :student_number AND o.id = :offering_id
), offering_mappings AS (
    SELECT m.id AS mapping_id, m.learning_outcome_id, m.weight,
           a.id AS assessment_id, a.max_score
    FROM core_assessmentlomapping AS m
    JOIN core_assessment AS a ON a.id = m.assessment_id
    WHERE a.offering_id = :offering_id
), evidence_totals AS (
    SELECT se.enrollment_id, se.student_number, se.offering_id,
           lo.id AS lo_id, lo.code AS lo_code,
           COUNT(m.mapping_id) AS mapped_assessment_count,
           COUNT(g.score) AS graded_assessment_count,
           COALESCE(SUM(CAST(m.weight AS REAL)), 0.0) AS total_mapping_weight,
           COALESCE(SUM(CASE WHEN g.score IS NOT NULL
                             THEN CAST(m.weight AS REAL) ELSE 0.0 END), 0.0)
               AS graded_mapping_weight,
           SUM(CASE WHEN g.score IS NOT NULL
                    THEN (100.0 * CAST(g.score AS REAL) / m.max_score) * m.weight
                    ELSE NULL END) AS weighted_score_total
    FROM selected_enrollment AS se
    JOIN core_learningoutcome AS lo ON lo.curriculum_id = se.curriculum_id
    LEFT JOIN offering_mappings AS m ON m.learning_outcome_id = lo.id
    LEFT JOIN core_grade AS g
        ON g.enrollment_id = se.enrollment_id AND g.assessment_id = m.assessment_id
    GROUP BY se.enrollment_id, se.student_number, se.offering_id, lo.id, lo.code
)
SELECT enrollment_id, student_number, offering_id, lo_id, lo_code,
       mapped_assessment_count, graded_assessment_count,
       total_mapping_weight, graded_mapping_weight,
       weighted_score_total / NULLIF(graded_mapping_weight, 0.0) AS attainment_percent,
       CASE WHEN total_mapping_weight > 0.0
            THEN 100.0 * graded_mapping_weight / total_mapping_weight
            ELSE 0.0 END AS coverage_percent,
       -- Positive mapping weights make count equality equivalent to all weight graded.
       -- Counts avoid deciding completeness using rounded floating-point coverage.
       CASE WHEN graded_assessment_count = 0 THEN 'no_data'
            WHEN graded_assessment_count = mapped_assessment_count THEN 'complete'
            ELSE 'provisional' END AS evidence_status
FROM evidence_totals
ORDER BY lo_id;
