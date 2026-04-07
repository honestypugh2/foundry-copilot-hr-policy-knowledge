import hashlib 
import re 
from dataclasses import dataclass 
from typing import List 

 

@dataclass(frozen=True) 
class TextChunk: 
    chunk_id: str
    chunk_index: int
    text: str


def _stable_chunk_id(document_id: str, chunk_index: int, chunk_text: str) -> str: 
    h = hashlib.md5(chunk_text.encode("utf-8", errors="ignore")).hexdigest() 
    return f"{document_id}:{chunk_index}:{h}" 

 
def fixed_size_chunking(
    text: str,
    size: int = 500,
    overlap: int = 50,
    document_id: str = "document",
) -> List[TextChunk]:
    """
    Splits text into fixed-size chunks with optional overlap and returns
    a list of `TextChunk` objects including `chunk_id` and `chunk_index`.

    Args:
        text: The input string.
        size: The maximum size of each chunk. Must be > 0.
        overlap: Overlap between consecutive chunks. Must be >= 0 and < size.
        document_id: Identifier used when generating stable chunk ids.

    Returns:
        A list of `TextChunk` instances.
    """
    if size <= 0:
        raise ValueError("size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    chunks: List[TextChunk] = []
    if not text:
        return chunks

    step = size - overlap
    text_length = len(text)
    index = 0
    start = 0

    while start < text_length:
        chunk_text = text[start : start + size]
        chunk_id = _stable_chunk_id(document_id, index, chunk_text)
        chunks.append(TextChunk(chunk_id=chunk_id, chunk_index=index, text=chunk_text))

        # Stop once this chunk reaches the end to avoid tiny trailing overlap-only chunks.
        if start + size >= text_length:
            break

        start += step
        index += 1

    return chunks