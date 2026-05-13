from io import BytesIO

from django.http import HttpResponse
from django.template.loader import render_to_string

try:
    from docx import Document
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
except ImportError:
    Document = None


def _build_export_filename(protocol, extension):
    safe_resident = protocol.resident.name.replace(' ', '_')
    safe_medicine = protocol.medicine_name.replace(' ', '_')
    return f"PRN_Protocol_{safe_resident}_{safe_medicine}.{extension}"


def _format_date(value):
    return value.strftime('%d/%m/%Y') if value else '—'


def _set_cell_border(cell, color='999999', size='8'):
    cell_properties = cell._tc.get_or_add_tcPr()
    borders = cell_properties.first_child_found_in('w:tcBorders')
    if borders is None:
        borders = OxmlElement('w:tcBorders')
        cell_properties.append(borders)

    for edge_name in ('top', 'left', 'bottom', 'right'):
        edge = borders.find(qn(f'w:{edge_name}'))
        if edge is None:
            edge = OxmlElement(f'w:{edge_name}')
            borders.append(edge)
        edge.set(qn('w:val'), 'single')
        edge.set(qn('w:sz'), size)
        edge.set(qn('w:color'), color)


def _set_cell_shading(cell, fill):
    cell_properties = cell._tc.get_or_add_tcPr()
    shading = cell_properties.first_child_found_in('w:shd')
    if shading is None:
        shading = OxmlElement('w:shd')
        cell_properties.append(shading)
    shading.set(qn('w:fill'), fill)


def _set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    cell_properties = cell._tc.get_or_add_tcPr()
    margins = cell_properties.first_child_found_in('w:tcMar')
    if margins is None:
        margins = OxmlElement('w:tcMar')
        cell_properties.append(margins)

    for side, value in (('top', top), ('start', start), ('bottom', bottom), ('end', end)):
        margin = margins.find(qn(f'w:{side}'))
        if margin is None:
            margin = OxmlElement(f'w:{side}')
            margins.append(margin)
        margin.set(qn('w:w'), str(value))
        margin.set(qn('w:type'), 'dxa')


def _clear_cell(cell):
    cell.text = ''


def _set_paragraph_spacing(paragraph, before=0, after=0, line=1.0, alignment=None):
    paragraph_format = paragraph.paragraph_format
    paragraph_format.space_before = Pt(before)
    paragraph_format.space_after = Pt(after)
    paragraph_format.line_spacing = line
    if alignment is not None:
        paragraph.alignment = alignment


def _add_paragraph_bottom_border(paragraph, color='000000', size='12'):
    paragraph_properties = paragraph._p.get_or_add_pPr()
    borders = paragraph_properties.first_child_found_in('w:pBdr')
    if borders is None:
        borders = OxmlElement('w:pBdr')
        paragraph_properties.append(borders)
    bottom = borders.find(qn('w:bottom'))
    if bottom is None:
        bottom = OxmlElement('w:bottom')
        borders.append(bottom)
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), size)
    bottom.set(qn('w:color'), color)


def _set_document_defaults(document):
    section = document.sections[0]
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)

    normal_style = document.styles['Normal']
    normal_style.font.name = 'Arial'
    normal_style._element.rPr.rFonts.set(qn('w:ascii'), 'Arial')
    normal_style._element.rPr.rFonts.set(qn('w:hAnsi'), 'Arial')
    normal_style.font.size = Pt(10)
    normal_style.paragraph_format.space_before = Pt(0)
    normal_style.paragraph_format.space_after = Pt(0)


def _add_title(document):
    paragraph = document.add_paragraph()
    _set_paragraph_spacing(paragraph, after=10, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    _add_paragraph_bottom_border(paragraph)
    run = paragraph.add_run('PRN PROTOCOL')
    run.bold = True
    run.font.name = 'Arial'
    run.font.size = Pt(16)


def _set_table_layout(table):
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False

    table_properties = table._tbl.tblPr
    table_indent = table_properties.first_child_found_in('w:tblInd')
    if table_indent is None:
        table_indent = OxmlElement('w:tblInd')
        table_properties.append(table_indent)
    table_indent.set(qn('w:w'), '0')
    table_indent.set(qn('w:type'), 'dxa')

    cell_spacing = table_properties.first_child_found_in('w:tblCellSpacing')
    if cell_spacing is None:
        cell_spacing = OxmlElement('w:tblCellSpacing')
        table_properties.append(cell_spacing)
    cell_spacing.set(qn('w:w'), '0')
    cell_spacing.set(qn('w:type'), 'dxa')


def _set_row_height(row, height_cm, exact=False):
    row.height = Cm(height_cm)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY if exact else WD_ROW_HEIGHT_RULE.AT_LEAST


def _write_field_cell(cell, label, value):
    _clear_cell(cell)
    _set_cell_border(cell)
    _set_cell_margins(cell)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP

    paragraph = cell.paragraphs[0]
    _set_paragraph_spacing(paragraph)

    label_run = paragraph.add_run(label)
    label_run.bold = True
    label_run.font.name = 'Arial'
    label_run.font.size = Pt(8)
    label_run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    paragraph.add_run('\n')

    lines = str(value or '—').splitlines() or ['—']
    for index, line in enumerate(lines):
        value_run = paragraph.add_run(line or ' ')
        value_run.font.name = 'Arial'
        value_run.font.size = Pt(10)
        if index < len(lines) - 1:
            paragraph.add_run('\n')


def _add_field_row(document, fields, total_width_cm=17, row_height_cm=1.0):
    table = document.add_table(rows=1, cols=len(fields))
    _set_table_layout(table)
    row = table.rows[0]
    _set_row_height(row, row_height_cm, exact=False)
    total_ratio = sum(field['ratio'] for field in fields)

    for index, field in enumerate(fields):
        width = Cm(total_width_cm * field['ratio'] / total_ratio)
        row.cells[index].width = width
        _write_field_cell(row.cells[index], field['label'], field['value'])

    spacer = document.add_paragraph()
    _set_paragraph_spacing(spacer, after=1)
    return table


def _add_section_box(document, heading, content_lines=None, bullets=False, min_height_cm=1.5):
    heading_paragraph = document.add_paragraph()
    _set_paragraph_spacing(heading_paragraph, before=3, after=3)
    heading_run = heading_paragraph.add_run(heading)
    heading_run.bold = True
    heading_run.font.name = 'Arial'
    heading_run.font.size = Pt(9)
    heading_run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    table = document.add_table(rows=1, cols=1)
    _set_table_layout(table)
    _set_row_height(table.rows[0], min_height_cm, exact=False)
    cell = table.cell(0, 0)
    _clear_cell(cell)
    _set_cell_border(cell)
    _set_cell_margins(cell, top=120, start=120, bottom=120, end=120)

    content_lines = content_lines or ['']
    if bullets:
        first_paragraph = cell.paragraphs[0]
        for index, item in enumerate(content_lines):
            paragraph = first_paragraph if index == 0 else cell.add_paragraph()
            paragraph.style = 'List Bullet'
            _set_paragraph_spacing(paragraph)
            paragraph.add_run(item)
    else:
        first_paragraph = cell.paragraphs[0]
        _set_paragraph_spacing(first_paragraph)
        for index, line in enumerate(content_lines):
            if index == 0:
                paragraph = first_paragraph
            else:
                paragraph = cell.add_paragraph()
                _set_paragraph_spacing(paragraph)
            paragraph.add_run(line or ' ')

    spacer = document.add_paragraph()
    _set_paragraph_spacing(spacer, after=1)
    return table


def _checkbox(value):
    return '☒' if value else '☐'


def _add_gp_section(document, protocol):
    table = document.add_table(rows=1, cols=1)
    _set_table_layout(table)
    _set_row_height(table.rows[0], 2.0, exact=False)
    cell = table.cell(0, 0)
    _clear_cell(cell)
    _set_cell_border(cell)
    _set_cell_margins(cell, top=120, start=120, bottom=120, end=120)

    title = cell.paragraphs[0]
    _set_paragraph_spacing(title, after=4)
    title_run = title.add_run('Circumstance of reporting to GP (Tick as appropriate)')
    title_run.bold = True
    title_run.font.name = 'Arial'
    title_run.font.size = Pt(9.5)

    gp_rows = [
        f"{_checkbox(protocol.gp_persistent_need)} Persistent need for upper level of dosage",
        f"{_checkbox(protocol.gp_never_requesting)} Never requesting dosage",
        f"{_checkbox(protocol.gp_requesting_too_often)} Requesting too often",
        f"{_checkbox(protocol.gp_side_effects)} Side effects experienced",
        f"☐ Other (please state): {protocol.gp_other or '___________'}",
    ]
    for item in gp_rows:
        paragraph = cell.add_paragraph()
        _set_paragraph_spacing(paragraph, after=1)
        run = paragraph.add_run(item)
        run.font.name = 'Arial'
        run.font.size = Pt(10)

    return table


def _write_table_cell(cell, text, bold=False, fill=None):
    _clear_cell(cell)
    _set_cell_border(cell)
    _set_cell_margins(cell)
    if fill:
        _set_cell_shading(cell, fill)
    paragraph = cell.paragraphs[0]
    _set_paragraph_spacing(paragraph)
    run = paragraph.add_run(text or '')
    run.bold = bold
    run.font.name = 'Arial'
    run.font.size = Pt(9.5)


def _add_signature_table(document, protocol, total_width_cm=17):
    table = document.add_table(rows=7, cols=4)
    _set_table_layout(table)
    widths = [Cm(total_width_cm * ratio) for ratio in (0.2, 0.3, 0.3, 0.2)]

    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = width

    _set_row_height(table.rows[0], 0.7, exact=True)
    _set_row_height(table.rows[1], 0.85)
    _set_row_height(table.rows[2], 0.85)
    _set_row_height(table.rows[3], 0.75)
    _set_row_height(table.rows[4], 0.85)
    _set_row_height(table.rows[5], 0.85)
    _set_row_height(table.rows[6], 0.75)

    header_cells = table.rows[0].cells
    _write_table_cell(header_cells[0], '', bold=True, fill='E0E0E0')
    _write_table_cell(header_cells[1], 'Name & Signature', bold=True, fill='E0E0E0')
    _write_table_cell(header_cells[2], 'Designation', bold=True, fill='E0E0E0')
    _write_table_cell(header_cells[3], 'Date', bold=True, fill='E0E0E0')

    _write_table_cell(table.rows[1].cells[0], 'Prepared by', bold=True)
    _write_table_cell(table.rows[1].cells[1], protocol.prepared_by_name)
    _write_table_cell(table.rows[1].cells[2], protocol.prepared_by_designation)
    _write_table_cell(table.rows[1].cells[3], _format_date(protocol.prepared_by_date) if protocol.prepared_by_date else '')

    _write_table_cell(table.rows[2].cells[0], 'Approved by', bold=True)
    _write_table_cell(table.rows[2].cells[1], protocol.approved_by_name)
    _write_table_cell(table.rows[2].cells[2], protocol.approved_by_designation)
    _write_table_cell(table.rows[2].cells[3], _format_date(protocol.approved_by_date) if protocol.approved_by_date else '')

    _write_table_cell(table.rows[3].cells[0], 'Review date:', bold=True)
    merged_review = table.rows[3].cells[1].merge(table.rows[3].cells[3])
    _write_table_cell(merged_review, _format_date(protocol.review_date) if protocol.review_date else '')

    _write_table_cell(table.rows[4].cells[0], 'Reviewed by', bold=True)
    _write_table_cell(table.rows[4].cells[1], protocol.reviewed_by_name)
    _write_table_cell(table.rows[4].cells[2], protocol.reviewed_by_designation)
    _write_table_cell(table.rows[4].cells[3], _format_date(protocol.reviewed_by_date) if protocol.reviewed_by_date else '')

    _write_table_cell(table.rows[5].cells[0], 'Checked by', bold=True)
    _write_table_cell(table.rows[5].cells[1], protocol.checked_by_name)
    _write_table_cell(table.rows[5].cells[2], protocol.checked_by_designation)
    _write_table_cell(table.rows[5].cells[3], _format_date(protocol.checked_by_date) if protocol.checked_by_date else '')

    _write_table_cell(table.rows[6].cells[0], 'New review date:', bold=True)
    merged_new_review = table.rows[6].cells[1].merge(table.rows[6].cells[3])
    _write_table_cell(merged_new_review, _format_date(protocol.new_review_date) if protocol.new_review_date else '')

    return table
def generate_protocol_pdf(protocol):
    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse("WeasyPrint is not installed. Cannot generate PDF.", status=500)

    html_string = render_to_string('core/protocol_pdf.html', {'protocol': protocol})
    html = HTML(string=html_string, base_url='/')
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    filename = _build_export_filename(protocol, 'pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_protocol_docx(protocol):
    if Document is None:
        return HttpResponse("python-docx is not installed. Cannot generate DOCX.", status=500)

    document = Document()
    _set_document_defaults(document)
    _add_title(document)

    _add_field_row(
        document,
        [
            {'label': "Resident's Name", 'value': protocol.resident.name, 'ratio': 2},
            {'label': 'Room No.', 'value': protocol.resident.room_number, 'ratio': 1},
            {'label': 'Date of Birth', 'value': _format_date(protocol.resident.date_of_birth), 'ratio': 1},
        ],
        row_height_cm=1.05,
    )
    _add_field_row(
        document,
        [
            {'label': 'Name of Medicine', 'value': protocol.medicine_name, 'ratio': 2},
            {'label': 'Form', 'value': protocol.form, 'ratio': 1},
        ],
        row_height_cm=1.0,
    )
    _add_field_row(
        document,
        [
            {'label': 'Strength', 'value': protocol.strength, 'ratio': 1},
            {'label': 'Route of Administration', 'value': protocol.route_of_administration, 'ratio': 1},
        ],
        row_height_cm=1.0,
    )
    _add_field_row(
        document,
        [
            {'label': 'Dose and Frequency', 'value': protocol.dose_and_frequency, 'ratio': 2},
            {'label': 'Minimum Time Interval Between Doses', 'value': protocol.min_time_interval, 'ratio': 1.5},
        ],
        row_height_cm=1.15,
    )
    _add_field_row(
        document,
        [
            {'label': 'Maximum Dose in 24 Hours', 'value': protocol.max_dose_24h, 'ratio': 1},
        ],
        row_height_cm=0.95,
    )

    _add_section_box(
        document,
        'Does the resident request medication / require prompting / require observing for symptoms:',
        protocol.capacity_statement.splitlines() or [''],
        min_height_cm=1.6,
    )
    _add_section_box(
        document,
        'Reason for medication administration - describe in as much detail as possible the condition being treated i.e. signs and symptoms, behaviours, type of pain - where and when, expected outcome. For creams indicate where it should be applied. If the dose is variable, describe the circumstances under which each dose is to be given.',
        protocol.reason_for_administration.splitlines() or [''],
        min_height_cm=2.5,
    )
    _add_section_box(
        document,
        'Special Instructions (e.g. specific administration instructions)',
        protocol.get_special_instructions_list() or [''],
        bullets=bool(protocol.get_special_instructions_list()),
        min_height_cm=1.5,
    )
    _add_section_box(
        document,
        'Additional information (e.g. side effects to look out for; what to do if requesting more frequently than prescribed or not requiring medication at all)',
        protocol.get_additional_information_list() or [''],
        bullets=bool(protocol.get_additional_information_list()),
        min_height_cm=1.7,
    )
    _add_gp_section(document, protocol)
    _add_signature_table(document, protocol)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    filename = _build_export_filename(protocol, 'docx')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _build_resident_export_filename(resident, extension):
    safe_resident = resident.name.replace(' ', '_')
    return f"MAR_Resident_Profile_{safe_resident}.{extension}"



def _split_lines(value):
    return [line.strip() for line in str(value or '').splitlines() if line.strip()] or ['—']



def generate_resident_pdf(resident):
    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse('WeasyPrint is not installed. Cannot generate PDF.', status=500)

    html_string = render_to_string('core/resident_pdf.html', {'resident': resident, 'care_home_name': 'Welshwood Manor'})
    html = HTML(string=html_string, base_url='/')
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{_build_resident_export_filename(resident, "pdf")}"'
    return response



def generate_resident_docx(resident):
    if Document is None:
        return HttpResponse('python-docx is not installed. Cannot generate DOCX.', status=500)

    document = Document()
    _set_document_defaults(document)

    heading = document.add_paragraph()
    _set_paragraph_spacing(heading, after=10, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    _add_paragraph_bottom_border(heading)
    run = heading.add_run('MAR RESIDENT PROFILE')
    run.bold = True
    run.font.name = 'Arial'
    run.font.size = Pt(16)

    _add_field_row(
        document,
        [
            {'label': "Resident's Name", 'value': resident.name, 'ratio': 2},
            {'label': 'Room No.', 'value': resident.room_number, 'ratio': 1},
            {'label': 'Date of Birth', 'value': _format_date(resident.date_of_birth), 'ratio': 1},
        ],
        row_height_cm=1.05,
    )
    _add_field_row(
        document,
        [
            {'label': 'NHS Number', 'value': resident.nhs_number or '—', 'ratio': 1},
            {'label': 'Review status', 'value': resident.get_review_status_display(), 'ratio': 1},
            {'label': 'Care plan reviewed', 'value': _format_date(resident.care_plan_reviewed), 'ratio': 1},
        ],
        row_height_cm=1.0,
    )
    _add_field_row(
        document,
        [
            {'label': 'GP', 'value': resident.gp_name or '—', 'ratio': 1},
            {'label': 'Pharmacy', 'value': resident.pharmacy_name or '—', 'ratio': 1},
            {'label': 'Emergency contact', 'value': resident.emergency_contact_name or '—', 'ratio': 1},
        ],
        row_height_cm=1.0,
    )

    _add_section_box(document, 'Mental capacity', _split_lines(resident.mental_capacity), min_height_cm=1.5)
    _add_section_box(document, 'Medical conditions', _split_lines(resident.medical_conditions), min_height_cm=1.8)
    _add_section_box(document, 'Allergies', resident.get_allergies_list() or ['—'], bullets=bool(resident.get_allergies_list()), min_height_cm=1.5)
    _add_section_box(document, 'Medication alerts', resident.get_medication_alerts_list() or ['—'], bullets=bool(resident.get_medication_alerts_list()), min_height_cm=1.5)
    _add_section_box(document, 'Monitoring requirements', resident.get_monitoring_requirements_list() or ['—'], bullets=bool(resident.get_monitoring_requirements_list()), min_height_cm=1.7)
    _add_section_box(document, 'Administration preferences', resident.get_administration_preferences_list() or ['—'], bullets=bool(resident.get_administration_preferences_list()), min_height_cm=1.7)
    _add_section_box(document, 'Legal / safeguarding information', resident.get_legal_safeguarding_information_list() or ['—'], bullets=bool(resident.get_legal_safeguarding_information_list()), min_height_cm=1.7)
    _add_section_box(document, 'Care summary', _split_lines(resident.care_summary), min_height_cm=1.8)
    _add_section_box(document, 'MAR front-page text', _split_lines(resident.mar_front_page_text), min_height_cm=2.2)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    response['Content-Disposition'] = f'attachment; filename="{_build_resident_export_filename(resident, "docx")}"'
    return response
