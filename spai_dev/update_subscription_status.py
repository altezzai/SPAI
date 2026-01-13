"""
Script to update subscription_status and subscription_count for all existing users
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spai_dev.settings')
django.setup()

from spai_app.models import User, AnnualSubscriptionModel
from django.utils import timezone

def update_all_users():
    users = User.objects.all()
    total = users.count()
    updated = 0
    
    print(f"Processing {total} users...")
    
    for user in users:
        # Get the user's subscription records
        subscription = user.annual_sub.order_by('-end_date').first()
        
        # Determine subscription_status
        if not user.admin_approved:
            # User not approved yet
            user.subscription_status = "Not Active"
            user.subscription_count = 0
        elif subscription:
            # User has subscription record
            current_date = timezone.now().date()
            
            # Handle subscriptions with no end_date (incomplete data)
            if not subscription.end_date:
                user.subscription_status = "Renewal Pending Approval"
                user.subscription_count = user.annual_sub.count()
            elif subscription.active and subscription.end_date >= current_date:
                # Active subscription
                user.subscription_status = "Active"
                # Count how many subscription records exist
                user.subscription_count = user.annual_sub.count()
            elif subscription.end_date < current_date:
                # Expired subscription
                user.subscription_status = "Renew Subscription"
                user.subscription_count = user.annual_sub.count()
            else:
                # Inactive subscription (might be pending approval)
                user.subscription_status = "Renewal Pending Approval"
                user.subscription_count = user.annual_sub.count()
        else:
            # User approved but no subscription record (shouldn't happen but handle it)
            user.subscription_status = "Not Active"
            user.subscription_count = 0
        
        # Update annual_subscription field to match
        if user.subscription_status == "Active":
            user.annual_subscription = True
        else:
            user.annual_subscription = False
        
        user.save()
        updated += 1
        
        if updated % 10 == 0:
            print(f"Updated {updated}/{total} users...")
    
    print(f"\n✓ Successfully updated {updated} users!")
    
    # Print summary
    print("\n--- Summary ---")
    print(f"Not Active: {User.objects.filter(subscription_status='Not Active').count()}")
    print(f"Active: {User.objects.filter(subscription_status='Active').count()}")
    print(f"Renew Subscription: {User.objects.filter(subscription_status='Renew Subscription').count()}")
    print(f"Renewal Pending Approval: {User.objects.filter(subscription_status='Renewal Pending Approval').count()}")

if __name__ == "__main__":
    update_all_users()
