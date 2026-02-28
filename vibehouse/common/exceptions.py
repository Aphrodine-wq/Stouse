from fastapi import HTTPException, status


class VibeHouseException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(VibeHouseException):
    def __init__(self, resource: str, resource_id: str | None = None):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} '{resource_id}' not found"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class PermissionDeniedError(VibeHouseException):
    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class BadRequestError(VibeHouseException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class ConflictError(VibeHouseException):
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class ExternalServiceError(VibeHouseException):
    def __init__(self, service: str, detail: str | None = None):
        msg = f"External service error: {service}"
        if detail:
            msg += f" - {detail}"
        super().__init__(detail=msg, status_code=status.HTTP_502_BAD_GATEWAY)
