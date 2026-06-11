from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class EmailAnalysis:
    category: str
    priority: str
    summary: str
    recommended_action: str
    detected_deadline: Optional[str] = None


@dataclass
class ExtractedTask:
    task_text: str
    owner: str = "Office Team"
    due_date: Optional[str] = None
    priority: str = "medium"


@dataclass
class DraftReplyResult:
    draft_text: str
    category: str
    ai_generated: bool = False


@dataclass
class ProcessedEmail:
    email_id: int
    category: str
    priority: str
    summary: str
    recommended_action: str
    detected_deadline: Optional[str]
    tasks: List[ExtractedTask]
    draft_reply: DraftReplyResult
    # Phase 4 — processing metadata
    processing_mode: str = "Rule-based mode"
    ai_used: bool = False
    fallback_used: bool = True
    confidence: float = 0.0
    safety_note: str = ""


@dataclass
class ProcessingReport:
    processed: int = 0
    tasks_created: int = 0
    drafts_generated: int = 0
    ai_used_count: int = 0
    fallback_used_count: int = 0
    errors: List[str] = field(default_factory=list)
