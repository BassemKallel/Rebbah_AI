"""
ContextManager — Hot memory layer using Redis.

Stores the last N messages of a conversation with intent/entities
for fast access by the pipeline and Gemini fallback prompt.

Schema per user (key: chat_context:{user_id}, TTL=1h):
[
  {"role": "user", "text": "...", "intent": "ORDER_PRODUCT", "confidence": 0.95,
   "entities": {"product": "pull", "color": "noir"}},
  {"role": "bot", "text": "Quelle taille ?"},
  ...
]
"""
import json
import os
import redis


class ContextManager:
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
        self.ttl = 3600   # 1 hour
        self.max_history = 10

    def _get_key(self, user_id):
        return f"chat_context:{user_id}"

    def get_context(self, user_id):
        """Retrieve full conversation history for a user."""
        key = self._get_key(user_id)
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return []

    def get_recent_context(self, user_id, n=5):
        """Return the last N messages formatted for LLM prompts."""
        context = self.get_context(user_id)
        return context[-n:] if context else []

    def add_message(self, user_id, role, text, intent=None, confidence=None, entities=None):
        """
        Add a message to the user's history.

        Args:
            user_id: Platform user ID
            role:    "user" or "bot"
            text:    Message text
            intent:  Detected intent (user messages only)
            confidence: Intent confidence score
            entities: Extracted entities dict (user messages only)
        """
        context = self.get_context(user_id)

        message_data = {
            "role": role,
            "text": text,
        }

        if intent:
            message_data["intent"] = intent
        if confidence is not None:
            message_data["confidence"] = round(confidence, 3)
        if entities:
            message_data["entities"] = entities

        context.append(message_data)

        # Keep only the last N messages
        if len(context) > self.max_history:
            context = context[-self.max_history:]

        # Save back to Redis and reset expiry
        key = self._get_key(user_id)
        self.redis_client.setex(key, self.ttl, json.dumps(context, ensure_ascii=False))

    def clear_context(self, user_id):
        """Clear context when conversation is completed."""
        key = self._get_key(user_id)
        self.redis_client.delete(key)
