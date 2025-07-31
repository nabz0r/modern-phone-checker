"""Module principal du vérificateur de numéros avec gestion avancée.

Ce module coordonne les différents vérificateurs de plateformes et gère
la logique centrale de l'application, y compris le cache et la concurrence.
"""

import asyncio
import time
from typing import List, Optional, Dict, Any
import httpx
from datetime import datetime

from .models import PhoneCheckResult, PhoneCheckRequest, PhoneCheckResponse, VerificationStatus
from .platforms import AVAILABLE_CHECKERS, DEFAULT_PLATFORMS
from .cache import CacheManager
from .utils import validate_phone_number, clean_phone_number, anonymize_phone_number
from .config import default_config
from .logging import logger

class PhoneChecker:
    """Classe principale pour la vérification des numéros de téléphone."""
    
    def __init__(
        self,
        platforms: Optional[List[str]] = None,
        proxy_url: Optional[str] = None,
        use_cache: bool = None,
        cache_expire: int = None,
        max_concurrent_checks: int = 4
    ):
        """Initialise le vérificateur avec les options spécifiées.
        
        Args:
            platforms: Liste des plateformes à vérifier (toutes si None)
            proxy_url: URL du proxy à utiliser (optionnel)
            use_cache: Activer le système de cache (utilise config par défaut si None)
            cache_expire: Durée de validité du cache en secondes
            max_concurrent_checks: Nombre maximum de vérifications simultanées
        """
        # Configuration
        self.config = default_config
        self.use_cache = use_cache if use_cache is not None else self.config.cache.enabled
        self.max_concurrent_checks = max_concurrent_checks
        
        # Client HTTP principal
        self.client = httpx.AsyncClient(
            proxies=proxy_url,
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
        )
        
        # Gestionnaire de cache
        if self.use_cache:
            cache_expire = cache_expire or self.config.cache.expire_after
            self.cache = CacheManager(
                cache_dir=self.config.cache.directory,
                expire_after=cache_expire
            )
        
        # Initialisation des vérificateurs
        self.checkers: Dict[str, Any] = {}
        self._initialize_checkers(platforms or DEFAULT_PLATFORMS)
        
        # Statistiques
        self.stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info(f"PhoneChecker initialisé avec {len(self.checkers)} plateformes")
    
    async def initialize(self):
        """Initialise les composants asynchrones."""
        if self.use_cache:
            await self.cache.initialize()
        logger.debug("PhoneChecker initialisé avec succès")
    
    def _initialize_checkers(self, platforms: List[str]):
        """Initialise les vérificateurs pour les plateformes sélectionnées."""
        for platform in platforms:
            if platform in AVAILABLE_CHECKERS:
                platform_config = self.config.get_platform_config(platform)
                if platform_config.enabled:
                    checker_class = AVAILABLE_CHECKERS[platform]
                    self.checkers[platform] = checker_class(self.client)
                    logger.debug(f"Vérificateur {platform} initialisé")
                else:
                    logger.debug(f"Plateforme {platform} désactivée dans la configuration")
            else:
                logger.warning(f"Plateforme inconnue: {platform}")
    
    async def check_number(
        self,
        phone: str,
        country_code: str,
        platforms: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> PhoneCheckResponse:
        """Vérifie un numéro sur les plateformes spécifiées.
        
        Args:
            phone: Numéro de téléphone sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
            platforms: Plateformes à vérifier (toutes par défaut)
            force_refresh: Force une nouvelle vérification même si en cache
            
        Returns:
            PhoneCheckResponse avec tous les résultats
        """
        start_time = time.time()
        
        # Validation et nettoyage du numéro
        if not validate_phone_number(phone, country_code):
            raise ValueError(f"Numéro invalide: +{country_code}{phone}")
        
        clean_number = clean_phone_number(phone)
        
        # Création de la requête
        request = PhoneCheckRequest(
            phone=clean_number,
            country_code=country_code,
            platforms=platforms or list(self.checkers.keys()),
            force_refresh=force_refresh,
            max_concurrent_checks=self.max_concurrent_checks
        )
        
        # Log du début de vérification
        anonymized = anonymize_phone_number(clean_number, country_code)
        logger.log_verification_start(anonymized, country_code, request.platforms)
        
        try:
            # Vérifie le cache si activé
            cached_results = []
            platforms_to_check = request.platforms.copy()
            
            if self.use_cache and not force_refresh:
                cached_data = await self.cache.get(clean_number, country_code)
                if cached_data:
                    self.stats['cache_hits'] += 1
                    logger.log_cache_hit(anonymized, country_code, cached_data['freshness_score'])
                    
                    # Utilise les résultats en cache
                    for platform, result_data in cached_data['results'].items():
                        if platform in request.platforms:
                            result = PhoneCheckResult.from_dict(result_data)
                            result.metadata['cached'] = True
                            result.metadata['freshness_score'] = cached_data['freshness_score']
                            cached_results.append(result)
                            platforms_to_check.remove(platform)
            
            if not platforms_to_check and cached_results:
                # Tous les résultats sont en cache
                response = PhoneCheckResponse(
                    request=request,
                    results=cached_results,
                    total_time=(time.time() - start_time) * 1000
                )
                logger.info(f"Vérification terminée (cache): {len(cached_results)} résultats")
                return response
            else:
                self.stats['cache_misses'] += 1
                logger.log_cache_miss(anonymized, country_code)
            
            # Effectue les vérifications nécessaires
            new_results = await self._perform_checks(
                clean_number, 
                country_code, 
                platforms_to_check
            )
            
            # Combine les résultats
            all_results = cached_results + new_results
            
            # Met en cache les nouveaux résultats
            if self.use_cache and new_results:
                results_dict = {r.platform: r.to_dict() for r in new_results}
                await self.cache.set(clean_number, country_code, results_dict)
            
            # Crée la réponse finale
            response = PhoneCheckResponse(
                request=request,
                results=all_results,
                total_time=(time.time() - start_time) * 1000
            )
            
            # Met à jour les statistiques
            self.stats['total_checks'] += len(all_results)
            self.stats['successful_checks'] += response.successful_checks
            self.stats['failed_checks'] += response.failed_checks
            
            logger.info(
                f"Vérification terminée: {len(all_results)} résultats "
                f"({response.success_rate:.1%} succès) en {response.total_time:.1f}ms"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification: {e}")
            raise
    
    async def _perform_checks(
        self, 
        phone: str, 
        country_code: str, 
        platforms: List[str]
    ) -> List[PhoneCheckResult]:
        """Effectue les vérifications sur les plateformes spécifiées.
        
        Args:
            phone: Numéro nettoyé
            country_code: Code pays
            platforms: Plateformes à vérifier
            
        Returns:
            Liste des résultats de vérification
        """
        # Limite la concurrence
        semaphore = asyncio.Semaphore(self.max_concurrent_checks)
        
        async def check_with_semaphore(platform: str):
            async with semaphore:
                checker = self.checkers.get(platform)
                if not checker:
                    return PhoneCheckResult(
                        platform=platform,
                        status=VerificationStatus.ERROR,
                        exists=False,
                        error=f"Vérificateur {platform} non disponible"
                    )
                
                try:
                    return await checker.check(phone, country_code)
                except Exception as e:
                    logger.error(f"Erreur vérificateur {platform}: {e}")
                    return PhoneCheckResult(
                        platform=platform,
                        status=VerificationStatus.ERROR,
                        exists=False,
                        error=str(e)
                    )
        
        # Lance toutes les vérifications en parallèle
        tasks = [check_with_semaphore(platform) for platform in platforms]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtre les résultats valides
        valid_results = []
        for result in results:
            if isinstance(result, PhoneCheckResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception lors de la vérification: {result}")
                # Crée un résultat d'erreur
                valid_results.append(PhoneCheckResult(
                    platform="unknown",
                    status=VerificationStatus.ERROR,
                    exists=False,
                    error=str(result)
                ))
        
        return valid_results
    
    async def check_multiple_numbers(
        self,
        numbers: List[Dict[str, str]],
        platforms: Optional[List[str]] = None
    ) -> List[PhoneCheckResponse]:
        """Vérifie plusieurs numéros en parallèle.
        
        Args:
            numbers: Liste de dict avec 'phone' et 'country_code'
            platforms: Plateformes à vérifier
            
        Returns:
            Liste des PhoneCheckResponse
        """
        tasks = []
        for number_info in numbers:
            task = self.check_number(
                phone=number_info['phone'],
                country_code=number_info['country_code'],
                platforms=platforms
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def invalidate_cache(self, phone: str, country_code: str):
        """Invalide le cache pour un numéro spécifique."""
        if self.use_cache:
            await self.cache.invalidate(phone, country_code)
            logger.debug(f"Cache invalidé pour +{country_code}{phone}")
    
    async def clear_cache(self):
        """Vide complètement le cache."""
        if self.use_cache:
            await self.cache.clear_all()
            logger.info("Cache complètement vidé")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation."""
        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
            ),
            'success_rate': (
                self.stats['successful_checks'] / max(1, self.stats['total_checks'])
            ),
            'available_platforms': list(self.checkers.keys()),
            'cache_enabled': self.use_cache
        }
    
    def get_available_platforms(self) -> List[str]:
        """Retourne la liste des plateformes disponibles."""
        return list(self.checkers.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Effectue un contrôle de santé des composants."""
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # Teste chaque plateforme avec un numéro fictif
        test_results = await asyncio.gather(
            *[
                self._test_platform_health(platform, checker)
                for platform, checker in self.checkers.items()
            ],
            return_exceptions=True
        )
        
        for i, (platform, result) in enumerate(zip(self.checkers.keys(), test_results)):
            if isinstance(result, Exception):
                health['components'][platform] = {
                    'status': 'unhealthy',
                    'error': str(result)
                }
                health['status'] = 'degraded'
            else:
                health['components'][platform] = result
        
        # Teste le cache
        if self.use_cache:
            try:
                await self.cache.get('test', '1')
                health['components']['cache'] = {'status': 'healthy'}
            except Exception as e:
                health['components']['cache'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health['status'] = 'degraded'
        
        return health
    
    async def _test_platform_health(self, platform: str, checker) -> Dict[str, Any]:
        """Teste la santé d'une plateforme spécifique."""
        try:
            # Test avec un numéro manifestement inexistant
            test_result = await checker.check('00000000', '999')
            return {
                'status': 'healthy' if not test_result.error else 'degraded',
                'response_time': test_result.response_time,
                'last_check': test_result.timestamp.isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def close(self):
        """Ferme proprement toutes les connexions."""
        try:
            # Ferme les vérificateurs
            for checker in self.checkers.values():
                if hasattr(checker, 'close'):
                    await checker.close()
            
            # Ferme le client HTTP principal
            await self.client.aclose()
            
            logger.info("PhoneChecker fermé proprement")
            
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture: {e}")
    
    async def __aenter__(self):
        """Support pour les context managers."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support pour les context managers."""
        await self.close()
