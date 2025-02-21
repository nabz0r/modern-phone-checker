# Modern Phone Checker

Un outil moderne et éthique pour la vérification des numéros de téléphone sur différentes plateformes.

## Fonctionnalités

- Vérification simultanée sur plusieurs plateformes (WhatsApp, Telegram, Instagram, etc.)
- Architecture asynchrone pour des performances optimales
- Système anti rate-limiting intégré
- Interface en ligne de commande et API REST
- Respect des bonnes pratiques RGPD

## Installation

```bash
# Cloner le repository
git clone https://github.com/nabz0r/modern-phone-checker.git
cd modern-phone-checker

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

## Utilisation

```bash
# Vérifier un numéro
python -m phone_checker check +33612345678

# Lancer l'API REST
python -m phone_checker serve
```

## Structure du Projet

```
modern-phone-checker/
├── phone_checker/         # Code source principal
│   ├── __init__.py
│   ├── core.py           # Fonctionnalités principales
│   ├── platforms/        # Modules pour chaque plateforme
│   └── api/              # API REST avec FastAPI
├── tests/                # Tests unitaires et d'intégration
├── docs/                 # Documentation
└── requirements.txt      # Dépendances du projet
```

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

📞 Contact
Email: nabz0r@gmail.com GitHub: @nabz0r

📜 License
MIT License - Innovation without Boundaries
