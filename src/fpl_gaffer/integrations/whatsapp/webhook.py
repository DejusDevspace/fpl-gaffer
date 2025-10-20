import os
import logging
import httpx
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Optional, Any
from fastapi import APIRouter, Request, Response, Form
from langchain_core.messages import HumanMessage
from fpl_gaffer.settings import settings
from fpl_gaffer.graph import graph_builder
from fpl_gaffer.integrations.whatsapp.schema import WhatsAppMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from twilio.rest import Client

logger = logging.getLogger(__name__)

router = APIRouter()

# Whatsapp API config
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
MY_NUMBER = "+2347016035694"

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_NUMBER")
client = Client(account_sid, auth_token)

@router.api_route("/webhook/whatsapp/response", methods=["GET", "POST"])
async def whatsapp_webhook(Body: str = Form()) -> Response:
    """Endpoint to handle WhatsApp webhook events."""

    # Verify whatsapp webook
    # if request.method == "GET":
    #     params = request.query_params
    #     if params.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"):
    #         return Response(content=params.get("hub.challenge"), status_code=200)
    #     return Response(content="Verification token mismatch", status_code=403)

    try:
        # TODO: Handle text and video for twilio requests
        message = WhatsAppMessage(
            message_type="text",
            from_number=twilio_number,
            message_body=Body,
            message_id=MY_NUMBER,
        )

        # # Extract message details from payload
        # message = parse_whatsapp_message(data)
        # if not message:
        #     return Response(content="Unknown event type", status_code=400)
        # logger.info(f"Received data from user {message.from_number}")
        #
        # Process the message through gaffer
        response = await process_message(message)

        # Send message to the user
        success = await send_whatsapp_message(
            to_number=MY_NUMBER,
            message=response
        )

        if not success:
            logger.warning(f"Failed to send message to user: {message.from_number}")
            return Response(content="Failed to send message to user", status_code=500)

        logger.info(f"Message sent successfully to user: {message.from_number}")
        return Response(content="Message processed successfully", status_code=200)
    except Exception as e:
        logger.error(f"Error processing messages: {str(e)}", exc_info=True)
        return Response(content="Internal server error", status_code=500)


def parse_whatsapp_message(data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
    """Parse webhook data into WhatsAppMessage object."""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None

        message = messages[0]

        return WhatsAppMessage(
            message_type=message.get("type", ""),
            from_number=twilio_number,
            message_body=message.get("text", {}).get("body", ""),
            message_id=message.get("id", ""),
            # timestamp=message.get("timestamp", "")
        )
    except Exception as e:
        logger.error(f"Error parsing WhatsApp message: {e}")
        return None

async def process_message(message: WhatsAppMessage) -> str:
    """Process message through the workflow graph and return the final response text."""
    # Get the content of the message
    session_id = message.from_number
    content = message.message_body

    # Ignore images and audio messages for now
    if message.message_type == "audio" or message.message_type == "image":
        return "FPL Gaffer does not have the ability to process audio or images for now"

    # Process the message (text) through FPL Gaffer
    async with AsyncSqliteSaver.from_conn_string(settings.SHORT_TERM_MEMORY_DB_PATH) as short_term_memory:
        graph = graph_builder.compile(checkpointer=short_term_memory)
        await graph.ainvoke(
            {"messages": [HumanMessage(content=content)]},
            {"configurable": {"thread_id": session_id}}
        )

        # Get state output
        output_state = await graph.aget_state(
            config={"configurable": {"thread_id": session_id}}
        )

    return output_state.values["messages"][-1].content

async def send_whatsapp_message(to_number: str , message: str,  type: str = "text") -> bool:
    "Send whatsapp message to user."
    logging.info(f"Attempting to send message to user: {to_number}")
    # ---------- WHATSAPP BUSINESS API ---------- #
    # headers = {
    #     "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    #     "Content-Type": "application/json",
    # }
    #
    # payload = {
    #     "messaging_product": "whatsapp",
    #     "to": to_number,
    #     "type": type,
    #     "text": {"body": message}
    # }
    #
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         f"",
    #         headers=headers,
    #         json=payload
    #     )

    # ---------- TWILIO API ---------- #
    try:
        message = client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            body=message,
            to=f"whatsapp:{to_number}"
        )
        logger.info(f"Message sent to {to_number}: {message.body}")
        return True

    except Exception as e:
        logger.error(f"Error sending message to {to_number}: {e}")

    return False
