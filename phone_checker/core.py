"""Module principal du vérificateur de numéros avec gestion du cache.

Ce module coordonne les différents vérificateurs de plateformes et gère
la logique centrale de l'application, y compris le système de cache.
"""

import asyncio
from typing import List, Optional, Dict, Any
import httpx
from datetime import datetime

from .models import PhoneCheckResult
from .platforms import AVAILABLE_CHECKERS, DEFAULT_PLATFORMS
from .cache import CacheManager
from .utils import validate_phone_number, clean_phone_number

class PhoneChecker:
    """Classe principale pour la vérification des numéros de téléphone."""
    
    def __init__(
        self,
        platforms: Optional[List[str]] = None,
        proxy_url: Optional[str] = None,
        use_cache: bool = True,
        cache_expire: int = 3600
    ):
        """Initialise le vérificateur avec les options spécifiées.
        
        Args:
            platforms: Liste des plateformes à vérifier (toutes si None)
            proxy_url: URL du proxy à utiliser (optionnel)
            use_cache: Activer le système de cache
            cache_expire: Durée de validité du cache en secondes
        """
        self.client = httpx.AsyncClient(proxies=proxy_url)
        self.checkers: Dict[str, Any] = {}
        self.use_cache = use_cache
        
        if use_cache:
            self.cache = CacheManager(expire_after=cache_expire)
        
        self._initialize_checkers(platforms or DEFAULT_PLATFORMS)
    
    async def initialize(self):
        """Initialise les composants asynchrones comme le cache."""
        if self.use_cache:
            await self.cache.initialize()
    
    def _initialize_checkers(self, platforms: List[str]):
        """Initialise les vérificateurs pour les plateformes sélectionnées."""
        for platform in platforms:
            if platform in AVAILABLE_CHECKERS:
                checker_class = AVAILABLE_CHECKERS[platform]
                self.checkers[platform] = checker_class(self.client)
    
    async def check_number(
        self,
        phone: str,
        country_code: str,
        force_refresh: bool = False
    ) -> List[PhoneCheckResult]:
        """Vérifie un numéro sur toutes les plateformes configurées.
        
        Args:
            phone: Numéro de téléphone sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
            force_refresh: Force une nouvelle vérification même si en cache
            
        Returns:
            Liste des résultats pour chaque plateforme
        """
        # Validation et nettoyage du numéro
        if not validate_phone_number(phone, country_code):
            raise ValueError(f"Numéro invalide: +{country_code}{phone}")
        
        clean_number = clean_phone_number(phone)
        
        # Vérifie d'abord le cache si activé
        if self.use_cache and not force_refresh:
            cached_results = await self.cache.get(clean_number, country_code)
            if cached_results:
                # Ajoute l'information de cache aux métadonnées
                for result in cached_results['results'].values():
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata['cached'] = True
                    result.metadata['freshness_score'] = cached_results['freshness_score']
                return list(cached_results['results'].values())
        
        # Si pas en cache ou force_refresh, fait les vérifications
        tasks = [
            checker.check(clean_number, country_code)
            for checker in self.checkers.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtre et organise les résultats
        valid_results = [
            r for r in results
            if isinstance(r, PhoneCheckResult)
        ]
        
        # Met en cache les nouveaux résultats
        if self.use_cache:
            results_dict = {
                r.platform: r for r in valid_results
            }
            await self.cache.set(clean_number, country_code, results_dict)
        
        return valid_results
    
    async def invalidate_cache(self, phone: str, country_code: str):
        """Invalide le cache pour un numéro spécifique."""
        if self.use_cache:
            await self.cache.invalidate(phone, country_code)
    
    async def close(self):
        """Ferme proprement les connexions HTTP."""
        await self.client.aclose()
