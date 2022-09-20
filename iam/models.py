import unicodedata

from django.utils import timezone
from django.db import models
from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Permission, UserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.validators import UnicodeUsernameValidator


from general.utils import *


class AbstractGroup(models.Model):
    name = models.CharField(_('name'), max_length=150, unique=False)
    builtin = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class UserGroup(AbstractGroup):
    folder = models.ForeignKey("general.Folder", verbose_name=_(
        "Domain"), on_delete=models.CASCADE, default=None)

    class Meta:
        verbose_name = _('user_group')
        verbose_name_plural = _('user_groups')

    def __str__(self) -> str:
        if self.builtin:
            return f"{self.folder.name} - {BUILTIN_USERGROUP_CODENAMES.get(self.name)}"
        return self.name

    def get_user_groups(user):
        l = []
        for user_group in UserGroup.objects.all():
            if user in user_group.user_set.all():
                l.append(user_group)
        return l

    def get_manager_user_groups(manager):
        l = []
        folders = []
        for user_group in UserGroup.get_user_groups(manager):
            for ra in user_group.roleassignment_set.all():
                if ra.role.name == "BI-RL-DMA":
                    for folder in ra.perimeter_folders.all():
                        folders.append(folder)
        for user_group in UserGroup.objects.all():
            if user_group.folder in folders:
                l.append(user_group)
        return l


class Role(AbstractGroup):
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('permissions'),
        blank=True,
    )

    def __str__(self) -> str:
        if self.builtin:
            return f"{BUILTIN_ROLE_CODENAMES.get(self.name)}"
        return self.name
        

class PermissionsMixin(models.Model):
    # is_superuser is not used in this project, it was kept for simplicity's
    # sake and to avoid having to rewrite the UserManager. It will be removed.
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_(
            'Designates that this user has all permissions without '
            'explicitly assigning them.'
        ),
    )
    user_groups = models.ManyToManyField(
        UserGroup,
        verbose_name=_('user groups'),
        blank=True,
        help_text=_(
            'The user_groups this user belongs to. A user will get all permissions '
            'granted to each of their user_groups.'
        ),
        related_name="user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="user_set",
        related_query_name="user",
    )

    class Meta:
        abstract = True

        

class User(AbstractBaseUser, PermissionsMixin):
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
    )
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), blank=True, unique=True, null=True)
    # is_staff won't be used, but is required by Django's UserManager()
    # We might ditch the UserManager() and use our own, but for now, we'll
    # just set is_staff to False.
    is_staff = models.BooleanField(
        default=False,
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = 'email'

    # USERNAME_FIELD is used as the unique identifier for the user
    # and is required by Django to be set to a non-empty value.
    # See https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#django.contrib.auth.models.CustomUser.USERNAME_FIELD
    USERNAME_FIELD = 'username'
    # REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        swappable = 'AUTH_USER_MODEL'

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()

    def get_short_name(self):
        return self.first_name

    def get_username(self) -> str:
        return self.username


class UsernameField(forms.CharField):
    def to_python(self, value):
        return unicodedata.normalize('NFKC', super().to_python(value))

    def widget_attrs(self, widget):
        return {
            **super().widget_attrs(widget),
            'autocapitalize': 'none',
            'autocomplete': 'username',
        }


class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'password_mismatch': _('The two password fields didn’t match.'),
    }
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = User
        fields = ("username",)
        field_classes = {'username': UsernameField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._meta.model.USERNAME_FIELD in self.fields:
            self.fields[self._meta.model.USERNAME_FIELD].widget.attrs['autofocus'] = True

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get('password2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password2', error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user