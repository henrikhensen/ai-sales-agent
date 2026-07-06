from backend.infrastructure.web.sanitizer import extract_readable_text


def test_extracts_title_and_meta_description():
    html = """
    <html>
      <head>
        <title>  Acme GmbH — Home  </title>
        <meta name="description" content="  We build logistics software.  ">
      </head>
      <body><p>Hello world.</p></body>
    </html>
    """
    result = extract_readable_text(html)

    assert result.title == "Acme GmbH — Home"
    assert result.meta_description == "We build logistics software."
    assert "Hello world." in result.text


def test_removes_script_and_style_content_entirely():
    html = """
    <html>
      <head><style>body { color: red; }</style></head>
      <body>
        <script>alert('should not appear');</script>
        <p>Visible paragraph.</p>
      </body>
    </html>
    """
    result = extract_readable_text(html)

    assert "color: red" not in result.text
    assert "alert" not in result.text
    assert "Visible paragraph." in result.text


def test_removes_nav_content_entirely():
    html = """
    <body>
      <nav><a href="/">Home</a><a href="/about">About</a></nav>
      <p>Main content only.</p>
    </body>
    """
    result = extract_readable_text(html)

    assert "Home" not in result.text
    assert "About" not in result.text
    assert "Main content only." in result.text


def test_normalizes_whitespace_and_blank_lines():
    html = """
    <body>
      <p>First    line   with   extra   spaces.</p>


      <p>Second line.</p>
    </body>
    """
    result = extract_readable_text(html)

    assert "First line with extra spaces." in result.text
    assert "Second line." in result.text
    assert "\n\n" not in result.text


def test_missing_title_and_meta_description_are_none():
    html = "<body><p>No head at all.</p></body>"
    result = extract_readable_text(html)

    assert result.title is None
    assert result.meta_description is None
    assert "No head at all." in result.text
