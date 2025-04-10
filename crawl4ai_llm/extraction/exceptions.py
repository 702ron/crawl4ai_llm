"""
Exceptions for the extraction module.

This module defines custom exceptions used in the extraction process.
"""


class ExtractionError(Exception):
    """Base class for extraction exceptions."""

    pass


class SchemaValidationError(ExtractionError):
    """
    Exception raised when a schema validation fails.

    This exception is raised when an extraction schema fails validation,
    such as missing required fields or invalid selectors.
    """

    pass


class SchemaGenerationError(ExtractionError):
    """
    Exception raised when schema generation fails.

    This exception is raised when the automatic schema generation process
    encounters errors, such as missing or invalid HTML content.
    """

    pass


class ExtractionTimeout(ExtractionError):
    """
    Exception raised when extraction exceeds the time limit.

    This exception is raised when an extraction operation takes longer
    than the specified timeout period.
    """

    pass


class NoDataExtracted(ExtractionError):
    """
    Exception raised when no data could be extracted.

    This exception is raised when the extraction process completes
    but no product data could be extracted from the page.
    """

    pass
