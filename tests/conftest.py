"""
Pytest configuration and shared fixtures.
"""

import pytest

from semantic_search.models import ContentType, ContentBlock


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown document for testing."""
    return """# Main Title

This is an introduction paragraph with some text.

## Section 1

Here's some content in section 1.

```python
def hello_world():
    print("Hello, world!")
```

## Section 2

More content here with a list:

- Item 1
- Item 2
- Item 3

### Subsection 2.1

Final paragraph.
"""


@pytest.fixture
def sample_code_block() -> ContentBlock:
    """Sample code block for testing."""
    return ContentBlock(
        type=ContentType.CODE_BLOCK,
        content='```python\ndef test():\n    pass\n```',
        start_offset=0,
        end_offset=34,
        metadata={"language": "python"},
    )


@pytest.fixture
def sample_header_block() -> ContentBlock:
    """Sample header block for testing."""
    return ContentBlock(
        type=ContentType.HEADER,
        content="## Test Header",
        start_offset=0,
        end_offset=15,
        metadata={"level": 2, "title": "Test Header", "path": ["Test Header"]},
    )
