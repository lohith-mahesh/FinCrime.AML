from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class EnterpriseApp(str, Enum):
    CORE_BANKING = "core_banking"
    GLOBAL_SANCTIONS = "global_sanctions"
    HR_PORTAL = "hr_portal"

class ViolationCategory(str, Enum):
    NONE = "NONE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    SANCTIONS_MATCH = "SANCTIONS_MATCH"
    STRUCTURING = "STRUCTURING"
    LAYERING = "LAYERING"

class AMLAction(BaseModel):
    target_app: EnterpriseApp = Field(..., description="The enterprise application to query.")
    command: str = Field(..., description="The specific command to execute.")
    account_id: Optional[str] = Field(None, description="The target account ID, if applicable.")
    search_name: Optional[str] = Field(None, description="The name to search in the sanctions database.")
    page: int = Field(1, description="Pagination index for transaction queries.")
    violation_category: ViolationCategory = Field(ViolationCategory.NONE, description="The category of the violation if escalating/clearing.")
    verified_dob: Optional[str] = Field(None, description="The verified Date of Birth for sanctions clearing.")
    complicit_account_ids: List[str] = Field(default_factory=list, description="A list of complicit account IDs if escalating a network.")
    rationale: Optional[str] = Field("No rationale provided", description="The justification for the action.")
    note_content: Optional[str] = Field(None, description="The text content to save to the internal scratchpad.")

class AMLObservation(BaseModel):
    alert_id: str
    alert_trigger: str
    command_status: str
    database_response: str
    documented_evidence: List[str]
    scratchpad: List[str]
    reward: float
    done: bool
