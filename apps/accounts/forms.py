from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Division
from .file_validators import validate_image_upload

# ── Privacy Notice text ──────────────────────────────────────────────────────
PRIVACY_NOTICE_SHORT = (
    'By signing in, I acknowledge that I have read and understood the '
    '<a href="/accounts/privacy-notice/" target="_blank" style="color:#2563eb;">'
    'DOTR-LMS Data Privacy Notice</a> and consent to the collection and '
    'processing of my personal data in accordance with <strong>Republic Act 10173</strong> '
    '(Data Privacy Act of 2012) and its Implementing Rules and Regulations.'
)


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Employee ID or Username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )
    # Shown only when the user has not yet consented (privacy_consent=False).
    # The view injects `require_consent=True` into the context when needed.
    privacy_consent = forms.BooleanField(
        required=False,
        label='',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'privacyConsent'}),
    )


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=(
            'Minimum 8 characters. Must include uppercase, lowercase, '
            'a number, and a special character.'
        ),
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'employee_id',
                  'role', 'division', 'position', 'salary_grade', 'employment_status',
                  'contact_number', 'date_hired', 'supervisor']
        widgets = {
            **{
                field: forms.TextInput(attrs={'class': 'form-control'})
                for field in ['username', 'first_name', 'last_name', 'email',
                              'employee_id', 'position', 'contact_number']
            },
            'date_hired': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'text', 'placeholder': 'YYYY-MM-DD'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not hasattr(field.widget, 'attrs'):
                continue
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('confirm_password'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'employee_id',
                  'role', 'division', 'position', 'salary_grade', 'employment_status',
                  'contact_number', 'date_hired', 'supervisor', 'avatar']
        widgets = {
            'date_hired': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'text', 'placeholder': 'YYYY-MM-DD'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'read'):
            try:
                validate_image_upload(avatar)
            except ValueError as e:
                raise forms.ValidationError(str(e))
        return avatar


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
    )
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text=(
            'Minimum 8 characters. Must include uppercase, lowercase, '
            'a number, and a special character.'
        ),
    )
    confirm_new_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get('current_password')
        if not self.user.check_password(current):
            raise forms.ValidationError('Current password is incorrect.')
        return current

    def clean_new_password(self):
        new_pw = self.cleaned_data.get('new_password')
        if new_pw:
            try:
                validate_password(new_pw, self.user)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return new_pw

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_new_password'):
            raise forms.ValidationError('New passwords do not match.')
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save(update_fields=['password'])
        return self.user


class DataErasureRequestForm(forms.Form):
    reason = forms.CharField(
        label='Reason for Data Erasure Request',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': (
                'Please describe why you are requesting the erasure of your '
                'personal data (e.g., separation from service, data no longer '
                'necessary for original purpose, withdrawal of consent).'
            ),
        }),
        min_length=20,
        help_text='Minimum 20 characters. Be as specific as possible.',
    )
    confirm = forms.BooleanField(
        label=(
            'I understand that this request will anonymise my personal data. '
            'Training completion records and audit logs will be retained as '
            'required by law (COA, CSC) but will no longer be linked to my identity.'
        ),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


class ErasureReviewForm(forms.Form):
    action = forms.ChoiceField(
        choices=[('approved', 'Approve'), ('rejected', 'Reject')],
        widget=forms.RadioSelect,
    )
    review_remarks = forms.CharField(
        label='Remarks',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
    )


class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = ['name', 'code', 'description', 'head']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
