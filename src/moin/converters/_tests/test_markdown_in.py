# Copyright: 2008 MoinMoin:BastianBlank
# Copyright: 2012 MoinMoin:AndreasKloeckner
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - moin.converters.markdown_in tests.
"""

import pytest

from collections import namedtuple
from flask import Flask

from moin.utils.tree import moin_page, xlink, xinclude, html
from moin.converters.markdown_in import Converter
from moin.i18n import i18n_init

from . import serialize, XMLNS_RE

DefaultConfig = namedtuple("DefaultConfig", ("markdown_extensions", "locale_default"))
config = DefaultConfig(markdown_extensions=[], locale_default="en")


@pytest.fixture
def _app_context_with_markdown_extensions_config():
    """
    A fixture providing an application context with just the Moin2 configuration
    settings required by the markdown_in converter.
    """
    app = Flask(__name__)
    app.cfg = config
    i18n_init(app)
    with app.app_context() as context:
        yield context


@pytest.mark.usefixtures("_app_context_with_markdown_extensions_config")
class TestConverter:
    namespaces = {moin_page: "", xlink: "xlink", xinclude: "xinclude", html: "html"}

    output_re = XMLNS_RE

    data = [
        ("Text", "<p>Text</p>"),
        ("Text\nTest", "<p>Text\nTest</p>"),
        ("Text\n\nTest", "<p>Text</p><p>Test</p>"),
        ("<http://moinmo.in/>", '<p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p>'),
        (  # ensure a safe scheme, fall back to wiki-internal reference:
            '[yo](javascript:alert("xss"))',
            '<p><a title="xss" html:title="xss" xlink:href="wiki.local:javascript:alert%28">yo</a>)</p>',
        ),
        ("[new page](Yesterday: a legacy)", '<p><a xlink:href="wiki.local:Yesterday:%20a%20legacy">new page</a></p>'),
        ("[MoinMoin](http://moinmo.in/)", '<p><a xlink:href="http://moinmo.in/">MoinMoin</a></p>'),
        ("----", '<separator class="moin-hr3" />'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_base(self, input, output):
        self.do(input, output)

    data = [
        ("*Emphasis*", "<p><emphasis>Emphasis</emphasis></p>"),
        ("_Emphasis_", "<p><emphasis>Emphasis</emphasis></p>"),
        ("**Strong**", "<p><strong>Strong</strong></p>"),
        ("_**Both**_", "<p><emphasis><strong>Both</strong></emphasis></p>"),
        ("**_Both_**", "<p><strong><emphasis>Both</emphasis></strong></p>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_emphasis(self, input, output):
        self.do(input, output)

    data = [
        ("http://moinmo.in/", "<p>http://moinmo.in/</p>"),
        ("\\[escape](yo)", "<p>[escape](yo)</p>"),
        ("\\*yo\\*", "<p>*yo*</p>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_escape(self, input, output):
        self.do(input, output)

    data = [
        (
            "* Item",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list>',
        ),
        (
            "* Item\nItem",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list>',
        ),
        (
            "* Item 1\n* Item 2",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list>',
        ),
        (
            "* Item 1\n    * Item 1.2\n* Item 2",
            '<list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list>',
        ),
        (
            "* List 1\n\nyo\n\n\n* List 2",
            '<list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><p>yo</p><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list>',
        ),
        (
            "8. Item",
            '<list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_list(self, input, output):
        self.do(input, output)

    data = [
        (
            '![Alt text](png "Optional title")',
            '<p><xinclude:include html:alt="Alt text" html:title="Optional title" xinclude:href="wiki.local:png" /></p>',
        ),
        (
            '![](png "Optional title")',
            '<p><xinclude:include html:title="Optional title" xinclude:href="wiki.local:png" /></p>',
        ),
        (
            "![remote image](http://static.moinmo.in/logos/moinmoin.png)",
            '<p><object html:alt="remote image" xlink:href="http://static.moinmo.in/logos/moinmoin.png" /></p>',
        ),
        (
            "![Alt text](http://test.moinmo.in/png)",
            '<p><object html:alt="Alt text" xlink:href="http://test.moinmo.in/png" /></p>',
        ),
        (
            "![transclude local wiki item](someitem)",
            '<p><xinclude:include html:alt="transclude local wiki item" xinclude:href="wiki.local:someitem" /></p>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_image(self, input, output):
        self.do(input, output)

    data = [
        (
            "First Header  | Second Header\n------------- | -------------\nContent Cell  | Content Cell\nContent Cell  | Content Cell",
            "<table><table-header><table-row><table-cell-head>First Header</table-cell-head><table-cell-head>Second Header</table-cell-head></table-row></table-header><table-body><table-row><table-cell>Content Cell</table-cell><table-cell>Content Cell</table-cell></table-row><table-row><table-cell>Content Cell</table-cell><table-cell>Content Cell</table-cell></table-row></table-body></table>",
        )
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_table(self, input, output):
        self.do(input, output)

    data = [
        ("[[Bracketed]]", '<p><a xlink:href="wiki.local:Bracketed">Bracketed</a></p>'),
        (
            "[[Main/sub]]",  # check if label is kept lower case, check if slash in link is detected
            '<p><a xlink:href="wiki.local:Main/sub">sub</a></p>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_wikilinks(self, input, output):
        """Test the Wikilinks extension: https://python-markdown.github.io/extensions/wikilinks/"""
        self.do(input, output)

    data = [
        (
            "!!! note\n    You should note that the title will be automatically capitalized.",
            '<div class="admonition note"><p class="admonition-title">Note</p><p>You should note that the title will be automatically capitalized.</p></div>',
        ),
        (
            '!!! danger "Don\'t try this at home"\n    ...',
            '<div class="admonition danger"><p class="admonition-title">Don\'t try this at home</p><p>...</p></div>',
        ),
        (
            '!!! important ""\n    This is an admonition box without a title.',
            '<div class="admonition important"><p>This is an admonition box without a title.</p></div>',
        ),
        (
            '!!! danger highlight blink "Don\'t try this at home"\n    ...',
            '<div class="admonition danger highlight blink"><p class="admonition-title">Don\'t try this at home</p><p>...</p></div>',
        ),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_admonition(self, input, output):
        self.do(input, output)

    data = [  # TODO: there are too many <div> wrappers!
        # only complete/correct tags are recognized.
        ("one < two", "<p>one &lt; two</p>"),
        ("[[one]] < two", '<p><a xlink:href="wiki.local:one">one</a> &lt; two</p>'),
        ("pre <strong>bold</strong> post", "<div><p>pre <strong>bold</strong> post</p></div>"),
        (  # a block-level element
            "<address>webmaster@example.org</address>",
            '<div><div><div html-tag="address">webmaster@example.org</div>\n</div></div>',
        ),
        # explicitly ignored tags (html_in.HtmlTags.ignored_tags) are dropped together with their content:
        ("<button>Stop</button>", "<div><p /></div>"),
        ("<script>1+1</script>", "<div><p>\n</p></div>"),
        # Markdown syntax in block-level HTML tags is not processed (https://daringfireball.net/projects/markdown/syntax#html)
        ("<h2>**strong** heading</h2>", '<div><div><h outline-level="2">**strong** heading</h>\n</div></div>'),
        # TODO: markdown 3.3 outputs `/>\n\n\n\n</p>`, prior versions output `/></p>`. Try test again with versions 3.3+
        # Added similar test to test_markdown_in_out
        # ('<hr>',
        #  '<div><p><separator html:class="moin-hr3" />\n\n\n\n</p></div>'),  # works only with markdown 3.3
        # <hr> is a block level tag: end paragraph before the tag, start new paragraph after it!
        # TODO currently fails:
        # ("a<hr>_break_", '<div><p>a</p><separator html:class="moin-hr3" /><p><emphasis>break</emphasis></p></div>'),
        # ("a<hr />_break_", '<div><p>a</p><separator html:class="moin-hr3" /><p><emphasis>break</emphasis></p></div>'),
        # (
        #     "a\n<hr>\n_break_",
        #     '<div><p>a</p><separator html:class="moin-hr3" />\n<p><emphasis>break</emphasis></p></div>',
        # ),
        # ("_a_<hr>break", '<div><p><emphasis>a</emphasis></p><separator html:class="moin-hr3" /><p>break</p></div>'),
        # ("_a_<hr>\nbreak", '<div><p><emphasis>a</emphasis></p><separator html:class="moin-hr3" />\n<p>break</p></div>'),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_html_markup(self, input, output):
        """Test handling of HTML markup."""
        self.do(input, output)

    data = [
        # TODO: there are too many <div> wrappers!
        ('<a href="subitem">link text</a>', '<div><p><a xlink:href="wiki.local:subitem">link text</a></p></div>'),
        ("<BIG>larger</BIG>", '<div><p><span html:class="moin-big">larger</span></p></div>'),
        ('<span class="moin-small">smaller</span>', '<div><p><span html:class="moin-small">smaller</span></p></div>'),
        ("<sub>sub</sub>script", "<div><p><sub>sub</sub>script</p></div>"),
        ("<sup>super</sup>script", "<div><p><sup>super</sup>script</p></div>"),
        ("<code>Code</code>", "<div><p><code>Code</code></p></div>"),
        ("<em>Emphasis</em>", "<div><p><emphasis>Emphasis</emphasis></p></div>"),
        ("<i>alternate voice</i>", '<div><p><emphasis html-tag="i">alternate voice</emphasis></p></div>'),
        ("<u>underline</u>", "<div><p><u>underline</u></p></div>"),
        ("<ins>inserted</ins>", "<div><p><ins>inserted</ins></p></div>"),
        ("<kbd>Ctrl-X</kbd>", "<div><p><kbd>Ctrl-X</kbd></p></div>"),
        ("<samp>Error 33</samp>", "<div><p><samp>Error 33</samp></p></div>"),
        ("<tt>literal</tt>", "<div><p><literal>literal</literal></p></div>"),
        ("<del>deleted</del>", "<div><p><del>deleted</del></p></div>"),
        ("<s>no longer accurate</s>", "<div><p><s>no longer accurate</s></p></div>"),
        # the <strike> tag is deprecated since HTML4.1!
        ("<strike>obsolete</strike>", "<div><p><s>obsolete</s></p></div>"),
        ("<q>Inline quote</q>", "<div><p><quote>Inline quote</quote></p></div>"),
        ("<dfn>term</dfn>", '<div><p><emphasis html-tag="dfn">term</emphasis></p></div>'),
        ("<small>fine print</small>", '<div><p><span html-tag="small">fine print</span></p></div>'),
        ("<abbr>e.g.</abbr>", '<div><p><span html-tag="abbr">e.g.</span></p></div>'),
        # keep standard attributes "title", "class", "style", and "alt":
        ('<del class="red">deleted</del>', '<div><p><del html:class="red">deleted</del></p></div>'),
        (
            '<abbr title="for example">e.g.</abbr>',
            '<div><p><span html-tag="abbr" html:title="for example">e.g.</span></p></div>',
        ),
        # in HTML5, <acronym> is deprecated in favour of <abbr>
        ("<acronym>AC/DC</acronym>", '<div><p><span html-tag="abbr">AC/DC</span></p></div>'),
        # <br> is a void inline element
        ("one<br />two", "<div><p>one<line-break />two</p></div>"),
        ("one<br>two", "<div><p>one<line-break />two</p></div>"),
        ("one<br />\ntwo", "<div><p>one<line-break />\ntwo</p></div>"),
        ("one  \ntwo", "<p>one<line-break />\ntwo</p>"),
        # there may be multiple HTML elements in a block
        ("<u>underline</u> and <sub>sub</sub>", "<div><p><u>underline</u> and <sub>sub</sub></p></div>"),
        ("<u>underline with <sub>sub</sub></u>", "<div><p><u>underline with <sub>sub</sub></u></p></div>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_inline_html(self, input, output):
        self.do(input, output)

    data = [  # Markdown syntax inside inline HMTL tags
        (  # Original issue #1838: emphasis inside <del> in a list item
            "* <del>Deleted list item with _emphasized text_</del>",
            '<list item-label-generate="unordered"><list-item><list-item-body>'
            "<del>Deleted list item with <emphasis>emphasized text</emphasis></del>"
            "</list-item-body></list-item></list>",
        ),
        (
            '<a href="subitem">link *text*</a>',
            '<p><a xlink:href="wiki.local:subitem">link <emphasis>text</emphasis></a></p>',
        ),
        (
            '<abbr title="for example">_e.g._</abbr>',
            '<p><span html-tag="abbr" html:title="for example"><emphasis>e.g.</emphasis></span></p>',
        ),
        ("<acronym>**AC/DC**</acronym>", '<p><span html-tag="abbr"><strong>AC/DC</strong></span></p>'),
        ("<BIG>_larger_</BIG>", '<p><span html:class="moin-big"><emphasis>larger</emphasis></span></p>'),
        ("<ins>Inserted with _emphasis_</ins>", "<p><ins>Inserted with <emphasis>emphasis</emphasis></ins></p>"),
        ("<kbd>Press **Q**</kbd>", "<p><kbd>Press <strong>Q</strong></kbd></p>"),
        ("<DEL>`1+1`</DEL>", "<p><del><code>1+1</code></del></p>"),
        ("<dfn>**strong** term</dfn>", '<p><emphasis html-tag="dfn"><strong>strong</strong> term</emphasis></p>'),
        ("<i>alternate **voice**</i>", '<p><emphasis html-tag="i">alternate <strong>voice</strong></emphasis></p>'),
        ("<small>`fine` print</small>", '<p><span html-tag="small"><code>fine</code> print</span></p>'),
        ("<tt>**mono**</tt>", "<p><literal><strong>mono</strong></literal></p>"),
        # explicitly ignored tags are dropped together with their content:
        ("<button>`Stop`</button>", "<p />"),
        ("<script>`1+1`</script>", "<div><p>\n</p></div>"),
        # unknown tags are ignored but their content is passed on:
        ("<custom>`1+1`</custom>", "<p><code>1+1</code></p>"),
    ]

    @pytest.mark.parametrize("input,output", data)
    def test_inline_html_with_embedded_markdown(self, input, output):
        """Test HTML markup containing Markdown markup"""
        self.do(input, output)

    data = [  # Some valid samples still fail!
        # <br> is an inline tag: do not break the paragraph!
        ("one<br>_two_", "<div><p>one<line-break /><emphasis>two</emphasis></p></div>"),
        ("one<br />_two_", "<div><p>one<line-break /><emphasis>two</emphasis</p>></div>"),
        ("one<br>\n_two_", "<div><p>one<line-break /><emphasis>two</emphasis></p></div>"),
        ("_one_<br>two", "<div><p><emphasis>one</emphasis><line-break />two</p></div>"),
        ("_one_<br>\ntwo", "<div><p><emphasis>one</emphasis><line-break />\ntwo</p></div>"),
        # there may be multiple HTML elements in a block
        (  # paragraph starts too late
            "<u>**underline**</u> and <sub>sub</sub>",
            "<div><p><u><strong>underline</strong></u> and <sub>sub</sub></p></div>",
        ),
        (  # Error: malformed HTML: end tag mismatch
            "<u>underline</u> and <sub>**sub**</sub>",
            "<div><p><u>underline</u> and <sub><strong>sub</strong></sub></p></div>",
        ),
        (
            "<u>**underline**</u> and <sub>**sub**</sub>",
            "<div><p><u><strong>underline</strong></u> and <sub><strong>sub</strong></sub></p></div>",
        ),
    ]

    @pytest.mark.xfail
    @pytest.mark.parametrize("input,output", data)
    def test_failing_html_and_markdown(self, input, output):
        """Test HTML tags containing Markdown inline markup"""
        self.do(input, output)

    def serialize_strip(self, elem, **options):
        result = serialize(elem, namespaces=self.namespaces, **options)
        return self.output_re.sub("", result)

    def do(self, input, output, args={}):
        conv = Converter()
        out = conv(input, "text/x-markdown;charset=utf-8", **args)
        got_output = self.serialize_strip(out)
        desired_output = "<page><body>%s</body></page>" % output
        print("------------------------------------")
        print("WANTED:")
        print(desired_output)
        print("GOT:")
        print(got_output)
        assert got_output == desired_output
