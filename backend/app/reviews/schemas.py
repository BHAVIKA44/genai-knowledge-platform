from pydantic import BaseModel

from app.documents.schemas import DocumentResponse
from app.knowledge_quality.models import QualityFinding


class ContributorReviewDetails(BaseModel):
    document: DocumentResponse
    finding: QualityFinding


class ContributorReviewDecision(BaseModel):
    action: str
