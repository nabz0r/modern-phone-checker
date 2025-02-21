"""Modèles de données pour le Phone Checker.

Ce module définit les structures de données principales utilisées dans l'application.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class PhoneCheckResult:
    """Résultat de la vérification d'un numéro sur une plateforme spécifique.
    
    Attributes:
        platform: Nom de la plateforme vérifiée (ex: 'whatsapp', 'telegram')
        exists: True si le numéro existe sur la plateforme
        error: Message d'erreur si la vérification a échoué
        username: Nom d'utilisateur associé si disponible
        last_seen: Dernière activité si disponible
        metadata: Données supplémentaires spécifiques à la plateforme
        timestamp: Date et heure de la vérification
    """
    platform: str
    exists: bool
    error: Optional[str] = None
    username: Optional[str] = None
    last_seen: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialise le timestamp s'il n'est pas fourni."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
