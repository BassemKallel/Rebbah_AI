# Predefined templates based on the TunBERT intents
TEMPLATES = {
    "GREETING": "Bonjour ! 👋 Bienvenue chez TikTak. Comment puis-je vous aider aujourd'hui ?",
    "ASK_PRICE": "Le {product} est au prix de {price} TND. Souhaitez-vous le commander ?",
    "ASK_AVAILABILITY": "Oui, le {product} est en stock. Nous avons les tailles {sizes} en {colors}.",
    "ORDER_PRODUCT": "Parfait. Pour finaliser votre commande de {product}, j'ai besoin de quelques informations supplémentaires.",
    "ASK_DELIVERY": "La livraison se fait sous 2 à 3 jours ouvrables sur toute la Tunisie et coûte 7 TND.",
    "ASK_DETAILS": "Ce {product} est d'excellente qualité ! Pour plus de détails, pouvez-vous me préciser ce que vous cherchez (taille, matière, origine) ?",
    "ASK_DISCOUNT": "Désolé, nos prix sont fixes, mais nous offrons parfois la livraison pour des commandes multiples !",
    "ASK_LOCATION": "Nous sommes une boutique 100% en ligne pour le moment.",
    "CANCEL_ORDER": "Votre commande a été annulée. N'hésitez pas à revenir vers nous !",
    "CHECK_PACKAGE": "Je vérifie le suivi de votre colis... Il devrait arriver bientôt.",
    "COMPLAINT": "Nous sommes désolés d'apprendre cela. Un conseiller humain va prendre le relais.",
    "CONFIRM_DENY": "D'accord, c'est noté.",
    "INFORM_INFO": "Merci pour l'information. C'est enregistré !",
    "TRACK_ORDER": "Pour suivre votre commande, veuillez me donner votre numéro de téléphone ou le numéro de suivi.",
    "UNKNOWN": "Je n'ai pas tout à fait compris. Pourriez-vous reformuler votre demande ?",
    "NOISE": "Pouvez-vous être plus clair(e) s'il vous plaît ?"
}

# Templates to ask for missing entities
MISSING_ENTITY_TEMPLATES = {
    "product": "Quel article vous intéresse ?",
    "color": "Très bien pour le {product} ! Quelle couleur préférez-vous ?",
    "size": "D'accord pour {product} en {color}. Quelle est votre taille ?",
    "quantity": "Combien de {product} souhaitez-vous commander ?",
    "address": "Dernière étape : quelle est votre adresse de livraison complète ?",
    "phone_number": "Pouvez-vous me donner votre numéro de téléphone pour le livreur ?"
}

# Entities required to complete an ORDER_PRODUCT intent
REQUIRED_ORDER_ENTITIES = ["product", "color", "size", "address", "phone_number"]

# Multiple products found — ask user to pick one
DISAMBIGUATION_TEMPLATE = (
    "J'ai trouvé {count} articles correspondants :\n{list}\n\n"
    "Lequel vous intéresse ? (tapez le numéro ou le nom) Ou envoyez-moi une photo 📸"
)

# Chosen variation is out of stock
OUT_OF_STOCK_TEMPLATE = (
    "Désolé, le {product} en {color} / taille {size} est actuellement en rupture de stock. 😔"
)

# Order confirmed with a reference number from the API
ORDER_CONFIRMED_TEMPLATE = (
    "🎉 Commande confirmée ! Votre {product} est en cours de préparation.\n"
    "📦 Référence commande : #{ref}\n"
    "Le livreur vous contactera dans 2 à 3 jours ouvrables."
)

# Order confirmed but Mock API did not return a reference
ORDER_CONFIRMED_NO_REF_TEMPLATE = (
    "🎉 Commande enregistrée ! Votre {product} est en cours de préparation.\n"
    "Le livreur vous contactera dans 2 à 3 jours ouvrables. 🚚"
)

# Fallback generic product names used if NLU fails to extract the product entity
FALLBACK_PRODUCTS = ["pull", "t-shirt", "veste", "pantalon", "robe"]

