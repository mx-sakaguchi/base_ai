"""アプリ共通例外クラス"""


class AppError(Exception):
    """ビジネスロジック起因のエラー（HTTP ステータスコード付き）"""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, status_code=404)


class ValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class FileTooLargeError(AppError):
    def __init__(self, message: str = "File too large") -> None:
        super().__init__(message, status_code=413)


class InvalidPDFError(AppError):
    def __init__(self, message: str = "Invalid or corrupted PDF") -> None:
        super().__init__(message, status_code=422)
