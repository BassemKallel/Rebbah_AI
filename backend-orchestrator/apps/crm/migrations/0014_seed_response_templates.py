"""
0014_seed_response_templates.py
Data migration: seeds all default response templates from response_templates.py into DB.
"""
from django.db import migrations


TEMPLATES_DATA = [
    # ── RESPONSE TEMPLATES (15 intents × 3 langs) ─────────────────────────
    # FR
    ("response", "GREETING",       "FR", "Bonjour ! 👋 Bienvenue chez {ai_agent_name}. Comment puis-je vous aider aujourd'hui ?"),
    ("response", "ASK_PRICE",      "FR", "Le {product} est au prix de {price} TND. Souhaitez-vous le commander ?"),
    ("response", "ASK_AVAILABILITY","FR","Oui, le {product} est en stock. Nous avons les tailles {sizes} en {colors}."),
    ("response", "ORDER_PRODUCT",  "FR", "Parfait. Pour finaliser votre commande de {product}, j'ai besoin de quelques informations supplémentaires."),
    ("response", "ASK_DELIVERY",   "FR", "La livraison se fait sous 2 à 3 jours ouvrables sur toute la Tunisie et coûte 7 TND."),
    ("response", "ASK_DETAILS",    "FR", "Ce {product} est d'excellente qualité ! Pour plus de détails, pouvez-vous me préciser ce que vous cherchez (taille, matière, origine) ?"),
    ("response", "ASK_DISCOUNT",   "FR", "Désolé, nos prix sont fixes, mais nous offrons parfois la livraison pour des commandes multiples !"),
    ("response", "ASK_LOCATION",   "FR", "Nous sommes une boutique 100% en ligne pour le moment."),
    ("response", "CANCEL_ORDER",   "FR", "Votre commande a été annulée. N'hésitez pas à revenir vers nous !"),
    ("response", "CHECK_PACKAGE",  "FR", "Je vérifie le suivi de votre colis... Il devrait arriver bientôt."),
    ("response", "COMPLAINT",      "FR", "Nous sommes désolés d'apprendre cela. Un conseiller humain va prendre le relais."),
    ("response", "CONFIRM_DENY",   "FR", "D'accord, c'est noté."),
    ("response", "INFORM_INFO",    "FR", "Merci pour l'information. C'est enregistré !"),
    ("response", "TRACK_ORDER",    "FR", "Pour suivre votre commande, veuillez me donner votre numéro de téléphone ou le numéro de suivi."),
    ("response", "UNKNOWN",        "FR", "Je n'ai pas tout à fait compris. Pourriez-vous reformuler votre demande ?"),
    ("response", "NOISE",          "FR", "Pouvez-vous être plus clair(e) s'il vous plaît ?"),
    # AR
    ("response", "GREETING",       "AR", "مرحباً ! 👋 أهلاً بك في {ai_agent_name}. كيف يمكنني مساعدتك اليوم؟"),
    ("response", "ASK_PRICE",      "AR", "سعر الـ {product} هو {price} دينار. هل ترغب في طلبه؟"),
    ("response", "ASK_AVAILABILITY","AR","نعم، الـ {product} متوفر. لدينا المقاسات {sizes} بالألوان {colors}."),
    ("response", "ORDER_PRODUCT",  "AR", "ممتاز. لإتمام طلبك لـ {product}، أحتاج إلى بعض المعلومات الإضافية."),
    ("response", "ASK_DELIVERY",   "AR", "يستغرق التوصيل من يومين إلى 3 أيام عمل في جميع أنحاء تونس بتكلفة 7 دنانير."),
    ("response", "ASK_DETAILS",    "AR", "هذا الـ {product} ذو جودة ممتازة! لمزيد من التفاصيل، هل يمكنك تحديد ما تبحث عنه (المقاس، القماش، المصدر)؟"),
    ("response", "ASK_DISCOUNT",   "AR", "عذراً، أسعارنا ثابتة، لكننا نقدم أحياناً توصيلاً مجانياً للطلبات الكبيرة!"),
    ("response", "ASK_LOCATION",   "AR", "نحن متجر إلكتروني 100% في الوقت الحالي."),
    ("response", "CANCEL_ORDER",   "AR", "تم إلغاء طلبك. لا تتردد في التواصل معنا مرة أخرى!"),
    ("response", "CHECK_PACKAGE",  "AR", "أقوم بالتحقق من مسار طردك... من المفترض أن يصل قريباً."),
    ("response", "COMPLAINT",      "AR", "نأسف لسماع ذلك. سيقوم أحد ممثلي خدمة العملاء بمتابعة الأمر معك."),
    ("response", "CONFIRM_DENY",   "AR", "حسناً، عُلم."),
    ("response", "INFORM_INFO",    "AR", "شكراً على المعلومة. تم تسجيلها!"),
    ("response", "TRACK_ORDER",    "AR", "لتتبع طلبك، يرجى تزويدي برقم هاتفك أو رقم تتبع الطلب."),
    ("response", "UNKNOWN",        "AR", "لم أفهم قصدك تماماً. هل يمكنك إعادة صياغة طلبك؟"),
    ("response", "NOISE",          "AR", "هل يمكنك التوضيح أكثر من فضلك؟"),
    # EN
    ("response", "GREETING",       "EN", "Hello ! 👋 Welcome to {ai_agent_name}. How can I help you today ?"),
    ("response", "ASK_PRICE",      "EN", "The {product} costs {price} TND. Would you like to order it ?"),
    ("response", "ASK_AVAILABILITY","EN","Yes, the {product} is in stock. We have sizes {sizes} in {colors}."),
    ("response", "ORDER_PRODUCT",  "EN", "Perfect. To process your order for {product}, I'll need a few more details."),
    ("response", "ASK_DELIVERY",   "EN", "Delivery takes 2 to 3 business days all over Tunisia and costs 7 TND."),
    ("response", "ASK_DETAILS",    "EN", "This {product} is of excellent quality! For more details, can you specify what you're looking for (size, material, origin) ?"),
    ("response", "ASK_DISCOUNT",   "EN", "Sorry, our prices are fixed, but we sometimes offer free delivery for multiple orders !"),
    ("response", "ASK_LOCATION",   "EN", "We are a 100% online store for now."),
    ("response", "CANCEL_ORDER",   "EN", "Your order has been canceled. Feel free to reach out again !"),
    ("response", "CHECK_PACKAGE",  "EN", "I'm checking your package tracking... It should arrive soon."),
    ("response", "COMPLAINT",      "EN", "We're sorry to hear that. A human agent will take over."),
    ("response", "CONFIRM_DENY",   "EN", "Alright, noted."),
    ("response", "INFORM_INFO",    "EN", "Thanks for the information. It's saved !"),
    ("response", "TRACK_ORDER",    "EN", "To track your order, please provide your phone number or tracking number."),
    ("response", "UNKNOWN",        "EN", "I didn't quite catch that. Could you rephrase your request ?"),
    ("response", "NOISE",          "EN", "Could you be clearer, please ?"),

    # ── MISSING ENTITY TEMPLATES (6 × 3) ──────────────────────────────────
    ("missing_entity", "product",      "FR", "Quel article vous intéresse ?"),
    ("missing_entity", "color",        "FR", "Très bien pour le {product} ! Quelle couleur préférez-vous ?"),
    ("missing_entity", "size",         "FR", "D'accord pour {product} en {color}. Quelle est votre taille ?"),
    ("missing_entity", "quantity",     "FR", "Combien de {product} souhaitez-vous commander ?"),
    ("missing_entity", "address",      "FR", "Dernière étape : quelle est votre adresse de livraison complète ?"),
    ("missing_entity", "phone_number", "FR", "Pouvez-vous me donner votre numéro de téléphone pour le livreur ?"),
    ("missing_entity", "product",      "AR", "ما هو المنتج الذي يثير اهتمامك؟"),
    ("missing_entity", "color",        "AR", "اختيار رائع لـ {product}! ما هو اللون الذي تفضله؟"),
    ("missing_entity", "size",         "AR", "حسناً لـ {product} باللون {color}. ما هو مقاسك؟"),
    ("missing_entity", "quantity",     "AR", "كم عدد الـ {product} الذي تود طلبه؟"),
    ("missing_entity", "address",      "AR", "الخطوة الأخيرة: ما هو عنوان التوصيل بالكامل؟"),
    ("missing_entity", "phone_number", "AR", "هل يمكنك إعطائي رقم هاتفك للتواصل مع عامل التوصيل؟"),
    ("missing_entity", "product",      "EN", "Which item are you interested in ?"),
    ("missing_entity", "color",        "EN", "Great for the {product} ! What color do you prefer ?"),
    ("missing_entity", "size",         "EN", "Alright for {product} in {color}. What is your size ?"),
    ("missing_entity", "quantity",     "EN", "How many {product} would you like to order ?"),
    ("missing_entity", "address",      "EN", "Last step: what is your full delivery address ?"),
    ("missing_entity", "phone_number", "EN", "Please share your phone number for the delivery driver ?"),

    # ── OUT OF STOCK (3 × 4 variants) ─────────────────────────────────────
    ("out_of_stock", "default",   "FR", "Désolé, le {product} en {color} / taille {size} est actuellement en rupture de stock. 😔"),
    ("out_of_stock", "default",   "AR", "عذراً، الـ {product} باللون {color} / المقاس {size} غير متوفر في المخزون حالياً. 😔"),
    ("out_of_stock", "default",   "EN", "Sorry, the {product} in {color} / size {size} is currently out of stock. 😔"),
    ("out_of_stock", "available", "FR", "\nDisponible en : {avail}"),
    ("out_of_stock", "available", "AR", "\nمتوفر في : {avail}"),
    ("out_of_stock", "available", "EN", "\nAvailable in : {avail}"),
    ("out_of_stock", "sizes",     "FR", "\nTailles disponibles : {avail}"),
    ("out_of_stock", "sizes",     "AR", "\nالمقاسات المتوفرة : {avail}"),
    ("out_of_stock", "sizes",     "EN", "\nAvailable sizes : {avail}"),
    ("out_of_stock", "colors",    "FR", "\nCouleurs disponibles : {avail}"),
    ("out_of_stock", "colors",    "AR", "\nالألوان المتوفرة : {avail}"),
    ("out_of_stock", "colors",    "EN", "\nAvailable colors : {avail}"),

    # ── ORDER CONFIRMED (2 × 3) ────────────────────────────────────────────
    ("order_confirmed", "with_ref", "FR", "🎉 Commande confirmée ! Votre {product} est en cours de préparation.\n📦 Référence commande : #{ref}\nLe livreur vous contactera dans 2 à 3 jours ouvrables."),
    ("order_confirmed", "with_ref", "AR", "🎉 تم تأكيد الطلب! جارٍ تجهيز الـ {product} الخاص بك.\n📦 رقم مرجع الطلب : #{ref}\nسيتواصل معك عامل التوصيل خلال يومين إلى 3 أيام عمل."),
    ("order_confirmed", "with_ref", "EN", "🎉 Order confirmed ! Your {product} is being prepared.\n📦 Order reference : #{ref}\nThe driver will contact you in 2 to 3 business days."),
    ("order_confirmed", "no_ref",   "FR", "🎉 Commande enregistrée ! Votre {product} est en cours de préparation.\nLe livreur vous contactera dans 2 à 3 jours ouvrables. 🚚"),
    ("order_confirmed", "no_ref",   "AR", "🎉 تم تسجيل الطلب! جارٍ تجهيز الـ {product} الخاص بك.\nسيتواصل معك عامل التوصيل خلال يومين إلى 3 أيام عمل. 🚚"),
    ("order_confirmed", "no_ref",   "EN", "🎉 Order registered ! Your {product} is being prepared.\nThe driver will contact you in 2 to 3 business days. 🚚"),

    # ── DISAMBIGUATION (1 × 3) ────────────────────────────────────────────
    ("disambiguation", "default", "FR", "J'ai trouvé {count} articles correspondants :\n{list}\n\nLequel vous intéresse ? (tapez le numéro ou le nom) Ou envoyez-moi une photo 📸"),
    ("disambiguation", "default", "AR", "لقد وجدت {count} منتجات مطابقة:\n{list}\n\nأي منها يهمك؟ (اكتب الرقم أو الاسم) أو أرسل لي صورة 📸"),
    ("disambiguation", "default", "EN", "I found {count} matching items :\n{list}\n\nWhich one are you interested in? (type the number or name) Or send me a photo 📸"),

    # ── MISC DEFAULTS (7 × 3) ────────────────────────────────────────────
    ("misc", "missing_entity_default",  "FR", "Pouvez-vous me dire {first_missing} ?"),
    ("misc", "missing_entity_default",  "AR", "هل يمكنك إخباري بـ {first_missing}؟"),
    ("misc", "missing_entity_default",  "EN", "Can you tell me {first_missing} ?"),
    ("misc", "inform_info_default",     "FR", "Et pour la {first_missing} ?"),
    ("misc", "inform_info_default",     "AR", "وماذا عن الـ {first_missing}؟"),
    ("misc", "inform_info_default",     "EN", "And what about the {first_missing} ?"),
    ("misc", "inform_product_default",  "FR", "Merci pour ces informations ! Quel article souhaitez-vous commander ?"),
    ("misc", "inform_product_default",  "AR", "شكراً على هذه المعلومات! ما هو المنتج الذي تود طلبه؟"),
    ("misc", "inform_product_default",  "EN", "Thanks for the info ! What item do you want to order ?"),
    ("misc", "ask_availability_default","FR", "Sur quel article souhaitez-vous vérifier la disponibilité ?"),
    ("misc", "ask_availability_default","AR", "ما هو المنتج الذي تود التحقق من توفره؟"),
    ("misc", "ask_availability_default","EN", "Which item do you want to check availability for ?"),
    ("misc", "ask_price_default",       "FR", "Sur quel article souhaitez-vous connaître le prix ?"),
    ("misc", "ask_price_default",       "AR", "ما هو المنتج الذي تود معرفة سعره؟"),
    ("misc", "ask_price_default",       "EN", "Which item do you want to know the price of ?"),
    ("misc", "noise_default",           "FR", "Parlez plus clairement s'il vous plaît. "),
    ("misc", "noise_default",           "AR", "يرجى التحدث بوضوح أكثر من فضلك. "),
    ("misc", "noise_default",           "EN", "Please speak more clearly. "),
    ("misc", "stock_check_error",       "FR", "Désolé, impossible de vérifier le stock pour le moment. Veuillez réessayer."),
    ("misc", "stock_check_error",       "AR", "عذراً، لا يمكن التحقق من المخزون في الوقت الحالي. يرجى المحاولة مرة أخرى."),
    ("misc", "stock_check_error",       "EN", "Sorry, unable to check stock at the moment. Please try again."),
]


def seed_templates(apps, schema_editor):
    ResponseTemplate = apps.get_model('crm', 'ResponseTemplate')
    created = 0
    for template_type, intent, language, text in TEMPLATES_DATA:
        _, was_created = ResponseTemplate.objects.get_or_create(
            shop_id=None,
            language=language,
            template_type=template_type,
            intent=intent,
            defaults={'text': text, 'is_default': True}
        )
        if was_created:
            created += 1
    print(f"\n  ✓ Seeded {created} default response templates.")


def unseed_templates(apps, schema_editor):
    ResponseTemplate = apps.get_model('crm', 'ResponseTemplate')
    ResponseTemplate.objects.filter(is_default=True, shop_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0013_responsetemplate'),
    ]

    operations = [
        migrations.RunPython(seed_templates, reverse_code=unseed_templates),
    ]
