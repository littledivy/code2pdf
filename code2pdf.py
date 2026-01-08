#!/usr/bin/env python3

import os
import glob
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, XPreformatted
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor
from pygments import lex
from pygments.lexers import CppLexer
from pygments.token import Token
from datetime import datetime

def get_code_files(base_path):
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

def syntax_highlight_line(line_content, line_num):
    """Apply syntax highlighting to a single line of C++ code."""
    # Color scheme for different token types
    token_colors = {
        Token.Keyword: '#0000FF',           # Blue for keywords
        Token.Keyword.Type: '#0000FF',      # Blue for types
        Token.Comment: '#008000',           # Green for comments
        Token.Comment.Single: '#008000',
        Token.Comment.Multiline: '#008000',
        Token.Comment.Preproc: '#0000FF',   # Blue for preprocessor
        Token.String: '#A31515',            # Red for strings
        Token.String.Char: '#A31515',
        Token.Number: '#098658',            # Teal for numbers
        Token.Name.Class: '#267F99',        # Teal for class names
        Token.Name.Function: '#795E26',     # Brown for functions
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

    lexer = CppLexer()
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

def create_pdf(output_filename='code_submission.pdf'):
    """Create PDF with all code files."""
    base_path = os.path.dirname(os.path.abspath(__file__))

    # Get all files
    files = get_code_files(base_path)

    if not files:
        print("No C++ or header files found!")
        return

    print(f"Found {len(files)} files to include in PDF")

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
    elements.append(Paragraph("Table of Contents", title_style))
    elements.append(Spacer(1, 0.2*inch))

    # Group files by directory
    include_files = []
    src_files = []
    file_index = 1

    for file_path in files:
        filename = os.path.basename(file_path)
        if 'include' in file_path:
            include_files.append((file_index, filename))
        else:
            src_files.append((file_index, filename))
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

    if include_files:
        elements.append(Paragraph("include/", toc_dir_style))
        for i, (idx, filename) in enumerate(include_files):
            prefix = "`--" if i == len(include_files) - 1 else "|--"
            elements.append(Paragraph(f"{prefix} {idx}. {filename}", toc_file_style))
        elements.append(Spacer(1, 0.1*inch))

    if src_files:
        elements.append(Paragraph("src/", toc_dir_style))
        for i, (idx, filename) in enumerate(src_files):
            prefix = "`--" if i == len(src_files) - 1 else "|--"
            elements.append(Paragraph(f"{prefix} {idx}. {filename}", toc_file_style))

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

        # Read and add file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Process each line with syntax highlighting
            for line_num, line in enumerate(lines, 1):
                # Remove trailing newline for processing
                line_content = line.rstrip('\n')

                # Apply syntax highlighting
                highlighted_line = syntax_highlight_line(line_content, line_num)

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
    create_pdf()
