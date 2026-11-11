"""
messenger_service.py — Meta Messenger Send API

Provides:
  - send_message(recipient_psid, text, token)  → sends a reply to Messenger
  - get_sender_name(psid, token)               → fetches sender first+last name from Graph API
"""
import requests
import logging

logger = logging.getLogger(__name__)

GRAPH_SEND_URL = "https://graph.facebook.com/v19.0/me/messages"
GRAPH_USER_URL = "https://graph.facebook.com/v19.0/{psid}"


def send_message(recipient_psid: str, text: str, page_access_token: str) -> bool:
    """
    Sends a text message to a Messenger user via the Meta Send API.

    Args:
        recipient_psid:    The sender's Page-Scoped ID (PSID)
        text:              The message text to send
        page_access_token: Page Access Token from Meta Developer Portal

    Returns:
        True on success, False on failure
    """
    if not page_access_token:
        logger.warning("[MESSENGER] send_message skipped — no page_access_token configured for this company")
        return False

    payload = {
        "recipient": {"id": recipient_psid},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
    }
    try:
        response = requests.post(
            GRAPH_SEND_URL,
            json=payload,
            params={"access_token": page_access_token},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"[MESSENGER] Message sent to PSID={recipient_psid}")
        return True
    except requests.HTTPError as e:
        logger.error(f"[MESSENGER] send_message HTTP error {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[MESSENGER] send_message failed: {e}")
        return False


def send_image(recipient_psid: str, image_url: str, page_access_token: str) -> bool:
    """
    Sends an image attachment to a Messenger user.

    Args:
        recipient_psid:    The sender's Page-Scoped ID
        image_url:         Publicly accessible URL of the image
        page_access_token: Page Access Token

    Returns:
        True on success, False on failure
    """
    if not page_access_token or not image_url:
        return False

    payload = {
        "recipient": {"id": recipient_psid},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url,
                    "is_reusable": True,
                },
            }
        },
        "messaging_type": "RESPONSE",
    }
    try:
        response = requests.post(
            GRAPH_SEND_URL,
            json=payload,
            params={"access_token": page_access_token},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"[MESSENGER] Image sent to PSID={recipient_psid}: {image_url}")
        return True
    except requests.HTTPError as e:
        logger.error(f"[MESSENGER] send_image HTTP error {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[MESSENGER] send_image failed: {e}")
        return False


def send_carousel(recipient_psid: str, elements: list, page_access_token: str) -> bool:
    """
    Sends a generic template (carousel) to a Messenger user.

    Args:
        recipient_psid:    The sender's Page-Scoped ID
        elements:          List of up to 10 generic template elements
        page_access_token: Page Access Token

    Returns:
        True on success, False on failure
    """
    if not page_access_token or not elements:
        return False

    payload = {
        "recipient": {"id": recipient_psid},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements[:10]
                }
            }
        },
        "messaging_type": "RESPONSE",
    }
    
    try:
        response = requests.post(
            GRAPH_SEND_URL,
            json=payload,
            params={"access_token": page_access_token},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"[MESSENGER] Carousel sent to PSID={recipient_psid} with {len(elements)} items")
        return True
    except requests.HTTPError as e:
        logger.error(f"[MESSENGER] send_carousel HTTP error {e.response.status_code}: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[MESSENGER] send_carousel failed: {e}")
        return False


def get_sender_name(psid: str, page_access_token: str) -> str | None:
    """
    Retrieves the sender's first and last name from the Meta Graph API.

    Args:
        psid:              The sender's Page-Scoped ID
        page_access_token: Page Access Token

    Returns:
        Full name as a string, or None if unavailable
    """
    if not page_access_token:
        return None

    try:
        response = requests.get(
            GRAPH_USER_URL.format(psid=psid),
            params={
                "fields": "first_name,last_name",
                "access_token": page_access_token,
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        first = data.get("first_name", "")
        last = data.get("last_name", "")
        full_name = f"{first} {last}".strip()
        logger.info(f"[MESSENGER] Sender name resolved: '{full_name}' for PSID={psid}")
        return full_name or None
    except Exception as e:
        logger.warning(f"[MESSENGER] get_sender_name failed for PSID={psid}: {e}")
        return None
