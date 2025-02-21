"""Utilitaires pour la vérification des numéros de téléphone.

Ce module fournit des fonctions utilitaires pour :
- Valider les numéros de téléphone
- Gérer le rate limiting
- Nettoyer les données
"""

import re
from typing import Optional
from functools import wraps
import asyncio
from datetime import datetime, timedelta

def clean_phone_number(phone: str) -> str:
    """Nettoie un numéro de téléphone en enlevant les caractères non numériques.
    
    Args:
        phone: Numéro de téléphone avec potentiellement des espaces, tirets, etc.
        
    Returns:
        Numéro nettoyé ne contenant que des chiffres
    """
    return re.sub(r'\D', '', phone)

def validate_phone_number(phone: str, country_code: str) -> bool:
    """Vérifie si un numéro de téléphone est valide pour un pays donné.
    
    Args:
        phone: Numéro de téléphone sans l'indicatif pays
        country_code: Indicatif pays (ex: '33' pour la France)
        
    Returns:
        True si le numéro est valide, False sinon
    """
    # Formats par pays (simplifié pour l'exemple)
    country_formats = {
        '33': r'^[67]\d{8}$',  # France: mobile commence par 6 ou 7, suivi de 8 chiffres
        '1': r'^\d{10}$',      # USA/Canada: 10 chiffres
    }
    
    clean_number = clean_phone_number(phone)
    pattern = country_formats.get(country_code)
    
    if not pattern:
        return True  # Si on ne connaît pas le format du pays, on accepte
        
    return bool(re.match(pattern, clean_number))

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
    
    async def acquire(self):
        """Attend si nécessaire pour respecter les limites."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)
        
        # Nettoie les timestamps obsolètes
        self.timestamps = [ts for ts in self.timestamps if ts > cutoff]
        
        if len(self.timestamps) >= self.calls:
            # Attend jusqu'à ce qu'un créneau se libère
            sleep_time = (self.timestamps[0] - cutoff).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
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
