from pydantic import BaseModel, Field


class Chunk(BaseModel):
    id: str
    text: str
    metadata: dict = Field(default_factory=dict)

class IngestDocumentResponse(BaseModel):
    upserted_count: int
    chunks: list[Chunk]
    embedding_tokens: int = 0


class DeleteChunksRequest(BaseModel):
    tenant_id: str
    chunk_ids: list[str]


class DeleteChunksResponse(BaseModel):
    deleted_count: int


class RetrieveRequest(BaseModel):
    tenant_id: str
    query: str
    filters: dict | None = None
    top_k: int = 5


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    results: list[RetrievedChunk]
    crag_triggered: bool = False


class HistoryTurn(BaseModel):
    role: str  # "user" | "assistant" — matches session_turns.role's check constraint 1:1
    content: str


class GenerateRequest(BaseModel):
    """No context field — /generate decides for itself, via a
    search_documents tool call, whether the query needs a real retrieval
    (see app/routers/generate.py) rather than the caller always pre-fetching
    it. history is the caller's own record of prior turns in this session
    (the Backend's session_turns, already persisted there) — this service
    has no session storage of its own, it's handed what's relevant per call."""

    tenant_id: str
    query: str
    history: list[HistoryTurn] = Field(default_factory=list)
    # The tenant's own customization (Backend's tenants.system_prompt, None
    # if never set) — appended to the fixed base system prompt, never
    # substituted for it, so a tenant manager can shape persona/tone/domain
    # context without being able to switch off grounding. See
    # generate.py::_build_system_prompt.
    system_prompt: str | None = None