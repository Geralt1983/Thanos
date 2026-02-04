#!/usr/bin/env python3
"""
EML to PDF Converter

Converts .eml files to PDFs with basic formatting.
"""

import os
import email
from email import policy
from email.parser import BytesParser
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def convert_eml_to_pdf(eml_path, output_dir=None):
    """
    Convert a single .eml file to PDF
    
    Args:
        eml_path (str): Path to the .eml file
        output_dir (str, optional): Directory to save PDF. 
                                    Defaults to same directory as .eml file
    
    Returns:
        str: Path to the generated PDF file
    """
    # Determine output path
    if output_dir is None:
        output_dir = os.path.dirname(eml_path)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate PDF filename
    pdf_filename = os.path.splitext(os.path.basename(eml_path))[0] + '.pdf'
    pdf_path = os.path.join(output_dir, pdf_filename)
    
    # Parse the .eml file
    with open(eml_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading3'],
        fontSize=10,
        textColor='darkblue'
    )
    
    # Story (content for PDF)
    story = []
    
    # Add header information
    header_info = [
        f"From: {msg.get('From', 'Unknown Sender')}",
        f"To: {msg.get('To', 'Unknown Recipient')}",
        f"Date: {msg.get('Date', 'Unknown Date')}",
        f"Subject: {msg.get('Subject', 'No Subject')}"
    ]
    
    for info in header_info:
        story.append(Paragraph(info, header_style))
    
    story.append(Spacer(1, 12))
    
    # Extract body text
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                try:
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8')
        except Exception:
            body = str(msg.get_payload())
    
    # Add body text
    body_style = styles['Normal']
    body_paragraphs = body.split('\n')
    for para in body_paragraphs:
        story.append(Paragraph(para, body_style))
    
    # Build PDF
    doc.build(story)
    
    return pdf_path

def convert_folder(input_folder, output_folder=None):
    """
    Convert all .eml files in a folder to PDFs
    
    Args:
        input_folder (str): Path to folder containing .eml files
        output_folder (str, optional): Path to save PDFs. 
                                       Defaults to same as input folder
    
    Returns:
        list: Paths of generated PDF files
    """
    if output_folder is None:
        output_folder = input_folder
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Find .eml files
    eml_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.eml')]
    
    # Convert each .eml file
    pdf_files = []
    for eml_file in eml_files:
        eml_path = os.path.join(input_folder, eml_file)
        pdf_path = convert_eml_to_pdf(eml_path, output_folder)
        pdf_files.append(pdf_path)
        print(f"Converted {eml_file} to PDF")
    
    return pdf_files

def main():
    import sys
    
    # Validate arguments
    if len(sys.argv) < 2:
        print("Usage: python eml_to_pdf_converter.py <input_folder> [output_folder]")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Convert folder
    converted_files = convert_folder(input_folder, output_folder)
    
    # Print results
    print(f"Converted {len(converted_files)} .eml files to PDFs:")
    for pdf in converted_files:
        print(f" - {pdf}")

if __name__ == '__main__':
    main()