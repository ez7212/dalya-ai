# T5 Server Cleanup Clarification

Date checked: 2026-06-25, Asia/Dubai.

## Disposition

- T5-owned browser QA server: `127.0.0.1:3197`
  - Source artifact: `.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/transcript.json`
  - QA transcript says `preExistingServerUsed: false`, `startedServer: true`, `baseUrl: http://127.0.0.1:3197`, and `serverCwd: /private/tmp/dalya-final-surface-listings-qa`.
  - Cleanup receipt says `server exited after SIGTERM`, `supabaseStub: closed`, and the safe temp workdir was removed.
  - Current check: `lsof -nP -iTCP:3197 -sTCP:LISTEN` returned no listener.

- User-facing/pre-existing dev server: `127.0.0.1:3000`
  - Current listener: PID `25996`, command `next-server (v16.2.1)`, cwd `/Users/eric/dalya-ai/frontend`.
  - Parent process: PID `25995`, command `node /Users/eric/dalya-ai/frontend/node_modules/.bin/next dev --hostname 127.0.0.1 --port 3000`.
  - Start time: `Wed Jun 24 19:29:06/07 2026`, roughly 4h34m before this check and hours before the T5 browser QA transcript/screenshot files written at `Jun 24 23:49:01/02 2026`.
  - This process was not killed because it matches the active user-facing app session on `localhost:3000`, not the T5 QA-owned staged server.

## Commands

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -p 25996 | awk '$4=="cwd" {print $1, $2, $4, $9}'
ps -p 25996 -o pid=,ppid=,lstart=,etime=,command=
ps -p 25995 -o pid=,ppid=,lstart=,etime=,command=
lsof -nP -iTCP:3197 -sTCP:LISTEN
stat -f '%Sm %N' .omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/transcript.json .omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/listings-1280.png
```

`ps` was run with metadata-only escalation after sandbox denial. No process environment, headers, cookies, or secrets were read or recorded.
