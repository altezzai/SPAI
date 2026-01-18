from datetime import datetime
from io import BytesIO
from time import timezone

from django.utils import timezone as tmz

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import User, Manuscript, AnnualSubscriptionModel, SubscriptionPayment


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return result.getvalue()
    return None


def get_registration_num():
    reg_no = "SPAILM"
    year = datetime.now().year
    reg_no = reg_no + str(year)
    user = User.objects.filter(admin_approved=True, user_role=2).order_by('-original_date_approved').first()
    if user and user.reg_no is not None:
        reg = user.reg_no
        reg = reg[10:]
        reg = int(reg) + 1
        reg_no = reg_no + str(reg)
    else:
        reg_no = reg_no + "1"
    return reg_no


def get_research_paper_no():
    num = "SPAIRP"
    year = datetime.now().year
    num = num + str(year)
    rp = Manuscript.objects.all().order_by('-date_created').first()
    if rp and rp.paper_no is not None:
        n = rp.paper_no
        n = n[10:]
        n = int(n) + 1
        num = num + str(n)
    else:
        num = num + "1"
    return num


def send_mail_to_executives(user, host):
    executives = User.objects.filter(executive__in=[settings.SECRETARY, settings.PRESIDENT])
    if executives:
        executive_emails = [user.email for user in executives]
        subject = "Notification of Registration Completion"
        link = f"{host}/user/detail/{user.slug_value}"
        message = (
            f"\nDear  Secretary / President SPAI,\n"
            f"The registration process for {user.first_name} {user.last_name} ({user.email}) has been successfully completed. All required information and documentation have been submitted and verified according to the guidelines.\n"
            f" Kindly verify and approve the same for further processing from the admin side for certificate generation.\n"
            f" Kind regards\n"
            f"Admin, SPAI\n"
            f"Click on the link to view profile {link}"
        )

        sender_email = "SPAI Online <spai05138@gmail.com>"
        recipient_list = executive_emails

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=sender_email,
            to=recipient_list,
        )
        try:
            email.send()
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")

def send_password_reset_email(user, host):
    link=f'{host}/reset/password/{user.slug_value}'
    message = (
        f"Dear {user.first_name} {user.last_name},\n"
        f"Your password reset link is given below, click to reset your password.\n"
        f"Password registration link : {link}"
    )
    subject = "Reset Your Password"
    sender_email = "SPAI Online <spai05138@gmail.com>"
    recipient_list = [user.email]

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=sender_email,
        to=recipient_list,
    )
    try:
        email.send()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def update_subscription_status(request, bulk):
    current_date = tmz.localdate()
    if bulk:
        subscriptions = AnnualSubscriptionModel.objects.filter(end_date__lt=current_date)
        for sub in subscriptions:
            
            sub.user.annual_subscription = False
            latest_payment = SubscriptionPayment.objects.filter(user=sub.user).order_by('-payment_date').first()
            if latest_payment and latest_payment.document and sub.end_date and latest_payment.payment_date >= sub.end_date:
                sub.user.subscription_status = "Renewal Pending Approval"
            else:
                sub.user.subscription_status = "Renew Subscription"
            sub.active = False
            sub.save()
            sub.user.save()
    else:
        sub = AnnualSubscriptionModel.objects.filter(end_date__lt=current_date, user=request.user).first()
        if sub is not None:
            sub.user.annual_subscription = False
            latest_payment = SubscriptionPayment.objects.filter(user=sub.user).order_by('-payment_date').first()
            if latest_payment and latest_payment.document and sub.end_date and latest_payment.payment_date >= sub.end_date:
                sub.user.subscription_status = "Renewal Pending Approval"
            else:
                sub.user.subscription_status = "Renew Subscription"
            sub.active = False
            sub.save()
            sub.user.save()

def send_contact_us_mail(contact, journal=False):
    message = (
        f"Hi Secretary and President,\n"
        f"You have enquiry from {contact.name}\n"
        f"Name: {contact.name}\n"
        f"Email: {contact.email}\n"
        f"Phone: {contact.phone}\n"
        f"Query: {contact.message}\n"
    )
    if journal:
        subject = f"Enquiry About Journal {contact.name}"
    else:
        subject = f"Enquiry from {contact.name}"
    sender_email = "SPAI Online <spai05138@gmail.com>"
    recipient_list = [settings.SECRETARY_EMAIL, settings.PRESIDENT_EMAIL]

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=sender_email,
        to=recipient_list,
    )
    try:
        email.send()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")