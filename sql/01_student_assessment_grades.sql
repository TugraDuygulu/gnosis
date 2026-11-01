-- Parameters: :student_number (TEXT), :offering_id (INTEGER).
-- Include the selected enrollment regardless of status; show its status explicitly.
SELECT
    s.student_number,
    e.id AS enrollment_id,
    e.status AS enrollment_status,
    o.id AS offering_id,
    c.code AS course_code,
    a.id AS assessment_id,
    a.name AS assessment_name,
    g.score AS raw_score,
    a.max_score,
    CASE WHEN g.score IS NOT NULL
         THEN 100.0 * CAST(g.score AS REAL) / a.max_score
         ELSE NULL END AS normalized_percent,
    CASE WHEN g.id IS NULL THEN 'missing_grade'
         WHEN g.score IS NULL THEN 'null_score'
         ELSE 'recorded' END AS grade_state
FROM core_student AS s
JOIN core_enrollment AS e ON e.student_id = s.id
JOIN core_courseoffering AS o ON o.id = e.offering_id
JOIN core_course AS c ON c.id = o.course_id
JOIN core_assessment AS a ON a.offering_id = o.id
LEFT JOIN core_grade AS g
    ON g.enrollment_id = e.id AND g.assessment_id = a.id
WHERE s.student_number = :student_number
  AND o.id = :offering_id
ORDER BY a.id;
