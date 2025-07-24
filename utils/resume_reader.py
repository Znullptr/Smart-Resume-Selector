import os
import fitz  # PyMuPDF
import docx
from pathlib import Path

def extract_resume_texts(filepaths, progress_callback=None):
    """
    Extract text from resume files with optional progress tracking
    
    Args:
        filepaths: List of file paths to process
        progress_callback: Optional callback function to report progress
    
    Returns:
        List of dictionaries containing filename and extracted text
    """
    resume_texts = []
    total_files = len(filepaths)
    
    for i, filepath in enumerate(filepaths):
        filename = os.path.basename(filepath)
        
        # Report progress if callback provided
        if progress_callback:
            progress_callback(i, total_files, f"Processing {filename}")
        
        try:
            # Extract text based on file extension
            text = extract_text_from_file(filepath)
            resume_texts.append({
                'filename': filename,
                'text': text,
                'filepath': filepath
            })
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            resume_texts.append({
                'filename': filename,
                'text': '',
                'filepath': filepath,
                'error': str(e)
            })
    
    return resume_texts

def extract_text_from_file(filepath):
    """Extract text from a single file based on its extension"""
    file_extension = Path(filepath).suffix.lower()
    
    if file_extension == '.pdf':
        return extract_text_from_pdf(filepath)
    elif file_extension in ['.doc', '.docx']:
        return extract_text_from_docx(filepath)
    elif file_extension == '.txt':
        return extract_text_from_txt(filepath)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

def extract_text_from_pdf(filepath):
    """Extract text from PDF file using PyMuPDF (fitz)"""
    text = ""
    try:
        # Open the PDF document
        doc = fitz.open(filepath)
        
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n"
        
        # Close the document
        doc.close()
        
    except Exception as e:
        raise Exception(f"Error reading PDF: {e}")
    
    return text.strip()

def extract_text_from_docx(filepath):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(filepath)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading DOCX: {e}")

def extract_text_from_txt(filepath):
    """Extract text from TXT file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        try:
            with open(filepath, 'r', encoding='latin-1') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Error reading TXT file: {e}")
    except Exception as e:
        raise Exception(f"Error reading TXT file: {e}")

# Legacy function for backward compatibility
def extract_resume_texts_legacy(filepaths):
    """Legacy function without progress tracking"""
    return extract_resume_texts(filepaths)