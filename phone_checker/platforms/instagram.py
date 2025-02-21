"""Vérificateur Instagram avec gestion intelligente des requêtes.

Ce module vérifie si un numéro est associé à un compte Instagram en utilisant
l'API publique de manière respectueuse et éthique.
"""

import httpx
from typing import Optional
from datetime import datetime
import json
from ..models import PhoneCheckResult
from ..utils import rate_limit, clean_phone_number, validate_phone_number

class InstagramChecker:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client or httpx.AsyncClient()
        self.client.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
            'Accept': 'application/json',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
        })
        self.timeout = httpx.Timeout(10.0)
    
    @rate_limit(calls=5, period=60)  # Plus restrictif car Instagram est sensible au rate limiting
    async def check(self, phone: str, country_code: str) -> PhoneCheckResult:
        """Vérifie la présence d'un numéro sur Instagram.
        
        Cette méthode utilise l'API publique d'inscription d'Instagram pour
        vérifier si un numéro est déjà associé à un compte.
        
        Args:
            phone: Numéro sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
        """
        try:
            if not validate_phone_number(phone, country_code):
                raise ValueError("Format de numéro invalide")
            
            clean_number = clean_phone_number(phone)
            full_number = f"+{country_code}{clean_number}"
            
            # On utilise l'endpoint de vérification du formulaire d'inscription
            url = "https://www.instagram.com/accounts/web_create_ajax/attempt/"
            data = {
                'email': '',
                'username': '',
                'first_name': '',
                'opt_into_one_tap': 'false',
                'phone_number': full_number
            }
            
            # On ajoute des headers spécifiques pour ressembler à une requête légitime
            headers = {
                'X-CSRFToken': 'missing',  # Instagram accepte 'missing' pour les requêtes non authentifiées
                'X-Instagram-AJAX': '1',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://www.instagram.com/accounts/emailsignup/'
            }
            
            response = await self.client.post(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            
            # Analyse de la réponse
            result = response.json()
            exists = bool(result.get('errors', {}).get('phone_number'))
            
            metadata = {
                'status_code': response.status_code,
                'response_type': 'account_exists' if exists else 'number_available'
            }
            
            return PhoneCheckResult(
                platform='instagram',
                exists=exists,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
        except json.JSONDecodeError:
            return PhoneCheckResult(
                platform='instagram',
                exists=False,
                error="Impossible d'analyser la réponse d'Instagram",
                timestamp=datetime.now()
            )
            
        except httpx.TimeoutException:
            return PhoneCheckResult(
                platform='instagram',
                exists=False,
                error="Délai d'attente dépassé",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return PhoneCheckResult(
                platform='instagram',
                exists=False,
                error=str(e),
                timestamp=datetime.now()
            )
