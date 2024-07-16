import math
import os
import shutil
from typing import Any, Dict

import mistune
from mistune.renderers.markdown import MarkdownRenderer


class HeadingsRenderer(MarkdownRenderer):
    def __init__(self, min_level: int):
        super().__init__()
        self.min_level = min_level
        self.initial_level = math.inf

    def heading(self, token: Dict[str, Any], state: Any):
        if self.initial_level == math.inf:
            self.initial_level = token["attrs"]["level"]
        token["attrs"]["level"] = self.min_level + max(
            token["attrs"]["level"] - self.initial_level, 0
        )
        return super().heading(token, state)


def limit_markdown_headings(source: str, min_level: int) -> str:
    markdown = mistune.create_markdown(renderer=HeadingsRenderer(min_level))
    return markdown(source)


def unescape_braces(text: str):
    return text.replace("%7B", "{").replace("%7D", "}")


class ImagePathRewriterRenderer(MarkdownRenderer):
    def __init__(self, prefix: str):
        super().__init__()
        self.prefix = prefix

    def image(self, token, state):
        url = token["attrs"]["url"]
        if "%7B" in url:
            pass
        elif "://" not in url and not url.startswith("/"):
            url = os.path.join(self.prefix, url)
        elif ".." in url:
            url = ""
        elif url.startswith("/"):
            url = os.path.join(self.prefix, "../" + url[1:])
        token["attrs"]["url"] = url
        return super().image(token, state)


def rewrite_image_paths(source: str, prefix: str) -> str:
    markdown = mistune.create_markdown(renderer=ImagePathRewriterRenderer(prefix))
    return unescape_braces(markdown(source))


class WebsiteImagePathRewriterRenderer(MarkdownRenderer):
    def __init__(self, source_dir: str, target_dir: str):
        super().__init__()
        self.source_dir = source_dir
        self.target_dir = target_dir

    def image(self, token, state):
        url = token["attrs"]["url"]
        if "%7B" in url:
            pass
        elif ".." in url:
            url = ""
        elif "://" not in url and not url.startswith("/"):
            filename = os.path.basename(url)
            if url.startswith("/"):
                url = "../" + url[1:]
            shutil.copyfile(
                os.path.join(self.source_dir, url),
                os.path.join(self.target_dir, filename),
            )
            url = f"images/{filename}"
        token["attrs"]["url"] = url
        return super().image(token, state)
