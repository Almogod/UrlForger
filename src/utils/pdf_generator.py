from fpdf import FPDF
import datetime
import os

class SEOReportPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(16, 185, 129) # Primary Theme Color
        self.cell(0, 10, 'Sitemap Fixer - SEO Suggestion Report', ln=True, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', align='C')

def generate_seo_pdf(report, output_path):
    pdf = SEOReportPDF()
    pdf.add_page()
    
    # Summary
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'Analysis Overview', ln=True)
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 8, f'Site URL: {report.get("site_url")}', ln=True)
    pdf.cell(0, 8, f'Initial SEO Score: {report.get("seo_score_before", "N/A")}', ln=True)
    pdf.ln(5)

    # Suggested Actions
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'Suggested SEO Fixes', ln=True)
    pdf.ln(2)
    
    actions = report.get("suggested_actions", [])
    if not actions:
        pdf.set_font('helvetica', 'I', 11)
        pdf.cell(0, 8, 'No manual fixes suggested.', ln=True)
    else:
        for idx, action in enumerate(actions, 1):
            pdf.set_font('helvetica', 'B', 11)
            pdf.cell(0, 8, f'{idx}. {action.get("type", "General")}', ln=True)
            pdf.set_font('helvetica', '', 10)
            pdf.multi_cell(0, 6, f'Page: {action.get("url")}')
            pdf.multi_cell(0, 6, f'Description: {action.get("description", action.get("tag", "Apply SEO optimization"))}')
            pdf.ln(2)

    # Generated Pages
    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 16)
    pdf.cell(0, 10, 'AI-Generated Content Briefs', ln=True)
    
    pages = report.get("pages_generated", [])
    if not pages:
        pdf.set_font('helvetica', 'I', 11)
        pdf.cell(0, 8, 'No new pages suggested.', ln=True)
    else:
        for pg in pages:
            pdf.set_font('helvetica', 'B', 11)
            pdf.cell(0, 8, f"Keyword: {pg['keyword']}", ln=True)
            pdf.set_font('helvetica', '', 10)
            pdf.cell(0, 6, f"Title: {pg['title']}", ln=True)
            pdf.cell(0, 6, f"Target Slug: /{pg['slug']}", ln=True)
            pdf.ln(2)

    pdf.output(output_path)
    return output_path
