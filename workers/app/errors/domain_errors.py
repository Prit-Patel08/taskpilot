from __future__ import annotations


class DomainError(Exception):
    error_code = "DOMAIN_ERROR"
    retryable = False

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.error_code = self.__class__.error_code
        self.retryable = self.__class__.retryable


class FileNotFoundError(DomainError):
    error_code = "FILE_NOT_FOUND"
    retryable = False


class ExternalServiceTimeout(DomainError):
    error_code = "EXTERNAL_TIMEOUT"
    retryable = True


class InvalidApplicationState(DomainError):
    error_code = "INVALID_STATE"
    retryable = False


class ParseFailed(DomainError):
    error_code = "PARSE_FAILED"
    retryable = False


class UnsupportedFormat(DomainError):
    error_code = "UNSUPPORTED_FORMAT"
    retryable = False


class ResumeExtractionPending(DomainError):
    error_code = "RESUME_EXTRACTION_PENDING"
    retryable = True


class DataMissing(DomainError):
    error_code = "DATA_MISSING"
    retryable = False


class ScoringFailed(DomainError):
    error_code = "SCORING_FAILED"
    retryable = False
