import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def load_epub(path):
    """Loads an EPUB file."""
    return epub.read_epub(path)

def save_epub(book, path):
    """Saves the EPUB book to the specified path."""
    epub.write_epub(path, book)

def get_chapter_items(book):
    """Yields (id, content) for all document items."""
    # Filter for XHTML/HTML documents
    return [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]

def extract_text_from_html(html_content):
    """Extracts plain text from HTML content using BeautifulSoup."""
    soup = BeautifulSoup(html_content, 'html.parser')
    lines = []
    # Targeted extraction for common novel tags
    for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = tag.get_text().strip()
        if text:
            lines.append(text)
    return "\n".join(lines)
