from django.conf import settings
from django.db import models
from django.utils import timezone


class Resident(models.Model):
    REVIEW_STATUS_DRAFT = 'draft'
    REVIEW_STATUS_IN_REVIEW = 'in_review'
    REVIEW_STATUS_REVIEWED = 'reviewed'
    REVIEW_STATUS_CHOICES = [
        (REVIEW_STATUS_DRAFT, 'Draft'),
        (REVIEW_STATUS_IN_REVIEW, 'In review'),
        (REVIEW_STATUS_REVIEWED, 'Reviewed'),
    ]

    name = models.CharField(max_length=200)
    room_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    mental_capacity = models.TextField(blank=True, default='')
    medical_conditions = models.TextField(blank=True, default='')
    allergies = models.TextField(blank=True, default='')
    medication_alerts = models.TextField(blank=True, default='')
    photo = models.ImageField(upload_to='resident_photos/', null=True, blank=True)
    nhs_number = models.CharField(max_length=20, blank=True, default='')
    next_of_kin = models.CharField(max_length=200, blank=True, default='')
    next_of_kin_contact = models.CharField(max_length=20, blank=True, default='')
    gp_name = models.CharField(max_length=200, blank=True, default='')
    gp_surgery = models.CharField(max_length=200, blank=True, default='')
    gp_contact = models.CharField(max_length=20, blank=True, default='')
    pharmacy_name = models.CharField(max_length=200, blank=True, default='')
    pharmacy_contact = models.CharField(max_length=20, blank=True, default='')
    emergency_contact_name = models.CharField(max_length=200, blank=True, default='')
    emergency_contact_relationship = models.CharField(max_length=100, blank=True, default='')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, default='')
    monitoring_requirements = models.TextField(blank=True, default='')
    administration_preferences = models.TextField(blank=True, default='')
    legal_safeguarding_information = models.TextField(blank=True, default='')
    care_summary = models.TextField(blank=True, default='')
    mar_front_page_text = models.TextField(blank=True, default='')
    care_plan_reviewed = models.DateField(null=True, blank=True)
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default=REVIEW_STATUS_DRAFT,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_residents',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Room {self.room_number})"

    def get_age(self):
        today = timezone.localdate()
        years = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        return years

    def _split_multiline(self, value):
        return [line.strip() for line in (value or '').splitlines() if line.strip()]

    def get_allergies_list(self):
        return self._split_multiline(self.allergies)

    def get_medication_alerts_list(self):
        return self._split_multiline(self.medication_alerts)

    def get_monitoring_requirements_list(self):
        return self._split_multiline(self.monitoring_requirements)

    def get_administration_preferences_list(self):
        return self._split_multiline(self.administration_preferences)

    def get_legal_safeguarding_information_list(self):
        return self._split_multiline(self.legal_safeguarding_information)


class PRNProtocol(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='protocols')
    medicine_name = models.CharField(max_length=200)
    form = models.CharField(max_length=100)
    strength = models.CharField(max_length=100)
    route_of_administration = models.CharField(max_length=100)
    dose_and_frequency = models.TextField()
    min_time_interval = models.CharField(max_length=100)
    max_dose_24h = models.CharField(max_length=100)
    medication_instruction = models.TextField(blank=True, default='')
    capacity_statement = models.TextField()
    reason_for_administration = models.TextField()
    special_instructions = models.TextField(blank=True)
    additional_information = models.TextField(blank=True)
    gp_persistent_need = models.BooleanField(default=False)
    gp_never_requesting = models.BooleanField(default=False)
    gp_requesting_too_often = models.BooleanField(default=False)
    gp_side_effects = models.BooleanField(default=False)
    gp_other = models.CharField(max_length=200, blank=True)
    prepared_by_name = models.CharField(max_length=200, blank=True)
    prepared_by_designation = models.CharField(max_length=100, blank=True)
    prepared_by_date = models.DateField(null=True, blank=True)
    approved_by_name = models.CharField(max_length=200, blank=True)
    approved_by_designation = models.CharField(max_length=100, blank=True)
    approved_by_date = models.DateField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True)
    reviewed_by_name = models.CharField(max_length=200, blank=True)
    reviewed_by_designation = models.CharField(max_length=100, blank=True)
    reviewed_by_date = models.DateField(null=True, blank=True)
    checked_by_name = models.CharField(max_length=200, blank=True)
    checked_by_designation = models.CharField(max_length=100, blank=True)
    checked_by_date = models.DateField(null=True, blank=True)
    new_review_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medicine_name} - {self.resident.name}"

    def get_special_instructions_list(self):
        if not self.special_instructions:
            return []
        return [line.strip() for line in self.special_instructions.splitlines() if line.strip()]

    def get_additional_information_list(self):
        if not self.additional_information:
            return []
        return [line.strip() for line in self.additional_information.splitlines() if line.strip()]


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('review', 'Review'),
        ('export_pdf', 'Export PDF'),
        ('export_docx', 'Export DOCX'),
        ('print', 'Print'),
        ('ai_assist', 'AI assist'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    resident = models.ForeignKey(
        Resident,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50, blank=True, default='')
    entity_label = models.CharField(max_length=255, blank=True, default='')
    description = models.CharField(max_length=255)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} {self.entity_type}: {self.entity_label or self.entity_id}"
