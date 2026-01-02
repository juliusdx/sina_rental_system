
from app import create_app
from models import db, Property, PropertyExpense
from datetime import date

app = create_app()

def verify():
    with app.app_context():
        # Get a property
        prop = Property.query.first()
        if not prop:
            print("No properties found to test.")
            return

        print(f"Testing with Property: {prop.unit_number} (ID: {prop.id})")
        
        # 1. Create Expense
        print("Creating Expense...")
        exp = PropertyExpense(
            property_id=prop.id,
            expense_type='quit_rent',
            amount=123.45,
            description="Test Expense",
            bill_date=date.today(),
            gl_code="8888"
        )
        db.session.add(exp)
        db.session.commit()
        print(f"Expense Created: ID {exp.id}")
        
        # 2. Retrieve
        print("Retrieving Expense...")
        retrieved = PropertyExpense.query.get(exp.id)
        if retrieved and retrieved.amount == 123.45:
            print(" -> Success: Data matches.")
        else:
            print(" -> Failed: Data verification failed.")
            
        # 3. Mark Paid
        print("Marking Paid...")
        retrieved.paid_by_company = True
        retrieved.payment_date = date.today()
        db.session.commit()
        
        # 4. Verify Relationship
        print(f"Property has {len(prop.expenses)} expenses.")
        if len(prop.expenses) >= 1:
            print(" -> Success: Relationship works.")
            
        # 5. Clean Up
        print("Deleting Test Expense...")
        db.session.delete(retrieved)
        db.session.commit()
        print("Cleanup Complete.")

if __name__ == "__main__":
    verify()
