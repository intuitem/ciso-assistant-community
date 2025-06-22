from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string


def send_basic_mail(): ...


def send_rich_mail(): ...
