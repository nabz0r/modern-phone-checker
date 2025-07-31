"""Modern Phone Checker - Un vérificateur de numéros de téléphone moderne et éthique"""

from .core import PhoneChecker
from .models import PhoneCheckResult
from .config import Config

__version__ = '0.1.0'
__all__ = ['PhoneChecker', 'PhoneCheckResult', 'Config']