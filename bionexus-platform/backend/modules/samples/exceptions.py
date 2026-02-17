"""Business-level exceptions for the Samples module."""


class SampleValidationError(Exception):
    """Raised when sample data fails business validation rules."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))


class SampleNotFoundError(Exception):
    """Raised when a requested sample does not exist."""

    def __init__(self, sample_id: int):
        self.sample_id = sample_id
        super().__init__(f"Sample with id {sample_id} not found")
