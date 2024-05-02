from weasyprint import HTML

def html_to_pdf(html_content, output_path):
    HTML(filename=html_content).write_pdf(output_path)

# Example HTML content
# html_content = open("./ticket/ticket.html").read()
# print(html_content)

# Convert HTML to PDF
html_to_pdf("./ticket/ticket.html", "./output_weasyprint.pdf")