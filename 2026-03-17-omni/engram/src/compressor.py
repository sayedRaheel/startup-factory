import re

def compress_code(code: str) -> str:
    """
    Token-crushing: basic AST trimming equivalent via regex.
    Removes comments, excessive whitespace, and blank lines.
    """
    # Remove single-line comments (Python/JS/TS)
    code = re.sub(r'(?m)^[\s]*[#//].*$', '', code)
    # Remove multi-line empty lines
    code = re.sub(r'\n\s*\n', '\n', code)
    # Trim overall payload
    return code.strip()
