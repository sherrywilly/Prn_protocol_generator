import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

from .models import Resident, PRNProtocol
from .forms import ResidentForm, PRNProtocolForm
from .ai_helper import get_ai_protocol_suggestions
from .pdf_generator import generate_protocol_docx, generate_protocol_pdf


DEFAULT_MEDICATION_SUGGESTIONS = [
    'Paracetamol',
    'Ibuprofen',
    'Loperamide',
    'Lactulose',
    'Senna',
    'Bisacodyl',
    'Gaviscon',
    'Cetirizine',
    'Loratadine',
    'Chlorphenamine',
    'Salbutamol',
    'Hydrocortisone cream',
    'Emollient cream',
    'Throat lozenges',
]


def get_medicine_name_suggestions():
    protocol_names = PRNProtocol.objects.order_by().values_list('medicine_name', flat=True).distinct()
    suggestions = {name.strip() for name in protocol_names if name and name.strip()}
    suggestions.update(DEFAULT_MEDICATION_SUGGESTIONS)
    return sorted(suggestions, key=str.lower)


def get_medication_instruction_suggestions():
    raw_instructions = PRNProtocol.objects.order_by().values_list('medication_instruction', flat=True).distinct()
    suggestions = set()
    for instruction in raw_instructions:
        if not instruction:
            continue
        for line in instruction.splitlines():
            cleaned = line.strip()
            if cleaned:
                suggestions.add(cleaned)
    return sorted(suggestions, key=str.lower)


def build_protocol_form_context(resident, title, form, protocol=None):
    context = {
        'form': form,
        'resident': resident,
        'title': title,
        'medicine_suggestions': get_medicine_name_suggestions(),
        'medication_instruction_suggestions': get_medication_instruction_suggestions(),
    }
    if protocol is not None:
        context['protocol'] = protocol
    return context


# Resident Views

def resident_list(request):
    residents = Resident.objects.all()
    return render(request, 'core/resident_list.html', {'residents': residents})


def resident_create(request):
    if request.method == 'POST':
        form = ResidentForm(request.POST)
        if form.is_valid():
            resident = form.save()
            messages.success(request, f'Resident {resident.name} added successfully.')
            return redirect('resident_detail', pk=resident.pk)
    else:
        form = ResidentForm()
    return render(request, 'core/resident_form.html', {'form': form, 'title': 'Add Resident'})


def resident_detail(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    protocols = resident.protocols.all()
    return render(request, 'core/resident_detail.html', {'resident': resident, 'protocols': protocols})


def resident_profile(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    protocols = resident.protocols.all().order_by('-created_at')

    # Summary stats
    total_protocols = protocols.count()
    unique_medicines = protocols.values_list('medicine_name', flat=True).distinct().count()

    context = {
        'resident': resident,
        'protocols': protocols,
        'total_protocols': total_protocols,
        'unique_medicines': unique_medicines,
    }

    return render(request, 'core/resident_profile.html', context)


def resident_edit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        form = ResidentForm(request.POST, instance=resident)
        if form.is_valid():
            form.save()
            messages.success(request, f'Resident {resident.name} updated successfully.')
            return redirect('resident_detail', pk=resident.pk)
    else:
        form = ResidentForm(instance=resident)
    return render(request, 'core/resident_form.html', {'form': form, 'title': 'Edit Resident', 'resident': resident})


def resident_delete(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        name = resident.name
        resident.delete()
        messages.success(request, f'Resident {name} deleted.')
        return redirect('resident_list')
    return render(request, 'core/resident_confirm_delete.html', {'object': resident, 'type': 'Resident'})


# Protocol Views

def protocol_list(request, resident_pk):
    resident = get_object_or_404(Resident, pk=resident_pk)
    protocols = resident.protocols.all()
    return render(request, 'core/protocol_list.html', {'resident': resident, 'protocols': protocols})


def protocol_create(request, resident_pk):
    resident = get_object_or_404(Resident, pk=resident_pk)
    if request.method == 'POST':
        form = PRNProtocolForm(request.POST)
        if form.is_valid():
            protocol = form.save(commit=False)
            protocol.resident = resident
            protocol.save()
            messages.success(request, f'Protocol for {protocol.medicine_name} created.')
            return redirect('protocol_detail', pk=protocol.pk)
    else:
        form = PRNProtocolForm()
    return render(request, 'core/protocol_form.html', build_protocol_form_context(
        resident,
        'Add PRN Protocol',
        form,
    ))


def protocol_detail(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    return render(request, 'core/protocol_detail.html', {'protocol': protocol})


def protocol_edit(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    if request.method == 'POST':
        form = PRNProtocolForm(request.POST, instance=protocol)
        if form.is_valid():
            form.save()
            messages.success(request, f'Protocol for {protocol.medicine_name} updated.')
            return redirect('protocol_detail', pk=protocol.pk)
    else:
        form = PRNProtocolForm(instance=protocol)
    return render(request, 'core/protocol_form.html', build_protocol_form_context(
        protocol.resident,
        'Edit PRN Protocol',
        form,
        protocol=protocol,
    ))


def protocol_delete(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    resident = protocol.resident
    if request.method == 'POST':
        medicine = protocol.medicine_name
        protocol.delete()
        messages.success(request, f'Protocol for {medicine} deleted.')
        return redirect('resident_detail', pk=resident.pk)
    return render(request, 'core/resident_confirm_delete.html', {
        'object': protocol,
        'type': 'Protocol',
        'back_url': f'/residents/{resident.pk}/',
    })


def protocol_pdf(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    return generate_protocol_pdf(protocol)


def protocol_docx(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    return generate_protocol_docx(protocol)


@require_GET
def protocol_autofill_by_medicine(request):
    medicine_name = request.GET.get('medicine_name', '').strip()
    if not medicine_name:
        return JsonResponse({'error': 'medicine_name is required'}, status=400)

    latest_protocol = (
        PRNProtocol.objects
        .filter(medicine_name__iexact=medicine_name)
        .order_by('-created_at')
        .first()
    )

    if latest_protocol is None:
        return JsonResponse({'found': False, 'data': {}})

    return JsonResponse(
        {
            'found': True,
            'data': {
                'form': latest_protocol.form,
                'strength': latest_protocol.strength,
                'route_of_administration': latest_protocol.route_of_administration,
                'dose_and_frequency': latest_protocol.dose_and_frequency,
                'min_time_interval': latest_protocol.min_time_interval,
                'max_dose_24h': latest_protocol.max_dose_24h,
                'medication_instruction': latest_protocol.medication_instruction,
            },
        }
    )


# AI Assist endpoint

@require_POST
def ai_suggest(request):
    try:
        data = json.loads(request.body)
        medicine_name = data.get('medicine_name', '').strip()
        form = data.get('form', '').strip()
        route_of_administration = data.get('route_of_administration', '').strip()
        resident_first_name = data.get('resident_first_name', '').strip()
        resident_mental_capacity = data.get('resident_mental_capacity', '').strip()
        resident_medical_conditions = data.get('resident_medical_conditions', '').strip()
        medication_instruction = data.get('medication_instruction', '').strip()
        if not medicine_name:
            return JsonResponse({'error': 'medicine_name is required'}, status=400)
        suggestions = get_ai_protocol_suggestions(
            medicine_name,
            form=form,
            route_of_administration=route_of_administration,
            resident_first_name=resident_first_name,
            resident_mental_capacity=resident_mental_capacity,
            resident_medical_conditions=resident_medical_conditions,
            medication_instruction=medication_instruction,
        )
        return JsonResponse(suggestions)
    except Exception:
        logger.exception("Error in ai_suggest endpoint")
        return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)
