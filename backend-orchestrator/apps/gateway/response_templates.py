# Predefined templates based on the TunBERT intents
TEMPLATES = {
    "FR": {
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
    },
    "AR": {
        "GREETING": "Aslama ! 👋 Marhbe bik fi TikTak. Kifech najam n3awnek lyoum ?",
        "ASK_PRICE": "El {product} b {price} TND. T7eb t3adi commande ?",
        "ASK_AVAILABILITY": "Ey, el {product} dispo. 3anna mennou tailettes {sizes} w fi les couleurs {colors}.",
        "ORDER_PRODUCT": "Bahi. bech nkamal el commande mte3ek l {product}, n7taj chwaya ma3loumet mnek.",
       "ASK_DELIVERY": "El livraison to93ed entre 2 w 3 jours sur toute la Tunisie w b 7 TND.",
        "ASK_DETAILS": "El {product} hetha tayara ! a3tini akthar details chnowa tfarekes (taille, matière, origine) ?",
        "ASK_DISCOUNT": "Samahni l'aswem fixe, ama sa3at na3mlou livraison gratuite l commandes kbar !",
        "ASK_LOCATION": "A7na boutique 100% en ligne l tawa.",
        "CANCEL_ORDER": "Commande mte3ek t'annulet. Marhbe bik wa9t ma t7eb !",
        "CHECK_PACKAGE": "Nchouflek m3a el livreur... taw youslek an 9arib.",
        "COMPLAINT": "Samahna 3ala hetha. Taw njiblek conseiller humain ychouf m3ak.",
        "CONFIRM_DENY": "Bahi, mriguel.",
        "INFORM_INFO": "Aychak 3al ma3louma. 9ayedneha !",
        "TRACK_ORDER": "Bech ntab3ou l commande mte3ek, a3tini num téléphounek wala numéro l commande.",
         "UNKNOWN": "Mafhemtekch mli7. tnajam t3awed t9olli chneya t7eb ?",
         "NOISE": "Tnajam twatha7li akthar y3aychek ?"
    },
    "EN": {
         "GREETING": "Hello ! 👋 Welcome to TikTak. How can I help you today ?",
         "ASK_PRICE": "The {product} costs {price} TND. Would you like to order it ?",
         "ASK_AVAILABILITY": "Yes, the {product} is in stock. We have sizes {sizes} in {colors}.",
         "ORDER_PRODUCT": "Perfect. To process your order for {product}, I'll need a few more details.",
         "ASK_DELIVERY": "Delivery takes 2 to 3 business days all over Tunisia and costs 7 TND.",
         "ASK_DETAILS": "This {product} is of excellent quality! For more details, can you specify what you're looking for (size, material, origin) ?",
         "ASK_DISCOUNT": "Sorry, our prices are fixed, but we sometimes offer free delivery for multiple orders !",
         "ASK_LOCATION": "We are a 100% online store for now.",
         "CANCEL_ORDER": "Your order has been canceled. Feel free to reach out again !",
         "CHECK_PACKAGE": "I'm checking your package tracking... It should arrive soon.",
         "COMPLAINT": "We're sorry to hear that. A human agent will take over.",
         "CONFIRM_DENY": "Alright, noted.",
         "INFORM_INFO": "Thanks for the information. It's saved !",
         "TRACK_ORDER": "To track your order, please provide your phone number or tracking number.",
         "UNKNOWN": "I didn't quite catch that. Could you rephrase your request ?",
         "NOISE": "Could you be clearer, please ?"
    }
}

# Templates to ask for missing entities
MISSING_ENTITY_TEMPLATES = {
    "FR": {
        "product": "Quel article vous intéresse ?",
        "color": "Très bien pour le {product} ! Quelle couleur préférez-vous ?",
        "size": "D'accord pour {product} en {color}. Quelle est votre taille ?",
        "quantity": "Combien de {product} souhaitez-vous commander ?",
        "address": "Dernière étape : quelle est votre adresse de livraison complète ?",
        "phone_number": "Pouvez-vous me donner votre numéro de téléphone pour le livreur ?"
    },
    "AR": {
        "product": "Ana article ya3jbek ?",
        "color": "Bahi pour el {product} ! Ana couleur t7eb ?",
        "size": "Mriguel pour {product} b {color}. chnowa taille mte3ek ?",
        "quantity": "Kadeh men {product} t7eb t3adi commande ?",
        "address": "Ekhir etape: a3tini l'adresse mte3ek kema lzem ?",
        "phone_number": "A3tini num téléphounek bech nkalmek el livreur ?"
    },
    "EN": {
         "product": "Which item are you interested in ?",
         "color": "Great for the {product} ! What color do you prefer ?",
         "size": "Alright for {product} in {color}. What is your size ?",
         "quantity": "How many {product} would you like to order ?",
         "address": "Last step: what is your full delivery address ?",
         "phone_number": "Please share your phone number for the delivery driver ?"
    }
}

# Entities required to complete an ORDER_PRODUCT intent
REQUIRED_ORDER_ENTITIES = ["product", "color", "size", "address", "phone_number"]

# Multiple products found — ask user to pick one
DISAMBIGUATION_TEMPLATE = {
    "FR": "J'ai trouvé {count} articles correspondants :\n{list}\n\nLequel vous intéresse ? (tapez le numéro ou le nom) Ou envoyez-moi une photo 📸",
    "AR": "L9it {count} article ychabhou l li tlawj 3lih :\n{list}\n\nAma hiya li t7eb 3liha ? (ekteb numéro wala l'esm) Wala ab3athli tswira 📸",
    "EN": "I found {count} matching items :\n{list}\n\nWhich one are you interested in? (type the number or name) Or send me a photo 📸"
}

# Chosen variation is out of stock
OUT_OF_STOCK_TEMPLATE = {
    "FR": "Désolé, le {product} en {color} / taille {size} est actuellement en rupture de stock. 😔",
    "AR": "Samahni, el {product} en {color} / taille {size} m3adech fih stock tawa. 😔",
    "EN": "Sorry, the {product} in {color} / size {size} is currently out of stock. 😔"
}

OUT_OF_STOCK_AVAILABLE = {
    "FR": "\nDisponible en : {avail}",
    "AR": "\nDispo fi : {avail}",
    "EN": "\nAvailable in : {avail}"
}

OUT_OF_STOCK_SIZES = {
    "FR": "\nTailles disponibles : {avail}",
    "AR": "\nTaillouet li fihom stock : {avail}",
    "EN": "\nAvailable sizes : {avail}"
}

OUT_OF_STOCK_COLORS = {
    "FR": "\nCouleurs disponibles : {avail}",
    "AR": "\nCouleurat li fihom stock : {avail}",
    "EN": "\nAvailable colors : {avail}"
}

MISSING_ENTITY_DEFAULT = {
    "FR": "Pouvez-vous me dire {first_missing} ?",
    "AR": "Tnajam t9olli {first_missing} ?",
    "EN": "Can you tell me {first_missing} ?"
}

INFORM_INFO_DEFAULT = {
    "FR": "Et pour la {first_missing} ?",
    "AR": "W ba9i {first_missing} ?",
    "EN": "And what about the {first_missing} ?"
}

INFORM_PRODUCT_DEFAULT = {
    "FR": "Merci pour ces informations ! Quel article souhaitez-vous commander ?",
    "AR": "Aychak 3al ma3loumet ! Ana article t7eb t3adi 3lih commande ?",
    "EN": "Thanks for the info ! What item do you want to order ?"
}

ASK_AVAILABILITY_DEFAULT = {
    "FR": "Sur quel article souhaitez-vous vérifier la disponibilité ?",
    "AR": "Ana article t7eb tchouf ken dispo ?",
    "EN": "Which item do you want to check availability for ?"
}

ASK_PRICE_DEFAULT = {
    "FR": "Sur quel article souhaitez-vous connaître le prix ?",
    "AR": "Ana article t7eb taaref soumou ?",
    "EN": "Which item do you want to know the price of ?"
}

NOISE_DEFAULT = {
    "FR": "Parlez plus clairement s'il vous plaît. ",
    "AR": "Watha7li klemek y3aychek. ",
    "EN": "Please speak more clearly. "
}

STOCK_CHECK_ERROR = {
    "FR": "Désolé, impossible de vérifier le stock pour le moment. Veuillez réessayer.",
    "AR": "Samahni, mnjmch nchouf stock tawa. 3awed jarab s'il vous plaît.",
    "EN": "Sorry, unable to check stock at the moment. Please try again."
}

# Order confirmed with a reference number from the API
ORDER_CONFIRMED_TEMPLATE = {
    "FR": "🎉 Commande confirmée ! Votre {product} est en cours de préparation.\n📦 Référence commande : #{ref}\nLe livreur vous contactera dans 2 à 3 jours ouvrables.",
    "AR": "🎉 Commande t3adet ! el {product} mte3ek 9a3din n7athrou fiha.\n📦 Référence commande : #{ref}\nLivreur bch ykalmek fi 2 wela 3 ayam.",
    "EN": "🎉 Order confirmed ! Your {product} is being prepared.\n📦 Order reference : #{ref}\nThe driver will contact you in 2 to 3 business days."
}

# Order confirmed but Mock API did not return a reference
ORDER_CONFIRMED_NO_REF_TEMPLATE = {
    "FR": "🎉 Commande enregistrée ! Votre {product} est en cours de préparation.\nLe livreur vous contactera dans 2 à 3 jours ouvrables. 🚚",
    "AR": "🎉 Commande 9ayedneha ! el {product} mte3ek 9a3din n7athrou fiha.\nLivreur bch ykalmek fi 2 wela 3 ayam. 🚚",
    "EN": "🎉 Order registered ! Your {product} is being prepared.\nThe driver will contact you in 2 to 3 business days. 🚚"
}

# Fallback generic product names used if NLU fails to extract the product entity
FALLBACK_PRODUCTS = ["pull", "t-shirt", "veste", "pantalon", "robe"]


