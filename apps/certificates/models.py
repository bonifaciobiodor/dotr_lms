import uuid
from django.db import models
from django.conf import settings


class CertificateTemplate(models.Model):
    """Customisable certificate template — HR can modify it at any time."""

    class Orientation(models.TextChoices):
        LANDSCAPE = 'landscape', 'Landscape'
        PORTRAIT  = 'portrait',  'Portrait'

    name         = models.CharField(max_length=200, default='DOTR Official Certificate')
    is_active    = models.BooleanField(default=True, help_text='The active template is used for all new certificates.')

    # Branding
    header_text  = models.CharField(max_length=300, default='Department of Transportation')
    subheader    = models.CharField(max_length=300, default='Republic of the Philippines')
    logo_left    = models.ImageField(upload_to='cert_templates/', null=True, blank=True, help_text='Left logo (DOTR seal)')
    logo_right   = models.ImageField(upload_to='cert_templates/', null=True, blank=True, help_text='Right logo (PH flag)')

    # Body copy
    intro_line   = models.CharField(max_length=300, default='is proudly presented to')
    body_after   = models.TextField(default='for his/her successful participation and completion of', blank=True)
    footer_note  = models.TextField(blank=True, default='')

    # Signatory 1
    signatory1_name     = models.CharField(max_length=200, default='')
    signatory1_position = models.CharField(max_length=200, default='Director IV for Administrative Service concurrent\nManagement Information Systems Service')
    signatory1_label    = models.CharField(max_length=100, default='')

    # Signatory 2 (optional)
    signatory2_name     = models.CharField(max_length=200, blank=True)
    signatory2_position = models.CharField(max_length=200, blank=True)
    signatory2_label    = models.CharField(max_length=100, blank=True)

    # Layout
    class LayoutType(models.TextChoices):
        CLASSIC = 'classic', 'Classic (Centered)'
        MODERN  = 'modern',  'Modern (Blue Sidebar)'

    layout_type = models.CharField(
        max_length=10, choices=LayoutType.choices, default=LayoutType.CLASSIC,
        help_text='Classic: traditional centered layout. Modern: DOTR blue sidebar with competency panel.'
    )
    competency_level_label = models.CharField(
        max_length=100, default='Basic Level',
        help_text='Proficiency level label shown in the modern layout sidebar (e.g. Basic Level, Intermediate Level)'
    )

    # Styling
    orientation       = models.CharField(max_length=10, choices=Orientation.choices, default=Orientation.LANDSCAPE)
    primary_color     = models.CharField(max_length=7, default='#003087',  help_text='Hex color e.g. #003087')
    accent_color      = models.CharField(max_length=7, default='#b8860b',  help_text='Gold accent — hex color')
    background_color  = models.CharField(max_length=7, default='#FFFFFF')
    border_style      = models.CharField(
        max_length=20,
        choices=[('classic','Classic Double Border'),('modern','Modern Single Line'),('minimal','Minimal'),('ribbon','Ribbon Band')],
        default='classic'
    )
    show_score        = models.BooleanField(default=True)
    show_duration     = models.BooleanField(default=True)
    show_cert_number  = models.BooleanField(default=True)

    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} {'[ACTIVE]' if self.is_active else ''}"

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first() or cls.objects.first()

    class Meta:
        app_label = 'certificates'
        ordering  = ['-is_active', '-updated_at']


class Certificate(models.Model):
    enrollment = models.OneToOneField(
        'trainings.Enrollment', on_delete=models.CASCADE, related_name='certificate'
    )
    certificate_number = models.CharField(max_length=100, unique=True)
    template    = models.ForeignKey(CertificateTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    qr_code     = models.ImageField(upload_to='certificates/qr/', null=True, blank=True)
    issued_date = models.DateField(auto_now_add=True)
    issued_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='issued_certificates'
    )
    is_valid       = models.BooleanField(default=True)
    revoked_reason = models.TextField(blank=True)

    def __str__(self):
        return f"CERT-{self.certificate_number} | {self.enrollment.user} - {self.enrollment.training.title}"

    @classmethod
    def generate_certificate_number(cls):
        return f"DOTR-{uuid.uuid4().hex[:8].upper()}"

    def get_verify_url(self, request=None):
        """Return the full absolute verification URL."""
        path = f"/certificates/verify/{self.certificate_number}/"
        if request:
            return request.build_absolute_uri(path)
        # Try to build from Django sites framework or fallback
        try:
            from django.conf import settings as dj_settings
            base = getattr(dj_settings, 'SITE_BASE_URL', 'http://localhost:8000')
            return f"{base}{path}"
        except Exception:
            return f"http://localhost:8000{path}"

    def generate_qr(self, request=None):
        """
        Generate a real, scannable QR code PNG and save it.
        Tries qrcode library first, then segno, then skips gracefully.
        Call this after saving the certificate instance.
        """
        import io
        from django.core.files.base import ContentFile

        verify_url = self.get_verify_url(request)

        # ── Attempt 1: qrcode (most common) ──────────────────────────────
        try:
            import qrcode
            from qrcode.image.pure import PyPNGImage

            qr = qrcode.QRCode(
                version=None,           # auto-size
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,              # 4-module quiet zone (spec minimum)
            )
            qr.add_data(verify_url)
            qr.make(fit=True)

            # Try PIL image first (better quality)
            try:
                img = qr.make_image(fill_color='black', back_color='white')
            except Exception:
                img = qr.make_image(image_factory=PyPNGImage)

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            self.qr_code.save(
                f'qr_{self.certificate_number}.png',
                ContentFile(buf.getvalue()),
                save=True
            )
            return True
        except ImportError:
            pass

        # ── Attempt 2: segno ─────────────────────────────────────────────
        try:
            import segno
            qr = segno.make(verify_url, error='m')
            buf = io.BytesIO()
            qr.save(buf, kind='png', scale=10, border=4,
                    dark='black', light='white')
            self.qr_code.save(
                f'qr_{self.certificate_number}.png',
                ContentFile(buf.getvalue()),
                save=True
            )
            return True
        except ImportError:
            pass

        # ── No library available — return False, template will use JS QR ─
        return False

    @property
    def verify_url(self):
        return f"/certificates/verify/{self.certificate_number}/"

    class Meta:
        app_label = 'certificates'
        ordering  = ['-issued_date']
