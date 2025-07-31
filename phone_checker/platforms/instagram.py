"""Vérificateur Instagram avec gestion intelligente des requêtes.

Ce module vérifie si un numéro est associé à un compte Instagram en utilisant
l'API publique de manière respectueuse et éthique.
"""

import time
import json
from typing import Optional, Dict, Any
from datetime import datetime
import httpx

from ..models import PhoneCheckResult, VerificationStatus
from ..utils import rate_limit, clean_phone_number, validate_phone_number
from .base import BaseChecker

class InstagramChecker(BaseChecker):
    """Vérificateur pour Instagram utilisant l'API web publique."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        super().__init__(client, "instagram")
        
        # Headers spécifiques à Instagram
        self.client.headers.update({
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com',
            'X-Instagram-AJAX': '1',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'
        })
        
        # Session data pour Instagram
        self._csrf_token = None
        self._session_initialized = False
    
    @rate_limit(calls=5, period=60)  # Plus restrictif car Instagram est sensible
    async def check(self, phone: str, country_code: str) -> PhoneCheckResult:
        """Vérifie la présence d'un numéro sur Instagram.
        
        Cette méthode utilise l'API publique d'inscription d'Instagram pour
        vérifier si un numéro est déjà associé à un compte.
        
        Args:
            phone: Numéro sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
        """
        start_time = time.time()
        
        try:
            # Validation des entrées
            self._validate_inputs(phone, country_code)
            
            if not validate_phone_number(phone, country_code):
                return self._create_error_result(
                    "Format de numéro invalide",
                    VerificationStatus.ERROR
                )
            
            clean_number = clean_phone_number(phone)
            full_number = f"+{country_code}{clean_number}"
            
            self.logger.debug(f"Vérification Instagram pour {full_number}")
            
            # Initialise la session si nécessaire
            if not self._session_initialized:
                await self._initialize_session()
            
            # Méthode 1: Vérification via l'API d'inscription
            result = await self._check_via_signup_api(full_number)
            
            if result['success']:
                response_time = (time.time() - start_time) * 1000
                self.logger.log_verification_result(
                    'instagram', full_number, result['exists']
                )
                
                return self._create_success_result(
                    exists=result['exists'],
                    response_time=response_time,
                    username=result.get('username'),
                    metadata=result.get('metadata', {})
                )
            
            # Méthode 2: Vérification via reset password (fallback)
            result = await self._check_via_password_reset(full_number)
            response_time = (time.time() - start_time) * 1000
            
            if result['success']:
                self.logger.log_verification_result(
                    'instagram', full_number, result['exists']
                )
                
                return self._create_success_result(
                    exists=result['exists'],
                    response_time=response_time,
                    metadata=result.get('metadata', {})
                )
            
            return self._create_error_result(
                result.get('error', 'Impossible de vérifier le numéro'),
                VerificationStatus.ERROR,
                {'response_time': response_time}
            )
            
        except httpx.TimeoutException:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Timeout Instagram après {response_time:.1f}ms")
            return self._create_error_result(
                "Délai d'attente dépassé",
                VerificationStatus.TIMEOUT,
                {'response_time': response_time}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Erreur inattendue Instagram: {e}")
            return self._create_error_result(
                str(e),
                VerificationStatus.ERROR,
                {'response_time': response_time}
            )
    
    async def _initialize_session(self):
        """Initialise une session Instagram pour les requêtes API."""
        try:
            # Récupère la page d'inscription pour obtenir le CSRF token
            response = await self._make_request('GET', 'https://www.instagram.com/accounts/emailsignup/')
            
            if response.status_code == 200:
                # Extrait le CSRF token du HTML ou des cookies
                self._csrf_token = self._extract_csrf_token(response)
                
                if self._csrf_token:
                    self.client.headers['X-CSRFToken'] = self._csrf_token
                    self._session_initialized = True
                    self.logger.debug("Session Instagram initialisée avec succès")
                else:
                    self.logger.warning("Impossible d'obtenir le CSRF token Instagram")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de session Instagram: {e}")
    
    def _extract_csrf_token(self, response: httpx.Response) -> Optional[str]:
        """Extrait le token CSRF de la réponse Instagram.
        
        Args:
            response: Réponse HTTP d'Instagram
            
        Returns:
            Token CSRF ou None si non trouvé
        """
        try:
            # Méthode 1: Depuis les cookies
            if 'csrftoken' in response.cookies:
                return response.cookies['csrftoken']
            
            # Méthode 2: Depuis le HTML
            import re
            content = response.text
            
            # Pattern pour le token dans une balise meta
            csrf_pattern = r'"csrf_token":"([^"]+)"'
            matches = re.findall(csrf_pattern, content)
            
            if matches:
                return matches[0]
            
            # Pattern alternatif
            csrf_pattern2 = r'csrfmiddlewaretoken["\']?\s*:\s*["\']([^"\']+)'
            matches2 = re.findall(csrf_pattern2, content)
            
            if matches2:
                return matches2[0]
            
            return None
            
        except Exception:
            return None
    
    async def _check_via_signup_api(self, phone_number: str) -> Dict[str, Any]:
        """Vérifie via l'API d'inscription Instagram.
        
        Args:
            phone_number: Numéro complet avec indicatif
            
        Returns:
            Dictionnaire avec le résultat
        """
        try:
            url = "https://www.instagram.com/accounts/web_create_ajax/attempt/"
            data = {
                'email': '',
                'username': '',
                'first_name': '',
                'opt_into_one_tap': 'false',
                'phone_number': phone_number
            }
            
            headers = {}
            if self._csrf_token:
                headers['X-CSRFToken'] = self._csrf_token
            
            response = await self._make_request('POST', url, data=data, headers=headers)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # Si Instagram retourne une erreur pour le numéro de téléphone
                    errors = result.get('errors', {})
                    phone_errors = errors.get('phone_number', [])
                    
                    if phone_errors:
                        # Le numéro existe déjà
                        error_msg = phone_errors[0] if isinstance(phone_errors, list) else str(phone_errors)
                        exists = 'already' in error_msg.lower() or 'taken' in error_msg.lower()
                        
                        return {
                            'success': True,
                            'exists': exists,
                            'metadata': {
                                'method': 'signup_api',
                                'status_code': response.status_code,
                                'instagram_error': error_msg
                            }
                        }
                    
                    # Pas d'erreur = numéro disponible (n'existe pas)
                    return {
                        'success': True,
                        'exists': False,
                        'metadata': {
                            'method': 'signup_api',
                            'status_code': response.status_code
                        }
                    }
                    
                except json.JSONDecodeError:
                    return {'success': False, 'error': "Réponse JSON invalide"}
            
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_via_password_reset(self, phone_number: str) -> Dict[str, Any]:
        """Vérifie via l'API de réinitialisation de mot de passe.
        
        Args:
            phone_number: Numéro complet
            
        Returns:
            Résultat de la vérification
        """
        try:
            url = "https://www.instagram.com/accounts/account_recovery_send_ajax/"
            data = {
                'email_or_username': phone_number,
                'recaptcha_challenge_field': ''
            }
            
            headers = {}
            if self._csrf_token:
                headers['X-CSRFToken'] = self._csrf_token
            
            response = await self._make_request('POST', url, data=data, headers=headers)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # Si Instagram trouve le compte
                    if result.get('status') == 'ok':
                        return {
                            'success': True,
                            'exists': True,
                            'metadata': {
                                'method': 'password_reset',
                                'status_code': response.status_code
                            }
                        }
                    
                    # Si le compte n'est pas trouvé
                    if 'error' in result or result.get('status') == 'fail':
                        return {
                            'success': True,
                            'exists': False,
                            'metadata': {
                                'method': 'password_reset',
                                'status_code': response.status_code,
                                'instagram_error': result.get('message', 'Account not found')
                            }
                        }
                    
                except json.JSONDecodeError:
                    pass
            
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _search_by_phone(self, phone_number: str) -> Dict[str, Any]:
        """Recherche un profil par numéro de téléphone (méthode alternative).
        
        Args:
            phone_number: Numéro à rechercher
            
        Returns:
            Résultat de la recherche
        """
        try:
            # Cette méthode utilise l'API de recherche d'Instagram
            url = "https://www.instagram.com/web/search/topsearch/"
            params = {
                'query': phone_number,
                'context': 'user'
            }
            
            response = await self._make_request('GET', url, params=params)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    users = result.get('users', [])
                    
                    # Si on trouve des utilisateurs
                    if users:
                        user = users[0]  # Premier résultat
                        username = user.get('user', {}).get('username')
                        
                        return {
                            'success': True,
                            'exists': True,
                            'username': username,
                            'metadata': {
                                'method': 'search_api',
                                'status_code': response.status_code,
                                'users_found': len(users)
                            }
                        }
                    
                    # Aucun utilisateur trouvé
                    return {
                        'success': True,
                        'exists': False,
                        'metadata': {
                            'method': 'search_api',
                            'status_code': response.status_code
                        }
                    }
                    
                except json.JSONDecodeError:
                    pass
            
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
