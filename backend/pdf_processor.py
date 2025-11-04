import base64
import io
import fitz  # PyMuPDF
from PIL import Image
from typing import List, Dict, Any, Iterator, Tuple, AsyncIterator
from langchain_unstructured import UnstructuredLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from loguru import logger
import tempfile
import os

class PDFProcessor:
    """PDF document processor"""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def process_pdf_stream(self, file_content: bytes, filename: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream PDF document processing
        Return processing progress and results
        """
        tmp_file_path = None
        try:
            # Step 1: Save temporary file
            yield {
                "type": "progress",
                "step": "saving_file",
                "message": f"Saving file {filename}...",
                "progress": 10
            }

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name

            try:
                # Step 2: Load PDF document
                yield {
                    "type": "progress",
                    "step": "loading_pdf",
                    "message": "Analyzing PDF structure...",
                    "progress": 30
                }

                # Use UnstructuredLoader to load PDF (full OCR configuration)
                try:
                    loader = UnstructuredLoader(
                        file_path=tmp_file_path,
                        partition_via_api=False,  # Local processing, no API
                        strategy="hi_res",  # High-resolution strategy for better complex PDF handling
                        extract_images_in_pdf=True,  # Enable image extraction
                        infer_table_structure=True,  # Enable table inference
                        ocr_languages=["eng"],  # Use English OCR
                        chunking_strategy="by_title"  # Chunk by title
                    )
                except ImportError as e:
                    error_msg = f"Missing required dependencies: {str(e)}. Please ensure unstructured[local-inference] and Tesseract OCR are installed"
                    logger.error(error_msg)
                    yield {
                        "type": "error",
                        "error": error_msg
                    }
                    return
                except Exception as e:
                    error_msg = f"PDF loader initialization failed: {str(e)}"
                    logger.error(error_msg)
                    yield {
                        "type": "error",
                        "error": error_msg
                    }
                    return

                # Load documents
                documents = []
                for doc in loader.lazy_load():
                    documents.append(doc)

                logger.info(f"PDF loading complete, total {len(documents)} document blocks")
                
                # Step 3: Text chunking
                yield {
                    "type": "progress",
                    "step": "splitting_text",
                    "message": f"Splitting text, {len(documents)} original blocks...",
                    "progress": 60
                }

                # Merge all document content and debug output
                full_text = "\n\n".join([doc.page_content for doc in documents])
                logger.info(f"Merged text length: {len(full_text)} characters")

                # Debug: output first 200 characters to see what was extracted
                preview = full_text[:200] if full_text else "Empty content"
                logger.info(f"Text preview: {repr(preview)}")

                # Check document metadata
                for i, doc in enumerate(documents):
                    logger.info(f"Document {i}: length={len(doc.page_content)}, metadata={doc.metadata}")
                    if doc.page_content:
                        logger.info(f"Document {i} preview: {repr(doc.page_content[:100])}")

                # Verify extracted content is not empty
                if not full_text or not full_text.strip():
                    error_msg = "PDF document extraction failed: Could not extract any text content. This may be a scanned PDF. Please ensure Tesseract OCR is installed and configured correctly."
                    logger.error(error_msg)
                    yield {
                        "type": "error",
                        "error": error_msg
                    }
                    return

                # Use RecursiveCharacterTextSplitter for intelligent chunking
                text_chunks = self.text_splitter.split_text(full_text)
                logger.info(f"Text chunking complete, total {len(text_chunks)} chunks")

                # Step 4: Build document chunks
                yield {
                    "type": "progress",
                    "step": "building_chunks",
                    "message": f"Building {len(text_chunks)} document chunks...",
                    "progress": 80
                }

                # Build document chunks with metadata (including page number information)
                document_chunks = []
                for i, chunk in enumerate(text_chunks):
                    if chunk.strip():  # Filter empty chunks
                        # Try to get page number from original document blocks
                        page_number = 1  # Default page number
                        if documents:
                            # Find original document block containing this chunk content
                            for doc in documents:
                                if hasattr(doc, 'metadata') and 'page_number' in doc.metadata:
                                    if chunk.strip()[:50] in doc.page_content:
                                        page_number = doc.metadata.get('page_number', 1)
                                        break

                        doc_chunk = {
                            "id": f"{filename}_{i}",
                            "content": chunk.strip(),
                            "metadata": {
                                "source": filename,
                                "chunk_id": i,
                                "chunk_size": len(chunk),
                                "total_chunks": len(text_chunks),
                                "page_number": page_number,
                                "reference_id": f"[{i+1}]",
                                "source_info": f"{filename} - Page {page_number}"
                            }
                        }
                        document_chunks.append(doc_chunk)

                # Step 5: Complete processing
                yield {
                    "type": "progress",
                    "step": "completed",
                    "message": f"Processing complete! Generated {len(document_chunks)} document chunks",
                    "progress": 100
                }

                # Return processing results
                yield {
                    "type": "result",
                    "chunks": document_chunks,
                    "summary": {
                        "filename": filename,
                        "total_chunks": len(document_chunks),
                        "total_characters": sum(len(chunk["content"]) for chunk in document_chunks),
                        "processing_strategy": "hi_res"
                    }
                }

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            yield {
                "type": "error",
                "error": f"PDF processing failed: {str(e)}"
            }
    
    def pdf_page_to_base64(self, pdf_content: bytes, page_number: int) -> str:
        """
        Convert PDF page to base64-encoded image
        For multimodal model processing
        """
        try:
            # Open PDF from memory
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            page = pdf_document.load_page(page_number - 1)  # 0-based indexing
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            pdf_document.close()

            return base64.b64encode(buffer.getvalue()).decode("utf-8")

        except Exception as e:
            logger.error(f"PDF page to image conversion failed: {str(e)}")
            raise

    async def extract_pdf_pages_as_images(self, file_content: bytes, max_pages: int = 5) -> List[str]:
        """
        Extract first few PDF pages as images for multimodal processing
        """
        try:
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            total_pages = len(pdf_document)
            pages_to_extract = min(max_pages, total_pages)

            images = []
            for page_num in range(pages_to_extract):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
                images.append(base64_image)

            pdf_document.close()
            logger.info(f"Extracted {len(images)} PDF page images")
            return images

        except Exception as e:
            logger.error(f"PDF image extraction failed: {str(e)}")
            raise 