"""
Management command to populate DOTR-LMS with demo data.
Run: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = 'Seed the database with sample DOTR-LMS data'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding DOTR-LMS database...')
        self._create_divisions()
        self._create_users()
        self._create_competencies()
        self._create_trainings()
        self._assign_competencies()
        self._create_certificate_template()
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))
        self.stdout.write('\n📋 Demo Accounts:')
        self.stdout.write('  Admin:      admin / admin123')
        self.stdout.write('  HR:         hr_officer / hr123')
        self.stdout.write('  Supervisor: supervisor1 / super123')
        self.stdout.write('  Employee:   employee1 / emp123')

    def _create_divisions(self):
        from apps.accounts.models import Division
        divisions_data = [
            ('Office of the Secretary', 'OSEC'),
            ('Information Technology Division', 'ITD'),
            ('Human Resource Division', 'HRD'),
            ('Finance Division', 'FD'),
            ('Legal Division', 'LD'),
            ('Planning Division', 'PD'),
            ('Engineering Division', 'ED'),
            ('Administrative Division', 'AD'),
        ]
        for name, code in divisions_data:
            Division.objects.get_or_create(code=code, defaults={'name': name})
        self.stdout.write(f'  ✓ {len(divisions_data)} divisions created')

    def _create_users(self):
        from apps.accounts.models import User, Division
        itd = Division.objects.get(code='ITD')
        hrd = Division.objects.get(code='HRD')
        fd = Division.objects.get(code='FD')
        ed = Division.objects.get(code='ED')

        users_data = [
            {
                'username': 'admin', 'password': 'admin123',
                'first_name': 'System', 'last_name': 'Administrator',
                'email': 'admin@dotr.gov.ph', 'role': 'admin',
                'employee_id': 'DOTR-ADMIN-001', 'position': 'System Administrator',
                'division': itd, 'is_superuser': True, 'is_staff': True,
            },
            {
                'username': 'hr_officer', 'password': 'hr123',
                'first_name': 'Maria', 'last_name': 'Santos',
                'email': 'hr@dotr.gov.ph', 'role': 'hr',
                'employee_id': 'DOTR-HRD-001', 'position': 'HR Officer III',
                'division': hrd, 'salary_grade': 18,
            },
            {
                'username': 'supervisor1', 'password': 'super123',
                'first_name': 'Jose', 'last_name': 'Reyes',
                'email': 'supervisor@dotr.gov.ph', 'role': 'supervisor',
                'employee_id': 'DOTR-ITD-001', 'position': 'Division Chief',
                'division': itd, 'salary_grade': 24,
            },
            {
                'username': 'employee1', 'password': 'emp123',
                'first_name': 'Ana', 'last_name': 'Cruz',
                'email': 'employee1@dotr.gov.ph', 'role': 'employee',
                'employee_id': 'DOTR-ITD-002', 'position': 'Information Technology Officer II',
                'division': itd, 'salary_grade': 16,
            },
            {
                'username': 'employee2', 'password': 'emp123',
                'first_name': 'Pedro', 'last_name': 'Garcia',
                'email': 'employee2@dotr.gov.ph', 'role': 'employee',
                'employee_id': 'DOTR-FD-001', 'position': 'Accountant III',
                'division': fd, 'salary_grade': 18,
            },
            {
                'username': 'engineer1', 'password': 'eng123',
                'first_name': 'Juan', 'last_name': 'dela Cruz',
                'email': 'engineer1@dotr.gov.ph', 'role': 'employee',
                'employee_id': 'DOTR-ED-001', 'position': 'Civil Engineer IV',
                'division': ed, 'salary_grade': 22,
            },
        ]
        created = 0
        supervisor = None
        for data in users_data:
            password = data.pop('password')
            is_superuser = data.pop('is_superuser', False)
            is_staff = data.pop('is_staff', False)
            if not User.objects.filter(username=data['username']).exists():
                user = User(**data)
                user.set_password(password)
                user.is_superuser = is_superuser
                user.is_staff = is_staff
                user.date_hired = datetime.date(2020, 1, 15)
                user.save()
                created += 1
            if data['username'] == 'supervisor1':
                supervisor = User.objects.get(username='supervisor1')
        # Assign supervisor
        if supervisor:
            User.objects.filter(username__in=['employee1', 'engineer1']).update(supervisor=supervisor)
        self.stdout.write(f'  ✓ {created} users created')

    def _create_competencies(self):
        from apps.competencies.models import Competency
        competencies_data = [
            ('CORE-001', 'Professionalism and Ethics', 'core', 'Demonstrates ethical behavior and professional conduct.'),
            ('CORE-002', 'Excellence', 'core', 'Strives for quality and continuous improvement.'),
            ('CORE-003', 'Teamwork', 'core', 'Works collaboratively with others toward common goals.'),
            ('CORE-004', 'Integrity', 'core', 'Acts with honesty and consistency in all situations.'),
            ('LEAD-001', 'Leading People', 'leadership', 'Effectively manages and motivates team members.'),
            ('LEAD-002', 'Strategic Thinking', 'leadership', 'Develops and communicates strategic direction.'),
            ('LEAD-003', 'Change Management', 'leadership', 'Leads and manages organizational change.'),
            ('TECH-001', 'IT Systems Management', 'technical', 'Manages and maintains IT infrastructure and systems.'),
            ('TECH-002', 'Data Analysis', 'technical', 'Collects, analyzes and interprets data for decision making.'),
            ('TECH-003', 'Financial Management', 'technical', 'Plans and manages financial resources.'),
            ('TECH-004', 'Project Management', 'technical', 'Plans, executes and monitors projects.'),
            ('FUNC-001', 'Records Management', 'functional', 'Maintains and manages organizational records.'),
            ('FUNC-002', 'Procurement', 'functional', 'Follows government procurement rules and regulations.'),
        ]
        created = 0
        for code, name, category, desc in competencies_data:
            _, c = Competency.objects.get_or_create(code=code, defaults={
                'name': name, 'category': category, 'description': desc
            })
            if c:
                created += 1
        self.stdout.write(f'  ✓ {len(competencies_data)} competencies created')

    def _create_trainings(self):
        from apps.trainings.models import TrainingProgram, TrainingModule, Enrollment
        from apps.accounts.models import User
        hr = User.objects.filter(role='hr').first()
        trainings_data = [
            {
                'code': 'TRN-2024-001', 'title': 'CSC-Prescribed Mandatory Trainings for Government Employees',
                'training_type': 'mandatory', 'delivery_mode': 'f2f', 'status': 'published',
                'description': 'Covers the mandatory trainings required by the Civil Service Commission for all government employees including ARTA, SALN, VAWC, and Data Privacy Act.',
                'duration_hours': 16, 'max_participants': 50, 'passing_score': 75,
                'start_date': datetime.date.today() + datetime.timedelta(days=14),
            },
            {
                'code': 'TRN-2024-002', 'title': 'Digital Literacy for Government Employees',
                'training_type': 'optional', 'delivery_mode': 'online', 'status': 'published',
                'description': 'Enhances digital skills of DOTR employees including Microsoft Office, email etiquette, and basic cybersecurity awareness.',
                'duration_hours': 8, 'max_participants': 100, 'passing_score': 70,
                'start_date': datetime.date.today() + datetime.timedelta(days=7),
            },
            {
                'code': 'TRN-2024-003', 'title': 'Project Management for Government Projects',
                'training_type': 'specialized', 'delivery_mode': 'blended', 'status': 'published',
                'description': 'Covers fundamentals of project management aligned with RA 9184 and COA regulations for government infrastructure projects.',
                'duration_hours': 24, 'max_participants': 30, 'passing_score': 80,
                'start_date': datetime.date.today() + datetime.timedelta(days=21),
            },
            {
                'code': 'TRN-2024-004', 'title': 'Anti-Red Tape Authority (ARTA) Orientation',
                'training_type': 'mandatory', 'delivery_mode': 'online', 'status': 'published',
                'description': 'Understanding Republic Act 11032 or the Ease of Doing Business Act and its implications for DOTR services.',
                'duration_hours': 4, 'max_participants': 200, 'passing_score': 75,
            },
            {
                'code': 'TRN-2024-005', 'title': 'Leadership Development Program for Supervisors',
                'training_type': 'specialized', 'delivery_mode': 'f2f', 'status': 'published',
                'description': 'Develops leadership competencies for DOTR supervisors and division chiefs.',
                'duration_hours': 40, 'max_participants': 20, 'passing_score': 80,
            },
        ]
        for data in trainings_data:
            t, created = TrainingProgram.objects.get_or_create(
                code=data['code'],
                defaults={**data, 'created_by': hr}
            )
            if created:
                # Add sample modules
                modules = [
                    {'title': 'Introduction and Overview', 'content_type': 'text', 'duration_minutes': 30,
                     'content': f'Welcome to {t.title}. This module covers the introduction and learning objectives.'},
                    {'title': 'Core Content', 'content_type': 'text', 'duration_minutes': 60,
                     'content': 'This module covers the main learning content for this training program.'},
                    {'title': 'Case Studies and Application', 'content_type': 'text', 'duration_minutes': 45,
                     'content': 'Apply what you have learned through relevant case studies and practical exercises.'},
                    {'title': 'Summary and Key Takeaways', 'content_type': 'text', 'duration_minutes': 15,
                     'content': 'Review key concepts and takeaways from this training program.'},
                ]
                for i, m in enumerate(modules, 1):
                    TrainingModule.objects.create(training=t, order=i, **m)

                # Add a post-test assessment with sample questions
                self._create_sample_assessment(t, hr)

        # Create some sample enrollments
        employee = User.objects.filter(username='employee1').first()
        employee2 = User.objects.filter(username='employee2').first()
        if employee:
            for t in TrainingProgram.objects.filter(status='published')[:2]:
                enr, _ = Enrollment.objects.get_or_create(user=employee, training=t)
                if _:
                    enr.progress_percent = 65
                    enr.save()
        if employee2:
            t = TrainingProgram.objects.filter(status='published').first()
            if t:
                enr, created = Enrollment.objects.get_or_create(user=employee2, training=t)
                if created:
                    enr.status = 'completed'
                    enr.progress_percent = 100
                    enr.final_score = 88
                    enr.completed_at = timezone.now()
                    enr.save()
                    # Auto-issue certificate for this completed enrollment
                    from apps.certificates.models import Certificate
                    Certificate.objects.get_or_create(
                        enrollment=enr,
                        defaults={'certificate_number': Certificate.generate_certificate_number()}
                    )
        self.stdout.write(f'  ✓ {len(trainings_data)} training programs created')

    def _create_sample_assessment(self, training, created_by):
        from apps.assessments.models import Assessment, Question, Choice
        assessment = Assessment.objects.create(
            training=training,
            title=f'Post-Test: {training.title[:60]}',
            assessment_type='post_test',
            description='Answer all questions to complete this training and earn your certificate.',
            time_limit_minutes=30,
            passing_score=training.passing_score,
            max_attempts=3,
            shuffle_questions=True,
            is_active=True,
            created_by=created_by,
        )
        # Sample questions
        questions_data = [
            {
                'text': 'What is the primary purpose of this training program?',
                'choices': [
                    ('To improve knowledge and skills relevant to government service', True),
                    ('To fulfill a personal interest', False),
                    ('To earn extra pay', False),
                    ('To avoid regular work duties', False),
                ],
            },
            {
                'text': 'Which of the following best describes a competency?',
                'choices': [
                    ('A combination of knowledge, skills, and attitudes needed for effective performance', True),
                    ('A job title given to senior employees', False),
                    ('A government mandate requiring attendance', False),
                    ('An annual performance bonus', False),
                ],
            },
            {
                'text': 'The Civil Service Commission (CSC) mandates which type of training for all government employees?',
                'choices': [
                    ('Mandatory trainings aligned with PRIME-HRM', True),
                    ('Optional recreational training', False),
                    ('Private sector certifications only', False),
                    ('Monthly team-building activities', False),
                ],
            },
            {
                'text': 'What should an employee do after completing a training program?',
                'choices': [
                    ('Apply the learning to their work and update their IDP', True),
                    ('Request for immediate promotion', False),
                    ('File a leave of absence', False),
                    ('Request a transfer to another division', False),
                ],
            },
            {
                'text': 'An Individual Development Plan (IDP) is used to:',
                'choices': [
                    ('Track and plan an employee\'s learning and career growth', True),
                    ('Document employee misconduct', False),
                    ('Schedule annual vacations', False),
                    ('Record daily attendance', False),
                ],
            },
        ]
        for order, qdata in enumerate(questions_data, 1):
            q = Question.objects.create(
                assessment=assessment,
                question_text=qdata['text'],
                question_type='mc',
                points=1,
                order=order,
            )
            for c_order, (text, is_correct) in enumerate(qdata['choices'], 1):
                Choice.objects.create(
                    question=q, choice_text=text,
                    is_correct=is_correct, order=c_order
                )

    def _assign_competencies(self):
        from apps.competencies.models import Competency, EmployeeCompetency
        from apps.accounts.models import User
        import random
        employees = User.objects.filter(role='employee')
        competencies = list(Competency.objects.all())
        count = 0
        for emp in employees:
            for comp in random.sample(competencies, min(5, len(competencies))):
                ec, created = EmployeeCompetency.objects.get_or_create(
                    user=emp, competency=comp,
                    defaults={
                        'current_level': random.randint(1, 3),
                        'target_level': random.randint(2, 4),
                    }
                )
                if created:
                    count += 1
        self.stdout.write(f'  ✓ {count} competency records assigned')

    def _create_certificate_template(self):
        from apps.certificates.models import CertificateTemplate
        from apps.accounts.models import User
        hr = User.objects.filter(role='hr').first()
        if not CertificateTemplate.objects.exists():
            CertificateTemplate.objects.create(
                name='DOTR Official Certificate 2025',
                is_active=True,
                header_text='Department of Transportation',
                subheader='Republic of the Philippines',
                intro_line='is proudly presented to',
                body_after='for his/her successful participation and completion of',
                footer_note='',
                signatory1_name=hr.get_full_name() if hr else 'ERIKA LLYSSA G. MAGPAYO',
                signatory1_position='Director IV for Administrative Service concurrent\nManagement Information Systems Service',
                signatory1_label='',
                primary_color='#003087',
                accent_color='#b8860b',
                background_color='#FFFFFF',
                border_style='classic',
                orientation='landscape',
                show_score=True,
                show_duration=True,
                show_cert_number=True,
                created_by=hr,
            )
            self.stdout.write('  ✓ Default certificate template created')
        else:
            self.stdout.write('  ✓ Certificate template already exists')
