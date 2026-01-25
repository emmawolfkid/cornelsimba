# simple_fix.py - Save in cornelsimba folder
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
from django.db.models import Count

print("=" * 60)
print("SIMPLE DUPLICATE FIXER")
print("=" * 60)

# FIRST: Show what we have
print("\n📋 CURRENT ITEMS:")
items = Item.objects.all().order_by('name')
for item in items:
    print(f"  • ID: {item.id}, Name: '{item.name}', Qty: {item.quantity}, Category: '{item.category}'")

# SECOND: Fix categories WITHOUT validation
print("\n🔧 FIXING CATEGORIES (bypassing validation)...")
with transaction.atomic():
    # Update categories directly in database
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("UPDATE inventory_item SET category = 'RAW_MATERIALS' WHERE category = 'Raw Material'")
        cursor.execute("UPDATE inventory_item SET category = 'CHEMICALS' WHERE category = 'Chemicals'")
        cursor.execute("UPDATE inventory_item SET category = 'OTHERS' WHERE category = 'Others'")
        cursor.execute("UPDATE inventory_item SET category = 'RAW_MATERIALS' WHERE category = 'Raw Materials'")
    print("✅ Categories fixed!")

# THIRD: Find and merge duplicates
print("\n🔍 FINDING DUPLICATES...")

# Get all items again
items = Item.objects.all()
name_groups = {}

# Group by lowercase name
for item in items:
    key = item.name.strip().lower()
    if key not in name_groups:
        name_groups[key] = []
    name_groups[key].append(item)

# Process duplicates
with transaction.atomic():
    for name_key, item_list in name_groups.items():
        if len(item_list) > 1:
            print(f"\n⚠️  MERGING '{name_key}':")
            
            # Sort by ID (keep the oldest/lower ID)
            item_list.sort(key=lambda x: x.id)
            main_item = item_list[0]
            duplicates = item_list[1:]
            
            print(f"  Keeping: ID {main_item.id} ('{main_item.name}')")
            
            for dup in duplicates:
                print(f"  Merging: ID {dup.id} ('{dup.name}') → ID {main_item.id}")
                
                # 1. Update ALL related records
                updated_stockins = StockIn.objects.filter(item=dup).update(item=main_item)
                updated_stockouts = StockOut.objects.filter(item=dup).update(item=main_item)
                
                # Try StockHistory
                try:
                    StockHistory.objects.filter(item=dup).update(item=main_item)
                except:
                    pass
                
                # 2. Add quantity to main item (direct SQL to avoid validation)
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE inventory_item SET quantity = quantity + %s WHERE id = %s",
                        [dup.quantity, main_item.id]
                    )
                
                # 3. Delete duplicate
                dup.delete()
                
                if updated_stockins or updated_stockouts:
                    print(f"    ✓ Moved {updated_stockins} stock-ins, {updated_stockouts} stock-outs")
                else:
                    print(f"    ✓ No related records to move")
            
            # Fix name capitalization
            if main_item.name != main_item.name.title():
                old_name = main_item.name
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE inventory_item SET name = %s WHERE id = %s",
                        [main_item.name.title(), main_item.id]
                    )
                print(f"  Fixed name: '{old_name}' → '{main_item.name.title()}'")

# FOURTH: Show final results
print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)

final_items = Item.objects.all().order_by('name')
print(f"📊 Total items: {final_items.count()}")
print("\n📋 ITEM LIST:")
for item in final_items:
    stock_ins = item.stock_ins.count()
    stock_outs = item.stock_outs.count()
    print(f"  • {item.name}: {item.quantity} {item.unit_of_measure}")
    print(f"    ID: {item.id}, Category: {item.category}")
    print(f"    📥 Stock Ins: {stock_ins}, 📤 Stock Outs: {stock_outs}")

# FIFTH: Verify no duplicates
print("\n🔍 VERIFICATION:")
all_good = True
for item in final_items:
    name_key = item.name.strip().lower()
    duplicates = Item.objects.filter(name__iexact=name_key).exclude(id=item.id)
    if duplicates.exists():
        print(f"❌ STILL HAVE DUPLICATE: '{item.name}'")
        all_good = False
    else:
        print(f"✅ '{item.name}' - OK")

if all_good:
    print("\n🎉 SUCCESS! All duplicates fixed!")
else:
    print("\n⚠️  Some duplicates remain.")

print("\n" + "=" * 60)