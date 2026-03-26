import os
import json
from google import genai
from apps.gateway.services.tiktak_service import get_products

def call_gemini_fallback(user_query: str, context: dict = None, shop_id: str = None) -> str:
    """
    Calls the Gemini 1.5 API to get a fallback response, equipped with Context and Tiktak Products.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Veuillez m'excuser, je n'ai pas tout à fait compris. Pourriez-vous reformuler votre demande s'il vous plaît ?"
        
    try:
        client = genai.Client(api_key=api_key)
        
        # 1. Obtenir les produits depuis l'API Tiktak
        products_text = "Catalogue temporairement indisponible."
        if shop_id:
            try:
                # Utilise le token de l'API s'il est present dans .env
                api_token = os.getenv("TIKTAK_API_TOKEN") 
                products = get_products(shop_id, api_token=api_token)
                if products:
                    # Gardons uniquement les noms et les prix pour optimiser les tokens Gemini
                    simplified = [{"nom": p["name"], "prix": p["base_price"]} for p in products[:50]]
                    products_text = json.dumps(simplified, ensure_ascii=False)
            except Exception as e:
                products_text = f"(Erreur de récupération catalogue: {e})"

        # 2. Formater le contexte de la conversation
        context_text = json.dumps(context or {}, ensure_ascii=False)

        # 3. Construire un prompt intelligent avec toutes les données
        prompt = f"""
Vous êtes l'assistant IA de la boutique e-commerce. Le système principal n'a pas pu répondre avec certitude au client, vous prenez donc le relais de façon transparente.

[INFORMATIONS BOUTIQUE]
Voici la liste exhaustive de nos produits actuels en stock (Noms et Prix) : 
{products_text}

[CONTEXTE DE LA CONVERSATION]
Voici l'historique et les informations déjà récoltées avec ce client (S'il est vide, c'est le début) : 
{context_text}

[INSTRUCTIONS]
1. Soyez poli, professionnel, empathique et naturel.
2. Si le client demande le prix ou une information sur un produit listé, répondez précisément en utilisant les INFORMATIONS BOUTIQUE.
3. S'il demande un produit qui n'est pas dans la liste, dites courtoisement que ce n'est pas disponible pour le moment, ou proposez autre chose.
4. Répondez dans la même langue que le client (généralement Français ou Dialecte Tunisien).
5. Ne mentionnez JAMAIS que vous êtes une IA de secours ou Gemini.

Question / Message du client : "{user_query}"
"""

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        if response.text:
            return response.text
        return "Veuillez m'excuser, je n'ai pas tout à fait compris. Pourriez-vous reformuler votre demande s'il vous plaît ?"
    except Exception as e:
        # Fallback failure for any reason (network, quota, etc.)
        return "Veuillez m'excuser, je n'ai pas tout à fait compris. Pourriez-vous reformuler votre demande s'il vous plaît ?"
