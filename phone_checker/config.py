"""Configuration centralisée pour Phone Checker.

Ce module gère toutes les configurations de l'application,
incluant les paramètres des APIs, le cache, et les limites de rate limiting.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class PlatformConfig:
    """Configuration pour une plateforme spécifique."""
    enabled: bool = True
    rate_limit_calls: int = 10
    rate_limit_period: int = 60
    timeout: float = 10.0
    retry_attempts: int = 3
    custom_headers: Dict[str, str] = field(default_factory=dict)

@dataclass
class CacheConfig:
    """Configuration du système de cache."""
    enabled: bool = True
    directory: str = '.cache'
    expire_after: int = 3600  # 1 heure
    max_size_mb: int = 100

@dataclass
class LoggingConfig:
    """Configuration du système de logging."""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: Optional[str] = None
    console_output: bool = True

class Config:
    """Gestionnaire de configuration principal."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialise la configuration.
        
        Args:
            config_file: Chemin vers le fichier de configuration JSON
        """
        self.config_file = config_file or self._get_default_config_path()
        self.load_config()
    
    def _get_default_config_path(self) -> str:
        """Retourne le chemin par défaut du fichier de configuration."""
        return os.path.join(os.path.dirname(__file__), '..', 'config', 'default.json')
    
    def load_config(self):
        """Charge la configuration depuis le fichier ou utilise les valeurs par défaut."""
        # Configuration par défaut
        self.cache = CacheConfig()
        self.logging = LoggingConfig()
        
        # Configurations par plateforme
        self.platforms = {
            'whatsapp': PlatformConfig(
                rate_limit_calls=10,
                rate_limit_period=60,
                timeout=10.0
            ),
            'telegram': PlatformConfig(
                rate_limit_calls=5,
                rate_limit_period=60,
                timeout=15.0
            ),
            'instagram': PlatformConfig(
                rate_limit_calls=5,
                rate_limit_period=60,
                timeout=10.0,
                retry_attempts=2
            ),
            'snapchat': PlatformConfig(
                rate_limit_calls=3,
                rate_limit_period=60,
                timeout=15.0,
                retry_attempts=1
            )
        }
        
        # Charge depuis le fichier si il existe
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._apply_file_config(config_data)
            except Exception as e:
                print(f"Erreur lors du chargement de la configuration: {e}")
        
        # Variables d'environnement
        self._apply_env_config()
    
    def _apply_file_config(self, config_data: Dict[str, Any]):
        """Applique la configuration depuis un fichier JSON."""
        # Cache
        if 'cache' in config_data:
            cache_config = config_data['cache']
            self.cache.enabled = cache_config.get('enabled', self.cache.enabled)
            self.cache.directory = cache_config.get('directory', self.cache.directory)
            self.cache.expire_after = cache_config.get('expire_after', self.cache.expire_after)
        
        # Logging
        if 'logging' in config_data:
            log_config = config_data['logging']
            self.logging.level = log_config.get('level', self.logging.level)
            self.logging.file_path = log_config.get('file_path', self.logging.file_path)
        
        # Plateformes
        if 'platforms' in config_data:
            for platform, platform_config in config_data['platforms'].items():
                if platform in self.platforms:
                    current = self.platforms[platform]
                    current.enabled = platform_config.get('enabled', current.enabled)
                    current.rate_limit_calls = platform_config.get('rate_limit_calls', current.rate_limit_calls)
                    current.rate_limit_period = platform_config.get('rate_limit_period', current.rate_limit_period)
    
    def _apply_env_config(self):
        """Applique la configuration depuis les variables d'environnement."""
        # Cache
        if os.getenv('PHONE_CHECKER_CACHE_ENABLED'):
            self.cache.enabled = os.getenv('PHONE_CHECKER_CACHE_ENABLED').lower() == 'true'
        
        if os.getenv('PHONE_CHECKER_CACHE_DIR'):
            self.cache.directory = os.getenv('PHONE_CHECKER_CACHE_DIR')
        
        # Logging
        if os.getenv('PHONE_CHECKER_LOG_LEVEL'):
            self.logging.level = os.getenv('PHONE_CHECKER_LOG_LEVEL')
        
        if os.getenv('PHONE_CHECKER_LOG_FILE'):
            self.logging.file_path = os.getenv('PHONE_CHECKER_LOG_FILE')
    
    def get_platform_config(self, platform: str) -> PlatformConfig:
        """Retourne la configuration pour une plateforme."""
        return self.platforms.get(platform, PlatformConfig())
    
    def save_config(self, file_path: Optional[str] = None):
        """Sauvegarde la configuration actuelle dans un fichier JSON."""
        file_path = file_path or self.config_file
        
        config_data = {
            'cache': {
                'enabled': self.cache.enabled,
                'directory': self.cache.directory,
                'expire_after': self.cache.expire_after,
                'max_size_mb': self.cache.max_size_mb
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file_path': self.logging.file_path,
                'console_output': self.logging.console_output
            },
            'platforms': {}
        }
        
        for platform, platform_config in self.platforms.items():
            config_data['platforms'][platform] = {
                'enabled': platform_config.enabled,
                'rate_limit_calls': platform_config.rate_limit_calls,
                'rate_limit_period': platform_config.rate_limit_period,
                'timeout': platform_config.timeout,
                'retry_attempts': platform_config.retry_attempts
            }
        
        # Crée le répertoire si nécessaire
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

# Instance globale par défaut
default_config = Config()
