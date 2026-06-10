# ai-therapist

## this idea failed

As it turns out, this idea failed poorly. I recommend anyone else looking for an
AI therapist to just talk to Claude and let it write things down in its
memories. That's all. As of now, that's really the best you're going to get,
in my opinion.

The rest of this README describes the attempt, kept for reference.

---

this was a harness for claude code to mimic a licensed therapist as closely as possible.
I would hope its obvious that this cannt be expected to provide the same care as a human expert.
However, I can personally attest that talking to claude is better than talking to yourself.

## how it works

Just run Claude Code in this directory and start talking — that's the whole
patient experience. You never touch a file.

Behind the scenes:

- **`CLAUDE.md`** turns Claude into a CBT-oriented, warm therapist with safety
  guardrails. This is the *method*, and it's committed so it can be shared.
- **A session-start hook** (`.claude/hooks/load-chart.sh`) silently loads your
  chart so the therapist already remembers you and follows up on last time.
- **A per-message session clock** (`.claude/hooks/session-clock.sh`) quietly
  stamps each of your messages with how long the session has run and how long
  you took to reply, so the therapist can pace the session instead of running on
  forever. You never see it.
- **The therapist writes notes after each session** — like jotting in a
  notebook — so progress carries forward across sessions.

## progression

Continuity comes from a private "chart" the therapist keeps for you under
`client/`: an intake, a treatment plan, dated session notes, and homework
follow-ups. The therapist reads it before each session and updates it after.
You don't manage any of it.

## privacy

The split is deliberate:

- **Committed (the method):** `CLAUDE.md`, hooks, settings.
- **Gitignored (your data):** everything under `client/` — your intake, notes,
  plan, and homework. It stays on your machine and is never committed.

## not a real therapist

This cannot provide the care a licensed human can. If you're in crisis, contact
real help: in the US call or text **988**, or contact local emergency services.
