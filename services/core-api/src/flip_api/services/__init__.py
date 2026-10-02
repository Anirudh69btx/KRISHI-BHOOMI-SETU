"""
FLIP Core API — services package (Segment 05)
Exposes all service classes for easy import.
"""
from .ingestion_service    import IngestionService, BulkIngestionRequest, IngestionResult
from .anomaly_service      import AnomalyService
from .health_scoring_service import HealthScoringService

__all__ = [
    "IngestionService",
    "BulkIngestionRequest",
    "IngestionResult",
    "AnomalyService",
    "HealthScoringService",
]
