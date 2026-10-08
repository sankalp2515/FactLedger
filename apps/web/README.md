# Research desk frontend

React, TypeScript and Vite client for the evidence workspace. The server owns all cases, revisions, run results, memberships and reviews; the frontend keeps only interface selections in React state and URL parameters.

```
pnpm install --frozen-lockfile
pnpm dev
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Development uses the Vite `/v1` proxy to `http://127.0.0.1:8000`. Production files are emitted to `dist/` and served by the API through the authenticated same-origin session. Every mutation uses the session CSRF token. Identity switches clear query caches; source passages are rendered as plain text with validated character anchors.

Routes: `/cases`, `/cases/new`, `/cases/:id`, `/cases/:id/runs/:runId`, `/cases/:id/revisions/:revision`, `/reviews`, `/reviews/:requestId`, `/workspace/settings`.

Fixture investigation mode is explicitly synthetic throughout the research workflow. Live mode requires server provider configuration; frontend screens never replace unavailable API data with fabricated records.
