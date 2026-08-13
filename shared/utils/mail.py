import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import yaml
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 30


class EmailSender:
    """
    Send plain-text emails with optional image attachments.
    """

    def __init__(self, smtp_server, smtp_port, email_address, email_password):
        """
        Initialize SMTP sender settings.

        Args:
            smtp_server (str): SMTP host name.
            smtp_port (int): SMTP port.
            email_address (str): Sender email address.
            email_password (str): Sender password or app password.

        Returns:
            None
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_address = email_address
        self.email_password = email_password

    def send_email(self, to_email, subject, body, attachment_paths=None):
        """
        Send an email with optional image attachments.

        Args:
            to_email (str): Destination email address.
            subject (str): Email subject.
            body (str): Plain-text body.
            attachment_paths (list[str] | None): Image attachment paths.

        Returns:
            None
        """
        message = MIMEMultipart()
        message["From"] = self.email_address
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if attachment_paths:
            for attachment_path in attachment_paths:
                try:
                    if not os.path.exists(attachment_path):
                        logger.error(f"Attachment file not found: {attachment_path}")
                        continue

                    with open(attachment_path, "rb") as attachment:
                        part = MIMEImage(
                            attachment.read(), name=os.path.basename(attachment_path)
                        )

                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(attachment_path)}",
                    )
                    message.attach(part)
                except Exception as e:
                    raise

        try:
            with smtplib.SMTP(
                self.smtp_server, self.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
            ) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(message)
        except Exception as e:
            raise


def load_secrets(secret_path):
    """
    Load secret values from YAML.

    Args:
        secret_path (str): Path to secret YAML.

    Returns:
        Dict: Parsed secrets.
    """
    with open(secret_path, "r", encoding="utf-8") as file:
        secrets = yaml.safe_load(file)
    return secrets


def debug_on_colab(secret_path: str = "./secret.yaml"):
    """
    Send a test email using the settings in secret.yaml.

    Usage:
    1. Upload `secret.yaml` to the `/content` directory in Google Colab.
    2. Paste this code into a code cell in Google Colab.
    3. Run the cell (Shift + Enter).
    """

    secrets = load_secrets(secret_path)

    mail_config = secrets["mail"]
    smtp_server = mail_config["smtp_server"]
    smtp_port = mail_config["smtp_port"]
    email_address = mail_config["from"]
    email_password = mail_config["password"]
    to_email = mail_config["to"]

    subject = "Test mail"
    body = "Test mail from seasonal-foods-scraper."

    sender = EmailSender(smtp_server, smtp_port, email_address, email_password)
    sender.send_email(to_email, subject, body)
    print("Email has been sent.")


if __name__ == "__main__":
    debug_on_colab()
