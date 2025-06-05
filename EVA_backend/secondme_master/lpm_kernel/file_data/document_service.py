# file_data/service.py
from pathlib import Path
from typing import List, Dict, Optional
import os
from sqlalchemy import select

from lpm_kernel.common.repository.database_session import DatabaseSession
from lpm_kernel.common.repository.vector_store_factory import VectorStoreFactory
from lpm_kernel.file_data.document_dto import DocumentDTO, CreateDocumentRequest
from lpm_kernel.file_data.exceptions import FileProcessingError
from lpm_kernel.kernel.l0_base import InsightKernel, SummaryKernel
from lpm_kernel.models.memory import Memory
from .document import Document
from .document_repository import DocumentRepository
from .dto.chunk_dto import ChunkDTO
from .embedding_service import EmbeddingService
from .process_factory import ProcessorFactory
from .process_status import ProcessStatus

from lpm_kernel.configs.logging import get_train_process_logger
logger = get_train_process_logger()


class DocumentService:
    def __init__(self):
        self._repository = DocumentRepository()
        self._insight_kernel = InsightKernel()
        self._summary_kernel = SummaryKernel()
        self.vector_store = VectorStoreFactory.get_instance()
        self.embedding_service = EmbeddingService()

    def create_document(self, data: CreateDocumentRequest) -> Document:
        """
        create new document
        Args:
            data (CreateDocumentRequest): create doc request
        Returns:
            Document: create doc object
        """
        doc = Document(
            name=data.name,
            title=data.title,
            mime_type=data.mime_type,
            user_description=data.user_description,
            url=str(data.url) if data.url else None,
            document_size=data.document_size,
            extract_status=data.extract_status,
            embedding_status=ProcessStatus.INITIALIZED,
            raw_content=data.raw_content,
        )
        return self._repository.create(doc)

    def list_documents(self) -> List[Document]:
        """
        get all doc list
        Returns:
            List[Document]: doc object list
        """
        return self._repository.list()

    def scan_directory(
        self, directory_path: str, recursive: bool = False
    ) -> List[DocumentDTO]:
        """
        scan and process files
        Args:
            directory_path (str): dir to scan
            recursive (bool, optional): if recursive scan. Defaults to False.
        Returns:
            List[Document]: processed doc object list
        Raises:
            FileProcessingError: when dir not exist or failed
        """

        path = Path(directory_path)
        if not path.is_dir():
            raise FileProcessingError(f"{directory_path} is not a directory")

        documents_dtos: List[DocumentDTO] = []
        pattern = "**/*" if recursive else "*"

        # list all files
        files = list(path.glob(pattern))
        logger.info(f"Found files: {files}")

        for file_path in files:
            if file_path.is_file():
                try:
                    logger.info(f"Processing file: {file_path}")
                    doc = ProcessorFactory.auto_detect_and_process(str(file_path))

                    # create CreateDocumentRequest obj to database
                    request = CreateDocumentRequest(
                        name=doc.name,
                        title=doc.name,
                        mime_type=doc.mime_type,
                        user_description="Auto scanned document",
                        document_size=doc.document_size,
                        url=str(file_path.absolute()),
                        raw_content=doc.raw_content,
                        extract_status=doc.extract_status,
                        embedding_status=ProcessStatus.INITIALIZED,
                    )
                    saved_doc = self.create_document(request)

                    documents_dtos.append(saved_doc.to_dto())
                    logger.info(f"Successfully processed and saved: {file_path}")

                except Exception as e:
                    # add detailed error log
                    logger.exception(
                        f"Error processing file {file_path}"
                    )
                    continue

        logger.info(f"Total documents processed and saved: {len(documents_dtos)}")
        return documents_dtos

    def _analyze_document(self, doc: DocumentDTO) -> DocumentDTO:
        """
        analyze one file
        Args:
            doc (Document): doc to analyze
        Returns:
            Document: updated doc
        Raises:
            Exception: error occurred
        """
        try:
            # generate insight
            insight_result = self._insight_kernel.analyze(doc)

            # generate summary
            summary_result = self._summary_kernel.analyze(
                doc, insight_result["insight"]
            )

            # update database
            updated_doc = self._repository.update_document_analysis(
                doc.id, insight_result, summary_result
            )

            return updated_doc

        except Exception as e:
            logger.error(f"Document {doc.id} analysis failed: {str(e)}", exc_info=True)
            # update status as failed
            self._update_analyze_status_failed(doc.id)
            raise

    def analyze_document(self, document_id: int) -> DocumentDTO:
        """
        Analyze a single document by ID
        
        Args:
            document_id (int): ID of document to analyze
            
        Returns:
            DocumentDTO: The analyzed document
            
        Raises:
            ValueError: If document not found
            Exception: If analysis fails
        """
        try:
            # Get document
            document = self._repository.find_one(document_id)
            if not document:
                raise ValueError(f"Document not found with id: {document_id}")
                
            # Perform analysis
            return self._analyze_document(document)
                
        except ValueError as e:
            logger.error(f"Document {document_id} not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing document {document_id}: {str(e)}", exc_info=True)
            self._update_analyze_status_failed(document_id)
            raise

    def _update_analyze_status_failed(self, doc_id: int) -> None:
        """update status as failed"""
        try:
            with self._repository._db.session() as session:
                document = session.get(self._repository.model, doc_id)
                if document:
                    document.analyze_status = ProcessStatus.FAILED
                    session.commit()
                    logger.debug(f"Updated analyze status for document {doc_id} to FAILED")
                else:
                    logger.warning(f"Document not found with id: {doc_id}")
        except Exception as e:
            logger.error(f"Error updating document analyze status: {str(e)}")

    def check_all_documents_embeding_status(self) -> bool:
        """
        Check if there are any documents that need embedding
        Returns:
            bool: True if there are documents that need embedding, False otherwise
        """
        # ... 省略部分 ...

    def delete_file_by_name(self, filename: str) -> bool:
        """
        Args:
            filename (str): name to delete
            
        Returns:
            bool: if success
            
        Raises:
            Exception: error occurred
        """
        logger.info(f"Starting to delete file: {filename}")
        
        try:
            # 1. search memories
            db = DatabaseSession()
            memory = None
            document_id = None
            
            with db._session_factory() as session:
                query = select(Memory).where(Memory.name == filename)
                result = session.execute(query)
                memory = result.scalar_one_or_none()
                
                if not memory:
                    logger.warning(f"File record not found: {filename}")
                    return False
                
                # get related document_id
                document_id = memory.document_id
                
                # get filepath
                file_path = memory.path
                
                # 2. delete memory
                session.delete(memory)
                session.commit()
                logger.info(f"Deleted record from memories table: {filename}")
            
            # if no related document, only delete physical file
            if not document_id:
                # delete physical file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted physical file: {file_path}")
                return True
            
            # 3. get doc obj
            document = self._repository.get_by_id(document_id)
            if not document:
                logger.warning(f"Corresponding document record not found, ID: {document_id}")
                # if no document record, delete physical file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted physical file: {file_path}")
                return True
            
            # 4. get all chunks
            chunks = self._repository.find_chunks(document_id)
            
            # 5. delete doc embedding from ChromaDB
            try:
                self.embedding_service.document_collection.delete(
                    ids=[str(document_id)]
                )
                logger.info(f"Deleted document embedding from ChromaDB, ID: {document_id}")
            except Exception as e:
                logger.error(f"Error deleting document embedding: {str(e)}")
            
            # 6. delete all chunk embedding from ChromaDB
            if chunks:
                try:
                    chunk_ids = [str(chunk.id) for chunk in chunks]
                    self.embedding_service.chunk_collection.delete(
                        ids=chunk_ids
                    )
                    logger.info(f"Deleted {len(chunk_ids)} chunk embeddings from ChromaDB")
                except Exception as e:
                    logger.error(f"Error deleting chunk embeddings: {str(e)}")
            
            # 7. delete all chunks embedding from ChromaDB
            with db._session_factory() as session:
                from lpm_kernel.file_data.models import ChunkModel
                session.query(ChunkModel).filter(
                    ChunkModel.document_id == document_id
                ).delete()
                session.commit()
                logger.info(f"Deleted all related chunks")
                
                # delete doc record
                doc_entity = session.get(Document, document_id)
                if doc_entity:
                    session.delete(doc_entity)
                    session.commit()
                    logger.info(f"Deleted document record from database, ID: {document_id}")
            
            # 8. delete physical file
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted physical file: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}", exc_info=True)
            raise 