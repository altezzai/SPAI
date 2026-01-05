import os
import random
import string

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils import timezone


def user_detail_image_path(instance, filename):
    path = f'user_detail/{instance.user.slug_value}/image/{filename}'
    return path


def user_detail_payment_path(instance, filename):
    path = f'user_detail/{instance.user_info.slug_value}/payment/lm/{filename}'
    return path

def subscription_payment_path(instance, filename):
    path = f'user_detail/{instance.user.slug_value}/payment/sub/{filename}'
    return path

def renew_proof_path(instance, filename):
    path = f'user_detail/{instance.user.slug_value}/renew/proof/{filename}'
    return path


def paper_submission_path(instance, filename):
    path = f'research_papers/{instance.title}/{filename}'
    return path


def event_document_path(instance, filename):
    path = f'event_doc/{instance.event.id}/{filename}'
    return path


def generate_unique_slug():
    slug = slugify(get_random_string(length=32))
    unique_slug = slug
    num = 1
    while User.objects.filter(slug_value=unique_slug).exists():
        unique_slug = '{}-{}'.format(slug, num)
        num += 1
    return unique_slug

def generate_unique_transaction_id():
    """Generate a unique 8-character alphanumeric transaction ID."""
    characters = string.ascii_letters + string.digits  # Letters and digits
    while True:
        payment_id = ''.join(random.choices(characters, k=8))
        if not SubscriptionPayment.objects.filter(payment_id=payment_id).exists():
            return payment_id

class EventManagement(models.Model):
    title = models.CharField(max_length=50, null=True, blank=True)
    image = models.ImageField(upload_to='SPAI/images/Events')
    datetime = models.DateTimeField()  # Updated field to store both date and time
    end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    registration_link = models.CharField(max_length=200, null=True, blank=True)

    def delete(self, *args, **kwargs):
        if self.image and os.path.exists(self.image.path):
            try:
                os.remove(self.image.path)
            except FileNotFoundError:
                # The file has already been deleted, so we can skip this step
                pass
        super(EventManagement, self).delete(*args, **kwargs)

    def __str__(self):
        return str(self.title)
    



class GalleryManagement(models.Model):
    image = models.ImageField(upload_to='SPAI/images/gallery', null=True)
    upload_date = models.DateTimeField( null=True, blank=True)
    image_name = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    event = models.ForeignKey(EventManagement, on_delete=models.SET_NULL, null=True, blank=True)
    place = models.CharField(max_length=255, null=True)

    def delete(self, *args, **kwargs):
        # Ensure the gallery image is deleted when the gallery entry is deleted
        if self.image:
            try:
                os.remove(self.image.path)
            except FileNotFoundError:
                pass
        super(GalleryManagement, self).delete(*args, **kwargs)

    def __str__(self):
        return str(self.image_name)


class GalleryImage(models.Model):
    gallery = models.ForeignKey(GalleryManagement, related_name='images', on_delete=models.CASCADE)
    images = models.ImageField(upload_to='gallery_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image {self.id} - {self.gallery.image_name}"

    def delete(self, *args, **kwargs):
        # Delete the image file from the local directory
        os.remove(self.images.path)
        super(GalleryImage, self).delete(*args, **kwargs)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("Please provide an email address"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_role", settings.ADMIN_ROLE_VALUE)
        extra_fields.setdefault("username", email)
        extra_fields.setdefault("status", settings.USER_CREATED)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("superuser should have is_staff field is true"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("superuser should have is_superuser field is true"))
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=50, verbose_name="email_address", unique=True)
    username = models.CharField(max_length=50, verbose_name="username", unique=True)
    first_name = models.CharField(max_length=50, verbose_name="first_name", null=True, blank=True)
    last_name = models.CharField(max_length=50, verbose_name="last_name", null=True, blank=True)
    state = models.CharField(max_length=60, choices=settings.STATE_CHOICES, default="None", null=True, blank=True)
    status = models.CharField(max_length=30, null=True, blank=True)
    user_role = models.PositiveSmallIntegerField(choices=settings.ROLE_CHOICES, blank=True, null=True)
    reg_no = models.CharField(max_length=15, null=True, blank=True)

    date_created = models.DateField(auto_now_add=True)
    slug_value = models.SlugField(auto_created=True, blank=True, null=True, unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    admin_approved = models.BooleanField(default=False)
    date_approved = models.DateTimeField(null=True, blank=True)
    approval_percentage = models.IntegerField(null=True, blank=True,
                                              validators=[MinValueValidator(0), MaxValueValidator(100)])
    original_date_approved = models.DateTimeField(null=True, blank=True)
    executive = models.PositiveSmallIntegerField(choices=settings.EXECUTIVE_CHOICES, blank=True, null=True)
    active_key = models.BooleanField(null=True, blank=True, default=False)
    annual_subscription = models.BooleanField(default=False)
    secretary_approval = models.BooleanField(default=False)
    president_approval = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.slug_value:
            self.slug_value = generate_unique_slug()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.email)


class UserDetailModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_details')
    degree = models.CharField(max_length=100, null=True, blank=True)
    profession = models.CharField(max_length=100, null=True, blank=True)
    institution = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=False, blank=False)
    alternate_number = models.CharField(max_length=15, null=True, blank=True)
    alternate_mail = models.EmailField(max_length=50, null=True, blank=True)
    photo = models.ImageField(upload_to=user_detail_image_path, null=True, blank=True)
    specialized_in = models.CharField(max_length=200, null=True, blank=True)
    research_interest = models.CharField(max_length=200, null=True, blank=True)

    def delete(self, *args, **kwargs):
        if self.photo:
            os.remove(self.photo.path)
        super(UserDetailModel, self).delete(*args, **kwargs)

    def __str__(self):
        return str(self.user.email)


class PaymentModel(models.Model):
    user_info = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_model')
    transaction_id = models.CharField(max_length=50, null=True, blank=True)
    reference_id = models.CharField(max_length=50, null=True, blank=True)
    bank_name = models.CharField(max_length=50, null=True, blank=True)
    payment_reported_date = models.DateField(auto_now_add=True)
    payment_type = models.PositiveSmallIntegerField(choices=settings.PAYMENT_TYPE, blank=True, null=True)
    document = models.FileField(upload_to=user_detail_payment_path, null=True, blank=True)

    def __str__(self):
        return str(self.user_info)

    def delete(self, *args, **kwargs):
        if self.document:
            os.remove(self.document.path)
        super(PaymentModel, self).delete(*args, **kwargs)


class LifeMembers(models.Model):
    reg_no = models.CharField(max_length=15, null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    mobile = models.CharField(max_length=30, null=True, blank=True)
    email = models.EmailField(max_length=50, null=True, blank=True)
    membership_date = models.DateField(null=True, blank=True)
    upload_date = models.DateTimeField(null=True, blank=True)
    update_date = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(null=True, blank=True)
    uid = models.SlugField(auto_created=True, blank=True, null=True, unique=True)
    lm_key = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.uid:
            self.uid = generate_unique_slug()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)


class InternshipApplication(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    college = models.CharField(max_length=100)
    university = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    internship_id = models.CharField(max_length=50, null=True, blank=True)

    interest_area = models.CharField(max_length=100)
    location_preference = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    qualification = models.CharField(max_length=100)
    course_name = models.CharField(max_length=100)
    passing_year = models.PositiveIntegerField()
    score = models.CharField(max_length=10)

    apply_date = models.DateField(auto_now=True)
    apply_time = models.TimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name}"


class Manuscript(models.Model):
    title = models.CharField(max_length=200)
    abstract = models.TextField()
    keywords = models.CharField(max_length=255)
    research_area = models.CharField(max_length=255)
    paper_file = models.FileField(upload_to=paper_submission_path)
    editor_message = models.TextField(null=True, blank=True)

    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    address = models.TextField()

    paper_no = models.CharField(max_length=20, null=True, blank=True)
    date_created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Author(models.Model):
    manuscript = models.ForeignKey(Manuscript, on_delete=models.CASCADE, related_name="authors")
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=100)
    organization = models.CharField(max_length=200)
    email = models.EmailField()
    mobile = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class EventDocumentModel(models.Model):
    event = models.ForeignKey(EventManagement, on_delete=models.CASCADE, related_name='event_doc')
    title = models.CharField(max_length=50, null=True, blank=True)
    file = models.FileField(upload_to=event_document_path)

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        if self.file:
            os.remove(self.file.path)
        super(EventDocumentModel, self).delete(*args, **kwargs)


class PasswordResetRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset')
    date_created = models.DateTimeField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.user.email} at {self.date_created}"


class AnnualSubscriptionModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='annual_sub')
    date_created = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user)

class SubscriptionPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_model_user')
    transaction_id = models.CharField(max_length=50, null=True, blank=True)
    bank_name = models.CharField(max_length=50, null=True, blank=True)
    payment_date = models.DateField(auto_now_add=True)
    document = models.FileField(upload_to=subscription_payment_path, null=True, blank=True)
    payment_id = models.CharField(max_length=8, unique=True, blank=True)

    def __str__(self):
        return str(self.user)

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = generate_unique_transaction_id()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.document:
            os.remove(self.document.path)
        super(SubscriptionPayment, self).delete(*args, **kwargs)


class Testimonials(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    message = models.TextField()
    publish = models.BooleanField(null=True)
    date_created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ContactUs(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    message = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class JournalQuery(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    message = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class BannerEvents(models.Model):
    event = models.ForeignKey(EventManagement, on_delete=models.CASCADE, related_name='event_banner_display')
    description = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return str(self.event.title)
    


# Leadership 
class Leadership(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='leadership_pics/')

    def __str__(self):
        return self.name