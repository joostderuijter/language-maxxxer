"""Request/response models. The frontend's TypeScript client is generated from these (ADR-7): change them and
`make api-client` + the frontend type check tell you what broke."""

from pydantic import BaseModel, Field

from ..knowledge.events import EventKind, WordState


class Health(BaseModel):
    ok: bool
    version: str


class Language(BaseModel):
    code: str
    name: str


class Progress(BaseModel):
    language: str
    words_known: int
    by_state: dict[str, int]


class AnalyzeRequest(BaseModel):
    language: str = Field(examples=['ko'])
    text: str = Field(max_length=20_000)


class AnalyzedToken(BaseModel):
    surface: str
    start: int
    end: int
    lemmas: list[str]
    pos: str
    key: str
    weak: bool
    state: WordState  # the user's state for the best-known candidate lemma
    lemma: str  # the candidate lemma that state belongs to


class AnalyzeResponse(BaseModel):
    language: str
    tokens: list[AnalyzedToken]


class EventRequest(BaseModel):
    language: str
    lemma: str = Field(min_length=1, max_length=200)
    kind: EventKind


class WordStatus(BaseModel):
    lemma: str
    state: WordState
    confidence: float


class ImportRequest(BaseModel):
    language: str
    csv: str = Field(
        description='lines "lemma,state"; state = known|learning|seen|ignored|unknown, or the '
        'Migaku-style numbers 2=known 1=seen 0=learning 3=ignored'
    )
    source: str = Field(default='import:csv', max_length=64)


class ImportResult(BaseModel):
    imported: int
    skipped: int
