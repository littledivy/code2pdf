#!/usr/bin/env python3

import os
import glob
import argparse
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, XPreformatted
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor
from pygments import lex
from pygments.lexers import CppLexer, JavascriptLexer, PythonLexer, get_lexer_by_name
from pygments.token import Token
from datetime import datetime

def detect_project_type(base_path):
    """Detect the type of project based on files present."""
    if os.path.exists(os.path.join(base_path, 'package.json')):
        return 'nodejs'
    elif os.path.exists(os.path.join(base_path, 'include')) or os.path.exists(os.path.join(base_path, 'src')):
        return 'cpp'
    return 'generic'

def get_nodejs_files(base_path):
    """Get all Node.js/Express project files, excluding common directories."""
    excluded_dirs = {'node_modules', '.git', 'dist', 'build', '.next', 'coverage', '.vscode', '.idea', '__pycache__'}
    excluded_files = {'package-lock.json', 'main.css', 'output.css', 'styles.css'}
    file_extensions = {'.js', '.ejs', '.json', '.ts', '.jsx', '.tsx', '.css', '.html', '.sql'}

    code_files = []

    for root, dirs, files in os.walk(base_path):
        # Remove excluded directories from the search
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        for file in sorted(files):
            # Skip excluded files
            if file in excluded_files:
                continue

            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file)

            if ext in file_extensions:
                code_files.append(file_path)

    return sorted(code_files)

def get_cpp_files(base_path):
    """Get all C++ source and header files, excluding build directory."""
    cpp_files = []
    h_files = []

    # Get all .cpp files from src/
    src_path = os.path.join(base_path, 'src')
    if os.path.exists(src_path):
        for file in sorted(glob.glob(os.path.join(src_path, '*.cpp'))):
            cpp_files.append(file)

    # Get all .h files from include/
    include_path = os.path.join(base_path, 'include')
    if os.path.exists(include_path):
        for file in sorted(glob.glob(os.path.join(include_path, '*.h'))):
            h_files.append(file)

    # Combine: headers first, then source files
    return h_files + cpp_files

def get_code_files(base_path, project_type=None):
    """Get all code files based on project type."""
    if project_type is None:
        project_type = detect_project_type(base_path)

    if project_type == 'nodejs':
        return get_nodejs_files(base_path)
    elif project_type == 'cpp':
        return get_cpp_files(base_path)
    else:
        return get_nodejs_files(base_path)  # Default to generic file collection

def get_lexer_for_file(file_path):
    """Get the appropriate Pygments lexer for a file based on its extension."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    lexer_map = {
        '.js': 'javascript',
        '.jsx': 'jsx',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.ejs': 'html+javascript',
        '.json': 'json',
        '.html': 'html',
        '.css': 'css',
        '.cpp': 'cpp',
        '.h': 'cpp',
        '.py': 'python',
        '.sql': 'sql',
    }

    try:
        lexer_name = lexer_map.get(ext, 'text')
        return get_lexer_by_name(lexer_name)
    except:
        return get_lexer_by_name('text')

def syntax_highlight_line(line_content, line_num, lexer):
    """Apply syntax highlighting to a single line of code."""
    # Color scheme for different token types
    token_colors = {
        Token.Keyword: '#0000FF',           # Blue for keywords
        Token.Keyword.Type: '#0000FF',      # Blue for types
        Token.Keyword.Constant: '#0000FF',  # Blue for constants
        Token.Comment: '#008000',           # Green for comments
        Token.Comment.Single: '#008000',
        Token.Comment.Multiline: '#008000',
        Token.Comment.Preproc: '#0000FF',   # Blue for preprocessor
        Token.String: '#A31515',            # Red for strings
        Token.String.Char: '#A31515',
        Token.Number: '#098658',            # Teal for numbers
        Token.Name.Class: '#267F99',        # Teal for class names
        Token.Name.Function: '#795E26',     # Brown for functions
        Token.Name.Builtin: '#0000FF',      # Blue for built-ins
        Token.Operator: '#000000',          # Black for operators
        Token.Punctuation: '#000000',       # Black for punctuation
    }

    def get_color(token_type):
        """Get color for a token type."""
        color = token_colors.get(token_type, '#000000')
        if color == '#000000':
            for parent_type, parent_color in token_colors.items():
                if token_type in parent_type:
                    return parent_color
        return color

    tokens = list(lex(line_content, lexer))

    # Build the highlighted line with proper escaping
    result_parts = []
    for token_type, token_value in tokens:
        # Escape XML special characters but preserve spaces
        escaped_value = (token_value
                        .replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace(' ', '&nbsp;'))

        color = get_color(token_type)
        result_parts.append(f'<font color="{color}">{escaped_value}</font>')

    highlighted_code = ''.join(result_parts)

    # Add line number in gray
    return f'<font color="#808080">{line_num:4d}</font>  {highlighted_code}'

def create_pdf(base_path=None, output_filename='code_submission.pdf'):
    """Create PDF with all code files."""
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))

    base_path = os.path.abspath(os.path.expanduser(base_path))

    if not os.path.exists(base_path):
        print(f"Error: Path '{base_path}' does not exist!")
        return

    project_type = detect_project_type(base_path)
    print(f"Detected project type: {project_type}")

    # Get all files
    files = get_code_files(base_path, project_type)

    if not files:
        print("No code files found!")
        return

    print(f"Found {len(files)} files to include in PDF")

    # Create project name from directory name
    project_name = os.path.basename(base_path)

    # Create PDF
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Container for the 'Flowable' objects
    elements = []

    # Styles
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_LEFT
    )

    # File header style
    file_header_style = ParagraphStyle(
        'FileHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#2c5aa0'),
        spaceAfter=12,
        spaceBefore=20,
        alignment=TA_LEFT
    )

    # Code style with preserved whitespace
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Code'],
        fontSize=7,
        leading=8.4,
        leftIndent=0,
        rightIndent=0,
        fontName='Courier',
        textColor=HexColor('#000000'),
        spaceBefore=0,
        spaceAfter=0,
        allowWidows=1,
        allowOrphans=1
    )

    # Add table of contents
    elements.append(Paragraph(f"Table of Contents - {project_name}", title_style))
    elements.append(Spacer(1, 0.2*inch))

    # Group files by directory
    from collections import defaultdict
    dir_files = defaultdict(list)
    file_index = 1

    for file_path in files:
        filename = os.path.basename(file_path)
        relative_dir = os.path.dirname(os.path.relpath(file_path, base_path))
        if relative_dir == '':
            relative_dir = '.'
        dir_files[relative_dir].append((file_index, filename))
        file_index += 1

    # Create tree-style TOC
    toc_dir_style = ParagraphStyle(
        'TOCDir',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#2c5aa0'),
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    toc_file_style = ParagraphStyle(
        'TOCFile',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=20,
        spaceAfter=4
    )

    # Sort directories
    for dir_name in sorted(dir_files.keys()):
        elements.append(Paragraph(f"{dir_name}/", toc_dir_style))
        files_in_dir = dir_files[dir_name]
        for i, (idx, filename) in enumerate(files_in_dir):
            prefix = "`--" if i == len(files_in_dir) - 1 else "|--"
            elements.append(Paragraph(f"{prefix} {idx}. {filename}", toc_file_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(PageBreak())

    # Add each file
    for i, file_path in enumerate(files, 1):
        filename = os.path.basename(file_path)
        relative_path = os.path.relpath(file_path, base_path)

        print(f"Processing {i}/{len(files)}: {filename}")

        # Add file header
        elements.append(Paragraph(f"{i}. {filename}", file_header_style))
        elements.append(Paragraph(f"<i>Path: {relative_path}</i>", styles['Italic']))
        elements.append(Spacer(1, 0.15*inch))

        # Get appropriate lexer for this file
        lexer = get_lexer_for_file(file_path)

        # Read and add file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Process each line with syntax highlighting
            for line_num, line in enumerate(lines, 1):
                # Remove trailing newline for processing
                line_content = line.rstrip('\n')

                # Apply syntax highlighting
                highlighted_line = syntax_highlight_line(line_content, line_num, lexer)

                # Add as paragraph (automatically handles page breaks)
                elements.append(Paragraph(highlighted_line, code_style))

        except Exception as e:
            elements.append(Paragraph(f"Error reading file: {str(e)}", styles['Normal']))

        # Add page break after each file (except the last one)
        if i < len(files):
            elements.append(PageBreak())

    # Build PDF
    print(f"\nGenerating PDF: {output_filename}")
    doc.build(elements)
    print(f"PDF created successfully: {output_filename}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert code projects to PDF')
    parser.add_argument('path', nargs='?', default=None, help='Path to the project directory')
    parser.add_argument('-o', '--output', default='code_submission.pdf', help='Output PDF filename')

    args = parser.parse_args()

    create_pdf(base_path=args.path, output_filename=args.output)
