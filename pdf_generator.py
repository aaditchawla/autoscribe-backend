from fpdf import FPDF
import io

def create_summary_pdf(summary, translated_summary=None):
    """Create a PDF from the summary and translated summary"""
    pdf = FPDF()
    pdf.add_page()
    
    # Set font for English text
    pdf.set_font('Arial', '', 12)
    
    # Add title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Meeting Summary', ln=True, align='C')
    pdf.ln(10)
    
    # Add original summary
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 10, summary)
    
    # Add translated summary if available
    if translated_summary:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Translated Summary', ln=True, align='C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, translated_summary)
    
    # Return the PDF bytes directly without additional encoding
    return pdf.output(dest='S') 