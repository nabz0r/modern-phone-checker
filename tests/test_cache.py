"""Tests pour le système de cache."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from phone_checker.cache import CacheManager
from phone_checker.models import PhoneCheckResult, VerificationStatus

class TestCacheManager:
    """Tests pour le gestionnaire de cache."""
    
    @pytest.fixture
    async def cache_manager(self):
        """Fixture pour créer un gestionnaire de cache temporaire."""
        temp_dir = tempfile.mkdtemp()
        cache = CacheManager(cache_dir=temp_dir, expire_after=3600)
        await cache.initialize()
        yield cache
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_manager):
        """Test de l'initialisation du cache."""
        assert cache_manager.cache_dir.exists()
        assert cache_manager.stats['entries_count'] == 0
        assert cache_manager.stats['size_bytes'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager):
        """Test de stockage et récupération du cache."""
        phone = "612345678"
        country_code = "33"
        
        # Données de test
        test_results = {
            "whatsapp": {
                "platform": "whatsapp",
                "status": "exists",
                "exists": True,
                "timestamp": datetime.now().isoformat(),
                "response_time": 150.0
            }
        }
        
        # Stockage
        await cache_manager.set(phone, country_code, test_results)
        assert cache_manager.stats['entries_count'] == 1
        assert cache_manager.stats['size_bytes'] > 0
        
        # Récupération
        cached_data = await cache_manager.get(phone, country_code)
        assert cached_data is not None
        assert 'results' in cached_data
        assert 'freshness_score' in cached_data
        assert cached_data['results'] == test_results
        assert 0.0 <= cached_data['freshness_score'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_manager):
        """Test de cache miss."""
        result = await cache_manager.get("nonexistent", "99")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test de l'expiration du cache."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Cache avec expiration très courte
            cache = CacheManager(cache_dir=temp_dir, expire_after=1)
            await cache.initialize()
            
            # Stockage
            test_results = {"test": "data"}
            await cache.set("test", "1", test_results)
            
            # Vérification immédiate - doit fonctionner
            cached_data = await cache.get("test", "1")
            assert cached_data is not None
            
            # Attendre expiration
            import asyncio
            await asyncio.sleep(1.1)
            
            # Vérification après expiration - doit retourner None
            cached_data = await cache.get("test", "1")
            assert cached_data is None
            
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_manager):
        """Test d'invalidation du cache."""
        phone = "612345678"
        country_code = "33"
        test_results = {"test": "data"}
        
        # Stockage
        await cache_manager.set(phone, country_code, test_results)
        assert await cache_manager.get(phone, country_code) is not None
        
        # Invalidation
        await cache_manager.invalidate(phone, country_code)
        assert await cache_manager.get(phone, country_code) is None
        assert cache_manager.stats['entries_count'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_clear_all(self, cache_manager):
        """Test de vidage complet du cache."""
        # Stockage de plusieurs entrées
        for i in range(3):
            await cache_manager.set(f"phone{i}", "33", {"test": f"data{i}"})
        
        assert cache_manager.stats['entries_count'] == 3
        
        # Vidage complet
        await cache_manager.clear_all()
        assert cache_manager.stats['entries_count'] == 0
        assert cache_manager.stats['size_bytes'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_size_limit(self):
        """Test de la limite de taille du cache."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Cache avec limite très petite (1KB)
            cache = CacheManager(cache_dir=temp_dir, max_size_mb=0.001)
            await cache.initialize()
            
            # Stockage de données qui dépassent la limite
            large_data = {"large_field": "x" * 1000}  # ~1KB de données
            
            await cache.set("test1", "1", large_data)
            await cache.set("test2", "1", large_data)
            await cache.set("test3", "1", large_data)  # Devrait déclencher une éviction
            
            # Vérification qu'une éviction a eu lieu
            assert cache.stats['evictions'] > 0
            assert cache.stats['entries_count'] < 3
            
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_manager):
        """Test des statistiques du cache."""
        initial_stats = cache_manager.get_stats()
        assert initial_stats['hit_rate'] == 0.0
        assert initial_stats['entries_count'] == 0
        
        # Stockage et accès
        await cache_manager.set("test", "1", {"data": "test"})
        await cache_manager.get("test", "1")  # Hit
        await cache_manager.get("nonexistent", "1")  # Miss
        
        stats = cache_manager.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5
        assert stats['entries_count'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_info(self, cache_manager):
        """Test des informations détaillées du cache."""
        # Stockage de test
        await cache_manager.set("test", "33", {"platform": "test"})
        
        info = await cache_manager.get_cache_info()
        
        assert 'stats' in info
        assert 'config' in info
        assert 'entries' in info
        assert len(info['entries']) > 0
        
        entry = info['entries'][0]
        assert 'key' in entry
        assert 'timestamp' in entry
        assert 'freshness' in entry
        assert 'platforms' in entry

if __name__ == "__main__":
    pytest.main([__file__])
