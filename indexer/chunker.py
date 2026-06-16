import re
from pathlib import Path
from typing import Optional


def estimate_tokens(text: str) -> int:
    """Rough token count estimate using word count * 1.3."""
    return int(len(text.split()) * 1.3)


def detect_content_type(content: str) -> str:
    """Detect content type to enable adaptive chunking.

    Returns:
        One of: 'code', 'prose', 'mixed', 'list'
    """
    code_blocks = len(re.findall(r"```", content))
    code_lines = len(re.findall(r"^\s{4,}[^\s]", content, re.MULTILINE))
    list_items = len(re.findall(r"^[-*+]\s", content, re.MULTILINE))
    total_lines = len(content.split("\n"))

    if code_blocks > 3 or code_lines > total_lines * 0.3:
        return "code"
    elif list_items > total_lines * 0.2:
        return "list"
    elif code_blocks > 0 or code_lines > 0:
        return "mixed"
    else:
        return "prose"


def extract_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown and return (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}, text

    frontmatter_text = match.group(1)
    body = text[match.end() :]

    metadata = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            metadata[key.strip()] = val.strip().strip('"')

    return metadata, body


def get_note_title(file_path: Path, body: str) -> str:
    """Extract note title from first H1 or use filename stem."""
    match = re.search(r"^# (.+)$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return file_path.stem


def chunk_markdown(file_path: Path, content: str) -> list[dict]:
    """
    Chunk markdown into sections with 400-token limit, overlap, and min size.
    Returns list of dicts: {text, index, context_info}
    """
    metadata, body = extract_frontmatter(content)
    title = get_note_title(file_path, body)

    chunks = []
    chunk_index = 0

    # Split on ## and ### headers
    sections = re.split(r"^(##+ .+)$", body, flags=re.MULTILINE)

    current_section = ""
    current_section_header = ""

    for i, section in enumerate(sections):
        if section.startswith("##"):
            if current_section:
                chunks.extend(
                    _split_section(
                        current_section,
                        title,
                        current_section_header,
                        chunk_index,
                    )
                )
                chunk_index += len(chunks)
            current_section_header = section.strip()
            current_section = ""
        else:
            current_section += section

    # Process final section
    if current_section.strip():
        chunks.extend(
            _split_section(
                current_section,
                title,
                current_section_header,
                chunk_index,
            )
        )

    return chunks


def _split_section(
    section: str,
    title: str,
    section_header: str,
    chunk_index: int,
) -> list[dict]:
    """Split a section with adaptive chunk sizes based on content type.

    Code and lists use smaller chunks (300 tokens) for precision.
    Prose uses larger chunks (400 tokens) for coherence.
    """
    chunks = []

    # Determine optimal chunk size based on content type
    content_type = detect_content_type(section)
    chunk_size = {
        "code": 300,  # Smaller for code precision
        "list": 300,  # Smaller for list items
        "mixed": 350,  # Medium for mixed content
        "prose": 400,  # Larger for prose coherence
    }.get(content_type, 400)

    if estimate_tokens(section) <= chunk_size:
        # Merge tiny sections upward
        if estimate_tokens(section) < 50:
            return []  # Merge to parent

        context_prefix = f"From {title}. "
        if section_header:
            context_prefix += f"Section: {section_header}. "

        chunk_text = context_prefix + section.strip()
        chunks.append(
            {
                "text": chunk_text,
                "index": chunk_index,
                "title": title,
                "section_header": section_header,
            }
        )
        return chunks

    # Split on paragraph boundaries (\n\n) with overlap
    paragraphs = re.split(r"\n\n+", section.strip())
    current_chunk = ""
    chunk_idx = chunk_index

    for para in paragraphs:
        test_chunk = current_chunk + para + "\n\n"
        if estimate_tokens(test_chunk) > chunk_size and current_chunk:
            # Finalize current chunk
            context_prefix = f"From {title}. "
            if section_header:
                context_prefix += f"Section: {section_header}. "

            chunk_text = context_prefix + current_chunk.strip()
            chunks.append(
                {
                    "text": chunk_text,
                    "index": chunk_idx,
                    "title": title,
                    "section_header": section_header,
                }
            )
            chunk_idx += 1

            # Start new chunk with overlap
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"

    # Final chunk
    if current_chunk.strip():
        context_prefix = f"From {title}. "
        if section_header:
            context_prefix += f"Section: {section_header}. "

        chunk_text = context_prefix + current_chunk.strip()
        chunks.append(
            {
                "text": chunk_text,
                "index": chunk_idx,
                "title": title,
                "section_header": section_header,
            }
        )

    return chunks
