"""
Custom exceptions for the PPTX Template Engine.
"""


class PPTXTemplateError(Exception):
    """Base exception for all PPTX template errors."""

    pass


class InvalidTemplateError(PPTXTemplateError):
    """Raised when the template file is not a valid PPTX."""

    def __init__(self, message: str = "Invalid PPTX template file", path: str = None):
        self.path = path
        super().__init__(f"{message}: {path}" if path else message)


class PlaceholderError(PPTXTemplateError):
    """Raised when there's an error with placeholder syntax or matching."""

    def __init__(self, message: str, placeholder: str = None, slide_num: int = None):
        self.placeholder = placeholder
        self.slide_num = slide_num
        details = []
        if placeholder:
            details.append(f"placeholder='{placeholder}'")
        if slide_num is not None:
            details.append(f"slide={slide_num}")
        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"{message}{detail_str}")


class MissingContextError(PPTXTemplateError):
    """Raised when a required context variable is not provided."""

    def __init__(self, variable: str, slide_num: int = None):
        self.variable = variable
        self.slide_num = slide_num
        location = f" on slide {slide_num}" if slide_num is not None else ""
        super().__init__(f"Missing required context variable '{variable}'{location}")


class ImageError(PPTXTemplateError):
    """Raised when there's an error processing an image placeholder."""

    def __init__(self, message: str, image_path: str = None, placeholder: str = None):
        self.image_path = image_path
        self.placeholder = placeholder
        details = []
        if placeholder:
            details.append(f"placeholder='{placeholder}'")
        if image_path:
            details.append(f"path='{image_path}'")
        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"{message}{detail_str}")


class LoopError(PPTXTemplateError):
    """Raised when there's an error processing a loop construct."""

    def __init__(self, message: str, loop_var: str = None, slide_num: int = None):
        self.loop_var = loop_var
        self.slide_num = slide_num
        details = []
        if loop_var:
            details.append(f"loop='{loop_var}'")
        if slide_num is not None:
            details.append(f"slide={slide_num}")
        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"{message}{detail_str}")
