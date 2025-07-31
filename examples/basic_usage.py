#!/usr/bin/env python3
"""
Exemple d'utilisation basique de Modern Phone Checker.

Ce script montre comment utiliser la bibliothèque pour vérifier
un numéro de téléphone sur différentes plateformes.
"""

import asyncio
import sys
from phone_checker import PhoneChecker
from phone_checker.logging import logger

async def example_basic_check():
    """Exemple de vérification basique d'un numéro."""
    print("🔍 Exemple 1: Vérification basique")
    print("=" * 50)
    
    # Numéro d'exemple (fictif)
    phone = "612345678"
    country_code = "33"
    
    try:
        async with PhoneChecker() as checker:
            logger.info(f"Vérification du numéro +{country_code} {phone}")
            
            response = await checker.check_number(phone, country_code)
            
            print(f"\n📱 Résultats pour +{country_code} {phone}:")
            print(f"   Plateformes vérifiées: {len(response.results)}")
            print(f"   Trouvé sur: {len(response.platforms_found)} plateforme(s)")
            print(f"   Temps total: {response.total_time:.1f}ms")
            print(f"   Taux de succès: {response.success_rate:.1%}")
            
            print("\n📊 Détails par plateforme:")
            for result in response.results:
                status = "✅ Trouvé" if result.exists else "❌ Non trouvé"
                if result.error:
                    status = f"⚠️ Erreur: {result.error}"
                
                confidence = f"({result.confidence_score:.1%})" if result.confidence_score > 0 else ""
                cached = " [Cache]" if result.is_cached else ""
                
                print(f"   {result.platform.upper():12} {status} {confidence}{cached}")
                
                if result.username:
                    print(f"                 👤 @{result.username}")
                    
                if result.response_time > 0:
                    print(f"                 ⏱️ {result.response_time:.0f}ms")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def example_specific_platforms():
    """Exemple de vérification sur des plateformes spécifiques."""
    print("\n🎯 Exemple 2: Plateformes spécifiques")
    print("=" * 50)
    
    phone = "712345678"
    country_code = "33"
    platforms = ["whatsapp", "telegram"]
    
    try:
        async with PhoneChecker(platforms=platforms) as checker:
            print(f"Vérification sur {', '.join(platforms)} seulement...")
            
            response = await checker.check_number(
                phone, 
                country_code, 
                platforms=platforms
            )
            
            print(f"\n📱 Résultats pour +{country_code} {phone}:")
            for result in response.results:
                print(f"   {result.platform}: {'Trouvé' if result.exists else 'Non trouvé'}")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def example_multiple_numbers():
    """Exemple de vérification de plusieurs numéros."""
    print("\n📋 Exemple 3: Vérification multiple")
    print("=" * 50)
    
    numbers = [
        {"phone": "612345678", "country_code": "33"},
        {"phone": "712345679", "country_code": "33"},
        {"phone": "5551234567", "country_code": "1"}
    ]
    
    try:
        async with PhoneChecker() as checker:
            print(f"Vérification de {len(numbers)} numéros...")
            
            responses = await checker.check_multiple_numbers(numbers)
            
            print("\n📊 Résumé des résultats:")
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"   Numéro {i+1}: ❌ Erreur - {response}")
                    continue
                
                number_info = numbers[i]
                found_count = len(response.platforms_found)
                
                print(f"   +{number_info['country_code']} {number_info['phone']}: "
                      f"{found_count} plateforme(s) trouvée(s)")
                
                if response.platforms_found:
                    print(f"      └─ Trouvé sur: {', '.join(response.platforms_found)}")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def example_with_cache():
    """Exemple montrant l'utilisation du cache."""
    print("\n💾 Exemple 4: Utilisation du cache")
    print("=" * 50)
    
    phone = "612345678"
    country_code = "33"
    
    try:
        async with PhoneChecker() as checker:
            # Première vérification (va en cache)
            print("Première vérification (mise en cache)...")
            start_time = asyncio.get_event_loop().time()
            
            response1 = await checker.check_number(phone, country_code)
            time1 = (asyncio.get_event_loop().time() - start_time) * 1000
            
            print(f"   Temps: {time1:.1f}ms")
            
            # Deuxième vérification (depuis le cache)
            print("\nDeuxième vérification (depuis le cache)...")
            start_time = asyncio.get_event_loop().time()
            
            response2 = await checker.check_number(phone, country_code)
            time2 = (asyncio.get_event_loop().time() - start_time) * 1000
            
            print(f"   Temps: {time2:.1f}ms")
            print(f"   Accélération: {time1/time2:.1f}x plus rapide!")
            
            # Vérification des données de cache
            cached_results = [r for r in response2.results if r.is_cached]
            print(f"   Résultats en cache: {len(cached_results)}/{len(response2.results)}")
            
            # Statistiques du cache
            stats = checker.get_stats()
            print(f"\n📊 Statistiques du cache:")
            print(f"   Hit rate: {stats['cache_hit_rate']:.1%}")
            print(f"   Hits: {stats['cache_hits']}")
            print(f"   Misses: {stats['cache_misses']}")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def example_health_check():
    """Exemple de vérification de santé du système."""
    print("\n🏥 Exemple 5: Vérification de santé")
    print("=" * 50)
    
    try:
        async with PhoneChecker() as checker:
            health = await checker.health_check()
            
            print(f"Statut général: {health['status'].upper()}")
            print(f"Dernière vérification: {health['timestamp']}")
            
            print("\n🔧 État des composants:")
            for component, info in health['components'].items():
                status_emoji = "✅" if info['status'] == 'healthy' else "⚠️"
                print(f"   {status_emoji} {component.capitalize()}: {info['status']}")
                
                if 'error' in info:
                    print(f"      └─ Erreur: {info['error']}")
                    
                if 'response_time' in info:
                    print(f"      └─ Temps de réponse: {info['response_time']:.1f}ms")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    return True

async def main():
    """Fonction principale qui lance tous les exemples."""
    print("🚀 Modern Phone Checker - Exemples d'utilisation")
    print("=" * 60)
    print("⚠️  Note: Ces exemples utilisent des numéros fictifs")
    print("=" * 60)
    
    examples = [
        example_basic_check,
        example_specific_platforms,
        example_multiple_numbers,
        example_with_cache,
        example_health_check
    ]
    
    results = []
    for example in examples:
        try:
            result = await example()
            results.append(result)
        except KeyboardInterrupt:
            print("\n⏹️ Exemples interrompus par l'utilisateur")
            break
        except Exception as e:
            print(f"❌ Erreur dans l'exemple: {e}")
            results.append(False)
    
    # Résumé final
    successful = sum(results)
    total = len(results)
    
    print(f"\n✨ Résumé des exemples:")
    print(f"   Réussis: {successful}/{total}")
    print(f"   Taux de succès: {successful/total:.1%}")
    
    if successful == total:
        print("\n🎉 Tous les exemples ont été exécutés avec succès!")
        return 0
    else:
        print(f"\n⚠️ {total - successful} exemple(s) ont échoué.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Au revoir!")
        sys.exit(0)
