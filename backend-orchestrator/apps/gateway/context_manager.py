import json
import redis
import os

class ContextManager:
    """
    Manages short-term conversation context (Hot Memory) using Redis.
    This allows the Orchestrator to "remember" the last few messages of a user.
    """
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
        self.ttl = 3600  # Context expires after 1 hour of inactivity
        self.max_history = 10  # Remember the last 10 messages

    def _get_key(self, user_id):
        return f"chat_context:{user_id}"

    def get_context(self, user_id):
        """Retrieve the conversation history for a user."""
        key = self._get_key(user_id)
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return []

    def add_message(self, user_id, role, text, intent=None, entities=None):
        """
        Add a message to the user's history context.
        role: "user" or "bot"
        """
        context = self.get_context(user_id)
        
        message_data = {
            "role": role,
            "text": text
        }
        
        if intent:
            message_data["intent"] = intent
        if entities:
            message_data["entities"] = entities
            
        context.append(message_data)
        
        # Keep only the last N messages to prevent context overflow
        if len(context) > self.max_history:
            context = context[-self.max_history:]
            
        # Save back to Redis and reset expiry timer
        key = self._get_key(user_id)
        self.redis_client.setex(key, self.ttl, json.dumps(context))

    def clear_context(self, user_id):
        """Clear the context for a specific user (e.g., when conversation is completed)"""
        key = self._get_key(user_id)
        self.redis_client.delete(key)
