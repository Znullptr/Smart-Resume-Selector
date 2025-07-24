from fpdf import FPDF
from unidecode import unidecode

RESULTS_DIR = 'results'

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Top Matching Resumes - AI Report", ln=True, align="C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, unidecode(title), ln=True)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 5, unidecode(body)) 
        self.ln()

    def add_resume(self, filename, score, content):
        self.add_page()
        title = f"{filename} - Score: {score}/10"
        self.chapter_title(title)
        self.chapter_body(content)

def generate_pdf_report(resumes, output_path="ranked_resumes.pdf"):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for res in resumes:
        pdf.add_resume(res['filename'], res['score'], res['full_content'])

    pdf.output(output_path)
    return output_path

