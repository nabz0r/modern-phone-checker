"""Vérificateur WhatsApp avec gestion du rate limiting et des erreurs.

Ce module implémente la vérification des numéros sur WhatsApp de manière
éthique et respectueuse des limites d'utilisation.
"""

import time
from typing import Optional
from datetime import datetime
import httpx

from ..models import PhoneCheckResult, VerificationStatus
from ..utils import rate_limit, clean_phone_number, validate_phone_number
from .base import BaseChecker

class WhatsAppError(Exception):
    """Erreur spécifique aux vérifications WhatsApp."""
    pass

class WhatsAppChecker(BaseChecker):
    """Vérificateur pour WhatsApp utilisant l'API wa.me."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        super().__init__(client, "whatsapp")
        
        # Headers spécifiques à WhatsApp
        self.client.headers.update({
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache'
        })
    
    @rate_limit(calls=10, period=60)  # Limite à 10 appels par minute
    async def check(self, phone: str, country_code: str) -> PhoneCheckResult:
        """Vérifie si un numéro est enregistré sur WhatsApp.
        
        Cette méthode utilise l'API publique wa.me pour vérifier l'existence
        d'un compte WhatsApp, sans envoyer de notifications.
        
        Args:
            phone: Numéro de téléphone sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
            
        Returns:
            PhoneCheckResult avec les détails de la vérification
        """
        start_time = time.time()
        
        try:
            # Validation des entrées
            self._validate_inputs(phone, country_code)
            
            # Vérifie d'abord si le numéro est valide
            if not validate_phone_number(phone, country_code):
                return self._create_error_result(
                    "Numéro de téléphone invalide",
                    VerificationStatus.ERROR
                )
            
            # Nettoie et prépare le numéro
            clean_number = clean_phone_number(phone)
            full_number = f"{country_code}{clean_number}"
            
            self.logger.debug(f"Vérification WhatsApp pour +{country_code}{clean_number}")
            
            # Vérifie via l'API wa.me
            url = f"https://wa.me/{full_number}"
            
            response = await self._make_request('HEAD', url, follow_redirects=True)
            response_time = (time.time() - start_time) * 1000
            
            # Analyse la réponse
            exists = self._analyze_whatsapp_response(response)
            
            metadata = {
                'status_code': response.status_code,
                'final_url': str(response.url),
                'headers': dict(response.headers),
                'method': 'wa.me_check'
            }
            
            # Log du résultat
            self.logger.log_verification_result(
                'whatsapp', f"+{country_code}{clean_number}", exists
            )
            
            return self._create_success_result(
                exists=exists,
                response_time=response_time,
                metadata=metadata
            )
            
        except httpx.TimeoutException:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Timeout WhatsApp après {response_time:.1f}ms")
            return self._create_error_result(
                "Délai d'attente dépassé lors de la vérification WhatsApp",
                VerificationStatus.TIMEOUT,
                {'response_time': response_time}
            )
            
        except httpx.HTTPStatusError as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = f"Erreur HTTP {e.response.status_code}"
            self.logger.error(f"Erreur HTTP WhatsApp: {error_msg}")
            
            # Certaines erreurs peuvent indiquer que le numéro n'existe pas
            if e.response.status_code == 404:
                return self._create_success_result(
                    exists=False,
                    response_time=response_time,
                    metadata={'status_code': 404, 'method': 'wa.me_check'}
                )
            
            return self._create_error_result(error_msg, VerificationStatus.ERROR)
            
        except WhatsAppError as e:
            self.logger.error(f"Erreur WhatsApp spécifique: {e}")
            return self._create_error_result(str(e), VerificationStatus.ERROR)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Erreur inattendue WhatsApp: {e}")
            return self._create_error_result(
                f"Erreur inattendue: {str(e)}",
                VerificationStatus.ERROR,
                {'response_time': response_time}
            )
    
    def _analyze_whatsapp_response(self, response: httpx.Response) -> bool:
        """Analyse la réponse de l'API WhatsApp pour déterminer si le numéro existe.
        
        Args:
            response: Réponse HTTP de wa.me
            
        Returns:
            True si le numéro existe sur WhatsApp
        """
        # WhatsApp redirige vers l'app si le numéro existe
        # ou affiche une page d'erreur si le numéro n'existe pas
        
        # Code 200 = numéro existe et redirigé vers l'app
        if response.status_code == 200:
            return True
        
        # Code 404 = numéro n'existe pas
        if response.status_code == 404:
            return False
        
        # Analyse l'URL finale après redirection
        final_url = str(response.url).lower()
        
        # Si on est redirigé vers WhatsApp web ou l'app, le numéro existe
        if 'web.whatsapp.com' in final_url or 'api.whatsapp.com' in final_url:
            return True
        
        # Si on reste sur wa.me avec un paramètre d'erreur, le numéro n'existe pas
        if 'wa.me' in final_url and ('error' in final_url or 'invalid' in final_url):
            return False
        
        # Par défaut, on considère que le numéro existe si pas d'erreur explicite
        return response.status_code < 400
    
    async def check_multiple(self, numbers: list, country_code: str) -> list:
        """Vérifie plusieurs numéros en parallèle avec gestion du rate limiting.
        
        Args:
            numbers: Liste des numéros à vérifier
            country_code: Indicatif pays
            
        Returns:
            Liste des PhoneCheckResult
        """
        import asyncio
        
        # Limite la concurrence pour respecter le rate limiting
        semaphore = asyncio.Semaphore(3)  # Max 3 requêtes simultanées
        
        async def check_with_semaphore(phone):
            async with semaphore:
                return await self.check(phone, country_code)
        
        tasks = [check_with_semaphore(phone) for phone in numbers]
        return await asyncio.gather(*tasks, return_exceptions=True)
