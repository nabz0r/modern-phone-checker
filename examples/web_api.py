#!/usr/bin/env python3
"""
Exemple d'intégration de Modern Phone Checker dans une API web.

Ce script montre comment intégrer la bibliothèque dans une application
web avec FastAPI pour créer un service de vérification de numéros.
"""

try:
    from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    print("❌ FastAPI non installé. Installez-le avec: pip install fastapi uvicorn")
    print("   ou utilisez: pip install 'modern-phone-checker[web]'")
    FASTAPI_AVAILABLE = False

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from phone_checker import PhoneChecker
from phone_checker.models import PhoneCheckResponse
from phone_checker.logging import logger

# Configuration du logging pour FastAPI
logging.basicConfig(level=logging.INFO)

# Modèles Pydantic pour l'API
class PhoneCheckRequest(BaseModel):
    """Modèle de requête pour la vérification d'un numéro."""
    phone: str = Field(..., description="Numéro de téléphone sans indicatif pays", example="612345678")
    country_code: str = Field(..., description="Indicatif pays", example="33")
    platforms: Optional[List[str]] = Field(None, description="Plateformes à vérifier")
    force_refresh: bool = Field(False, description="Force le rafraîchissement du cache")

class MultiplePhoneCheckRequest(BaseModel):
    """Modèle pour la vérification de plusieurs numéros."""
    numbers: List[PhoneCheckRequest] = Field(..., description="Liste des numéros à vérifier")
    max_concurrent: int = Field(5, description="Nombre maximum de vérifications simultanées")

class HealthResponse(BaseModel):
    """Modèle de réponse pour le health check."""
    status: str
    timestamp: str
    uptime_seconds: float
    components: Dict[str, Any]

class StatsResponse(BaseModel):
    """Modèle de réponse pour les statistiques."""
    total_checks: int
    successful_checks: int
    failed_checks: int
    cache_hit_rate: float
    available_platforms: List[str]

if not FASTAPI_AVAILABLE:
    exit(1)

# Instance globale du checker (sera initialisée au démarrage)
phone_checker: Optional[PhoneChecker] = None
app_start_time = datetime.now()

# Application FastAPI
app = FastAPI(
    title="Modern Phone Checker API",
    description="API REST pour la vérification éthique de numéros de téléphone",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Initialise le PhoneChecker au démarrage de l'application."""
    global phone_checker
    logger.info("🚀 Démarrage de l'API Modern Phone Checker")
    
    phone_checker = PhoneChecker()
    await phone_checker.initialize()
    
    logger.info("✅ PhoneChecker initialisé avec succès")

@app.on_event("shutdown")
async def shutdown_event():
    """Ferme proprement le PhoneChecker à l'arrêt."""
    global phone_checker
    if phone_checker:
        await phone_checker.close()
        logger.info("👋 PhoneChecker fermé proprement")

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Point d'entrée racine de l'API."""
    return {
        "name": "Modern Phone Checker API",
        "version": "0.1.0",
        "description": "API de vérification éthique de numéros de téléphone",
        "endpoints": {
            "check": "/check - Vérification d'un numéro",
            "check_multiple": "/check/multiple - Vérification multiple",
            "health": "/health - État de santé",
            "stats": "/stats - Statistiques",
            "docs": "/docs - Documentation interactive"
        }
    }

@app.post("/check", response_model=Dict[str, Any])
async def check_phone_number(request: PhoneCheckRequest):
    """
    Vérifie un numéro de téléphone sur les plateformes spécifiées.
    
    - **phone**: Numéro sans l'indicatif pays (ex: "612345678")
    - **country_code**: Indicatif pays (ex: "33" pour la France)
    - **platforms**: Liste des plateformes à vérifier (optionnel)
    - **force_refresh**: Force le rafraîchissement du cache
    """
    if not phone_checker:
        raise HTTPException(status_code=503, detail="Service non disponible")
    
    try:
        logger.info(f"API: Vérification +{request.country_code} {request.phone}")
        
        response = await phone_checker.check_number(
            phone=request.phone,
            country_code=request.country_code,
            platforms=request.platforms,
            force_refresh=request.force_refresh
        )
        
        return response.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la vérification: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/check/multiple", response_model=Dict[str, Any])
async def check_multiple_numbers(request: MultiplePhoneCheckRequest):
    """
    Vérifie plusieurs numéros de téléphone en parallèle.
    
    - **numbers**: Liste des numéros à vérifier
    - **max_concurrent**: Nombre maximum de vérifications simultanées
    """
    if not phone_checker:
        raise HTTPException(status_code=503, detail="Service non disponible")
    
    if len(request.numbers) > 50:
        raise HTTPException(
            status_code=400, 
            detail="Trop de numéros (maximum 50 par requête)"
        )
    
    try:
        logger.info(f"API: Vérification multiple de {len(request.numbers)} numéros")
        
        # Conversion des modèles Pydantic en dictionnaires
        numbers_data = [
            {
                "phone": num.phone,
                "country_code": num.country_code
            }
            for num in request.numbers
        ]
        
        responses = await phone_checker.check_multiple_numbers(numbers_data)
        
        # Traitement des résultats
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                results.append({
                    "request": numbers_data[i],
                    "error": str(response),
                    "success": False
                })
            else:
                results.append({
                    "request": numbers_data[i],
                    "result": response.to_dict(),
                    "success": True
                })
        
        return {
            "total_requests": len(request.numbers),
            "successful_checks": sum(1 for r in results if r["success"]),
            "failed_checks": sum(1 for r in results if not r["success"]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification multiple: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Vérifie l'état de santé de l'API et de ses composants.
    """
    if not phone_checker:
        raise HTTPException(status_code=503, detail="Service non initialisé")
    
    try:
        health = await phone_checker.health_check()
        uptime = (datetime.now() - app_start_time).total_seconds()
        
        return HealthResponse(
            status=health["status"],
            timestamp=health["timestamp"],
            uptime_seconds=uptime,
            components=health["components"]
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du health check: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du health check")

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Retourne les statistiques d'utilisation de l'API.
    """
    if not phone_checker:
        raise HTTPException(status_code=503, detail="Service non disponible")
    
    try:
        stats = phone_checker.get_stats()
        
        return StatsResponse(
            total_checks=stats["total_checks"],
            successful_checks=stats["successful_checks"],
            failed_checks=stats["failed_checks"],
            cache_hit_rate=stats["cache_hit_rate"],
            available_platforms=stats["available_platforms"]
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/platforms")
async def get_platforms():
    """
    Retourne la liste des plateformes disponibles.
    """
    if not phone_checker:
        raise HTTPException(status_code=503, detail="Service non disponible")
    
    from phone_checker.platforms import get_available_platforms
    return get_available_platforms()

@app.delete("/cache")
async def clear_cache():
    """
    Vide le cache de l'application.
    """
    if not phone_checker:
        raise HTTPException(status_code=503, detail="Service non disponible")
    
    try:
        await phone_checker.clear_cache()
        return {"message": "Cache vidé avec succès"}
    except Exception as e:
        logger.error(f"Erreur lors du vidage du cache: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du vidage du cache")

@app.get("/cache/info")
async def get_cache_info():
    """
    Retourne des informations sur le cache.
    """
    if not phone_checker:
        raise HTTPException(status_code=503, detail="Service non disponible")
    
    if not phone_checker.use_cache:
        return {"message": "Cache désactivé"}
    
    try:
        cache_info = await phone_checker.cache.get_cache_info()
        return cache_info
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des infos cache: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Gestionnaire global des exceptions."""
    logger.error(f"Erreur non gérée: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur"}
    )

def main():
    """Lance le serveur API."""
    print("🚀 Démarrage de l'API Modern Phone Checker")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🔍 API Root: http://localhost:8000/")
    print("⏹️  Arrêt: Ctrl+C")
    
    uvicorn.run(
        "web_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Pas de reload pour éviter les problèmes avec les connections async
        log_level="info"
    )

if __name__ == "__main__":
    main()
