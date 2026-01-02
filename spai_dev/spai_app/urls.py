from tkinter.font import names

from django.urls import path  # type: ignore
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('history/', views.history, name="history"),
    path('about_members/', views.about_members, name="about_members"),
    path('gallery/', views.gallery_list, name="gallery_list"),

    path('gallery/<int:pk>/', views.gallery_detail, name='gallery_detail'),
    path('gallery/create/', views.gallery_create, name='gallery_create'),
    path('gallery/delete/<int:pk>/', views.gallery_delete, name='gallery_delete'),
    path('gallery/image/delete/<int:image_id>/', views.delete_gallery_image, name='delete_gallery_image'),
    path('gallery/image/add/<int:gallery_id>/', views.add_gallery_image, name='add_gallery_image'),

    path('news/', views.news, name="news"),
    path('news/<int:pk>/', views.news_detail, name="news_detail"),
    path('events/delete/<int:event_id>/', views.delete_event, name='event_delete'),
    path('eventadd/', views.eventadd, name="eventadd"),
    path('update_reg_link/<pk>', views.update_reg_link, name="update_reg_link"),
    path('add_image_template/', views.add_image_template, name="add_image_template"),
    path('upload-photo/', views.profile_upload_photo, name='upload_photo'),

    # latest URLs
    path('user/login', views.user_login_page, name='login_page'),
    path('user/registration/', views.user_registration, name='user_registration'),
    path('renew/', views.renew, name="renew"),
    path('user/profile/details/', views.user_profile_details, name='user_profile_details'),
    path('members/', views.members, name="members"),
    path('logout/', views.user_logout, name='logout'),
    path('user/detail/<str:slug>', views.user_details_vew, name='individual_user_details'),
    path('user/executive/approve/<str:slug>', views.admin_approval, name='user_approval'),
    path('certificate/<str:slug>', views.certificate, name='certificate'),
    path('get/life-members', views.life_members_get, name='life_members_get'),
    path('get/life-member/<str:uid>', views.life_member_info, name='life_member_info'),
    path('join-internship/', views.internship_page, name='internship_page'),
    path('list/applications/', views.list_applications, name='list_applications'),
    path('get/<int:pk>/application', views.application_retrieve, name='application_retrieve'),
    path('publications/manuscript', views.call_for_manuscript, name='call_for_manuscript'),
    path('publications/manuscripts/list', views.research_paper_list, name='list_manuscripts'),
    path('publications/manuscripts/<int:pk>/get', views.research_paper_retrieve, name='research_paper_retrieve'),
    path('annual-subscription/payment/<str:slug>', views.annual_sub_payment, name='annual_sub_payment'),
    path('annual-subscription/<str:slug>/approval', views.annual_sub_approval, name='subscription_approval'),
    path('refresh/members', views.refresh_members, name='refresh_members'),
    path('user/role/<str:slug>/switch', views.user_role_switch, name="user_role_switch"),

    path('user/payment/<str:slug>', views.payment_model, name='payment_model'),
    path('payment/info', views.fee_and_payment, name='fee_and_payment'),
    path('search/', views.search_view, name='search'),
    path('lm/search', views.search_lm, name='search_lm'),
    path('email/forgot/passcode', views.email_redirection, name='email_redirection'),
    path('reset/password/<str:slug>', views.reset_password, name='reset_password'),
    path('upload/testimonials', views.testimonial_create, name='upload_testimonials'),
    path('view/testimonials', views.testimonials_list, name='view_testimonials'),
    path('approve/<int:pk>/testimonial', views.approve_testimonial, name='approve_testimonial'),
    path('delete/<int:pk>/testimonial', views.delete_testimonial, name='delete_testimonial'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('view/contact-us/', views.view_contact_us, name='view_contact_us'),
    path('journals/query', views.journal_queries, name='journal_queries'),
    path('view/journal/queries', views.view_journal_queries, name='view_journal_query'),
    path('journal/search/', views.manuscript_search, name='manuscript_search'),

    path('about', views.about_page, name='about_page'),
    path('add_testimonals', views.add_testimonals, name='add_testimonals'),
    path('membership', views.membership, name='membership'),
    path('publications', views.publications, name='publications'),
    path('academic', views.academic, name='academic'),
    path('unauthorized/403/', views.unauthorized_page_403, name='unauthorized_403'),
    path('success/', views.success_page, name='success'),
    path('upload_event_document/<int:event_id>/', views.upload_event_document, name='upload_event_document'),
    path('delete_event_document/<int:document_id>/<int:event_id>/', views.delete_event_document,
         name='delete_event_document'),

    # rest api
    path('life-members', views.create_or_update_life_member, name='life-members'),
    path('user/data/ingestion', views.BulkDataIngestionAPIView.as_view())

]
