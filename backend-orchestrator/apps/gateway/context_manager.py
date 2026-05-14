"""
ContextManager — Hot memory layer using Redis.

Stores the last N messages of a conversation with intent/entities
for fast access by the pipeline and Gemini fallback prompt.

Schema per user (key: chat_context:{shop_id}:{user_id}, TTL=24h):
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
        self.max_history = 6

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
        """Retrieve full conversation history for a user. Fallbacks to DB on cache miss."""
        key = self._get_key(user_id, shop_id)
        data = self.redis_client.get(key)
        
        if data:
            return json.loads(data)
            
        # ── Cache Miss: Restore from PostgreSQL ───────────────────────────
        if shop_id:
            try:
                from apps.crm.models.conversation import Conversation
                conversation = Conversation.objects.filter(
                    sender_id=user_id,
                    shop_id=shop_id,
                    state__in=["NEW_CONVERSATION", "WAITING_USER_REPLY", "LLM_ACTIVE", "LLM_CONFIRMING"]
                ).order_by('-created_at').first()
                
                if conversation:
                    db_messages = list(conversation.messages.order_by('-created_at')[:self.max_history])
                    db_messages.reverse()  # Chronological order
                    
                    history = [{"role": m.sender.lower(), "text": m.text} for m in db_messages]
                    
                    if history:
                        self.redis_client.setex(key, self.ttl, json.dumps(history))
                        return history
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to restore DB context for {user_id}: {e}")
                
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

    def preload_context(self, user_id: str, known_entities: dict, shop_id: str = None) -> None:
        """
        Pre-load Redis context with known client info for returning customers.

        Inserts a synthetic 'system' message so Gemini sees previously collected
        data (name, phone_number, etc.) without re-asking the client.

        Args:
            user_id:         Platform user ID
            known_entities:  Dict of known info, e.g. {"name": "Ali", "phone_number": "55001122"}
            shop_id:         Shop identifier for multi-tenant isolation
        """
        if not known_entities:
            return

        summary_parts = [f"{k}: {v}" for k, v in known_entities.items()]
        summary_text = f"[Client connu] {', '.join(summary_parts)}"

        context = [{
            "role": "bot",
            "text": summary_text,
        }]

        key = self._get_key(user_id, shop_id)
        self.redis_client.setex(key, self.ttl, json.dumps(context, ensure_ascii=False))

    # ── Circuit Breaker: error counter per client ─────────────────────────────

    def _error_key(self, user_id: str, shop_id: str = None) -> str:
        """Redis key for the per-client Gemini error counter."""
        prefix = f"gemini_errors:{shop_id}" if shop_id else "gemini_errors"
        return f"{prefix}:{user_id}"

    def increment_error_count(self, user_id: str, shop_id: str = None) -> int:
        """
        Increment the Gemini error counter for this client.

        The counter expires automatically after 5 minutes (300s) so that
        a temporary spike doesn't permanently block the client.

        Returns the new counter value.
        """
        key = self._error_key(user_id, shop_id)
        count = self.redis_client.incr(key)
        # Set/reset TTL on every increment so the window slides correctly
        self.redis_client.expire(key, 300)   # 5-minute sliding window
        return int(count)

    def reset_error_count(self, user_id: str, shop_id: str = None) -> None:
        """Delete the error counter (called after successful handoff or Gemini recovery)."""
        self.redis_client.delete(self._error_key(user_id, shop_id))

    def get_error_count(self, user_id: str, shop_id: str = None) -> int:
        """Return the current error count without incrementing."""
        val = self.redis_client.get(self._error_key(user_id, shop_id))
        return int(val) if val else 0
