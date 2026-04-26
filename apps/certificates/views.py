from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest
from .models import Certificate, CertificateTemplate
from apps.trainings.models import Enrollment
from apps.accounts.decorators import role_required
from apps.accounts.file_validators import validate_image_upload


# ─── Helper ──────────────────────────────────────────────────────────────────

def _issue_cert(enrollment, issued_by=None, request=None):
    """Create certificate + generate QR. Idempotent."""
    if hasattr(enrollment, 'certificate'):
        return enrollment.certificate, False
    # Prefer training's assigned template if it exists and is_active; fallback to global active.
    assigned = getattr(enrollment.training, 'certificate_template', None)
    if assigned and assigned.is_active:
        template = assigned
    else:
        template = CertificateTemplate.get_active()
    cert = Certificate.objects.create(
        enrollment=enrollment,
        certificate_number=Certificate.generate_certificate_number(),
        template=template,
        issued_by=issued_by,
    )
    cert.generate_qr(request=request)
    return cert, True


# ─── Employee views ───────────────────────────────────────────────────────────

@login_required
def my_certificates(request):
    certs = Certificate.objects.filter(
        enrollment__user=request.user, is_valid=True
    ).select_related('enrollment__training', 'template')
    return render(request, 'certificates/my_certificates.html', {'certificates': certs})


@login_required
def certificate_detail(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    if cert.enrollment.user != request.user and request.user.role not in ['admin', 'hr']:
        messages.error(request, 'Access denied.')
        return redirect('my_certificates')
    template = cert.template or CertificateTemplate.get_active()
    return render(request, 'certificates/certificate_detail.html', {
        'cert': cert,
        'tmpl': template,
    })


def verify_certificate(request, cert_number):
    """Public — no login required."""
    try:
        cert = Certificate.objects.select_related(
            'enrollment__user', 'enrollment__training', 'issued_by'
        ).get(certificate_number=cert_number)
        return render(request, 'certificates/verify.html', {'cert': cert, 'valid': cert.is_valid})
    except Certificate.DoesNotExist:
        return render(request, 'certificates/verify.html', {'valid': False, 'cert_number': cert_number})


# ─── HR / Admin views ─────────────────────────────────────────────────────────

@login_required
@role_required(['admin', 'hr'])
def certificate_list(request):
    certs = Certificate.objects.select_related(
        'enrollment__user', 'enrollment__training', 'template'
    ).all()
    return render(request, 'certificates/certificate_list.html', {'certificates': certs})


@login_required
@role_required(['admin', 'hr'])
def issue_certificate(request, enrollment_pk):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, status='completed')
    cert, created = _issue_cert(enrollment, issued_by=request.user, request=request)
    if created:
        messages.success(request, f'Certificate {cert.certificate_number} issued with QR code.')
    else:
        messages.warning(request, 'Certificate already issued.')
    return redirect('certificate_detail', pk=cert.pk)


@login_required
@role_required(['admin', 'hr'])
def certificate_revoke(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    if request.method == 'POST':
        cert.is_valid = False
        cert.revoked_reason = request.POST.get('reason', '')
        cert.save()
        messages.success(request, f'Certificate {cert.certificate_number} revoked.')
        return redirect('certificate_list')
    return render(request, 'certificates/revoke_confirm.html', {'cert': cert})


# ─── Template management ──────────────────────────────────────────────────────

@login_required
@role_required(['admin', 'hr'])
def template_list(request):
    templates = CertificateTemplate.objects.all()
    return render(request, 'certificates/template_list.html', {'templates': templates})


@login_required
@role_required(['admin', 'hr'])
def template_create(request):
    if request.method == 'POST':
        try:
            tmpl = _save_template(request, CertificateTemplate())
            messages.success(request, f'Template "{tmpl.name}" created.')
            return redirect('template_list')
        except ValueError as e:
            messages.error(request, str(e))
    blank = CertificateTemplate()
    return render(request, 'certificates/template_form.html', {
        'tmpl': blank,
        'title': 'Create Certificate Template',
        'is_new': True,
        'border_style_choices': CertificateTemplate._meta.get_field('border_style').choices,
        'layout_type_choices': CertificateTemplate.LayoutType.choices,
    })


@login_required
@role_required(['admin', 'hr'])
def template_edit(request, pk):
    tmpl = get_object_or_404(CertificateTemplate, pk=pk)
    if request.method == 'POST':
        try:
            _save_template(request, tmpl)
            messages.success(request, f'Template "{tmpl.name}" updated.')
            return redirect('template_list')
        except ValueError as e:
            messages.error(request, str(e))
    return render(request, 'certificates/template_form.html', {
        'tmpl': tmpl,
        'title': f'Edit — {tmpl.name}',
        'is_new': False,
        'border_style_choices': CertificateTemplate._meta.get_field('border_style').choices,
        'layout_type_choices': CertificateTemplate.LayoutType.choices,
    })


@login_required
@role_required(['admin', 'hr'])
def template_activate(request, pk):
    # Deactivate all, activate selected
    CertificateTemplate.objects.all().update(is_active=False)
    tmpl = get_object_or_404(CertificateTemplate, pk=pk)
    tmpl.is_active = True
    tmpl.save()
    messages.success(request, f'"{tmpl.name}" is now the active certificate template.')
    return redirect('template_list')


@login_required
@role_required(['admin', 'hr'])
def template_preview(request, pk):
    tmpl = get_object_or_404(CertificateTemplate, pk=pk)
    return render(request, 'certificates/template_preview.html', {'tmpl': tmpl})


def _validate_logo(upload):
    """Raise ValueError if the uploaded file is not an allowed image (magic-byte check)."""
    validate_image_upload(upload)


def _save_template(request, tmpl):
    p = request.POST
    tmpl.name                   = p.get('name', tmpl.name)
    tmpl.layout_type            = p.get('layout_type', tmpl.layout_type)
    tmpl.competency_level_label = p.get('competency_level_label', tmpl.competency_level_label)
    tmpl.header_text            = p.get('header_text', tmpl.header_text)
    tmpl.subheader        = p.get('subheader', tmpl.subheader)
    tmpl.intro_line       = p.get('intro_line', tmpl.intro_line)
    tmpl.body_after       = p.get('body_after', tmpl.body_after)
    tmpl.footer_note      = p.get('footer_note', tmpl.footer_note)
    tmpl.signatory1_name     = p.get('signatory1_name', '')
    tmpl.signatory1_position = p.get('signatory1_position', '')
    tmpl.signatory1_label    = p.get('signatory1_label', 'Issued by')
    tmpl.signatory2_name     = p.get('signatory2_name', '')
    tmpl.signatory2_position = p.get('signatory2_position', '')
    tmpl.signatory2_label    = p.get('signatory2_label', '')
    tmpl.primary_color    = p.get('primary_color', tmpl.primary_color)
    tmpl.accent_color     = p.get('accent_color', tmpl.accent_color)
    tmpl.background_color = p.get('background_color', tmpl.background_color)
    tmpl.border_style     = p.get('border_style', tmpl.border_style)
    tmpl.orientation      = p.get('orientation', tmpl.orientation)
    tmpl.show_score       = bool(p.get('show_score'))
    tmpl.show_duration    = bool(p.get('show_duration'))
    tmpl.show_cert_number = bool(p.get('show_cert_number'))
    tmpl.created_by       = request.user
    tmpl.save()
    # Handle logo uploads with type and size validation
    for field in ('logo_left', 'logo_right'):
        upload = request.FILES.get(field)
        if upload:
            _validate_logo(upload)
            setattr(tmpl, field, upload)
    tmpl.save()
    return tmpl