.PHONY: help install install-dev test test-verbose test-coverage lint format clean run-example check-security docs

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest
BLACK := black
FLAKE8 := flake8
MYPY := mypy
BANDIT := bandit

help: ## Affiche cette aide
	@echo "Modern Phone Checker - Commandes disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances de base
	$(PIP) install -e .

install-dev: ## Installe les dépendances de développement
	$(PIP) install -e ".[dev,docs,security]"
	pre-commit install

test: ## Lance les tests
	$(PYTEST) tests/ -v

test-verbose: ## Lance les tests en mode verbose
	$(PYTEST) tests/ -v -s --tb=short

test-coverage: ## Lance les tests avec rapport de couverture
	$(PYTEST) tests/ --cov=phone_checker --cov-report=html --cov-report=term-missing

lint: ## Vérifie le code avec flake8 et mypy
	$(FLAKE8) phone_checker/ tests/
	$(MYPY) phone_checker/

format: ## Formate le code avec black
	$(BLACK) phone_checker/ tests/ setup.py

check-format: ## Vérifie le formatage sans modifier
	$(BLACK) --check phone_checker/ tests/ setup.py

check-security: ## Vérifie la sécurité avec bandit
	$(BANDIT) -r phone_checker/ -f json -o security-report.json || true
	$(BANDIT) -r phone_checker/

clean: ## Nettoie les fichiers temporaires
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/
	rm -f security-report.json

run-example: ## Lance un exemple de vérification
	$(PYTHON) -m phone_checker check 612345678 --country 33

run-example-json: ## Lance un exemple avec sortie JSON
	$(PYTHON) -m phone_checker check 612345678 --country 33 --json-output

stats: ## Affiche les statistiques
	$(PYTHON) -m phone_checker stats

clear-cache: ## Vide le cache
	$(PYTHON) -m phone_checker clear-cache --confirm

show-config: ## Affiche la configuration
	$(PYTHON) -m phone_checker config-show

docs: ## Génère la documentation
	cd docs && make html

serve-docs: docs ## Sert la documentation localement
	cd docs/_build/html && $(PYTHON) -m http.server 8000

build: clean ## Construit le package
	$(PYTHON) setup.py sdist bdist_wheel

publish-test: build ## Publie sur TestPyPI
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

publish: build ## Publie sur PyPI
	twine upload dist/*

docker-build: ## Construit l'image Docker
	docker build -t phone-checker .

docker-run: ## Lance le container Docker
	docker run --rm -it phone-checker

pre-commit: ## Lance pre-commit sur tous les fichiers
	pre-commit run --all-files

health-check: ## Vérifie la santé de l'installation
	$(PYTHON) -c "import phone_checker; print('✅ Phone Checker installé correctement')"
	$(PYTHON) -c "from phone_checker import PhoneChecker; print('✅ Import PhoneChecker OK')"

init-project: ## Initialise un nouveau projet de développement
	$(MAKE) install-dev
	$(MAKE) health-check
	@echo ""
	@echo "🎉 Projet initialisé avec succès!"
	@echo "📚 Utilisez 'make help' pour voir toutes les commandes disponibles"
	@echo "🔧 Utilisez 'make run-example' pour tester une vérification"

# Commandes Git helpers
git-status: ## Affiche le statut Git avec des stats
	@echo "📊 Statut du repository:"
	@git status --short
	@echo ""
	@echo "📈 Statistiques:"
	@git log --oneline | wc -l | xargs echo "  Commits:"
	@git branch -a | wc -l | xargs echo "  Branches:"
	@git ls-files | wc -l | xargs echo "  Fichiers trackés:"

git-clean-branches: ## Nettoie les branches mergées
	git branch --merged | grep -v "\*\|main\|master" | xargs -n 1 git branch -d

# Commandes de débogage
debug-install: ## Debug des problèmes d'installation
	@echo "🔍 Informations de débogage:"
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Pip version: $$($(PIP) --version)"
	@echo "Virtual env: $$VIRTUAL_ENV"
	@echo "Current directory: $$(pwd)"
	@echo "Phone checker module:"
	@$(PYTHON) -c "import phone_checker; print(f'  Path: {phone_checker.__file__}'); print(f'  Version: {phone_checker.__version__}')" || echo "  ❌ Module non trouvé"

performance-test: ## Test de performance basique
	$(PYTHON) -c "
import asyncio
import time
from phone_checker import PhoneChecker

async def perf_test():
    start = time.time()
    async with PhoneChecker() as checker:
        # Test avec un numéro fictif
        result = await checker.check_number('123456789', '33')
        print(f'✅ Test terminé en {time.time() - start:.2f}s')
        print(f'📊 {len(result.results)} plateformes vérifiées')

asyncio.run(perf_test())
"

# Valeur par défaut
.DEFAULT_GOAL := help
