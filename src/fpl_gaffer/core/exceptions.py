class FPLGafferError(Exception):
    """Base exception class for FPL Gaffer app."""

    pass

class NewsSearchError(FPLGafferError):
    """Custom class for news searching errors."""

    pass

class FPLAPIError(FPLGafferError):
    """Custom class for FPL API errors."""

    pass
