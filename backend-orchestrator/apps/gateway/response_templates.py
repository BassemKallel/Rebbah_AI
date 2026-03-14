# Predefined templates based on the TunBERT intents
TEMPLATES = {
    "FR": {
        "GREETING": "Bonjour ! 👋 Bienvenue chez {ai_agent_name}. Comment puis-je vous aider aujourd'hui ?",
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
        "GREETING": "مرحباً ! 👋 أهلاً بك في {ai_agent_name}. كيف يمكنني مساعدتك اليوم؟",
        "ASK_PRICE": "سعر الـ {product} هو {price} دينار. هل ترغب في طلبه؟",
        "ASK_AVAILABILITY": "نعم، الـ {product} متوفر. لدينا المقاسات {sizes} بالألوان {colors}.",
        "ORDER_PRODUCT": "ممتاز. لإتمام طلبك لـ {product}، أحتاج إلى بعض المعلومات الإضافية.",
        "ASK_DELIVERY": "يستغرق التوصيل من يومين إلى 3 أيام عمل في جميع أنحاء تونس بتكلفة 7 دنانير.",
        "ASK_DETAILS": "هذا الـ {product} ذو جودة ممتازة! لمزيد من التفاصيل، هل يمكنك تحديد ما تبحث عنه (المقاس، القماش، المصدر)؟",
        "ASK_DISCOUNT": "عذراً، أسعارنا ثابتة، لكننا نقدم أحياناً توصيلاً مجانياً للطلبات الكبيرة!",
        "ASK_LOCATION": "نحن متجر إلكتروني 100% في الوقت الحالي.",
        "CANCEL_ORDER": "تم إلغاء طلبك. لا تتردد في التواصل معنا مرة أخرى!",
        "CHECK_PACKAGE": "أقوم بالتحقق من مسار طردك... من المفترض أن يصل قريباً.",
        "COMPLAINT": "نأسف لسماع ذلك. سيقوم أحد ممثلي خدمة العملاء بمتابعة الأمر معك.",
        "CONFIRM_DENY": "حسناً، عُلم.",
        "INFORM_INFO": "شكراً على المعلومة. تم تسجيلها!",
        "TRACK_ORDER": "لتتبع طلبك، يرجى تزويدي برقم هاتفك أو رقم تتبع الطلب.",
        "UNKNOWN": "لم أفهم قصدك تماماً. هل يمكنك إعادة صياغة طلبك؟",
        "NOISE": "هل يمكنك التوضيح أكثر من فضلك؟"
    },
    "EN": {
         "GREETING": "Hello ! 👋 Welcome to {ai_agent_name}. How can I help you today ?",
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
        "product": "ما هو المنتج الذي يثير اهتمامك؟",
        "color": "اختيار رائع لـ {product}! ما هو اللون الذي تفضله؟",
        "size": "حسناً لـ {product} باللون {color}. ما هو مقاسك؟",
        "quantity": "كم عدد الـ {product} الذي تود طلبه؟",
        "address": "الخطوة الأخيرة: ما هو عنوان التوصيل بالكامل؟",
        "phone_number": "هل يمكنك إعطائي رقم هاتفك للتواصل مع عامل التوصيل؟"
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
    "AR": "لقد وجدت {count} منتجات مطابقة:\n{list}\n\nأي منها يهمك؟ (اكتب الرقم أو الاسم) أو أرسل لي صورة 📸",
    "EN": "I found {count} matching items :\n{list}\n\nWhich one are you interested in? (type the number or name) Or send me a photo 📸"
}

# Chosen variation is out of stock
OUT_OF_STOCK_TEMPLATE = {
    "FR": "Désolé, le {product} en {color} / taille {size} est actuellement en rupture de stock. 😔",
    "AR": "عذراً، الـ {product} باللون {color} / المقاس {size} غير متوفر في المخزون حالياً. 😔",
    "EN": "Sorry, the {product} in {color} / size {size} is currently out of stock. 😔"
}

OUT_OF_STOCK_AVAILABLE = {
    "FR": "\nDisponible en : {avail}",
    "AR": "\nمتوفر في : {avail}",
    "EN": "\nAvailable in : {avail}"
}

OUT_OF_STOCK_SIZES = {
    "FR": "\nTailles disponibles : {avail}",
    "AR": "\nالمقاسات المتوفرة : {avail}",
    "EN": "\nAvailable sizes : {avail}"
}

OUT_OF_STOCK_COLORS = {
    "FR": "\nCouleurs disponibles : {avail}",
    "AR": "\nالألوان المتوفرة : {avail}",
    "EN": "\nAvailable colors : {avail}"
}

MISSING_ENTITY_DEFAULT = {
    "FR": "Pouvez-vous me dire {first_missing} ?",
    "AR": "هل يمكنك إخباري بـ {first_missing}؟",
    "EN": "Can you tell me {first_missing} ?"
}

INFORM_INFO_DEFAULT = {
    "FR": "Et pour la {first_missing} ?",
    "AR": "وماذا عن الـ {first_missing}؟",
    "EN": "And what about the {first_missing} ?"
}

INFORM_PRODUCT_DEFAULT = {
    "FR": "Merci pour ces informations ! Quel article souhaitez-vous commander ?",
    "AR": "شكراً على هذه المعلومات! ما هو المنتج الذي تود طلبه؟",
    "EN": "Thanks for the info ! What item do you want to order ?"
}

ASK_AVAILABILITY_DEFAULT = {
    "FR": "Sur quel article souhaitez-vous vérifier la disponibilité ?",
    "AR": "ما هو المنتج الذي تود التحقق من توفره؟",
    "EN": "Which item do you want to check availability for ?"
}

ASK_PRICE_DEFAULT = {
    "FR": "Sur quel article souhaitez-vous connaître le prix ?",
    "AR": "ما هو المنتج الذي تود معرفة سعره؟",
    "EN": "Which item do you want to know the price of ?"
}

NOISE_DEFAULT = {
    "FR": "Parlez plus clairement s'il vous plaît. ",
    "AR": "يرجى التحدث بوضوح أكثر من فضلك. ",
    "EN": "Please speak more clearly. "
}

STOCK_CHECK_ERROR = {
    "FR": "Désolé, impossible de vérifier le stock pour le moment. Veuillez réessayer.",
    "AR": "عذراً، لا يمكن التحقق من المخزون في الوقت الحالي. يرجى المحاولة مرة أخرى.",
    "EN": "Sorry, unable to check stock at the moment. Please try again."
}

# Order confirmed with a reference number from the API
ORDER_CONFIRMED_TEMPLATE = {
    "FR": "🎉 Commande confirmée ! Votre {product} est en cours de préparation.\n📦 Référence commande : #{ref}\nLe livreur vous contactera dans 2 à 3 jours ouvrables.",
    "AR": "🎉 تم تأكيد الطلب! جارٍ تجهيز الـ {product} الخاص بك.\n📦 رقم مرجع الطلب : #{ref}\nسيتواصل معك عامل التوصيل خلال يومين إلى 3 أيام عمل.",
    "EN": "🎉 Order confirmed ! Your {product} is being prepared.\n📦 Order reference : #{ref}\nThe driver will contact you in 2 to 3 business days."
}

# Order confirmed but Mock API did not return a reference
ORDER_CONFIRMED_NO_REF_TEMPLATE = {
    "FR": "🎉 Commande enregistrée ! Votre {product} est en cours de préparation.\nLe livreur vous contactera dans 2 à 3 jours ouvrables. 🚚",
    "AR": "🎉 تم تسجيل الطلب! جارٍ تجهيز الـ {product} الخاص بك.\nسيتواصل معك عامل التوصيل خلال يومين إلى 3 أيام عمل. 🚚",
    "EN": "🎉 Order registered ! Your {product} is being prepared.\nThe driver will contact you in 2 to 3 business days. 🚚"
}

# Fallback generic product names used if NLU fails to extract the product entity
FALLBACK_PRODUCTS = ["pull", "t-shirt", "veste", "pantalon", "robe"]