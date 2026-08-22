"""Document loader for reading files into Document models."""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from superapp.models import Document


class DocumentLoader:
    """Loads documents from files or strings into Document objects."""

    def load_file(self, file_path: str) -> Document:
        """Load a single .txt or .md file, extract content and metadata."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        stat = path.stat()
        metadata = {
            "filename": path.name,
            "file_size": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

        return Document(
            filename=path.name,
            content=content,
            metadata=metadata
        )

    def load_from_text(self, text: str, filename: str) -> Document:
        """Create a Document from raw text."""
        metadata = {
            "filename": filename,
            "file_size": len(text.encode("utf-8")),
            "modified_time": datetime.now().isoformat()
        }
        return Document(
            filename=filename,
            content=text,
            metadata=metadata
        )

    def load_directory(self, dir_path: str, extensions: Optional[List[str]] = None) -> List[Document]:
        """Load all matching files from a directory."""
        path = Path(dir_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        if extensions is None:
            extensions = [".txt", ".md"]
        else:
            extensions = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]

        documents = []
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    try:
                        doc = self.load_file(full_path)
                        documents.append(doc)
                    except Exception as e:
                        print(f"Error loading {full_path}: {e}")

        return documents
