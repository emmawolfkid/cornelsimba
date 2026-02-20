from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string


def send_leave_email(subject, to_email, template_name, context):
    """
    Generic leave email sender (HTML + text fallback)
    """

    text_content = render_to_string(template_name, context)
    html_content = render_to_string(template_name, context)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()
