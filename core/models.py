from django.conf import settings
from django.db import models
from django.utils import timezone


class Resident(models.Model):
    RESIDENTIAL_OR_NURSING_CHOICES = [
        ('residential', 'Residential'),
        ('nursing', 'Nursing'),
    ]

    name = models.CharField(max_length=200)
    room_number = models.CharField(max_length=20)
    residential_or_nursing = models.CharField(
        max_length=20,
        choices=RESIDENTIAL_OR_NURSING_CHOICES,
        default='residential',
    )
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
    monitoring_requirements = models.TextField(blank=True, default='')
    administration_preferences = models.TextField(blank=True, default='')
    legal_safeguarding_information = models.TextField(blank=True, default='')
    mar_front_page_text = models.TextField(blank=True, default='')
    dnar_in_place = models.BooleanField(default=False)
    is_diabetic = models.BooleanField(default=False)
    has_peg = models.BooleanField(default=False)
    self_medicates = models.BooleanField(default=False)
    risk_assessment_in_place = models.BooleanField(default=False)
    has_swallowing_difficulties = models.BooleanField(default=False)
    on_oxygen = models.BooleanField(default=False)
    can_take_medication_orally = models.BooleanField(default=False)
    requires_inhaler = models.BooleanField(default=False)
    has_medication_capacity = models.BooleanField(default=False)
    has_parkinsons = models.BooleanField(default=False)
    mca_in_place = models.BooleanField(default=False)
    has_dementia = models.BooleanField(default=False)
    on_blood_thinning_medication = models.BooleanField(default=False)
    requires_pulse_or_bp_before_medication = models.BooleanField(default=False)
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

    def get_medical_conditions_list(self):
        return self._split_multiline(self.medical_conditions)

    def get_medication_alerts_list(self):
        return self._split_multiline(self.medication_alerts)

    def get_monitoring_requirements_list(self):
        return self._split_multiline(self.monitoring_requirements)

    def get_administration_preferences_list(self):
        return self._split_multiline(self.administration_preferences)

    def get_legal_safeguarding_information_list(self):
        return self._split_multiline(self.legal_safeguarding_information)


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
