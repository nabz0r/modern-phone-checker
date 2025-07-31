# Guide de contribution

Merci de votre intérêt pour contribuer à Modern Phone Checker ! 🎉

Ce guide vous aidera à contribuer de manière efficace et cohérente avec l'esprit du projet.

## 📋 Table des matières

1. [Code de conduite](#code-de-conduite)
2. [Comment contribuer](#comment-contribuer)
3. [Configuration de l'environnement](#configuration-de-lenvironnement)
4. [Standards de développement](#standards-de-développement)
5. [Tests](#tests)
6. [Documentation](#documentation)
7. [Process de review](#process-de-review)

## 🤝 Code de conduite

Ce projet adhère au [Contributor Covenant](https://www.contributor-covenant.org/). En participant, vous vous engagez à respecter ce code de conduite.

### Nos engagements

- Utiliser un langage accueillant et inclusif
- Respecter les différents points de vue et expériences
- Accepter avec grâce les critiques constructives
- Se concentrer sur ce qui est le mieux pour la communauté
- Faire preuve d'empathie envers les autres membres

## 🚀 Comment contribuer

### Types de contributions acceptées

- 🐛 **Bug reports**: Signaler des problèmes
- 💡 **Feature requests**: Proposer de nouvelles fonctionnalités
- 📚 **Documentation**: Améliorer la documentation
- 🔧 **Code**: Corriger des bugs ou ajouter des fonctionnalités
- 🧪 **Tests**: Ajouter ou améliorer les tests
- 🌐 **Traductions**: Traduire l'interface ou la documentation

### Avant de commencer

1. **Vérifiez les issues existantes** pour éviter les doublons
2. **Ouvrez une issue** pour discuter des changements majeurs
3. **Forkez le repository** et créez une branche pour votre travail
4. **Respectez l'éthique** du projet : vérifications respectueuses et légales

## ⚙️ Configuration de l'environnement

### Prérequis

- Python 3.8+
- Git
- Make (optionnel mais recommandé)

### Installation pour le développement

```bash
# 1. Clonez votre fork
git clone https://github.com/VOTRE_USERNAME/modern-phone-checker.git
cd modern-phone-checker

# 2. Configurez l'environnement de développement
make init-project

# Ou manuellement :
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev,docs,security]"
pre-commit install
```

### Vérification de l'installation

```bash
make health-check
make test
```

## 📏 Standards de développement

### Style de code

Nous utilisons plusieurs outils pour maintenir la qualité du code :

- **Black**: Formatage automatique
- **isort**: Tri des imports
- **flake8**: Linting
- **mypy**: Vérification de types
- **bandit**: Sécurité

```bash
# Formatage automatique
make format

# Vérifications
make lint
make check-security
```

### Conventions de nommage

- **Variables et fonctions**: `snake_case`
- **Classes**: `PascalCase`
- **Constantes**: `UPPER_SNAKE_CASE`
- **Modules**: `snake_case`
- **Packages**: `lowercase`

### Structure des commits

Utilisez des messages de commit clairs et descriptifs :

```
type(scope): description courte

Description plus détaillée si nécessaire.

Fixes #123
```

Types acceptés :
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage (pas de changement de code)
- `refactor`: Refactoring
- `test`: Ajout/modification de tests
- `chore`: Maintenance
- `perf`: Amélioration de performance
- `ci`: CI/CD

### Exemples de commits

```bash
feat(whatsapp): add retry mechanism for failed requests
fix(cache): resolve memory leak in cache cleanup
docs(readme): update installation instructions
test(integration): add tests for concurrent checks
```

## 🧪 Tests

### Types de tests

1. **Tests unitaires**: `tests/test_*.py`
2. **Tests d'intégration**: `tests/test_integration.py`
3. **Tests de performance**: Optionnels pour les PR importantes

### Lancement des tests

```bash
# Tests complets
make test

# Tests avec couverture
make test-coverage

# Tests spécifiques
pytest tests/test_utils.py -v

# Tests d'intégration seulement
pytest tests/test_integration.py
```

### Écriture des tests

- **Nommage**: `test_fonction_que_je_teste`
- **Structure**: Arrange, Act, Assert
- **Mocks**: Utilisez des mocks pour les APIs externes
- **Async**: Marquez les tests async avec `@pytest.mark.asyncio`

Exemple :

```python
@pytest.mark.asyncio
async def test_check_number_returns_results():
    """Test que check_number retourne des résultats valides."""
    # Arrange
    checker = PhoneChecker(use_cache=False)
    
    # Act
    result = await checker.check_number("123456789", "33")
    
    # Assert
    assert isinstance(result, PhoneCheckResponse)
    assert len(result.results) > 0
    
    await checker.close()
```

### Couverture de code

- **Minimum**: 80% de couverture
- **Objectif**: 90%+ pour les nouveaux modules
- **Exclusions**: Fichiers de configuration, scripts d'exemple

## 📚 Documentation

### Types de documentation

1. **Docstrings**: Pour toutes les fonctions/classes publiques
2. **README**: Utilisation générale
3. **API docs**: Documentation technique
4. **Exemples**: Scripts d'utilisation

### Format des docstrings

```python
def check_number(self, phone: str, country_code: str) -> PhoneCheckResponse:
    """Vérifie un numéro de téléphone sur les plateformes configurées.
    
    Args:
        phone: Numéro sans l'indicatif pays (ex: "612345678")
        country_code: Indicatif pays (ex: "33" pour la France)
        
    Returns:
        PhoneCheckResponse avec les résultats de vérification
        
    Raises:
        ValueError: Si le numéro est invalide
        
    Example:
        >>> checker = PhoneChecker()
        >>> result = await checker.check_number("612345678", "33")
        >>> print(f"Trouvé sur {len(result.platforms_found)} plateformes")
    """
```

### Génération de la documentation

```bash
make docs
make serve-docs  # Serveur local sur http://localhost:8000
```

## 🔍 Process de review

### Avant de soumettre une PR

1. **Tests**: Tous les tests passent
2. **Linting**: Code formaté et vérifié
3. **Documentation**: Mise à jour si nécessaire
4. **Changelog**: Ajout des modifications importantes

```bash
# Vérification complète
make pre-commit
make test-coverage
```

### Checklist pour les PR

- [ ] Description claire du problème résolu
- [ ] Tests ajoutés/modifiés
- [ ] Documentation mise à jour
- [ ] Changements ajoutés au CHANGELOG.md
- [ ] Commits suivent les conventions
- [ ] Pas de conflits avec main
- [ ] CI passe (tests, linting, sécurité)

### Template de PR

```markdown
## Description
Brève description des changements apportés.

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Tests
- [ ] Tests unitaires ajoutés/modifiés
- [ ] Tests d'intégration vérifiés
- [ ] Tests manuels effectués

## Checklist
- [ ] Code formaté avec black
- [ ] Tests passent
- [ ] Documentation mise à jour
- [ ] CHANGELOG.md mis à jour
```

### Review process

1. **Automated checks**: CI doit passer
2. **Code review**: Au moins 1 reviewer approuve
3. **Testing**: Tests automatisés et manuels
4. **Merge**: Squash and merge préféré

## 🐛 Signaler des bugs

### Informations à inclure

- **Environnement**: OS, version Python, version du package
- **Reproduction**: Étapes claires pour reproduire
- **Comportement attendu vs actuel**
- **Logs**: Messages d'erreur complets
- **Code**: Exemple minimal de reproduction

### Template d'issue

```markdown
**Description du bug**
Description claire et concise du problème.

**Reproduction**
Étapes pour reproduire le problème :
1. Aller à '...'
2. Cliquer sur '....'
3. Voir l'erreur

**Comportement attendu**
Ce qui devrait se passer.

**Screenshots/Logs**
Si applicable, ajoutez des captures d'écran ou logs.

**Environnement:**
- OS: [ex: Ubuntu 20.04]
- Python: [ex: 3.9.5]
- Version: [ex: 0.1.0]

**Contexte supplémentaire**
Ajoutez tout autre contexte pertinent.
```

## 💡 Proposer des fonctionnalités

### Avant de proposer

1. **Vérifiez** si la fonctionnalité existe déjà
2. **Recherchez** dans les issues existantes
3. **Considérez** l'impact sur l'éthique du projet

### Template de feature request

```markdown
**Problème résolu**
Description claire du problème que cette fonctionnalité résoudrait.

**Solution proposée**
Description de la solution souhaitée.

**Alternatives considérées**
Autres solutions envisagées.

**Impact**
- Performance
- Sécurité
- Éthique
- Maintenance

**Implémentation**
Idées sur comment l'implémenter (optionnel).
```

## 🌟 Reconnaissance des contributeurs

Tous les contributeurs sont reconnus dans :

- **README.md**: Section contributors
- **CHANGELOG.md**: Mentions dans les releases
- **GitHub**: Contributors automatiques

Types de contributions reconnues :
- Code
- Documentation
- Tests
- Bug reports
- Feature requests
- Reviews
- Traductions

## 📞 Contact

- **Issues GitHub**: Pour les bugs et fonctionnalités
- **Discussions GitHub**: Pour les questions générales
- **Email**: nabz0r@gmail.com pour les questions privées

## 🙏 Remerciements

Merci de contribuer à Modern Phone Checker ! Chaque contribution, petite ou grande, aide à améliorer l'outil pour toute la communauté.

---

**Rappel important**: Ce projet vise à fournir des outils de vérification éthiques et légaux. Toute contribution doit respecter cette philosophie et les lois applicables.
