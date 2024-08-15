import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.settings import EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

def send_email(to_email: str, subject: str, content: str):
    message = MIMEMultipart()
    message['From'] = EMAIL_HOST_USER
    message['To'] = to_email
    message['Subject'] = subject

    # Add body to email
    message.attach(MIMEText(content, 'plain'))

    # Create SMTP session
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Enable security
            # Login to the server
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

            # Send the email
            text = message.as_string()
            server.sendmail(EMAIL_HOST_USER, to_email, text)

        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise