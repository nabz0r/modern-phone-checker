"""Vérificateur WhatsApp avec gestion du rate limiting et des erreurs.

Ce module implémente la vérification des numéros sur WhatsApp de manière
éthique et respectueuse des limites d'utilisation.
"""

import httpx
from typing import Optional
from datetime import datetime
from ..models import PhoneCheckResult
from ..utils import rate_limit, clean_phone_number, validate_phone_number

class WhatsAppError(Exception):
    """Erreur spécifique aux vérifications WhatsApp."""
    pass

class WhatsAppChecker:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        """Initialise le vérificateur WhatsApp.
        
        Args:
            client: Client HTTP asynchrone optionnel
        """
        self.client = client or httpx.AsyncClient()
        self.timeout = httpx.Timeout(10.0, connect=5.0)
    
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
        try:
            # Vérifie d'abord si le numéro est valide
            if not validate_phone_number(phone, country_code):
                raise WhatsAppError("Numéro de téléphone invalide")
            
            # Nettoie et prépare le numéro
            clean_number = clean_phone_number(phone)
            full_number = f"{country_code}{clean_number}"
            
            # Vérifie via l'API wa.me
            url = f"https://wa.me/{full_number}"
            response = await self.client.head(
                url,
                follow_redirects=True,
                timeout=self.timeout
            )
            
            # Analyse la réponse
            exists = response.status_code == 200
            metadata = {
                'status_code': response.status_code,
                'url': str(response.url)
            }
            
            return PhoneCheckResult(
                platform='whatsapp',
                exists=exists,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
        except httpx.TimeoutException:
            return PhoneCheckResult(
                platform='whatsapp',
                exists=False,
                error="Timeout lors de la vérification",
                timestamp=datetime.now()
            )
            
        except WhatsAppError as e:
            return PhoneCheckResult(
                platform='whatsapp',
                exists=False,
                error=str(e),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return PhoneCheckResult(
                platform='whatsapp',
                exists=False,
                error=f"Erreur inattendue: {str(e)}",
                timestamp=datetime.now()
            )
