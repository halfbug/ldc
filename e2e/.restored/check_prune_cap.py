"""ONLINE-8062: one sync run may not prune more than MAX_PRUNE_SHARE of a type, or MAX_PRUNE_DOCS in all, unless
`--force-large-prune` is passed; the hourly schedule never passes it.

    uv run --no-project --with typer --with rich --with pymongo --with python-dotenv \\
        python experiments/content_sync/check_prune_cap.py

Pinecone and Mongo are in-memory fakes and the export is a temporary local directory: nothing is written anywhere.
"""

import gzip
import json
import re
import sys
import tempfile
import types
from pathlib import Path

RAG = Path(__file__).resolve().parents[2]

pinecone = types.ModuleType("pinecone")
pinecone.Vector = lambda **kw: kw
pinecone.SparseValues = lambda **kw: kw
sys.modules["pinecone"] = pinecone
# The real module pings MongoDB on import; every command here gets its own fake instead.
mongo_engine = types.ModuleType("commands.mongo_engine")
mongo_engine.mongo = None
sys.modules["commands.mongo_engine"] = mongo_engine

sys.path.insert(0, str(RAG))
import typer  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from commands import ai_sync_command as sync_module  # noqa: E402
from commands.ai_sync_command import (  # noqa: E402
    MAX_PRUNE_DOCS, STATE_COLLECTION, AiSyncCommand, SyncStats, vector_id,
)

FAILED = 0


def check(label, condition, detail=None):
    global FAILED
    print(("PASS " if condition else "FAIL ") + label + ("" if condition or detail is None else f" — {detail}"))
    if not condition:
        FAILED += 1


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = {row["_id"]: row for row in rows or []}

    def find(self, *args, **kwargs):
        return list(self.rows.values())

    def find_one(self, query, *args, **kwargs):
        return self.rows.get(query.get("_id"))

    def update_one(self, query, update, upsert=False):
        self.rows.setdefault(query["_id"], {"_id": query["_id"]}).update(update.get("$set", {}))

    def delete_many(self, query):
        for doc_id in query["_id"]["$in"]:
            self.rows.pop(doc_id, None)


class FakeMongo:
    def __init__(self, state_rows):
        self.collections = {STATE_COLLECTION: FakeCollection(state_rows)}

    def get_collection(self, name):
        return self.collections.setdefault(name, FakeCollection())


class FakeIndex:
    def __init__(self, ids):
        self.vectors = set(ids)

    def delete(self, ids, namespace):
        self.vectors.difference_update(ids)


def gz(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def make_command(indexed):
    command = AiSyncCommand.__new__(AiSyncCommand)
    command.mongo = FakeMongo([{"_id": d, "sha": "s", "chunks": 1} for d in indexed])
    index = FakeIndex(vector_id(d, 0) for d in indexed)
    command._index = None
    command._embeddings = None
    command._sparse = None
    command._lease = None
    command._placements = None

    def connect(_name):
        command._index = index

    command._connect = connect
    command._preflight = lambda *args, **kwargs: None
    command._index_documents = lambda *args, **kwargs: None
    return command, index


def write_export(root, indexed, exported):
    types_ = sorted({d.split(":", 1)[0] for d in indexed})
    gz(root / "runs/r1/manifest-0001.jsonl.gz", [{"doc_id": d, "content_sha": "s"} for d in exported])
    (root / "runs/r1/run.json").write_text(json.dumps({
        "run_id": "r1", "mode": "full", "types": types_, "complete": True,
        "manifest_files": ["ai-export/runs/r1/manifest-0001.jsonl.gz"],
    }))
    (root / "latest.json").write_text(json.dumps({"run_id": "r1"}))


def run(indexed, exported, force=False, dry_run=False):
    """Index `indexed` doc ids, export `exported` of them unchanged, run one pinned sync; (stats, state, index)."""
    command, index = make_command(indexed)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "ai-export"
        write_export(root, indexed, exported)
        stats = SyncStats()
        command._sync(stats, sync_module.ExportSource(str(root)), "r1", None, True, "content-v2", dry_run, None,
                      True, False, "fake", True, force)
    return stats, command.mongo.collections[STATE_COLLECTION].rows, index.vectors


articles = [f"article:{n}" for n in range(200)]
definitions = [f"definition:{n}" for n in range(400)]

# An export missing half of one type.
stats, state, vectors = run(articles + definitions, articles[:100] + definitions)
check("an export missing 50% of a type refuses the prune", bool(stats.prune_refused), stats)
check("the refusal names the type and the share",
      any(r.startswith("article: 100 of 200") and "(50%)" in r for r in stats.prune_refused), stats.prune_refused)
check("and deletes nothing: every state row and vector is still there",
      len(state) == 600 and len(vectors) == 600 and stats.deleted == 0 and stats.chunks_deleted == 0)

# A normal run: a few unpublished documents.
stats, state, vectors = run(articles + definitions, articles[3:] + definitions)
check("a normal run (3 of 200 articles gone) deletes as before",
      not stats.prune_refused and stats.deleted == 3 and len(state) == 597 and len(vectors) == 597, stats)

# Within the floor, a small type may lose a large share.
small = [f"glossary:{n}" for n in range(30)]
stats, state, _ = run(small + definitions, small[20:] + definitions)
check("20 of a 30-document type (67%) is within the 25-document floor and deletes",
      not stats.prune_refused and stats.deleted == 20, stats)

# The absolute cap, with no type over its share.
big = [f"article:{n}" for n in range(30000)]
gone = MAX_PRUNE_DOCS + 1
stats, state, vectors = run(big, big[gone:])
check(f"{gone:,} deletions ({gone / 30000:.0%} of the type) are over the absolute cap and refused",
      len(stats.prune_refused) == 1 and "over the cap" in stats.prune_refused[0]
      and len(state) == 30000 and len(vectors) == 30000, stats.prune_refused)

# --force-large-prune lets the same export through.
stats, state, vectors = run(articles + definitions, articles[:100] + definitions, force=True)
check("--force-large-prune deletes the oversized set",
      not stats.prune_refused and stats.deleted == 100 and len(state) == 500 and len(vectors) == 500, stats)

# A dry run reports the refusal and writes nothing.
printed = []
real_print = sync_module.console.print
sync_module.console.print = lambda *a, **k: printed.append(" ".join(map(str, a)))
stats, state, vectors = run(articles + definitions, articles[:100] + definitions, dry_run=True)
dry_printed, printed[:] = list(printed), []
run(articles + definitions, articles[:100] + definitions)
sync_module.console.print = real_print
check("a dry run reports the refusal and writes nothing",
      bool(stats.prune_refused) and len(state) == 600 and len(vectors) == 600, stats)
check("a dry run never prints the \"Prune refused\" the alarm counts, and says the prune would be refused",
      not any("Prune refused" in line for line in dry_printed)
      and any("Prune would be refused: article: 100 of 200" in line for line in dry_printed), dry_printed)
check("a real run still prints \"Prune refused\" for the alarm", any("Prune refused" in line for line in printed), printed)

# Unpinned, as the hourly schedule runs it: a refused prune leaves the run unsynced, so the advised
# `sync-content --force-large-prune` rerun picks up the same export and prunes.
sync_module.SyncLease = type("FreeLease", (), {
    "__init__": lambda self, *a, **k: None, "acquire": lambda self: True,
    "release": lambda self: None, "renew": lambda self: None, "held_by": lambda self: None})
command, index = make_command(articles + definitions)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "ai-export"
    write_export(root, articles + definitions, articles[:100] + definitions)
    refused_stats = command.sync(str(root), "content-v2", None, False, None, True, False, "fake", True, False)
    synced = command.mongo.get_collection(sync_module.SYNC_META_COLLECTION).find_one({"_id": sync_module.LAST_RUN_ID})
    forced_stats = command.sync(str(root), "content-v2", None, False, None, True, False, "fake", True, True)
state = command.mongo.collections[STATE_COLLECTION].rows
check("unpinned: a refused prune does not record the run as synced",
      bool(refused_stats.prune_refused) and not (synced or {}).get("run_id"), (refused_stats, synced))
check("unpinned: the --force-large-prune rerun picks up the same export and prunes it",
      not forced_stats.skipped and forced_stats.deleted == 100 and len(state) == 500 and len(index.vectors) == 500,
      (forced_stats, len(state), len(index.vectors)))

# The command exits 1 on a refused prune and 0 on a normal run, and says why.
app = typer.Typer()
cli_command = AiSyncCommand.__new__(AiSyncCommand)
cli_command.register(app)
sync_module.config.validate_partial = lambda *names: True
sync_module.config.AI_EXPORT_SOURCE = "/nowhere"
forced = []


def fake_sync(*args):
    forced.append(args[-1])
    stats = SyncStats(deleted=0)
    stats.prune_refused = ["article: 100 of 200 indexed documents (50%) is over 10%"] if not args[-1] else []
    return stats


cli_command.sync = fake_sync
refused = CliRunner().invoke(app, ["sync-content", "--yes"])
allowed = CliRunner().invoke(app, ["sync-content", "--yes", "--force-large-prune"])
check("sync-content --yes exits 1 when the prune is refused", refused.exit_code == 1, refused.output)
check("--force-large-prune reaches sync() and the run exits 0",
      forced == [False, True] and allowed.exit_code == 0, (forced, allowed.output))

# The hourly schedule and the task's default command never pass the flag.
main_tf = (RAG / "infra/swo/main.tf").read_text()
commands = re.findall(r'command\s*=\s*\[([^\]]*sync-content[^\]]*)\]', main_tf)
check("infra/swo/main.tf runs sync-content (task default and hourly schedule) without --force-large-prune",
      len(commands) == 2 and all("force-large-prune" not in c for c in commands), commands)

print(f"\n{FAILED} failure(s)")
sys.exit(1 if FAILED else 0)
