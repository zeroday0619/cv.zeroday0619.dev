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
cp web/styles.css dist/styles.css
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
