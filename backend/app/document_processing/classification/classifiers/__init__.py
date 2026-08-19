from app.document_processing.classification.classifiers.composite import CompositeDocumentClassifier
from app.document_processing.classification.classifiers.filename import FilenameRuleClassifier
from app.document_processing.classification.classifiers.metadata import MetadataDocumentClassifier
from app.document_processing.classification.classifiers.structural import StructuralFileClassifier

__all__ = [
    "CompositeDocumentClassifier",
    "FilenameRuleClassifier",
    "MetadataDocumentClassifier",
    "StructuralFileClassifier",
]
