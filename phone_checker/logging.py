"""Système de logging structuré pour Phone Checker.

Ce module configure et gère tous les logs de l'application
avec support pour différents niveaux et formats.
"""

import logging
import logging.handlers
import sys
from typing import Optional
from pathlib import Path
from .config import default_config

class ColoredFormatter(logging.Formatter):
    """Formateur avec couleurs pour la console."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Vert
        'WARNING': '\033[33m',  # Jaune
        'ERROR': '\033[31m',    # Rouge
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Ajoute la couleur au niveau de log
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)

class PhoneCheckerLogger:
    """Gestionnaire de logging personnalisé pour Phone Checker."""
    
    def __init__(self, name: str = 'phone_checker'):
        self.logger = logging.getLogger(name)
        self.setup_logging()
    
    def setup_logging(self):
        """Configure le système de logging."""
        config = default_config.logging
        
        # Configure le niveau
        level = getattr(logging, config.level.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        # Évite la duplication des handlers
        if self.logger.handlers:
            return
        
        # Handler pour la console
        if config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            
            # Formateur avec couleurs pour la console
            console_formatter = ColoredFormatter(config.format)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # Handler pour les fichiers
        if config.file_path:
            file_path = Path(config.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Rotation des logs pour éviter les gros fichiers
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(level)
            
            # Formateur simple pour les fichiers
            file_formatter = logging.Formatter(config.format)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """Log au niveau DEBUG."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log au niveau INFO."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log au niveau WARNING."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log au niveau ERROR."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log au niveau CRITICAL."""
        self.logger.critical(message, extra=kwargs)
    
    def log_verification_start(self, phone: str, country_code: str, platforms: list):
        """Log le début d'une vérification."""
        self.info(
            f"Début vérification: +{country_code}{phone} sur {', '.join(platforms)}",
            phone=phone,
            country_code=country_code,
            platforms=platforms
        )
    
    def log_verification_result(self, platform: str, phone: str, exists: bool, error: Optional[str] = None):
        """Log le résultat d'une vérification."""
        if error:
            self.error(
                f"Erreur vérification {platform}: {error}",
                platform=platform,
                phone=phone,
                error=error
            )
        else:
            status = "trouvé" if exists else "non trouvé"
            self.info(
                f"{platform}: {status}",
                platform=platform,
                phone=phone,
                exists=exists
            )
    
    def log_rate_limit(self, platform: str, wait_time: float):
        """Log un délai dû au rate limiting."""
        self.warning(
            f"Rate limit {platform}: attente de {wait_time:.1f}s",
            platform=platform,
            wait_time=wait_time
        )
    
    def log_cache_hit(self, phone: str, country_code: str, freshness: float):
        """Log un hit de cache."""
        self.debug(
            f"Cache hit: +{country_code}{phone} (fraîcheur: {freshness:.2f})",
            phone=phone,
            country_code=country_code,
            freshness=freshness
        )
    
    def log_cache_miss(self, phone: str, country_code: str):
        """Log un miss de cache."""
        self.debug(
            f"Cache miss: +{country_code}{phone}",
            phone=phone,
            country_code=country_code
        )

# Instance globale du logger
logger = PhoneCheckerLogger()

# Fonction pour obtenir un logger spécialisé
def get_logger(name: str) -> PhoneCheckerLogger:
    """Retourne un logger spécialisé pour un module."""
    return PhoneCheckerLogger(f'phone_checker.{name}')
