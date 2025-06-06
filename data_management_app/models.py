from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.core.exceptions import ValidationError


class WebhookLog(models.Model):
    received_at = models.DateTimeField(auto_now_add=True)
    data = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.webhook_id} : {self.received_at}"
    



class Contact(models.Model):
    contact_id = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    dnd = models.BooleanField(default=False)
    country = models.CharField(max_length=50, blank=True, null=True)
    date_added = models.DateTimeField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    custom_fields = models.JSONField(default=list, blank=True)
    location_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1, defaults={'minimum_price': 0})
        return obj


class GlobalSettings(SingletonModel):
    minimum_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Minimum price for this service"
    )

    def __str__(self):
        return "Global Settings"


class Service(models.Model):
    """
    Main service model that represents a service offering
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return self.name


class Feature(models.Model):
    """
    Features that can be associated with services
    """
    service = models.ForeignKey(
        Service, 
        on_delete=models.CASCADE, 
        related_name='features'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['service', 'name']

    def __str__(self):
        return f"{self.service.name} - {self.name}"


class PricingOption(models.Model):
    """
    Different pricing options for a service (e.g., monthly, quarterly)
    """
    service = models.ForeignKey(
        Service, 
        on_delete=models.CASCADE, 
        related_name='pricing_options'
    )
    name = models.CharField(max_length=100)
    discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (0-100)"
    )
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Base price before discount"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['service', 'name']
        unique_together = ['service', 'name']

    def __str__(self):
        return f"{self.service.name} - {self.name}"

    @property
    def discounted_price(self):
        """Calculate price after discount"""
        if self.discount > 0:
            return self.base_price * (1 - self.discount / 100)
        return self.base_price


class PricingOptionFeature(models.Model):
    """
    Junction table to link pricing options with features and their inclusion status
    """
    pricing_option = models.ForeignKey(
        PricingOption, 
        on_delete=models.CASCADE, 
        related_name='selected_features'
    )
    feature = models.ForeignKey(
        Feature, 
        on_delete=models.CASCADE,
        related_name='pricing_options'
    )
    is_included = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['pricing_option', 'feature']
        verbose_name = "Pricing Option Feature"
        verbose_name_plural = "Pricing Option Features"

    def clean(self):
        """Ensure feature belongs to the same service as pricing option"""
        if self.feature.service != self.pricing_option.service:
            raise ValidationError(
                "Feature must belong to the same service as the pricing option"
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        included = "✓" if self.is_included else "✗"
        return f"{self.pricing_option.name} - {self.feature.name} [{included}]"


class Question(models.Model):
    """
    Questions associated with services for customization
    """
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean/Yes-No'),
        ('choice', 'Multiple Choice'),
        ('multiple_choice', 'Multiple Selection'),
        ('date', 'Date'),
        ('email', 'Email'),
    ]

 
    service = models.ForeignKey(
        Service, 
        on_delete=models.CASCADE, 
        related_name='questions'
    )
    text = models.CharField(max_length=500)
    type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Additional price per unit for this question"
    )
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['service', 'order', 'created_at']

    def __str__(self):
        return f"{self.service.name} - {self.text}"


class QuestionOption(models.Model):
    """
    Options for choice-type questions
    """
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='options'
    )
    value = models.CharField(max_length=200)
    label = models.CharField(max_length=200, blank=True)
    additional_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Additional price for selecting this option"
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['question', 'order']
        unique_together = ['question', 'value']

    def clean(self):
        """Ensure question type supports options"""
        if self.question.type not in ['choice', 'multiple_choice']:
            raise ValidationError(
                "Options can only be added to choice or multiple_choice questions"
            )

    def save(self, *args, **kwargs):
        self.clean()
        # Set label to value if not provided
        if not self.label:
            self.label = self.value
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.question.text} - {self.label}"






class Purchase(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="purchases")
    services = models.ManyToManyField(Service, related_name="purchases")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    price_plan = models.ForeignKey(PricingOption, on_delete=models.CASCADE, related_name='purchases')
    is_submited = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Purchase #{self.id} by Contact {self.contact.contact_id}"
        
class SavedPricingPlan(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="savedpricingplan")
    name = models.CharField(max_length=100)
    discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (0-100)"
    )
    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Base price before discount"
    )

class QuestionsAndAnswers(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='questionsandanswers')
    ans = models.BooleanField(default=False)

class QuestionOptionAnswers(models.Model):
    qu_ans = models.ForeignKey(QuestionsAndAnswers, on_delete=models.CASCADE)
    question_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, related_name='answers', null=True, blank=True)
    qty = models.CharField(max_length=200, null=True, blank=True)
    