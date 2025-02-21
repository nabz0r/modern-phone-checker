"""Package contenant les vérificateurs spécifiques à chaque plateforme.

Chaque module dans ce package implémente la logique de vérification
pour une plateforme spécifique.
"""

from .whatsapp import WhatsAppChecker
from .telegram import TelegramChecker
from .instagram import InstagramChecker
from .snapchat import SnapchatChecker

# Mapping des vérificateurs disponibles
AVAILABLE_CHECKERS = {
    'whatsapp': WhatsAppChecker,
    'telegram': TelegramChecker,
    'instagram': InstagramChecker,
    'snapchat': SnapchatChecker,
}

# Liste des plateformes activées par défaut
DEFAULT_PLATFORMS = ['whatsapp', 'telegram', 'instagram', 'snapchat']
