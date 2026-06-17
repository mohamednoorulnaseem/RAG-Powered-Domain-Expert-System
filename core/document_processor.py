"""
RAG Expert System - Document Processor
Handles document ingestion: loading, parsing, and text extraction
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain_core.documents import Document
from loguru import logger

from config import get_settings


@dataclass
class ProcessedDocument:
    """Represents a processed document with metadata"""

    doc_id: str
    filename: str
    file_path: str
    file_type: str
    file_size: int
    num_pages: int
    num_chunks: int
    chunks: List[Document]
    processed_at: datetime
    checksum: str


class DocumentProcessor:
    """
    Document Processing Pipeline

    Flow:
    1. Load document (PDF, DOCX, TXT, MD)
    2. Extract text content
    3. Split into chunks with overlap
    4. Add metadata to each chunk
    """

    def __init__(self):
        self.settings = get_settings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Mapping of file extensions to loaders
        self.loader_mapping = {
            ".pdf": PyPDFLoader,
            ".docx": Docx2txtLoader,
            ".txt": TextLoader,
            ".md": UnstructuredMarkdownLoader,
        }

        logger.info(
            f"DocumentProcessor initialized with chunk_size={self.settings.chunk_size}, overlap={self.settings.chunk_overlap}"
        )

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of file for deduplication"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _generate_doc_id(self, filename: str, checksum: str) -> str:
        """Generate unique document ID"""
        return f"{filename}_{checksum[:8]}"

    def _get_loader(self, file_path: str):
        """Get appropriate document loader based on file extension"""
        extension = Path(file_path).suffix.lower()

        if extension not in self.loader_mapping:
            raise ValueError(
                f"Unsupported file type: {extension}. Supported types: {list(self.loader_mapping.keys())}"
            )

        loader_class = self.loader_mapping[extension]
        return loader_class(file_path)

    def _extract_text(self, file_path: str) -> List[Document]:
        """Extract text from document using appropriate loader"""
        extension = Path(file_path).suffix.lower()

        # Custom PDF handling to avoid 'bbox' errors and empty content from LangChain loader
        if extension == ".pdf":
            try:
                import pypdf

                reader = pypdf.PdfReader(file_path)
                documents = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        documents.append(
                            Document(
                                page_content=text,
                                metadata={
                                    "source": Path(file_path).name,
                                    "page": i + 1,
                                },
                            )
                        )

                logger.info(
                    f"Extracted {len(documents)} pages from {Path(file_path).name} (Direct pypdf)"
                )
                return documents
            except Exception as e:
                logger.warning(
                    f"Direct PDF extraction failed: {e}. Falling back to loader."
                )
                # Fallback to original logic if custom fails

        loader = self._get_loader(file_path)
        documents = loader.load()

        logger.info(f"Extracted {len(documents)} pages from {Path(file_path).name}")
        return documents

    def _chunk_documents(
        self, documents: List[Document], filename: str
    ) -> List[Document]:
        """
        Split documents into chunks with overlap

        Why overlap?
        - Ensures no sentence is cut in half
        - Preserves context at chunk boundaries
        - Improves retrieval quality
        """
        all_chunks = []

        for page_num, doc in enumerate(documents, 1):
            # Split this page into chunks
            chunks = self.text_splitter.split_text(doc.page_content)

            # Create Document objects with rich metadata
            for chunk_num, chunk_text in enumerate(chunks, 1):
                chunk_doc = Document(
                    page_content=chunk_text,
                    metadata={
                        "source": filename,
                        "page": page_num,
                        "chunk": chunk_num,
                        "total_chunks_in_page": len(chunks),
                        "char_count": len(chunk_text),
                        "word_count": len(chunk_text.split()),
                        "chunk_id": f"{filename}_p{page_num}_c{chunk_num}",
                    },
                )
                all_chunks.append(chunk_doc)

        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} pages")
        return all_chunks

    def process_document(self, file_path: str) -> ProcessedDocument:
        """
        Main document processing pipeline

        Steps:
        1. Validate file
        2. Calculate checksum (for deduplication)
        3. Extract text
        4. Split into chunks
        5. Add metadata
        6. Return ProcessedDocument
        """
        file_path = Path(file_path)

        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate file size
        file_size = file_path.stat().st_size
        max_size = self.settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            raise ValueError(
                f"File too large: {file_size / (1024*1024):.2f}MB (max: {self.settings.max_file_size_mb}MB)"
            )

        # Validate file type
        if file_path.suffix.lower() not in self.settings.allowed_extensions:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        logger.info(f"Processing document: {file_path.name}")

        # Calculate checksum for deduplication
        checksum = self._calculate_checksum(str(file_path))
        doc_id = self._generate_doc_id(file_path.name, checksum)

        # Extract text from document
        documents = self._extract_text(str(file_path))

        # Split into chunks
        chunks = self._chunk_documents(documents, file_path.name)

        # Add document-level metadata to each chunk
        for chunk in chunks:
            chunk.metadata.update(
                {
                    "doc_id": doc_id,
                    "file_type": file_path.suffix.lower(),
                    "file_size": file_size,
                    "checksum": checksum,
                    "processed_at": datetime.now().isoformat(),
                }
            )

        processed_doc = ProcessedDocument(
            doc_id=doc_id,
            filename=file_path.name,
            file_path=str(file_path),
            file_type=file_path.suffix.lower(),
            file_size=file_size,
            num_pages=len(documents),
            num_chunks=len(chunks),
            chunks=chunks,
            processed_at=datetime.now(),
            checksum=checksum,
        )

        logger.success(
            f"Successfully processed {file_path.name}: {len(chunks)} chunks from {len(documents)} pages"
        )
        return processed_doc

    def process_multiple_documents(
        self, file_paths: List[str]
    ) -> List[ProcessedDocument]:
        """Process multiple documents"""
        results = []
        for file_path in file_paths:
            try:
                result = self.process_document(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        return results


# Convenience function for quick processing
def process_document(file_path: str) -> ProcessedDocument:
    """Quick function to process a single document"""
    processor = DocumentProcessor()
    return processor.process_document(file_path)
