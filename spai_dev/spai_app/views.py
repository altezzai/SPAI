import datetime

import requests
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from datetime import datetime, timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from . import models, forms
from .models import GalleryManagement, User, EventManagement, UserDetailModel, GalleryImage, PaymentModel, Testimonials, \
    AnnualSubscriptionModel, SubscriptionPayment, BannerEvents
from .decorators import admin_only, authenticated_only
from .utils import render_to_pdf, get_registration_num, get_research_paper_no, send_mail_to_executives, \
    send_password_reset_email, update_subscription_status, send_contact_us_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import LifeMembers
from .serializers import LifeMembersSerializer, UserSerializer, UserDetailSerializer, PaymentSerializer, \
    AnnualSubscriptionSerializer, SubscriptionPaymentSerializer


# Frequently used methods
def admin_action(sts):
    if sts == settings.EX_2_APPROVED:
        return 'Admin approval pending'
    return 'No action needed'


def user_status_change(slug, current_status):
    user = User.objects.get(slug_value=slug)
    if user is not None:
        if current_status == settings.USER_CREATED:
            user.status = settings.USER_DETAILS_ADDED
        elif current_status == settings.USER_DETAILS_ADDED:
            user.status = settings.PAYMENT_PENDING
        elif current_status == settings.PAYMENT_PENDING:
            user.status = settings.PAYMENT_DONE
        elif current_status == settings.PAYMENT_DONE:
            user.status = settings.EX_1_APPROVAL_PENDING
        elif current_status == settings.EX_1_APPROVAL_PENDING:
            user.status = settings.EX_1_APPROVED
        elif current_status == settings.EX_1_APPROVED:
            user.status = settings.EX_2_APPROVAL_PENDING
        elif current_status == settings.EX_2_APPROVAL_PENDING:
            user.status = settings.EX_2_APPROVED
        elif current_status == settings.EX_2_APPROVED:
            user.status = settings.ADMIN_APPROVAL_PENDING
        elif current_status == settings.ADMIN_APPROVAL_PENDING:
            user.status = settings.ADMIN_APPROVED
        else:
            pass
        user.save()


def get_next_step(status):
    if status == settings.USER_CREATED:
        return 'User created, Details not added'
    if status == settings.USER_DETAILS_ADDED:
        return 'User Details added, Payment not completed'
    if status == settings.PAYMENT_PENDING:
        return 'Payment Pending'
    if status == settings.PAYMENT_DONE:
        return 'Payment completed, Executive Approval Pending'
    if status in [settings.EX_1_APPROVAL_PENDING, settings.EX_2_APPROVAL_PENDING]:
        return 'Executive Approval Pending'
    if status == settings.EX_1_APPROVED:
        return 'First Executive Approved, Waiting for Second Approval'
    if status == settings.EX_2_APPROVED:
        return 'Executives Are Approved, Admin Approval Pending'
    if status == settings.ADMIN_APPROVAL_PENDING:
        return 'Admin Approval Pending'
    if status == settings.ADMIN_APPROVED:
        return 'Admin Approved, No action needed'
    if status == settings.ADMIN_REJECTED:
        return 'Admin Rejected'

def recaptcha_verification(recaptcha_response):
    data = {
        "secret": settings.RECAPTCHA_PRIVATE_KEY,
        "response": recaptcha_response
    }
    response = requests.post(settings.VERIFICATION_URL, data=data)
    res = response.json()
    return res.get("success")

# Views
def index(request):
    now = timezone.now()
    update_subscription_status(request, True)
    upcoming_events = list(EventManagement.objects.filter(datetime__gte=now).order_by('datetime')[:5])
    if len(upcoming_events) < 5:
        remaining_slots = 5 - len(upcoming_events)
        past_events = list(EventManagement.objects.filter(datetime__lt=now).order_by('-datetime')[:remaining_slots])
        upcoming_events.extend(past_events)
    context = {
        'upcoming_events': upcoming_events,
        'page':0
    }

    testimonials = Testimonials.objects.filter(publish=True).order_by('-date_created')
    if testimonials.count() >= 3:
        latest_testimonials = testimonials[:3]  # Get the first 3
    else:
        latest_testimonials = testimonials
    context["testimonials"] = latest_testimonials

    ribben = get_nearest_event()
    context['events'] = ribben
    form = forms.ContactUsForm()
    context['form'] = form
    return render(request, 'mainpages/new_home.html', context)


def add_testimonals(request):
    return render(request, 'members/add_testimonials.html')


def about_page(request):
    page = request.GET.get('page')
    context = {"page": 1}
    if page == "about_spai":
        return render(request, 'static_pages/about/about.html', context)
    if page == "mission":
        return render(request, 'static_pages/about/mission.html', context)
    if page == "history":
        return render(request, 'static_pages/about/history.html', context)
    if page == "message_from_president":
        return render(request, 'static_pages/about/msgpresident.html', context)
    if page == "message_from_secretary":
        return render(request, 'static_pages/about/msgsecretary.html', context)
    if page == "president":
        return render(request, 'static_pages/about/leadership/president.html', context)
    if page == "secretary":
        return render(request, 'static_pages/about/leadership/secretary.html', context)
    if page == "finance_secretary":
        return render(request, 'static_pages/about/leadership/finance.html', context)
    if page == "patron":
        return render(request, 'static_pages/about/leadership/patron.html', context)
    if page == "committee":
        return render(request, 'static_pages/about/leadership/committee.html', context)
    if page == "pre_committee":
        return render(request, 'static_pages/about/leadership/previous_year.html', context)
    if page == "regional":
        return render(request, 'static_pages/about/leadership/regional.html', context)


def membership(request):
    page = request.GET.get('page')
    context = {"page": 3}
    user_key = False
    if request.user.is_authenticated and (request.user.user_role == 1 or request.user.executive in [1, 2, 3]):
        user_key = True
    if page == "previlege":
        return render(request, 'static_pages/membership/previlege.html', context)
    if page == "patrons":
        return render(request, 'static_pages/membership/patrons.html', context)
    if page == "major":
        return render(request, 'static_pages/news/major.html', {"page": 2})
    if page == "exe_meeting":
        return render(request, 'static_pages/news/exe_meeting.html', {"page": 2, "uk": user_key})
    if page == "general_body":
        return render(request, 'static_pages/news/general_body.html', {"page": 2})


def publications(request):
    context = {"page": 4}
    page = request.GET.get('page')
    if page == "about_spai_journal":
        return render(request, 'static_pages/publications/spai_journel.html', context)
    if page == "editorial":
        return render(request, 'static_pages/publications/editorial.html', context)
    if page == "joinaseditor":
        return render(request, 'static_pages/publications/joinaseditor.html', context)
    if page == "joinasreviewer":
        return render(request, 'static_pages/publications/joinasreviewer.html', context)
    if page == "call_for_manuscripts":
        return render(request, 'static_pages/publications/call.html', context)
    if page == "journal_archives":
        return render(request, 'static_pages/publications/journalarchieve.html', context)


def academic(request):
    context = {"page": 5}
    page = request.GET.get('page')
    if page == "about_internship":
        return render(request, 'static_pages/academic/internship/about.html', context)
    if page == "upcoming_annual":
        today = timezone.now().date()
        events = EventManagement.objects.filter(end_date__gte=today).order_by('end_date')
        context['events'] = events
        return render(request, 'static_pages/academic/anual_conference/upcoming.html', context)
    if page == "past_annual":
        today = timezone.now().date()
        events = EventManagement.objects.filter(end_date__lt=today).order_by('-end_date')
        context['events'] = events
        return render(request, 'static_pages/academic/anual_conference/past.html', context)
    if page == "annual_archives":
        return render(request, 'static_pages/academic/anual_conference/archives.html', context)
    if page == "spai_award":
        return render(request, 'static_pages/academic/awards/awards.html', context)
    if page == "paper_presenter":
        return render(request, 'static_pages/academic/awards/papper.html', context)
    if page == "poster_presentation":
        return render(request, 'static_pages/academic/awards/poster.html', context)
    if page == "publication":
        return render(request, 'static_pages/academic/awards/publications.html', context)
    if page == "research":
        return render(request, 'static_pages/academic/awards/research.html', context)
    if page == "student_research":
        return render(request, 'static_pages/academic/awards/student.html', context)
    if page == "research_grant":
        return render(request, 'static_pages/academic/grant/research.html', context)
    if page == "call_for_grants":
        return render(request, 'static_pages/academic/grant/call.html', context)
    if page == "mentors":
        return render(request, 'static_pages/academic/internship/mentors.html', context)
    if page == "internship_testimonials":
        return render(request, 'static_pages/academic/internship/testimonials.html', context)
    if page == "upcoming_online_webinars":
        return render(request, 'static_pages/academic/online/upcoming.html', context)
    if page == "completed_online_webinars":
        return render(request, 'static_pages/academic/online/past.html', context)
    if page == "upcoming_state_workshop":
        return render(request, 'static_pages/academic/state_workshop/upcomming.html', context)
    if page == "completed_state_workshop":
        return render(request, 'static_pages/academic/state_workshop/past.html', context)
    if page == "upcoming_national_workshop":
        return render(request, 'static_pages/academic/workshop/upcoming.html', context)
    if page == "completed_national_workshop":
        return render(request, 'static_pages/academic/workshop/past.html', context)
    if page == "certification":
        return render(request, 'static_pages/academic/certification.html', context)
    if page == "latest_update":
        return render(request, 'static_pages/academic/latest_update.html', context)
    if page == "mou":
        return render(request, 'static_pages/academic/mou.html', context)


def history(request):
    context = {'page': 'about', 'page2': 'history'}
    return render(request, 'mainpages/history.html', context)


def about_members(request):
    context = {}
    user_details_vew(request)
    if request.user.user_role == settings.ADMIN_ROLE_VALUE:
        users = User.objects.all()
        for user in users:
            user.next_step = get_next_step(user.status)
        context['users'] = users
    context['page'] = 'about'
    context['page2'] = 'members'
    context['request'] = request
    return render(request, 'about/members.html', context)


@admin_only
def members(request):
    users = User.objects.all()
    user_list = []
    for user in users:
        user_data = get_user_full_details(request, user.slug_value)
        user_list.append(user_data)
    context = {'users': user_list}
    return render(request, 'members/members.html', context)


def user_registration(request):
    if request.method == "POST":
        form = forms.UserRegistrationForm(request.POST)
        recaptcha_response = request.POST.get("g-recaptcha-response")
        res = recaptcha_verification(recaptcha_response)
        if not res:
            messages.error(request, "reCAPTCHA verification failed. Please try again.")
            return render(request, "members/user_registration.html", {"form": form})

        if form.is_valid():
            user = form.save()
            logout(request)
            messages.success(request, "Registration successfully completed. Please log in.")
            return redirect("login_page")
        else:
            context = {"form": form}
            return render(request, "members/user_registration.html", context)
    else:
        form = forms.UserRegistrationForm()
        context = {"form": form}
        return render(request, "members/user_registration.html", context)


def gallery(request):
    gallery_objects = GalleryManagement.objects.all()
    context = {'page': 'gallery', 'gallery_objects': gallery_objects}
    return render(request, 'mainpages/gallery.html', context)


def gallery_list(request):
    galleries = GalleryManagement.objects.all().order_by("-id")
    page_number = request.GET.get('page', 1)
    paginator = Paginator(galleries, 9)
    page_obj = paginator.get_page(page_number)
    context = {'galleries': galleries, 'page_obj': page_obj, 'page': 2}
    return render(request, 'mainpages/gallery.html', context)


def gallery_detail(request, pk):
    gallery = GalleryManagement.objects.get(pk=pk)
    images = GalleryImage.objects.filter(gallery=gallery)
    return render(request, 'mainpages/gallery_detail.html', {'gallery': gallery, 'images': images})


@admin_only
def gallery_create(request):
    fs = FileSystemStorage()
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        place = request.POST.get('place')
        image = request.FILES.get('mainimage')
        gallery = GalleryManagement.objects.create(
            image_name=title,
            description=description,
            place=place,
            image=image
        )

        # Loop through the files in request.FILES
        # Process multiple image uploads
        multiple_images = request.FILES.getlist('multiple_images')
        for image_file in multiple_images:
            image_name = fs.save(image_file.name, image_file)
            GalleryImage.objects.create(gallery=gallery, images=image_name)

        return redirect('gallery_list')  # Return a success response

    return render(request, 'admin/galleryadd.html')  # Render the add gallery template


@admin_only
def gallery_delete(request, pk):
    gallery = get_object_or_404(GalleryManagement, pk=pk)
    gallery.delete()
    return redirect('gallery_list')


@admin_only
def delete_gallery_image(request, image_id):
    # Get the image object or return a 404 if not found
    obj = GalleryImage.objects.get(pk=image_id)
    gallery_id = obj.gallery.pk  # Save gallery ID to redirect back later

    # Delete the image file
    obj.delete()

    # Add a success message
    messages.success(request, 'Image deleted successfully.')

    # Redirect back to the gallery detail page
    return redirect('gallery_detail', pk=gallery_id)


@admin_only
def add_gallery_image(request, gallery_id):
    gallery = get_object_or_404(GalleryManagement, id=gallery_id)

    if request.method == 'POST' and request.FILES['image']:
        image = request.FILES['image']
        # Create a new GalleryImage object
        new_image = GalleryImage.objects.create(gallery=gallery, images=image)
        new_image.save()
        messages.success(request, 'Image added successfully.')
        return redirect('gallery_detail', pk=gallery_id)

    return redirect('gallery_detail', pk=gallery_id)


def news(request):
    all_events = EventManagement.objects.all().order_by('-datetime')
    upcoming_events = EventManagement.objects.filter(end_date__gte=timezone.now()).order_by('datetime')
    past_events = EventManagement.objects.filter(end_date__lt=timezone.now()).order_by('-datetime')

    page_number = request.GET.get('page', 1)
    current_tab = request.GET.get('tab', 'all')

    if current_tab == 'upcoming':
        paginator = Paginator(upcoming_events, 9)
    elif current_tab == 'post':
        paginator = Paginator(past_events, 9)
    else:
        paginator = Paginator(all_events, 9)
        current_tab = 'all'  # Default to 'all' if the tab is not specified
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'current_tab': current_tab,
        'page': 2
    }
    return render(request, 'mainpages/news.html', context)


def news_detail(request, pk):
    event_object = EventManagement.objects.get(pk=pk)
    upcoming_events = list(EventManagement.objects.filter(datetime__gt=event_object.datetime).order_by('datetime')[:3])
    if len(upcoming_events) < 3:
        remaining_slots = 3 - len(upcoming_events)
        past_events = list(
            EventManagement.objects.filter(datetime__lt=event_object.datetime).order_by('-datetime')[:remaining_slots])
        upcoming_events.extend(past_events)
    if GalleryManagement.objects.filter(event=event_object).exists():
        gallery = GalleryManagement.objects.get(event=event_object)
    else:
        gallery = None
    files = models.EventDocumentModel.objects.filter(event=event_object)
    context = {
        "event": event_object,
        'related_events': upcoming_events,
        "gallery": gallery,
        "files": files
    }
    return render(request, 'mainpages/news_details.html', context)


from django.core.files.storage import FileSystemStorage

@admin_only
def update_reg_link(request,pk):
    if request.method == 'POST':
        # Get the new registration link from the request
        new_link = request.POST.get('link', None)
        
        if new_link:
            try:
                # Fetch the event by primary key
                event = get_object_or_404(EventManagement, pk=pk)

                # Update the registration link
                event.registration_link = new_link
                event.save()

                return JsonResponse({'success': True, 'message': 'Registration link updated successfully!'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})


@admin_only
def eventadd(request):
    if request.method == 'POST':
        # Process the main event image
        fs = FileSystemStorage()
        image = request.FILES['image']
        image_name = fs.save(image.name, image)

        # Create the event object
        event = EventManagement.objects.create(
            title=request.POST['title'],
            image=image_name,
            datetime=request.POST['datetime'],
            end_date=request.POST.get('end_date', None),
            location=request.POST['location'],
            description=request.POST.get('description', ''),
            registration_link=request.POST.get('registration_link', '')
        )

        # Check if the checkbox for multiple images is checked
        if 'multipleImagesCheck' in request.POST:
            gallery = GalleryManagement.objects.create(
                image=image_name,
                upload_date=request.POST['datetime'],
                image_name=request.POST['title'],
                description=request.POST.get('description', ''),
                event=event,
                place=request.POST['location']
            )

            # Process multiple image uploads
            multiple_images = request.FILES.getlist('multiple_images')
            for image_file in multiple_images:
                image_name = fs.save(image_file.name, image_file)
                GalleryImage.objects.create(gallery=gallery, images=image_name)

        return redirect('news')  # Redirect to a success page after creation

    return render(request, 'admin/eventadd.html')


@admin_only
def delete_event(request, event_id):
    if request.user.user_role == settings.ADMIN_ROLE_VALUE:
        event = get_object_or_404(EventManagement, id=event_id)
        event.delete()
        return redirect(reverse('news'))
    return redirect(reverse('news'))


# @admin_only
def add_image_template(request):
    if request.POST and (request.user.user_role == settings.ADMIN_ROLE_VALUE or request.user.executive in [settings.SECRETARY, settings.PRESIDENT]):
        frm = forms.GalleryManagementForm(request.POST, request.FILES)
        if frm.is_valid:
            frm.save()
            return redirect('gallery')
    else:
        frm = forms.GalleryManagementForm()
    context = {'page': 'gallery', 'frm': frm}
    return render(request, 'admin/add_image_template.html', context)


def user_login(request):
    form = forms.UserLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            if request.user.status == settings.USER_CREATED:
                return redirect('user_detail')
            else:
                return redirect('index')
    return render(request, 'mainpages/login.html', {'form': form})


@admin_only
def delete_gallery_item(request, *args, **kwargs):
    if request.user.user_role == settings.ADMIN_ROLE_VALUE:
        try:
            instance = models.GalleryManagement.objects.get(id=kwargs["id"])
            instance.delete()
            return redirect("gallery")
        except:
            return redirect("gallery")
    return redirect("gallery")


@authenticated_only
def user_profile_details(request):
    if request.method == 'POST':
        form = forms.UserDetailForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            request.user.status = settings.USER_DETAILS_ADDED
            request.user.approval_percentage = 0
            request.user.save()
            form.save()
            user_status_change(request.user.slug_value, request.user.status)
            return redirect('payment_model', slug=request.user.slug_value)  # redirect to a success page
    else:
        form = forms.UserDetailForm(request.user)
    return render(request, 'members/user_profile_details.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('index')


@authenticated_only
def user_details_vew(request, *args, **kwargs):
    slug = kwargs.get("slug", None)
    if request.user.user_role == settings.ADMIN_ROLE_VALUE or request.user.slug_value == slug or request.user.executive in [
        settings.SECRETARY, settings.PRESIDENT]:
        context = {}
        user_data = get_user_full_details(request, slug)
        context['user'] = user_data
        return render(request, 'members/member_details.html', context)
    else:
        return redirect('login_page')


@authenticated_only
def admin_approval(request, *args, **kwargs):
    if request.user.executive in [settings.SECRETARY, settings.PRESIDENT]:
        slug = kwargs.get("slug", None)
        user = User.objects.filter(slug_value=slug).first()
        if user is None:
            return redirect("life_members_get")
        if user.approval_percentage == 0:
            user.approval_percentage = 50
            user.status = settings.EX_1_APPROVED
        elif user.approval_percentage == 50:
            user.approval_percentage = 100
            user.status = settings.EX_2_APPROVED
        if request.user.executive == settings.SECRETARY:
            user.secretary_approval = True
        elif request.user.executive == settings.PRESIDENT:
            user.president_approval = True
        user.save()
        user_status_change(slug, user.status)
        return redirect('life_members_get')
    elif request.user.user_role == settings.ADMIN_ROLE_VALUE:
        slug = kwargs.get("slug", None)
        user = User.objects.filter(slug_value=slug).first()
        if user is None:
            return redirect("life_members_get")
        if user.approval_percentage == 100 and user.status in [settings.ADMIN_APPROVAL_PENDING, settings.EX_2_APPROVED]:
            reg_no = get_registration_num()
            user.admin_approved = True

            cutoff_date = datetime(2025, 4, 1, 0, 0, 0)
            if datetime.now() < cutoff_date:
                user.date_approved = cutoff_date
            else:
                user.date_approved = datetime.now()
            user.reg_no = reg_no
            user.active_key = True

            # Annual Subscription section
            current = datetime.today().date()
            cutoff_date_1 = cutoff_date.date()
            if current < cutoff_date_1:
                original_date = cutoff_date_1
            else:
                original_date = current
            annual_subscription = AnnualSubscriptionModel(
                user=user,
                date_created=original_date,
                end_date=original_date + timedelta(days=365),
                active=True
            )
            user.annual_subscription = True
            user.original_date_approved = datetime.now()
            annual_subscription.save()
            user.save()

            send_email_with_attachment(request, slug)
            user_status_change(slug, user.status)
            return redirect('life_members_get')
        else:
            return redirect("life_members_get")
    else:
        return redirect('login_page')


@admin_only
def executive_approval(request, *args, **kwargs):
    if request.user.executive in [settings.SECRETARY, settings.PRESIDENT]:
        slug = kwargs.get("slug", None)
        user = User.objects.filter(slug_value=slug).first()
        if user is None:
            return redirect("members")
        if user.approval_percentage == 0:
            user.approval_percentage = 50
            user.status = settings.EX_1_APPROVED
        elif user.approval_percentage == 50:
            user.approval_percentage = 100
            user.status = settings.EX_2_APPROVED
        user.save()
        return redirect('members')
    else:
        return redirect('login_page')


def user_login_page(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = forms.UserLoginForm(request.POST or None)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user:
                login(request, user)
                if request.user.status == settings.USER_CREATED:
                    return redirect('user_profile_details')
                else:
                    return redirect('index')
    else:
        form = forms.UserLoginForm()
    return render(request, 'members/user_login.html', {'form': form})


@authenticated_only
def certificate(request, *args, **kwargs):
    slug = kwargs.get("slug", None)
    if request.user.is_authenticated and request.user.admin_approved:
        if request.user.user_role == settings.ADMIN_ROLE_VALUE:
            user = User.objects.get(slug_value=slug)
        else:
            user = User.objects.get(slug_value=request.user.slug_value)
        context = {"name": f"{user.first_name} {user.last_name}", "reg_no": user.reg_no, "date": user.date_approved}
        template_path = 'pdf_template.html'
        template = get_template(template_path)
        html = template.render(context)
        pdf = render_to_pdf(template_path, context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"{user.username}_certificate.pdf"
            content = f"inline; filename={filename}"
            response['Content-Disposition'] = content
            return response
        return HttpResponse("Something went wrong..!")
    else:
        return redirect('index')


def send_email_with_attachment(request, slug):
    if request.user.user_role == settings.ADMIN_ROLE_VALUE:
        user = User.objects.get(slug_value=slug)
    else:
        user = User.objects.get(slug_value=request.user.slug_value)

    subject = "Approval of Your Registration with SPAI"
    message = (
        f"Dear {user.first_name} {user.last_name},\nI hope this email finds you well.\n"
        f"We are pleased to inform you that your registration for membership with the Sports"
        f" Psychology Association of India (SPAI) has been successfully approved.\n"
        f"Your registration ID/number is: {user.reg_no}. Please retain this for future reference.\n"
        f"If you have any questions or require further assistance, feel free to reach out to us at "
        f"secretaryspai@gmail.com.\n"
        f"We look forward to your active participation and involvement with SPAI.\n"
        f"Warm regards,\nProf. Anil Ramachandran\nSecretary, SPAI\nanilrkannuruniv.ac.in")

    sender_email = "SPAI Online <spai05138@gmail.com>"
    recipient_list = [user.email]
    context = {"name": f"{user.first_name} {user.last_name}", "reg_no": user.reg_no, "date": user.date_approved}
    template_path = 'pdf_template.html'
    pdf_content = render_to_pdf(template_path, context)

    if pdf_content:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=sender_email,
            to=recipient_list,
        )
        file_name = f"{user.first_name}_certificate.pdf"
        email.attach(file_name, pdf_content, "application/pdf")

        try:
            email.send()
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")
    else:
        print("Failed to generate PDF.")


def get_user_full_details(req, slug):
    user_data = {}
    user = User.objects.filter(slug_value=slug).first()
    if user is None:
        return redirect("index")
    user_dict = model_to_dict(user)
    user_data['email'] = user_dict.get("email", None)
    user_data['username'] = user_dict.get("username", None)
    user_data['first_name'] = user_dict.get("first_name", None)
    user_data['last_name'] = user_dict.get("last_name", None)
    user_data['state'] = user_dict.get("state", None)
    user_data['status'] = user_dict.get("status", None)
    user_data['slug_value'] = user_dict.get("slug_value", None)
    user_data['admin_approved'] = user_dict.get("admin_approved", None)
    user_data['next_step'] = get_next_step(user_dict.get("status", None))
    user_data['date_created'] = user.date_created
    user_data['admin_action'] = admin_action(user_dict.get("status", None))
    user_data['reg_no'] = user_dict.get("reg_no", None)
    user_data['active_key'] = user_dict.get("active_key", False)
    user_data['annual_subscription'] = user_dict.get("annual_subscription", False)
    user_data['executive'] = user_dict.get("executive", None)
    sec_msg = "Pending"
    pre_msg = "Pending"
    if user_dict.get("secretary_approval", False):
        sec_msg = "Done"
    if user_dict.get("president_approval", False):
        pre_msg = "Done"
    user_data['sec_msg'] = sec_msg
    user_data['pre_msg'] = pre_msg

    user_details = UserDetailModel.objects.filter(user=user.id).first()
    if user_details is not None:
        user_detail_dict = model_to_dict(user_details)
        user_data['degree'] = user_detail_dict.get("degree", None)
        user_data['profession'] = user_detail_dict.get("profession", None)
        user_data['institution'] = user_detail_dict.get("institution", None)
        user_data['department'] = user_detail_dict.get("department", None)
        user_data['address'] = user_detail_dict.get("address", None)
        user_data['phone_number'] = user_detail_dict.get("phone_number", None)
        user_data['alternate_number'] = user_detail_dict.get("alternate_number", None)
        user_data['alternate_mail'] = user_detail_dict.get("alternate_mail", None)
        user_data['photo'] = user_detail_dict.get("photo", None)
        user_data['specialized_in'] = user_detail_dict.get("specialized_in", None)
        user_data['research_interest'] = user_detail_dict.get("research_interest", None)
        user_data['payment'] = False

    payment_data = PaymentModel.objects.filter(user_info=user).order_by('-payment_reported_date').first()
    if payment_data is not None:
        payment_dict = model_to_dict(payment_data)
        user_data['payment'] = True
        user_data["transaction_id"] = payment_dict.get("transaction_id", None)
        user_data["reference_id"] = payment_dict.get("reference_id", None)
        user_data["bank_name"] = payment_dict.get("bank_name", None)
        p_t = payment_dict.get("payment_type", None)
        user_data["payment_type"] = settings.QR_CODE_NAME
        if p_t == settings.BANK_TRANSFER:
            user_data["payment_type"] = settings.BANK_TRANSFER_NAME
        if payment_dict.get("document", None).name == '':
            user_data["payment_doc"] = None
        else:
            user_data["payment_doc"] = payment_dict.get("document", None)
        user_data["payment_date"] = payment_data.payment_reported_date

        sub_pay = models.SubscriptionPayment.objects.filter(user=user).order_by('-payment_date').first()
        if sub_pay is not None:
            sub_dict = model_to_dict(sub_pay)
            user_data['sub_pay'] = True
            user_data["sub_transaction_id"] = sub_dict.get("transaction_id", None)
            user_data["sub_bank_name"] = sub_dict.get("bank_name", None)
            user_data["annual_payment_date"] = sub_pay.payment_date
            if sub_dict.get("document", None).name == '':
                user_data["payment_file"] = None
            else:
                user_data["payment_file"] = sub_dict.get("document", None)
        annual = models.AnnualSubscriptionModel.objects.filter(user=user).first()
        if annual is not None:
            annual_dict = model_to_dict(annual)
            user_data['annual'] = True
            user_data["start_date"] = annual_dict.get("date_created", None)
            user_data["end_date"] = annual_dict.get("end_date", None)

        key = False
        if req.user.is_authenticated:
            if req.user.user_role == settings.ADMIN_ROLE_VALUE and not user.admin_approved and user.approval_percentage == 100 and user.status in [
                settings.ADMIN_APPROVAL_PENDING, settings.EX_2_APPROVED]:
                key = True
            elif req.user.executive in [settings.SECRETARY, settings.PRESIDENT]:
                if req.user.executive == settings.SECRETARY:
                    if user.secretary_approval:
                        key = False  # Secretary approval is True, set key to False
                    else:
                        key = True  # Secretary approval is False, set key to True
                elif req.user.executive == settings.PRESIDENT:
                    if user.president_approval:
                        key = False  # President approval is True, set key to False
                    else:
                        key = True  # President approval is False, set key to True
                else:
                    # Existing conditions for executive roles
                    if (user.approval_percentage == 0 and user.status == settings.PAYMENT_DONE) or \
                            (user.approval_percentage == 50 and user.status in [settings.EX_2_APPROVAL_PENDING,
                                                                                settings.EX_1_APPROVED]):
                        key = True
                    elif user.approval_percentage == 100:
                        key = False
        user_data["key"] = key

    return user_data


@authenticated_only
def payment_model(request, *args, **kwargs):
    if request.user.is_authenticated and request.user.status == settings.PAYMENT_PENDING:
        slug = kwargs.get("slug", None)
        if request.user.slug_value != slug:
            return redirect("index")
        if request.method == 'POST':
            user = User.objects.filter(slug_value=slug).first()
            if not user:
                return redirect("login_page")
            form = forms.PaymentForm(request.user, request.POST, request.FILES)
            if form.is_valid():
                subcription_form = forms.SubscriptionPaymentForm(request.POST, request.FILES)
                if subcription_form.is_valid():
                    instance = subcription_form.save(commit=False)
                    instance.user = request.user
                    instance.save()
                form.save()
                user_status_change(request.user.slug_value, request.user.status)
                send_mail_to_executives(user, request.get_host())
                return redirect(
                    f"{reverse('success')}?message=Your application submitted successfully, your details are under validation. Thank you!")
        else:
            form = forms.PaymentForm(request.user)
        return render(request, 'members/payment_page.html', {'form': form})
    else:
        return redirect('individual_user_details', slug=request.user.slug_value)


def fee_and_payment(request):
    context = {}
    return render(request, 'members/fee_and_payment.html', context)


def unauthorized_page_403(request):
    return render(request, 'permission/403_page.html')


# rest API
@api_view(['POST'])
def create_or_update_life_member(request):
    api_key = request.headers.get('Authorization')
    if api_key != settings.USER_INGEST_KEY:
        return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
    data = {key: (value if value != "" else None) for key, value in request.data.items()}
    name = data.get('name')
    if name is None:
        name = data.get("email")
    data['name'] = name
    life_member = LifeMembers.objects.filter(name=name).first()
    if life_member:
        serializer = LifeMembersSerializer(life_member, data=data, partial=True)
        if serializer.is_valid():
            serializer.save(update_date=timezone.now())
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        serializer = LifeMembersSerializer(data=data)
        if serializer.is_valid():
            serializer.save(upload_date=timezone.now(), update_date=timezone.now())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


def life_members_get(request):
    life_members = LifeMembers.objects.all()
    all_members = User.objects.all()
    new_members = []
    active_members = []
    in_active_members = []
    for user in all_members:
        user_data = get_user_full_details(request, user.slug_value)
        new_members.append(user_data)
        if user_data['annual_subscription'] is True:
            active_members.append(user_data)
        else:
            in_active_members.append(user_data)

    # Add pagination for life_members
    paginator = Paginator(life_members, 20)
    page = request.GET.get('page')

    try:
        paginated_life_members = paginator.page(page)
    except PageNotAnInteger:
        paginated_life_members = paginator.page(1)
    except EmptyPage:
        paginated_life_members = paginator.page(paginator.num_pages)

    context = {
        'life_members': paginated_life_members,
        'new_members': new_members,
        'active': active_members,
        'non_active': in_active_members,
    }
    return render(request, 'members/life_members.html', context)


def life_member_info(request, *args, **kwargs):
    uid = kwargs.get("uid", None)
    context = {}
    user_data = LifeMembers.objects.get(uid=uid)
    context['user'] = user_data
    return render(request, 'members/life_member_details.html', context)


def internship_page(request):
    if request.method == 'POST':
        form = forms.InternshipApplicationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(
                f"{reverse('success')}?message=Your internship application submitted successfully. Thank you!")
        return redirect('index')
    else:
        form = forms.InternshipApplicationForm()
    return render(request, 'internship/internship.html', {'form': form})


def list_applications(request):
    context = {}
    applications = models.InternshipApplication.objects.all()
    context['applications'] = applications
    return render(request, 'internship/list_applications.html', context)


def research_paper_list(request):
    context = {}
    applications = models.Manuscript.objects.all()
    context['applications'] = applications
    return render(request, 'static_pages/publications/list_manuscripts.html', context)


def research_paper_retrieve(request, *args, **kwargs):
    pk = kwargs.get("pk", None)
    context = {}
    paper = models.Manuscript.objects.get(pk=pk)
    authors = models.Author.objects.filter(manuscript=paper)
    context['paper'] = paper
    context['authors'] = authors
    return render(request, 'static_pages/publications/view_research_paper.html', context)



@admin_only
def application_retrieve(request, *args, **kwargs):
    pk = kwargs.get("pk", None)
    if request.user.user_role == settings.ADMIN_ROLE_VALUE:
        context = {}
        user_data = models.InternshipApplication.objects.get(pk=pk)
        context['user'] = user_data
        return render(request, 'internship/view_applications.html', context)
    else:
        return redirect('login')


def call_for_manuscript(request):
    if request.method == 'POST':
        manuscript_form = forms.ManuscriptForm(request.POST, request.FILES)
        if manuscript_form.is_valid():
            manuscript = manuscript_form.save(commit=False)
            rp_no = get_research_paper_no()
            # print(rp_no)
            manuscript.paper_no = rp_no
            manuscript.save()

            author_names = request.POST.getlist('name[]')
            designations = request.POST.getlist('designation[]')
            organizations = request.POST.getlist('organization[]')
            emails = request.POST.getlist('email[]')
            mobiles = request.POST.getlist('mobile[]')

            authors = []
            for name, designation, organization, email, mobile in zip(author_names, designations, organizations, emails,
                                                                      mobiles):
                authors.append(models.Author(
                    manuscript=manuscript,
                    name=name,
                    designation=designation,
                    organization=organization,
                    email=email,
                    mobile=mobile
                ))
                # print(authors)
            models.Author.objects.bulk_create(authors)
            return redirect(
                f"{reverse('success')}?message=Your research paper application submitted successfully. Thank you!")
        manuscript_form = forms.ManuscriptForm()
        return render(request, 'static_pages/publications/manuscript.html', {'form': manuscript_form, 'page': 4})
    return render(request, 'static_pages/publications/manuscript.html', {'page': 4})


def search_view(request):
    query = request.GET.get('query', '')
    results = []
    if query:
        results = EventManagement.objects.filter(
            Q(title__icontains=query) | Q(location__icontains=query)
        )
    return render(request, 'mainpages/search_results.html', {'results': results, 'query': query})


def search_lm(request):
    query = request.GET.get('query', '')
    user_results = []
    lm_results = []
    if query:
        lm_results = LifeMembers.objects.filter(
            Q(reg_no__icontains=query) |
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(membership_date__icontains=query)
        )

        # Search in User model
        user_results = User.objects.filter(
            Q(reg_no__icontains=query) |
            Q(first_name__icontains=query) |
            Q(email__icontains=query) |
            Q(date_created__icontains=query) |
            Q(state__icontains=query)
        )
    return render(request, 'mainpages/lm_search_results.html',
                  {'user_results': user_results, 'lm_results': lm_results, 'query': query})


def success_page(request, *args, **kwargs):
    message = request.GET.get('message', '')
    return render(request, 'success.html', {"message": message})


def email_redirection(request):
    if request.method == 'POST':
        form = forms.ResetPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please check email address that you entered')
                return redirect('email_redirection')
            reset_request = models.PasswordResetRequest.objects.create(user=user, status=settings.EMAIL_SEND,
                                                                       date_created=datetime.now())
            send_password_reset_email(user, request.get_host())
            messages.success(request, "A password reset link sent to your email. it expires with in 10 minutes")
            return redirect('login_page')
    else:
        form = forms.ResetPasswordForm()
    return render(request, 'members/email_redirection.html', {'form': form})


def reset_password(request, *args, **kwargs):
    slug = kwargs.get("slug", "")
    context = {"slug": slug}
    user = get_object_or_404(User, slug_value=slug)
    tracker = models.PasswordResetRequest.objects.filter(user=user).order_by('-date_created').first()
    if tracker and tracker.status == settings.EMAIL_SEND:
        time_delta = timezone.now() - tracker.date_created  # Use timezone.now() instead of datetime.now()
        if time_delta > timedelta(seconds=600):
            messages.error(request, 'Your password reset link has expired')
            return redirect('login_page')
    else:
        messages.error(request, 'You already changed your password')
        return redirect('login_page')
    if request.method == 'POST':
        form = forms.PasswordSetFrom(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            user.set_password(password)
            tracker.status = settings.PASSWORD_RESET
            user.save()
            tracker.save()
            messages.success(request, 'Password changed successfully')
            return redirect('login_page')
        else:
            context["form"] = form
            return render(request, 'members/reset_password.html', context)
    else:
        form = forms.PasswordSetFrom()
        context["form"] = form
        return render(request, 'members/reset_password.html', context)


@authenticated_only
def annual_sub_payment(request, *args, **kwargs):
    if request.method == 'POST':
        # if not (request.user.slug_value == kwargs.get("slug", "") and request.user.status == settings.ADMIN_APPROVED and request.user.annual_subscription is False):
        #     return redirect('index')
        form = forms.SubscriptionPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.user = request.user
            payment.save()
            if not models.AnnualSubscriptionModel.objects.filter(user=request.user).exists():
                sub_obj = models.AnnualSubscriptionModel.objects.create(user=request.user, active=False)
            return redirect(
                f"{reverse('success')}?message=Your Annual subscription payment done, your details are under validation. Thank you!")
        else:
            return render(request, 'members/subscription_fee.html', {"form": form})
    else:
        form = forms.SubscriptionPaymentForm()
        return render(request, 'members/subscription_fee.html', {"form": form})


@admin_only
def annual_sub_approval(request, *args, **kwargs):
    slug = kwargs.get("slug", "")
    user = models.User.objects.get(slug_value=slug)
    annual_model = models.AnnualSubscriptionModel.objects.filter(user=user).first()
    if annual_model is None:
        return redirect('individual_user_details', slug=slug)
    # current = datetime.today()
    current = datetime.today().date()
    cutoff_date = datetime(2025, 4, 1, 0, 0, 0)
    cutoff_date_1 = cutoff_date.date()
    if current < cutoff_date_1:
        original_date = cutoff_date_1
    else:
        original_date = current
    annual_model.date_created = original_date
    annual_model.end_date = original_date + timedelta(days=365)
    annual_model.active = True
    user.annual_subscription = True
    annual_model.save()
    user.save()
    return redirect('individual_user_details', slug=slug)


def refresh_members(request, *args, **kwargs):
    update_subscription_status(request, True)
    return redirect('life_members_get')


@admin_only
def testimonials_list(request):
    published = Testimonials.objects.filter(publish=True).order_by('-date_created')
    non_published = Testimonials.objects.exclude(publish=True).order_by('-date_created')
    return render(request, 'members/testimonial_list.html', {'published': published, 'non_published': non_published})


def testimonial_create(request):
    if request.method == 'POST':
        form = forms.TestimonialForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = forms.TestimonialForm()
    return render(request, 'members/add_testimonials.html', {'form': form})


@admin_only
def approve_testimonial(request, *args, **kwargs):
    pk = kwargs.get('pk')
    obj = Testimonials.objects.filter(pk=pk).first()
    if obj is not None:
        obj.publish = True
        obj.save()
        return redirect('view_testimonials')
    return redirect('view_testimonials')


@admin_only
def delete_testimonial(request, *args, **kwargs):
    pk = kwargs.get('pk')
    obj = Testimonials.objects.filter(pk=pk).first()
    if obj is not None:
        obj.delete()
        return redirect('view_testimonials')
    return redirect('view_testimonials')


def contact_us(request):
    if request.method == 'POST':
        form = forms.ContactUsForm(request.POST)
        recaptcha_response = request.POST.get("g-recaptcha-response")
        res = recaptcha_verification(recaptcha_response)
        if not res:
            messages.error(request, "reCAPTCHA verification failed. Please try again.")
            return redirect('index')
        if form.is_valid():
            contact = form.save()
            send_contact_us_mail(contact)
            return redirect(
                f"{reverse('success')}?message=Our team will connect you soon. Thank you!")
        else:
            return redirect('index')
    return redirect('index')

@admin_only
def view_contact_us(request):
    contacts = models.ContactUs.objects.all()
    return render(request, 'members/view_contact_us.html', {'contacts': contacts})

@admin_only
def view_journal_queries(request):
    contacts = models.JournalQuery.objects.all()
    return render(request, 'static_pages/publications/view_journal_queries.html', {'contacts': contacts})

@admin_only
def upload_event_document(request,*args, **kwargs):
    if request.method == 'POST':
        event_id = kwargs.get('event_id')
        event = EventManagement.objects.get(id=event_id)
        form = forms.EventDocumentForm(request.POST, request.FILES)

        if form.is_valid():
            event_document = form.save(commit=False)
            event_document.event = event
            event_document.title = form.cleaned_data.get("title")
            event_document.save()
            return JsonResponse({'success': True, 'redirect_url': f'/news/{event_id}/'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})

    return JsonResponse({'success': False, 'error': 'Invalid request'})

@admin_only
def delete_event_document(request, document_id, event_id):
    if request.method == 'POST':
        document = get_object_or_404(models.EventDocumentModel, id=document_id)
        document.delete()
        return redirect('news_detail', pk=event_id)
    return redirect('news_detail', pk=event_id)


def manuscript_search(request):
    query = request.GET.get('query', '')
    results = []
    if query:
        results = models.Manuscript.objects.filter(
            Q(title__icontains=query) | Q(keywords__icontains=query) | Q(research_area__icontains=query)
        )
    return render(request, 'static_pages/publications/search_manuscript.html', {'results': results, 'query': query})


# user ingestion API

class BulkDataIngestionAPIView(APIView):
    def post(self, request):
        api_key = request.headers.get('Authorization')
        if api_key != settings.USER_INGEST_KEY:
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        with transaction.atomic():
            try:
                # Check if User already exists
                user = User.objects.filter(email=data.get('email')).first()
                if user:
                    user.status = settings.ADMIN_APPROVED
                    user.user_role = settings.MEMBER_ROLE_VALUE
                    user.admin_approved = True
                    if user.date_approved is None:
                        cutoff_date = datetime(2025, 4, 1, 0, 0, 0)
                        if datetime.now() < cutoff_date:
                            user.date_approved = cutoff_date
                        else:
                            user.date_approved = datetime.now()
                    user.approval_percentage = 100
                    user.active_key = True
                    user.president_approval = True
                    user.secretary_approval = True
                    if user.original_date_approved is None:
                        user.original_date_approved = datetime.now()
                    if user.reg_no is None:
                        user.reg_no = get_registration_num()
                    user.save()
                    user_message = "User already exists."
                else:
                    # Create User instance
                    user_data = {
                        'email': data.get('email', f"user{datetime.now().timestamp()}@example.com"),
                        'username': data.get('username', f"user{datetime.now().timestamp()}"),
                        'first_name': data.get('first_name', 'John'),
                        'last_name': data.get('last_name', 'Doe'),
                        'state': data.get('state', 'None'),
                        'annual_subscription': data.get('annual_subscription', False)
                    }
                    user_serializer = UserSerializer(data=user_data)
                    user_serializer.is_valid(raise_exception=True)
                    user = user_serializer.save()
                    user_message = "User created successfully."

                # Check if UserDetailModel already exists
                user_detail = UserDetailModel.objects.filter(user=user).first()
                if user_detail:
                    user_detail_message = "UserDetail already exists."
                else:
                    # Create UserDetailModel instance
                    address = f"{data.get('house_name', 'Unknown')} {data.get('street_name', 'Unknown')} {data.get('city_name', 'Unknown')} {data.get('pin', '000000')}"
                    user_detail_data = {
                        'user': user.pk,
                        'degree': data.get('degree', 'Unknown'),
                        'profession': data.get('profession', 'Unknown'),
                        'institution': data.get('institution', 'Unknown'),
                        'department': data.get('department', 'Unknown'),
                        'address': address,
                        'phone_number': data.get('phone_number', '0000000000'),
                        'alternate_number': data.get('alternate_phone_number', None),
                        'alternate_mail': data.get('alternate_email', None),
                        'specialized_in': data.get('specialized_in', 'None'),
                        'research_interest': data.get('research_interest', 'None'),
                    }
                    user_detail_serializer = UserDetailSerializer(data=user_detail_data)
                    user_detail_serializer.is_valid(raise_exception=True)
                    user_detail_serializer.save()
                    user_detail_message = "UserDetail created successfully."

                # Check if PaymentModel already exists
                payment = PaymentModel.objects.filter(user_info=user).first()
                if payment:
                    payment_message = "Payment record already exists."
                else:
                    # Create PaymentModel instance
                    payment_data = {
                        'user_info': user.pk,
                        'transaction_id': f"TXN{datetime.now().timestamp()}",
                        'reference_id': f"REF{datetime.now().timestamp()}",
                        'bank_name': 'Demo Bank',
                        'payment_type': 1,
                        'document': None
                    }
                    payment_serializer = PaymentSerializer(data=payment_data)
                    payment_serializer.is_valid(raise_exception=True)
                    payment_serializer.save()
                    payment_message = "Payment record created successfully."

                # Check if SubscriptionPayment already exists
                if data.get('annual_subscription', False):
                    subscription_payment = SubscriptionPayment.objects.filter(user=user).first()
                    if subscription_payment:
                        subscription_payment_message = "Subscription payment already exists."
                    else:
                        # Create SubscriptionPayment instance
                        subscription_payment_data = {
                            'user': user.pk,
                            'transaction_id': f"SUBTXN{datetime.now().timestamp()}",
                            'bank_name': 'Demo Bank',
                            'document': None
                        }
                        subscription_payment_serializer = SubscriptionPaymentSerializer(data=subscription_payment_data)
                        subscription_payment_serializer.is_valid(raise_exception=True)
                        subscription_payment_serializer.save()
                        subscription_payment_message = "Subscription payment created successfully."
                else:
                    subscription_payment_message = "Subscription payment not applicable."
                # Check if AnnualSubscriptionModel already exists
                annual_subscription = AnnualSubscriptionModel.objects.filter(user=user).first()
                if data.get('annual_subscription', False):
                    if annual_subscription:
                        annual_subscription_message = "Annual subscription already exists."
                    else:
                        end_date_str = data.get('end_date', None)
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                        annual_sub_data = {
                            'user': user.pk,
                            'date_created': end_date - timedelta(days=365),
                            'end_date': end_date,
                            'active': True
                        }
                        annual_subscription_serializer = AnnualSubscriptionSerializer(data=annual_sub_data)
                        annual_subscription_serializer.is_valid(raise_exception=True)
                        annual_subscription_serializer.save()
                        annual_subscription_message = "Annual subscription created successfully."
                else:
                    annual_subscription_message = "Annual subscription not applicable."

                # Final response
                return Response({
                    "user_message": user_message,
                    "user_detail_message": user_detail_message,
                    "payment_message": payment_message,
                    "subscription_payment_message": subscription_payment_message,
                    "annual_subscription_message": annual_subscription_message
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def journal_queries(request):
    if request.method == 'POST':
        form = forms.JournalQueryForm(request.POST)
        if form.is_valid():
            journal = form.save()
            send_contact_us_mail(journal, True)
            return redirect(
                f"{reverse('success')}?message=Our team will connect you soon. Thank you!")
    return redirect('index')


@csrf_exempt
@login_required
def profile_upload_photo(request):
    if request.method == 'POST' and request.FILES.get('photo'):
        user = request.user
        photo = request.FILES['photo']

        try:
            user_details = UserDetailModel.objects.get(user=user)
            user_details.photo.save(photo.name, photo)
            user_details.save()
            return JsonResponse({'message': 'Photo updated successfully!'})
        except UserDetailModel.DoesNotExist:
            return JsonResponse({'error': 'UserDetails instance not found.'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)


def get_nearest_event():
    nearest_events = BannerEvents.objects.all()[:3]
    if not nearest_events:
        return [{"title":"Sports Psychology", "location":"Association of India", "link":reverse('user_registration')}]
    event_data = []
    for event in nearest_events:
        event_data.append({"title":event.event.title, "location":event.event.location, "link":reverse('news_detail', kwargs={'pk': event.event.id})})
    return event_data


@admin_only
def user_role_switch(request, *args, **kwargs):
    slug = kwargs.get("slug", "")
    user = User.objects.filter(slug_value=slug, active_key=True).first()
    if user is None:
        return redirect('individual_user_details', slug=slug)

    key = request.GET.get('key')
    if key == 'promote':
        user.executive = settings.EXECUTIVE
    elif key == 'demote':
        user.executive = None
    else:
        pass
    user.save()
    return redirect('individual_user_details', slug=user.slug_value)