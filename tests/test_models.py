"""Tests pour les modèles de données."""

import pytest
from datetime import datetime
from phone_checker.models import (
    PhoneCheckResult,
    PhoneCheckRequest,
    PhoneCheckResponse,
    VerificationStatus
)

class TestPhoneCheckResult:
    """Tests pour PhoneCheckResult."""
    
    def test_phone_check_result_creation(self):
        """Test de création d'un PhoneCheckResult."""
        result = PhoneCheckResult(
            platform="whatsapp",
            status=VerificationStatus.EXISTS,
            exists=True,
            username="testuser",
            confidence_score=0.95,
            response_time=150.5
        )
        
        assert result.platform == "whatsapp"
        assert result.status == VerificationStatus.EXISTS
        assert result.exists == True
        assert result.username == "testuser"
        assert result.confidence_score == 0.95
        assert result.response_time == 150.5
        assert result.is_successful == True
        assert result.is_cached == False
        assert isinstance(result.timestamp, datetime)
    
    def test_phone_check_result_status_consistency(self):
        """Test de la cohérence entre status et exists."""
        # Test EXISTS -> exists=True
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.EXISTS
        )
        assert result.exists == True
        
        # Test NOT_EXISTS -> exists=False
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.NOT_EXISTS
        )
        assert result.exists == False
        
        # Test ERROR -> exists=False
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.ERROR,
            error="Test error"
        )
        assert result.exists == False
    
    def test_phone_check_result_is_successful(self):
        """Test de la propriété is_successful."""
        # Succès
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.EXISTS
        )
        assert result.is_successful == True
        
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.NOT_EXISTS
        )
        assert result.is_successful == True
        
        # Échec
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.ERROR
        )
        assert result.is_successful == False
        
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.TIMEOUT
        )
        assert result.is_successful == False
    
    def test_phone_check_result_is_cached(self):
        """Test de la propriété is_cached."""
        # Non mis en cache
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.EXISTS
        )
        assert result.is_cached == False
        
        # Mis en cache
        result = PhoneCheckResult(
            platform="test",
            status=VerificationStatus.EXISTS,
            metadata={"cached": True}
        )
        assert result.is_cached == True
    
    def test_phone_check_result_to_dict(self):
        """Test de conversion en dictionnaire."""
        timestamp = datetime.now()
        result = PhoneCheckResult(
            platform="whatsapp",
            status=VerificationStatus.EXISTS,
            exists=True,
            username="testuser",
            confidence_score=0.95,
            metadata={"test": "value"},
            timestamp=timestamp,
            response_time=150.5
        )
        
        data = result.to_dict()
        
        assert data['platform'] == "whatsapp"
        assert data['status'] == "exists"
        assert data['exists'] == True
        assert data['username'] == "testuser"
        assert data['confidence_score'] == 0.95
        assert data['metadata'] == {"test": "value"}
        assert data['timestamp'] == timestamp.isoformat()
        assert data['response_time'] == 150.5
    
    def test_phone_check_result_from_dict(self):
        """Test de création depuis un dictionnaire."""
        timestamp = datetime.now()
        data = {
            'platform': 'telegram',
            'status': 'not_exists',
            'exists': False,
            'error': 'Not found',
            'confidence_score': 0.8,
            'metadata': {'method': 'api'},
            'timestamp': timestamp.isoformat(),
            'response_time': 200.0
        }
        
        result = PhoneCheckResult.from_dict(data)
        
        assert result.platform == 'telegram'
        assert result.status == VerificationStatus.NOT_EXISTS
        assert result.exists == False
        assert result.error == 'Not found'
        assert result.confidence_score == 0.8
        assert result.metadata == {'method': 'api'}
        assert result.timestamp == timestamp
        assert result.response_time == 200.0

class TestPhoneCheckRequest:
    """Tests pour PhoneCheckRequest."""
    
    def test_phone_check_request_creation(self):
        """Test de création d'une PhoneCheckRequest."""
        request = PhoneCheckRequest(
            phone="612345678",
            country_code="33",
            platforms=["whatsapp", "telegram"],
            force_refresh=True,
            max_concurrent_checks=2
        )
        
        assert request.phone == "612345678"
        assert request.country_code == "33"
        assert request.platforms == ["whatsapp", "telegram"]
        assert request.force_refresh == True
        assert request.max_concurrent_checks == 2
        assert request.full_number == "+33612345678"
    
    def test_phone_check_request_default_platforms(self):
        """Test des plateformes par défaut."""
        request = PhoneCheckRequest(
            phone="612345678",
            country_code="33"
        )
        
        # Devrait utiliser les plateformes par défaut
        assert len(request.platforms) > 0
        assert "whatsapp" in request.platforms

class TestPhoneCheckResponse:
    """Tests pour PhoneCheckResponse."""
    
    def test_phone_check_response_creation(self):
        """Test de création d'une PhoneCheckResponse."""
        request = PhoneCheckRequest(
            phone="612345678",
            country_code="33",
            platforms=["whatsapp", "telegram"]
        )
        
        results = [
            PhoneCheckResult(
                platform="whatsapp",
                status=VerificationStatus.EXISTS,
                exists=True
            ),
            PhoneCheckResult(
                platform="telegram",
                status=VerificationStatus.NOT_EXISTS,
                exists=False
            )
        ]
        
        response = PhoneCheckResponse(
            request=request,
            results=results,
            total_time=500.0
        )
        
        assert response.request == request
        assert response.results == results
        assert response.total_time == 500.0
        assert response.successful_checks == 2
        assert response.failed_checks == 0
        assert response.success_rate == 1.0
    
    def test_phone_check_response_statistics(self):
        """Test des statistiques de réponse."""
        request = PhoneCheckRequest(
            phone="612345678",
            country_code="33"
        )
        
        results = [
            PhoneCheckResult(
                platform="whatsapp",
                status=VerificationStatus.EXISTS,
                exists=True
            ),
            PhoneCheckResult(
                platform="telegram",
                status=VerificationStatus.NOT_EXISTS,
                exists=False
            ),
            PhoneCheckResult(
                platform="instagram",
                status=VerificationStatus.ERROR,
                exists=False,
                error="API Error"
            )
        ]
        
        response = PhoneCheckResponse(
            request=request,
            results=results
        )
        
        assert response.successful_checks == 2
        assert response.failed_checks == 1
        assert response.success_rate == 2/3
        assert response.platforms_found == ["whatsapp"]
        assert response.platforms_not_found == ["telegram"]
        assert response.platforms_error == ["instagram"]
    
    def test_phone_check_response_get_result_by_platform(self):
        """Test de récupération de résultat par plateforme."""
        request = PhoneCheckRequest(
            phone="612345678",
            country_code="33"
        )
        
        whatsapp_result = PhoneCheckResult(
            platform="whatsapp",
            status=VerificationStatus.EXISTS,
            exists=True
        )
        
        telegram_result = PhoneCheckResult(
            platform="telegram",
            status=VerificationStatus.NOT_EXISTS,
            exists=False
        )
        
        response = PhoneCheckResponse(
            request=request,
            results=[whatsapp_result, telegram_result]
        )
        
        assert response.get_result_by_platform("whatsapp") == whatsapp_result
        assert response.get_result_by_platform("telegram") == telegram_result
        assert response.get_result_by_platform("nonexistent") is None
    
    def test_phone_check_response_to_dict(self):
        """Test de conversion en dictionnaire."""
        request = PhoneCheckRequest(
            phone="612345678",
            country_code="33",
            platforms=["whatsapp"]
        )
        
        result = PhoneCheckResult(
            platform="whatsapp",
            status=VerificationStatus.EXISTS,
            exists=True
        )
        
        response = PhoneCheckResponse(
            request=request,
            results=[result],
            total_time=300.0
        )
        
        data = response.to_dict()
        
        assert 'request' in data
        assert 'results' in data
        assert 'summary' in data
        
        assert data['request']['phone'] == "612345678"
        assert data['request']['country_code'] == "33"
        assert len(data['results']) == 1
        assert data['summary']['total_time'] == 300.0
        assert data['summary']['successful_checks'] == 1
        assert data['summary']['failed_checks'] == 0

if __name__ == "__main__":
    pytest.main([__file__])
