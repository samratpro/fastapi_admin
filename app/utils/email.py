import smtplib
from email.mime.text import MIMEText
from app.core.config import settings

class EmailSender:
    @staticmethod
    async def send_verification_email(to_email: str, code: str):
        msg = MIMEText(
            f'Your verification code is: {code}\n\nPlease use this code to verify your email address.'
        )
        msg['Subject'] = 'Verify your email'
        msg['From'] = settings.SMTP_USER
        msg['To'] = to_email

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")
            raise
    @staticmethod
    async def send_password_reset_email(to_email: str, reset_code: str) -> None:
        """
        Send a password reset email with the provided reset code.
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{reset_code}"
        msg = MIMEText(
            f"Use the following code to reset your password: {reset_code}\n\n"
            f"If you did not request this, please ignore this email."
        )
        msg['Subject'] = 'Password Reset Request'
        msg['From'] = settings.SMTP_USER
        msg['To'] = to_email

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)