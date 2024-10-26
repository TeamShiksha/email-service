"""
For all controllers
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from schemas import SendEmailRequestBody, SendEmailResponseBody

emailRouter = APIRouter()
templates = Jinja2Templates(directory="templates")


# use SendEmailResponseBody response model here
@emailRouter.post(
    "/send_email",
)
async def send_email(request: Request, email_details: SendEmailRequestBody):
    """
    Sends email to the receipient

    Args:

        request: The request details
        email_details: Details about email template to be used and recipient information

    Returns:

        message: A success or failed message with status and details.
    """
    print(email_details)
    # write the code here for sending emails

    # create a generic function for generating response.
    return {"message": "Email sent successfully."}
