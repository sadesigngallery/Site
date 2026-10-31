# SA Design — public site

The site that visitors see. It is built from the SA Design app (the claude.ai artifact) with `tools/build.py`.

- `public/` — the finished site. Cloudflare Pages serves this folder.
- `state/` — studio settings copied from the app (Subjects layout and glass, 3D room, lights, edition colours, edition sales). They are baked into the page at build time, because the public site cannot reach the app's shared store.
- `tools/build.py` — builds `public/` from the app page, its photos and its films.

## Cloudflare Pages settings
- Framework preset: None
- Build command: (leave empty)
- Build output directory: `public`

Every push to `main` is deployed automatically.
