from fastapi import APIRouter, Body
from email.message import EmailMessage
import base64
from pydantic import BaseModel, Field
from typing import Optional

from support_services.utils.logger import get_logger

logger = get_logger(__name__)

email_router = APIRouter(prefix="/common/email", tags=["common"])

class EmailRequestBody(BaseModel):
    sender: Optional[str] = Field(None, description="The sender's email address.")
    recipient: str = Field(..., description="The recipient's email address.")
    subject: Optional[str] = Field(None, description="The subject of the email.")
    email_body: str = Field(..., description="The body of the email.")

@email_router.post(
    "/raw",
    summary="Generate RFC 2822 formatted email message as base64url encoded string.",
    description="Generate an entire email message in RFC 2822 format and base64url encoded string. This format is commonly used by email APIs for sending raw email messages.",
)
def get_raw_email_body(
    email_request: EmailRequestBody = Body(...)
):
    """
    Generates an entire email message in RFC 2822 format and base64url encoded string.
    
    This format is commonly used by email APIs for sending raw email messages.
    Based on standard email message formatting practices.
    
    Returns:
        dict: Contains 'raw' key with base64url-encoded RFC 2822 formatted email message
    """
    logger.info(f"Request received for /common/email/raw")

    # Create EmailMessage object (following Google sample pattern)
    message = EmailMessage()
    message.set_content(email_request.email_body)
    
    # Set headers
    message["To"] = email_request.recipient
    if email_request.sender:
        message["From"] = email_request.sender
    if email_request.subject:
        message["Subject"] = email_request.subject

    # Encode message following Google sample pattern
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return {"raw": encoded_message}
