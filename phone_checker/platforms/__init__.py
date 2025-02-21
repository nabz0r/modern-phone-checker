"""Package contenant les vérificateurs spécifiques à chaque plateforme.

Chaque module dans ce package implémente la logique de vérification
pour une plateforme spécifique (WhatsApp, Telegram, etc.).
"""

from .whatsapp import WhatsAppChecker
from .telegram import TelegramChecker

# Mapping des vérificateurs disponibles
AVAILABLE_CHECKERS = {
    'whatsapp': WhatsAppChecker,
    'telegram': TelegramChecker,
}
