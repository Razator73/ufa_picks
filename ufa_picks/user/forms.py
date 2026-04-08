# -*- coding: utf-8 -*-
"""User forms."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from .models import User


class RegisterForm(FlaskForm):
    """Register form."""

    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=25)]
    )
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(min=6, max=40)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=40)]
    )
    confirm = PasswordField(
        "Verify password",
        [DataRequired(), EqualTo("password", message="Passwords must match")],
    )

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.user = None

    def validate(self, **kwargs):
        """Validate the form."""
        initial_validation = super(RegisterForm, self).validate()
        if not initial_validation:
            return False
        user = User.query.filter_by(username=self.username.data).first()
        if user:
            self.username.errors.append("Username already registered")
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if user:
            self.email.errors.append("Email already registered")
            return False
        return True


class EditProfileForm(FlaskForm):
    """Edit profile form."""

    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(min=6, max=80)]
    )
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password", validators=[Optional(), Length(min=6, max=40)]
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[Optional(), EqualTo("new_password", message="Passwords must match")],
    )
    get_email_reminder = BooleanField("Send me weekly email reminders")

    def __init__(self, user, *args, **kwargs):
        """Create instance."""
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self._user = user

    def validate(self, **kwargs):
        """Validate the form."""
        initial_validation = super(EditProfileForm, self).validate()
        if not initial_validation:
            return False
        if not self._user.check_password(self.current_password.data):
            self.current_password.errors.append("Current password is incorrect")
            return False
        if self.email.data.lower() != self._user.email.lower():
            existing = User.query.filter(
                User.email == self.email.data, User.id != self._user.id
            ).first()
            if existing:
                self.email.errors.append("Email already in use by another account")
                return False
        return True
