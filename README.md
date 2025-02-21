# 📱 Modern Phone Checker

> Une solution Python moderne et éthique pour la vérification des numéros de téléphone sur les réseaux sociaux.

Ce projet permet de vérifier rapidement et efficacement si un numéro de téléphone est enregistré sur différentes plateformes comme WhatsApp, Telegram, Instagram et Snapchat, tout en respectant les bonnes pratiques et les limitations d'API.

## ✨ Caractéristiques

🚀 **Performances Optimales**
- Architecture asynchrone pour des vérifications ultra-rapides
- Système de cache intelligent avec score de fraîcheur 
- Rate limiting intégré pour respecter les limites des APIs

🛡️ **Sécurité & Éthique**
- Vérifications éthiques sans notifications aux utilisateurs
- Respect complet du RGPD
- Gestion sécurisée des données sensibles

🎯 **Plateformes Supportées**
- WhatsApp - Vérification via l'API wa.me
- Telegram - Détection de présence discrète
- Instagram - Recherche de profil associé
- Snapchat - Vérification de l'existence du compte

## 🚀 Installation

```bash
# Cloner le repository
git clone https://github.com/nabz0r/modern-phone-checker.git
cd modern-phone-checker

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Installer les dépendances
pip install -r requirements.txt
```

## 💡 Utilisation

En ligne de commande :
```bash
# Vérifier un numéro
python -m phone_checker check +33612345678

# Lancer l'API REST
python -m phone_checker serve
```

En tant que bibliothèque Python :
```python
from phone_checker import PhoneChecker

async def check_number():
    checker = PhoneChecker()
    await checker.initialize()
    
    results = await checker.check_number(
        phone="612345678",
        country_code="33"
    )
    
    for result in results:
        print(f"{result.platform}: {'✅' if result.exists else '❌'}")
```

## 🏗️ Architecture

Le projet est conçu de manière modulaire avec :

```
modern-phone-checker/
├── phone_checker/         # Code source principal
│   ├── core.py           # Logique centrale
│   ├── cache.py          # Système de cache intelligent
│   ├── models.py         # Modèles de données
│   └── platforms/        # Vérificateurs par plateforme
├── tests/                # Tests unitaires et d'intégration
└── docs/                 # Documentation détaillée
```

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- 🐛 Signaler des bugs
- 💡 Proposer des fonctionnalités
- 🔧 Soumettre des pull requests

## 📬 Contact

- 📧 Email : nabz0r@gmail.com
- 🐙 GitHub : [@nabz0r](https://github.com/nabz0r)

## 📝 Licence

MIT License - © 2025 nabz0r
