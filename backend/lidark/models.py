"""Modelos do banco (SQLite via SQLModel)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


def JsonField(default: Any = None) -> Any:
    factory = (lambda: default.copy()) if isinstance(default, (dict, list)) else (lambda: default)
    return Field(default_factory=factory, sa_column=Column(JSON))


def TextField(default: str = "") -> Any:
    return Field(default=default, sa_column=Column(Text))


class Channel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    # Dados puxados do YouTube (o canal nasce do login do Google)
    youtube_id: str = Field(default="", index=True)
    handle: str = ""
    avatar_url: str = ""
    banner_url: str = ""
    yt_description: str = TextField()
    stats: dict = JsonField({})  # subscribers, views, videos
    synced_at: Optional[datetime] = None
    setup_status: str = "ready"  # pending | configuring | ready
    radar: dict = JsonField({})  # radar de tendências: {"keywords": [...], "competitors": [...]}
    niche: str = ""
    audience: str = ""
    language: str = "pt-BR"
    description: str = TextField()
    # Orientações editoriais livres que entram em todo prompt de roteiro
    editorial_guide: str = TextField()
    tone: str = "envolvente, didático, curioso"
    formats: list = JsonField(["short"])  # short | long
    short_seconds: int = 65
    long_minutes: int = 6
    # Voz
    voice_provider: str = "edge"  # edge | gemini | kokoro
    voice_name: str = "pt-BR-AntonioNeural"
    voice_style: str = "Narrador brasileiro empolgado, ritmo rápido de vídeo curto"
    voice_rate: str = "+8%"
    # Visual
    visual_mode: str = "mixed"  # real | ai | mixed
    image_style: str = "fotografia histórica realista, cinematográfica, iluminação dramática, alta definição"
    template: str = "ouro"  # layout de vídeo (ver lidark/render/templates)
    templates: list = JsonField([])  # se 2+, alterna entre eles (variedade)
    series: dict = JsonField({})  # estrutura narrativa → nome da série (playlist)
    playlists: dict = JsonField({})  # nome da série → id da playlist no YouTube
    campaigns: list = JsonField([])  # campanhas sazonais: [{id, name, focus, start, end, share, active}]
    theme: dict = JsonField({})  # cores, textos e mascote do template
    music_mood: str = "epic cinematic documentary"
    music_volume: float = 0.12
    # Metadados
    default_hashtags: list = JsonField([])
    cta: str = "Siga para mais curiosidades!"
    # Automação
    auto_pilot: bool = False
    min_score_to_produce: int = 75
    posting_slots: list = JsonField(["12:00", "19:00"])
    color: str = "#d4a017"
    created_at: datetime = Field(default_factory=now)


class Idea(SQLModel, table=True):
    """Pauta."""
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, foreign_key="channel.id")
    title: str
    angle: str = TextField()
    summary: str = TextField()
    format: str = "short"
    origin: str = "auto"  # auto | manual | trend
    status: str = Field(default="new", index=True)  # new | approved | rejected | scripted | produced
    score: Optional[int] = None
    score_breakdown: dict = JsonField({})
    score_reason: str = TextField()
    predicted_views: Optional[int] = None
    fact_status: str = "pending"  # pending | verified | disputed | unverified
    facts: list = JsonField([])  # [{claim, verdict, sources:[url]}]
    sources: list = JsonField([])  # [{title, url, snippet}]
    tags: list = JsonField([])
    created_at: datetime = Field(default_factory=now)


class Script(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, foreign_key="channel.id")
    idea_id: Optional[int] = Field(default=None, foreign_key="idea.id")
    format: str = "short"
    title: str
    hook: str = TextField()
    # cenas: [{text, visual: {kind: real|ai, query, prompt}, emphasis:[...]}]
    scenes: list = JsonField([])
    description: str = TextField()
    tags: list = JsonField([])
    hashtags: list = JsonField([])
    thumbnail_text: str = ""
    status: str = Field(default="draft", index=True)  # draft | approved | rejected
    quality_score: Optional[int] = None
    review_notes: str = TextField()
    fact_check: list = JsonField([])
    sources: list = JsonField([])
    variety: dict = JsonField({})  # plano de variedade (estrutura, gancho, CTA, duração...)
    version: int = 1
    created_at: datetime = Field(default_factory=now)

    @property
    def full_text(self) -> str:
        return " ".join(s.get("text", "").strip() for s in self.scenes)


class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, foreign_key="channel.id")
    script_id: int = Field(foreign_key="script.id")
    format: str = "short"
    status: str = Field(default="queued", index=True)  # queued | rendering | ready | failed | published
    path: str = ""
    thumbnail_path: str = ""
    duration: float = 0
    assets: dict = JsonField({})
    error: str = TextField()
    created_at: datetime = Field(default_factory=now)


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str = Field(index=True)
    channel_id: Optional[int] = Field(default=None, index=True)
    ref_id: Optional[int] = None
    title: str = ""
    payload: dict = JsonField({})
    status: str = Field(default="queued", index=True)  # queued | running | done | failed | cancelled
    progress: float = 0
    stage: str = ""
    log: str = TextField()
    error: str = TextField()
    result: dict = JsonField({})
    created_at: datetime = Field(default_factory=now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class Account(SQLModel, table=True):
    """Conta conectada de uma plataforma (YouTube)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, foreign_key="channel.id")
    platform: str  # youtube
    display_name: str = ""
    external_id: str = ""
    credentials: dict = JsonField({})
    connected_at: datetime = Field(default_factory=now)


class Publication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True, foreign_key="channel.id")
    video_id: Optional[int] = Field(default=None, foreign_key="video.id")  # None = vídeo importado da plataforma
    account_id: int = Field(foreign_key="account.id")
    platform: str
    status: str = Field(default="scheduled", index=True)  # scheduled | uploading | published | failed
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    title: str = ""
    description: str = TextField()
    privacy: str = "public"
    external_id: str = ""
    url: str = ""
    duration: float = 0
    thumbnail_url: str = ""
    error: str = TextField()
    links: list = JsonField([])  # comentários de ligação Short ↔ longo já feitos (ids de vídeo)
    created_at: datetime = Field(default_factory=now)


class MetricSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    publication_id: int = Field(index=True, foreign_key="publication.id")
    channel_id: int = Field(index=True)
    platform: str
    captured_at: datetime = Field(default_factory=now, index=True)
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    subscribers_gained: int = 0
    watch_time_minutes: float = 0
    avg_view_duration: float = 0
    avg_view_percentage: float = 0
    raw: dict = JsonField({})


class Insight(SQLModel, table=True):
    """Aprendizados gerados a partir das métricas — alimentam pautas e notas."""
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True)
    kind: str = "pattern"  # pattern | calibration | recommendation
    text: str = TextField()
    data: dict = JsonField({})
    created_at: datetime = Field(default_factory=now)


class Comment(SQLModel, table=True):
    """Comentário do público num vídeo do canal + resposta sugerida pela IA (você aprova)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True)
    yt_id: str = Field(index=True)  # id do comentário principal (thread)
    video_id: str = ""  # id do vídeo no YouTube
    video_title: str = ""
    author: str = ""
    author_avatar: str = ""
    text: str = TextField()
    likes: int = 0
    published_at: Optional[datetime] = None
    kind: str = ""  # pergunta | elogio | correcao | sugestao | critica | spam | outro
    suggestion: str = TextField()
    reply: str = TextField()
    status: str = Field(default="new", index=True)  # new | replied | ignored
    replied_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=now)
