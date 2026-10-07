import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from .models import MergeJob
from .spotify_client import SpotifyClient
from .merge_tree import execution_order, normalize_playlist_id, propagation_plan
from .api_calls import describe_api_error
from ..config import settings
from loguru import logger

# Name of the extra result row for the saved-tracks sync that follows a run
SAVED_LABEL = "Me gusta"

@dataclass
class JobResult:
    name: str
    added: int = 0
    status: str = "ok"  # ok | error | skipped
    detail: str = ""

@dataclass
class JobPreview:
    """What one merge would add to its target playlist."""
    name: str
    target_id: str
    to_add: List[Dict[str, Any]]  # slim tracks, each with "from": the source playlist it comes from
    local_skipped: int = 0

@dataclass
class RunPreview:
    """What a run would do, without having written anything."""
    jobs: List[JobPreview]
    to_save: List[Dict[str, Any]] = field(default_factory=list)  # tracks that would be saved to Liked Songs
    sync_saved: bool = True
    cyclic: List[str] = field(default_factory=list)
    scope: str = ""  # merge that was previewed with its parents; empty for the whole tree
    read: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # playlists read from Spotify (true state)

class JobManager:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = settings.merges_path
        self.config_path = Path(config_path)
        # Ensure data directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.jobs: List[MergeJob] = self._load_jobs()

    def _load_jobs(self) -> List[MergeJob]:
        if not self.config_path.exists():
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [MergeJob(**job) for job in data]
        except Exception as e:
            logger.error(f"Error loading jobs: {e}")
            return []

    def save_jobs(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump([job.model_dump() for job in self.jobs], f, indent=4)
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")

    def add_job(self, job: MergeJob):
        # Remove existing job with same name
        self.jobs = [j for j in self.jobs if j.name != job.name]
        self.jobs.append(job)
        self.save_jobs()

    def delete_job(self, name: str):
        self.jobs = [j for j in self.jobs if j.name != name]
        self.save_jobs()

    def run_plan(self, plan: List[MergeJob], client: SpotifyClient, sync_saved: bool = True,
                 saved_uris: Optional[Set[str]] = None) -> List[JobResult]:
        """
        Runs jobs in the given order. A failure does not stop unrelated jobs, but the
        jobs above a failed one are skipped (they would be built on an outdated playlist).
        With sync_saved, every track in the playlists involved that is not in the user's
        saved tracks (Liked Songs) is saved afterwards.
        """
        track_cache: Dict[str, List[Dict[str, Any]]] = {}
        failed_targets: Set[str] = set()
        results: List[JobResult] = []

        for job in plan:
            target = normalize_playlist_id(job.target_id)
            blocked = [s for s in job.source_ids if normalize_playlist_id(s) in failed_targets]
            if blocked:
                results.append(JobResult(job.name, status="skipped", detail="Depende de un merge que ha fallado."))
                failed_targets.add(target)
                continue
            try:
                added = client.merge_playlists(job.target_id, job.source_ids, track_cache)
                results.append(JobResult(job.name, added))
            except Exception as e:
                logger.error(f"Merge '{job.name}' failed: {type(e).__name__}: {e}")
                results.append(JobResult(job.name, status="error", detail=describe_api_error(e)))
                failed_targets.add(target)

        if sync_saved and any(r.status == "ok" for r in results):
            results.append(self._sync_saved(client, track_cache, saved_uris))
        return results

    def _sync_saved(self, client: SpotifyClient, track_cache: Dict[str, List[Dict[str, Any]]],
                    saved_uris: Optional[Set[str]] = None) -> JobResult:
        uris = {t['uri'] for playlist in track_cache.values() for t in playlist}
        try:
            added = client.sync_to_saved(uris, saved_uris)
            return JobResult(SAVED_LABEL, added, detail="Canciones de estas playlists que faltaban en tus guardadas.")
        except Exception as e:
            logger.error(f"Saved-tracks sync failed: {type(e).__name__}: {e}")
            return JobResult(SAVED_LABEL, status="error", detail=describe_api_error(e))

    def run_with_propagation(self, name: str, client: SpotifyClient, sync_saved: bool = True,
                             saved_uris: Optional[Set[str]] = None) -> List[JobResult]:
        """Runs one merge and then every merge above it in the tree, in order."""
        plan = propagation_plan(self.jobs, name)
        if not plan:
            logger.error(f"Job {name} not found")
            return [JobResult(name, status="error", detail="No existe ese merge.")]
        logger.info(f"Running jobs: {[j.name for j in plan]}")
        return self.run_plan(plan, client, sync_saved, saved_uris)

    def run_tree_intelligent(self, client: SpotifyClient, sync_saved: bool = True,
                             saved_uris: Optional[Set[str]] = None) -> List[JobResult]:
        """Runs every merge, each one after the merges that fill its sources."""
        ordered, cyclic = execution_order(self.jobs)
        results = self.run_plan(ordered, client, sync_saved, saved_uris)
        results += [
            JobResult(j.name, status="error", detail="Forma parte de un ciclo entre playlists.")
            for j in cyclic
        ]
        return results

    def preview_plan(
        self,
        plan: List[MergeJob],
        client: SpotifyClient,
        sync_saved: bool = True,
        seed: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        saved_uris: Optional[Set[str]] = None,
    ) -> RunPreview:
        """
        What run_plan would do, computed without writing anything: the tracks each merge would add
        (merges above see what the ones below would add) and the ones that would be saved to Liked Songs.
        `seed` (playlist id -> slim tracks) is data already read recently, so those playlists are not read
        again; `saved_uris` does the same for the saved tracks. RunPreview.read returns what was read.
        """
        track_cache: Dict[str, List[Dict[str, Any]]] = dict(seed or {})
        read: Dict[str, List[Dict[str, Any]]] = {}
        previews: List[JobPreview] = []
        for job in plan:
            known = set(track_cache)
            new_tracks = client.plan_merge(job.target_id, job.source_ids, track_cache)
            for playlist_id in set(track_cache) - known:
                read[playlist_id] = track_cache[playlist_id]  # as Spotify has it, before simulating the merge
            addable = [t for t in new_tracks if not t['uri'].startswith("spotify:local:")]
            target = client.get_playlist_id(job.target_id)
            track_cache[target] = track_cache[target] + addable
            previews.append(JobPreview(job.name, target, addable, len(new_tracks) - len(addable)))

        to_save: List[Dict[str, Any]] = []
        if sync_saved and plan:
            by_uri = {t['uri']: t for tracks in track_cache.values() for t in tracks}
            to_save = [by_uri[uri] for uri in client.filter_unsaved(by_uri, saved_uris)]
        return RunPreview(previews, to_save, sync_saved, read=read)

    def preview_with_propagation(self, name: str, client: SpotifyClient, sync_saved: bool = True, **reuse) -> RunPreview:
        """Preview of run_with_propagation: one merge and every merge above it."""
        preview = self.preview_plan(propagation_plan(self.jobs, name), client, sync_saved, **reuse)
        preview.scope = name
        return preview

    def preview_tree(self, client: SpotifyClient, sync_saved: bool = True, **reuse) -> RunPreview:
        """Preview of run_tree_intelligent: every merge, each after the ones that fill its sources."""
        ordered, cyclic = execution_order(self.jobs)
        preview = self.preview_plan(ordered, client, sync_saved, **reuse)
        preview.cyclic = [j.name for j in cyclic]
        return preview
