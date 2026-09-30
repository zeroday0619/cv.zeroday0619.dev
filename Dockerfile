FROM python:3.13-alpine AS builder
WORKDIR /build
COPY cv.tex ./cv.tex
COPY scripts/build_html.py ./scripts/build_html.py
COPY web/styles.css ./web/styles.css
RUN python scripts/build_html.py --source cv.tex --output dist/index.html \
    && cp web/styles.css dist/styles.css

FROM python:3.13-alpine
WORKDIR /site
RUN addgroup -S cv && adduser -S -G cv cv
COPY --from=builder /build/dist/ /site/
USER cv
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/', timeout=2).close()"
CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", "/site"]
