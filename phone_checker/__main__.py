"""Interface en ligne de commande avec un affichage amélioré."""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from datetime import datetime
from . import PhoneChecker
from .utils import validate_phone_number

console = Console()

def format_timestamp(timestamp):
    """Formate un timestamp de manière lisible."""
    return timestamp.strftime("%H:%M:%S %d/%m/%Y")

def create_result_table(results):
    """Crée un tableau rich pour afficher les résultats."""
    table = Table(box=box.ROUNDED)
    table.add_column("Plateforme", style="cyan bold")
    table.add_column("Statut", style="green bold")
    table.add_column("Détails", style="yellow")
    table.add_column("Vérifié le", style="blue")
    
    for result in results:
        status = "[green]✓ Trouvé[/green]" if result.exists else "[red]✗ Non trouvé[/red]"
        details = []
        
        if result.error:
            details.append(f"Erreur: {result.error}")
        if result.username:
            details.append(f"Utilisateur: {result.username}")
        if result.metadata:
            for key, value in result.metadata.items():
                details.append(f"{key}: {value}")
                
        details_text = "\n".join(details) if details else "-"
        timestamp = format_timestamp(result.timestamp)
        
        table.add_row(
            result.platform.upper(),
            status,
            details_text,
            timestamp
        )
    
    return table

@click.command()
@click.argument('phone')
@click.option('--country', '-c', default='33', help='Code pays (par défaut: 33 pour France)')
def main(phone: str, country: str):
    """Vérifie un numéro de téléphone sur différentes plateformes."""
    async def run():
        # Vérifie le format du numéro
        if not validate_phone_number(phone, country):
            console.print(Panel(
                "[red]Format de numéro invalide![/red]\n\n"
                f"Le numéro {phone} ne semble pas valide pour le pays {country}.",
                title="Erreur de validation",
                border_style="red"
            ))
            return

        # Affiche un message de progression
        with console.status("[bold blue]Vérification en cours..."):
            checker = PhoneChecker()
            try:
                results = await checker.check_number(phone, country)
                
                # Crée et affiche le tableau des résultats
                console.print("\n")
                console.print(Panel(
                    f"Résultats pour le numéro: [bold]+{country} {phone}[/bold]",
                    style="cyan"
                ))
                console.print(create_result_table(results))
                
            finally:
                await checker.close()
    
    asyncio.run(run())

if __name__ == '__main__':
    main()
