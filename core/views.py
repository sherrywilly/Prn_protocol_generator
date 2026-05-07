import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

from .models import Resident, PRNProtocol
from .forms import ResidentForm, PRNProtocolForm
from .ai_helper import get_ai_protocol_suggestions
from .pdf_generator import generate_protocol_pdf


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
    return render(request, 'core/protocol_form.html', {
        'form': form,
        'resident': resident,
        'title': 'Add PRN Protocol',
    })


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
    return render(request, 'core/protocol_form.html', {
        'form': form,
        'resident': protocol.resident,
        'title': 'Edit PRN Protocol',
        'protocol': protocol,
    })


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


# AI Assist endpoint

@require_POST
def ai_suggest(request):
    try:
        data = json.loads(request.body)
        medicine_name = data.get('medicine_name', '').strip()
        resident_name = data.get('resident_name', 'the resident').strip()
        if not medicine_name:
            return JsonResponse({'error': 'medicine_name is required'}, status=400)
        suggestions = get_ai_protocol_suggestions(medicine_name, resident_name)
        return JsonResponse(suggestions)
    except Exception:
        logger.exception("Error in ai_suggest endpoint")
        return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)
