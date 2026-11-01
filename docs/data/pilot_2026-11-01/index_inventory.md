# Physical application index inventory

Measured after core.0009. SQLite rowid-alias primary keys have no separate PK B-tree. Four single-column UNIQUE constraints and ten composite UNIQUE constraints produce 14 unique autoindexes. Django creates 20 nonunique FK indexes. No additional application indexes are declared.

| Table | Index | Unique | Columns, in index order | Allocated bytes |
| --- | --- | --- | --- | ---: |
| `core_assessment` | `core_assessment_offering_id_3e279ed1` | no | `offering_id` | 4096 |
| `core_assessmentlomapping` | `core_assessmentlomapping_learning_outcome_id_7c0a66b7` | no | `learning_outcome_id` | 4096 |
| `core_assessmentlomapping` | `core_assessmentlomapping_assessment_id_d56c4af7` | no | `assessment_id` | 4096 |
| `core_assessmentlomapping` | `sqlite_autoindex_core_assessmentlomapping_1` | yes | `assessment_id`, `learning_outcome_id` | 4096 |
| `core_course` | `sqlite_autoindex_core_course_1` | yes | `code` | 4096 |
| `core_coursecurriculum` | `core_coursecurriculum_course_id_18a1867e` | no | `course_id` | 4096 |
| `core_coursecurriculum` | `sqlite_autoindex_core_coursecurriculum_1` | yes | `course_id`, `version_number` | 4096 |
| `core_courseoffering` | `core_courseoffering_po_framework_id_9729f169` | no | `po_framework_id` | 4096 |
| `core_courseoffering` | `core_courseoffering_instructor_id_7a8603ff` | no | `instructor_id` | 4096 |
| `core_courseoffering` | `core_courseoffering_curriculum_id_f20e5d4e` | no | `curriculum_id` | 4096 |
| `core_courseoffering` | `core_courseoffering_course_id_17cf7317` | no | `course_id` | 4096 |
| `core_courseoffering` | `sqlite_autoindex_core_courseoffering_1` | yes | `course_id`, `year`, `term`, `section` | 4096 |
| `core_coursepocontribution` | `core_coursepocontribution_program_outcome_id_67c6910c` | no | `program_outcome_id` | 4096 |
| `core_coursepocontribution` | `core_coursepocontribution_curriculum_id_df1bff12` | no | `curriculum_id` | 4096 |
| `core_coursepocontribution` | `sqlite_autoindex_core_coursepocontribution_1` | yes | `curriculum_id`, `program_outcome_id` | 4096 |
| `core_enrollment` | `core_enrollment_student_id_e42e49b3` | no | `student_id` | 4096 |
| `core_enrollment` | `core_enrollment_offering_id_3bc3e4fc` | no | `offering_id` | 4096 |
| `core_enrollment` | `sqlite_autoindex_core_enrollment_1` | yes | `student_id`, `offering_id` | 4096 |
| `core_grade` | `core_grade_enrollment_id_022947b3` | no | `enrollment_id` | 4096 |
| `core_grade` | `core_grade_assessment_id_aa4db391` | no | `assessment_id` | 4096 |
| `core_grade` | `sqlite_autoindex_core_grade_1` | yes | `enrollment_id`, `assessment_id` | 4096 |
| `core_instructor` | `sqlite_autoindex_core_instructor_1` | yes | `email` | 4096 |
| `core_learningoutcome` | `core_learningoutcome_curriculum_id_856a4c62` | no | `curriculum_id` | 4096 |
| `core_learningoutcome` | `sqlite_autoindex_core_learningoutcome_1` | yes | `curriculum_id`, `code` | 4096 |
| `core_lopomapping` | `core_lopomapping_program_outcome_id_757c9376` | no | `program_outcome_id` | 4096 |
| `core_lopomapping` | `core_lopomapping_learning_outcome_id_40bbe6c3` | no | `learning_outcome_id` | 4096 |
| `core_lopomapping` | `sqlite_autoindex_core_lopomapping_1` | yes | `learning_outcome_id`, `program_outcome_id` | 4096 |
| `core_poframework` | `core_poframework_program_id_867444d4` | no | `program_id` | 4096 |
| `core_poframework` | `sqlite_autoindex_core_poframework_1` | yes | `program_id`, `version_number` | 4096 |
| `core_program` | `sqlite_autoindex_core_program_1` | yes | `code` | 4096 |
| `core_programoutcome` | `core_programoutcome_framework_id_e5357323` | no | `framework_id` | 4096 |
| `core_programoutcome` | `sqlite_autoindex_core_programoutcome_1` | yes | `framework_id`, `code` | 4096 |
| `core_student` | `core_student_program_id_4836c078` | no | `program_id` | 4096 |
| `core_student` | `sqlite_autoindex_core_student_1` | yes | `student_number` | 4096 |
