"""
Regenerate QR codes for all certificates.
Run: python manage.py generate_qr_codes
     python manage.py generate_qr_codes --base-url https://yourdomain.gov.ph
     python manage.py generate_qr_codes --cert-number DOTR-ABCD1234
"""
from django.core.management.base import BaseCommand
from apps.certificates.models import Certificate


class Command(BaseCommand):
    help = 'Regenerate QR codes for certificates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-url',
            default='http://localhost:8000',
            help='Base URL of your site (e.g. https://lms.dotr.gov.ph)',
        )
        parser.add_argument(
            '--cert-number',
            default=None,
            help='Regenerate only a specific certificate number',
        )
        parser.add_argument(
            '--missing-only',
            action='store_true',
            help='Only generate QR codes for certificates that have none yet',
        )

    def handle(self, *args, **options):
        base_url = options['base_url'].rstrip('/')
        cert_number = options['cert_number']
        missing_only = options['missing_only']

        qs = Certificate.objects.all()
        if cert_number:
            qs = qs.filter(certificate_number=cert_number)
        if missing_only:
            qs = qs.filter(qr_code='')

        total = qs.count()
        if total == 0:
            self.stdout.write('No certificates found matching the criteria.')
            return

        self.stdout.write(f'Generating QR codes for {total} certificate(s)...')
        self.stdout.write(f'Base URL: {base_url}')

        ok = 0
        fail = 0
        for cert in qs:
            # Temporarily patch get_verify_url to use the supplied base_url
            verify_url = f"{base_url}/certificates/verify/{cert.certificate_number}/"
            success = self._generate(cert, verify_url)
            if success:
                ok += 1
                self.stdout.write(f'  ✓ {cert.certificate_number}')
            else:
                fail += 1
                self.stdout.write(self.style.WARNING(f'  ✗ {cert.certificate_number} — library not available'))

        self.stdout.write('')
        if ok:
            self.stdout.write(self.style.SUCCESS(f'✅ {ok} QR code(s) generated successfully.'))
        if fail:
            self.stdout.write(self.style.WARNING(
                f'⚠  {fail} certificate(s) skipped — install qrcode or segno:\n'
                f'   pip install "qrcode[pil]"\n'
                f'   OR: pip install segno'
            ))

    def _generate(self, cert, verify_url):
        import io
        from django.core.files.base import ContentFile

        # Try qrcode
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(verify_url)
            qr.make(fit=True)
            try:
                img = qr.make_image(fill_color='black', back_color='white')
            except Exception:
                from qrcode.image.pure import PyPNGImage
                img = qr.make_image(image_factory=PyPNGImage)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            cert.qr_code.save(
                f'qr_{cert.certificate_number}.png',
                ContentFile(buf.getvalue()),
                save=True
            )
            return True
        except ImportError:
            pass

        # Try segno
        try:
            import segno
            qr = segno.make(verify_url, error='m')
            buf = io.BytesIO()
            qr.save(buf, kind='png', scale=10, border=4, dark='black', light='white')
            cert.qr_code.save(
                f'qr_{cert.certificate_number}.png',
                ContentFile(buf.getvalue()),
                save=True
            )
            return True
        except ImportError:
            pass

        return False