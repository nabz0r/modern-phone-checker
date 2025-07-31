"""Tests d'intégration pour Modern Phone Checker."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from phone_checker import PhoneChecker
from phone_checker.models import VerificationStatus
from phone_checker.platforms.base import BaseChecker

class MockChecker(BaseChecker):
    """Vérificateur mock pour les tests d'intégration."""
    
    def __init__(self, client=None, should_exist=False, should_error=False):
        super().__init__(client, "mock")
        self.should_exist = should_exist
        self.should_error = should_error
        self.call_count = 0
    
    async def check(self, phone: str, country_code: str):
        """Simule une vérification."""
        self.call_count += 1
        
        if self.should_error:
            return self._create_error_result("Mock error for testing")
        
        return self._create_success_result(
            exists=self.should_exist,
            response_time=100.0,
            metadata={"mock": True, "call_count": self.call_count}
        )

@pytest.fixture
async def temp_cache_dir():
    """Fixture pour créer un répertoire de cache temporaire."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
async def mock_phone_checker(temp_cache_dir):
    """Fixture pour créer un PhoneChecker avec des vérificateurs mock."""
    checker = PhoneChecker(
        platforms=[],  # Pas de plateformes par défaut
        use_cache=True
    )
    
    # Remplace le répertoire de cache
    if checker.use_cache:
        checker.cache.cache_dir = Path(temp_cache_dir)
        await checker.cache.initialize()
    
    # Ajoute des vérificateurs mock
    checker.checkers = {
        'mock_success': MockChecker(should_exist=True),
        'mock_failure': MockChecker(should_exist=False),
        'mock_error': MockChecker(should_error=True)
    }
    
    yield checker
    await checker.close()

class TestIntegrationPhoneChecker:
    """Tests d'intégration pour PhoneChecker."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_phone_checker):
        """Test du workflow complet de vérification."""
        phone = "123456789"
        country_code = "33"
        
        # Première vérification
        response = await mock_phone_checker.check_number(phone, country_code)
        
        assert len(response.results) == 3
        assert response.successful_checks == 2  # mock_success et mock_failure
        assert response.failed_checks == 1      # mock_error
        assert len(response.platforms_found) == 1  # mock_success
        assert len(response.platforms_not_found) == 1  # mock_failure
        assert len(response.platforms_error) == 1  # mock_error
        
        # Vérification des résultats individuels
        success_result = response.get_result_by_platform('mock_success')
        assert success_result.exists == True
        assert success_result.status == VerificationStatus.EXISTS
        
        failure_result = response.get_result_by_platform('mock_failure')
        assert failure_result.exists == False
        assert failure_result.status == VerificationStatus.NOT_EXISTS
        
        error_result = response.get_result_by_platform('mock_error')
        assert error_result.exists == False
        assert error_result.status == VerificationStatus.ERROR
        assert error_result.error == "Mock error for testing"
    
    @pytest.mark.asyncio
    async def test_cache_behavior(self, mock_phone_checker):
        """Test du comportement du cache."""
        phone = "123456789"
        country_code = "33"
        
        # Première vérification (mise en cache)
        response1 = await mock_phone_checker.check_number(phone, country_code)
        
        # Vérification que les appels ont été faits
        assert mock_phone_checker.checkers['mock_success'].call_count == 1
        assert mock_phone_checker.checkers['mock_failure'].call_count == 1
        assert mock_phone_checker.checkers['mock_error'].call_count == 1
        
        # Deuxième vérification (depuis le cache)
        response2 = await mock_phone_checker.check_number(phone, country_code)
        
        # Les compteurs ne doivent pas avoir changé (cache hit)
        assert mock_phone_checker.checkers['mock_success'].call_count == 1
        assert mock_phone_checker.checkers['mock_failure'].call_count == 1
        assert mock_phone_checker.checkers['mock_error'].call_count == 1
        
        # Vérification que les résultats sont marqués comme mis en cache
        for result in response2.results:
            if result.is_successful:  # Les erreurs ne sont pas mises en cache
                assert result.is_cached == True
        
        # Force refresh doit refaire les appels
        response3 = await mock_phone_checker.check_number(
            phone, country_code, force_refresh=True
        )
        
        assert mock_phone_checker.checkers['mock_success'].call_count == 2
        assert mock_phone_checker.checkers['mock_failure'].call_count == 2
        assert mock_phone_checker.checkers['mock_error'].call_count == 2
    
    @pytest.mark.asyncio
    async def test_multiple_numbers(self, mock_phone_checker):
        """Test de vérification de plusieurs numéros."""
        numbers = [
            {"phone": "123456789", "country_code": "33"},
            {"phone": "987654321", "country_code": "33"},
            {"phone": "555123456", "country_code": "1"}
        ]
        
        responses = await mock_phone_checker.check_multiple_numbers(numbers)
        
        assert len(responses) == 3
        
        for response in responses:
            assert len(response.results) == 3
            assert response.successful_checks == 2
            assert response.failed_checks == 1
    
    @pytest.mark.asyncio
    async def test_platform_selection(self, mock_phone_checker):
        """Test de sélection des plateformes."""
        phone = "123456789"
        country_code = "33"
        
        # Vérification avec une seule plateforme
        response = await mock_phone_checker.check_number(
            phone, country_code, platforms=['mock_success']
        )
        
        assert len(response.results) == 1
        assert response.results[0].platform == 'mock_success'
        assert response.results[0].exists == True
        
        # Vérification avec deux plateformes
        response = await mock_phone_checker.check_number(
            phone, country_code, platforms=['mock_success', 'mock_error']
        )
        
        assert len(response.results) == 2
        assert response.successful_checks == 1
        assert response.failed_checks == 1
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, mock_phone_checker):
        """Test du suivi des statistiques."""
        initial_stats = mock_phone_checker.get_stats()
        assert initial_stats['total_checks'] == 0
        
        # Effectue quelques vérifications
        await mock_phone_checker.check_number("123456789", "33")
        await mock_phone_checker.check_number("987654321", "33")
        
        final_stats = mock_phone_checker.get_stats()
        assert final_stats['total_checks'] == 6  # 2 numéros × 3 plateformes
        assert final_stats['successful_checks'] == 4  # 2 numéros × 2 plateformes réussies
        assert final_stats['failed_checks'] == 2  # 2 numéros × 1 plateforme échouée
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_phone_checker):
        """Test du health check."""
        health = await mock_phone_checker.health_check()
        
        assert 'status' in health
        assert 'timestamp' in health
        assert 'components' in health
        
        # Toutes les plateformes mock devraient être healthy
        for platform in ['mock_success', 'mock_failure', 'mock_error']:
            assert platform in health['components']
            component_health = health['components'][platform]
            assert 'status' in component_health
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, mock_phone_checker):
        """Test d'invalidation du cache."""
        phone = "123456789"
        country_code = "33"
        
        # Première vérification (mise en cache)
        await mock_phone_checker.check_number(phone, country_code)
        call_count_before = mock_phone_checker.checkers['mock_success'].call_count
        
        # Deuxième vérification (depuis le cache)
        await mock_phone_checker.check_number(phone, country_code)
        assert mock_phone_checker.checkers['mock_success'].call_count == call_count_before
        
        # Invalidation du cache
        await mock_phone_checker.invalidate_cache(phone, country_code)
        
        # Troisième vérification (cache invalidé, doit refaire l'appel)
        await mock_phone_checker.check_number(phone, country_code)
        assert mock_phone_checker.checkers['mock_success'].call_count == call_count_before + 1
    
    @pytest.mark.asyncio
    async def test_context_manager(self, temp_cache_dir):
        """Test de l'utilisation comme context manager."""
        async with PhoneChecker(use_cache=False) as checker:
            # Ajoute un vérificateur mock
            checker.checkers = {'mock': MockChecker(should_exist=True)}
            
            response = await checker.check_number("123456789", "33")
            assert len(response.results) == 1
            assert response.results[0].exists == True
        
        # Le checker devrait être fermé automatiquement
        # (pas de moyen facile de tester cela avec les mocks actuels)

class TestIntegrationErrorHandling:
    """Tests d'intégration pour la gestion d'erreurs."""
    
    @pytest.mark.asyncio
    async def test_invalid_phone_number(self):
        """Test avec un numéro invalide."""
        async with PhoneChecker(use_cache=False) as checker:
            with pytest.raises(ValueError, match="Numéro invalide"):
                await checker.check_number("invalid", "33")
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_phone_checker):
        """Test de gestion des timeouts."""
        # Simule un timeout en ajoutant un délai
        class TimeoutChecker(BaseChecker):
            async def check(self, phone, country_code):
                await asyncio.sleep(0.1)  # Simule un délai
                return self._create_error_result("Timeout", VerificationStatus.TIMEOUT)
        
        mock_phone_checker.checkers['timeout_test'] = TimeoutChecker()
        
        response = await mock_phone_checker.check_number("123456789", "33")
        
        # Trouve le résultat du timeout
        timeout_result = next(
            (r for r in response.results if r.platform == 'timeout_test'),
            None
        )
        
        assert timeout_result is not None
        assert timeout_result.status == VerificationStatus.TIMEOUT
        assert timeout_result.error == "Timeout"

class TestIntegrationConcurrency:
    """Tests d'intégration pour la concurrence."""
    
    @pytest.mark.asyncio
    async def test_concurrent_checks(self, mock_phone_checker):
        """Test de vérifications concurrentes."""
        # Lance plusieurs vérifications en parallèle
        tasks = [
            mock_phone_checker.check_number(f"12345678{i}", "33")
            for i in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 5
        for response in responses:
            assert len(response.results) == 3
            assert response.successful_checks == 2
            assert response.failed_checks == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, mock_phone_checker):
        """Test d'intégration du rate limiting."""
        # Ajoute un vérificateur avec rate limiting très strict
        class RateLimitedChecker(BaseChecker):
            def __init__(self):
                super().__init__(None, "rate_limited")
                self.call_times = []
            
            async def check(self, phone, country_code):
                import time
                self.call_times.append(time.time())
                return self._create_success_result(exists=True, response_time=50.0)
        
        rate_checker = RateLimitedChecker()
        mock_phone_checker.checkers['rate_limited'] = rate_checker
        
        # Lance plusieurs vérifications rapides
        start_time = asyncio.get_event_loop().time()
        
        tasks = [
            mock_phone_checker.check_number(f"12345678{i}", "33")
            for i in range(3)
        ]
        
        await asyncio.gather(*tasks)
        
        # Vérifie que les appels ont été faits
        assert len(rate_checker.call_times) == 3
        
        # (Le rate limiting est géré au niveau des plateformes individuelles)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
