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
    def __init__(self, message: str, provider_code: str = "PROVIDER_ERROR"):
        super().__init__(message=message, code=provider_code, status_code=status.HTTP_502_BAD_GATEWAY)

class SandboxExecutionError(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, code="SANDBOX_ERROR", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
