from fastapi import HTTPException, status

class AppException(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class EntityNotFoundError(AppException):
    def __init__(self, entity_name: str, identifier: str = ""):
        message = f"{entity_name} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message=message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid credentials or token expired"):
        super().__init__(message=message, code="AUTHENTICATION_FAILED", status_code=status.HTTP_401_UNAUTHORIZED)

class AuthorizationError(AppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message=message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)

class ProviderError(AppException):
    def __init__(self, message: str, provider_code: str = "PROVIDER_ERROR", code: str = None):
        c = code or provider_code
        super().__init__(message=message, code=c, status_code=status.HTTP_502_BAD_GATEWAY)

class SandboxExecutionError(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, code="SANDBOX_ERROR", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(entity_name=message, identifier="")

class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=status.HTTP_400_BAD_REQUEST)



def translate_model_error(exc: Exception) -> AppException:
    """Map raw LLM provider exceptions (Azure/Bedrock/LangChain) to user-safe typed errors.
    Never echoes provider payloads, which can include request IDs or account details."""
    if isinstance(exc, AppException):
        return exc
    name = type(exc).__name__
    text = str(exc)
    low = text.lower()
    if ("content management policy" in low or "content_filter" in low or "responsibleaipolicyviolation" in low
            or "jailbreak" in low or "guardrail" in low or "content filtering" in low):
        return AppException(
            "Your answer tripped the AI provider's safety filter, so the interviewer couldn't read it. "
            "Rephrase it as a normal answer and send it again.",
            code="MODEL_CONTENT_FILTERED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if "ratelimit" in name.lower() or "throttl" in low or "429" in text or "too many requests" in low:
        return AppException(
            "The AI provider is rate-limiting requests. Wait a few seconds and resend.",
            code="MODEL_RATE_LIMITED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    if "timeout" in name.lower() or "timed out" in low:
        return AppException(
            "The AI provider timed out. Your answer was not lost; resend it.",
            code="MODEL_TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    return AppException(
        "The AI interviewer is temporarily unavailable. Your draft is preserved; try again.",
        code="MODEL_UNAVAILABLE",
        status_code=status.HTTP_502_BAD_GATEWAY,
    )
