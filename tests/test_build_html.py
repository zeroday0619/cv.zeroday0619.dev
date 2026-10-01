"""Verify content preservation and rejection of unsupported input."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

from scripts.build_html import ConversionError, build_html, render


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.text = []
        self.metadata = {}
        self.canonical = None
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if tag == "meta":
            self.metadata[values.get("property", values.get("name"))] = values.get("content")
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical = values["href"]
        if tag == "a":
            self.links.append(dict(attributes)["href"])

    def handle_data(self, data):
        self.text.append(data)


class ConversionTests(unittest.TestCase):
    def test_current_cv_content_and_links(self):
        source = (Path(__file__).resolve().parents[1] / "cv.tex").read_text()
        document = Document(build_html(source))
        self.assertEqual(document.links, re.findall(r"\\href\{([^}]+)\}", source))
        text = " ".join(" ".join(document.text).split())
        for phrase in (
            "Euiseo Cha", "Work Experience", "Technical Skills", "Open Source Contributions",
            "Backend development:", "Linux security automation:", "Platform design:",
            "Network performance experiments:", "JSONL interfaces", "eight Linux container images",
            "Kubernetes-based Platform as a Service (PaaS)", "Ixia-c/snappi", "Valkey",
            "discordown (Team Project)", "On leave of absence", "MiniDebConf Korea 2026 Team",
        ):
            self.assertIn(phrase, text)
        self.assertEqual(build_html(source).count("<section "), 8)
        self.assertEqual(build_html(source).count("<article "), 5)
        self.assertEqual(build_html(source).count("<li>"), source.count("\\item "))

    def test_nested_formatting_and_escaping(self):
        self.assertEqual(render(r"\textbf{A \textit{B \& C}} <script>"),
                         "<strong>A <em>B &amp; C</em></strong> &lt;script&gt;")
        self.assertEqual(render(r"\href{https://example.com/?a=1&b=2}{X \#1}"),
                         '<a href="https://example.com/?a=1&amp;b=2">X #1</a>')

    def test_social_metadata_derives_and_escapes_content(self):
        source = r'\begin{document}\cvname{Alice \& "Bob"}\section{Summary}Builds \textbf{safe} tools <script>.\end{document}'
        rendered = build_html(source, "https://example.com/cv")
        document = Document(rendered)
        metadata = document.metadata
        self.assertEqual(document.canonical, "https://example.com/cv/")
        self.assertEqual(metadata["og:url"], document.canonical)
        self.assertEqual(metadata["og:title"], 'Alice & "Bob" — CV')
        self.assertEqual(metadata["og:description"], "Builds safe tools <script>.")
        self.assertEqual(metadata["description"], metadata["og:description"])
        self.assertEqual(metadata["twitter:title"], metadata["og:title"])
        self.assertEqual(metadata["twitter:description"], metadata["og:description"])
        self.assertEqual(metadata["twitter:image"], "https://example.com/cv/og-image.png")
        self.assertEqual(metadata["twitter:image"], metadata["og:image"])
        self.assertEqual(metadata["twitter:image:alt"], metadata["og:image:alt"])
        self.assertEqual(metadata["twitter:card"], "summary_large_image")
        self.assertEqual(metadata["og:type"], "website")
        self.assertEqual(metadata["og:locale"], "en_US")
        self.assertEqual(metadata["og:image:type"], "image/png")
        self.assertEqual((metadata["og:image:width"], metadata["og:image:height"]), ("1200", "630"))
        self.assertIn("&quot;Bob&quot;", rendered)
        self.assertNotIn('<script>', rendered)

    def test_invalid_site_urls_are_rejected(self):
        source = r"\begin{document}\cvname{Alice}\end{document}"
        for site_url in ("/relative", "ftp://example.com/", "https:///missing", "https://a:b@example.com/",
                         "https://example.com/?q=x", "https://example.com/#fragment", "https://example.com/?",
                         "https://example.com:invalid/", "https://example.com/ bad", "https://example.com/\\bad"):
            with self.subTest(site_url=site_url), self.assertRaises(ConversionError):
                build_html(source, site_url)

    def test_unsupported_commands_fail(self):
        with self.assertRaisesRegex(ConversionError, "Unsupported LaTeX command"):
            render(r"\textbf{Before \unsupported{hidden} after}")
        with self.assertRaisesRegex(ConversionError, "Unclosed"):
            render(r"\textbf{broken")
        with self.assertRaisesRegex(ConversionError, "Unsupported link scheme"):
            render(r"\href{javascript:alert(1)}{unsafe}")


if __name__ == "__main__":
    unittest.main()
