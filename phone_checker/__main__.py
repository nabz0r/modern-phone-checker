"""Point d'entrée pour l'utilisation en ligne de commande."""

import asyncio
import click
from . import PhoneChecker

@click.command()
@click.argument('phone')
@click.option('--country', '-c', default='33', help='Code pays (par défaut: 33 pour France)')
def main(phone: str, country: str):
    """Vérifie un numéro de téléphone sur différentes plateformes."""
    async def run():
        checker = PhoneChecker()
        try:
            results = await checker.check_number(phone, country)
            for result in results:
                print(f"\n{result.platform.upper()}:")
                print(f"Existe: {'Oui' if result.exists else 'Non'}")
                if result.error:
                    print(f"Erreur: {result.error}")
                if result.username:
                    print(f"Nom d'utilisateur: {result.username}")
        finally:
            await checker.close()
    
    asyncio.run(run())

if __name__ == '__main__':
    main()
