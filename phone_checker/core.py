"""Module principal du vérificateur de numéros.

Ce module coordonne les différents vérificateurs de plateformes
et gère la logique centrale de l'application.
"""

import asyncio
from typing import List, Optional, Dict, Type
import httpx
from .models import PhoneCheckResult
from .platforms import AVAILABLE_CHECKERS

class PhoneChecker:
    """Classe principale pour la vérification des numéros de téléphone."""
    
    def __init__(self, platforms: Optional[List[str]] = None, proxy_url: Optional[str] = None):
        """Initialise le vérificateur avec les plateformes souhaitées.
        
        Args:
            platforms: Liste des plateformes à vérifier (toutes si None)
            proxy_url: URL du proxy à utiliser (optionnel)
        """
        self.client = httpx.AsyncClient(proxies=proxy_url)
        self.checkers: Dict[str, Type] = {}
        self._initialize_checkers(platforms)
    
    def _initialize_checkers(self, platforms: Optional[List[str]] = None):
        """Initialise les vérificateurs pour les plateformes sélectionnées."""
        available = AVAILABLE_CHECKERS.keys() if platforms is None else platforms
        for platform in available:
            if platform in AVAILABLE_CHECKERS:
                checker_class = AVAILABLE_CHECKERS[platform]
                self.checkers[platform] = checker_class(self.client)
    
    async def check_number(self, phone: str, country_code: str) -> List[PhoneCheckResult]:
        """Vérifie un numéro sur toutes les plateformes configurées.
        
        Args:
            phone: Numéro de téléphone sans l'indicatif pays
            country_code: Indicatif pays (ex: '33' pour la France)
            
        Returns:
            Liste des résultats pour chaque plateforme
        """
        tasks = [
            checker.check(phone, country_code)
            for checker in self.checkers.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, PhoneCheckResult)]
    
    async def close(self):
        """Ferme proprement les connexions HTTP."""
        await self.client.aclose()
