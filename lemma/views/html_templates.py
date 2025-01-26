CODE_HIGHLIGHT_HTML_CONTENT = (
    lambda language, code: f"""
<html>
<head>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.4.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.4.0/highlight.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/highlightjs-line-numbers.js/dist/highlightjs-line-numbers.min.js"></script>
    <style>
        .hljs-ln-numbers {{
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            -khtml-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;

            text-align: left;
            color: #ccc;
            vertical-align: top;
            padding-right: 5px;
            color: #bbb;
        }}
    </style>
</head>
<body>
    <pre><code class="{language}">{code}</code></pre>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            hljs.highlightAll();
            hljs.initLineNumbersOnLoad();
        }});
    </script>
</body>
</html>
"""
)


DIFF_VIEWER_HTML_CONTENT = (
    lambda diff: f"""
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/diff2html/bundles/css/diff2html.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.4.0/styles/github.min.css">
</head>
<body>
    <div id="diff-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/diff2html/bundles/js/diff2html.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.4.0/highlight.min.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        var diffString = `{diff}`;
        var targetElement = document.getElementById('diff-container');
        var html = Diff2Html.html(diffString, {{
            drawFileList: false,
            matching: 'lines',
            outputFormat: 'line-by-line',
            synchronisedScroll: true
        }});
        targetElement.innerHTML = html;

        // Manually trigger highlight.js on the diff output
        document.querySelectorAll('pre code').forEach((block) => {{
            hljs.highlightBlock(block);
        }});
    }});
    </script>
</body>
</html>
"""
)


MERMAID_HTML_CONTENT = (
    lambda mermaid_code: f"""
<div class="mermaid">
    {mermaid_code}
</div>
<script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@9/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true }});
</script>
"""
)
