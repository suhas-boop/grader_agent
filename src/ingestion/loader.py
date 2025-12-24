import os
import nbformat
import PyPDF2

class IngestionEngine:
    """Handles loading and parsing of student submissions."""
    
    def load_submission(self, file_path):
        """Detects file type and returns content."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Submission file not found: {file_path}")
            
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.txt':
            return self._read_text(file_path)
        elif ext == '.pdf':
            return self._read_pdf(file_path)
        elif ext == '.ipynb':
            return self._read_notebook(file_path)
        elif ext == '.json':
            return self._read_text(file_path) # JSON is text, strategies parse it
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _read_text(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _read_pdf(self, path):
        text = ""
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _read_notebook(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        # Extract code and markdown cells
        content = []
        for cell in nb.cells:
            if cell.cell_type == 'code':
                content.append(f"CODE:\n{cell.source}")
            elif cell.cell_type == 'markdown':
                content.append(f"MARKDOWN:\n{cell.source}")
        return "\n\n".join(content)
