"""
document_processor.py — Document Loading & Chunking

Handles loading PDF, TXT, and DOCX files using LangChain loaders,
then splits them into overlapping chunks for embedding.
Each chunk retains metadata (source file, page number) for citation.
"""

import os
from typing import List, Optional

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# Mapping of file extensions to their LangChain loader class
SUPPORTED_EXTENSIONS = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".docx": Docx2txtLoader,
}


class DocumentProcessor:
    """Loads documents from disk and splits them into chunks with metadata."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: Maximum number of characters per chunk.
            chunk_overlap: Number of overlapping characters between consecutive chunks.
                           Overlap ensures context isn't lost at chunk boundaries.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _get_loader(self, file_path: str):
        """Select the correct LangChain loader based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        loader_class = SUPPORTED_EXTENSIONS.get(ext)
        if loader_class is None:
            raise ValueError(
                f"Unsupported file type: '{ext}'. "
                f"Supported types: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
            )
        return loader_class(file_path)

    def load_and_split(
        self,
        file_path: str,
        doc_id: str,
        original_filename: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[Document]:
        """
        Load a document and split it into chunks.

        Args:
            file_path: Path to the file on disk.
            doc_id: Unique identifier for this document (used for deletion).
            original_filename: The user-facing filename for citations.
            chunk_size: Override the default chunk size.
            chunk_overlap: Override the default chunk overlap.

        Returns:
            List of LangChain Document objects, each with metadata:
              - source: original filename
              - doc_id: unique document identifier
              - page: page number (if available, else 0)
              - chunk_index: sequential chunk number within the document
        """
        # Load raw documents using the appropriate loader
        loader = self._get_loader(file_path)
        raw_documents = loader.load()

        if not raw_documents:
            raise ValueError(f"No content could be extracted from '{original_filename}'.")

        # Configure the text splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or self.chunk_size,
            chunk_overlap=chunk_overlap or self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Split into chunks
        chunks = splitter.split_documents(raw_documents)

        # Enrich metadata on every chunk for source citation
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "doc_id": doc_id,
                "source": original_filename,
                "chunk_index": i,
                # Preserve page number from PDF loader; default to 0 for others
                "page": chunk.metadata.get("page", 0),
            })

        return chunks

    @staticmethod
    def is_supported(filename: str) -> bool:
        """Check if a file extension is supported."""
        ext = os.path.splitext(filename)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def supported_extensions() -> List[str]:
        """Return list of supported file extensions."""
        return list(SUPPORTED_EXTENSIONS.keys())
