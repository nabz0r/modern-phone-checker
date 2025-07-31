"""Système de cache intelligent pour les vérifications de numéros.

Ce module permet de stocker temporairement les résultats des vérifications
pour éviter de faire trop de requêtes aux APIs. Il utilise un système de
score de fraîcheur et de gestion de la taille du cache.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import aiofiles
import aiofiles.os
from .models import PhoneCheckResult
from .logging import get_logger

logger = get_logger('cache')

class CacheManager:
    """Gestionnaire de cache intelligent avec gestion de la taille et de la fraîcheur."""
    
    def __init__(
        self, 
        cache_dir: str = '.cache', 
        expire_after: int = 3600,
        max_size_mb: int = 100
    ):
        """Initialise le gestionnaire de cache.
        
        Args:
            cache_dir: Répertoire où stocker les fichiers de cache
            expire_after: Durée de validité du cache en secondes (1h par défaut)
            max_size_mb: Taille maximale du cache en MB
        """
        self.cache_dir = Path(cache_dir)
        self.expire_after = expire_after
        self.max_size_mb = max_size_mb
        self.cache_data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        
        # Statistiques du cache
        self.stats = {
            'hits': 0,
            'misses': 0,
            'size_bytes': 0,
            'entries_count': 0,
            'evictions': 0
        }
    
    async def initialize(self):
        """Crée le répertoire de cache et charge les données existantes."""
        await self._ensure_cache_dir()
        await self._load_cache()
        await self._cleanup_expired()
        logger.info(f"Cache initialisé: {self.stats['entries_count']} entrées, {self._format_size(self.stats['size_bytes'])}")
    
    async def _ensure_cache_dir(self):
        """Crée le répertoire de cache s'il n'existe pas."""
        if not self.cache_dir.exists():
            await aiofiles.os.makedirs(str(self.cache_dir))
            logger.debug(f"Répertoire de cache créé: {self.cache_dir}")
    
    def _get_cache_file(self, phone: str, country_code: str) -> Path:
        """Génère le chemin du fichier de cache pour un numéro."""
        cache_key = f"{country_code}_{phone}"
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_cache_key(self, phone: str, country_code: str) -> str:
        """Génère une clé de cache unique."""
        return f"{country_code}_{phone}"
    
    async def _load_cache(self):
        """Charge les données de cache existantes."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            logger.debug(f"Chargement de {len(cache_files)} fichiers de cache")
            
            for cache_file in cache_files:
                try:
                    async with aiofiles.open(cache_file, mode='r', encoding='utf-8') as f:
                        content = await f.read()
                        data = json.loads(content)
                        
                        # Vérifie la structure des données
                        if self._validate_cache_data(data):
                            self.cache_data[cache_file.stem] = data
                            self.stats['size_bytes'] += len(content.encode('utf-8'))
                        else:
                            logger.warning(f"Fichier de cache invalide: {cache_file}")
                            # Supprime le fichier invalide
                            await aiofiles.os.remove(str(cache_file))
                            
                except Exception as e:
                    logger.error(f"Erreur lors du chargement de {cache_file}: {e}")
                    try:
                        await aiofiles.os.remove(str(cache_file))
                    except:
                        pass
            
            self.stats['entries_count'] = len(self.cache_data)
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du cache: {e}")
    
    def _validate_cache_data(self, data: Dict[str, Any]) -> bool:
        """Valide la structure des données de cache."""
        required_fields = ['timestamp', 'results']
        return all(field in data for field in required_fields)
    
    def _calculate_freshness_score(self, timestamp: datetime) -> float:
        """Calcule un score de fraîcheur pour les données en cache.
        
        Le score varie de 1.0 (très récent) à 0.0 (expiré).
        """
        age = (datetime.now() - timestamp).total_seconds()
        return max(0.0, 1.0 - (age / self.expire_after))
    
    async def get(self, phone: str, country_code: str) -> Optional[Dict[str, Any]]:
        """Récupère les résultats en cache pour un numéro.
        
        Returns:
            Résultats en cache si valides, None sinon
        """
        async with self._lock:
            cache_key = self._get_cache_key(phone, country_code)
            cached_data = self.cache_data.get(cache_key)
            
            if not cached_data:
                self.stats['misses'] += 1
                return None
            
            # Vérifie la fraîcheur des données
            timestamp = datetime.fromisoformat(cached_data['timestamp'])
            freshness = self._calculate_freshness_score(timestamp)
            
            if freshness <= 0:
                # Données expirées, on les supprime
                await self._remove_entry(cache_key)
                self.stats['misses'] += 1
                logger.debug(f"Entrée de cache expirée supprimée: {cache_key}")
                return None
            
            # Hit de cache
            self.stats['hits'] += 1
            cached_data['freshness_score'] = freshness
            logger.debug(f"Cache hit: {cache_key} (fraîcheur: {freshness:.2f})")
            return cached_data
    
    async def set(self, phone: str, country_code: str, results: Dict[str, Any]):
        """Stocke les résultats en cache pour un numéro."""
        async with self._lock:
            cache_key = self._get_cache_key(phone, country_code)
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'phone': phone,
                'country_code': country_code
            }
            
            # Calcule la taille des nouvelles données
            data_str = json.dumps(cache_data, indent=2)
            data_size = len(data_str.encode('utf-8'))
            
            # Vérifie si on dépasse la limite de taille
            if self.stats['size_bytes'] + data_size > self.max_size_mb * 1024 * 1024:
                await self._evict_old_entries()
            
            # Sauvegarde en mémoire
            old_size = 0
            if cache_key in self.cache_data:
                # Mise à jour d'une entrée existante
                old_entry = self.cache_data[cache_key]
                old_size = len(json.dumps(old_entry).encode('utf-8'))
            else:
                self.stats['entries_count'] += 1
            
            self.cache_data[cache_key] = cache_data
            self.stats['size_bytes'] = self.stats['size_bytes'] - old_size + data_size
            
            # Sauvegarde sur disque
            cache_file = self._get_cache_file(phone, country_code)
            try:
                async with aiofiles.open(cache_file, mode='w', encoding='utf-8') as f:
                    await f.write(data_str)
                
                logger.debug(f"Entrée sauvegardée en cache: {cache_key} ({self._format_size(data_size)})")
                
            except Exception as e:
                # En cas d'erreur d'écriture, on retire l'entrée de la mémoire
                if cache_key in self.cache_data:
                    del self.cache_data[cache_key]
                    self.stats['entries_count'] -= 1
                    self.stats['size_bytes'] -= data_size
                logger.error(f"Erreur lors de la sauvegarde en cache: {e}")
    
    async def invalidate(self, phone: str, country_code: str):
        """Invalide le cache pour un numéro spécifique."""
        async with self._lock:
            cache_key = self._get_cache_key(phone, country_code)
            await self._remove_entry(cache_key)
            logger.debug(f"Cache invalidé: {cache_key}")
    
    async def _remove_entry(self, cache_key: str):
        """Supprime une entrée du cache (mémoire et disque)."""
        if cache_key in self.cache_data:
            # Calcule la taille de l'entrée
            entry_size = len(json.dumps(self.cache_data[cache_key]).encode('utf-8'))
            
            # Supprime de la mémoire
            del self.cache_data[cache_key]
            self.stats['entries_count'] -= 1
            self.stats['size_bytes'] -= entry_size
            
            # Supprime du disque
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    await aiofiles.os.remove(str(cache_file))
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression du fichier de cache: {e}")
    
    async def _evict_old_entries(self):
        """Supprime les entrées les plus anciennes pour libérer de l'espace."""
        if not self.cache_data:
            return
        
        # Trie les entrées par âge (plus anciennes en premier)
        entries_by_age = []
        for cache_key, data in self.cache_data.items():
            timestamp = datetime.fromisoformat(data['timestamp'])
            entries_by_age.append((timestamp, cache_key))
        
        entries_by_age.sort(key=lambda x: x[0])
        
        # Supprime les entrées jusqu'à atteindre 80% de la limite
        target_size = self.max_size_mb * 1024 * 1024 * 0.8
        
        for timestamp, cache_key in entries_by_age:
            if self.stats['size_bytes'] <= target_size:
                break
            
            await self._remove_entry(cache_key)
            self.stats['evictions'] += 1
        
        logger.info(f"Éviction terminée: {self.stats['evictions']} entrées supprimées")
    
    async def _cleanup_expired(self):
        """Nettoie les entrées expirées au démarrage."""
        expired_keys = []
        current_time = datetime.now()
        
        for cache_key, data in self.cache_data.items():
            timestamp = datetime.fromisoformat(data['timestamp'])
            if (current_time - timestamp).total_seconds() > self.expire_after:
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            await self._remove_entry(cache_key)
        
        if expired_keys:
            logger.info(f"Nettoyage initial: {len(expired_keys)} entrées expirées supprimées")
    
    async def clear_all(self):
        """Vide complètement le cache."""
        async with self._lock:
            # Supprime tous les fichiers
            cache_files = list(self.cache_dir.glob("*.json"))
            for cache_file in cache_files:
                try:
                    await aiofiles.os.remove(str(cache_file))
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de {cache_file}: {e}")
            
            # Remet à zéro les données en mémoire
            self.cache_data.clear()
            self.stats['entries_count'] = 0
            self.stats['size_bytes'] = 0
            
            logger.info("Cache complètement vidé")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache."""
        hit_rate = 0.0
        total_requests = self.stats['hits'] + self.stats['misses']
        if total_requests > 0:
            hit_rate = self.stats['hits'] / total_requests
        
        return {
            **self.stats,
            'hit_rate': hit_rate,
            'size_formatted': self._format_size(self.stats['size_bytes']),
            'max_size_formatted': self._format_size(self.max_size_mb * 1024 * 1024),
            'usage_percent': (self.stats['size_bytes'] / (self.max_size_mb * 1024 * 1024)) * 100
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Formate une taille en bytes de manière lisible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Retourne des informations détaillées sur le cache."""
        info = {
            'stats': self.get_stats(),
            'config': {
                'cache_dir': str(self.cache_dir),
                'expire_after': self.expire_after,
                'max_size_mb': self.max_size_mb
            },
            'entries': []
        }
        
        # Ajoute des informations sur chaque entrée
        for cache_key, data in list(self.cache_data.items())[:10]:  # Limite à 10 entrées
            timestamp = datetime.fromisoformat(data['timestamp'])
            freshness = self._calculate_freshness_score(timestamp)
            
            info['entries'].append({
                'key': cache_key,
                'timestamp': data['timestamp'],
                'freshness': freshness,
                'platforms': list(data.get('results', {}).keys()),
                'size': len(json.dumps(data).encode('utf-8'))
            })
        
        return info
