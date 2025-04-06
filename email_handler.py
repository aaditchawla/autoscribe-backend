import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName,
    FileType, Disposition, ContentId
)
import base64
from dotenv import load_dotenv
import logging
import certifi
import ssl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def send_summary_email(recipients, summary, pdf_data, translated_summary=None):
    """
    Send meeting summary via email with PDF attachment using SendGrid
    
    Args:
        recipients (list): List of email addresses
        summary (str): Meeting summary text
        pdf_data (bytes): PDF file data
        translated_summary (str, optional): Translated summary text
    """
    try:
        # SendGrid configuration
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        sender_email = os.getenv('SENDGRID_FROM_EMAIL')  # Verified sender email in SendGrid
        
        if not sendgrid_api_key or not sender_email:
            raise ValueError("SendGrid API key or sender email not configured")

        logger.info(f"Using SendGrid API key: {sendgrid_api_key[:5]}...")
        logger.info(f"Using sender email: {sender_email}")

        # Create email content
        preview = summary[:500] + "..." if len(summary) > 500 else summary
        body = f"""
        Hello,

        Here's your meeting summary:

        {preview}

        Please find the complete summary attached as a PDF.

        Best regards,
        AutoScribe
        """

        if translated_summary:
            body += "\n\nTranslated Summary Preview:\n"
            translated_preview = translated_summary[:500] + "..." if len(translated_summary) > 500 else translated_summary
            body += translated_preview

        # Create the email
        message = Mail(
            from_email=sender_email,
            to_emails=recipients,
            subject='Meeting Summary - AutoScribe',
            plain_text_content=body
        )

        # Attach PDF
        encoded_pdf = base64.b64encode(pdf_data).decode()
        attachment = Attachment()
        attachment.file_content = FileContent(encoded_pdf)
        attachment.file_type = FileType('application/pdf')
        attachment.file_name = FileName('meeting_summary.pdf')
        attachment.disposition = Disposition('attachment')
        attachment.content_id = ContentId('Meeting Summary')
        message.attachment = attachment

        # Create SSL context with proper certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        # Create SendGrid client with proper SSL configuration
        sg = SendGridAPIClient(api_key=sendgrid_api_key)
        sg.client.verify_ssl_certs = True
        sg.client.ssl_context = ssl_context
        
        # Send the email and log the response
        logger.info(f"Attempting to send email to {recipients}")
        try:
            response = sg.send(message)
            logger.info(f"SendGrid Response Status Code: {response.status_code}")
            logger.info(f"SendGrid Response Headers: {response.headers}")
            logger.info(f"SendGrid Response Body: {response.body}")
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {len(recipients)} recipients")
                return True
            else:
                logger.error(f"Failed to send email. Status code: {response.status_code}")
                logger.error(f"Response body: {response.body}")
                raise Exception(f"Failed to send email. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"SendGrid API Error: {str(e)}")
            if hasattr(e, 'body'):
                logger.error(f"Error body: {e.body}")
            raise

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise 