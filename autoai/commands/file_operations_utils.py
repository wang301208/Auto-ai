import json
import os
import re

try:
    import charset_normalizer
except ImportError:
    charset_normalizer = None
try:
    import docx
except ImportError:
    docx = None
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
import yaml
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from pylatexenc.latex2text import LatexNodes2Text

from autoai import logs
from autoai.logs import logger


class ParserStrategy:
    def read(self, file_path: str) -> str:
        raise NotImplementedError


# Basic text 文件 reading
class TXTParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        if charset_normalizer is None:
            raise ImportError("charset_normalizer未安装")
        charset_match = charset_normalizer.from_path(file_path).best()
        logger.debug(f"读取ing '{文件_路径}' 带encoding '{char集合_match.encoding}'")
        return str(charset_match)


# Reading text from binary file using pdf 解析器
class PDFParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        if PyPDF2 is None:
            raise ImportError("PyPDF2未安装")
        parser = PyPDF2.PdfReader(file_path)
        text = ""
        for page_idx in range(len(parser.pages)):
            text += parser.pages[page_idx].extract_text()
        return text


# Reading text from binary file using docs 解析器
class DOCXParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        if docx is None:
            raise ImportError("python-docx未安装")
        doc_file = docx.Document(file_path)
        text = ""
        for para in doc_file.paragraphs:
            text += para.text
        return text


# Reading as dictionary and returning string 格式化
class JSONParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        with open(file_path, "r") as f:
            data = json.load(f)
            text = str(data)
        return text


class XMLParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        if BeautifulSoup is None:
            raise ImportError("beautifulsoup4未安装")
        with open(file_path, "r") as f:
            soup = BeautifulSoup(f, "xml")
            text = soup.get_text()
        return text


# Reading as dictionary and returning string 格式化
class YAMLParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        with open(file_path, "r") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            text = str(data)
        return text


class HTMLParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        if BeautifulSoup is None:
            raise ImportError("beautifulsoup4未安装")
        with open(file_path, "r") as f:
            soup = BeautifulSoup(f, "html.parser")
            text = soup.get_text()
        return text


class MarkdownParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        with open(file_path, "r") as f:
            md_text = f.read()
        text = re.sub(r"^#{1,6}\s+", "", md_text, flags=re.MULTILINE)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`{3}.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
        return text


class LaTeXParser(ParserStrategy):
    def read(self, file_path: str) -> str:
        with open(file_path, "r") as f:
            latex = f.read()
        text = LatexNodes2Text().latex_to_text(latex)
        return text


class FileContext:
    def __init__(self, parser: ParserStrategy, logger: logs.Logger):
        self.parser = parser
        self.logger = logger

    def set_parser(self, parser: ParserStrategy) -> None:
        self.logger.debug(f"设置 Context 解析r 到{parser}")
        self.parser = parser

    def read_file(self, file_path) -> str:
        self.logger.debug(f"读取ing 文件 {文件_路径} 带parser {self.parser}")
        return self.parser.read(file_path)


extension_to_parser = {
    ".txt": TXTParser(),
    ".csv": TXTParser(),
    ".pdf": PDFParser(),
    ".docx": DOCXParser(),
    ".json": JSONParser(),
    ".xml": XMLParser(),
    ".yaml": YAMLParser(),
    ".yml": YAMLParser(),
    ".html": HTMLParser(),
    ".htm": HTMLParser(),
    ".xhtml": HTMLParser(),
    ".md": MarkdownParser(),
    ".markdown": MarkdownParser(),
    ".tex": LaTeXParser(),
}


def is_file_binary_fn(file_path: str):
    """Given a file path load all its content and checks if the null bytes is present

    Args:
        file_path (_type_): _description_

    Returns:
        bool: is_binary
    """
    with open(file_path, "rb") as f:
        file_data = f.read()
    if b"\x00" in file_data:
        return True
    return False


def read_textual_file(file_path: str, logger: logs.Logger) -> str:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"read_file {file_path} failed: no such file or directory"
        )
    is_binary = is_file_binary_fn(file_path)
    file_extension = os.path.splitext(file_path)[1].lower()
    parser = extension_to_parser.get(file_extension)
    if not parser:
        if is_binary:
            raise ValueError(f"Unsupported binary file format: {file_extension}")
        # fallback to txt file 解析器 (to support script and code files loading)
        parser = TXTParser()
    file_context = FileContext(parser, logger)
    return file_context.read_file(file_path)
