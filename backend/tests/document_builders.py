"""In-memory builders for real test documents.

Test inputs are generated with the same libraries that parse them, so the
suite is self-contained and needs no checked-in binary fixture files.
"""

import io

from docx import Document


def build_docx_bytes(paragraphs, table_rows=()):
    """Build a .docx file in memory.

    paragraphs: an iterable of paragraph strings, added in order.
    table_rows: an iterable of equal-length row tuples appended as one table.
    """
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    if table_rows:
        table = document.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for row_index, row_values in enumerate(table_rows):
            for cell_index, value in enumerate(row_values):
                table.cell(row_index, cell_index).text = value
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
