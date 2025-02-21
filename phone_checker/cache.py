"""Système de cache intelligent pour les vérifications de numéros.

Ce module permet de stocker temporairement les résultats des vérifications
pour éviter de faire trop de requêtes aux APIs. Il utilise un système de
score de fraîcheur pour déterminer quand renouveler les données.
"""

from datetime import datetime, timedelta
import json
from typing import Optional, Dict, Any
from pathlib import Path
import aiofiles
import aiofiles.os
from .models import PhoneCheckResult

class CacheManager:
    def __init__(self, cache_dir: str = '.cache', expire_after: int = 3600):
        """Initialise le gestionnaire de cache.
        
        Args:
            cache_dir: Répertoire où stocker les fichiers de cache
            expire_after: Durée de validité du cache en secondes (1h par défaut)
        """
        self.cache_dir = Path(cache_dir)
        self.expire_after = expire_after
        self.cache_data: Dict[str, Any] = {}
        
    async def initialize(self):
        """Crée le répertoire de cache si nécessaire et charge les données existantes."""
        await self._ensure_cache_dir()
        await self._load_cache()
    
    async def _ensure_cache_dir(self):
        """Crée le répertoire de cache s'il n'existe pas."""
        if not self.cache_dir.exists():
            await aiofiles.os.makedirs(str(self.cache_dir))
    
    def _get_cache_file(self, phone: str, country_code: str) -> Path:
        """Génère le chemin du fichier de cache pour un numéro."""
        cache_key = f"{country_code}_{phone}"
        return self.cache_dir / f"{cache_key}.json"
    
    async def _load_cache(self):
        """Charge les données de cache existantes."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                async with aiofiles.open(cache_file, mode='r') as f:
                    content = await f.read()
                    self.cache_data[cache_file.stem] = json.loads(content)
        except Exception as e:
            print(f"Erreur lors du chargement du cache: {e}")
    
    def _calculate_freshness_score(self, timestamp: datetime) -> float:
        """Calcule un score de fraîcheur pour les données en cache.
        
        Le score varie de 1.0 (très récent) à 0.0 (expiré).
        """
        age = (datetime.now() - timestamp).total_seconds()
        return max(0.0, 1.0 - (age / self.expire_after))
    
    async def get(self, phone: str, country_code: str) -> Optional[Dict[str, PhoneCheckResult]]:
        """Récupère les résultats en cache pour un numéro.
        
        Returns:
            Résultats en cache si valides, None sinon
        """
        cache_key = f"{country_code}_{phone}"
        cached_data = self.cache_data.get(cache_key)
        
        if not cached_data:
            return None
            
        # Vérifie la fraîcheur des données
        timestamp = datetime.fromisoformat(cached_data['timestamp'])
        freshness = self._calculate_freshness_score(timestamp)
        
        if freshness <= 0:
            # Données expirées, on les supprime
            await self.invalidate(phone, country_code)
            return None
            
        # Ajoute le score de fraîcheur aux métadonnées
        cached_data['freshness_score'] = freshness
        return cached_data
    
    async def set(self, phone: str, country_code: str, results: Dict[str, PhoneCheckResult]):
        """Stocke les résultats en cache pour un numéro."""
        cache_key = f"{country_code}_{phone}"
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'results': results
        }
        
        # Sauvegarde en mémoire
        self.cache_data[cache_key] = cache_data
        
        # Sauvegarde sur disque
        cache_file = self._get_cache_file(phone, country_code)
        async with aiofiles.open(cache_file, mode='w') as f:
            await f.write(json.dumps(cache_data, indent=2))
    
    async def invalidate(self, phone: str, country_code: str):
        """Invalide le cache pour un numéro spécifique."""
        cache_key = f"{country_code}_{phone}"
        self.cache_data.pop(cache_key, None)
        
        cache_file = self._get_cache_file(phone, country_code)
        if cache_file.exists():
            await aiofiles.os.remove(str(cache_file))
