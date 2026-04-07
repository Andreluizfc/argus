"""Writing tools for the Writer agent."""

from pathlib import Path

from agno.tools import tool


@tool
def write_draft(
    title: str,
    content: str,
    output_path: str,
) -> str:
    """Write a draft document to disk.

    Args:
        title: Document title.
        content: Document body content.
        output_path: File path to write the draft.
    """
    file_path = Path("data/drafts") / output_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        f"# {title}\n\n{content}",
        encoding="utf-8",
    )
    return f"Draft written to {file_path}"


@tool
def format_as_markdown(content: str) -> str:
    """Format raw content as clean Markdown.

    Args:
        content: Raw text content to format.
    """
    return f"## Formatted Content\n\n{content}"
