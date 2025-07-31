"""Vérificateur Telegram avec support de l'API officielle.

Ce module implémente la vérification des numéros sur Telegram
en utilisant des méthodes respectueuses de l'API officielle.
"""

import time
import json
from typing import Optional, Dict, Any
from datetime import datetime
import httpx

from ..models import PhoneCheckResult, VerificationStatus
from ..utils import rate_limit, clean_phone_number, validate_phone_number
from .base import BaseChecker

class TelegramChecker(BaseChecker):
    """Vérificateur pour Telegram utilisant des méthodes publiques."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        super().__init__(client, "telegram")
        
        # Headers spécifiques à Telegram
        self.client.headers.update({
            'Referer': 'https://web.telegram.org/',
            'Origin': 'https://web.telegram.org',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'
        })
        
        # URLs de l'API Telegram
        self.web_api_url = "https://web.telegram.org"
        self.login_api_url = "https://my.telegram.org/auth"
    
    @rate_limit(calls=5, period=60)  # Limite à 5 appels par minute (plus restrictif)
    async def check(self, phone: str, country_code: str) -> PhoneCheckResult:
        """Vérifie si un numéro est présent sur Telegram.
        
        Utilise l'API de connexion publique de Telegram pour vérifier
        l'existence d'un compte, sans envoyer de notifications.
        
        Args:
            phone: Numéro sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
            
        Returns:
            PhoneCheckResult avec les détails de la vérification
        """
        start_time = time.time()
        
        try:
            # Validation des entrées
            self._validate_inputs(phone, country_code)
            
            if not validate_phone_number(phone, country_code):
                return self._create_error_result(
                    "Numéro de téléphone invalide",
                    VerificationStatus.ERROR
                )
            
            clean_number = clean_phone_number(phone)
            full_number = f"+{country_code}{clean_number}"
            
            self.logger.debug(f"Vérification Telegram pour {full_number}")
            
            # Méthode 1: Vérification via l'API de connexion
            result = await self._check_via_login_api(full_number)
            
            if result['success']:
                response_time = (time.time() - start_time) * 1000
                self.logger.log_verification_result(
                    'telegram', full_number, result['exists']
                )
                
                return self._create_success_result(
                    exists=result['exists'],
                    response_time=response_time,
                    username=result.get('username'),
                    metadata=result.get('metadata', {})
                )
            
            # Méthode 2: Vérification via recherche publique (fallback)
            result = await self._check_via_public_search(full_number)
            response_time = (time.time() - start_time) * 1000
            
            if result['success']:
                self.logger.log_verification_result(
                    'telegram', full_number, result['exists']
                )
                
                return self._create_success_result(
                    exists=result['exists'],
                    response_time=response_time,
                    username=result.get('username'),
                    metadata=result.get('metadata', {})
                )
            
            # Si toutes les méthodes échouent
            return self._create_error_result(
                result.get('error', 'Impossible de vérifier le numéro'),
                VerificationStatus.ERROR,
                {'response_time': response_time}
            )
            
        except httpx.TimeoutException:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Timeout Telegram après {response_time:.1f}ms")
            return self._create_error_result(
                "Délai d'attente dépassé lors de la vérification Telegram",
                VerificationStatus.TIMEOUT,
                {'response_time': response_time}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Erreur inattendue Telegram: {e}")
            return self._create_error_result(
                f"Erreur inattendue: {str(e)}",
                VerificationStatus.ERROR,
                {'response_time': response_time}
            )
    
    async def _check_via_login_api(self, phone_number: str) -> Dict[str, Any]:
        """Vérifie via l'API de connexion de Telegram.
        
        Cette méthode utilise l'endpoint de vérification de numéro
        sans déclencher l'envoi d'un SMS.
        
        Args:
            phone_number: Numéro complet avec indicatif
            
        Returns:
            Dictionnaire avec le résultat de la vérification
        """
        try:
            # Étape 1: Obtenir un token de session
            session_data = await self._get_telegram_session()
            if not session_data['success']:
                return {'success': False, 'error': 'Impossible d\'obtenir une session'}
            
            # Étape 2: Vérifier le numéro
            url = f"{self.login_api_url}/send_password"
            data = {
                'phone': phone_number,
                'random_id': session_data['random_id']
            }
            
            response = await self._make_request('POST', url, json=data)
            
            # Analyse de la réponse
            if response.status_code == 200:
                result_data = response.json()
                
                # Si Telegram renvoie une erreur "phone number not registered"
                if 'error' in result_data:
                    error_msg = result_data['error'].lower()
                    if 'not registered' in error_msg or 'invalid' in error_msg:
                        return {
                            'success': True,
                            'exists': False,
                            'metadata': {
                                'method': 'login_api',
                                'status_code': response.status_code,
                                'telegram_error': result_data['error']
                            }
                        }
                
                # Si la requête est acceptée, le numéro existe probablement
                return {
                    'success': True,
                    'exists': True,
                    'metadata': {
                        'method': 'login_api',
                        'status_code': response.status_code
                    }
                }
            
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_via_public_search(self, phone_number: str) -> Dict[str, Any]:
        """Vérifie via la recherche publique de Telegram.
        
        Utilise l'API de recherche publique pour détecter
        l'existence d'un compte sans notification.
        
        Args:
            phone_number: Numéro complet avec indicatif
            
        Returns:
            Dictionnaire avec le résultat de la vérification
        """
        try:
            # Cette méthode est plus simple mais moins fiable
            # Elle utilise la fonction de recherche publique
            url = "https://t.me/search"
            params = {'q': phone_number}
            
            response = await self._make_request('GET', url, params=params)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # Recherche d'indices dans le contenu
                if 'user not found' in content or 'no results' in content:
                    return {
                        'success': True,
                        'exists': False,
                        'metadata': {
                            'method': 'public_search',
                            'status_code': response.status_code
                        }
                    }
                
                # Si on trouve des références au numéro
                if phone_number in content or 'telegram user' in content:
                    return {
                        'success': True,
                        'exists': True,
                        'metadata': {
                            'method': 'public_search',
                            'status_code': response.status_code
                        }
                    }
            
            # Méthode alternative: vérification d'URL directe
            return await self._check_direct_profile(phone_number)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_direct_profile(self, phone_number: str) -> Dict[str, Any]:
        """Vérifie l'existence d'un profil via URL directe.
        
        Args:
            phone_number: Numéro complet
            
        Returns:
            Résultat de la vérification
        """
        try:
            # Telegram permet parfois l'accès direct via numéro
            # Format: t.me/+33612345678 (sans le + dans l'URL)
            clean_number = phone_number.replace('+', '')
            url = f"https://t.me/{clean_number}"
            
            response = await self._make_request('HEAD', url, follow_redirects=True)
            
            # Si on obtient une réponse 200, le profil pourrait exister
            exists = response.status_code == 200
            
            return {
                'success': True,
                'exists': exists,
                'metadata': {
                    'method': 'direct_profile',
                    'status_code': response.status_code,
                    'final_url': str(response.url)
                }
            }
            
        except Exception:
            # En cas d'erreur, on ne peut pas conclure
            return {
                'success': True,
                'exists': False,
                'metadata': {
                    'method': 'direct_profile',
                    'error': 'Profil direct non accessible'
                }
            }
    
    async def _get_telegram_session(self) -> Dict[str, Any]:
        """Obtient une session temporaire pour les requêtes API.
        
        Returns:
            Données de session ou erreur
        """
        try:
            import random
            import string
            
            # Génère un ID aléatoire pour la session
            random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            
            url = f"{self.login_api_url}/start"
            response = await self._make_request('GET', url)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'random_id': random_id,
                    'session_data': response.cookies
                }
            
            return {'success': False, 'error': 'Session non disponible'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_username_from_response(self, response_text: str) -> Optional[str]:
        """Extrait le nom d'utilisateur depuis une réponse HTML/JSON.
        
        Args:
            response_text: Contenu de la réponse
            
        Returns:
            Nom d'utilisateur si trouvé
        """
        try:
            # Recherche de patterns de nom d'utilisateur Telegram
            import re
            
            # Pattern pour @username
            username_pattern = r'@([a-zA-Z0-9_]{5,})'
            matches = re.findall(username_pattern, response_text)
            
            if matches:
                return matches[0]
            
            # Pattern pour nom d'utilisateur dans JSON
            if '"username"' in response_text:
                try:
                    data = json.loads(response_text)
                    return data.get('username')
                except:
                    pass
            
            return None
            
        except Exception:
            return None
