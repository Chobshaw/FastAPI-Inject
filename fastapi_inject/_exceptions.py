class NotEnabledError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Injection must be enabled before using @inject. "
            "Please use enable_injection(app)",
        )
