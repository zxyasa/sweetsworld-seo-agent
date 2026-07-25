# Plan — SweetsWorld AIO Scoreboard

1. Create task records and lock the non-website scope.
2. Replace overwrite semantics with an append-only observation model while preserving the existing API.
3. Add a versioned AU query basket and read-only OpenAI/Gemini probe adapters.
4. Add reporting, Telegram formatting, and a local weekly scheduler wrapper.
5. Run unit tests and offline dry-run verification; do not execute live probes without explicit approval.

