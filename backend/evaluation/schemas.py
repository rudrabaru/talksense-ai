from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


# 1. Speaker Attribution
class Segment(BaseModel):
    start: float
    end: float
    speaker: str


class SpeakerAttributionGT(BaseModel):
    segments: List[Segment]


# 2. Role Classification
class RoleClassificationGT(BaseModel):
    speaker_roles: Dict[str, Literal["sales_rep", "customer", "unknown"]]


# 3. Buying Signals
class BuyingSignalGT(BaseModel):
    signals: List[
        Literal["interested", "sounds_good", "makes_sense", "ready_to_buy", "other"]
    ]


# 4. Objections
class ObjectionGT(BaseModel):
    objections: List[
        Literal["pricing", "security", "timing", "authority", "competition", "other"]
    ]


# 5. Objection Handling
class ObjectionHandlingGT(BaseModel):
    handling_status: Dict[
        str, Literal["ignored", "acknowledged", "addressed", "resolved"]
    ]


# Unified Ground Truth
class GroundTruth(BaseModel):
    speaker_attribution: Optional[SpeakerAttributionGT] = None
    role_classification: Optional[RoleClassificationGT] = None
    buying_signals: Optional[BuyingSignalGT] = None
    objections: Optional[ObjectionGT] = None
    objection_handling: Optional[ObjectionHandlingGT] = None


# Base Schema for the JSON dataset
class EvaluationDataset(BaseModel):
    session_id: str
    ground_truth: GroundTruth
