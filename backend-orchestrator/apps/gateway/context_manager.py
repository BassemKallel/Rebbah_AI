"""
ContextManager — Hot memory layer using Redis.

Stores the last N messages of a conversation with intent/entities
for fast access by the pipeline and Gemini fallback prompt.

Schema per user (key: chat_context:{shop_id}:{user_id}, TTL=1h):
[
  {"role": "user", "text": "...", "intent": "ORDER_PRODUCT", "confidence": 0.95,
   "entities": {"product": "pull", "color": "noir"}},
  {"role": "bot", "text": "Quelle taille ?"},
  ...
]

Multi-tenant isolation:
  - LLM pipeline  → passes shop_id → key = chat_context:{shop_id}:{user_id}
  - NLU pipeline  → no shop_id    → key = chat_context:{user_id}  (backward compat)

Meta guarantees distinct sender_ids per Facebook Page so NLU is safe
without isolation. The LLM pipeline explicitly isolates by shop_id.
"""
import json
import os
import redis

# Module-level singleton pool — shared across all ContextManager instances
# and Gunicorn threads. Prevents connection leaks when ContextManager()
# is instantiated multiple times per request lifecycle.
_REDIS_HOST = os.getenv("REDIS_HOST", "redis")
_REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
_pool = redis.ConnectionPool(
    host=_REDIS_HOST, port=_REDIS_PORT, db=0,
    decode_responses=True, max_connections=20
)


class ContextManager:
    def __init__(self):
        self.redis_client = redis.Redis(connection_pool=_pool)
        self.ttl = 3600   # 1 hour
        self.max_history = 10

    # ── Key builder ──────────────────────────────────────────────────────────

    def _get_key(self, user_id: str, shop_id: str = None) -> str:
        """
        Build the Redis key for a user's conversation history.

        Args:
            user_id:  Platform user ID (e.g. Messenger sender_id)
            shop_id:  Optional shop identifier for multi-tenant isolation.
                      When provided → chat_context:{shop_id}:{user_id}
                      When omitted  → chat_context:{user_id}  (NLU backward compat)
        """
        if shop_id:
            return f"chat_context:{shop_id}:{user_id}"
        return f"chat_context:{user_id}"

    # ── Public API ───────────────────────────────────────────────────────────

    def get_context(self, user_id: str, shop_id: str = None) -> list:
        """Retrieve full conversation history for a user."""
        data = self.redis_client.get(self._get_key(user_id, shop_id))
        if data:
            return json.loads(data)
        return []

    def get_recent_context(self, user_id: str, n: int = 5, shop_id: str = None) -> list:
        """Return the last N messages formatted for LLM prompts."""
        context = self.get_context(user_id, shop_id)
        return context[-n:] if context else []

    def add_message(
        self,
        user_id: str,
        role: str,
        text: str,
        intent: str = None,
        confidence: float = None,
        entities: dict = None,
        shop_id: str = None,
    ) -> None:
        """
        Add a message to the user's history.

        Args:
            user_id:    Platform user ID
            role:       "user" or "bot"
            text:       Message text
            intent:     Detected intent (user messages only)
            confidence: Intent confidence score
            entities:   Extracted entities dict (user messages only)
            shop_id:    Optional — for multi-tenant isolation (LLM pipeline)
        """
        context = self.get_context(user_id, shop_id)

        message_data: dict = {"role": role, "text": text}
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
        key = self._get_key(user_id, shop_id)
        self.redis_client.setex(key, self.ttl, json.dumps(context, ensure_ascii=False))

    def clear_context(self, user_id: str, shop_id: str = None) -> None:
        """Clear context when conversation is completed."""
        self.redis_client.delete(self._get_key(user_id, shop_id))
