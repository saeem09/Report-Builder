from bs4 import BeautifulSoup

HTML_PARSER_NAME = "html.parser"
NON_CONTENT_TAGS = ("script", "style")


def parse_html(content: bytes) -> str:
    """Extract visible text from an HTML document.

    Script and style bodies are removed because they are markup machinery,
    not meeting content. BeautifulSoup handles encoding detection on bytes.
    The soup is a locally built parse tree, so decomposing nodes on it never
    mutates caller-owned data.
    """
    soup = BeautifulSoup(content, HTML_PARSER_NAME)
    for element in soup(list(NON_CONTENT_TAGS)):
        element.decompose()
    return soup.get_text(separator="\n")
