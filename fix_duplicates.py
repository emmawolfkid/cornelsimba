# fix_duplicates.py - Save this in cornelsimba folder (same as manage.py)
import os
import django
import sys

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cornelsimba.settings')
django.setup()

from inventory.models import Item, StockIn, StockOut, StockHistory
from django.db import transaction
from django.core.exceptions import ValidationError

def fix_all_duplicates():
    print("=" * 70)
    print("COMPLETE DUPLICATE ITEM FIXER")
    print("=" * 70)
    
    # First, fix any category issues
    print("🔧 Fixing category values...")
    category_mapping = {
        'Raw Material': 'RAW_MATERIALS',
        'Raw Materials': 'RAW_MATERIALS',
        'RAW MATERIAL': 'RAW_MATERIALS',
        'raw materials': 'RAW_MATERIALS',
        'Chemicals': 'CHEMICALS',
        'Chemical': 'CHEMICALS',
        'CHEMICAL': 'CHEMICALS',
        'chemicals': 'CHEMICALS',
        'Others': 'OTHERS',
        'Other': 'OTHERS',
        'other': 'OTHERS',
        'OTHERS': 'OTHERS',
    }
    
    items_updated = 0
    for item in Item.objects.all():
        original_category = item.category
        if original_category in category_mapping:
            item.category = category_mapping[original_category]
            item.save()
            items_updated += 1
            print(f"   Fixed category: '{original_category}' → '{item.category}' for '{item.name}'")
    
    print(f"✅ Fixed {items_updated} items with incorrect categories")
    
    # Get all items after category fix
    all_items = Item.objects.all()
    print(f"📊 Total items in database: {all_items.count()}")
    
    # Group by lowercase name
    items_dict = {}
    for item in all_items:
        clean_name = item.name.strip().lower()
        if clean_name not in items_dict:
            items_dict[clean_name] = []
        items_dict[clean_name].append(item)
    
    print(f"🔍 Found {len(items_dict)} unique item names (case-insensitive)")
    print("-" * 70)
    
    # Process each group
    with transaction.atomic():
        items_fixed = 0
        items_deleted = 0
        
        for base_name, item_list in items_dict.items():
            if len(item_list) > 1:
                print(f"\n⚠️  DUPLICATES FOUND for '{base_name}':")
                for i, item in enumerate(item_list, 1):
                    print(f"   {i}. '{item.name}' (ID: {item.id}, Stock: {item.quantity}, Category: {item.category})")
                
                # Find best item to keep
                main_item = None
                
                # Strategy: Keep the one with proper name formatting
                for item in item_list:
                    if item.name == item.name.title() and item.name == item.name.strip():
                        main_item = item
                        break
                
                # If not found, use item with most stock
                if not main_item:
                    main_item = max(item_list, key=lambda x: x.quantity)
                
                # If still not found, use oldest
                if not main_item:
                    main_item = min(item_list, key=lambda x: x.created_at)
                
                print(f"\n   ✅ Keeping: '{main_item.name}' (ID: {main_item.id})")
                
                # Merge all duplicates into main item
                for duplicate in item_list:
                    if duplicate.id == main_item.id:
                        continue
                    
                    print(f"   🔄 Merging: '{duplicate.name}' → '{main_item.name}'")
                    
                    # Update all related records
                    StockIn.objects.filter(item=duplicate).update(item=main_item)
                    StockOut.objects.filter(item=duplicate).update(item=main_item)
                    
                    try:
                        StockHistory.objects.filter(item=duplicate).update(item=main_item)
                    except:
                        pass
                    
                    # Add quantities
                    old_qty = main_item.quantity
                    main_item.quantity += duplicate.quantity
                    print(f"      📦 Stock: {old_qty} + {duplicate.quantity} = {main_item.quantity}")
                    
                    # Delete duplicate
                    duplicate.delete()
                    items_deleted += 1
                    print(f"      🗑️  Deleted duplicate item")
                
                # Fix main item name if needed
                if main_item.name != main_item.name.title():
                    old_name = main_item.name
                    main_item.name = main_item.name.title()
                    print(f"   ✏️  Fixed name: '{old_name}' → '{main_item.name}'")
                
                # Save the main item
                try:
                    main_item.save()
                    print(f"   💾 Saved main item successfully")
                    items_fixed += 1
                except ValidationError as e:
                    print(f"   ❌ Error saving item: {e}")
                    # Try to fix any validation issues
                    for field, errors in e.message_dict.items():
                        print(f"      Field '{field}': {errors}")
            
            else:
                # Single item - just fix its name
                item = item_list[0]
                original_name = item.name
                fixed_name = item.name.strip().title()
                
                if original_name != fixed_name:
                    print(f"\n✏️  Fixing capitalization: '{original_name}' → '{fixed_name}'")
                    item.name = fixed_name
                    try:
                        item.save()
                        items_fixed += 1
                        print(f"   ✅ Fixed successfully")
                    except ValidationError as e:
                        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("FIX SUMMARY")
    print("=" * 70)
    print(f"✅ Items fixed/merged: {items_fixed}")
    print(f"🗑️  Duplicate items deleted: {items_deleted}")
    print(f"📊 Total items after fix: {Item.objects.count()}")
    
    # Final verification
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    remaining_items = Item.objects.all().order_by('name')
    all_good = True
    
    for item in remaining_items:
        duplicates = Item.objects.filter(name__iexact=item.name.strip().lower()).exclude(id=item.id)
        
        if duplicates.exists():
            print(f"❌ STILL HAVE ISSUE with '{item.name}':")
            for dup in duplicates:
                print(f"   - Duplicate: '{dup.name}' (ID: {dup.id})")
            all_good = False
        else:
            print(f"✅ '{item.name}' (ID: {item.id}, Stock: {item.quantity}, Category: {item.category})")
    
    if all_good:
        print("\n🎉 ALL ITEMS FIXED SUCCESSFULLY!")
    else:
        print("\n⚠️  Some issues remain.")
    
    # Show final list
    print("\n" + "=" * 70)
    print("FINAL ITEM LIST")
    print("=" * 70)
    for item in remaining_items:
        stock_ins = item.stock_ins.count()
        stock_outs = item.stock_outs.count()
        print(f"• {item.name}: {item.quantity} {item.unit_of_measure} (ID: {item.id})")
        print(f"  📥 Stock Ins: {stock_ins}, 📤 Stock Outs: {stock_outs}")

if __name__ == "__main__":
    fix_all_duplicates()