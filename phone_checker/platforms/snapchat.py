"""Vérificateur Snapchat avec gestion des sessions et des tokens.

Ce module vérifie l'existence d'un numéro sur Snapchat en utilisant
l'API web publique de manière éthique.
"""

import time
import json
from typing import Optional, Dict, Any
from datetime import datetime
import httpx

from ..models import PhoneCheckResult, VerificationStatus
from ..utils import rate_limit, clean_phone_number, validate_phone_number
from .base import BaseChecker

class SnapchatChecker(BaseChecker):
    """Vérificateur pour Snapchat utilisant l'API web."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        super().__init__(client, "snapchat")
        
        # Headers spécifiques à Snapchat
        self.client.headers.update({
            'Referer': 'https://accounts.snapchat.com/',
            'Origin': 'https://accounts.snapchat.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        })
        
        # Session data pour Snapchat
        self._xsrf_token = None
        self._session_initialized = False
        
        # Timeout plus long car Snapchat peut être lent
        self.timeout = httpx.Timeout(15.0)
    
    @rate_limit(calls=3, period=60)  # Très restrictif pour éviter les blocages
    async def check(self, phone: str, country_code: str) -> PhoneCheckResult:
        """Vérifie si un numéro est associé à un compte Snapchat.
        
        Cette méthode utilise l'API de vérification de connexion de Snapchat
        pour déterminer si un numéro est déjà utilisé.
        
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
            
            self.logger.debug(f"Vérification Snapchat pour {full_number}")
            
            # Initialise la session si nécessaire
            if not self._session_initialized:
                await self._initialize_session()
            
            # Méthode 1: Vérification via l'API de validation de numéro
            result = await self._check_via_phone_validation(clean_number, country_code)
            
            if result['success']:
                response_time = (time.time() - start_time) * 1000
                self.logger.log_verification_result(
                    'snapchat', full_number, result['exists']
                )
                
                return self._create_success_result(
                    exists=result['exists'],
                    response_time=response_time,
                    metadata=result.get('metadata', {})
                )
            
            # Méthode 2: Vérification via login (fallback)
            result = await self._check_via_login_attempt(full_number)
            response_time = (time.time() - start_time) * 1000
            
            if result['success']:
                self.logger.log_verification_result(
                    'snapchat', full_number, result['exists']
                )
                
                return self._create_success_result(
                    exists=result['exists'],
                    response_time=response_time,
                    metadata=result.get('metadata', {})
                )
            
            return self._create_error_result(
                result.get('error', 'Impossible d\'obtenir un token d\'accès'),
                VerificationStatus.ERROR,
                {'response_time': response_time}
            )
            
        except httpx.TimeoutException:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Timeout Snapchat après {response_time:.1f}ms")
            return self._create_error_result(
                "Délai d'attente dépassé",
                VerificationStatus.TIMEOUT,
                {'response_time': response_time}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Erreur inattendue Snapchat: {e}")
            return self._create_error_result(
                str(e),
                VerificationStatus.ERROR,
                {'response_time': response_time}
            )
    
    async def _initialize_session(self):
        """Initialise une session Snapchat et récupère le token XSRF."""
        try:
            # Récupère la page d'inscription
            response = await self._make_request('GET', 'https://accounts.snapchat.com/accounts/signup')
            
            if response.status_code == 200:
                # Extrait le token XSRF
                self._xsrf_token = self._extract_xsrf_token(response)
                
                if self._xsrf_token:
                    self.client.headers['X-XSRF-TOKEN'] = self._xsrf_token
                    self._session_initialized = True
                    self.logger.debug("Session Snapchat initialisée avec succès")
                else:
                    self.logger.warning("Impossible d'obtenir le token XSRF Snapchat")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de session Snapchat: {e}")
    
    def _extract_xsrf_token(self, response: httpx.Response) -> Optional[str]:
        """Extrait le token XSRF de la réponse Snapchat.
        
        Args:
            response: Réponse HTTP de Snapchat
            
        Returns:
            Token XSRF ou None si non trouvé
        """
        try:
            # Méthode 1: Depuis les cookies
            if 'xsrf_token' in response.cookies:
                return response.cookies['xsrf_token']
            
            # Méthode 2: Depuis le HTML
            import re
            content = response.text
            
            # Pattern pour le token dans une balise meta ou script
            xsrf_patterns = [
                r'"xsrf_token":"([^"]+)"',
                r"'xsrf_token':'([^']+)'",
                r'xsrf_token["\']?\s*:\s*["\']([^"\']+)',
                r'<meta name="csrf-token" content="([^"]+)"'
            ]
            
            for pattern in xsrf_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    return matches[0]
            
            return 'missing'  # Snapchat accepte parfois 'missing' comme token
            
        except Exception:
            return 'missing'
    
    async def _check_via_phone_validation(self, phone: str, country_code: str) -> Dict[str, Any]:
        """Vérifie via l'API de validation de numéro de Snapchat.
        
        Args:
            phone: Numéro sans indicatif
            country_code: Code pays
            
        Returns:
            Dictionnaire avec le résultat
        """
        try:
            url = "https://accounts.snapchat.com/accounts/validate_phone_number"
            data = {
                'phone_country_code': country_code,
                'phone_number': phone,
                'xsrf_token': self._xsrf_token or 'missing'
            }
            
            response = await self._make_request('POST', url, data=data)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # Snapchat retourne des codes d'erreur spécifiques
                    if 'error' in result:
                        error_code = result.get('error_code')
                        error_msg = result.get('error', '').lower()
                        
                        # Codes indiquant que le numéro existe déjà
                        if error_code in ['PHONE_NUMBER_TAKEN', 'PHONE_ALREADY_VERIFIED']:
                            return {
                                'success': True,
                                'exists': True,
                                'metadata': {
                                    'method': 'phone_validation',
                                    'status_code': response.status_code,
                                    'snapchat_error': result['error'],
                                    'error_code': error_code
                                }
                            }
                        
                        # Codes indiquant un numéro invalide/inexistant
                        if error_code in ['INVALID_PHONE_NUMBER', 'PHONE_NUMBER_INVALID']:
                            return {
                                'success': True,
                                'exists': False,
                                'metadata': {
                                    'method': 'phone_validation',
                                    'status_code': response.status_code,
                                    'snapchat_error': result['error'],
                                    'error_code': error_code
                                }
                            }
                    
                    # Pas d'erreur = probablement disponible
                    return {
                        'success': True,
                        'exists': False,
                        'metadata': {
                            'method': 'phone_validation',
                            'status_code': response.status_code
                        }
                    }
                    
                except json.JSONDecodeError:
                    pass
            
            # Status code 400 peut indiquer un numéro déjà utilisé
            if response.status_code == 400:
                return {
                    'success': True,
                    'exists': True,
                    'metadata': {
                        'method': 'phone_validation',
                        'status_code': response.status_code,
                        'note': 'HTTP 400 souvent = numéro existant'
                    }
                }
            
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_via_login_attempt(self, phone_number: str) -> Dict[str, Any]:
        """Vérifie via une tentative de connexion.
        
        Args:
            phone_number: Numéro complet
            
        Returns:
            Résultat de la vérification
        """
        try:
            url = "https://accounts.snapchat.com/accounts/login"
            data = {
                'username': phone_number,
                'password': 'fake_password_for_check',
                'xsrf_token': self._xsrf_token or 'missing'
            }
            
            response = await self._make_request('POST', url, data=data)
            
            if response.status_code in [200, 400, 401]:
                try:
                    result = response.json()
                    
                    # Si Snapchat retourne une erreur de mot de passe,
                    # cela signifie que le compte existe
                    if 'error' in result:
                        error_msg = result['error'].lower()
                        
                        if 'password' in error_msg or 'incorrect' in error_msg:
                            return {
                                'success': True,
                                'exists': True,
                                'metadata': {
                                    'method': 'login_attempt',
                                    'status_code': response.status_code,
                                    'note': 'Erreur mot de passe = compte existe'
                                }
                            }
                        
                        if 'user not found' in error_msg or 'account not found' in error_msg:
                            return {
                                'success': True,
                                'exists': False,
                                'metadata': {
                                    'method': 'login_attempt',
                                    'status_code': response.status_code,
                                    'snapchat_error': result['error']
                                }
                            }
                
                except json.JSONDecodeError:
                    pass
            
            # Par défaut, on ne peut pas déterminer
            return {
                'success': True,
                'exists': False,
                'metadata': {
                    'method': 'login_attempt',
                    'status_code': response.status_code,
                    'note': 'Résultat indéterminé'
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _check_via_username_search(self, phone_number: str) -> Dict[str, Any]:
        """Vérifie via la recherche d'utilisateur (méthode alternative).
        
        Args:
            phone_number: Numéro à rechercher
            
        Returns:
            Résultat de la recherche
        """
        try:
            # Snapchat permet parfois la recherche par numéro
            url = "https://accounts.snapchat.com/accounts/username_available"
            data = {
                'username': phone_number.replace('+', ''),
                'xsrf_token': self._xsrf_token or 'missing'
            }
            
            response = await self._make_request('POST', url, data=data)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # Si le "nom d'utilisateur" (numéro) n'est pas disponible
                    if not result.get('available', True):
                        return {
                            'success': True,
                            'exists': True,
                            'metadata': {
                                'method': 'username_search',
                                'status_code': response.status_code
                            }
                        }
                    
                except json.JSONDecodeError:
                    pass
            
            return {
                'success': True,
                'exists': False,
                'metadata': {
                    'method': 'username_search',
                    'status_code': response.status_code
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
