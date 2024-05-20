import pytest

from apps.shared.domain.custom_validations import sanitize_string


@pytest.mark.parametrize(
    "value, sanitized_value_expected",
    (
        # needs sanitization
        ("One <script>alert('Injected!')</script> Two", "One  Two"),
        ("<script>alert('Injected!');</script>", ""),
        ("""<img src="nothing" onerror="alert('Injected!');">""", '<img src="nothing">'),
        ("""<div style="background-image: url('javascript:alert(\'Injected!\')')">""", "<div></div>"),
        ("""<a href="javascript:alert('Injected!')">Click me</a>""", "<a>Click me</a>"),
        ("""<input type="text" value="<img src=x onerror=alert('Injected!')>">""", ""),
        (
            '<ul class="contain"><li class="task"><input class="item" disabled type="checkbox"> Friday</li></ul>',
            '<ul class="contain"><li class="task"> Friday</li></ul>',
        ),
        # don't need sanitization
        ('<a href="http://test.com/test">Click me</a>', '<a href="http://test.com/test">Click me</a>'),
        (
            '<p data-line="0"><code>test</code><br> <strong>test</strong><br> <em>test</em></p>',
            '<p data-line="0"><code>test</code><br> <strong>test</strong><br> <em>test</em></p>',
        ),
        ('<h1 id="test" data-line="3">test</h1>', '<h1 id="test" data-line="3">test</h1>'),
        (
            '<p data-line="4"><ins>test</ins><br> <s>test</s><br> <mark>test</mark><br> <sub>test</sub><br></p>',
            '<p data-line="4"><ins>test</ins><br> <s>test</s><br> <mark>test</mark><br> <sub>test</sub><br></p>',
        ),
        ('<div class="hljs-left"> <p>test</p> </div>', '<div class="hljs-left"> <p>test</p> </div>'),
        (
            '<blockquote data-line="19"> <p>test</p> </blockquote>',
            '<blockquote data-line="19"> <p>test</p> </blockquote>',
        ),
        (
            '<p data-line="21"><a href="http://test.com/test">test</a></p>',
            '<p data-line="21"><a href="http://test.com/test">test</a></p>',
        ),
        (
            '<figure><img loading="lazy" class="md-zoom" alt="Screenshot 2024-05-13 at 19.40.34.png" src="https://media.cmiml.net/test.png"></figure>',
            '<figure><img loading="lazy" class="md-zoom" alt="Screenshot 2024-05-13 at 19.40.34.png" src="https://media.cmiml.net/test.png"></figure>',
        ),
        (
            '<figure><img src="https://imzbf.github.io/mark_emoji.gif" alt="Picture" class="md-zoom"></figure>',
            '<figure><img src="https://imzbf.github.io/mark_emoji.gif" alt="Picture" class="md-zoom"></figure>',
        ),
        (
            '<h2 data-line="20" id="🤗 Demo">🤗 Demo</h2>',
            '<h2 data-line="20" id="🤗 Demo">🤗 Demo</h2>',
        ),
        (
            '<span class="mspace">🧬 Demo</span>',
            '<span class="mspace">🧬 Demo</span>',
        ),
        (
            """<table data-line="44">
                <thead>
                    <tr>
                        <th>nickname</th>
                        <th>from</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Demo</td>
                        <td>TX, USA</td>
                    </tr>
                </tbody>
                </table>""",
            """<table data-line="44">
                <thead>
                    <tr>
                        <th>nickname</th>
                        <th>from</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Demo</td>
                        <td>TX, USA</td>
                    </tr>
                </tbody>
                </table>""",
        ),
    ),
)
def test_validate_not_valid_hour_minute(value: str, sanitized_value_expected: str):
    sanitized_value = sanitize_string(value)
    assert sanitized_value == sanitized_value_expected
