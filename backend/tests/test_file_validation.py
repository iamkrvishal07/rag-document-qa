from app.utils.file_validation import (
    get_file_extension,
    is_supported_file,
)


def test_pdf_extension():
    assert (
        get_file_extension(
            "document.pdf"
        )
        == ".pdf"
    )


def test_docx_extension():
    assert (
        get_file_extension(
            "resume.docx"
        )
        == ".docx"
    )


def test_extension_case_insensitive():
    assert (
        get_file_extension(
            "FILE.PDF"
        )
        == ".pdf"
    )


def test_supported_pdf():
    assert is_supported_file(
        "document.pdf",
        "application/pdf",
    )


def test_supported_docx():
    assert is_supported_file(
        "document.docx",
        (
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
    )


def test_reject_txt_file():
    assert not is_supported_file(
        "document.txt",
        "text/plain",
    )


def test_reject_wrong_mime_type():
    assert not is_supported_file(
        "document.pdf",
        "text/plain",
    )
