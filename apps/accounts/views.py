import json
import os
from html import escape as _he
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse, FileResponse, Http404
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse
from .models import User, Division, AuditLog, DataErasureRequest, OrganizationalStructure, OrgUnit
from .forms import (
    LoginForm, UserCreateForm, UserEditForm, DivisionForm,
    ChangePasswordForm, DataErasureRequestForm, ErasureReviewForm,
)
from .decorators import role_required

FEATURES = [
    ('graduation-cap', 'CSC PRIME-HRM Aligned Training Programs'),
    ('brain', 'Competency-Based Learning Framework'),
    ('certificate', 'Digital Certificates with QR Verification'),
    ('chart-line', 'Real-time Analytics & Compliance Reports'),
    ('route', 'Individual Development Plan (IDP)'),
    ('file', 'Job Analysis Form (JAF)'),
]

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        # Enforce consent checkbox on every login before even authenticating
        if not form.cleaned_data.get('privacy_consent'):
            messages.error(
                request,
                'You must accept the Data Privacy Notice before signing in.'
            )
            return render(request, 'accounts/login.html', {
                'form': form, 'features': FEATURES,
            })

        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        if user:
            # Record consent timestamp on first acceptance (or re-acceptance)
            if not user.privacy_consent:
                user.privacy_consent = True
                user.privacy_consent_date = timezone.now()
                user.save(update_fields=['privacy_consent', 'privacy_consent_date'])
                AuditLog.objects.create(
                    user=user, action='PRIVACY_CONSENT', model_name='User',
                    object_id=str(user.id),
                    details='User accepted the Data Privacy Notice.',
                    ip_address=get_client_ip(request),
                )

            login(request, user)
            AuditLog.objects.create(
                user=user, action='LOGIN', model_name='User',
                object_id=str(user.id), ip_address=get_client_ip(request)
            )
            next_url = request.GET.get('next', '')
            if next_url:
                parsed = urlparse(next_url)
                if parsed.netloc or parsed.scheme:
                    next_url = ''
            return redirect(next_url or 'dashboard')

        messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html', {'form': form, 'features': FEATURES})


def logout_view(request):
    if request.method != 'POST':
        return redirect('dashboard' if request.user.is_authenticated else 'login')
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user, action='LOGOUT', model_name='User',
            object_id=str(request.user.id), ip_address=get_client_ip(request)
        )
    logout(request)
    return redirect('login')


def privacy_notice_view(request):
    """Public page — no login required — for the full DPA privacy notice."""
    return render(request, 'accounts/privacy_notice.html')


@login_required
def profile_view(request):
    user = request.user
    from apps.trainings.models import Enrollment
    enrollments = Enrollment.objects.filter(user=user).select_related('training')[:5]
    profile_data = [
        ('id-badge', 'Employee ID', user.employee_id),
        ('building', 'Division', str(user.division) if user.division else None),
        ('briefcase', 'Position', user.position),
        ('layer-group', 'Salary Grade', f'SG-{user.salary_grade}' if user.salary_grade else None),
        ('file-contract', 'Employment', user.get_employment_status_display()),
        ('phone', 'Contact', user.contact_number),
        ('envelope', 'Email', user.email),
        ('calendar', 'Date Hired', user.date_hired.strftime('%B %d, %Y') if user.date_hired else None),
    ]
    pending_erasure = DataErasureRequest.objects.filter(
        requester=user,
        status__in=[DataErasureRequest.Status.PENDING, DataErasureRequest.Status.APPROVED],
    ).exists()
    return render(request, 'accounts/profile.html', {
        'profile_user': user,
        'enrollments': enrollments,
        'profile_data': profile_data,
        'pending_erasure': pending_erasure,
    })


@login_required
@role_required(['admin', 'hr'])
def user_list(request):
    query = request.GET.get('q', '')
    division = request.GET.get('division', '')
    role = request.GET.get('role', '')

    users = User.objects.select_related('division').all()
    if query:
        users = users.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) |
            Q(employee_id__icontains=query) | Q(email__icontains=query)
        )
    if division:
        users = users.filter(division_id=division)
    if role:
        users = users.filter(role=role)

    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get('page'))
    divisions = Division.objects.all()
    return render(request, 'accounts/user_list.html', {
        'page_obj': page,
        'divisions': divisions,
        'roles': User.Role.choices,
        'query': query,
    })


@login_required
@role_required(['admin', 'hr'])
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        AuditLog.objects.create(
            user=request.user, action='CREATE_USER', model_name='User',
            object_id=str(user.id), details=f"Created user: {user.username}"
        )
        messages.success(request, f'User {user.get_full_name()} created successfully.')
        return redirect('user_list')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Add New Employee'})


@login_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.user.role not in ['admin', 'hr'] and request.user.pk != pk:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    form = UserEditForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_list' if request.user.role in ['admin', 'hr'] else 'profile')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Edit Employee', 'edit_user': user})


@login_required
def change_password_view(request):
    form = ChangePasswordForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        # Keep the user logged in after password change
        update_session_auth_hash(request, request.user)
        AuditLog.objects.create(
            user=request.user, action='CHANGE_PASSWORD', model_name='User',
            object_id=str(request.user.id), ip_address=get_client_ip(request),
            details='User changed their password.',
        )
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')
    return render(request, 'accounts/change_password.html', {'form': form})


# ── Data Erasure (RA 10173) ───────────────────────────────────────────────────

@login_required
def erasure_request_create(request):
    """Employee submits a data erasure request."""
    # Block duplicate pending/approved requests
    existing = DataErasureRequest.objects.filter(
        requester=request.user,
        status__in=[DataErasureRequest.Status.PENDING, DataErasureRequest.Status.APPROVED],
    ).first()
    if existing:
        messages.warning(
            request,
            f'You already have an active erasure request (#{existing.pk}) '
            f'with status: {existing.get_status_display()}.'
        )
        return redirect('profile')

    form = DataErasureRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        er = DataErasureRequest.objects.create(
            requester=request.user,
            reason=form.cleaned_data['reason'],
        )
        AuditLog.objects.create(
            user=request.user, action='ERASURE_REQUEST', model_name='DataErasureRequest',
            object_id=str(er.id), ip_address=get_client_ip(request),
            details=f'Data erasure request submitted by {request.user.username}.',
        )
        messages.success(
            request,
            'Your data erasure request has been submitted. '
            'The Data Protection Officer will review it within 15 business days.'
        )
        return redirect('profile')
    return render(request, 'accounts/erasure_request_form.html', {'form': form})


@login_required
@role_required(['admin', 'hr'])
def erasure_request_list(request):
    """Admin/HR — view all erasure requests."""
    status_filter = request.GET.get('status', '')
    requests_qs = DataErasureRequest.objects.select_related('requester', 'reviewed_by').all()
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
    paginator = Paginator(requests_qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/erasure_request_list.html', {
        'page_obj': page,
        'status_choices': DataErasureRequest.Status.choices,
        'status_filter': status_filter,
    })


@login_required
@role_required(['admin', 'hr'])
def erasure_request_review(request, pk):
    """Admin/HR — approve or reject a pending erasure request."""
    er = get_object_or_404(DataErasureRequest, pk=pk)
    if er.status != DataErasureRequest.Status.PENDING:
        messages.error(request, 'This request has already been reviewed.')
        return redirect('erasure_request_list')

    form = ErasureReviewForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        action = form.cleaned_data['action']
        er.status = action  # 'approved' or 'rejected'
        er.reviewed_by = request.user
        er.review_date = timezone.now()
        er.review_remarks = form.cleaned_data.get('review_remarks', '')
        er.save()
        AuditLog.objects.create(
            user=request.user, action=f'ERASURE_{action.upper()}',
            model_name='DataErasureRequest', object_id=str(er.id),
            ip_address=get_client_ip(request),
            details=f'Erasure request #{er.id} {action} by {request.user.username}.',
        )
        messages.success(request, f'Erasure request #{er.pk} has been {action}.')
        return redirect('erasure_request_list')
    return render(request, 'accounts/erasure_request_review.html', {'er': er, 'form': form})


@login_required
@role_required(['admin'])
def erasure_request_process(request, pk):
    """
    Admin — execute the anonymisation for an approved erasure request.
    Personal identifiers are replaced with anonymised placeholders.
    Training completion counts and audit log entries are retained per COA/CSC
    requirements but are de-linked from the individual.
    """
    er = get_object_or_404(DataErasureRequest, pk=pk)
    if er.status != DataErasureRequest.Status.APPROVED:
        messages.error(request, 'Only approved requests can be processed.')
        return redirect('erasure_request_list')

    if request.method == 'POST':
        target = er.requester
        if target is None:
            messages.error(request, 'Requester account not found — may already be anonymised.')
            return redirect('erasure_request_list')

        uid = target.pk
        anon_tag = f'anon-{uid}'

        # Anonymise personal data fields
        target.first_name = 'ANONYMIZED'
        target.last_name = str(uid)
        target.username = anon_tag
        target.email = f'{anon_tag}@anonymized.invalid'
        target.employee_id = None
        target.contact_number = ''
        target.position = ''
        target.date_hired = None
        target.avatar = None
        target.is_active = False          # Prevent login
        target.privacy_consent = False
        target.privacy_consent_date = None
        target.set_unusable_password()    # Cannot authenticate
        target.save()

        # Nullify the FK on the erasure request so the User object can be
        # de-identified in the future without cascading issues.
        er.requester = None
        er.status = DataErasureRequest.Status.COMPLETED
        er.processed_at = timezone.now()
        er.save()

        AuditLog.objects.create(
            user=request.user, action='ERASURE_PROCESSED',
            model_name='DataErasureRequest', object_id=str(er.id),
            ip_address=get_client_ip(request),
            details=f'Personal data anonymised for user #{uid} by {request.user.username}.',
        )
        messages.success(
            request,
            f'Personal data for user #{uid} has been anonymised. '
            'Audit logs and training statistics have been retained as required by law.'
        )
        return redirect('erasure_request_list')

    return render(request, 'accounts/erasure_process_confirm.html', {'er': er})


@login_required
@role_required(['admin'])
def audit_log(request):
    logs = AuditLog.objects.select_related('user').all()
    paginator = Paginator(logs, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/audit_log.html', {'page_obj': page})


@login_required
@role_required(['admin', 'hr'])
def division_list(request):
    from django.db.models import Q as _Q
    qs = Division.objects.prefetch_related('user_set').select_related('head')
    q = request.GET.get('q', '').strip()
    has_head = request.GET.get('has_head', '')
    sort = request.GET.get('sort', 'name')

    if q:
        qs = qs.filter(
            _Q(name__icontains=q) |
            _Q(code__icontains=q) |
            _Q(description__icontains=q)
        )
    if has_head == '1':
        qs = qs.filter(head__isnull=False)
    elif has_head == '0':
        qs = qs.filter(head__isnull=True)

    sort_map = {
        'name': 'name', '-name': '-name',
        'code': 'code', 'newest': '-created_at', 'oldest': 'created_at',
    }
    qs = qs.order_by(sort_map.get(sort, 'name'))

    return render(request, 'accounts/division_list.html', {
        'divisions': qs,
        'q': q,
        'has_head': has_head,
        'sort': sort,
        'total': Division.objects.count(),
    })


@login_required
@role_required(['admin', 'hr'])
def division_create(request):
    form = DivisionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        division = form.save()
        AuditLog.objects.create(
            user=request.user, action='CREATE_DIVISION', model_name='Division',
            object_id=str(division.pk), details=f'Division "{division.name}" created.',
            ip_address=get_client_ip(request),
        )
        messages.success(request, f'Division "{division.name}" created.')
        return redirect('division_list')
    return render(request, 'accounts/division_form.html', {'form': form, 'title': 'Add Division'})


@login_required
@role_required(['admin', 'hr'])
def division_edit(request, pk):
    division = get_object_or_404(Division, pk=pk)
    form = DivisionForm(request.POST or None, instance=division)
    if request.method == 'POST' and form.is_valid():
        form.save()
        AuditLog.objects.create(
            user=request.user, action='EDIT_DIVISION', model_name='Division',
            object_id=str(division.pk), details=f'Division "{division.name}" updated.',
            ip_address=get_client_ip(request),
        )
        messages.success(request, f'Division "{division.name}" updated.')
        return redirect('division_list')
    return render(request, 'accounts/division_form.html', {
        'form': form, 'title': 'Edit Division', 'division': division,
    })


@login_required
@role_required(['admin', 'hr'])
def division_delete(request, pk):
    division = get_object_or_404(Division, pk=pk)
    if request.method == 'POST':
        staff_count = division.user_set.count()
        if staff_count > 0:
            messages.error(
                request,
                f'Cannot delete "{division.name}" — it still has {staff_count} employee(s) assigned. '
                'Reassign them first.'
            )
            return redirect('division_list')
        name = division.name
        AuditLog.objects.create(
            user=request.user, action='DELETE_DIVISION', model_name='Division',
            object_id=str(division.pk), details=f'Division "{name}" deleted.',
            ip_address=get_client_ip(request),
        )
        division.delete()
        messages.success(request, f'Division "{name}" deleted.')
        return redirect('division_list')
    return render(request, 'accounts/division_confirm_delete.html', {'division': division})


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0]
    return request.META.get('REMOTE_ADDR')


@login_required
def user_manual_view(request):
    import markdown
    import os
    import re
    import unicodedata

    def _slugify(value):
        """Replicates python-markdown toc slugify so anchor hrefs match heading IDs."""
        value = unicodedata.normalize('NFKD', str(value))
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return re.sub(r'[-\s]+', '-', value)

    manual_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        'DOTR_LMS_USER_MANUAL.md'
    )

    # Sections visible per role (by section number). None = all sections.
    ROLE_SECTIONS = {
        'employee':   {1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17},
        'supervisor': {1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17},
        'trainer':    {1, 2, 3, 4, 5, 6, 9, 12, 13, 14, 15, 16, 17},
        'hr':         {1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17},
        'admin':      None,
        'executive':  {1, 2, 3, 4, 5, 11, 14, 15, 16, 17},
    }

    content_html = ''
    toc_sections = []

    if os.path.exists(manual_path):
        with open(manual_path, 'r', encoding='utf-8') as f:
            raw = f.read()

        role = getattr(request.user, 'role', 'employee')
        allowed = ROLE_SECTIONS.get(role)  # None = show everything

        # Split on H2 headings; first part is the preamble
        parts = re.split(r'(?=^## )', raw, flags=re.MULTILINE)

        filtered_parts = []
        for part in parts:
            if not part.startswith('## '):
                # Preamble (H1 title + metadata) — always include
                filtered_parts.append(part)
                continue

            m = re.match(r'## (\d+)\. (.+)', part)
            if not m:
                # Non-numbered heading (e.g. "## Table of Contents") — skip entirely
                continue

            sec_num = int(m.group(1))
            sec_title = m.group(2).strip()

            if allowed is None or sec_num in allowed:
                filtered_parts.append(part)
                toc_sections.append({
                    'number': sec_num,
                    'title': sec_title,
                    'anchor': _slugify(f'{sec_num} {sec_title}'),
                })

        content_html = markdown.markdown(
            ''.join(filtered_parts),
            extensions=['tables', 'fenced_code', 'toc'],
        )

    return render(request, 'accounts/user_manual.html', {
        'content_html': content_html,
        'toc_sections': toc_sections,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ORGANIZATIONAL STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def org_structure_view(request):
    """Public view – shows the currently active org structure."""
    active = OrganizationalStructure.objects.filter(is_active=True).first()
    tree_json = '[]'
    if active:
        root_units = active.units.filter(parent=None).order_by('order')
        tree_json = json.dumps(_build_tree(root_units))
    return render(request, 'accounts/org_structure_view.html', {
        'active': active,
        'tree_json': tree_json,
    })


@login_required
@role_required(['admin', 'hr'])
def org_structure_design(request, pk=None):
    """Drag-and-drop org chart designer for Admin / HRDD."""
    instance = None
    tree_json = '[]'
    divisions = list(Division.objects.values('id', 'name', 'code'))

    employees = list(
        User.objects.filter(is_active=True)
        .order_by('last_name', 'first_name')
        .values('id', 'first_name', 'last_name', 'position', 'employee_id')
    )
    for e in employees:
        e['full_name'] = f"{e['last_name']}, {e['first_name']}".strip(', ')

    if pk:
        instance = get_object_or_404(OrganizationalStructure, pk=pk)
        root_units = instance.units.filter(parent=None).order_by('order')
        tree_json = json.dumps(_build_tree(root_units))

    return render(request, 'accounts/org_structure_design.html', {
        'instance': instance,
        'tree_json': tree_json,
        'divisions_json': json.dumps(divisions),
        'employees_json': json.dumps(employees),
    })


def _build_tree(units):
    result = []
    for u in units:
        children = u.children.all().order_by('order')
        head_user_data = None
        if u.head_user_id:
            hu = u.head_user
            head_user_data = {
                'id': hu.id,
                'full_name': hu.get_full_name() or hu.username,
                'position': hu.position or '',
                'employee_id': hu.employee_id or '',
            }
        result.append({
            'id': u.id,
            'name': u.name,
            'abbreviation': u.abbreviation,
            'unit_type': u.unit_type,
            'head_position': u.head_position,
            'division_ref': u.division_ref_id,
            'head_user': head_user_data,
            'children': _build_tree(children),
        })
    return result


@login_required
@role_required(['admin', 'hr'])
def org_structure_save(request):
    """Receives JSON tree, stores OrgUnit records, generates HTML file, sets active."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    tree = payload.get('tree', [])
    description = payload.get('description', '')

    # Generate timestamped filename
    ts = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{ts}_DOTr_OrganizationalStructure.html'

    # Build HTML content
    html_content = _render_org_html(tree, filename, request.user)

    # Save the HTML file to media/org_structures/
    rel_path = f'org_structures/{filename}'
    abs_dir = os.path.join(settings.MEDIA_ROOT, 'org_structures')
    os.makedirs(abs_dir, exist_ok=True)
    abs_path = os.path.join(abs_dir, filename)
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Deactivate all others
    OrganizationalStructure.objects.update(is_active=False)

    # Create the structure record
    structure = OrganizationalStructure.objects.create(
        filename=filename,
        html_file=rel_path,
        description=description,
        is_active=True,
        created_by=request.user,
    )

    # Persist OrgUnit tree
    _save_org_units(tree, structure, parent=None, order_start=0)

    AuditLog.objects.create(
        user=request.user,
        action='ORG_STRUCTURE_SAVED',
        model_name='OrganizationalStructure',
        object_id=str(structure.pk),
        details=f'Saved and activated: {filename}',
        ip_address=_get_ip(request),
    )

    return JsonResponse({'ok': True, 'pk': structure.pk, 'filename': filename})


def _save_org_units(tree, structure, parent, order_start):
    for idx, node in enumerate(tree):
        head_user_data = node.get('head_user') or {}
        head_user_id = head_user_data.get('id') if head_user_data else None
        unit = OrgUnit.objects.create(
            org_structure=structure,
            name=node.get('name', ''),
            abbreviation=node.get('abbreviation', ''),
            unit_type=node.get('unit_type', 'division'),
            head_position=node.get('head_position', ''),
            parent=parent,
            order=order_start + idx,
            division_ref_id=node.get('division_ref') or None,
            head_user_id=head_user_id or None,
        )
        _save_org_units(node.get('children', []), structure, unit, 0)


def _render_org_html(tree, filename, user):
    """Generate a self-contained HTML file for the org chart."""
    nodes_html = _render_nodes_html(tree, level=0)
    now_str = timezone.now().strftime('%B %d, %Y %I:%M %p')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DOTr Organizational Structure</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; padding: 30px 20px; }}
  .os-header {{ text-align: center; margin-bottom: 30px; }}
  .os-header h1 {{ font-size: 20px; font-weight: 800; color: #003087; letter-spacing: 1px; }}
  .os-header h2 {{ font-size: 14px; color: #475569; font-weight: 500; margin-top: 4px; }}
  .os-header .meta {{ font-size: 11px; color: #94a3b8; margin-top: 6px; }}
  /* Each node group: column, centered */
  .org-node-wrap {{ display: flex; flex-direction: column; align-items: center; }}
  /* Box */
  .org-node {{
    background: white; border-radius: 10px; border: 2px solid #e2e8f0;
    padding: 10px 14px; min-width: 140px; max-width: 200px;
    text-align: center; box-shadow: 0 2px 8px rgba(0,48,135,.1);
  }}
  .org-node.level-0 {{ border-color: #003087; background: #003087; }}
  .org-node.level-0 .node-abbr  {{ color: #FDB913; }}
  .org-node.level-0 .node-name  {{ color: #ffffff; }}
  .org-node.level-0 .node-type  {{ color: rgba(255,255,255,.55); }}
  .org-node.level-0 .node-person {{ color: #FDB913; border-top-color: rgba(255,255,255,.2); }}
  .org-node.level-0 .node-head  {{ color: rgba(255,255,255,.65); }}
  .org-node.level-1 {{ border-color: #0047BD; }}
  .org-node.level-2 {{ border-color: #2563eb; }}
  .org-node.level-3 {{ border-color: #64748b; }}
  .node-abbr   {{ font-size: 11px; font-weight: 800; color: #d4a017; letter-spacing: .5px; }}
  .node-name   {{ font-size: 12px; font-weight: 700; color: #0f172a; line-height: 1.3; margin-top: 2px; }}
  .node-type   {{ font-size: 9px; color: #94a3b8; text-transform: uppercase; letter-spacing: .5px; margin-top: 3px; }}
  .node-person {{ font-size: 11px; font-weight: 600; color: #1e3a6e; margin-top: 5px;
                  border-top: 1px dashed rgba(0,0,0,.12); padding-top: 4px; line-height: 1.35; }}
  .node-head   {{ font-size: 10px; color: #64748b; margin-top: 2px; font-style: italic; }}
  /* ── Connectors ── */
  /* Vertical line: parent box → h-bar level */
  .cn-v-parent {{ width: 2px; height: 20px; background: #cbd5e1; }}
  /* Children row: the border-top IS the horizontal bar for 2+ children */
  .children-row {{ display: flex; justify-content: center; align-items: flex-start; }}
  .children-row.multi {{ border-top: 2px solid #cbd5e1; }}
  /* Each child column */
  .child-branch {{ display: flex; flex-direction: column; align-items: center; padding: 0 14px; }}
  /* Vertical line: h-bar → child box (only used when multi) */
  .cn-v-child {{ width: 2px; height: 20px; background: #cbd5e1; }}
  /* Footer */
  .os-footer {{ text-align: center; margin-top: 40px; font-size: 10px; color: #94a3b8; }}
  /* ── Zoom toolbar ── */
  .zoom-bar {{
    display: flex; align-items: center; gap: 6px;
    background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 6px 14px; margin: 0 auto 14px; width: fit-content;
    box-shadow: 0 1px 4px rgba(0,0,0,.08); flex-wrap: wrap;
  }}
  .zoom-bar-label {{ font-size: 12px; font-weight: 600; color: #475569; margin-right: 4px; }}
  .zoom-btn {{
    width: 28px; height: 28px; border-radius: 6px;
    border: 1px solid #e2e8f0; background: #f8fafc; cursor: pointer;
    font-size: 16px; font-weight: 700; color: #334155;
    display: flex; align-items: center; justify-content: center;
  }}
  .zoom-btn:hover {{ background: #e2e8f0; }}
  .zoom-level {{ font-size: 12px; font-weight: 700; color: #1e293b; min-width: 38px; text-align: center; }}
  .zoom-sep {{ width: 1px; height: 20px; background: #e2e8f0; margin: 0 4px; }}
  .zoom-fit-btn {{
    padding: 4px 10px; border-radius: 6px; border: 1px solid #e2e8f0;
    background: #f8fafc; cursor: pointer; font-size: 11px; font-weight: 600; color: #334155;
  }}
  .zoom-fit-btn:hover {{ background: #e2e8f0; }}
  .zoom-hint {{ font-size: 10px; color: #94a3b8; margin-left: 6px; }}
  /* ── Viewport ── */
  .org-viewport {{
    position: relative; overflow: hidden;
    height: 680px; cursor: grab; background: #f8fafc;
    border: 1px solid #e2e8f0; border-radius: 10px;
    user-select: none;
  }}
  .org-viewport.dragging {{ cursor: grabbing; }}
  .org-tree {{
    display: inline-flex; flex-direction: column; align-items: center;
    transform-origin: 0 0; will-change: transform; padding: 28px;
    transition: none;
  }}
</style>
</head>
<body>
<div class="os-header">
  <h1>DEPARTMENT OF TRANSPORTATION</h1>
  <h2>Organizational Structure</h2>
  <div class="meta">Generated: {_he(now_str)} &nbsp;|&nbsp; By: {_he(user.get_full_name() or user.username)} &nbsp;|&nbsp; {_he(filename)}</div>
</div>
<div class="zoom-bar">
  <span class="zoom-bar-label">&#128269; Zoom</span>
  <button class="zoom-btn" id="btn-zoom-out" title="Zoom out">&#8722;</button>
  <span class="zoom-level" id="zoom-level">100%</span>
  <button class="zoom-btn" id="btn-zoom-in" title="Zoom in">&#43;</button>
  <div class="zoom-sep"></div>
  <button class="zoom-fit-btn" id="btn-zoom-fit">&#8600; Fit</button>
  <button class="zoom-fit-btn" id="btn-zoom-reset">&#8635; 100%</button>
  <span class="zoom-hint">Scroll to zoom &middot; Drag to pan</span>
</div>
<div class="org-viewport" id="org-viewport">
  <div class="org-tree" id="org-tree">
{nodes_html}
  </div>
</div>
<div class="os-footer">
  <p>Republic of the Philippines &mdash; Department of Transportation (DOTr)</p>
  <p style="margin-top:4px;">This document is officially generated by the DOTr Learning Management System.</p>
</div>
<script>
(function() {{
  var viewport = document.getElementById('org-viewport');
  var tree     = document.getElementById('org-tree');
  var levelEl  = document.getElementById('zoom-level');
  var scale = 1, panX = 0, panY = 0;
  var MIN_SCALE = 0.15, MAX_SCALE = 3, STEP = 0.15;

  function applyTransform(animated) {{
    tree.style.transition = animated ? 'transform .2s ease' : 'none';
    tree.style.transform  = 'translate(' + panX + 'px,' + panY + 'px) scale(' + scale + ')';
    levelEl.textContent   = Math.round(scale * 100) + '%';
  }}

  function zoomToward(newScale, vpX, vpY) {{
    newScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, newScale));
    var ratio = newScale / scale;
    panX  = vpX - ratio * (vpX - panX);
    panY  = vpY - ratio * (vpY - panY);
    scale = newScale;
    applyTransform(false);
  }}

  function fitToView(animated) {{
    var vw = viewport.clientWidth, vh = viewport.clientHeight;
    var tw = tree.scrollWidth,     th = tree.scrollHeight;
    var ns = Math.min(vw / tw, vh / th) * 0.90;
    scale  = Math.max(MIN_SCALE, Math.min(1, ns));
    panX   = (vw - tw * scale) / 2;
    panY   = (vh - th * scale) / 2;
    applyTransform(animated !== false);
  }}

  document.getElementById('btn-zoom-in').addEventListener('click', function() {{
    var cx = viewport.clientWidth / 2, cy = viewport.clientHeight / 2;
    zoomToward(scale + STEP, cx, cy);
  }});
  document.getElementById('btn-zoom-out').addEventListener('click', function() {{
    var cx = viewport.clientWidth / 2, cy = viewport.clientHeight / 2;
    zoomToward(scale - STEP, cx, cy);
  }});
  document.getElementById('btn-zoom-fit').addEventListener('click', function() {{
    fitToView(true);
  }});
  document.getElementById('btn-zoom-reset').addEventListener('click', function() {{
    scale = 1; panX = 0; panY = 0; applyTransform(true);
  }});

  viewport.addEventListener('wheel', function(e) {{
    e.preventDefault();
    var rect = viewport.getBoundingClientRect();
    var vpX = e.clientX - rect.left;
    var vpY = e.clientY - rect.top;
    var delta = e.deltaY < 0 ? STEP : -STEP;
    zoomToward(scale + delta, vpX, vpY);
  }}, {{ passive: false }});

  var drag = false, dragStartX = 0, dragStartY = 0, dragPanX = 0, dragPanY = 0;
  viewport.addEventListener('mousedown', function(e) {{
    if (e.button !== 0) return;
    drag = true; dragStartX = e.clientX; dragStartY = e.clientY;
    dragPanX = panX; dragPanY = panY;
    viewport.classList.add('dragging');
    e.preventDefault();
  }});
  document.addEventListener('mousemove', function(e) {{
    if (!drag) return;
    panX = dragPanX + (e.clientX - dragStartX);
    panY = dragPanY + (e.clientY - dragStartY);
    applyTransform(false);
  }});
  document.addEventListener('mouseup', function() {{
    if (!drag) return;
    drag = false;
    viewport.classList.remove('dragging');
  }});

  var touch = null;
  viewport.addEventListener('touchstart', function(e) {{
    if (e.touches.length === 1) {{
      touch = {{ x: e.touches[0].clientX, y: e.touches[0].clientY, px: panX, py: panY }};
    }}
  }}, {{ passive: true }});
  viewport.addEventListener('touchmove', function(e) {{
    if (touch && e.touches.length === 1) {{
      panX = touch.px + (e.touches[0].clientX - touch.x);
      panY = touch.py + (e.touches[0].clientY - touch.y);
      applyTransform(false);
      e.preventDefault();
    }}
  }}, {{ passive: false }});
  viewport.addEventListener('touchend', function() {{ touch = null; }});

  requestAnimationFrame(function() {{ fitToView(false); }});
}})();
</script>
</body>
</html>"""


def _render_nodes_html(nodes, level):
    if not nodes:
        return ''
    parts = []
    for node in nodes:
        abbr      = _he(node.get('abbreviation', ''))
        name      = _he(node.get('name', ''))
        ntype     = _he(node.get('unit_type', '').capitalize())
        head      = _he(node.get('head_position', ''))
        head_user = node.get('head_user') or {}
        children  = node.get('children', [])

        # ── Person line ──────────────────────────────────────────────────────
        abbr_html = f'<div class="node-abbr">{abbr}</div>' if abbr else ''
        if head_user.get('full_name'):
            emp_pos = _he(head_user.get('position') or node.get('head_position', '') or '')
            person_html = (
                f'<div class="node-person">{_he(head_user["full_name"])}</div>'
                + (f'<div class="node-head">{emp_pos}</div>' if emp_pos else '')
            )
        elif head:
            person_html = f'<div class="node-head">{head}</div>'
        else:
            person_html = ''

        # ── Children connectors ──────────────────────────────────────────────
        children_html = ''
        if children:
            is_multi = len(children) >= 2

            if is_multi:
                # Each child-branch gets a cn-v-child (vertical from h-bar down).
                # The h-bar itself is the border-top of .children-row.multi.
                child_branches = ''.join(
                    f'<div class="child-branch">'
                    f'<div class="cn-v-child"></div>'
                    f'{_render_nodes_html([c], level + 1)}'
                    f'</div>'
                    for c in children
                )
                children_html = (
                    f'<div class="cn-v-parent"></div>'
                    f'<div class="children-row multi">'
                    f'{child_branches}'
                    f'</div>'
                )
            else:
                # Single child: straight vertical line only, no h-bar.
                children_html = (
                    f'<div class="cn-v-parent"></div>'
                    f'{_render_nodes_html(children, level + 1)}'
                )

        parts.append(
            f'<div class="org-node-wrap">'
            f'<div class="org-node level-{min(level, 3)}">'
            f'{abbr_html}'
            f'<div class="node-name">{name}</div>'
            f'<div class="node-type">{ntype}</div>'
            f'{person_html}'
            f'</div>'
            f'{children_html}'
            f'</div>'
        )
    return '\n'.join(parts)


@login_required
@role_required(['admin', 'hr'])
def org_structure_history(request):
    """List all saved org structure versions."""
    structures = OrganizationalStructure.objects.select_related('created_by').all()
    return render(request, 'accounts/org_structure_history.html', {
        'structures': structures,
    })


@login_required
@role_required(['admin', 'hr'])
def org_structure_activate(request, pk):
    """Set a saved version as active."""
    if request.method != 'POST':
        return redirect('org_structure_history')
    structure = get_object_or_404(OrganizationalStructure, pk=pk)
    structure.activate()
    AuditLog.objects.create(
        user=request.user,
        action='ORG_STRUCTURE_ACTIVATED',
        model_name='OrganizationalStructure',
        object_id=str(structure.pk),
        details=f'Activated: {structure.filename}',
        ip_address=_get_ip(request),
    )
    messages.success(request, f'"{structure.filename}" is now the active organizational structure.')
    return redirect('org_structure_history')


@login_required
@role_required(['admin', 'hr'])
def org_structure_delete(request, pk):
    """Delete a saved org structure version (cannot delete the active one)."""
    if request.method != 'POST':
        return redirect('org_structure_history')
    structure = get_object_or_404(OrganizationalStructure, pk=pk)
    if structure.is_active:
        messages.error(request, 'Cannot delete the active organizational structure. Activate another version first.')
        return redirect('org_structure_history')
    filename = structure.filename
    # Remove the stored HTML file from disk
    if structure.html_file:
        abs_path = os.path.join(settings.MEDIA_ROOT, str(structure.html_file))
        if os.path.exists(abs_path):
            os.remove(abs_path)
    structure.delete()
    AuditLog.objects.create(
        user=request.user,
        action='ORG_STRUCTURE_DELETED',
        model_name='OrganizationalStructure',
        object_id=str(pk),
        details=f'Deleted: {filename}',
        ip_address=_get_ip(request),
    )
    messages.success(request, f'"{filename}" has been deleted.')
    return redirect('org_structure_history')


@login_required
def org_structure_download(request, pk):
    """Download the saved HTML file for a given structure (admin/hr or viewing active)."""
    structure = get_object_or_404(OrganizationalStructure, pk=pk)
    if request.user.role not in ('admin', 'hr') and not structure.is_active:
        raise Http404
    abs_path = os.path.join(settings.MEDIA_ROOT, str(structure.html_file))
    if not os.path.exists(abs_path):
        raise Http404
    return FileResponse(open(abs_path, 'rb'), as_attachment=True, filename=structure.filename)


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
