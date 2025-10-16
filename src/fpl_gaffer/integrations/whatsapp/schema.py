from pydantic import BaseModel


class WhatsAppMessage(BaseModel):
    "Whatsapp message model."
    message_type: str
    from_number: str
    message_body: str
    message_id: str
    # timestamp: str
