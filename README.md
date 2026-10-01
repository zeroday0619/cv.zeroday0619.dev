# CV

`cv.tex` is the source for both the LaTeX document and the HTML website.
The HTML build and server use only the Python standard library. No LaTeX
installation is required for the Docker image.

## Docker deployment

```bash
docker compose up --build -d
```

Open <http://localhost:8080>. The container runs as an unprivileged user,
with a read-only filesystem and an HTTP health check. Python 3.13 serves
the generated static files on container port 8080.

The default host binding is `127.0.0.1`. To expose the server on all host
interfaces or change the host port:

```bash
CV_BIND_ADDRESS=0.0.0.0 CV_PORT=8000 docker compose up --build -d
```

For an Internet-facing deployment, place this static server behind a reverse
proxy that provides HTTPS and request limits. Python's `http.server` is a basic
static server and does not provide those controls.

After editing `cv.tex` or `web/styles.css`, rebuild with
`docker compose up --build -d`. The image contains a build-time snapshot;
source files are not mounted into the running container.

```bash
docker compose ps
docker compose logs cv
docker compose down
```

## Local HTML preview

Python 3.10 or later is required for the builder.

```bash
python3 scripts/build_html.py --source cv.tex --output dist/index.html
cp web/styles.css web/og-image.png dist/
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist
```

The builder supports the commands used by this CV rather than arbitrary LaTeX.
Unsupported content commands fail the build so that content is not silently
omitted. The generated `dist/` directory is not committed.

## Validation

```bash
python3 -m unittest discover -s tests -v
docker compose config
```

## Social link previews

The HTML builder injects Open Graph and Twitter Card metadata directly into
the document head. Titles and descriptions come from the CV name and Summary.
The image is `web/og-image.png` (1200 × 630 pixels), copied into the static site.
No client-side JavaScript or platform API credentials are required.

The default canonical URL is `https://cv.zeroday0619.dev/`. Set the actual
public deployment URL before building if it differs:

```bash
CV_SITE_URL=https://cv.example.com/ docker compose up --build -d
```

For a local build, pass `--site-url https://cv.example.com/` to the HTML builder.
Rebuild the image after changing this setting. Replace `web/og-image.png` when
the name or roles shown in the preview image change; the image is a static asset.

Open Graph provides shared preview metadata for Facebook, Mastodon, Misskey,
Bluesky clients, and Discord. Twitter/X receives explicit `twitter:*` tags with
`summary_large_image`. Actual rendering depends on the client, instance, user
settings, and cached preview. Bluesky clients fetch and embed website-card
metadata when composing posts; tags do not create a post or refresh old embeds.

External previews require the page and image to be publicly accessible.
Localhost validation checks the markup and asset delivery, not platform-side
rendering. After deployment, verify previews in each platform without posting.

References: [Open Graph protocol](https://ogp.me/),
[Twitter Card markup](https://docs.x.com/resources/fundamentals/cards/overview/markup),
[Bluesky website cards](https://docs.bsky.app/docs/advanced-guides/posts#website-card-embeds).

## PDF build
- Recommended: `latexmk`

```bash
latexmk -pdf cv.tex
```

## Clean
```bash
latexmk -c
```

## Editing

Edit the content in `cv.tex` and the website presentation in `web/styles.css`.
Keep experience statements scoped to documented work and validation evidence.
