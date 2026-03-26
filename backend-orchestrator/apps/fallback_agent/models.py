from django.db import models

class RetrainingBuffer(models.Model):
    user_query = models.TextField()
    original_agent_response = models.TextField()
    confidence_score = models.FloatField()
    gemini_fallback_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'retraining_buffer'

    def __str__(self):
        return f"Fallback on {self.created_at} (Confidence: {self.confidence_score})"
