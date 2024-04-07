import os
from typing import Any, Dict

import mistune
from mistune.renderers.markdown import MarkdownRenderer


class HeadingsRenderer(MarkdownRenderer):
    def __init__(self, min_level: int):
        super().__init__()
        self.min_level = min_level
        self.initial_level = float("inf")

    def heading(self, token: Dict[str, Any], state: Any):
        if self.initial_level == float("inf"):
            self.initial_level = token["attrs"]["level"]
        token["attrs"]["level"] += self.min_level - max(1, self.initial_level)
        return super().heading(token, state)


def limit_markdown_headings(source: str, min_level: int) -> str:
    markdown = mistune.create_markdown(renderer=HeadingsRenderer(min_level))
    return markdown(source)


class ImagePathRewriterRenderer(MarkdownRenderer):
    def __init__(self, prefix: str):
        super().__init__()
        self.prefix = prefix

    def image(self, token, state):
        url = token["attrs"]["url"]
        if "://" not in url and not url.startswith("/"):
            token["attrs"]["url"] = os.path.join(self.prefix, url)
        elif ".." in url:
            token["attrs"]["url"] = ""
        elif url.startswith("/"):
            token["attrs"]["url"] = os.path.join(self.prefix, "../" + url[1:])
        return super().image(token, state)


def rewrite_image_paths(source: str, prefix: str) -> str:
    markdown = mistune.create_markdown(renderer=ImagePathRewriterRenderer(prefix))
    return markdown(source)
