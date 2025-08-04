from flask import Flask, render_template, request, jsonify
import re
import subprocess
import sys

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    js_code = ''
    py_code = ''
    output = ''
    if request.method == 'POST':
        js_code = request.form['js_code']
        py_code = convert_js_to_py(js_code)
    return render_template('index.html', js_code=js_code, py_code=py_code, output='')

@app.route('/run', methods=['POST'])
def run_code():
    py_code = request.form['py_code']
    try:
        result = subprocess.run(
            [sys.executable, '-c', py_code],
            text=True,
            capture_output=True,
            timeout=2
        )
        output = result.stdout or result.stderr
    except subprocess.TimeoutExpired:
        output = "⚠️ Execution timed out."
    except Exception as e:
        output = f"❌ Error: {str(e)}"

    # If the request was made via fetch (AJAX), return plain text
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return output

    # Otherwise, render full page (normal form submission)
    return render_template('index.html', js_code='', py_code=py_code, output=output)


def convert_js_to_py(js):
    py = js

    # 🔁 Convert for-loops
    py = re.sub(
        r'for\s*\(\s*(?:let|const|var)?\s*(\w+)\s*=\s*(\d+);\s*\1\s*<\s*(\d+);\s*\1\+\+\s*\)',
        r'for \1 in range(\2, \3):',
        py
    )

    # 🔁 Convert function declarations
    py = re.sub(
        r'function\s+(\w+)\s*\((.*?)\)\s*\{?',
        r'def \1(\2):',
        py
    )

    # 🔁 Convert console.log to print
    py = re.sub(r'console\.log\((.*?)\)', r'print(\1)', py)

    # Convert single-line comments
    py = re.sub(r'//(.*)', r'#\1', py)

    # 🔁 Remove let/const/var
    py = re.sub(r'\b(let|const|var)\s+', '', py)

    # 🔁 Convert true/false/null
    py = re.sub(r'\btrue\b', 'True', py, flags=re.IGNORECASE)
    py = re.sub(r'\bfalse\b', 'False', py, flags=re.IGNORECASE)
    py = re.sub(r'\bnull\b', 'None', py, flags=re.IGNORECASE)

    # ✅ Convert JS list methods
    py = re.sub(r'(\w+)\.push\((.*?)\)', r'\1.append(\2)', py)
    py = re.sub(r'(\w+)\.splice\((\d+),\s*0,\s*(.*?)\)', r'\1.insert(\2, \3)', py)
    py = re.sub(r'(\w+)\.splice\((\d+),\s*1\)', r'del \1[\2]', py)

    # ✅ Add colons to if / elif / while lines
    py = re.sub(
        r'^\s*(if|elif|while)\s*\((.*?)\)\s*\{?\s*$',
        r'\1 \2:',
        py,
        flags=re.MULTILINE
    )

    # ✅ Add colon to else (must be BEFORE removing braces!)
    py = re.sub(
        r'^\s*else\s*[:{]?\s*$',
        'else:',
        py,
        flags=re.MULTILINE
    )

    # Remove lines that contain only whitespace and one or more closing braces
    py = re.sub(r'^\s*\}+\s*;?\s*$', '', py, flags=re.MULTILINE)

    # ❌ Remove braces and semicolons AFTER adding colons
    py = re.sub(r'[{};]', '', py)

    # ✅ Final cleanup: apply 4-space indentation
    lines = py.strip().split('\n')
    indented_lines = []
    indent_level = 0

    for line in lines:
        stripped = line.strip()

        if not stripped:
            indented_lines.append('')
            continue

        if re.match(r'^(elif .*:|else:)$', stripped):
            indent_level = max(indent_level - 1, 0)

        indented_lines.append('    ' * indent_level + stripped)

        if stripped.endswith(':'):
            indent_level += 1

        if re.match(r'^\s*(return|break|continue|pass|raise)\b', stripped) and indent_level > 0:
            indent_level -= 1

    return '\n'.join(indented_lines).strip()



if __name__ == '__main__':
    app.run(debug=True)
