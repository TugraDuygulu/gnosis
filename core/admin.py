from django.contrib import admin
from .models import (
    Program, Course, Instructor, Student,
    CourseCurriculum, CourseOffering, Enrollment,
    Assessment, Grade, LearningOutcome,
    AssessmentLOMapping, POFramework,
    ProgramOutcome, LOPOMapping,
)

admin.site.register([
    Program, Course, Instructor, Student,
    CourseCurriculum, CourseOffering, Enrollment,
    Assessment, Grade, LearningOutcome,
    AssessmentLOMapping, POFramework,
    ProgramOutcome, LOPOMapping,
])