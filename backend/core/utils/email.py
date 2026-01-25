import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import decode_header
from django.conf import settings
from core.models import EmailConfig
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def get_email_config(user):
    """Helper to get email config for a user"""
    try:
        return user.email_config
    except EmailConfig.DoesNotExist:
        return None

def send_invoice_email(user, recipient_email, subject, body, attachment_path=None, in_reply_to_id=None):
    """
    Send an email via SMTP and save to Sent folder via IMAP.
    """
    config = get_email_config(user)
    if not config:
        raise ValueError("Email configuration not found for this user.")

    msg = MIMEMultipart()
    msg['From'] = config.smtp_user
    msg['To'] = recipient_email
    msg['Subject'] = subject
    # Important for proper date on the saved message
    msg['Date'] = email.utils.formatdate() 

    if in_reply_to_id:
        msg['In-Reply-To'] = in_reply_to_id
        msg['References'] = in_reply_to_id

    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        try:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(
                    f.read(),
                    Name=filename
                )
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to attach file: {e}")

    try:
        # 1. Send via SMTP
        if config.smtp_port == 465:
            server = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15)
            if config.use_tls:
                server.starttls()
                
        server.login(config.smtp_user, config.smtp_password)
        server.send_message(msg)
        server.quit()

        # 2. Append to Sent Folder via IMAP
        try:
            # Fallback for IMAP timeout
            try:
                imap = imaplib.IMAP4_SSL(config.imap_host, config.imap_port, timeout=10)
            except TypeError:
                imap = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
                
            imap.login(config.imap_user, config.imap_password)
            
            # Identify "Sent" folder (common names: Sent, Sent Items, [Gmail]/Sent Mail)
            # Confirmed as 'INBOX.Sent' for this server'
            sent_folder = "INBOX.Sent"
            
            # For Gmail specifically: "[Gmail]/Sent Mail"
            if "gmail" in config.imap_host:
                sent_folder = "[Gmail]/Sent Mail"
                
            # Append the message
            # timestmap is now (None means current time)
            imap.append(sent_folder, '\\Seen', imaplib.Time2Internaldate(datetime.now().timestamp()), msg.as_bytes())
            imap.logout()
            
        except Exception as e:
            logger.warning(f"Failed to save to Sent folder: {e}")
            # Non-critical error, don't fail the sending process

        return True
    except Exception as e:
        logger.error(f"SMTP Error: {e}")
        raise e

def fetch_recent_threads(user, sender_email, limit=10):
    """
    Fetch recent emails related to specific email address(es) (FROM or TO) using IMAP.
    sender_email can be a single email or comma-separated string.
    Searches both INBOX and Sent folder.
    Returns list of dicts: {subject, date, message_id, snippet}
    """
    config = get_email_config(user)
    if not config or not sender_email:
        return []

    # Handle multiple emails
    emails_to_check = [e.strip() for e in sender_email.split(',') if e.strip()]
    if not emails_to_check:
        return []

    threads = []
    # Helper to extract text from message
    def get_text_from_msg(msg):
        text = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        text += part.get_payload(decode=True).decode(errors="replace")
                        break # Found plain text, stop
                    except: pass
                elif content_type == "text/html":
                     # Fallback to HTML if no plain text
                     pass 
        else:
             content_type = msg.get_content_type()
             if content_type == "text/plain":
                  try:
                      text = msg.get_payload(decode=True).decode(errors="replace")
                  except: pass
        
        # Clean up whitespace
        return " ".join(text.split())[:150] + "..." if text else ""

    def fetch_from_folder(mail_conn, folder, criteria):
        local_threads = []
        try:
            status, _ = mail_conn.select(folder)
            if status != "OK":
                return []
                
            status, messages = mail_conn.search(None, criteria)
            if status != "OK":
                return []
                
            email_ids = messages[0].split()
            # optimizing: fetch latest X messages
            latest_email_ids = email_ids[-limit:]
            
            for num in reversed(latest_email_ids):
                # Fetch full message RFC822 to get body
                status, msg_data = mail_conn.fetch(num, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        try:
                            msg = email.message_from_bytes(response_part[1])
                            
                            subject_header = msg.get("Subject", "")
                            subject_decoded_list = decode_header(subject_header)
                            subject = ""
                            for part, encoding in subject_decoded_list:
                                if isinstance(part, bytes):
                                    subject += part.decode(encoding if encoding else "utf-8", errors="replace")
                                else:
                                    subject += part
                            
                            date_str = msg.get("Date")
                            # Parse date for sorting
                            date_obj = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.min
                            
                            msg_id = msg.get("Message-ID")
                            snippet = get_text_from_msg(msg)
                            
                            local_threads.append({
                                'subject': subject,
                                'date': date_str, 
                                'date_obj': date_obj,
                                'message_id': msg_id,
                                'folder': folder,
                                'snippet': snippet
                            })
                        except Exception as parse_err:
                            logger.warn(f"Error parsing email {num}: {parse_err}")
                            continue
        except Exception as e:
            logger.warn(f"Error fetching from {folder}: {e}")
        
        return local_threads

    try:
        # Note: Some python versions/envs don't support timeout in __init__ for IMAP4_SSL
        try:
             mail = imaplib.IMAP4_SSL(config.imap_host, config.imap_port, timeout=10)
        except TypeError:
             # Fallback if timeout arg not supported
             mail = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
             
        mail.login(config.imap_user, config.imap_password)
        
        # Search for each email address
        for email_addr in emails_to_check:
            # 1. Fetch from Inbox (FROM customer)
            threads.extend(fetch_from_folder(mail, "inbox", f'(FROM "{email_addr}")'))
            
            # 2. Fetch from Sent (TO customer)
            # Try to guess Sent folder name
            # Based on debug output, it is 'INBOX.Sent' for this server
            sent_folder = "INBOX.Sent"
            
            # Keep Gmail fallback just in case
            if "gmail" in config.imap_host:
                sent_folder = "[Gmail]/Sent Mail"
                
            threads.extend(fetch_from_folder(mail, sent_folder, f'(TO "{email_addr}")'))
        
        mail.logout()
        
        # Deduplicate by Message-ID (in case same email found via multiple addresses context?)
        # Or just sort.
        unique_threads = {t['message_id']: t for t in threads}.values()
        
        # Sort by date desc
        # Handle timezone-aware vs naive (make all naive UTC for simple comparison or just ignore error if mixed)
        # parsedate_to_datetime returns timezone aware if timezone is in string.
        # We'll just try to sort; if it fails due to tz mismatch, we'll handle it.
        sorted_threads = list(unique_threads)
        try:
            sorted_threads.sort(key=lambda x: x['date_obj'], reverse=True)
        except TypeError:
            # Fallback for mixed offset-aware and offset-naive
             sorted_threads.sort(key=lambda x: str(x['date']), reverse=True)
             
        return sorted_threads[:limit]

    except Exception as e:
        logger.error(f"IMAP Error: {e}")
        return []
