from django.db import models


class Resident(models.Model):
    name = models.CharField(max_length=200)
    room_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Room {self.room_number})"


class PRNProtocol(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='protocols')
    medicine_name = models.CharField(max_length=200)
    form = models.CharField(max_length=100)
    strength = models.CharField(max_length=100)
    route_of_administration = models.CharField(max_length=100)
    dose_and_frequency = models.TextField()
    min_time_interval = models.CharField(max_length=100)
    max_dose_24h = models.CharField(max_length=100)
    capacity_statement = models.TextField()
    reason_for_administration = models.TextField()
    special_instructions = models.TextField(blank=True)
    additional_information = models.TextField(blank=True)
    # GP reporting checkboxes
    gp_persistent_need = models.BooleanField(default=False)
    gp_never_requesting = models.BooleanField(default=False)
    gp_requesting_too_often = models.BooleanField(default=False)
    gp_side_effects = models.BooleanField(default=False)
    gp_other = models.CharField(max_length=200, blank=True)
    # Signatures
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
