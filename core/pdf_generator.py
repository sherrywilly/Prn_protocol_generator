from django.template.loader import render_to_string
from django.http import HttpResponse


def generate_protocol_pdf(protocol):
    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse("WeasyPrint is not installed. Cannot generate PDF.", status=500)

    html_string = render_to_string('core/protocol_pdf.html', {'protocol': protocol})
    html = HTML(string=html_string, base_url='/')
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    safe_resident = protocol.resident.name.replace(' ', '_')
    safe_medicine = protocol.medicine_name.replace(' ', '_')
    filename = f"PRN_Protocol_{safe_resident}_{safe_medicine}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
