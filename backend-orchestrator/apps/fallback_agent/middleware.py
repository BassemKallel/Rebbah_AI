import json
import os
from django.utils.deprecation import MiddlewareMixin
from apps.fallback_agent.models import RetrainingBuffer
from apps.fallback_agent.services import call_gemini_fallback

class AIFallbackMiddleware(MiddlewareMixin):
    """
    Middleware that monitors outgoing AI agent responses.
    If the confidence_score < 0.7 for 3 times in a session,
    it intercepts the message, routes to Gemini API, and saves to RetrainingBuffer.
    """
    def process_request(self, request):
        # Force evaluation of request.body before DRF consumes the stream,
        # caching it in request._body to prevent RawPostDataException later.
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                _ = request.body
            except Exception:
                pass

    def process_response(self, request, response):
        # We only care about JSON responses that might contain agent replies
        if not response.get('Content-Type', '').startswith('application/json'):
            return response

        # Ensure we have a valid session to track state
        if not hasattr(request, 'session') or not request.session.session_key:
            try:
                if hasattr(request, 'session'):
                    request.session.save()
            except Exception:
                pass

        try:
            data = json.loads(response.content.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            return response

        # Handle the MessengerWebhookPOC format
        is_poc_format = isinstance(data, dict) and 'bot_response' in data and 'internal_debug' in data['bot_response']
        # Handle the older/direct specific agent format if any
        is_legacy_format = isinstance(data, dict) and 'confidence_score' in data and 'agent_response' in data

        if is_poc_format or is_legacy_format:
            if is_poc_format:
                debug_info = data['bot_response']['internal_debug']
                confidence_score = debug_info.get('confidence_score')
                context = debug_info.get('accumulated_context', {})
                original_response = data['bot_response'].get('text', '')
                # Revenir à la source fiable : l'info debug passée par la vue
                user_from_debug = debug_info.get('user_query')
            else:
                confidence_score = data.get('confidence_score')
                context = data.get('context', {})
                original_response = data.get('agent_response', '')
                user_from_debug = data.get('user_query')
            
            # Treat missing or null confidence (e.g., when intent is UNKNOWN) as 0.0
            if confidence_score is None:
                confidence_score = 0.0
            
            if isinstance(confidence_score, (int, float)) and confidence_score < 0.7:
                # Increment the low confidence counter in the user's session
                if hasattr(request, 'session'):
                    low_conf_count = request.session.get('low_confidence_counter', 0)
                    low_conf_count += 1
                    request.session['low_confidence_counter'] = low_conf_count

                    if low_conf_count >= 3:
                        # Attempt to extract the original user query from the request
                        user_query = user_from_debug or "Requête inconnue"
                        shop_id = os.getenv('COMPANY_SLUG')
                        
                        # Fallback parsing if not in debug (Legacy/Backup)
                        if not user_from_debug:
                            body = getattr(request, '_body', None) or (request.body if hasattr(request, 'body') else None)
                            if request.method in ['POST', 'PUT', 'PATCH'] and body:
                                try:
                                    req_data = json.loads(body.decode('utf-8'))
                                    msg_data = req_data.get('message', {})
                                    if isinstance(msg_data, dict):
                                        user_query = msg_data.get('text', req_data.get('text', user_query))
                                    elif isinstance(msg_data, str):
                                        user_query = msg_data
                                    else:
                                        user_query = req_data.get('text', user_query)
                                    shop_id = req_data.get('shop_id', shop_id)
                                except (json.JSONDecodeError, UnicodeDecodeError):
                                    pass

                        # Trigger the Gemini fallback logic
                        gemini_response = call_gemini_fallback(user_query, context=context, shop_id=shop_id)

                        # Save the interaction to the PostgreSQL `retraining_buffer` table
                        RetrainingBuffer.objects.create(
                            user_query=user_query,
                            original_agent_response=original_response,
                            confidence_score=confidence_score,
                            gemini_fallback_response=gemini_response
                        )

                        # Update the JSON response content to output the Gemini fallback
                        if is_poc_format:
                            data['bot_response']['text'] = gemini_response
                            data['bot_response']['fallback_triggered'] = True
                            data['bot_response']['internal_debug']['confidence_score'] = 1.0
                        else:
                            data['agent_response'] = gemini_response
                            data['fallback_triggered'] = True
                            data['confidence_score'] = 1.0  # High confidence from fallback
                        
                        # Reset the counter
                        request.session['low_confidence_counter'] = 0

                        # Serialize and update response
                        response.content = json.dumps(data).encode('utf-8')
                        if 'Content-Length' in response:
                            response['Content-Length'] = str(len(response.content))
                    
        return response
