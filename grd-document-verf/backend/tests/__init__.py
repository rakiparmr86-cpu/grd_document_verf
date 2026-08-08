import fitz


def make_pdf_bytes(text: str = "valid document", pages: int = 1) -> bytes:
    document = fitz.open()
    try:
        for page_number in range(pages):
            page = document.new_page()
            page.insert_text((72, 72), f"{text} - page {page_number + 1}")
        return document.tobytes()
    finally:
        document.close()
