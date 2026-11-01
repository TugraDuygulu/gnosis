# Measured SQLite inventory

Source: `31890b81b43c9479c4d4ec5ea8fa4b87ee48f403`; recipe: migrate then seed_pilot once; fictional data only.

Payload is SQLite dbstat B-tree record payload; allocated bytes are full pages. Index allocations are separate. These are November 1 checkpoint measurements, not final-stage production sizes.

| Scope | Table | Columns | Rows | Record payload bytes | Table allocated bytes | Index allocated bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Django infrastructure | auth_group | 2 | 0 | 0 | 4096 | 4096 |
| Django infrastructure | auth_group_permissions | 3 | 0 | 0 | 4096 | 12288 |
| Django infrastructure | auth_permission | 4 | 84 | 3610 | 4096 | 8192 |
| Django infrastructure | auth_user | 11 | 0 | 0 | 4096 | 4096 |
| Django infrastructure | auth_user_groups | 3 | 0 | 0 | 4096 | 12288 |
| Django infrastructure | auth_user_user_permissions | 3 | 0 | 0 | 4096 | 12288 |
| application | core_assessment | 5 | 4 | 58 | 4096 | 4096 |
| application | core_assessmentlomapping | 4 | 6 | 44 | 4096 | 12288 |
| application | core_course | 4 | 2 | 96 | 4096 | 4096 |
| application | core_coursecurriculum | 4 | 2 | 21 | 4096 | 8192 |
| application | core_courseoffering | 9 | 2 | 54 | 4096 | 20480 |
| application | core_coursepocontribution | 4 | 5 | 38 | 4096 | 12288 |
| application | core_enrollment | 4 | 4 | 48 | 4096 | 12288 |
| application | core_grade | 4 | 8 | 57 | 4096 | 12288 |
| application | core_instructor | 3 | 1 | 62 | 4096 | 4096 |
| application | core_learningoutcome | 4 | 4 | 224 | 4096 | 8192 |
| application | core_lopomapping | 4 | 7 | 53 | 4096 | 12288 |
| application | core_poframework | 4 | 1 | 10 | 4096 | 8192 |
| application | core_program | 3 | 1 | 45 | 4096 | 4096 |
| application | core_programoutcome | 4 | 11 | 2225 | 4096 | 8192 |
| application | core_student | 4 | 2 | 56 | 4096 | 8192 |
| Django infrastructure | django_admin_log | 8 | 0 | 0 | 4096 | 8192 |
| Django infrastructure | django_content_type | 3 | 21 | 401 | 4096 | 4096 |
| Django infrastructure | django_migrations | 4 | 27 | 1774 | 4096 | 0 |
| Django infrastructure | django_session | 3 | 0 | 0 | 4096 | 8192 |
| sqlite internal | sqlite_sequence | 2 | 21 | 414 | 4096 | 0 |

File bytes: 344064; page size: 4096; pages: 84; free pages: 0.

SQLite catalog allocation (sqlite_schema) is in other_dbstat_objects; it is not an application table. Exact index definitions, columns, FK actions and DDL are in schema_inventory.json. Infrastructure tables are included so the physical inventory is not confused with the 15 application models.
