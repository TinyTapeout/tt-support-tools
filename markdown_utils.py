import mistune
from mistune.renderers.markdown import MarkdownRenderer


class HeadingsRenderer(MarkdownRenderer):
    def __init__(self, min_level: int):
        super().__init__()
        self.min_level = min_level

    def heading(self, token, state):
        token["attrs"]["level"] += self.min_level - 1
        return super().heading(token, state)


def limit_markdown_headings(source: str, min_level: int) -> str:
    markdown = mistune.create_markdown(renderer=HeadingsRenderer(min_level))
    return markdown(source)
