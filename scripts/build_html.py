#!/usr/bin/env python3
"""Render the CV's supported LaTeX vocabulary as accessible HTML."""

import argparse
import html
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit


class ConversionError(ValueError):
    """Indicate unsupported or malformed LaTeX input."""


class Parser:
    def __init__(self, source):
        self.source = source
        self.position = 0

    def skip_space(self):
        while self.position < len(self.source) and self.source[self.position].isspace():
            self.position += 1

    def group(self, opening="{", closing="}"):
        self.skip_space()
        if self.position >= len(self.source) or self.source[self.position] != opening:
            raise ConversionError(f"Expected {opening!r} at offset {self.position}")
        self.position += 1
        start = self.position
        depth = 1
        while self.position < len(self.source):
            character = self.source[self.position]
            if character == "\\":
                self.position += 2
                continue
            if character == opening:
                depth += 1
            elif character == closing:
                depth -= 1
                if depth == 0:
                    value = self.source[start:self.position]
                    self.position += 1
                    return value
            self.position += 1
        raise ConversionError(f"Unclosed {opening!r} group")

    def render(self, list_items=False):
        output = []
        item_open = False
        while self.position < len(self.source):
            character = self.source[self.position]
            if character == "{":
                output.append(render(self.group()))
                continue
            if character == "}":
                raise ConversionError("Unexpected closing brace")
            if character != "\\":
                start = self.position
                while self.position < len(self.source) and self.source[self.position] not in "\\{}":
                    self.position += 1
                output.append(html.escape(self.source[start:self.position]).replace("---", "—").replace("--", "–"))
                continue
            self.position += 1
            match = re.match(r"[A-Za-z]+\*?|.", self.source[self.position:], re.DOTALL)
            if not match:
                raise ConversionError("Trailing backslash")
            command = match.group()
            self.position += len(command)
            if command in ("&", "%", "#", "_", "$", "{", "}"):
                output.append(html.escape(command))
            elif command in (";", ",", " "):
                output.append(" ")
            elif command == "\\":
                output.append("<br>\n")
            elif command in ("small", "hfill"):
                output.append(" ")
            elif command in ("textbf", "textit", "texttt"):
                tag = {"textbf": "strong", "textit": "em", "texttt": "code"}[command]
                output.append(f"<{tag}>{render(self.group())}</{tag}>")
            elif command == "href":
                address = self.group()
                if not re.match(r"^(https?://|mailto:|tel:)", address):
                    raise ConversionError(f"Unsupported link scheme: {address}")
                output.append(f'<a href="{html.escape(address, quote=True)}">{render(self.group())}</a>')
            elif command == "cvname":
                output.append(f"<h1>{render(self.group())}</h1>")
            elif command == "cvcontact":
                output.append(f'<div class="contact">{render(self.group())}</div>')
            elif command == "cventry":
                title, organization, location, dates, items = [self.group() for _ in range(5)]
                output.append('<article class="entry">'
                              f'<div class="entry-header"><h3>{render(title)}</h3><span class="dates">{render(dates)}</span></div>'
                              f'<div class="entry-meta"><span>{render(organization)}</span><span>{render(location)}</span></div>'
                              f'<ul>{render(items, list_items=True)}</ul></article>')
            elif command == "cvskill":
                output.append(f'<p><strong>{render(self.group())}</strong>: {render(self.group())}</p>')
            elif command == "item":
                if not list_items:
                    raise ConversionError("Item outside itemize")
                if item_open:
                    output.append("</li>")
                output.append("<li>")
                item_open = True
            elif command == "begin":
                environment = self.group()
                if environment != "itemize":
                    raise ConversionError(f"Unsupported environment: {environment}")
                self.skip_space()
                if self.position < len(self.source) and self.source[self.position] == "[":
                    self.group("[", "]")
                ending = "\\end{itemize}"
                end = self.source.find(ending, self.position)
                if end < 0:
                    raise ConversionError("Unclosed itemize environment")
                output.append(f'<ul>{render(self.source[self.position:end], list_items=True)}</ul>')
                self.position = end + len(ending)
            else:
                raise ConversionError(f"Unsupported LaTeX command: \\{command}")
        if item_open:
            output.append("</li>")
        return "".join(output).strip()


def render(source, list_items=False):
    return Parser(source).render(list_items=list_items)


class PlainText(HTMLParser):
    """Extract text without exposing markup in social metadata."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attributes):
        if tag == "br":
            self.parts.append(" ")


def plain_text(source):
    parser = PlainText()
    parser.feed(source)
    return " ".join("".join(parser.parts).split())


def normalize_site_url(site_url):
    try:
        address = urlsplit(site_url)
        # Accessing the port rejects malformed authority components.
        address.port
    except ValueError as error:
        raise ConversionError("Invalid site URL") from error
    if (address.scheme not in ("http", "https") or not address.hostname
            or address.username is not None or address.password is not None
            or address.query or address.fragment or "?" in site_url or "#" in site_url
            or any(character.isspace() or ord(character) < 32 for character in site_url)
            or "\\" in site_url):
        raise ConversionError("Site URL must be an absolute HTTP(S) URL without credentials, query, or fragment")
    return urlunsplit((address.scheme, address.netloc, address.path.rstrip("/") + "/", "", ""))


def social_metadata(name, description, site_url):
    title = f"{name} — CV"
    image_url = site_url + "og-image.png"
    image_alt = f"{name} curriculum vitae"
    attributes = [
        ("name", "description", description),
        ("property", "og:type", "website"),
        ("property", "og:title", title),
        ("property", "og:description", description),
        ("property", "og:url", site_url),
        ("property", "og:site_name", title),
        ("property", "og:locale", "en_US"),
        ("property", "og:image", image_url),
        ("property", "og:image:type", "image/png"),
        ("property", "og:image:width", "1200"),
        ("property", "og:image:height", "630"),
        ("property", "og:image:alt", image_alt),
        ("name", "twitter:card", "summary_large_image"),
        ("name", "twitter:title", title),
        ("name", "twitter:description", description),
        ("name", "twitter:image", image_url),
        ("name", "twitter:image:alt", image_alt),
    ]
    output = [f'<title>{html.escape(title)}</title>',
              f'<link rel="canonical" href="{html.escape(site_url, quote=True)}">']
    output.extend(f'<meta {kind}="{key}" content="{html.escape(value, quote=True)}">'
                  for kind, key, value in attributes)
    return "\n".join(output)


def build_html(source, site_url="https://cv.zeroday0619.dev/"):
    site_url = normalize_site_url(site_url)
    # Comments are removed before parsing so commented commands cannot affect output.
    source = re.sub(r"(?<!\\)%[^\n]*", "", source)
    match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", source, re.DOTALL)
    if not match:
        raise ConversionError("Expected a complete document environment")
    body = match.group(1)
    sections = list(re.finditer(r"\\section\*?\{", body))
    header_end = sections[0].start() if sections else len(body)
    header = render(body[:header_end])
    name_match = re.search(r"<h1>(.*?)</h1>", header, re.DOTALL)
    if not name_match:
        raise ConversionError("Expected a CV name")
    name = plain_text(name_match.group(1))
    description = f"Curriculum vitae of {name}."
    output = [f'<div class="cv"><header>{header}</header><main>']
    for index, section in enumerate(sections):
        parser = Parser(body)
        parser.position = section.end() - 1
        heading = render(parser.group())
        end = sections[index + 1].start() if index + 1 < len(sections) else len(body)
        content = render(body[parser.position:end])
        if plain_text(heading).lower() == "summary":
            description = plain_text(content)
        if not re.search(r"<(ul|article|p)\b", content):
            content = f"<p>{content}</p>"
        identifier = re.sub(r"[^a-z0-9]+", "-", html.unescape(re.sub(r"<[^>]+>", "", heading)).lower()).strip("-")
        output.append(f'<section aria-labelledby="{identifier}"><h2 id="{identifier}">{heading}</h2>{content}</section>')
    output.append("</main></div>")
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            + social_metadata(name, description, site_url) + '<link rel="stylesheet" href="styles.css">'
            '</head><body>' + "\n".join(output) + '</body></html>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("cv.tex"))
    parser.add_argument("--output", type=Path, default=Path("dist/index.html"))
    parser.add_argument("--site-url", default="https://cv.zeroday0619.dev/")
    arguments = parser.parse_args()
    try:
        result = build_html(arguments.source.read_text(encoding="utf-8"), arguments.site_url)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(result, encoding="utf-8")
    except (OSError, ConversionError) as error:
        parser.exit(1, f"CV conversion failed: {error}\n")


if __name__ == "__main__":
    main()
