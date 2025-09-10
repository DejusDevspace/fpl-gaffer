class FPLGafferError(Exception):
    """Base exception class for FPL Gaffer app."""

    pass

class NewsSearchError(FPLGafferError):
    """Custom class for news searching errors."""

    pass

class FPLAPIError(FPLGafferError):
    """Custom class for FPL API errors."""

    pass

class ToolError(FPLGafferError):
    """Custom class for tool-related errors."""

    pass

class ToolExecutionError(FPLGafferError):
    """Custom class for tool wrapper execution errors."""

    pass
