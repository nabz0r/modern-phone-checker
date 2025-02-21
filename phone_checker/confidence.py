"""Système de score de confiance pour les vérifications.

Ce module implémente un système sophistiqué de scoring qui prend en compte
plusieurs facteurs pour évaluer la fiabilité d'une vérification.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class PlatformReliability:
    """Configuration de fiabilité pour une plateforme.
    
    Attributes:
        base_score: Score de base pour la plateforme (0.0 à 1.0)
        api_timeouts: Nombre de timeouts récents
        success_rate: Taux de succès des dernières vérifications
        last_failure: Timestamp du dernier échec
    """
    base_score: float = 0.8  # Score par défaut
    api_timeouts: int = 0
    success_rate: float = 1.0
    last_failure: Optional[datetime] = None

class ConfidenceScorer:
    """Calculateur de scores de confiance pour les vérifications."""
    
    def __init__(self):
        # Scores de base par plateforme basés sur la fiabilité historique
        self.platform_scores = {
            'whatsapp': PlatformReliability(base_score=0.9),   # Très fiable
            'telegram': PlatformReliability(base_score=0.85),  # Fiable
            'instagram': PlatformReliability(base_score=0.75), # Modérément fiable
            'snapchat': PlatformReliability(base_score=0.7)    # Moins fiable
        }
        
        # Facteurs de pondération pour différents aspects
        self.weights = {
            'platform_reliability': 0.4,  # Fiabilité historique de la plateforme
            'api_response': 0.3,         # Qualité de la réponse API
            'cache_age': 0.3,           # Fraîcheur des données en cache
        }
    
    def calculate_api_response_score(self, status_code: int, response_time: float) -> float:
        """Calcule un score basé sur la qualité de la réponse API.
        
        Args:
            status_code: Code HTTP de la réponse
            response_time: Temps de réponse en secondes
            
        Returns:
            Score entre 0.0 et 1.0
        """
        # Score basé sur le status code
        if status_code == 200:
            status_score = 1.0
        elif status_code in (201, 202, 203):
            status_score = 0.9
        elif status_code in (429, 503):  # Rate limiting ou service indisponible
            status_score = 0.3
        else:
            status_score = 0.5
            
        # Score basé sur le temps de réponse (1.0 si <0.5s, 0.0 si >5s)
        time_score = max(0.0, min(1.0, (5.0 - response_time) / 4.5))
        
        return (status_score * 0.7) + (time_score * 0.3)
    
    def calculate_cache_age_score(self, timestamp: datetime) -> float:
        """Calcule un score basé sur l'âge des données en cache.
        
        Args:
            timestamp: Date de la dernière vérification
            
        Returns:
            Score entre 0.0 et 1.0 (1.0 = très récent, 0.0 = très ancien)
        """
        age = (datetime.now() - timestamp).total_seconds()
        
        # Score dégressif sur 24 heures
        max_age = 24 * 3600  # 24 heures en secondes
        return max(0.0, 1.0 - (age / max_age))
    
    def update_platform_reliability(
        self,
        platform: str,
        success: bool,
        response_time: Optional[float] = None
    ):
        """Met à jour les statistiques de fiabilité d'une plateforme.
        
        Args:
            platform: Nom de la plateforme
            success: Si la vérification a réussi
            response_time: Temps de réponse (optionnel)
        """
        if platform not in self.platform_scores:
            return
            
        reliability = self.platform_scores[platform]
        
        # Met à jour le taux de succès (moyenne mobile sur les 100 dernières)
        alpha = 0.01  # Facteur de lissage
        reliability.success_rate = (
            reliability.success_rate * (1 - alpha) +
            (1.0 if success else 0.0) * alpha
        )
        
        if not success:
            reliability.last_failure = datetime.now()
            if response_time and response_time > 5.0:
                reliability.api_timeouts += 1
    
    def get_confidence_score(
        self,
        platform: str,
        status_code: int,
        response_time: float,
        cache_timestamp: Optional[datetime] = None
    ) -> float:
        """Calcule le score de confiance global pour une vérification.
        
        Args:
            platform: Nom de la plateforme
            status_code: Code HTTP de la réponse
            response_time: Temps de réponse en secondes
            cache_timestamp: Date de mise en cache (si applicable)
            
        Returns:
            Score de confiance entre 0.0 et 1.0
        """
        # Score de fiabilité de la plateforme
        reliability = self.platform_scores.get(
            platform,
            PlatformReliability()  # Valeurs par défaut pour plateformes inconnues
        )
        platform_score = (
            reliability.base_score *
            reliability.success_rate *
            (0.9 ** reliability.api_timeouts)  # Pénalité pour les timeouts
        )
        
        # Score de la réponse API
        api_score = self.calculate_api_response_score(status_code, response_time)
        
        # Score de fraîcheur du cache
        cache_score = (
            self.calculate_cache_age_score(cache_timestamp)
            if cache_timestamp
            else 1.0  # Données fraîches si pas de cache
        )
        
        # Score pondéré final
        final_score = (
            platform_score * self.weights['platform_reliability'] +
            api_score * self.weights['api_response'] +
            cache_score * self.weights['cache_age']
        )
        
        return round(final_score, 2)  # Arrondi à 2 décimales
