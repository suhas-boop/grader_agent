import nbformat as nbf

nb = nbf.v4.new_notebook()

code_source = """
def add(a, b):
    return a + b

print(add(2, 3))
"""

text_source = "This is a markdown cell explaining the code."

nb.cells = [
    nbf.v4.new_markdown_cell(text_source),
    nbf.v4.new_code_cell(code_source)
]

with open('grader_agent/test_notebook.ipynb', 'w') as f:
    nbf.write(nb, f)
