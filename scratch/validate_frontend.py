import glob
import os
import re
from html.parser import HTMLParser

class StrictHTMLParser(HTMLParser):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.tags = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in ['img', 'input', 'br', 'hr', 'meta', 'link']:
            self.tags.append(tag)

    def handle_endtag(self, tag):
        if tag not in ['img', 'input', 'br', 'hr', 'meta', 'link']:
            if self.tags and self.tags[-1] == tag:
                self.tags.pop()

def check_html_files():
    html_files = glob.glob('frontend/*.html')
    print(f"Validating {len(html_files)} HTML files...")
    for f in sorted(html_files):
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
        parser = StrictHTMLParser(f)
        try:
            parser.feed(content)
            print(f" [OK] {f} ({len(content):,} chars)")
        except Exception as e:
            print(f" [ERROR] {f}: {e}")

def check_js_files():
    js_files = glob.glob('frontend/**/*.js', recursive=True)
    print(f"\nValidating {len(js_files)} JS files...")
    for f in sorted(js_files):
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
        
        # Check matching braces, brackets, parentheses
        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        in_string = None
        escaped = False
        in_line_comment = False
        in_block_comment = False
        line_no = 1
        error = None

        i = 0
        while i < len(content):
            ch = content[i]
            if ch == '\n':
                line_no += 1
                in_line_comment = False
                i += 1
                continue
            if in_line_comment:
                i += 1
                continue
            if in_block_comment:
                if ch == '*' and i + 1 < len(content) and content[i+1] == '/':
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if in_string:
                if escaped:
                    escaped = False
                elif ch == '\\':
                    escaped = True
                elif ch == in_string:
                    in_string = None
                i += 1
                continue
            if ch == '/' and i + 1 < len(content):
                if content[i+1] == '/':
                    in_line_comment = True
                    i += 2
                    continue
                elif content[i+1] == '*':
                    in_block_comment = True
                    i += 2
                    continue
            if ch in ['"', "'", '`']:
                in_string = ch
                i += 1
                continue
            if ch in ['(', '{', '[']:
                stack.append((ch, line_no))
            elif ch in [')', '}', ']']:
                if not stack:
                    error = f"Unmatched closing '{ch}' at line {line_no}"
                    break
                top, l = stack.pop()
                if top != pairs[ch]:
                    error = f"Mismatched '{top}' (line {l}) and '{ch}' (line {line_no})"
                    break
            i += 1

        if not error and stack:
            top, l = stack[-1]
            error = f"Unclosed '{top}' opened at line {l}"

        if error:
            print(f" [WARN] {f}: {error}")
        else:
            print(f" [OK] {f} ({len(content):,} chars)")

if __name__ == '__main__':
    check_html_files()
    check_js_files()
