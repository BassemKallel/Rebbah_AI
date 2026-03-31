"""
Anonymization utilities for NLU processing
Replaces sensitive information (addresses, phone numbers) with tokens
to match TunBERT training data format (__address__, __phone__)

Optimized: regex patterns compiled once at module load, not per-call.
"""
import re
from typing import List

# Tunisian addresses (loaded from geographic data)
TUNISIA_ADDRESSES = [
    # Grand Tunis
    "La Marsa", "Le Kram", "Carthage", "Sidi Bousaid", "Goulette", "Bardo",
    "Medina", "Lafayette", "Montplaisir", "Bab Bhar", "Bab Souika",
    "Menzah 1", "Menzah 2", "Menzah 3", "Menzah 4", "Menzah 5",
    "Menzah 6", "Menzah 7", "Menzah 8", "Menzah 9",
    "Ennasr", "Ennasr 1", "Ennasr 2", "Lac 1", "Lac 2",
    "Jardins de Carthage", "Centre Urbain Nord", "CUN", "Les Berges du Lac",
    "El Mourouj", "Mourouj", "Mourouj 1", "Mourouj 2", "Mourouj 3",
    "Mourouj 4", "Mourouj 5", "Mourouj 6",
    "Cité El Khadra", "El Khadra", "Hay El Khadra", "El Omrane",
    "El Omrane Supérieur", "El Intilaka", "Bab Alioua", "Bab Menara",
    "El Ouardia", "Sijoumi", "Ettahrir", "Sidi Hassine",
    "Cité Olympique", "El Menzah", "El Ghazela",
    "Tunis", "Ariana", "Ben Arous", "Manouba",
    # Cap Bon
    "Nabeul", "Hammamet", "Hammamet Nord", "Hammamet Sud", "Yasmine Hammamet",
    "Korba", "Kelibia", "Grombalia", "Soliman", "Beni Khiar",
    "Menzel Temime", "Dar Chaabane", "Mrezga", "Haouaria", "Tazarka",
    "Zaghouan", "Zriba", "El Fahs", "Bir Mcherga", "Nadhour", "Saouaf",
    # Nord
    "Bizerte", "Bizerte Ville", "Mateur", "Ras Jebel", "Menzel Bourguiba",
    "Ghar El Melh", "Zarzouna", "Sejnane", "Joumine", "Utique",
    "Béja", "Béja Ville", "Medjez el-Bab", "Teboursouk", "Testour", "Nefza",
    "Amdoun", "Goubellat", "Thibar", "Slouguia",
    "Jendouba", "Jendouba Ville", "Tabarka", "Aïn Draham", "Bou Salem",
    "Ghardimaou", "Fernana", "Jendouba Nord",
    "Le Kef", "Le Kef Ville", "Dahmani", "Tajerouine", "Sakiet Sidi Youssef",
    "Kalaat Senan", "Jerissa", "El Ksour", "Touiref",
    "Siliana", "Siliana Ville", "Bou Arada", "Gaâfour", "Makthar", "Bargou",
    "Kesra", "El Aroussa", "Rohia",
    # Centre-Est
    "Sousse", "Sahloul", "Kantaoui", "Msaken", "Akouda", "Hammam Sousse",
    "Kalaa Kebira", "Boujaafar", "Khzema", "Jawhara", "Sousse Medina",
    "Kalaa Sghira", "Enfidha", "Hergla", "Sidi Bou Ali",
    "Monastir", "Monastir Ville", "Skanes", "Jammel", "Moknine", "Sayada",
    "Téboulba", "Ouerdanine", "Ksar Hellal", "Bembla", "Sahline",
    "Bekalta", "Beni Hassen", "Zeramdine",
    "Mahdia", "Mahdia Ville", "Ksour Essef", "Chebba", "El Jem", "Bou Merdes",
    "Mellouleche", "Rejiche", "Sidi Alouane", "Chorbane",
    "Sfax", "Sfax Ville", "Sfax Medina", "Sakiet Ezzit", "Sakiet ed-Daïer",
    "Thyna", "Agareb", "Mahres", "Jebiniana", "Gremda", "Teniour",
    "Markez Chaker", "Markez Sahnoun",
    "Route Mahdia", "Route Tunis", "Route Gabes", "Route Mharza",
    # Centre-Ouest
    "Kairouan", "Kairouan Ville", "Bou Hajla", "Sbikha", "Haffouz", "Oueslatia",
    "Nasrallah", "Chebika", "Hajeb El Ayoun", "El Ala",
    "Kasserine", "Kasserine Ville", "Sbeïtla", "Thala", "Feriana", "Sbiba",
    "Foussana", "Majel Bel Abbes", "Ezzouhour", "Hidra",
    "Sidi Bouzid", "Sidi Bouzid Ville", "Regueb", "Menzel Bouzaiane", "Jilma",
    "Mazzouna", "Bir El Hafey", "Meknassy", "Souk Jedid",
    # Sud-Est
    "Gabès", "Gabès Ville", "Gabès Médina", "Mareth", "Matmata", "El Hamma",
    "Metouia", "Chenini", "Ghannouch", "Nouvelle Matmata", "Ouedhref",
    "Medenine", "Medenine Ville", "Djerba", "Zarzis", "Ben Guerdane", "Houmt Souk",
    "Midoun", "Ajim", "Beni Khedache", "Erriadh", "Aghir",
    "Tataouine", "Tataouine Ville", "Ghomrassen", "Remada", "Bir Lahmar",
    "Dehiba", "Smar", "Tataouine Sud",
    # Sud-Ouest
    "Gafsa", "Gafsa Ville", "Metlaoui", "El Ksar", "Redeyef", "Moularès",
    "Sened", "Mdhilla", "Oum El Araies",
    "Tozeur", "Tozeur Ville", "Nefta", "Degache", "Hazoua", "Tamaghza",
    "El Hamma du Jerid",
    "Kebili", "Kebili Ville", "Douz", "Souk Lahad", "Faouar", "Jemna",
    "El Golaa", "Douz Nord", "Douz Sud",
    # Arabic addresses
    "المرسى", "الكرم", "قرطاج", "سيدي بوسعيد", "حلق الوادي", "باردو",
    "المدينة", "لافاييت", "مونبليزير", "باب البحر", "باب سويقة",
    "المنزه", "النصر", "البحيرة", "حي الخضراء", "العمران",
    "الانطلاقة", "الورادية", "سيدي حسين", "المروج", "سجومي",
    "أريانة", "سكرة", "رواد", "المنيهلة", "سيدي ثابت",
    "الغزالة", "برج الوزير", "النخيلات", "شطرانة", "جعفر",
    "قلعة الأندلس", "دوار هيشر", "التضامن", "مدينة العمال",
]

# ── Compiled patterns (built once at module load) ─────────────────────────────

# Phone patterns
_PHONE_PATTERNS = [
    re.compile(r'\+216\s?[0-9]{8}', re.IGNORECASE),
    re.compile(r'00216\s?[0-9]{8}', re.IGNORECASE),
    re.compile(r'216\s?[0-9]{8}', re.IGNORECASE),
    re.compile(r'(?:^|\s)[0-9]{8}(?:\s|$)', re.IGNORECASE),
]

# Single compiled regex for ALL addresses (sorted longest-first, joined with |)
_SORTED_ADDRESSES = sorted(TUNISIA_ADDRESSES, key=len, reverse=True)
_ADDRESS_PATTERN = re.compile(
    '|'.join(rf'\b{re.escape(addr)}\b' for addr in _SORTED_ADDRESSES),
    flags=re.IGNORECASE,
)


def anonymize_phone_numbers(text: str) -> str:
    """Replace Tunisian phone numbers with __phone__ token"""
    for pattern in _PHONE_PATTERNS:
        text = pattern.sub(' __phone__ ', text)
    return text.strip()


def anonymize_addresses(text: str) -> str:
    """Replace Tunisian addresses with __address__ token (single-pass regex)"""
    return _ADDRESS_PATTERN.sub(' __address__ ', text).strip()


def anonymize_message(text: str) -> str:
    """
    Anonymize a message by replacing sensitive information with tokens.

    Returns:
        Anonymized message with __phone__ and __address__ tokens
    """
    # Order matters: anonymize addresses first, then phone numbers
    text = anonymize_addresses(text)
    text = anonymize_phone_numbers(text)

    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text
