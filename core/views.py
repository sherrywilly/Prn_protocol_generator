import json
import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .ai_helper import get_ai_protocol_suggestions, get_ai_resident_profile_assistance
from .forms import PRNProtocolForm, ResidentForm
from .models import AuditLog, PRNProtocol, Resident
from .pdf_generator import (
    generate_protocol_docx,
    generate_protocol_pdf,
    generate_resident_docx,
    generate_resident_pdf,
)

logger = logging.getLogger(__name__)

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

CARE_HOME_NAME = 'Welshwood Manor'


def role_names_for_user(user):
    if not user.is_authenticated:
        return []
    if user.is_superuser:
        return ['Portal Admin']
    return list(user.groups.order_by('name').values_list('name', flat=True))


def has_portal_access(user):
    return user.is_authenticated and (user.is_superuser or user.groups.exists())


def can_view_portal(user):
    return has_portal_access(user) and (user.is_superuser or user.has_perm('core.view_resident'))


def can_edit_portal(user):
    return has_portal_access(user) and (
        user.is_superuser or user.has_perm('core.add_resident') or user.has_perm('core.change_resident')
    )


def can_review_profiles(user):
    return has_portal_access(user) and (user.is_superuser or user.has_perm('core.change_resident'))


REQUIRED_PROFILE_FIELDS = {
    'medical_conditions': 'Medical conditions',
    'allergies': 'Allergies',
    'medication_alerts': 'Medication alerts',
    'gp_name': 'GP name',
    'pharmacy_name': 'Pharmacy name',
    'emergency_contact_name': 'Emergency contact name',
    'monitoring_requirements': 'Monitoring requirements',
    'administration_preferences': 'Administration preferences',
    'legal_safeguarding_information': 'Legal / safeguarding information',
}


def portal_access_required(check):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                request.session['post_login_next'] = request.get_full_path()
                return redirect('login')
            if not check(request.user):
                raise PermissionDenied('You do not have permission to access this part of the portal.')
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


viewer_required = portal_access_required(can_view_portal)
editor_required = portal_access_required(can_edit_portal)
reviewer_required = portal_access_required(can_review_profiles)




def _safe_next_url(request, fallback):
    candidate = request.GET.get('next') or request.POST.get('next')
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback

def log_audit_event(action, description, user=None, target=None, resident=None, metadata=None):
    resident = resident or getattr(target, 'resident', None) or (target if isinstance(target, Resident) else None)
    entity_type = target.__class__.__name__ if target is not None else 'Session'
    entity_id = str(getattr(target, 'pk', '')) if target is not None else ''
    entity_label = str(target) if target is not None else ''
    AuditLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        resident=resident,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        description=description,
        metadata=metadata or {},
    )


@require_GET
def login_view(request):
    if request.user.is_authenticated:
        return redirect('resident_list')
    form = AuthenticationForm(request)
    return render(request, 'registration/login.html', {'form': form})


@require_POST
def login_submit(request):
    form = AuthenticationForm(request, data=request.POST)
    if form.is_valid():
        user = form.get_user()
        if not has_portal_access(user):
            form.add_error(None, 'Your account does not have a portal role assigned yet.')
        else:
            auth_login(request, user)
            log_audit_event('login', 'User logged into the MAR portal.', user=user)
            fallback = request.session.pop('post_login_next', None) or '/'
            return redirect(_safe_next_url(request, fallback))
    return render(request, 'registration/login.html', {'form': form}, status=400)


@viewer_required
@require_POST
def logout_view(request):
    user = request.user
    log_audit_event('logout', 'User logged out of the MAR portal.', user=user)
    auth_logout(request)
    return redirect('login')


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


def calculate_profile_gaps(data):
    missing = [label for field, label in REQUIRED_PROFILE_FIELDS.items() if not (data.get(field) or '').strip()]
    inconsistencies = []
    allergies = (data.get('allergies') or '').lower()
    medication_alerts = (data.get('medication_alerts') or '').lower()
    medical_conditions = (data.get('medical_conditions') or '').lower()
    monitoring = (data.get('monitoring_requirements') or '').lower()

    allergy_lines = [line.strip() for line in allergies.splitlines() if line.strip()]
    if 'no known allergies' in allergies and len(allergy_lines) > 1:
        inconsistencies.append('Allergy section includes “No known allergies” alongside additional allergy entries.')
    if 'nkda' in medication_alerts and allergy_lines:
        inconsistencies.append('Medication alerts mention NKDA while allergy details are present.')
    if 'diabetes' in medical_conditions and 'blood glucose' not in monitoring and 'blood sugar' not in monitoring:
        inconsistencies.append('Monitoring requirements may be incomplete for diabetes because blood glucose monitoring is not mentioned.')
    if 'warfarin' in medical_conditions and 'bleeding' not in medication_alerts:
        inconsistencies.append('Medication alerts may be incomplete because warfarin-related bleeding precautions are not mentioned.')

    return missing, inconsistencies


def build_dashboard_context(user, residents):
    recent_logs = AuditLog.objects.select_related('user', 'resident')[:8]
    due_reviews = residents.filter(Q(care_plan_reviewed__isnull=True) | Q(care_plan_reviewed__lt=timezone.localdate())).count()
    return {
        'residents': residents,
        'total_residents': residents.count(),
        'reviewed_residents': residents.filter(review_status=Resident.REVIEW_STATUS_REVIEWED).count(),
        'draft_residents': residents.filter(review_status=Resident.REVIEW_STATUS_DRAFT).count(),
        'due_reviews': due_reviews,
        'recent_logs': recent_logs,
        'can_edit': can_edit_portal(user),
        'can_review': can_review_profiles(user),
        'role_names': role_names_for_user(user),
        'care_home_name': CARE_HOME_NAME,
    }


def build_resident_form_context(request, form, title, resident=None):
    current_data = form.initial.copy()
    if request.method == 'POST':
        current_data.update(request.POST.dict())
    elif resident:
        for field in form.fields:
            current_data[field] = getattr(resident, field, '') if hasattr(resident, field) else form.initial.get(field, '')
    missing_information, inconsistencies = calculate_profile_gaps(current_data)
    return {
        'form': form,
        'title': title,
        'resident': resident,
        'missing_information': missing_information,
        'inconsistencies': inconsistencies,
        'required_profile_fields': REQUIRED_PROFILE_FIELDS,
        'care_home_name': CARE_HOME_NAME,
    }


def build_protocol_form_context(resident, title, form, protocol=None):
    context = {
        'form': form,
        'resident': resident,
        'title': title,
        'medicine_suggestions': get_medicine_name_suggestions(),
        'medication_instruction_suggestions': get_medication_instruction_suggestions(),
        'care_home_name': CARE_HOME_NAME,
    }
    if protocol is not None:
        context['protocol'] = protocol
    return context


@viewer_required
def resident_list(request):
    query = request.GET.get('q', '').strip()
    residents = Resident.objects.annotate(protocol_count=Count('protocols')).select_related('reviewed_by')
    if query:
        residents = residents.filter(
            Q(name__icontains=query)
            | Q(room_number__icontains=query)
            | Q(nhs_number__icontains=query)
            | Q(medical_conditions__icontains=query)
        )
    context = build_dashboard_context(request.user, residents)
    context['query'] = query
    return render(request, 'core/resident_list.html', context)


@editor_required
def resident_create(request):
    if request.method == 'POST':
        form = ResidentForm(request.POST, request.FILES)
        if form.is_valid():
            resident = form.save(commit=False)
            resident.review_status = Resident.REVIEW_STATUS_DRAFT
            resident.save()
            log_audit_event('create', f'Resident profile created for {resident.name}.', user=request.user, target=resident)
            messages.success(request, f'Resident profile for {resident.name} added successfully.')
            return redirect('resident_detail', pk=resident.pk)
    else:
        form = ResidentForm()
    return render(request, 'core/resident_form.html', build_resident_form_context(request, form, 'Create MAR resident profile'))


@viewer_required
def resident_detail(request, pk):
    resident = get_object_or_404(Resident.objects.select_related('reviewed_by'), pk=pk)
    protocols = resident.protocols.all()
    missing_information, inconsistencies = calculate_profile_gaps({
        field: getattr(resident, field, '') for field in REQUIRED_PROFILE_FIELDS
    } | {
        'medical_conditions': resident.medical_conditions,
        'allergies': resident.allergies,
        'medication_alerts': resident.medication_alerts,
        'monitoring_requirements': resident.monitoring_requirements,
    })
    context = {
        'resident': resident,
        'protocols': protocols,
        'total_protocols': protocols.count(),
        'unique_medicines': protocols.values_list('medicine_name', flat=True).distinct().count(),
        'missing_information': missing_information,
        'inconsistencies': inconsistencies,
        'audit_logs': resident.audit_logs.select_related('user')[:10],
        'can_edit': can_edit_portal(request.user),
        'can_review': can_review_profiles(request.user),
        'care_home_name': CARE_HOME_NAME,
    }
    return render(request, 'core/resident_detail.html', context)


@viewer_required
def resident_profile(request, pk):
    resident = get_object_or_404(Resident.objects.select_related('reviewed_by'), pk=pk)
    context = {
        'resident': resident,
        'care_home_name': CARE_HOME_NAME,
        'missing_information': calculate_profile_gaps({field: getattr(resident, field, '') for field in REQUIRED_PROFILE_FIELDS})[0],
    }
    return render(request, 'core/resident_profile.html', context)


@editor_required
def resident_edit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        form = ResidentForm(request.POST, request.FILES, instance=resident)
        if form.is_valid():
            resident = form.save(commit=False)
            if resident.review_status == Resident.REVIEW_STATUS_REVIEWED:
                resident.review_status = Resident.REVIEW_STATUS_IN_REVIEW
            resident.reviewed_at = None
            resident.reviewed_by = None
            resident.save()
            log_audit_event(
                'update',
                f'Resident profile updated for {resident.name}.',
                user=request.user,
                target=resident,
                metadata={'changed_fields': form.changed_data},
            )
            messages.success(request, f'Resident profile for {resident.name} updated successfully.')
            return redirect('resident_detail', pk=resident.pk)
    else:
        form = ResidentForm(instance=resident)
    return render(request, 'core/resident_form.html', build_resident_form_context(request, form, 'Edit MAR resident profile', resident=resident))


@editor_required
def resident_delete(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        name = resident.name
        log_audit_event('delete', f'Resident profile deleted for {name}.', user=request.user, target=resident)
        resident.delete()
        messages.success(request, f'Resident profile for {name} deleted.')
        return redirect('resident_list')
    return render(request, 'core/resident_confirm_delete.html', {'object': resident, 'type': 'Resident Profile', 'care_home_name': CARE_HOME_NAME})


@reviewer_required
@require_POST
def resident_mark_reviewed(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    resident.review_status = Resident.REVIEW_STATUS_REVIEWED
    resident.reviewed_at = timezone.now()
    resident.reviewed_by = request.user
    resident.save(update_fields=['review_status', 'reviewed_at', 'reviewed_by', 'updated_at'])
    log_audit_event('review', f'Resident profile reviewed for {resident.name}.', user=request.user, target=resident)
    messages.success(request, f'{resident.name} has been marked as reviewed.')
    return redirect('resident_detail', pk=resident.pk)


@viewer_required
def resident_pdf(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    log_audit_event('export_pdf', f'Exported resident MAR profile PDF for {resident.name}.', user=request.user, target=resident)
    return generate_resident_pdf(resident)


@viewer_required
def resident_docx(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    log_audit_event('export_docx', f'Exported resident MAR profile DOCX for {resident.name}.', user=request.user, target=resident)
    return generate_resident_docx(resident)


@viewer_required
def resident_print(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    log_audit_event('print', f'Opened print-friendly MAR profile for {resident.name}.', user=request.user, target=resident)
    return render(request, 'core/resident_print.html', {'resident': resident, 'care_home_name': CARE_HOME_NAME})


@editor_required
@require_POST
def resident_ai_assist(request):
    try:
        data = json.loads(request.body)
        suggestions = get_ai_resident_profile_assistance(data)
        log_audit_event(
            'ai_assist',
            'Generated AI-assisted resident profile suggestions requiring staff review.',
            user=request.user,
            metadata={'fields_requested': sorted(data.keys())},
        )
        return JsonResponse(suggestions)
    except Exception:
        logger.exception('Error in resident_ai_assist endpoint')
        return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)


@viewer_required
def protocol_list(request, resident_pk):
    resident = get_object_or_404(Resident, pk=resident_pk)
    protocols = resident.protocols.all()
    return render(request, 'core/protocol_list.html', {'resident': resident, 'protocols': protocols, 'care_home_name': CARE_HOME_NAME})


@editor_required
def protocol_create(request, resident_pk):
    resident = get_object_or_404(Resident, pk=resident_pk)
    if request.method == 'POST':
        form = PRNProtocolForm(request.POST)
        if form.is_valid():
            protocol = form.save(commit=False)
            protocol.resident = resident
            protocol.save()
            log_audit_event('create', f'PRN protocol created for {protocol.medicine_name}.', user=request.user, target=protocol)
            messages.success(request, f'Protocol for {protocol.medicine_name} created.')
            return redirect('protocol_detail', pk=protocol.pk)
    else:
        form = PRNProtocolForm()
    return render(request, 'core/protocol_form.html', build_protocol_form_context(resident, 'Add PRN Protocol', form))


@viewer_required
def protocol_detail(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    return render(request, 'core/protocol_detail.html', {'protocol': protocol, 'care_home_name': CARE_HOME_NAME})


@editor_required
def protocol_edit(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    if request.method == 'POST':
        form = PRNProtocolForm(request.POST, instance=protocol)
        if form.is_valid():
            form.save()
            log_audit_event(
                'update',
                f'PRN protocol updated for {protocol.medicine_name}.',
                user=request.user,
                target=protocol,
                metadata={'changed_fields': form.changed_data},
            )
            messages.success(request, f'Protocol for {protocol.medicine_name} updated.')
            return redirect('protocol_detail', pk=protocol.pk)
    else:
        form = PRNProtocolForm(instance=protocol)
    return render(request, 'core/protocol_form.html', build_protocol_form_context(protocol.resident, 'Edit PRN Protocol', form, protocol=protocol))


@editor_required
def protocol_delete(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    resident = protocol.resident
    if request.method == 'POST':
        medicine = protocol.medicine_name
        log_audit_event('delete', f'PRN protocol deleted for {medicine}.', user=request.user, target=protocol)
        protocol.delete()
        messages.success(request, f'Protocol for {medicine} deleted.')
        return redirect('resident_detail', pk=resident.pk)
    return render(request, 'core/resident_confirm_delete.html', {
        'object': protocol,
        'type': 'Protocol',
        'back_url': f'/residents/{resident.pk}/',
        'care_home_name': CARE_HOME_NAME,
    })


@viewer_required
def protocol_pdf(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    log_audit_event('export_pdf', f'Exported PRN protocol PDF for {protocol.medicine_name}.', user=request.user, target=protocol)
    return generate_protocol_pdf(protocol)


@viewer_required
def protocol_docx(request, pk):
    protocol = get_object_or_404(PRNProtocol, pk=pk)
    log_audit_event('export_docx', f'Exported PRN protocol DOCX for {protocol.medicine_name}.', user=request.user, target=protocol)
    return generate_protocol_docx(protocol)


@viewer_required
@require_GET
def protocol_autofill_by_medicine(request):
    medicine_name = request.GET.get('medicine_name', '').strip()
    if not medicine_name:
        return JsonResponse({'error': 'medicine_name is required'}, status=400)

    latest_protocol = PRNProtocol.objects.filter(medicine_name__iexact=medicine_name).order_by('-created_at').first()
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


@editor_required
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
        log_audit_event(
            'ai_assist',
            f'Generated AI PRN protocol suggestions for {medicine_name}.',
            user=request.user,
            metadata={'medicine_name': medicine_name},
        )
        return JsonResponse(suggestions)
    except Exception:
        logger.exception('Error in ai_suggest endpoint')
        return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)
