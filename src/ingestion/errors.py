"""Typed rejection reasons raised by the ingestion layer.

All of them subclass ``ValueError`` so existing ``except ValueError`` handlers keep
working; the API layer inspects the concrete type to pick an HTTP status instead of
treating every bad upload as a server fault.
"""


class DocumentRejectedError(ValueError):
    """The document was refused; the message is safe to show to the client."""


class EmptyFileError(DocumentRejectedError):
    """The upload contains no bytes."""


class FileTooLargeError(DocumentRejectedError):
    """The upload exceeds a size or page limit."""


class UnsupportedFileTypeError(DocumentRejectedError):
    """The extension is not allowed, or the content does not match the extension."""


class CorruptedFileError(DocumentRejectedError):
    """The file is of an accepted type but cannot be read (corrupt or encrypted)."""
