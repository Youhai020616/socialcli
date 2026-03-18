"""social publish — publish content to one or all platforms."""
from __future__ import annotations

import click

from socialcli.platforms.base import Content
from socialcli.platforms import registry
from socialcli.core.publisher import publish_all, print_results
from socialcli.utils import output


@click.command()
@click.argument("text", default="")
@click.option("--title", "-t", default="", help="Post title")
@click.option("--image", "-i", multiple=True, help="Image file path (can use multiple)")
@click.option("--video", "-v", default="", help="Video file path")
@click.option("--link", "-l", default="", help="Link URL")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--platforms", "-p", default="", help="Comma-separated platforms (or 'all')")
@click.option("--subreddit", "-r", default="", help="Reddit subreddit name")
@click.option("--visibility", default="public", type=click.Choice(["public", "private", "friends"]))
@click.option("--schedule", default="", help="Schedule time (ISO 8601)")
@click.option("--file", "-f", "content_file", default="", help="Read content from file (Markdown/text)")
@click.option("--account", "-a", default="default", help="Account name")
@click.option("--dry-run", is_flag=True, help="Preview without publishing")
def publish(text, title, image, video, link, tags, platforms, subreddit,
            visibility, schedule, content_file, account, dry_run):
    """Publish content to social media platforms.

    Examples:

        social publish "Hello World!" -p twitter

        social publish -t "Title" -v video.mp4 -p douyin,xhs

        social publish --file post.md -p all

        social publish "Check this out" -p reddit -r programming
    """
    # Read content from file
    if content_file:
        try:
            with open(content_file) as f:
                file_content = f.read()
            # If file is markdown, extract title from first heading
            if content_file.endswith(".md"):
                lines = file_content.split("\n")
                for line in lines:
                    if line.startswith("# ") and not title:
                        title = line[2:].strip()
                        file_content = "\n".join(l for l in lines if l != line)
                        break
            if not text:
                text = file_content.strip()
        except FileNotFoundError:
            output.error(f"File not found: {content_file}")
            raise SystemExit(1)

    # Parse platforms
    if not platforms:
        output.error("Please specify platforms: -p twitter,reddit,douyin or -p all")
        output.dim(f"  Available: {', '.join(registry.names())}")
        raise SystemExit(1)

    if platforms == "all":
        platform_list = registry.names()
    else:
        platform_list = [p.strip() for p in platforms.split(",") if p.strip()]

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    # Build content
    content = Content(
        title=title,
        text=text,
        images=list(image),
        video=video,
        link=link,
        tags=tag_list,
        visibility=visibility,
        schedule_time=schedule,
        extras={"subreddit": subreddit} if subreddit else {},
    )

    if not content.title and not content.text and not content.images and not content.video:
        output.error("No content provided. Use text argument, --file, --image, or --video")
        raise SystemExit(1)

    output.info(f"Publishing to {len(platform_list)} platform(s): {', '.join(platform_list)}")
    if dry_run:
        output.warn("DRY RUN — nothing will be published")

    results = publish_all(content, platform_list, account=account, dry_run=dry_run)
    print_results(results)
