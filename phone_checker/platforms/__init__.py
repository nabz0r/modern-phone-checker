"""Package contenant les vérificateurs spécifiques à chaque plateforme.

Chaque module dans ce package implémente la logique de vérification
pour une plateforme spécifique en respectant une interface commune.
"""

from .whatsapp import WhatsAppChecker
from .telegram import TelegramChecker
from .instagram import InstagramChecker
from .snapchat import SnapchatChecker
from .base import BaseChecker

# Mapping des vérificateurs disponibles
AVAILABLE_CHECKERS = {
    'whatsapp': WhatsAppChecker,
    'telegram': TelegramChecker,
    'instagram': InstagramChecker,
    'snapchat': SnapchatChecker,
}

# Liste des plateformes activées par défaut
DEFAULT_PLATFORMS = ['whatsapp', 'telegram', 'instagram', 'snapchat']

# Configuration des plateformes
PLATFORM_INFO = {
    'whatsapp': {
        'name': 'WhatsApp',
        'description': 'Service de messagerie instantanée',
        'reliability': 0.9,
        'supports_username': False
    },
    'telegram': {
        'name': 'Telegram',
        'description': 'Application de messagerie cloud',
        'reliability': 0.85,
        'supports_username': True
    },
    'instagram': {
        'name': 'Instagram',
        'description': 'Réseau social de partage de photos',
        'reliability': 0.75,
        'supports_username': True
    },
    'snapchat': {
        'name': 'Snapchat',
        'description': 'Application de partage de photos éphémères',
        'reliability': 0.7,
        'supports_username': True
    }
}

def get_available_platforms():
    """Retourne la liste des plateformes disponibles avec leurs infos."""
    return {
        platform: {
            **PLATFORM_INFO.get(platform, {}),
            'checker_class': checker_class
        }
        for platform, checker_class in AVAILABLE_CHECKERS.items()
    }

def is_platform_available(platform: str) -> bool:
    """Vérifie si une plateforme est disponible."""
    return platform in AVAILABLE_CHECKERS

__all__ = [
    'AVAILABLE_CHECKERS',
    'DEFAULT_PLATFORMS', 
    'PLATFORM_INFO',
    'BaseChecker',
    'WhatsAppChecker',
    'TelegramChecker',
    'InstagramChecker',
    'SnapchatChecker',
    'get_available_platforms',
    'is_platform_available'
]
