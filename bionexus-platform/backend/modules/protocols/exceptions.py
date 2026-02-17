"""Business-level exceptions for the Protocols module."""


class ProtocolValidationError(Exception):
    """Raised when protocol data fails business validation rules."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))


class ProtocolNotFoundError(Exception):
    """Raised when a requested protocol does not exist."""

    def __init__(self, protocol_id: int):
        self.protocol_id = protocol_id
        super().__init__(f"Protocol with id {protocol_id} not found")
