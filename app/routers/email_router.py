"""
Email router for creating and controlling the endpoint. 
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from app.services.email_service import EmailService
from app.schemas.email import SendEmailRequestBody, SendEmailResponseBody
from app.utils import (
    EmailSender,
    success_response,
    get_email_sender,
    require_authentication,
    logger,
)
from app.config import TEMPLATE_HASH_MAP

email_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@email_router.post("/email", response_model=SendEmailResponseBody)
@require_authentication()
async def send_email(
    request: Request,
    email_details: SendEmailRequestBody,
    email_sender: EmailSender = Depends(get_email_sender),
):
    """
    Sends an email to the recipient using provided details.

    Args:
        email_details (SendEmailRequestBody): The details of the email to be sent.
        email_sender (EmailSender): Email sender dependency injection.

    Returns:
        success_response: JSONResponse type object containing status_code, message and body.
    """
    logger.info(
        "Inside send_email router, request origin %s ...", request.headers["origin"]
    )
    email_service = EmailService(email_sender)
    try:
        template_name = TEMPLATE_HASH_MAP.get(email_details.id)
        template = templates.get_template(template_name)
        rendered_body = template.render(**email_details.body)
        _ = email_service.send_email(email_details, rendered_body)
        return success_response(status_code=200, message="Success", body=email_details)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong. Try again later.",
        ) from e
