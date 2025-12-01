"""
Custom email backend that logs minimal information instead of full email content.
This makes logs much more readable during development.
"""

import logging
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend

logger = logging.getLogger("email")


class MinimalConsoleEmailBackend(ConsoleEmailBackend):
    """
    Email backend that logs only recipient and subject instead of full email content.
    Extends the console backend but overrides the write_message method.
    """

    def write_message(self, message):
        """
        Write a minimal log entry instead of the full email content.
        """
        recipients = ", ".join(message.to)
        subject = message.subject
        from_email = message.from_email

        # Log minimal information
        msg = (
            f"\n{'='*70}\n"
            f"Email sent:\n"
            f"  From: {from_email}\n"
            f"  To: {recipients}\n"
            f"  Subject: {subject}\n"
            f"{'='*70}\n"
        )

        self.stream.write(msg)
        self.stream.flush()
