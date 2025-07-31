"""Tests pour les utilitaires de Phone Checker."""

import pytest
from phone_checker.utils import (
    clean_phone_number,
    validate_phone_number,
    format_phone_number,
    get_country_code_from_number,
    is_mobile_number,
    anonymize_phone_number,
    calculate_confidence_score
)

class TestPhoneNumberUtils:
    """Tests pour les utilitaires de numéros de téléphone."""
    
    def test_clean_phone_number(self):
        """Test du nettoyage des numéros."""
        # Cas normaux
        assert clean_phone_number("06 12 34 56 78") == "0612345678"
        assert clean_phone_number("06-12-34-56-78") == "0612345678"
        assert clean_phone_number("06.12.34.56.78") == "0612345678"
        assert clean_phone_number("06 12.34-56 78") == "0612345678"
        
        # Cas avec espaces et caractères spéciaux
        assert clean_phone_number("  06 12 34 56 78  ") == "0612345678"
        assert clean_phone_number("(06) 12 34 56 78") == "0612345678"
        assert clean_phone_number("+33 6 12 34 56 78") == "33612345678"
        
        # Cas vides
        assert clean_phone_number("") == ""
        assert clean_phone_number("   ") == ""
    
    def test_validate_phone_number(self):
        """Test de la validation des numéros."""
        # Numéros français valides
        assert validate_phone_number("612345678", "33") == True
        assert validate_phone_number("712345678", "33") == True
        
        # Numéros français invalides
        assert validate_phone_number("512345678", "33") == False  # Ne commence pas par 6 ou 7
        assert validate_phone_number("61234567", "33") == False   # Trop court
        assert validate_phone_number("6123456789", "33") == False # Trop long
        
        # Numéros US/Canada
        assert validate_phone_number("5551234567", "1") == True
        assert validate_phone_number("555123456", "1") == False   # Trop court
    
    def test_format_phone_number(self):
        """Test du formatage des numéros."""
        # Format international
        result = format_phone_number("612345678", "33", "international")
        assert result is not None
        assert "+33" in result
        
        # Format E164
        result = format_phone_number("612345678", "33", "e164")
        assert result is not None
        assert result.startswith("+33")
        
        # Numéro invalide
        result = format_phone_number("invalid", "33", "international")
        assert result is None
    
    def test_get_country_code_from_number(self):
        """Test d'extraction du code pays."""
        assert get_country_code_from_number("+33612345678") == "33"
        assert get_country_code_from_number("+15551234567") == "1"
        assert get_country_code_from_number("invalid") is None
    
    def test_is_mobile_number(self):
        """Test de détection des mobiles."""
        # Mobile français
        assert is_mobile_number("612345678", "33") == True
        assert is_mobile_number("712345678", "33") == True
        
        # Numéro invalide
        assert is_mobile_number("invalid", "33") == False
    
    def test_anonymize_phone_number(self):
        """Test d'anonymisation des numéros."""
        result = anonymize_phone_number("612345678", "33")
        assert "+33" in result
        assert "612345678" not in result  # Le numéro complet ne doit pas apparaître
        assert "X" in result  # Doit contenir des X pour masquer
    
    def test_calculate_confidence_score(self):
        """Test du calcul de score de confiance."""
        # Score parfait
        score = calculate_confidence_score(200, 0.5, 1.0)
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Devrait être élevé
        
        # Score faible
        score = calculate_confidence_score(500, 10.0, 0.3)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Devrait être faible
        
        # Score moyen
        score = calculate_confidence_score(200, 2.0, 0.7)
        assert 0.0 <= score <= 1.0

class TestRateLimiter:
    """Tests pour le rate limiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basique du rate limiter."""
        from phone_checker.utils import RateLimiter
        import time
        
        limiter = RateLimiter(calls=2, period=1)
        
        # Premier appel - doit passer immédiatement
        start = time.time()
        await limiter.acquire()
        assert time.time() - start < 0.1
        
        # Deuxième appel - doit passer immédiatement
        start = time.time()
        await limiter.acquire()
        assert time.time() - start < 0.1
        
        # Troisième appel - doit attendre
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start
        assert elapsed >= 0.5  # Doit attendre au moins 0.5s
    
    @pytest.mark.asyncio
    async def test_rate_limit_decorator(self):
        """Test du décorateur de rate limiting."""
        from phone_checker.utils import rate_limit
        import time
        
        call_times = []
        
        @rate_limit(calls=2, period=1)
        async def test_function():
            call_times.append(time.time())
            return "ok"
        
        # Première vague d'appels
        await test_function()
        await test_function()
        
        # Troisième appel doit être retardé
        start = time.time()
        await test_function()
        
        assert len(call_times) == 3
        # Le troisième appel doit être décalé d'au moins 0.5s
        assert call_times[2] - call_times[1] >= 0.5

if __name__ == "__main__":
    pytest.main([__file__])
