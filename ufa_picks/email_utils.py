# -*- coding: utf-8 -*-
"""Email utility functions."""
import datetime as dt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app, render_template, url_for


def send_email(recipients, subject, html_body, text_body=None):
    """Send an email via SMTP using app config.

    Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_TOKEN from current_app.config.
    """
    smtp_host = current_app.config.get("SMTP_HOST")
    smtp_port = current_app.config.get("SMTP_PORT", 587)
    smtp_user = current_app.config.get("SMTP_USER")
    smtp_token = current_app.config.get("SMTP_TOKEN")

    if not smtp_host or not smtp_user:
        current_app.logger.warning("SMTP not configured; skipping email send.")
        return

    if isinstance(recipients, str):
        recipients = [recipients]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls()
                server.ehlo()
            if smtp_user and smtp_token:
                server.login(smtp_user, smtp_token)
            server.sendmail(smtp_user, recipients, msg.as_string())
        current_app.logger.info(f"Email sent to {recipients}: {subject}")
    except Exception as e:
        current_app.logger.exception(f"Failed to send email to {recipients}: {e}")
        raise


def send_welcome_email(user, new_user=True):
    """Send a welcome email to a newly registered user."""
    from ufa_picks.game.models import Game

    year = str(dt.datetime.now().year)
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    upcoming = (
        Game.query.filter(Game.season == year, Game.start_timestamp > now)
        .order_by(Game.week)
        .first()
    )

    picks_url = None
    week_num = None
    if upcoming:
        week_num = upcoming.week
        picks_url = url_for("game.week", year=year, week_num=week_num, _external=True)

    profile_url = url_for("user.edit_profile", _external=True)

    html_body = render_template(
        "emails/welcome.html",
        user=user,
        picks_url=picks_url,
        week_num=week_num,
        profile_url=profile_url,
        new_user=new_user
    )
    send_email(
        recipients=user.email,
        subject="Welcome to UFA Picks!",
        html_body=html_body,
    )


def send_temp_password_email(user, temp_password):
    """Send a temporary password email to a user."""
    html_body = render_template(
        "emails/temp_password.html", user=user, temp_password=temp_password
    )
    send_email(
        recipients=user.email,
        subject="UFA Picks — Password Reset",
        html_body=html_body,
    )
