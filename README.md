# DOTR-LMS — Department of Transportation Learning Management System

A full-featured Django-based Learning Management System aligned with CSC PRIME-HRM standards.

---

## 🚀 Quick Setup

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Seed with demo data
```bash
python manage.py seed_data
```

### 6. Start the development server
```bash
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## 👤 Demo Accounts

| Role        | Username      | Password  |
|-------------|---------------|-----------|
| Admin       | `admin`       | `admin123`|
| HR Officer  | `hr_officer`  | `hr123`   |
| Supervisor  | `supervisor1` | `super123`|
| Employee    | `employee1`   | `emp123`  |
| Employee 2  | `employee2`   | `emp123`  |

Django Admin: **http://127.0.0.1:8000/admin/** (use admin credentials)

---

## 🏗️ System Architecture

```
dotr_lms/
├── manage.py
├── requirements.txt
├── dotr_lms/                  # Project config
│   ├── settings.py
│   └── urls.py
├── apps/
│   ├── accounts/              # Users, RBAC, Divisions
│   ├── competencies/          # Competency Framework, IDP
│   ├── trainings/             # Training Programs, Enrollments
│   ├── assessments/           # Exams, Quizzes, Grading
│   ├── certificates/          # Digital Certificates
│   └── reports/               # Dashboard, Analytics
├── templates/                 # HTML Templates
└── static/                    # CSS, JS, Images
```

---

## 🔐 Role-Based Access Control (RBAC)

| Feature                    | Admin | HR  | Supervisor | Employee |
|----------------------------|-------|-----|------------|----------|
| Dashboard (full)           | ✅    | ✅  | Partial    | Partial  |
| Manage Employees           | ✅    | ✅  | ❌         | ❌       |
| Create Training Programs   | ✅    | ✅  | ❌         | ❌       |
| Approve Training Requests  | ✅    | ✅  | ✅         | ❌       |
| View Competency Gaps (All) | ✅    | ✅  | Team only  | Own only |
| Issue Certificates         | ✅    | ✅  | ❌         | ❌       |
| Compliance Reports         | ✅    | ✅  | ❌         | ❌       |
| Enroll in Trainings        | ✅    | ✅  | ✅         | ✅       |

---

## 📚 Core Modules

### 1. User & RBAC Management
- Custom User model with 6 roles
- Division/Office management
- Employee profiles with employment details
- Supervisor-subordinate hierarchy

### 2. Competency Framework (CSC-Aligned)
- Core, Leadership, Technical, Functional competencies
- 4-level proficiency scale (Basic → Expert)
- Position-based required competencies
- Gap analysis reports

### 3. Training Program Management
- Create & publish training programs
- Mandatory / Optional / Specialized types
- Online / Face-to-Face / Blended delivery modes
- Module-based course structure

### 4. Training Requests & Approvals
**Flow:** Employee → Supervisor → HR → Auto-Enrollment
- Justification submission
- Two-level approval (Supervisor + HR)
- Auto-enrollment upon approval

### 5. Learning Delivery (LMS Core)
- Module-by-module progression
- Progress tracking with resume support
- Multiple content types (text, video, PDF, quiz)

### 6. Assessments & Grading
- Pre-test / Post-test / Quiz / Final Exam
- Multiple choice, True/False, Identification
- Auto-grading with configurable passing scores
- Multiple attempts support

### 7. Digital Certificates
- Auto-generated upon completion
- Unique certificate numbers (DOTR-XXXXXXXX format)
- Public QR verification endpoint (no login required)

### 8. IDP (Individual Development Plan)
- Annual IDP creation
- Competency-linked learning activities
- Supervisor/HR approval workflow

### 9. Reports & Analytics Dashboard
- Training completion rates
- Competency gap heatmap
- Division performance ranking
- CSC PRIME-HRM compliance report

---

## ⚙️ Configuration

### Database (PostgreSQL for Production)
Update `dotr_lms/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dotr_lms',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Email Notifications
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your@email.com'
EMAIL_HOST_PASSWORD = 'your_password'
```

### Production Settings
```python
DEBUG = False
SECRET_KEY = 'your-secure-random-key'
ALLOWED_HOSTS = ['dotr.gov.ph', 'lms.dotr.gov.ph']
```

---

## 🔗 Key URLs

| URL                                    | Description                      |
|----------------------------------------|----------------------------------|
| `/`                                    | Redirects to Dashboard           |
| `/accounts/login/`                     | Login page                       |
| `/dashboard/`                          | Main dashboard                   |
| `/trainings/`                          | Training catalog                 |
| `/trainings/manage/`                   | HR/Admin training management     |
| `/trainings/my-learnings/`             | Employee's enrolled courses      |
| `/trainings/requests/`                 | Training requests & approvals    |
| `/competencies/`                       | Competency framework             |
| `/competencies/gap-analysis/`          | Gap analysis report              |
| `/competencies/idp/`                   | Individual Development Plans     |
| `/certificates/`                       | My certificates                  |
| `/certificates/verify/<cert_number>/`  | Public certificate verification  |
| `/dashboard/reports/`                  | Analytics & reports              |
| `/dashboard/reports/compliance/`       | PRIME-HRM compliance report      |
| `/admin/`                              | Django admin panel               |

---

## 📋 CSC PRIME-HRM Alignment

✅ Competency-Based Learning  
✅ Individual Development Plan (IDP)  
✅ Learning Interventions Tracking  
✅ Monitoring & Evaluation  
✅ Mandatory Training Compliance Tracking  
✅ Audit-ready Reports (Export-ready)  

---

## 🛠️ Development Notes

- **Database**: SQLite for development, PostgreSQL for production
- **Media Files**: Stored in `/media/` directory
- **Static Files**: Run `python manage.py collectstatic` for production
- **Time Zone**: Asia/Manila (Philippine Standard Time)

---

## 📞 Support

DOTR Sutil Division  
Email: bonifaciobiodor@gmail.com  
