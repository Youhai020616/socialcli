"""social ai — AI content generation and adaptation."""
from __future__ import annotations

import click

from socialcli.utils import output


@click.group()
def ai():
    """AI content generation and adaptation."""
    pass


@ai.command()
@click.argument("topic")
@click.option("--platforms", "-p", default="", help="Comma-separated platforms (default: all)")
@click.option("--json", "as_json", is_flag=True)
def generate(topic, platforms, as_json):
    """Generate content for multiple platforms from a topic.

    Example: social ai generate "AI coding tools" -p twitter,reddit,xhs
    """
    from socialcli.core.ai_writer import generate as ai_generate
    from socialcli.core.content_adapter import PLATFORM_RULES

    platform_list = [p.strip() for p in platforms.split(",") if p.strip()] if platforms else list(PLATFORM_RULES.keys())

    output.info(f"Generating content for: {topic}")
    output.dim(f"  Platforms: {', '.join(platform_list)}")

    try:
        results = ai_generate(topic, platform_list)

        if as_json:
            import json
            click.echo(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for platform, text in results.items():
                output.console.print(f"\n  [bold cyan]── {platform} ──[/bold cyan]")
                output.console.print(f"  {text}\n")

        output.success(f"Generated for {len(results)} platform(s)")
    except Exception as e:
        output.error(f"AI generation failed: {e}")
        raise SystemExit(1)


@ai.command()
@click.argument("text")
@click.option("--platform", "-p", required=True, help="Target platform")
@click.option("--json", "as_json", is_flag=True)
def adapt(text, platform, as_json):
    """Rewrite content for a specific platform's style.

    Example: social ai adapt "My long article..." -p twitter
    """
    from socialcli.core.ai_writer import adapt as ai_adapt

    output.info(f"Adapting for {platform}...")

    try:
        result = ai_adapt(text, platform)

        if as_json:
            import json
            click.echo(json.dumps({"platform": platform, "original": text, "adapted": result}, ensure_ascii=False, indent=2))
        else:
            output.console.print(f"\n  [bold cyan]── {platform} ──[/bold cyan]")
            output.console.print(f"  {result}\n")

        output.success("Content adapted")
    except Exception as e:
        output.error(f"AI adaptation failed: {e}")
        raise SystemExit(1)


@ai.command()
@click.argument("text")
@click.option("--platform", "-p", default="", help="Target platform")
@click.option("--count", "-n", default=5, help="Number of tags")
def tags(text, platform, count):
    """Generate hashtag suggestions for content.

    Example: social ai tags "My post about AI tools" -p twitter -n 5
    """
    from socialcli.core.ai_writer import suggest_tags

    try:
        result = suggest_tags(text, platform, count)
        output.console.print("\n  [bold]Suggested tags:[/bold]")
        for tag in result:
            output.console.print(f"  [cyan]#{tag}[/cyan]")
        output.console.print()
    except Exception as e:
        output.error(f"Tag generation failed: {e}")
        raise SystemExit(1)
