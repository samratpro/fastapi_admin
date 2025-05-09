import smtplib
from email.mime.text import MIMEText
from app.core.config import settings

class EmailSender:
    @staticmethod
    async def send_verification_email(to_email: str, token: str):
        verification_url = f"{settings.FRONTEND_URL}/verify/{token}"
        
        msg = MIMEText(
            f'Please click the following link to verify your email: {verification_url}'
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
