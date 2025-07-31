"""Classe de base pour tous les vérificateurs de plateformes.

Cette classe définit l'interface commune que doivent respecter
tous les vérificateurs spécifiques aux plateformes.
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
from datetime import datetime

from ..models import PhoneCheckResult, VerificationStatus
from ..utils import calculate_confidence_score, generate_user_agent, parse_response_error
from ..logging import get_logger
from ..config import default_config

class BaseChecker(ABC):
    """Classe de base pour tous les vérificateurs de plateformes."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None, platform: str = "unknown"):
        """Initialise le vérificateur de base.
        
        Args:
            client: Client HTTP asyncrone optionnel
            platform: Nom de la plateforme
        """
        self.platform = platform
        self.client = client or httpx.AsyncClient()
        self.logger = get_logger(f'platforms.{platform}')
        self.config = default_config.get_platform_config(platform)
        
        # Configuration du client HTTP
        self.client.headers.update({
            'User-Agent': generate_user_agent(),
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Headers personnalisés par plateforme
        if self.config.custom_headers:
            self.client.headers.update(self.config.custom_headers)
        
        self.timeout = httpx.Timeout(self.config.timeout)
        
    @abstractmethod
    async def check(self, phone: str, country_code: str) -> PhoneCheckResult:
        """Vérifie si un numéro existe sur la plateforme.
        
        Args:
            phone: Numéro de téléphone sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
            
        Returns:
            PhoneCheckResult avec les détails de la vérification
        """
        pass
    
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Effectue une requête HTTP avec gestion d'erreurs et retry.
        
        Args:
            method: Méthode HTTP (GET, POST, etc.)
            url: URL à requêter
            **kwargs: Arguments supplémentaires pour la requête
            
        Returns:
            Réponse HTTP
            
        Raises:
            httpx.HTTPError: En cas d'erreur de requête
        """
        kwargs.setdefault('timeout', self.timeout)
        
        for attempt in range(self.config.retry_attempts + 1):
            try:
                start_time = time.time()
                response = await self.client.request(method, url, **kwargs)
                response_time = (time.time() - start_time) * 1000  # en ms
                
                self.logger.debug(
                    f"Requête {method} {url}: {response.status_code} en {response_time:.1f}ms"
                )
                
                return response
                
            except httpx.TimeoutException as e:
                if attempt < self.config.retry_attempts:
                    wait_time = 2 ** attempt  # Backoff exponentiel
                    self.logger.warning(f"Timeout, retry dans {wait_time}s (tentative {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                raise e
                
            except httpx.RequestError as e:
                if attempt < self.config.retry_attempts:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Erreur requête, retry dans {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                raise e
    
    def _create_error_result(
        self,
        error_message: str,
        status: VerificationStatus = VerificationStatus.ERROR,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PhoneCheckResult:
        """Crée un résultat d'erreur standardisé.
        
        Args:
            error_message: Message d'erreur
            status: Statut de vérification
            metadata: Métadonnées supplémentaires
            
        Returns:
            PhoneCheckResult avec l'erreur
        """
        return PhoneCheckResult(
            platform=self.platform,
            status=status,
            exists=False,
            error=error_message,
            metadata=metadata or {},
            timestamp=datetime.now()
        )
    
    def _create_success_result(
        self,
        exists: bool,
        response_time: float = 0.0,
        username: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None
    ) -> PhoneCheckResult:
        """Crée un résultat de succès standardisé.
        
        Args:
            exists: Si le numéro existe sur la plateforme
            response_time: Temps de réponse de la requête
            username: Nom d'utilisateur trouvé (optionnel)
            metadata: Métadonnées supplémentaires
            confidence_score: Score de confiance (calculé automatiquement si non fourni)
            
        Returns:
            PhoneCheckResult avec le résultat
        """
        if confidence_score is None:
            # Utilise le status code 200 par défaut pour le calcul
            status_code = metadata.get('status_code', 200) if metadata else 200
            platform_reliability = {
                'whatsapp': 0.9,
                'telegram': 0.85,
                'instagram': 0.75,
                'snapchat': 0.7
            }.get(self.platform, 0.8)
            
            confidence_score = calculate_confidence_score(
                status_code,
                response_time / 1000,  # Convertit ms en secondes
                platform_reliability
            )
        
        status = VerificationStatus.EXISTS if exists else VerificationStatus.NOT_EXISTS
        
        return PhoneCheckResult(
            platform=self.platform,
            status=status,
            exists=exists,
            username=username,
            confidence_score=confidence_score,
            metadata=metadata or {},
            timestamp=datetime.now(),
            response_time=response_time
        )
    
    async def _handle_response(
        self,
        response: httpx.Response,
        response_time: float
    ) -> Dict[str, Any]:
        """Gère une réponse HTTP et retourne les données utiles.
        
        Args:
            response: Réponse HTTP
            response_time: Temps de réponse en ms
            
        Returns:
            Dictionnaire avec les données parsées
        """
        metadata = {
            'status_code': response.status_code,
            'response_time': response_time,
            'url': str(response.url)
        }
        
        # Essaie de parser le JSON si possible
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                metadata['response_data'] = data
                return {
                    'success': True,
                    'data': data,
                    'metadata': metadata
                }
        except Exception:
            pass
        
        # Sinon utilise le texte
        return {
            'success': response.status_code < 400,
            'text': response.text,
            'metadata': metadata
        }
    
    def _validate_inputs(self, phone: str, country_code: str) -> None:
        """Valide les paramètres d'entrée.
        
        Args:
            phone: Numéro de téléphone
            country_code: Code pays
            
        Raises:
            ValueError: Si les paramètres sont invalides
        """
        if not phone or not phone.strip():
            raise ValueError("Le numéro de téléphone ne peut pas être vide")
        
        if not country_code or not country_code.strip():
            raise ValueError("L'indicatif pays ne peut pas être vide")
        
        if not country_code.isdigit():
            raise ValueError("L'indicatif pays doit être numérique")
    
    async def close(self):
        """Ferme les ressources du vérificateur."""
        if hasattr(self.client, 'aclose'):
            await self.client.aclose()
