"""The web app: JSON API under /api, the built frontend (SvelteKit, static) for everything else."""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .. import comprehension, languages
from ..config import Settings
from ..content.cache import StatsWorker
from ..content.jellyfin import Episode, Jellyfin, WatchState
from ..content.library import Finder, Ingest
from ..content.subtitles import korean_subtitles
from ..db import Database, migrate
from ..knowledge import importer, service
from ..knowledge.events import WordState
from ..models import WordKnowledge
from ..users import default_user_id
from ..util import cached_for
from . import schemas
from .deps import Db
from .library import router as library_router

# a word counts as the best-known of its candidate lemmas
RANK = {WordState.IGNORED: 5, WordState.KNOWN: 4, WordState.LEARNING: 3, WordState.SEEN: 2, WordState.UNKNOWN: 1}


def create_app(
    settings: Settings | None = None,
    *,
    episodes: Callable[[], list[Episode]] | None = None,
    find: Finder | None = None,
    watch: Callable[[], dict[str, WatchState]] | None = None,
) -> FastAPI:
    """episodes / find / watch replace Jellyfin and the subtitle finder (tests)."""
    settings = settings or Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    migrate(settings.db_url)
    db = Database(settings.db_url)
    with db.session() as s:
        default_user_id(s)

    stats_worker = StatsWorker(db)
    if settings.jellyfin_api_key:
        jf = Jellyfin(settings.jellyfin_url, settings.jellyfin_api_key)
        episodes = episodes or jf.episodes
        watch = watch or cached_for(60, lambda: jf.watch_states(settings.jellyfin_user), fallback=dict)
    ingest = None
    if episodes is not None:
        lang = settings.library_language
        ingest = Ingest(
            db,
            episodes,
            languages.get(lang),
            lang,
            settings.library_interval_s,
            find or korean_subtitles,
            on_change=stats_worker.poke,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        if settings.library_autostart:
            stats_worker.start()
            if ingest is not None:
                ingest.start()
        yield

    app = FastAPI(title='language-maxxer', version=version('language-maxxer'), lifespan=lifespan)
    app.state.db = db
    app.state.ingest = ingest
    app.state.stats = stats_worker
    app.state.settings = settings
    app.state.watch = watch or dict  # no Jellyfin: nothing watched
    app.include_router(library_router)

    def language(code: str) -> str:
        if code not in languages.available():
            raise HTTPException(404, f'unknown language {code!r}')
        return code

    @app.get('/api/health', response_model=schemas.Health)
    def health() -> schemas.Health:
        return schemas.Health(ok=True, version=app.version)

    @app.get('/api/languages', response_model=list[schemas.Language])
    def list_languages() -> list[schemas.Language]:
        return [
            schemas.Language(code=c, name=n, dictionary=languages.get(c).dictionary_info())
            for c, n in languages.available().items()
        ]

    @app.get('/api/dictionary/{code}', response_model=schemas.LookupResponse)
    def lookup(code: str, lemma: Annotated[list[str], Query(min_length=1, max_length=10)]) -> schemas.LookupResponse:
        """Meanings of the first candidate lemma the dictionary knows (a token's lemmas, most specific first)."""
        pack = languages.get(language(code))
        for cand in lemma:
            senses = pack.lookup(cand)
            if senses:
                return schemas.LookupResponse(
                    lemma=cand,
                    senses=[schemas.SenseOut.model_validate(x, from_attributes=True) for x in senses],
                    idioms=[schemas.IdiomOut.model_validate(i, from_attributes=True) for i in pack.idioms(cand)],
                )
        return schemas.LookupResponse(lemma=lemma[0], senses=[], idioms=[])

    @app.get('/api/progress/{code}', response_model=schemas.Progress)
    def progress(code: str, s: Db) -> schemas.Progress:
        lang = language(code)
        counts = service.counts(s, default_user_id(s), lang)
        return schemas.Progress(language=lang, words_known=counts[WordState.KNOWN.value], by_state=counts)

    @app.post('/api/analyze', response_model=schemas.AnalyzeResponse)
    def analyze(body: schemas.AnalyzeRequest, s: Db) -> schemas.AnalyzeResponse:
        lang = language(body.language)
        tokens = languages.get(lang).analyze(body.text)
        uid = default_user_id(s)
        lemmas = {x for t in tokens for x in t.lemmas}
        known = (
            {
                r.lemma: WordState(r.state)
                for r in s.scalars(
                    select(WordKnowledge).where(
                        WordKnowledge.user_id == uid, WordKnowledge.language == lang, WordKnowledge.lemma.in_(lemmas)
                    )
                )
            }
            if lemmas
            else {}
        )
        out: list[schemas.AnalyzedToken] = []
        for t in tokens:
            best = max(t.lemmas, key=lambda x: RANK[known.get(x, WordState.UNKNOWN)])
            out.append(
                schemas.AnalyzedToken(
                    surface=t.surface,
                    start=t.start,
                    end=t.end,
                    lemmas=list(t.lemmas),
                    pos=t.pos,
                    key=t.key,
                    weak=t.weak,
                    state=known.get(best, WordState.UNKNOWN),
                    lemma=best,
                )
            )
        sents = comprehension.analyse(body.text, [(t, o.state) for t, o in zip(tokens, out, strict=True)])
        return schemas.AnalyzeResponse(
            language=lang,
            tokens=out,
            sentences=[schemas.SentenceOut(start=x.start, end=x.end, unknown=len(x.unknown)) for x in sents],
        )

    @app.post('/api/knowledge/events', response_model=schemas.WordStatus)
    def add_event(body: schemas.EventRequest, s: Db) -> schemas.WordStatus:
        lang = language(body.language)
        snap = service.record(s, default_user_id(s), lang, body.lemma, body.kind, source='app')
        stats_worker.poke()
        return schemas.WordStatus(lemma=body.lemma.strip(), state=snap.state, confidence=snap.confidence)

    @app.post('/api/knowledge/import', response_model=schemas.ImportResult)
    def import_words(body: schemas.ImportRequest, s: Db) -> schemas.ImportResult:
        lang = language(body.language)
        items, skipped = importer.parse(body.csv)
        n = service.record_many(s, default_user_id(s), lang, items, source=body.source)
        stats_worker.poke()
        return schemas.ImportResult(imported=n, skipped=skipped)

    if settings.static_dir and (settings.static_dir / 'index.html').exists():
        mount_frontend(app, settings.static_dir)
    return app


def mount_frontend(app: FastAPI, static: Path) -> None:
    """Serve the SvelteKit build; unknown paths get index.html (client-side routing)."""
    app.mount('/_app', StaticFiles(directory=static / '_app'), name='assets')

    @app.get('/{path:path}', include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith('api/'):
            raise HTTPException(404)
        f = (static / path).resolve()
        if path and f.is_file() and static.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(static / 'index.html')
