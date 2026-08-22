"""Document chunker for splitting documents into smaller chunks."""

import re
from typing import List, Optional

from superapp.models import Document, Chunk
from superapp.config import settings


class DocumentChunker:
    """Chunks documents into smaller segments for embedding and analysis."""

    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        """Initialize with chunk size and overlap from settings if not provided."""
        self.chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Section-aware chunking that respects markdown headings (##) and paragraph boundaries.
        Splits on headings first, then on paragraph breaks if chunks are still too large,
        then on sentences as last resort.
        """
        chunks = []
        content = document.content
        chunk_index = 0

        # Split on headings: looks for lines starting with '## '
        sections = re.split(r'(?=\n##\s+)', content)
        if not sections:
            sections = [content]

        for section in sections:
            if not section.strip():
                continue

            if len(section) <= self.chunk_size:
                chunks.extend(self._create_chunks_from_text(section, document, chunk_index, offset=content.find(section)))
                chunk_index += len(chunks)  # rough estimation, we'll fix indexes later
            else:
                # Split by paragraphs
                paragraphs = re.split(r'\n\s*\n', section)
                current_text = ""
                
                for p in paragraphs:
                    if not p.strip():
                        continue
                        
                    if len(current_text) + len(p) + 2 <= self.chunk_size:
                        current_text += (p + "\n\n")
                    else:
                        if current_text:
                            chunks.extend(self._create_chunks_from_text(current_text.strip(), document, chunk_index, content.find(current_text.strip())))
                            chunk_index += 1
                        
                        if len(p) <= self.chunk_size:
                            current_text = p + "\n\n"
                        else:
                            # Split by sentences
                            sentences = re.split(r'(?<=[.!?])\s+', p)
                            sent_text = ""
                            for s in sentences:
                                if len(sent_text) + len(s) <= self.chunk_size:
                                    sent_text += (s + " ")
                                else:
                                    if sent_text:
                                        chunks.extend(self._create_chunks_from_text(sent_text.strip(), document, chunk_index, content.find(sent_text.strip())))
                                        chunk_index += 1
                                    sent_text = s + " "
                                    
                            if sent_text.strip():
                                chunks.extend(self._create_chunks_from_text(sent_text.strip(), document, chunk_index, content.find(sent_text.strip())))
                                chunk_index += 1
                            current_text = ""
                            
                if current_text.strip():
                    chunks.extend(self._create_chunks_from_text(current_text.strip(), document, chunk_index, content.find(current_text.strip())))
                    chunk_index += 1

        # Fix chunk indexes and start/end chars more accurately
        final_chunks = []
        current_idx = 0
        for i, c in enumerate(chunks):
            # This is a simplified reconstruction. For exact start_char/end_char, 
            # we do a search from the last found position to handle duplicates.
            start_char = content.find(c.content) if i == 0 else content.find(c.content, final_chunks[-1].start_char)
            if start_char == -1:
                start_char = 0
            
            c.chunk_index = current_idx
            c.start_char = start_char
            c.end_char = start_char + len(c.content)
            final_chunks.append(c)
            current_idx += 1

        return final_chunks

    def _create_chunks_from_text(self, text: str, document: Document, chunk_index: int, offset: int) -> List[Chunk]:
        """Helper to create a Chunk object from text."""
        # Note: accurate start_char and end_char are resolved in the main method
        if not text.strip():
            return []
            
        return [Chunk(
            document_id=document.id,
            content=text,
            chunk_index=chunk_index,
            start_char=max(0, offset),
            end_char=max(0, offset) + len(text)
        )]
