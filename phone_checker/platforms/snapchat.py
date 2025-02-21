"""Vérificateur Snapchat avec gestion des sessions et des tokens.

Ce module vérifie l'existence d'un numéro sur Snapchat en utilisant
l'API web publique de manière éthique.
"""

import httpx
from typing import Optional, Dict
from datetime import datetime
import json
from ..models import PhoneCheckResult
from ..utils import rate_limit, clean_phone_number, validate_phone_number

class SnapchatChecker:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client or httpx.AsyncClient()
        self.client.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
            'Accept': 'application/json',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
        })
        self.timeout = httpx.Timeout(15.0)  # Timeout plus long car Snapchat peut être lent
        
    async def _get_web_token(self) -> Optional[str]:
        """Récupère un token temporaire pour l'API web de Snapchat."""
        try:
            response = await self.client.get(
                'https://accounts.snapchat.com/accounts/signup',
                timeout=self.timeout
            )
            # Le token est dans une balise meta ou dans un script JS
            # Cette partie est simplifiée, en réalité il faudrait parser le HTML
            return 'xsrf-token'
        except Exception:
            return None
    
    @rate_limit(calls=3, period=60)  # Très restrictif pour éviter les blocages
    async def check(self, phone: str, country_code: str) -> PhoneCheckResult:
        """Vérifie si un numéro est associé à un compte Snapchat.
        
        Cette méthode utilise l'API de vérification de connexion de Snapchat
        pour déterminer si un numéro est déjà utilisé.
        
        Args:
            phone: Numéro sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
        """
        try:
            if not validate_phone_number(phone, country_code):
                raise ValueError("Format de numéro invalide")
            
            clean_number = clean_phone_number(phone)
            full_number = f"+{country_code}{clean_number}"
            
            # Récupération du token (dans un vrai scénario)
            token = await self._get_web_token()
            if not token:
                return PhoneCheckResult(
                    platform='snapchat',
                    exists=False,
                    error="Impossible d'obtenir un token d'accès",
                    timestamp=datetime.now()
                )
            
            # Requête de vérification
            url = "https://accounts.snapchat.com/accounts/validate_phone_number"
            data = {
                'phone_country_code': country_code,
                'phone_number': clean_number,
                'xsrf_token': token
            }
            
            headers = {
                'X-XSRF-TOKEN': token,
                'Referer': 'https://accounts.snapchat.com/accounts/signup',
            }
            
            response = await self.client.post(
                url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            # Dans un cas réel, on analyserait la réponse de l'API
            # Ici on simule une vérification basique
            exists = response.status_code == 400  # Sur Snapchat, 400 indique souvent un numéro déjà utilisé
            
            metadata = {
                'status_code': response.status_code,
                'verification_method': 'signup_validation'
            }
            
            return PhoneCheckResult(
                platform='snapchat',
                exists=exists,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
        except httpx.TimeoutException:
            return PhoneCheckResult(
                platform='snapchat',
                exists=False,
                error="Délai d'attente dépassé",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return PhoneCheckResult(
                platform='snapchat',
                exists=False,
                error=str(e),
                timestamp=datetime.now()
            )
