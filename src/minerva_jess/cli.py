"""
Command-line interface for Minerva-Jess.

Provides an interactive way to query the Jess video intelligence agent.

Usage:
    jess "What are the key risks in AI investments?"
    jess --list-videos
    jess --interactive
"""

import argparse
import asyncio
import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from minerva_jess.agent import JessAgent
from minerva_jess.config import Settings, get_settings


console = Console()


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="jess",
        description="Jess - Video Intelligence Agent powered by Minerva",
        epilog="Example: jess 'What did Andy say about AI bubbles?'",
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Question to ask Jess",
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start interactive mode",
    )

    parser.add_argument(
        "-l", "--list-videos",
        action="store_true",
        help="List available videos",
    )

    parser.add_argument(
        "-r", "--recommendations",
        action="store_true",
        help="Get video recommendations",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


async def run_query(agent: JessAgent, query: str) -> None:
    """Run a single query and display the result."""
    with console.status("[bold blue]Searching video library...", spinner="dots"):
        result = await agent.query(query)

    if result.success:
        # Display the response as markdown
        console.print()
        console.print(Markdown(result.content))

        # Show video info if available
        if result.video_info:
            video = result.video_info
            console.print()
            console.print(
                Panel(
                    f"[bold]{video.get('title', 'Video')}[/bold]\n"
                    f"⏱️ {video.get('timestamp', '0:00')}\n"
                    f"🔗 {video.get('url', '')}",
                    title="📺 Watch Now",
                    border_style="blue",
                )
            )

        # Show follow-up suggestions
        if result.clickable_examples:
            console.print()
            console.print("[dim]Try asking:[/dim]")
            for example in result.clickable_examples[:3]:
                console.print(f"  [cyan]{example}[/cyan]")
    else:
        console.print(f"[red]Error:[/red] {result.content}")


async def run_interactive(agent: JessAgent) -> None:
    """Run interactive mode."""
    console.print(
        Panel(
            "[bold blue]Jess[/bold blue] - Video Intelligence Agent\n\n"
            "Ask me about videos on markets, investments, and strategy.\n"
            "Type 'quit' or 'exit' to leave, 'help' for suggestions.",
            border_style="blue",
        )
    )

    while True:
        try:
            query = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if query.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break

            if query.lower() in ("help", "?"):
                query = "help"

            if not query.strip():
                continue

            await run_query(agent, query)

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def async_main(args: argparse.Namespace) -> int:
    """Async main function."""
    try:
        settings = get_settings()

        if args.verbose:
            settings.log_level = "DEBUG"

        settings.configure_logging()
        agent = JessAgent(settings)

        if args.interactive:
            await run_interactive(agent)
        elif args.list_videos or args.recommendations:
            query = "list videos" if args.list_videos else "recommendations"
            await run_query(agent, query)
        elif args.query:
            await run_query(agent, args.query)
        else:
            # No args - start interactive mode
            await run_interactive(agent)

        return 0

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        return 130
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if args.verbose:
            console.print_exception()
        return 1


def main() -> None:
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    exit_code = asyncio.run(async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
