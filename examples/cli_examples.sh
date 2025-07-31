#!/bin/bash

# Script d'exemples d'utilisation en ligne de commande
# Modern Phone Checker - Exemples CLI

set -e  # Arrêt en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Fonction d'affichage avec couleurs
print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Vérification que phone-checker est installé
check_installation() {
    if ! command -v phone-checker &> /dev/null; then
        print_error "phone-checker n'est pas installé ou pas dans le PATH"
        echo "Installez-le avec: pip install -e ."
        exit 1
    fi
    print_success "phone-checker est installé et disponible"
}

# Exemple 1: Vérification basique
example_basic() {
    print_header "Exemple 1: Vérification basique"
    
    print_info "Vérification d'un numéro français fictif..."
    phone-checker check 612345678 --country 33
    
    echo ""
    print_info "Vérification avec sortie JSON..."
    phone-checker check 612345678 --country 33 --json-output | python -m json.tool
}

# Exemple 2: Plateformes spécifiques
example_platforms() {
    print_header "Exemple 2: Plateformes spécifiques"
    
    print_info "Vérification WhatsApp et Telegram seulement..."
    phone-checker check 712345678 --country 33 --platforms whatsapp --platforms telegram
    
    echo ""
    print_info "Vérification Instagram seulement..."
    phone-checker check 612345679 --country 33 --platforms instagram
}

# Exemple 3: Différents pays
example_countries() {
    print_header "Exemple 3: Différents pays"
    
    print_info "Numéro français..."
    phone-checker check 612345678 --country 33 --json-output | jq '.request.full_number'
    
    print_info "Numéro américain..."
    phone-checker check 5551234567 --country 1 --json-output | jq '.request.full_number'
    
    print_info "Numéro allemand..."
    phone-checker check 1512345678 --country 49 --json-output | jq '.request.full_number'
}

# Exemple 4: Gestion du cache
example_cache() {
    print_header "Exemple 4: Gestion du cache"
    
    print_info "Première vérification (mise en cache)..."
    time phone-checker check 612345678 --country 33 > /dev/null
    
    print_info "Deuxième vérification (depuis le cache)..."
    time phone-checker check 612345678 --country 33 > /dev/null
    
    echo ""
    print_info "Affichage des statistiques du cache..."
    phone-checker stats
    
    echo ""
    print_info "Vidage du cache..."
    phone-checker clear-cache --confirm
}

# Exemple 5: Traitement par lots avec fichier CSV
example_batch() {
    print_header "Exemple 5: Traitement par lots"
    
    # Création d'un fichier CSV d'exemple
    cat > /tmp/phones_example.csv << EOF
phone,country_code
612345678,33
712345679,33
5551234567,1
1512345678,49
EOF
    
    print_info "Fichier CSV créé avec des numéros d'exemple:"
    cat /tmp/phones_example.csv
    
    echo ""
    print_info "Traitement par lots avec 2 vérifications simultanées..."
    phone-checker batch /tmp/phones_example.csv --concurrent 2 --output /tmp/results.json
    
    echo ""
    print_info "Résultats sauvegardés:"
    cat /tmp/results.json | jq '.results | length' | xargs echo "Nombre de résultats:"
    
    # Nettoyage
    rm -f /tmp/phones_example.csv /tmp/results.json
}

# Exemple 6: Configuration
example_config() {
    print_header "Exemple 6: Configuration"
    
    print_info "Configuration actuelle:"
    phone-checker config-show
}

# Exemple 7: Utilisation avec des options avancées
example_advanced() {
    print_header "Exemple 7: Options avancées"
    
    print_info "Vérification avec rafraîchissement forcé du cache..."
    phone-checker check 612345678 --country 33 --force-refresh --json-output | jq '.results[0].metadata.cached'
    
    echo ""
    print_info "Mode verbeux pour le débogage..."
    phone-checker --verbose check 612345678 --country 33 2>&1 | head -10
    
    echo ""
    print_info "Mode silencieux (codes de sortie seulement)..."
    if phone-checker --quiet check 612345678 --country 33; then
        print_success "Numéro trouvé sur au moins une plateforme (code 0)"
    else
        case $? in
            1) print_warning "Numéro non trouvé (code 1)" ;;
            2) print_error "Erreurs rencontrées (code 2)" ;;
        esac
    fi
}

# Exemple 8: Pipeline avec autres outils
example_pipeline() {
    print_header "Exemple 8: Intégration avec d'autres outils"
    
    print_info "Extraction des plateformes où un numéro est trouvé:"
    phone-checker check 612345678 --country 33 --json-output | \
        jq -r '.summary.platforms_found[]' | \
        while read platform; do
            echo "  📱 Trouvé sur: $platform"
        done
    
    echo ""
    print_info "Comptage des succès vs échecs:"
    result=$(phone-checker check 612345678 --country 33 --json-output)
    success_rate=$(echo "$result" | jq -r '.summary.success_rate')
    echo "  📊 Taux de succès: $(echo "$success_rate * 100" | bc -l | cut -d. -f1)%"
    
    echo ""
    print_info "Filtrage des résultats par plateforme:"
    phone-checker check 612345678 --country 33 --json-output | \
        jq -r '.results[] | select(.platform == "whatsapp") | "WhatsApp: " + (.exists | tostring)'
}

# Exemple 9: Monitoring et alertes
example_monitoring() {
    print_header "Exemple 9: Monitoring et scripts d'alerte"
    
    print_info "Script de monitoring basique:"
    
    # Simule un script de monitoring
    cat << 'EOF'
#!/bin/bash
# Exemple de script de monitoring

PHONE="$1"
COUNTRY="$2"

# Vérification avec timeout
timeout 30 phone-checker check "$PHONE" --country "$COUNTRY" --json-output > /tmp/check_result.json

if [ $? -eq 0 ]; then
    # Analyse des résultats
    platforms_found=$(jq -r '.summary.platforms_found | length' /tmp/check_result.json)
    
    if [ "$platforms_found" -gt 0 ]; then
        echo "ALERT: Numéro +$COUNTRY$PHONE trouvé sur $platforms_found plateforme(s)"
        jq -r '.summary.platforms_found[]' /tmp/check_result.json | while read platform; do
            echo "  - $platform"
        done
    else
        echo "INFO: Numéro +$COUNTRY$PHONE non trouvé"
    fi
else
    echo "ERROR: Échec de la vérification pour +$COUNTRY$PHONE"
fi

rm -f /tmp/check_result.json
EOF
    
    echo ""
    print_info "Ce script peut être utilisé avec cron, systemd, ou d'autres outils de monitoring"
}

# Fonction principale
main() {
    echo -e "${PURPLE}🚀 Modern Phone Checker - Exemples CLI${NC}"
    echo -e "${PURPLE}========================================${NC}"
    
    # Vérification de l'installation
    check_installation
    
    # Vérification des outils optionnels
    if ! command -v jq &> /dev/null; then
        print_warning "jq n'est pas installé (recommandé pour le traitement JSON)"
        print_info "Installez avec: apt-get install jq (Ubuntu/Debian) ou brew install jq (macOS)"
    fi
    
    if ! command -v bc &> /dev/null; then
        print_warning "bc n'est pas installé (utilisé pour les calculs)"
    fi
    
    # Menu interactif
    while true; do
        echo ""
        echo -e "${CYAN}Choisissez un exemple à exécuter:${NC}"
        echo "1. Vérification basique"
        echo "2. Plateformes spécifiques"
        echo "3. Différents pays"
        echo "4. Gestion du cache"
        echo "5. Traitement par lots"
        echo "6. Configuration"
        echo "7. Options avancées"
        echo "8. Pipeline avec autres outils"
        echo "9. Monitoring et alertes"
        echo "0. Tous les exemples"
        echo "q. Quitter"
        
        read -p "Votre choix: " choice
        
        case $choice in
            1) example_basic ;;
            2) example_platforms ;;
            3) example_countries ;;
            4) example_cache ;;
            5) example_batch ;;
            6) example_config ;;
            7) example_advanced ;;
            8) example_pipeline ;;
            9) example_monitoring ;;
            0) 
                example_basic
                example_platforms
                example_countries
                example_cache
                example_batch
                example_config
                example_advanced
                example_pipeline
                example_monitoring
                ;;
            q|Q) 
                print_success "Au revoir!"
                exit 0 
                ;;
            *) 
                print_error "Choix invalide. Essayez encore."
                ;;
        esac
    done
}

# Lancement du script principal
main "$@"
