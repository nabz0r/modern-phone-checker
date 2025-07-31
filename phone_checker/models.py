"""Modèles de données pour le Phone Checker.

Ce module définit les structures de données principales utilisées dans l'application.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class VerificationStatus(Enum):
    """Statut de vérification d'un numéro."""
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"

@dataclass
class PhoneCheckResult:
    """Résultat de la vérification d'un numéro sur une plateforme spécifique.
    
    Attributes:
        platform: Nom de la plateforme vérifiée (ex: 'whatsapp', 'telegram')
        status: Statut de la vérification
        exists: True si le numéro existe sur la plateforme
        error: Message d'erreur si la vérification a échoué
        username: Nom d'utilisateur associé si disponible
        last_seen: Dernière activité si disponible
        confidence_score: Score de confiance de 0.0 à 1.0
        metadata: Données supplémentaires spécifiques à la plateforme
        timestamp: Date et heure de la vérification
        response_time: Temps de réponse en millisecondes
    """
    platform: str
    status: VerificationStatus
    exists: bool = False
    error: Optional[str] = None
    username: Optional[str] = None
    last_seen: Optional[datetime] = None
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_time: float = 0.0
    
    def __post_init__(self):
        """Initialise les valeurs dérivées après création."""
        # Assure la cohérence entre status et exists
        if self.status == VerificationStatus.EXISTS:
            self.exists = True
        elif self.status == VerificationStatus.NOT_EXISTS:
            self.exists = False
        elif self.status in [VerificationStatus.ERROR, VerificationStatus.TIMEOUT]:
            self.exists = False
    
    @property
    def is_successful(self) -> bool:
        """Retourne True si la vérification s'est déroulée sans erreur."""
        return self.status in [VerificationStatus.EXISTS, VerificationStatus.NOT_EXISTS]
    
    @property
    def is_cached(self) -> bool:
        """Retourne True si le résultat provient du cache."""
        return self.metadata.get('cached', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            'platform': self.platform,
            'status': self.status.value,
            'exists': self.exists,
            'error': self.error,
            'username': self.username,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'confidence_score': self.confidence_score,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'response_time': self.response_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PhoneCheckResult':
        """Crée un PhoneCheckResult depuis un dictionnaire."""
        return cls(
            platform=data['platform'],
            status=VerificationStatus(data['status']),
            exists=data.get('exists', False),
            error=data.get('error'),
            username=data.get('username'),
            last_seen=datetime.fromisoformat(data['last_seen']) if data.get('last_seen') else None,
            confidence_score=data.get('confidence_score', 0.0),
            metadata=data.get('metadata', {}),
            timestamp=datetime.fromisoformat(data['timestamp']),
            response_time=data.get('response_time', 0.0)
        )

@dataclass
class PhoneCheckRequest:
    """Requête de vérification d'un numéro."""
    phone: str
    country_code: str
    platforms: List[str] = field(default_factory=list)
    force_refresh: bool = False
    max_concurrent_checks: int = 4
    
    def __post_init__(self):
        """Valide la requête après création."""
        if not self.platforms:
            from .platforms import DEFAULT_PLATFORMS
            self.platforms = DEFAULT_PLATFORMS.copy()
    
    @property
    def full_number(self) -> str:
        """Retourne le numéro complet avec l'indicatif."""
        return f"+{self.country_code}{self.phone}"

@dataclass
class PhoneCheckResponse:
    """Réponse complète d'une vérification."""
    request: PhoneCheckRequest
    results: List[PhoneCheckResult]
    total_time: float = 0.0
    successful_checks: int = 0
    failed_checks: int = 0
    
    def __post_init__(self):
        """Calcule les statistiques après création."""
        self.successful_checks = sum(1 for r in self.results if r.is_successful)
        self.failed_checks = len(self.results) - self.successful_checks
    
    @property
    def success_rate(self) -> float:
        """Taux de succès des vérifications."""
        if not self.results:
            return 0.0
        return self.successful_checks / len(self.results)
    
    @property
    def platforms_found(self) -> List[str]:
        """Liste des plateformes où le numéro a été trouvé."""
        return [r.platform for r in self.results if r.exists]
    
    @property
    def platforms_not_found(self) -> List[str]:
        """Liste des plateformes où le numéro n'a pas été trouvé."""
        return [r.platform for r in self.results if not r.exists and r.is_successful]
    
    @property
    def platforms_error(self) -> List[str]:
        """Liste des plateformes avec des erreurs."""
        return [r.platform for r in self.results if not r.is_successful]
    
    def get_result_by_platform(self, platform: str) -> Optional[PhoneCheckResult]:
        """Retourne le résultat pour une plateforme spécifique."""
        return next((r for r in self.results if r.platform == platform), None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la réponse en dictionnaire."""
        return {
            'request': {
                'phone': self.request.phone,
                'country_code': self.request.country_code,
                'platforms': self.request.platforms,
                'force_refresh': self.request.force_refresh
            },
            'results': [r.to_dict() for r in self.results],
            'summary': {
                'total_time': self.total_time,
                'successful_checks': self.successful_checks,
                'failed_checks': self.failed_checks,
                'success_rate': self.success_rate,
                'platforms_found': self.platforms_found,
                'platforms_not_found': self.platforms_not_found,
                'platforms_error': self.platforms_error
            }
        }
