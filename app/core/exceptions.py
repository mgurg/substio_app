from uuid import UUID


class NotFoundError(Exception):
    """Raised when a resource is not found"""
    def __init__(self, model_name: str, identifier: str | UUID):
        self.model_name = model_name
        self.identifier = identifier
        super().__init__(f"{model_name} with identifier '{identifier}' not found")


class ConflictError(Exception):
    pass
