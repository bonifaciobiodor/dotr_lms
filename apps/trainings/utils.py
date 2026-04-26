import datetime


def award_competencies(enrollment):
    """
    Called when an enrollment is marked completed.
    For each Competency linked to the training:
      - If no EmployeeCompetency record exists, create one at current_level=1.
      - If one exists and current_level < 4, increment current_level by 1.
    assessment_date is set to today so the gap analysis reflects the update.
    """
    from apps.competencies.models import EmployeeCompetency
    for competency in enrollment.training.competencies.all():
        ec, created = EmployeeCompetency.objects.get_or_create(
            user=enrollment.user,
            competency=competency,
            defaults={
                'current_level': 1,
                'target_level': 2,
                'assessment_date': datetime.date.today(),
            },
        )
        if not created and ec.current_level < 4:
            ec.current_level = min(ec.current_level + 1, 4)
            ec.assessment_date = datetime.date.today()
            ec.save()
