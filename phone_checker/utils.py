"""Utilitaires pour la vérification des numéros de téléphone.

Ce module fournit des fonctions utilitaires pour :
- Valider les numéros de téléphone
- Gérer le rate limiting
- Nettoyer les données
- Formatage et validation
"""

import re
import time
from typing import Optional, Dict, List
from functools import wraps
import asyncio
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

def clean_phone_number(phone: str) -> str:
    """Nettoie un numéro de téléphone en enlevant les caractères non numériques.
    
    Args:
        phone: Numéro de téléphone avec potentiellement des espaces, tirets, etc.
        
    Returns:
        Numéro nettoyé ne contenant que des chiffres
    """
    return re.sub(r'\D', '', phone)

def validate_phone_number(phone: str, country_code: str) -> bool:
    """Valide un numéro de téléphone en utilisant la bibliothèque phonenumbers.
    
    Args:
        phone: Numéro de téléphone sans l'indicatif pays
        country_code: Indicatif pays (ex: '33' pour la France)
        
    Returns:
        True si le numéro est valide, False sinon
    """
    try:
        # Nettoie le numéro
        clean_number = clean_phone_number(phone)
        full_number = f"+{country_code}{clean_number}"
        
        # Parse avec phonenumbers
        parsed = phonenumbers.parse(full_number, None)
        
        # Vérifie la validité
        return phonenumbers.is_valid_number(parsed)
        
    except (NumberParseException, ValueError):
        return False

def format_phone_number(phone: str, country_code: str, format_type: str = 'international') -> Optional[str]:
    """Formate un numéro de téléphone selon le standard demandé.
    
    Args:
        phone: Numéro de téléphone
        country_code: Indicatif pays
        format_type: Type de formatage ('international', 'national', 'e164')
        
    Returns:
        Numéro formaté ou None si invalide
    """
    try:
        clean_number = clean_phone_number(phone)
        full_number = f"+{country_code}{clean_number}"
        parsed = phonenumbers.parse(full_number, None)
        
        if not phonenumbers.is_valid_number(parsed):
            return None
        
        format_map = {
            'international': phonenumbers.PhoneNumberFormat.INTERNATIONAL,
            'national': phonenumbers.PhoneNumberFormat.NATIONAL,
            'e164': phonenumbers.PhoneNumberFormat.E164
        }
        
        format_enum = format_map.get(format_type, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return phonenumbers.format_number(parsed, format_enum)
        
    except (NumberParseException, ValueError):
        return None

def get_country_code_from_number(phone: str) -> Optional[str]:
    """Extrait l'indicatif pays d'un numéro complet.
    
    Args:
        phone: Numéro complet avec indicatif (ex: "+33612345678")
        
    Returns:
        Indicatif pays ou None si impossible à déterminer
    """
    try:
        parsed = phonenumbers.parse(phone, None)
        return str(parsed.country_code)
    except NumberParseException:
        return None

def get_country_name_from_code(country_code: str) -> Optional[str]:
    """Retourne le nom du pays depuis son indicatif.
    
    Args:
        country_code: Indicatif pays (ex: '33')
        
    Returns:
        Nom du pays ou None si non trouvé
    """
    country_names = {
        '33': 'France',
        '1': 'États-Unis/Canada',
        '49': 'Allemagne',
        '44': 'Royaume-Uni',
        '39': 'Italie',
        '34': 'Espagne',
        '32': 'Belgique',
        '41': 'Suisse',
        '31': 'Pays-Bas',
        '46': 'Suède',
        '47': 'Norvège',
        '45': 'Danemark',
        '358': 'Finlande',
        '43': 'Autriche',
        '351': 'Portugal',
        '30': 'Grèce',
        '48': 'Pologne',
        '7': 'Russie',
        '86': 'Chine',
        '81': 'Japon',
        '82': 'Corée du Sud',
        '91': 'Inde',
        '55': 'Brésil',
        '54': 'Argentine',
        '52': 'Mexique',
        '61': 'Australie',
        '64': 'Nouvelle-Zélande',
        '27': 'Afrique du Sud',
        '20': 'Égypte',
        '212': 'Maroc',
        '216': 'Tunisie',
        '213': 'Algérie'
    }
    return country_names.get(country_code)

def is_mobile_number(phone: str, country_code: str) -> bool:
    """Détermine si un numéro est un mobile.
    
    Args:
        phone: Numéro de téléphone
        country_code: Indicatif pays
        
    Returns:
        True si c'est un mobile, False sinon
    """
    try:
        clean_number = clean_phone_number(phone)
        full_number = f"+{country_code}{clean_number}"
        parsed = phonenumbers.parse(full_number, None)
        
        number_type = phonenumbers.number_type(parsed)
        return number_type in (
            phonenumbers.PhoneNumberType.MOBILE,
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE
        )
    except NumberParseException:
        return False

class RateLimiter:
    """Gestionnaire de rate limiting pour les requêtes aux APIs."""
    
    def __init__(self, calls: int, period: int):
        """Initialise le rate limiter.
        
        Args:
            calls: Nombre d'appels autorisés
            period: Période en secondes
        """
        self.calls = calls
        self.period = period
        self.timestamps = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Attend si nécessaire pour respecter les limites."""
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.period)
            
            # Nettoie les timestamps obsolètes
            self.timestamps = [ts for ts in self.timestamps if ts > cutoff]
            
            if len(self.timestamps) >= self.calls:
                # Calcule le temps d'attente
                oldest_timestamp = self.timestamps[0]
                sleep_time = (oldest_timestamp + timedelta(seconds=self.period) - now).total_seconds()
                
                if sleep_time > 0:
                    from .logging import logger
                    logger.log_rate_limit("rate_limiter", sleep_time)
                    await asyncio.sleep(sleep_time)
                
                # Retire le plus ancien timestamp
                self.timestamps.pop(0)
            
            self.timestamps.append(now)

def rate_limit(calls: int, period: int):
    """Décorateur pour appliquer le rate limiting à une méthode asynchrone.
    
    Args:
        calls: Nombre d'appels autorisés
        period: Période en secondes
    """
    limiter = RateLimiter(calls, period)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def anonymize_phone_number(phone: str, country_code: str) -> str:
    """Anonymise un numéro pour les logs en gardant les premiers et derniers chiffres.
    
    Args:
        phone: Numéro de téléphone
        country_code: Indicatif pays
        
    Returns:
        Numéro anonymisé (ex: "+33 6XX XX XX 78")
    """
    try:
        formatted = format_phone_number(phone, country_code, 'international')
        if not formatted:
            return f"+{country_code}XXXXXXXX"
        
        # Remplace les chiffres du milieu par des X
        if len(formatted) > 8:
            # Garde les 4 premiers et 2 derniers caractères visibles
            start = formatted[:6]
            end = formatted[-2:]
            middle = 'X' * (len(formatted) - 8)
            return f"{start}{middle}{end}"
        
        return formatted
    except:
        return f"+{country_code}XXXXXXXX"

def calculate_confidence_score(
    status_code: int,
    response_time: float,
    platform_reliability: float = 0.8
) -> float:
    """Calcule un score de confiance basé sur plusieurs facteurs.
    
    Args:
        status_code: Code de statut HTTP
        response_time: Temps de réponse en secondes
        platform_reliability: Fiabilité de la plateforme (0.0 à 1.0)
        
    Returns:
        Score de confiance entre 0.0 et 1.0
    """
    # Score basé sur le status code
    if status_code == 200:
        status_score = 1.0
    elif status_code in (201, 202, 203):
        status_score = 0.9
    elif status_code in (429, 503):  # Rate limiting
        status_score = 0.3
    elif status_code in (404, 400):
        status_score = 0.7
    else:
        status_score = 0.5
    
    # Score basé sur le temps de réponse
    if response_time < 1.0:
        time_score = 1.0
    elif response_time < 3.0:
        time_score = 0.8
    elif response_time < 5.0:
        time_score = 0.6
    else:
        time_score = 0.3
    
    # Score final pondéré
    final_score = (
        status_score * 0.4 +
        time_score * 0.3 +
        platform_reliability * 0.3
    )
    
    return round(final_score, 2)

def generate_user_agent() -> str:
    """Génère un User-Agent réaliste pour les requêtes HTTP."""
    user_agents = [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0 Firefox/88.0',
        'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
    ]
    import random
    return random.choice(user_agents)

def parse_response_error(response_text: str, status_code: int) -> str:
    """Parse une réponse d'erreur pour extraire un message utile.
    
    Args:
        response_text: Texte de la réponse
        status_code: Code de statut HTTP
        
    Returns:
        Message d'erreur parsé
    """
    error_messages = {
        400: "Requête invalide",
        401: "Non autorisé",
        403: "Accès interdit",
        404: "Ressource non trouvée",
        429: "Trop de requêtes",
        500: "Erreur serveur interne",
        502: "Mauvaise gateway",
        503: "Service indisponible",
        504: "Timeout gateway"
    }
    
    default_message = error_messages.get(status_code, f"Erreur HTTP {status_code}")
    
    # Essaie d'extraire des infos de la réponse
    if response_text:
        # Recherche des patterns d'erreur courants
        import json
        try:
            data = json.loads(response_text)
            if isinstance(data, dict):
                error = data.get('error') or data.get('message') or data.get('detail')
                if error:
                    return str(error)
        except:
            pass
    
    return default_message
