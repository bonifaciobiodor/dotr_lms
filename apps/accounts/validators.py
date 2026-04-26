"""
Custom password validators for RA 10173 / government password policy compliance.
Enforces: minimum length, uppercase, lowercase, digit, special character.
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexPasswordValidator:
    """
    Require at least one uppercase letter, one lowercase letter,
    one digit, and one special character.
    Minimum length is enforced separately by MinimumLengthValidator in settings.
    """

    SPECIAL_CHARS = r'[!@#$%^&*(),.?":{}|<>_\-\+=/\\;\[\]\'`~]'

    def validate(self, password, user=None):
        errors = []
        if not re.search(r'[A-Z]', password):
            errors.append(_('at least one uppercase letter (A–Z)'))
        if not re.search(r'[a-z]', password):
            errors.append(_('at least one lowercase letter (a–z)'))
        if not re.search(r'\d', password):
            errors.append(_('at least one number (0–9)'))
        if not re.search(self.SPECIAL_CHARS, password):
            errors.append(_('at least one special character (!@#$%^&* …)'))
        if errors:
            raise ValidationError(
                _('Password must contain %(requirements)s.'),
                code='password_too_simple',
                params={'requirements': ', '.join(errors)},
            )

    def get_help_text(self):
        return _(
            'Your password must contain at least one uppercase letter, '
            'one lowercase letter, one number, and one special character.'
        )
