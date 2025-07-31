"""Interface en ligne de commande avancée avec affichage riche."""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.tree import Tree
from rich.json import JSON
from rich import box
from datetime import datetime

from . import PhoneChecker
from .models import PhoneCheckResponse, VerificationStatus
from .utils import validate_phone_number, format_phone_number
from .config import default_config
from .logging import logger

console = Console()

def format_timestamp(timestamp):
    """Formate un timestamp de manière lisible."""
    return timestamp.strftime("%H:%M:%S %d/%m/%Y")

def get_status_emoji(status: VerificationStatus, exists: bool) -> str:
    """Retourne l'emoji approprié pour un statut."""
    if status == VerificationStatus.EXISTS:
        return "✅"
    elif status == VerificationStatus.NOT_EXISTS:
        return "❌"
    elif status == VerificationStatus.ERROR:
        return "❌"
    elif status == VerificationStatus.TIMEOUT:
        return "⏰"
    elif status == VerificationStatus.RATE_LIMITED:
        return "🚫"
    else:
        return "❓"

def create_result_table(response: PhoneCheckResponse) -> Table:
    """Crée un tableau rich pour afficher les résultats."""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Plateforme", style="cyan bold", width=12)
    table.add_column("Statut", style="green bold", width=15)
    table.add_column("Détails", style="yellow", min_width=20)
    table.add_column("Confiance", style="blue", width=10)
    table.add_column("Temps", style="magenta", width=12)
    
    for result in response.results:
        # Status avec emoji
        status_text = get_status_emoji(result.status, result.exists)
        if result.exists:
            status_text += " [green]Trouvé[/green]"
        else:
            status_text += " [red]Non trouvé[/red]"
        
        if result.error:
            status_text = "❌ [red]Erreur[/red]"
        
        # Détails
        details = []
        if result.error:
            details.append(f"[red]Erreur:[/red] {result.error[:50]}...")
        if result.username:
            details.append(f"[blue]@{result.username}[/blue]")
        if result.is_cached:
            freshness = result.metadata.get('freshness_score', 0)
            details.append(f"[dim]Cache ({freshness:.1%})[/dim]")
        if result.metadata.get('method'):
            details.append(f"[dim]{result.metadata['method']}[/dim]")
        
        details_text = "\n".join(details) if details else "-"
        
        # Score de confiance
        confidence = f"{result.confidence_score:.1%}" if result.confidence_score > 0 else "-"
        
        # Temps de réponse
        time_text = f"{result.response_time:.0f}ms" if result.response_time > 0 else "-"
        
        table.add_row(
            result.platform.upper(),
            status_text,
            details_text,
            confidence,
            time_text
        )
    
    return table

def create_summary_panel(response: PhoneCheckResponse) -> Panel:
    """Crée un panneau de résumé."""
    found_count = len(response.platforms_found)
    not_found_count = len(response.platforms_not_found)
    error_count = len(response.platforms_error)
    
    summary_text = f"""[bold]Résultats pour {response.request.full_number}[/bold]

📊 [cyan]Statistiques:[/cyan]
   • Plateformes vérifiées: {len(response.results)}
   • Trouvé sur: [green]{found_count}[/green] plateforme(s)
   • Non trouvé sur: [yellow]{not_found_count}[/yellow] plateforme(s)
   • Erreurs: [red]{error_count}[/red]
   • Taux de succès: [blue]{response.success_rate:.1%}[/blue]
   • Temps total: [magenta]{response.total_time:.1f}ms[/magenta]

🎯 [cyan]Plateformes où le numéro existe:[/cyan]
   {', '.join(response.platforms_found) if response.platforms_found else 'Aucune'}
"""
    
    if response.platforms_error:
        summary_text += f"\n\n⚠️  [yellow]Plateformes avec erreurs:[/yellow]\n   {', '.join(response.platforms_error)}"
    
    return Panel(
        summary_text,
        title="Résumé de la vérification",
        border_style="cyan"
    )

@click.group()
@click.option('--config', '-c', help='Fichier de configuration personnalisé')
@click.option('--verbose', '-v', is_flag=True, help='Mode verbeux')
@click.option('--quiet', '-q', is_flag=True, help='Mode silencieux')
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """Modern Phone Checker - Vérifiez des numéros sur les réseaux sociaux."""
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    # Configure le niveau de log
    if verbose:
        default_config.logging.level = 'DEBUG'
    elif quiet:
        default_config.logging.level = 'ERROR'

@cli.command()
@click.argument('phone')
@click.option('--country', '-c', default='33', help='Code pays (défaut: 33 pour France)')
@click.option('--platforms', '-p', multiple=True, help='Plateformes à vérifier')
@click.option('--force-refresh', '-f', is_flag=True, help='Force le rafraîchissement du cache')
@click.option('--json-output', '-j', is_flag=True, help='Sortie au format JSON')
@click.option('--no-cache', is_flag=True, help='Désactive le cache')
@click.pass_context
def check(ctx, phone: str, country: str, platforms: tuple, force_refresh: bool, json_output: bool, no_cache: bool):
    """Vérifie un numéro de téléphone sur différentes plateformes."""
    async def run():
        # Validation du numéro
        if not validate_phone_number(phone, country):
            if not ctx.obj['quiet']:
                console.print(Panel(
                    f"[red]Format de numéro invalide![/red]\n\n"
                    f"Le numéro {phone} ne semble pas valide pour le pays +{country}.\n"
                    f"Format attendu: numéro sans l'indicatif pays.",
                    title="❌ Erreur de validation",
                    border_style="red"
                ))
            sys.exit(1)
        
        # Formate le numéro pour l'affichage
        formatted_number = format_phone_number(phone, country, 'international')
        if not formatted_number:
            formatted_number = f"+{country} {phone}"
        
        # Configuration du checker
        platforms_list = list(platforms) if platforms else None
        
        try:
            async with PhoneChecker(
                platforms=platforms_list,
                use_cache=not no_cache
            ) as checker:
                
                if not ctx.obj['quiet'] and not json_output:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        TimeElapsedColumn(),
                        console=console
                    ) as progress:
                        task = progress.add_task(
                            f"Vérification de {formatted_number}...", 
                            total=None
                        )
                        
                        response = await checker.check_number(
                            phone, country, platforms_list, force_refresh
                        )
                else:
                    response = await checker.check_number(
                        phone, country, platforms_list, force_refresh
                    )
                
                # Affichage des résultats
                if json_output:
                    console.print(JSON.from_data(response.to_dict()))
                else:
                    if not ctx.obj['quiet']:
                        console.print("\n")
                        console.print(create_summary_panel(response))
                        console.print("\n")
                        console.print(create_result_table(response))
                    
                    # Code de sortie basé sur les résultats
                    if response.platforms_found:
                        sys.exit(0)  # Trouvé sur au moins une plateforme
                    elif response.platforms_error:
                        sys.exit(2)  # Erreurs rencontrées
                    else:
                        sys.exit(1)  # Non trouvé
        
        except ValueError as e:
            console.print(f"[red]Erreur:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Erreur inattendue:[/red] {e}")
            if ctx.obj['verbose']:
                console.print_exception()
            sys.exit(1)
    
    asyncio.run(run())

@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--country', '-c', default='33', help='Code pays par défaut')
@click.option('--output', '-o', help='Fichier de sortie JSON')
@click.option('--platforms', '-p', multiple=True, help='Plateformes à vérifier')
@click.option('--concurrent', default=5, help='Nombre de vérifications simultanées')
@click.pass_context
def batch(ctx, file: str, country: str, output: str, platforms: tuple, concurrent: int):
    """Vérifie plusieurs numéros depuis un fichier."""
    async def run():
        import csv
        import json
        
        numbers = []
        
        # Lecture du fichier
        try:
            with open(file, 'r', encoding='utf-8') as f:
                if file.endswith('.csv'):
                    reader = csv.DictReader(f)
                    for row in reader:
                        phone_num = row.get('phone', '').strip()
                        country_code = row.get('country_code', country).strip()
                        if phone_num:
                            numbers.append({'phone': phone_num, 'country_code': country_code})
                else:
                    # Fichier texte simple
                    for line in f:
                        phone_num = line.strip()
                        if phone_num:
                            numbers.append({'phone': phone_num, 'country_code': country})
        
        except Exception as e:
            console.print(f"[red]Erreur lors de la lecture du fichier:[/red] {e}")
            sys.exit(1)
        
        console.print(f"[cyan]Traitement de {len(numbers)} numéros...[/cyan]")
        
        platforms_list = list(platforms) if platforms else None
        results = []
        
        async with PhoneChecker(platforms=platforms_list) as checker:
            # Limite la concurrence
            semaphore = asyncio.Semaphore(concurrent)
            
            async def check_number(number_info):
                async with semaphore:
                    try:
                        return await checker.check_number(
                            number_info['phone'], 
                            number_info['country_code'],
                            platforms_list
                        )
                    except Exception as e:
                        logger.error(f"Erreur pour {number_info}: {e}")
                        return None
            
            # Progress bar pour le traitement par lots
            with Progress(console=console) as progress:
                task = progress.add_task("Vérification...", total=len(numbers))
                
                tasks = [check_number(num_info) for num_info in numbers]
                
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    if result:
                        results.append(result)
                    progress.advance(task)
        
        # Sauvegarde des résultats
        output_data = {
            'processed_at': datetime.now().isoformat(),
            'total_numbers': len(numbers),
            'successful_checks': len(results),
            'results': [r.to_dict() for r in results]
        }
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            console.print(f"[green]Résultats sauvegardés dans {output}[/green]")
        else:
            console.print(JSON.from_data(output_data))
    
    asyncio.run(run())

@cli.command()
@click.pass_context
def stats(ctx):
    """Affiche les statistiques du cache et de l'application."""
    async def run():
        async with PhoneChecker() as checker:
            # Statistiques du checker
            checker_stats = checker.get_stats()
            
            # Informations du cache si disponible
            cache_info = None
            if checker.use_cache:
                cache_info = await checker.cache.get_cache_info()
            
            # Affichage des statistiques du checker
            stats_tree = Tree("📊 [bold cyan]Statistiques Phone Checker[/bold cyan]")
            
            # Nœud pour les vérifications
            verification_node = stats_tree.add("🔍 [bold]Vérifications[/bold]")
            verification_node.add(f"Total: {checker_stats['total_checks']}")
            verification_node.add(f"Succès: [green]{checker_stats['successful_checks']}[/green]")
            verification_node.add(f"Échecs: [red]{checker_stats['failed_checks']}[/red]")
            verification_node.add(f"Taux de succès: [blue]{checker_stats['success_rate']:.1%}[/blue]")
            
            # Nœud pour les plateformes
            platforms_node = stats_tree.add("🌐 [bold]Plateformes[/bold]")
            for platform in checker_stats['available_platforms']:
                platforms_node.add(f"✅ {platform}")
            
            # Nœud pour le cache
            if cache_info:
                cache_node = stats_tree.add("💾 [bold]Cache[/bold]")
                cache_stats = cache_info['stats']
                cache_node.add(f"Entrées: {cache_stats['entries_count']}")
                cache_node.add(f"Taille: {cache_stats['size_formatted']}")
                cache_node.add(f"Hits: [green]{cache_stats['hits']}[/green]")
                cache_node.add(f"Misses: [yellow]{cache_stats['misses']}[/yellow]")
                cache_node.add(f"Taux de hit: [blue]{cache_stats['hit_rate']:.1%}[/blue]")
                cache_node.add(f"Utilisation: [magenta]{cache_stats['usage_percent']:.1f}%[/magenta]")
            
            console.print(stats_tree)
            
            # Santé des composants
            health = await checker.health_check()
            
            health_panel = Panel(
                f"[bold]Statut général:[/bold] {health['status'].upper()}\n"
                f"[bold]Dernière vérification:[/bold] {health['timestamp']}\n\n"
                + "\n".join([
                    f"[cyan]{comp}:[/cyan] {info['status']}"
                    for comp, info in health['components'].items()
                ]),
                title="🏥 État de santé",
                border_style="green" if health['status'] == 'healthy' else "yellow"
            )
            
            console.print("\n")
            console.print(health_panel)
    
    asyncio.run(run())

@cli.command()
@click.option('--confirm', is_flag=True, help='Confirme la suppression')
@click.pass_context
def clear_cache(ctx, confirm):
    """Vide le cache complètement."""
    async def run():
        if not confirm:
            if not click.confirm("Êtes-vous sûr de vouloir vider le cache ?"):
                console.print("[yellow]Opération annulée.[/yellow]")
                return
        
        async with PhoneChecker() as checker:
            if not checker.use_cache:
                console.print("[yellow]Le cache n'est pas activé.[/yellow]")
                return
            
            await checker.clear_cache()
            console.print("[green]✅ Cache vidé avec succès![/green]")
    
    asyncio.run(run())

@cli.command()
@click.pass_context
def config_show(ctx):
    """Affiche la configuration actuelle."""
    config_data = {
        'cache': {
            'enabled': default_config.cache.enabled,
            'directory': default_config.cache.directory,
            'expire_after': default_config.cache.expire_after,
            'max_size_mb': default_config.cache.max_size_mb
        },
        'logging': {
            'level': default_config.logging.level,
            'console_output': default_config.logging.console_output,
            'file_path': default_config.logging.file_path
        },
        'platforms': {}
    }
    
    for platform, config in default_config.platforms.items():
        config_data['platforms'][platform] = {
            'enabled': config.enabled,
            'rate_limit_calls': config.rate_limit_calls,
            'rate_limit_period': config.rate_limit_period,
            'timeout': config.timeout
        }
    
    console.print(Panel(
        JSON.from_data(config_data),
        title="⚙️ Configuration actuelle",
        border_style="cyan"
    ))

def main():
    """Point d'entrée principal."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Opération interrompue par l'utilisateur.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Erreur fatale:[/red] {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
