#!/usr/bin/env python3
"""Save a Claude Code session transcript into the patient's private chart.

Two ways to run it:

  * As a Stop hook: Claude Code sends hook JSON on stdin, including
    ``transcript_path``. We save that one session.
  * From the command line for backfill: pass one or more ``.jsonl`` paths,
    or ``--all`` to process every log in this project's transcript folder.

For each session it writes two files under ``client/transcripts/``:

    raw/<date>-<id>.jsonl        exact copy of the original log (complete)
    readable/<date>-<id>.md      cleaned conversation (patient + therapist)

Errors never propagate. A problem saving a transcript must never disrupt a
session, so everything is wrapped and failures are logged to
``client/transcripts/.errors.log`` instead of raised.
"""
import sys, os, json, glob, shutil, datetime, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT  = os.path.join(REPO, "client", "transcripts")
RAW  = os.path.join(OUT, "raw")
READ = os.path.join(OUT, "readable")

# Text injected by the harness, not spoken by the patient. Lines that begin
# with any of these are dropped from the readable transcript.
SKIP_PREFIXES = (
    "[session-clock]",
    "<local-command", "<command-", "<bash-",
    "Caveat:",
    "Today's date is",
    "THERAPIST'S PRIVATE CHART",
    "=====",
    "<system-reminder>",
)


def local_date(ts):
    """ISO timestamp (UTC) -> local YYYY-MM-DD; today's date as a fallback."""
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d")
    except Exception:
        return datetime.date.today().strftime("%Y-%m-%d")


def load(path):
    entries = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                entries.append(json.loads(ln))
            except Exception:
                continue
    return entries


def _injected(text):
    return any(text.lstrip().startswith(p) for p in SKIP_PREFIXES)


def clean_user_text(content):
    """Return the patient's actual words, or None if this entry is not speech."""
    if isinstance(content, str):
        txt = content
        if _injected(txt):
            return None
    elif isinstance(content, list):
        parts = []
        for b in content:
            # tool_result blocks are tool output coming back to the
            # therapist, not the patient talking -- skip them.
            if isinstance(b, dict) and b.get("type") == "text":
                t = b.get("text", "")
                if t and not _injected(t):
                    parts.append(t)
        txt = "\n".join(parts)
    else:
        return None
    txt = txt.strip()
    return txt or None


def tool_note(b):
    name = b.get("name", "tool")
    inp = b.get("input", {}) or {}
    if name in ("Write", "Edit", "NotebookEdit"):
        return "wrote to %s" % inp.get("file_path", "a file")
    if name == "Read":
        return "read %s" % inp.get("file_path", "a file")
    if name == "Bash":
        return inp.get("description") or "ran a command"
    return "used %s" % name


def assistant_render(content):
    """Return [("text"|"tool", str)] for an assistant turn; thinking dropped."""
    out = []
    if isinstance(content, str):
        if content.strip():
            out.append(("text", content.strip()))
    elif isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text":
                tx = b.get("text", "").strip()
                if tx:
                    out.append(("text", tx))
            elif t == "tool_use":
                out.append(("tool", tool_note(b)))
            # "thinking" blocks are intentionally left out of the readable copy
    return out


def to_markdown(entries, sid, date):
    L = []
    L.append("# Session transcript -- %s" % date)
    L.append("")
    L.append(
        "_Session id `%s`. This is the readable version: the conversation "
        "between you and me, with my note-taking marked briefly. My private "
        "thinking and the tool details are not included here. The complete, "
        "unedited record is the matching raw log in the `raw/` folder._" % sid
    )
    L.append("")
    L.append("---")
    L.append("")
    for o in entries:
        if o.get("isMeta"):
            continue
        t = o.get("type")
        if t == "user":
            txt = clean_user_text(o.get("message", {}).get("content"))
            if txt:
                L += ["**Patient:**", "", txt, ""]
        elif t == "assistant":
            rendered = assistant_render(o.get("message", {}).get("content"))
            for kind, val in rendered:
                if kind == "text":
                    L += ["**Therapist:**", "", val, ""]
                else:
                    L += ["_(%s)_" % val, ""]
    return "\n".join(L).rstrip() + "\n"


def save_one(path):
    entries = load(path)
    if not entries:
        return None
    sid = next((o["sessionId"] for o in entries if o.get("sessionId")), None)
    if not sid:
        sid = os.path.splitext(os.path.basename(path))[0]
    first_ts = next((o["timestamp"] for o in entries if o.get("timestamp")), None)
    date = local_date(first_ts)
    stem = "%s-%s" % (date, sid[:8])
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(READ, exist_ok=True)
    shutil.copyfile(path, os.path.join(RAW, stem + ".jsonl"))
    with open(os.path.join(READ, stem + ".md"), "w", encoding="utf-8") as fh:
        fh.write(to_markdown(entries, sid, date))
    return stem


def project_dir():
    return os.path.join(os.path.expanduser("~/.claude/projects"),
                        os.getcwd().replace("/", "-"))


def log_error():
    try:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, ".errors.log"), "a") as fh:
            fh.write("--- %s\n%s\n" % (datetime.datetime.now(), traceback.format_exc()))
    except Exception:
        pass


def main():
    args = sys.argv[1:]
    if args:
        targets = sorted(glob.glob(os.path.join(project_dir(), "*.jsonl"))) \
            if args[0] == "--all" else args
    else:
        try:
            targets = [json.load(sys.stdin)["transcript_path"]]
        except Exception:
            return
    done = []
    for t in targets:
        try:
            s = save_one(t)
            if s:
                done.append(s)
        except Exception:
            log_error()
    if args and done:
        print("saved: " + ", ".join(done))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error()
    sys.exit(0)  # never disrupt a session
