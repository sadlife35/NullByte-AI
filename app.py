import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF
import io
from faker import Faker
import random
import openpyxl
import re
from datetime import datetime
from datetime import timedelta


# Initialize Faker
fake = Faker()

# Application Details
APP_NAME = "NullByte AI"
APP_TAGLINE = "Synthetic Data Generator"

# Configure Streamlit page
st.set_page_config(
    page_title=f"{APP_NAME} - {APP_TAGLINE}", 
    page_icon="🔬",  # A science/tech icon to represent data generation
    layout="wide"
)

# PII Fields to Detect
PII_FIELDS = ['Name', 'Email', 'Phone', 'Address', 'SSN']
DPDP_PII_FIELDS = ['Phone', 'Aadhaar', 'PAN', 'Passport', 'Voter ID']  # DPDP-specific identifiers
AUTO_MASK_KEY = "auto_mask_pii"  # Key for session state

# ---- Header ----
st.title(f"{APP_NAME}: {APP_TAGLINE}")
st.markdown(f"*Generate AI-ready, bias-checked, privacy-compliant synthetic datasets in minutes.*")

# Add a brief app description
st.markdown("""
<style>
.highlight-box {
    background-color: #black;
    border-left: 5px solid #4e8098;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 20px;
}
.dpdp-warning {
    background-color: #fff3cd;
    border-left: 5px solid #ffc107;
    padding: 5px;
    border-radius: 3px;
    margin: 5px 0;
    font-size: 0.9em;
}
.indian-id {
    font-family: monospace;
    background-color: #f8f9fa;
    padding: 2px 4px;
    border-radius: 3px;
}
</style>
<div class="highlight-box">
**About NullByte AI**<br>
NullByte AI helps data scientists, researchers, solo entreprenuers and businesses create privacy-preserving synthetic datasets 
with advanced bias detection and ethical compliance checks.
</div>
""", unsafe_allow_html=True)

# Text Input for Dataset Description
prompt = st.text_input("Describe the dataset you want (e.g., '10 rows of employee data with name, age, salary, email')")

# Reproducibility Option
use_fixed_seed = st.checkbox("Use fixed random seed for reproducible dataset")

# Field type definitions
FIELD_TYPES = {
    "string": "Text String",
    "email": "Email Address",
    "int": "Integer Number",
    "float": "Decimal Number",
    "date": "Date",
    "category": "Category/Enum",
    "phone": "Phone Number",
    "address": "Address",
    "name": "Full Name",
    "aadhaar": "Aadhaar Number",
    "pan": "PAN Number",
    "passport": "Passport Number",
    "voterid": "Voter ID",
    "ifsc": "IFSC Code",
    "upi": "UPI ID"
}

def is_dpdp_pii(field_name):
    """Check if a field name matches DPDP-sensitive PII."""
    field_lower = field_name.lower()
    return (
        'phone' in field_lower or 
        'aadhaar' in field_lower or 
        'pan' in field_lower or 
        'passport' in field_lower or 
        'voter' in field_lower or
        'ifsc' in field_lower or
        'upi' in field_lower
    )

def mask_pii(value, field_type):
    """Mask PII data according to field type."""
    if pd.isna(value) or value == "":
        return value
    
    if field_type == "phone":
        if len(str(value)) >= 4:
            return f"XXXXXX{str(value)[-4:]}"
        return "XXXXXX"
    elif field_type in ["aadhaar", "pan", "passport", "voterid", "ifsc", "upi"]:
        if len(str(value)) >= 4:
            return f"XXXXXX{str(value)[-4:]}"
        return "XXXXXX"
    elif field_type == "email":
        parts = str(value).split('@')
        if len(parts) == 2:
            return f"{parts[0][0]}***@{parts[1]}"
        return "***@***"
    return value

def validate_constraint(field_type, constraint):
    """Validate if the constraint is valid for the given field type."""
    if field_type in ["int", "float"]:
        # Check if constraint is in format "min-max"
        pattern = r"^\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$"
        match = re.match(pattern, constraint)
        if match:
            min_val, max_val = match.groups()
            try:
                min_val = float(min_val)
                max_val = float(max_val)
                return min_val != max_val
            except ValueError:
                return False
        return False
    elif field_type == "date":
        # Check if constraint is in format "YYYY-MM-DD - YYYY-MM-DD"
        pattern = r"^\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})\s*$"
        match = re.match(pattern, constraint)
        if match:
            start_date, end_date = match.groups()
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                return True
            except ValueError:
                return False
        return False
    elif field_type == "category":
        # Check if constraint is a comma-separated list of values
        values = [v.strip() for v in constraint.split(",")]
        return len(values) > 0
    elif field_type == "string":
        # For string type, constraint is optional
        return True
    elif field_type in ["email", "phone", "address", "name", "aadhaar", "pan", "passport", "voterid", "ifsc", "upi"]:
        # These types don't need constraints
        return True
    return False

def generate_aadhaar():
    """Generate a fake but realistic Aadhaar number (12 digits, optionally with spaces)"""
    aadhaar = ''.join([str(random.randint(0, 9)) for _ in range(12)])
    # Randomly add spaces for formatting (40% chance)
    if random.random() < 0.4:
        aadhaar = f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:12]}"
    return aadhaar

def generate_pan():
    """Generate a fake but realistic PAN number (AAAAA0000A format)"""
    first_five = ''.join([random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(5)])
    four_digits = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    last_char = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    return f"{first_five}{four_digits}{last_char}"

def generate_passport():
    """Generate a fake but realistic Indian passport number"""
    first_char = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    seven_digits = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{first_char}{seven_digits}"

def generate_voter_id():
    """Generate a fake but realistic Voter ID (2 letters followed by 7 digits)"""
    first_two = ''.join([random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(2)])
    seven_digits = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{first_two}{seven_digits}"

def generate_ifsc():
    """Generate a fake but realistic IFSC code (4 letters + 0 + 6 digits)"""
    bank_code = ''.join([random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(4)])
    branch_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"{bank_code}0{branch_code}"

def generate_upi():
    """Generate a fake but realistic UPI ID"""
    username = fake.user_name()
    domain = random.choice(['@oksbi', '@paytm', '@ybl', '@axl', '@ibl'])
    return f"{username}{domain}".lower()

# --- Value Generation Helper Functions ---
def _generate_string_value(constraint, field_name, auto_mask, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
        return str(edge_condition['value'])
    return fake.text(max_nb_chars=20).replace('\n', ' ')

def _generate_int_value(constraint, field_name, auto_mask, edge_condition=None):
    min_default, max_default = 1, 1000
    if constraint and validate_constraint("int", constraint): # Original constraint
        min_val_str, max_val_str = map(str.strip, constraint.split('-'))
        min_default, max_default = int(float(min_val_str)), int(float(max_val_str))

    min_target, max_target = min_default, max_default

    if edge_condition:
        op = edge_condition['operator']
        val = int(edge_condition['value'])
        if op == '>': min_target = val + 1
        elif op == '<': max_target = val - 1
        elif op == '==': min_target, max_target = val, val
        elif op == '>=': min_target = val
        elif op == '<=': max_target = val
        # Note: != is complex for direct generation, would require generate-then-check-retry.

    if "age" in field_name.lower() or "salary" in field_name.lower(): # Ensure non-negative for these
        min_target = max(0, min_target)

    if min_target > max_target: # If edge case created invalid range, try to make a small valid one
        if edge_condition and edge_condition['operator'] == '==': return int(edge_condition['value']) # Exact value
        st.warning(f"Edge case for '{field_name}' created an invalid range ({min_target}-{max_target}). Attempting to adjust or use original constraint.")
        # Attempt to create a small valid range around the edge value if possible, else revert
        if op in ['>', '>=']: max_target = min_target + abs(min_target // 20 or 10) + 10
        elif op in ['<', '<=']: min_target = max_target - abs(max_target // 20 or 10) - 10
        if min_target > max_target: # Still invalid, revert to original default or constraint
            min_target, max_target = min_default, max_default
            if "age" in field_name.lower() or "salary" in field_name.lower(): min_target = max(0, min_target)
            if min_target > max_target: return random.randint(0,100) # Absolute fallback

    return random.randint(min_target, max_target)

def _generate_float_value(constraint, field_name, auto_mask, edge_condition=None):
    min_default, max_default = 1.0, 1000.0
    if constraint and validate_constraint("float", constraint):
        min_val_str, max_val_str = map(str.strip, constraint.split('-'))
        min_default, max_default = float(min_val_str), float(max_val_str)

    min_target, max_target = min_default, max_default

    if edge_condition:
        op = edge_condition['operator']
        val = float(edge_condition['value'])
        if op == '>': min_target = val + 0.01 # Small epsilon for float
        elif op == '<': max_target = val - 0.01
        elif op == '==': min_target, max_target = val, val
        elif op == '>=': min_target = val
        elif op == '<=': max_target = val

    if "age" in field_name.lower() or "salary" in field_name.lower() or "price" in field_name.lower():
        min_target = max(0.0, min_target)

    if min_target > max_target:
        if edge_condition and edge_condition['operator'] == '==': return float(edge_condition['value'])
        st.warning(f"Edge case for '{field_name}' created an invalid float range ({min_target}-{max_target}). Attempting to adjust or use original constraint.")
        if op in ['>', '>=']: max_target = min_target + abs(min_target / 20.0 or 10.0) + 10.0
        elif op in ['<', '<=']: min_target = max_target - abs(max_target / 20.0 or 10.0) - 10.0
        if min_target > max_target:
            min_target, max_target = min_default, max_default
            if "age" in field_name.lower() or "salary" in field_name.lower() or "price" in field_name.lower(): min_target = max(0.0, min_target)
            if min_target > max_target: return round(random.uniform(0.0,100.0), 2)

    return round(random.uniform(min_target, max_target), 2)

def _generate_date_value(constraint, field_name, auto_mask, edge_condition=None):
    start_default = datetime.now() - timedelta(days=365)
    end_default = datetime.now()

    if constraint and validate_constraint("date", constraint):
        start_date_str, end_date_str = map(str.strip, constraint.split('-'))
        start_default = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_default = datetime.strptime(end_date_str, "%Y-%m-%d")

    start_target, end_target = start_default, end_default

    if edge_condition:
        op = edge_condition['operator']
        val_date = datetime.strptime(str(edge_condition['value']), "%Y-%m-%d")
        if op == '>': start_target = val_date + timedelta(days=1)
        elif op == '<': end_target = val_date - timedelta(days=1)
        elif op == '==': start_target, end_target = val_date, val_date
        elif op == '>=': start_target = val_date
        elif op == '<=': end_target = val_date

    if start_target > end_target:
        if edge_condition and edge_condition['operator'] == '==': return val_date.strftime("%Y-%m-%d")
        st.warning(f"Edge case for '{field_name}' created an invalid date range. Using original constraint.")
        start_target, end_target = start_default, end_default
        if start_target > end_target: return fake.date_this_year().strftime("%Y-%m-%d")

    days_between = (end_target - start_target).days
    if days_between < 0: days_between = 0 # Should not happen if logic above is correct
    random_days = random.randint(0, days_between)
    return (start_target + timedelta(days=random_days)).strftime("%Y-%m-%d")

def _generate_category_value(constraint, field_name, auto_mask, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
        # Ensure the edge case value is one of the possible categories if constraint exists
        if constraint:
            values = [v.strip() for v in constraint.split(",") if v.strip()]
            if str(edge_condition['value']) in values:
                return str(edge_condition['value'])
            else: # Edge case value not in allowed categories, warn and pick from original
                st.warning(f"Edge case value '{edge_condition['value']}' for '{field_name}' not in allowed categories. Picking from original constraint.")
        else: # No original constraint, so edge case value is fine
            return str(edge_condition['value'])

    if constraint:
        values = [v.strip() for v in constraint.split(",") if v.strip()]
        if values: return random.choice(values)
    return random.choice(["Option A", "Option B", "Option C"])

def _generate_email_value(constraint, field_name, auto_mask, edge_condition=None):
    # Edge cases for email (like '==') are less common for generation, but could be supported
    val = fake.email()
    return mask_pii(val, "email") if auto_mask else val

def _generate_phone_value(constraint, field_name, auto_mask, edge_condition=None):
    val = f"+91 {random.randint(7000, 9999)}{random.randint(100000, 999999)}"
    return mask_pii(val, "phone") if auto_mask else val

def _generate_address_value(constraint, field_name, auto_mask, edge_condition=None):
    val = fake.address().replace('\n', ', ')
    # Address usually not masked with XXXX by default, Faker provides a fake one.
    # If mask_pii had specific "address" masking, it would be applied if auto_mask.
    return val

def _generate_name_value(constraint, field_name, auto_mask, edge_condition=None):
    val = fake.name()
    # Name usually not masked with XXXX by default, Faker provides a fake one.
    return val

def _generate_aadhaar_value(constraint, field_name, auto_mask, edge_condition=None):
    val = generate_aadhaar()
    return mask_pii(val, "aadhaar") if auto_mask else val

def _generate_pan_value(constraint, field_name, auto_mask, edge_condition=None):
    val = generate_pan()
    return mask_pii(val, "pan") if auto_mask else val

def _generate_passport_value(constraint, field_name, auto_mask, edge_condition=None):
    val = generate_passport()
    return mask_pii(val, "passport") if auto_mask else val

def _generate_voterid_value(constraint, field_name, auto_mask, edge_condition=None):
    val = generate_voter_id()
    return mask_pii(val, "voterid") if auto_mask else val

def _generate_ifsc_value(constraint, field_name, auto_mask, edge_condition=None):
    val = generate_ifsc()
    return mask_pii(val, "ifsc") if auto_mask else val

def _generate_upi_value(constraint, field_name, auto_mask, edge_condition=None):
    val = generate_upi()
    return mask_pii(val, "upi") if auto_mask else val

VALUE_GENERATOR_FUNCTIONS = {
    "string": _generate_string_value,
    "int": _generate_int_value,
    "float": _generate_float_value,
    "date": _generate_date_value,
    "category": _generate_category_value,
    "email": _generate_email_value,
    "phone": _generate_phone_value,
    "address": _generate_address_value,
    "name": _generate_name_value,
    "aadhaar": _generate_aadhaar_value,
    "pan": _generate_pan_value,
    "passport": _generate_passport_value,
    "voterid": _generate_voterid_value,
    "ifsc": _generate_ifsc_value,
    "upi": _generate_upi_value,
}

def generate_value(field_type, constraint, field_name="", edge_condition=None):
    """Generate a random value based on field type and constraint using a dispatch dictionary."""
    auto_mask = st.session_state.get(AUTO_MASK_KEY, False)
    generator_func = VALUE_GENERATOR_FUNCTIONS.get(field_type)
    if generator_func:
        # Pass edge_condition to the specific helper
        return generator_func(constraint, field_name, auto_mask, edge_condition=edge_condition)
    st.warning(f"Unknown field type '{field_type}' for field '{field_name}'. Defaulting to N/A.")
    return "N/A" # Fallback for unknown types

# --- Constants for Domain-Specific Data Generation ---
DIAGNOSES_LIST = ["Hypertension", "Diabetes", "Asthma", "Arthritis", "Migraine", 
                  "Bronchitis", "Anemia", "Pneumonia", "Sinusitis", "Depression"]
INSURANCE_PROVIDERS_LIST = ["United Health", "Aetna", "Blue Cross", "Cigna", "Humana"]
BLOOD_TYPES_LIST = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
MEDICATIONS_LIST = ["Paracetamol", "Ibuprofen", "Amoxicillin", "Lisinopril", "Metformin", 
                    "Atorvastatin", "Omeprazole", "Losartan", "Albuterol", "Gabapentin"]
TRANSACTION_TYPES_LIST = ["Deposit", "Withdrawal", "Transfer", "Payment", "Refund"]
PRODUCT_NAMES_LIST = ["Laptop", "Smartphone", "Headphones", "Smartwatch", "Tablet",
                      "Camera", "Speaker", "Monitor", "Keyboard", "Mouse"]
PAYMENT_METHODS_LIST = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Cash on Delivery"]
PRODUCT_CATEGORIES_LIST = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Beauty"]
SHIPPING_STATUSES_LIST = ["Pending", "Shipped", "Delivered", "Cancelled", "Returned"]
GRADES_LIST = ["A", "B", "C", "D", "F"]
SUBJECTS_LIST = ["Math", "Science", "English", "History", "Geography"]
DEPARTMENTS_LIST = ["IT", "HR", "Finance", "Marketing", "Operations"]
POSITIONS_LIST = ["Manager", "Developer", "Analyst", "Designer", "Accountant"]
DEGREES_LIST = ["B.Tech", "MBA", "B.Com", "B.A", "M.Sc"]
SKILLS_LIST = ["Python", "Java", "SQL", "Excel", "Communication"]
PROPERTY_TYPES_LIST = ["Apartment", "Villa", "Plot", "Office", "Shop"]
REALESTATE_STATUSES_LIST = ["Available", "Sold", "Rented", "Under Construction"]
AMENITIES_LIST = ["Swimming Pool", "Gym", "Park", "Security", "Play Area"]
GENERAL_CATEGORIES_LIST = ["Category A", "Category B", "Category C", "Category D"]
GENERAL_STATUSES_LIST = ["Active", "Inactive", "Pending", "Completed"]

# --- Field Generator Dispatch Dictionary ---
FIELD_GENERATORS = {
    "patient_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "transaction_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "order_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "student_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "employee_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "property_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "patient_name": lambda nr: [fake.name() for _ in range(nr)],
    "customer_name": lambda nr: [fake.name() for _ in range(nr)],
    "student_name": lambda nr: [fake.name() for _ in range(nr)],
    "employee_name": lambda nr: [fake.name() for _ in range(nr)],
    "owner_name": lambda nr: [fake.name() for _ in range(nr)],
    "name": lambda nr: [fake.name() for _ in range(nr)],
    "age": lambda nr: [random.randint(18, 80) for _ in range(nr)],
    "gender": lambda nr: [random.choice(["Male", "Female", "Other"]) for _ in range(nr)],
    "doctor_name": lambda nr: [f"Dr. {fake.name()}" for _ in range(nr)],
    "hospital_name": lambda nr: [fake.company() + " Hospital" for _ in range(nr)],
    "diagnosis": lambda nr: [random.choice(DIAGNOSES_LIST) for _ in range(nr)],
    "admission_date": lambda nr: [fake.date_between(start_date="-1y", end_date="today").strftime("%Y-%m-%d") for _ in range(nr)],
    "discharge_date": lambda nr: [(fake.date_between(start_date="-1y", end_date="today") + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d") for _ in range(nr)], # Simplified independent generation
    "room_number": lambda nr: [f"{random.randint(1, 10)}{random.choice(['A', 'B', 'C'])}" for _ in range(nr)],
    "insurance_provider": lambda nr: [random.choice(INSURANCE_PROVIDERS_LIST) for _ in range(nr)],
    "blood_type": lambda nr: [random.choice(BLOOD_TYPES_LIST) for _ in range(nr)],
    "medication": lambda nr: [random.choice(MEDICATIONS_LIST) for _ in range(nr)],
    "account_number": lambda nr: [str(random.randint(1000000000, 9999999999)) for _ in range(nr)],
    "amount": lambda nr: [round(random.uniform(1000, 10000), 2) for _ in range(nr)],
    "price": lambda nr: [round(random.uniform(100, 5000), 2) for _ in range(nr)], # Adjusted range for product price
    "salary": lambda nr: [round(random.uniform(20000, 200000), 2) for _ in range(nr)], # Adjusted range for salary
    "bank_name": lambda nr: [fake.company() + " Bank" for _ in range(nr)],
    "account_holder": lambda nr: [fake.name() for _ in range(nr)],
    "transaction_type": lambda nr: [random.choice(TRANSACTION_TYPES_LIST) for _ in range(nr)],
    "balance": lambda nr: [round(random.uniform(-5000, 50000), 2) for _ in range(nr)],
    "ifsc_code": lambda nr: [generate_ifsc() for _ in range(nr)],
    "branch": lambda nr: [fake.city() + " Branch" for _ in range(nr)],
    "upi_id": lambda nr: [generate_upi() for _ in range(nr)],
    "reference_number": lambda nr: [f"REF{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "product_name": lambda nr: [random.choice(PRODUCT_NAMES_LIST) + " " + str(random.randint(1, 10)) for _ in range(nr)],
    "quantity": lambda nr: [random.randint(1, 5) for _ in range(nr)],
    "payment_method": lambda nr: [random.choice(PAYMENT_METHODS_LIST) for _ in range(nr)],
    "delivery_address": lambda nr: [fake.address().replace('\n', ', ') for _ in range(nr)],
    "customer_email": lambda nr: [fake.email() for _ in range(nr)],
    "customer_phone": lambda nr: [f"+91 {random.randint(7000, 9999)}{random.randint(100000, 999999)}" for _ in range(nr)],
    "product_category": lambda nr: [random.choice(PRODUCT_CATEGORIES_LIST) for _ in range(nr)],
    "discount": lambda nr: [round(random.uniform(0, 0.5), 2) for _ in range(nr)],
    "shipping_status": lambda nr: [random.choice(SHIPPING_STATUSES_LIST) for _ in range(nr)],
    "grade": lambda nr: [random.choice(GRADES_LIST) for _ in range(nr)],
    "school_name": lambda nr: [fake.company() + " School" for _ in range(nr)],
    "teacher_name": lambda nr: [f"Mr./Ms. {fake.last_name()}" for _ in range(nr)],
    "subject": lambda nr: [random.choice(SUBJECTS_LIST) for _ in range(nr)],
    "attendance": lambda nr: [f"{random.randint(70, 100)}%" for _ in range(nr)],
    "marks": lambda nr: [random.randint(50, 100) for _ in range(nr)],
    "parent_name": lambda nr: [fake.name() for _ in range(nr)],
    "department": lambda nr: [random.choice(DEPARTMENTS_LIST) for _ in range(nr)],
    "position": lambda nr: [random.choice(POSITIONS_LIST) for _ in range(nr)],
    "manager": lambda nr: [fake.name() for _ in range(nr)],
    "education": lambda nr: [random.choice(DEGREES_LIST) for _ in range(nr)],
    "skills": lambda nr: [", ".join(random.sample(SKILLS_LIST, random.randint(2, 4))) for _ in range(nr)],
    "performance_rating": lambda nr: [round(random.uniform(1, 5), 1) for _ in range(nr)],
    "property_type": lambda nr: [random.choice(PROPERTY_TYPES_LIST) for _ in range(nr)],
    "area": lambda nr: [f"{random.randint(500, 3000)} sq.ft." for _ in range(nr)],
    "location": lambda nr: [fake.city() for _ in range(nr)],
    "bedrooms": lambda nr: [random.randint(1, 5) for _ in range(nr)],
    "bathrooms": lambda nr: [random.randint(1, 3) for _ in range(nr)],
    "contact_phone": lambda nr: [f"+91 {random.randint(7000, 9999)}{random.randint(100000, 999999)}" for _ in range(nr)],
    "status": lambda nr: [random.choice(GENERAL_STATUSES_LIST + SHIPPING_STATUSES_LIST + REALESTATE_STATUSES_LIST) for _ in range(nr)], # Combined status
    "amenities": lambda nr: [", ".join(random.sample(AMENITIES_LIST, random.randint(1, 3))) for _ in range(nr)],
    "year_built": lambda nr: [random.randint(1990, 2023) for _ in range(nr)],
    "email": lambda nr: [fake.email() for _ in range(nr)],
    "phone": lambda nr: [f"+91 {random.randint(7000, 9999)}{random.randint(100000, 999999)}" for _ in range(nr)],
    "address": lambda nr: [fake.address().replace('\n', ', ') for _ in range(nr)],
    "date": lambda nr: [fake.date_between(start_date="-1y", end_date="today").strftime("%Y-%m-%d") for _ in range(nr)],
    "value": lambda nr: [round(random.uniform(10, 1000), 2) for _ in range(nr)], # Generic value
    "category": lambda nr: [random.choice(GENERAL_CATEGORIES_LIST) for _ in range(nr)],
    "description": lambda nr: [fake.sentence() for _ in range(nr)],
    "score": lambda nr: [round(random.uniform(0, 100), 1) for _ in range(nr)],
    "default_word": lambda nr: [fake.word() for _ in range(nr)] # Fallback generator
}

# --- Synonym and Phrase Mapping for Fields ---
# Maps user-friendly terms/phrases to canonical field keys used in FIELD_GENERATORS
FIELD_SYNONYM_TO_CANONICAL_MAP = {
    # General
    "identifier": "id", "record id": "id",
    "full name": "name", "person name": "name",
    "years old": "age",
    "sex": "gender",
    "email address": "email",
    "phone number": "phone", "contact number": "phone", "mobile number": "phone",
    "location address": "address", "street address": "address",
    "specific date": "date", "transaction date": "date", "order date": "date", "join date": "date", "listing date": "date", "date of birth": "date", "dob": "date",
    "monetary value": "value",
    "type": "category", "classification": "category", # 'category' itself is a key
    "details": "description",
    "current status": "status", # 'status' itself is a key
    "rating": "score", # 'score' itself is a key

    # Hospital
    "patient id": "patient_id", "patient number": "patient_id", "medical record number": "patient_id", "mrn": "patient_id",
    "patient name": "patient_name",
    "doctor name": "doctor_name", "physician name": "doctor_name",
    "hospital name": "hospital_name", "clinic name": "hospital_name",
    "medical condition": "diagnosis", # 'diagnosis' itself is a key
    "admission date": "admission_date", "date of admission": "admission_date",
    "discharge date": "discharge_date", "date of discharge": "discharge_date",
    "room number": "room_number", "hospital room": "room_number",
    "insurance provider": "insurance_provider", "health insurance": "insurance_provider",
    "blood type": "blood_type", "blood group": "blood_type",
    "prescription": "medication", "drug name": "medication", # 'medication' itself is a key

    # Finance
    "transaction id": "transaction_id", "transaction number": "transaction_id", "txn id": "transaction_id",
    "account number": "account_number", "acct no": "account_number", "bank account number": "account_number",
    "transaction amount": "amount", # 'amount' itself is a key
    "bank name": "bank_name",
    "account holder": "account_holder", "account name": "account_holder",
    "transaction type": "transaction_type", "type of transaction": "transaction_type",
    "account balance": "balance", # 'balance' itself is a key
    "ifsc code": "ifsc_code", "ifsc": "ifsc_code",
    "bank branch": "branch", # 'branch' itself is a key
    "upi id": "upi_id", "upi address": "upi_id",
    "reference number": "reference_number", "ref no": "reference_number",

    # Ecommerce
    "order id": "order_id", "order number": "order_id",
    "customer name": "customer_name",
    "product name": "product_name", "item name": "product_name",
    "cost": "price", "product price": "price", # 'price' itself is a key
    "number of items": "quantity", # 'quantity' itself is a key
    "payment method": "payment_method", "mode of payment": "payment_method",
    "delivery address": "delivery_address", "shipping address": "delivery_address",
    "customer email": "customer_email",
    "customer phone": "customer_phone",
    "product category": "product_category", "item category": "product_category",
    "price reduction": "discount", # 'discount' itself is a key
    "shipping status": "shipping_status", "order status": "shipping_status",

    # Education (many are already direct matches or covered by general)
    "student id": "student_id", "student number": "student_id", "roll number": "student_id",
    "student name": "student_name",
    "class": "grade", "student grade": "grade", # 'grade' itself is a key
    "college name": "school_name", "university name": "school_name", # 'school_name' itself is a key
    "teacher name": "teacher_name", "instructor name": "teacher_name", "professor name": "teacher_name",
    "course name": "subject", # 'subject' itself is a key
    "student attendance": "attendance", # 'attendance' itself is a key
    "score obtained": "marks", "exam score": "marks", # 'marks' itself is a key
    "parent name": "parent_name", "guardian name": "parent_name",

    # Employee (many are already direct matches or covered by general)
    "employee id": "employee_id", "employee number": "employee_id", "staff id": "employee_id",
    "employee name": "employee_name", "staff name": "employee_name",
    "dept": "department", # 'department' itself is a key
    "compensation": "salary", "pay": "salary", "income": "salary", # 'salary' itself is a key
    "joining date": "date", "date of joining": "date", # Covered by general date
    "job title": "position", "designation": "position", "role": "position", # 'position' itself is a key
    "reporting manager": "manager", "supervisor": "manager", # 'manager' itself is a key
    "qualification": "education", "degree": "education", # 'education' itself is a key
    "abilities": "skills", "expertise": "skills", # 'skills' itself is a key
    "performance rating": "performance_rating", "appraisal score": "performance_rating",

    # Real Estate
    "property id": "property_id", "property number": "property_id", "listing id": "property_id",
    "type of property": "property_type", # 'property_type' itself is a key
    "size": "area", "square feet": "area", "sq ft": "area", # 'area' itself is a key
    "property location": "location", # 'location' itself is a key
    "number of bedrooms": "bedrooms", "beds": "bedrooms", # 'bedrooms' itself is a key
    "number of bathrooms": "bathrooms", "baths": "bathrooms", # 'bathrooms' itself is a key
    "seller name": "owner_name", # 'owner_name' itself is a key
    # "contact_phone" is direct
    "facilities": "amenities", # 'amenities' itself is a key
    "construction year": "year_built", # 'year_built' itself is a key

    # Add direct keys from FIELD_GENERATORS if they are not complex phrases
    **{key: key for key in FIELD_GENERATORS.keys()} # Ensures direct matches are also considered
}

def generate_domain_specific_data(prompt, num_rows=10):
    """Generate domain-specific synthetic data based on natural language input."""
    # Set random seed if reproducibility is requested
    if use_fixed_seed:
        random.seed(42)
        Faker.seed(42)
    
    # Parse number of rows from prompt if specified
    for word in prompt.split():
        if word.isdigit():
            num_rows = int(word)
            break
    
    # Detect domain from prompt
    domain = "general"
    domain_keywords = {
        "hospital": ["hospital", "patient", "doctor", "medical", "healthcare", "clinic"],
        "finance": ["finance", "bank", "transaction", "account", "payment", "loan"],
        "ecommerce": ["ecommerce", "product", "order", "customer", "shopping", "retail"],
        "education": ["school", "student", "teacher", "education", "university", "college"],
        "employee": ["employee", "staff", "worker", "hr", "human resources", "salary"],
        "realestate": ["property", "real estate", "house", "apartment", "rent", "sale"]
    }
    
    prompt_lower = prompt.lower()
    for domain_name, keywords in domain_keywords.items():
        if any(keyword in prompt_lower for keyword in keywords):
            domain = domain_name
            break
    
    # Define domain-specific field templates
    domain_templates = {
        "hospital": {
            "required": ["patient_id", "patient_name", "age", "gender"],
            "optional": [
                "doctor_name", "hospital_name", "diagnosis", 
                "admission_date", "discharge_date", "room_number",
                "insurance_provider", "blood_type", "medication"
            ]
        },
        "finance": {
            "required": ["transaction_id", "account_number", "amount"],
            "optional": [
                "transaction_date", "bank_name", "account_holder",
                "transaction_type", "balance", "ifsc_code",
                "branch", "upi_id", "reference_number"
            ]
        },
        "ecommerce": {
            "required": ["order_id", "customer_name", "product_name", "price"],
            "optional": [
                "order_date", "quantity", "payment_method",
                "delivery_address", "customer_email", "customer_phone",
                "product_category", "discount", "shipping_status"
            ]
        },
        "education": {
            "required": ["student_id", "student_name", "age", "grade"],
            "optional": [
                "school_name", "teacher_name", "subject",
                "attendance", "marks", "parent_name",
                "address", "email", "phone"
            ]
        },
        "employee": {
            "required": ["employee_id", "employee_name", "department", "salary"],
            "optional": [
                "join_date", "position", "manager",
                "email", "phone", "address",
                "education", "skills", "performance_rating"
            ]
        },
        "realestate": {
            "required": ["property_id", "property_type", "price", "area"],
            "optional": [
                "location", "bedrooms", "bathrooms",
                "owner_name", "contact_phone", "listing_date",
                "status", "amenities", "year_built"
            ]
        },
        "general": {
            "required": ["id", "name"],
            "optional": [
                "age", "email", "phone", "address",
                "date", "value", "category",
                "description", "status", "score"
            ]
        }
    }
    
    # Get the appropriate template
    template = domain_templates[domain]
    
    # Parse requested fields from prompt
    requested_fields = []
    # Sort synonyms by length (descending) to match longer phrases first
    sorted_synonyms = sorted(FIELD_SYNONYM_TO_CANONICAL_MAP.keys(), key=len, reverse=True)
    
    temp_prompt_lower = prompt_lower # Work on a copy for replacing matched parts
    added_canonical_fields = set()

    for user_phrase in sorted_synonyms:
        if user_phrase in temp_prompt_lower:
            canonical_field = FIELD_SYNONYM_TO_CANONICAL_MAP[user_phrase]
            # Check if this canonical field is relevant for the current domain template
            if canonical_field in template["required"] or canonical_field in template["optional"]:
                if canonical_field not in added_canonical_fields:
                    requested_fields.append(canonical_field)
                    added_canonical_fields.add(canonical_field)
                temp_prompt_lower = temp_prompt_lower.replace(user_phrase, "", 1) # Avoid re-matching

    if not requested_fields:
        requested_fields = template["required"]
        # Add up to 3 optional fields
        requested_fields.extend(random.sample(template["optional"], min(3, len(template["optional"]))))
    
    # Generate data
    data = {}
    for field in requested_fields:
        # Use the dispatch dictionary to get the generator function
        # Fallback to 'default_word' if a specific generator isn't found
        generator_func = FIELD_GENERATORS.get(field, FIELD_GENERATORS["default_word"])
        try:
            data[field] = generator_func(num_rows)
        except Exception as e:
            st.error(f"Error generating data for field '{field}': {e}")
            data[field] = [None] * num_rows # Fill with None on error to maintain DataFrame structure
            
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Convert column names to more readable format
    df.columns = [col.replace("_", " ").title() for col in df.columns]
    
    return df

# Generate Synthetic Data Based on Input (Simplified prompt-based, distinct from domain-specific)
def generate_synthetic_data(description):
    # Global access to use_fixed_seed
    global use_fixed_seed
    
    # Set random seed if reproducibility is requested
    if use_fixed_seed:
        random.seed(42)
        Faker.seed(42)
    
    # Parse basic keywords
    description = description.lower()
    
    # Default values
    num_rows = 10
    columns = []
    detected_pii = []
    detected_dpdp = []
    
    # Parse number of rows
    for word in description.split():
        if word.isdigit():
            num_rows = int(word)
            break
    
    # Detect column types with Indian-specific fields
    PROMPT_FIELD_CONFIG = {
        'name':    {'display': 'Name', 'gen_type': 'name', 'constraint': ''},
        'age':     {'display': 'Age', 'gen_type': 'int', 'constraint': '18-65'},
        'salary':  {'display': 'Salary', 'gen_type': 'int', 'constraint': '30000-150000'},
        'email':   {'display': 'Email', 'gen_type': 'email', 'constraint': ''},
        'phone':   {'display': 'Phone', 'gen_type': 'phone', 'constraint': ''},
        'address': {'display': 'Address', 'gen_type': 'address', 'constraint': ''},
        'gender':  {'display': 'Gender', 'gen_type': 'category', 'constraint': 'Male,Female,Other'},
        'job':     {'display': 'Job Title', 'gen_func': lambda nr: [fake.job() for _ in range(nr)]},
        'company': {'display': 'Company', 'gen_func': lambda nr: [fake.company() for _ in range(nr)]},
        'aadhaar': {'display': 'Aadhaar', 'gen_type': 'aadhaar', 'constraint': ''},
        'pan':     {'display': 'PAN', 'gen_type': 'pan', 'constraint': ''},
        'passport':{'display': 'Passport', 'gen_type': 'passport', 'constraint': ''},
        'voter':   {'display': 'Voter ID', 'gen_type': 'voterid', 'constraint': ''},
        'ifsc':    {'display': 'IFSC', 'gen_type': 'ifsc', 'constraint': ''},
        'upi':     {'display': 'UPI', 'gen_type': 'upi', 'constraint': ''},
        'city':    {'display': 'City', 'gen_func': lambda nr: [fake.city() for _ in range(nr)]},
        'state':   {'display': 'State', 'gen_func': lambda nr: [fake.state() for _ in range(nr)]},
        'pincode': {'display': 'Pincode', 'gen_func': lambda nr: [fake.postcode() for _ in range(nr)]},
        'account': {'display': 'Account Number', 'gen_func': lambda nr: [str(random.randint(1000000000, 9999999999)) for _ in range(nr)]},
        'bank':    {'display': 'Bank Name', 'gen_func': lambda nr: [fake.bank_name() for _ in range(nr)]}
    }
    
    # Sort PROMPT_FIELD_CONFIG keys by length (descending) to match longer phrases first
    sorted_prompt_keywords = sorted(PROMPT_FIELD_CONFIG.keys(), key=len, reverse=True)

    temp_description = description # Work on a copy
    for keyword in sorted_prompt_keywords:
        if keyword in description:
            config = PROMPT_FIELD_CONFIG[keyword]
            columns.append(config['display'])
            if config['display'] in PII_FIELDS:
                detected_pii.append(config['display'])
            if is_dpdp_pii(config['display']):
                detected_dpdp.append(config['display'])
            temp_description = temp_description.replace(keyword, "", 1) # Avoid re-matching parts of longer keywords
    
    # If we detect domain-specific keywords, use domain-specific generation
    # This check should ideally be more robust or integrated with the schema editor's keyword detection
    domain_keywords_list = ["hospital", "patient", "doctor", "finance", "bank", "transaction", 
                           "ecommerce", "product", "order", "education", "student", "school",
                           "employee", "hr", "real estate", "property"]
    
    if any(keyword in description for keyword in domain_keywords_list):
        # Pass the original prompt and num_rows to the domain-specific generator
        return generate_domain_specific_data(prompt, num_rows) # Use the original prompt text box value
    
    # Ensure we have at least some columns for simple generation
    if not columns:
        st.error("No valid columns detected from your prompt for simple generation. Please use keywords like name, age, salary, email, etc., or try the Smart Schema Editor for more control.")
        return None
    
    # Generate data using the generate_value function for simple prompt-based requests
    data = {}
    # Iterate through the original prompt keywords to find their configs
    # This ensures we use the correct config for each detected column
    processed_display_names = set() # To handle cases where multiple keywords map to same display name
    
    # We need to iterate based on the order columns were detected (which implies keyword order)
    # or iterate through PROMPT_FIELD_CONFIG again, sorted, and check if its display name is in 'columns'
    for keyword in sorted_prompt_keywords: # Iterate in sorted order again for generation
        if keyword in description: # Check if the original keyword was in the prompt
            config = PROMPT_FIELD_CONFIG[keyword]
            col_display_name = config['display']
            if col_display_name in columns and col_display_name not in processed_display_names:
                if 'gen_func' in config:
                    data[col_display_name] = config['gen_func'](num_rows)
                elif 'gen_type' in config:
                    data[col_display_name] = [
                        generate_value(config['gen_type'], config['constraint'], col_display_name)
                        for _ in range(num_rows)
                    ]
                processed_display_names.add(col_display_name)
    
    # Create DataFrame
    synthetic_df = pd.DataFrame(data)
    
    # Display PII warning if detected
    if detected_pii:
        st.warning(f"⚠️ Detected possible PII fields: {', '.join(detected_pii)}. Ensure compliance with privacy regulations.")
    
    # Display DPDP-specific warnings
    if detected_dpdp:
        for field in detected_dpdp:
            st.markdown(f"""
            <div class="dpdp-warning">
            🔐 <strong>DPDP Compliance Note</strong>: "{field}" contains PII under India's DPDP Act
            </div>
            """, unsafe_allow_html=True)
    
    return synthetic_df

# --- Schema Inference Rules for pre-populating Smart Schema Editor ---
SCHEMA_INFERENCE_RULES = [
    (r"(?:email)", "email", ""),
    (r"(?:name)", "name", ""),
    (r"(?:phone|contact)", "phone", ""),
    (r"(?:address|location)", "address", ""),
    (r"(?:age)", "int", "18-60"),
    (r"(?:salary|income|pay)", "int", "20000-500000"),
    (r"(?:gender)", "category", "Male, Female, Other"),
    (r"(?:aadhaar)", "aadhaar", ""),
    (r"(?:pan)", "pan", ""),
    (r"(?:passport)", "passport", ""),
    (r"(?:voter)", "voterid", ""), # voter or voter id
    (r"(?:ifsc)", "ifsc", ""),
    (r"(?:upi)", "upi", ""),
    (r"(?:date|dob|joining_date|order_date)", "date", f"{fake.date_this_year(before_today=True, after_today=False).strftime('%Y-%m-%d')} - {fake.date_this_year(before_today=False, after_today=True).strftime('%Y-%m-%d')}"),
    (r"(?:price|amount|value|cost)", "float", "10.00-1000.00"),
    (r"(?:id|number|code)$", "string", ""), # Ends with id, number, or code
    (r"(?:status|type|category)$", "category", "Type A, Type B, Type C"), # Ends with status, type, or category
]

# Smart Schema Editor Section
def show_smart_schema_editor(synthetic_df=None, num_rows=10):
    st.subheader("🧠 Smart Schema Editor")
    st.markdown("Define and customize your data schema with field types and constraints.")
    
    # Initialize schema state if not already present
    if 'schema' not in st.session_state:
        st.session_state.schema = []
        if synthetic_df is not None:
            # Clear any previous schema if pre-populating from a new source
            if st.session_state.schema and synthetic_df.columns.tolist() != [f['name'] for f in st.session_state.schema]:
                st.session_state.schema = []

            # Pre-populate schema with columns from synthetic_df
            for col in synthetic_df.columns:
                inferred_type = "string" # Default
                inferred_constraint = ""
                
                for pattern, f_type, f_constraint in SCHEMA_INFERENCE_RULES:
                    if re.search(pattern, col, re.IGNORECASE):
                        inferred_type = f_type
                        inferred_constraint = f_constraint
                        break # First match wins
                
                st.session_state.schema.append({
                    "name": col,
                    "type": inferred_type,
                    "constraint": inferred_constraint
                })
    
    # Display existing schema fields
    for i, field in enumerate(st.session_state.schema):
        col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
        
        with col1:
            st.session_state.schema[i]["name"] = st.text_input(
                f"Field Name", 
                value=field["name"], 
                key=f"field_name_{i}"
            )
        
        with col2:
            st.session_state.schema[i]["type"] = st.selectbox(
                f"Field Type", 
                options=list(FIELD_TYPES.keys()),
                format_func=lambda x: FIELD_TYPES[x],
                index=list(FIELD_TYPES.keys()).index(field["type"]) if field["type"] in FIELD_TYPES else 0,
                key=f"field_type_{i}"
            )
        
        with col3:
            field_type = st.session_state.schema[i]["type"]
            placeholder = ""
            
            if field_type == "int" or field_type == "float":
                placeholder = "e.g., 1-100 or 20000-500000"
            elif field_type == "date":
                placeholder = "e.g., 2023-01-01 - 2023-12-31"
            elif field_type == "category":
                placeholder = "e.g., Option A, Option B, Option C"
            
            st.session_state.schema[i]["constraint"] = st.text_input(
                f"Constraints",
                value=field["constraint"],
                placeholder=placeholder,
                key=f"field_constraint_{i}"
            )
        
        with col4:
            if st.button("Delete", key=f"delete_{i}"):
                st.session_state.schema.pop(i)
                st.rerun()
    
    # Add new field button
    if st.button("➕ Add Field"):
        st.session_state.schema.append({
            "name": f"Field{len(st.session_state.schema) + 1}",
            "type": "string",
            "constraint": ""
        })
        st.rerun()

    # --- Edge Case Injection UI ---
    st.markdown("---")
    st.subheader("🧪 Edge Case Injection")
    st.markdown("Define specific scenarios to inject into a percentage of your dataset.")

    if 'edge_cases' not in st.session_state:
        st.session_state.edge_cases = []

    schema_field_names = [field['name'] for field in st.session_state.schema if field['name']]
    OPERATORS = ['==', '!=', '>', '<', '>=', '<=']

    for i, edge_rule in enumerate(st.session_state.edge_cases):
        st.markdown(f"**Edge Case Rule {i+1}**")
        rule_cols = st.columns([2, 1, 1])
        edge_rule['percentage'] = rule_cols[0].number_input(
            "Percentage of rows", 
            min_value=0.0, max_value=100.0, 
            value=edge_rule.get('percentage', 1.0), 
            step=0.1, format="%.1f", 
            key=f"edge_perc_{i}"
        )
        if rule_cols[1].button("🗑️ Delete Rule", key=f"del_edge_rule_{i}"):
            st.session_state.edge_cases.pop(i)
            st.rerun()

        if 'conditions' not in edge_rule:
            edge_rule['conditions'] = []

        for j, condition in enumerate(edge_rule['conditions']):
            cond_cols = st.columns([3,2,2,1])
            condition['field'] = cond_cols[0].selectbox(
                "Field", schema_field_names, 
                index=schema_field_names.index(condition['field']) if condition['field'] in schema_field_names else 0, 
                key=f"edge_field_{i}_{j}"
            )
            condition['operator'] = cond_cols[1].selectbox(
                "Operator", OPERATORS, 
                index=OPERATORS.index(condition['operator']) if condition['operator'] in OPERATORS else 0, 
                key=f"edge_op_{i}_{j}"
            )
            condition['value'] = cond_cols[2].text_input(
                "Value", value=condition.get('value', ''), 
                key=f"edge_val_{i}_{j}"
            )
            if cond_cols[3].button("➖", key=f"del_edge_cond_{i}_{j}"): # Delete condition
                edge_rule['conditions'].pop(j)
                st.rerun()
        
        if st.button("➕ Add Condition to Rule", key=f"add_edge_cond_{i}"):
            if schema_field_names: # Only add if there are fields to select
                edge_rule['conditions'].append({'field': schema_field_names[0], 'operator': '==', 'value': ''})
                st.rerun()
            else:
                st.warning("Please define schema fields before adding edge case conditions.")
        st.markdown("---")

    if st.button("➕ Add New Edge Case Rule"):
        st.session_state.edge_cases.append({'percentage': 1.0, 'conditions': []})
        st.rerun()
    
    # Number of rows input
    num_rows = st.number_input("Number of rows to generate", min_value=1, value=max(1, num_rows), step=1)
    
    # Auto-masking toggle
    st.session_state[AUTO_MASK_KEY] = st.checkbox(
        "Auto-mask sensitive fields (PII, DPDP identifiers)",
        value=st.session_state.get(AUTO_MASK_KEY, False))
    
    # Generate button
    if st.button("🔄 Generate Data from Schema"):
        # Validate schema
        invalid_fields = []
        for field in st.session_state.schema:
            if not field["name"]:
                invalid_fields.append("Field name cannot be empty")
                continue
                
            if not validate_constraint(field["type"], field["constraint"]) and field["constraint"]:
                invalid_fields.append(f"Invalid constraint for {field['name']} ({field['type']})")
        
        if invalid_fields:
            for error in invalid_fields:
                st.error(error)
        else:
            # Generate data from schema
            all_rows_data = []
            schema_valid = True
            detected_dpdp = []
            edge_case_rules = st.session_state.get('edge_cases', [])

            for row_idx in range(num_rows):
                row_data = {}
                applied_edge_rule_for_row = None

                # Determine if this row should be an edge case
                # This is a simple way; more sophisticated sampling could be used.
                # For now, it checks each rule. If multiple rules could apply by chance,
                # the current logic would try to apply conditions from all of them if fields differ,
                # or the last one if fields overlap. This could be refined.
                # Let's try to apply at most one rule per row for simplicity.
                
                # Create a list of rules that could apply based on random chance
                potential_rules_for_row = []
                for rule in edge_case_rules:
                    if random.random() < (rule.get('percentage', 0.0) / 100.0):
                        potential_rules_for_row.append(rule)
                
                if potential_rules_for_row:
                    applied_edge_rule_for_row = random.choice(potential_rules_for_row) # Pick one if multiple qualify

                for field_schema in st.session_state.schema:
                    field_name = field_schema["name"]
                    field_type = field_schema["type"]
                    original_constraint = field_schema["constraint"]
                    field_specific_edge_condition = None

                    if applied_edge_rule_for_row and applied_edge_rule_for_row.get('conditions'):
                        for cond_in_rule in applied_edge_rule_for_row['conditions']:
                            if cond_in_rule['field'] == field_name:
                                field_specific_edge_condition = cond_in_rule # e.g. {'operator': '>', 'value': 100}
                                break
                    try:
                        row_data[field_name] = generate_value(
                            field_type, original_constraint, field_name, edge_condition=field_specific_edge_condition
                        )
                        if is_dpdp_pii(field_name):
                            if field_name not in detected_dpdp: detected_dpdp.append(field_name)
                    except Exception as e:
                        st.error(f"Error generating data for field '{field_name}' (row {row_idx+1}): {str(e)}")
                        row_data[field_name] = None # Or some default error marker
                        schema_valid = False # Mark schema as invalid if any row fails
                    
                all_rows_data.append(row_data)
            
            if schema_valid:
                schema_df = pd.DataFrame(all_rows_data)
                st.session_state.schema_df = schema_df
                
                # Identify PII fields
                pii_detected = [
                    field["name"] for field in st.session_state.schema
                    if field["type"] in ["email", "phone", "address", "name", "aadhaar", "pan", "passport", "voterid", "ifsc", "upi"]
                ]
                
                if pii_detected:
                    st.warning(f"⚠️ Generated data contains PII fields: {', '.join(pii_detected)}. Ensure compliance with privacy regulations.")
                
                # Display DPDP-specific warnings
                if detected_dpdp:
                    for field in detected_dpdp:
                        st.markdown(f"""
                        <div class="dpdp-warning">
                        🔐 <strong>DPDP Compliance Note</strong>: "{field}" contains PII under India's DPDP Act
                        </div>
                        """, unsafe_allow_html=True)
                
                st.success(f"✅ Successfully generated {num_rows} rows of synthetic data!")
    
    # Display generated data if available
    if "schema_df" in st.session_state:
        st.subheader("📊 Generated Data from Schema")
        st.dataframe(st.session_state.schema_df)
        
        # Download options
        csv = st.session_state.schema_df.to_csv(index=False)
        
        # Use openpyxl to create Excel file
        writer = pd.ExcelWriter('schema_data.xlsx', engine='openpyxl')
        st.session_state.schema_df.to_excel(writer, index=False, sheet_name='Sheet1')
        writer.close()
        
        # Read the created Excel file
        with open('schema_data.xlsx', 'rb') as excel_file:
            excel_data = excel_file.read()
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="schema_data.csv",
                mime="text/csv",
                key="download_csv_schema"
            )
        with col2:
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name="schema_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_schema"
            )

# --- Helper functions for Ethical AI Dashboard Scores ---
def calculate_bias_score(df):
    """Calculates a bias score based on categorical column distributions."""
    if df is None or df.empty:
        return 50 # Default score if no data

    categorical_cols = df.select_dtypes(include='object').columns.tolist()
    if not categorical_cols: # Try to find more categoricals
        categorical_cols = [col for col in df.columns if df[col].nunique() < 20 and df[col].nunique() > 1 and df[col].nunique() < len(df)]

    if not categorical_cols:
        return 100 # No categorical columns to assess bias, so perfectly unbiased in this context

    column_scores = []
    for col in categorical_cols:
        counts = df[col].value_counts()
        num_categories = len(counts)
        if num_categories <= 1:
            column_scores.append(100) # Perfectly uniform or single category
            continue

        probabilities = counts / len(df[col].dropna())
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-9)) # Add epsilon to avoid log(0)
        max_entropy = np.log2(num_categories)
        
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 1.0
        column_scores.append(normalized_entropy * 100)

    return np.mean(column_scores) if column_scores else 50

def calculate_compliance_score(pii_risk_level, dpdp_risk_level, bias_score_val):
    """Calculates a compliance score."""
    score = 100

    # Deductions for PII/DPDP risk
    if pii_risk_level == "High": score -= 25
    elif pii_risk_level == "Medium": score -= 10 # Assuming we might add a Medium state
    
    if dpdp_risk_level == "High": score -= 35 # Higher penalty for DPDP
    elif dpdp_risk_level == "Medium": score -= 15

    # Deduction for bias (if bias score is low, deduct more)
    if bias_score_val < 70: # If bias score is less than 70 (meaning more biased)
        score -= (70 - bias_score_val) * 0.5 # Scale down the penalty from bias

    return max(0, min(100, round(score))) # Ensure score is between 0 and 100

# --- Helper functions for synthesizing data from uploaded file ---
def _synthesize_numeric_column_from_upload(series, column_name):
    """Adds noise to a numeric series, ensuring positivity for relevant columns."""
    if any(keyword in column_name.lower() for keyword in ['age', 'salary', 'price', 'cost', 'amount', 'quantity', 'marks', 'bedrooms', 'bathrooms']):
        # Ensure positive values and add relative noise
        return series.apply(lambda x: max(1 if pd.api.types.is_integer_dtype(series) else 0.01, x + np.random.normal(0, abs(x * 0.1) if x != 0 else 0.1)))
    else:
        # Add noise, can be negative
        return series.apply(lambda x: x + np.random.normal(0, abs(x * 0.1) if x != 0 else 1))

PII_FIELD_SYNTHESIZERS_FOR_UPLOAD = {
    # Maps keywords found in column names to (field_type_for_generate_value, constraint_for_generate_value)
    'name': ("name", ""),
    'email': ("email", ""),
    'phone': ("phone", ""),
    'address': ("address", ""),
    'aadhaar': ("aadhaar", ""),
    'pan': ("pan", ""),
    'passport': ("passport", ""),
    'voter': ("voterid", ""), # Catches "voter" or "voter id"
    'ifsc': ("ifsc", ""),
    'upi': ("upi", ""),
    # SSN is in PII_FIELDS but not DPDP_PII_FIELDS, add if needed: 'ssn': ("ssn", "")
}

def _synthesize_categorical_column_from_upload(series, column_name):
    """Synthesizes a categorical/object column. Fakes PII, shuffles others."""
    num_rows = len(series)
    for keyword, (gen_type, gen_constraint) in PII_FIELD_SYNTHESIZERS_FOR_UPLOAD.items():
        if keyword in column_name.lower() and (column_name in PII_FIELDS or is_dpdp_pii(column_name)):
            return [generate_value(gen_type, gen_constraint, column_name) for _ in range(num_rows)]
    return np.random.permutation(series) # Default for non-PII or unmapped PII-like

# File Upload
uploaded_file = st.file_uploader("Upload your CSV or XLSX dataset", type=["csv", "xlsx"])

# Tabs for different workflows
tab1, tab2 = st.tabs(["Text-based Generation", "Smart Schema Editor"])

with tab1:
    # Main Content for Text-based Generation
    if prompt:
        # Generate Synthetic Data from Text Input
        synthetic_df = generate_synthetic_data(prompt)
        
        if synthetic_df is not None:
            st.subheader("📊 Generated Synthetic Data")
            st.dataframe(synthetic_df)
            
            # Dataset Summary
            st.markdown(f"**Rows:** {synthetic_df.shape[0]} | **Columns:** {synthetic_df.shape[1]}")
            
            # --- Ethical AI Dashboard for Prompt-Generated Data ---
            st.subheader("🛡️ Ethical AI Dashboard (Prompt Data)")
            dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
            
            pii_cols_prompt = [col for col in synthetic_df.columns if col in PII_FIELDS or is_dpdp_pii(col)] # Combine PII and DPDP for general risk
            dpdp_cols_prompt_specific = [col for col in synthetic_df.columns if is_dpdp_pii(col)]

            pii_risk_level_prompt = "High" if pii_cols_prompt else "Low"
            dpdp_risk_level_prompt = "High" if dpdp_cols_prompt_specific else "Low"
            
            bias_score_prompt = calculate_bias_score(synthetic_df)
            compliance_score_prompt = calculate_compliance_score(pii_risk_level_prompt, dpdp_risk_level_prompt, bias_score_prompt)

            dash_col1.metric("Bias Score", f"{bias_score_prompt:.0f} / 100", 
                             help="Measures fairness in categorical distributions. Higher (closer to 100) is better (more balanced).")
            dash_col2.metric("PII Risk", pii_risk_level_prompt, 
                             help=f"Detected PII-like fields: {', '.join(pii_cols_prompt)}" if pii_cols_prompt else "No common PII fields detected.")
            dash_col3.metric("DPDP Risk", dpdp_risk_level_prompt, 
                             help=f"Detected DPDP-specific fields: {', '.join(dpdp_cols_prompt_specific)}" if dpdp_cols_prompt_specific else "No specific DPDP fields detected.")
            dash_col4.metric("Compliance Score", f"{compliance_score_prompt:.0f}%", 
                             help="An estimated score for overall compliance readiness based on PII, DPDP, and Bias.")

            # --- Bias Detection for Prompt-Generated Data ---
            st.subheader("📊 Bias Detection (Prompt Data)")
            categorical_cols_prompt = synthetic_df.select_dtypes(include='object').columns.tolist()
            # Attempt to find more categoricals if 'object' type is not sufficient
            if not categorical_cols_prompt:
                 categorical_cols_prompt = [col for col in synthetic_df.columns if synthetic_df[col].nunique() < 20 and synthetic_df[col].nunique() > 1]

            if categorical_cols_prompt:
                selected_col_prompt = st.selectbox(
                    "Select a categorical column from generated data to check bias", 
                    categorical_cols_prompt,
                    key="bias_checker_prompt"
                )
                if selected_col_prompt:
                    value_counts_prompt = synthetic_df[selected_col_prompt].value_counts(normalize=True) * 100
                    fig_prompt = px.bar(
                        value_counts_prompt,
                        x=value_counts_prompt.index,
                        y=value_counts_prompt.values,
                        labels={"x": selected_col_prompt, "y": "Percentage"},
                        title=f"Distribution in '{selected_col_prompt}' (Prompt Generated Data)"
                    )
                    st.plotly_chart(fig_prompt)
            else:
                st.info("No suitable categorical columns found in the prompt-generated data for bias checking.")

            # --- Compliance Report Generator for Prompt-Generated Data ---
            st.subheader("📄 Download Compliance Report (Prompt Data)")
            if st.button("Generate & Download PDF Report (Prompt Data)", key="pdf_prompt_data"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt=f"{APP_NAME} - Synthetic Data Report (From Text Prompt)", ln=True, align="C")
                pdf.ln(10)
                pdf.cell(200, 10, txt=f"Dataset Source: Text Prompt", ln=True)
                pdf.cell(200, 10, txt=f"Generated Rows: {synthetic_df.shape[0]}, Columns: {synthetic_df.shape[1]}", ln=True)
                pdf.cell(200, 10, txt=f"Bias Score: {bias_score_prompt:.0f} / 100", ln=True)
                pdf.cell(200, 10, txt=f"PII Risk: {pii_risk_level_prompt}", ln=True)
                if pii_cols_prompt:
                    pdf.cell(200, 10, txt=f"Detected PII Fields: {', '.join(pii_cols_prompt)}", ln=True)
                pdf.cell(200, 10, txt=f"DPDP Risk: {dpdp_risk_level_prompt}", ln=True)
                if dpdp_cols_prompt_specific:
                    pdf.cell(200, 10, txt=f"Detected DPDP-Specific Fields: {', '.join(dpdp_cols_prompt_specific)}", ln=True)
                pdf.cell(200, 10, txt=f"Compliance Readiness Score: {compliance_score_prompt:.0f}%", ln=True)
                pdf.ln(10)
                pdf.cell(200, 10, txt="Note: Scores are illustrative. Conduct thorough validation.", ln=True)
                
                buffer_prompt_pdf = io.BytesIO()
                pdf.output(buffer_prompt_pdf)
                st.download_button(
                    label="Download PDF Now",
                    data=buffer_prompt_pdf.getvalue(),
                    file_name="prompt_data_compliance_report.pdf",
                    mime="application/pdf",
                    key="download_pdf_prompt_data_final"
                )

            # Download options for generated data
            csv = synthetic_df.to_csv(index=False)
            
            # Use openpyxl to create Excel file
            writer = pd.ExcelWriter('synthetic_data.xlsx', engine='openpyxl')
            synthetic_df.to_excel(writer, index=False, sheet_name='Sheet1')
            writer.close()
            
            # Read the created Excel file
            with open('synthetic_data.xlsx', 'rb') as excel_file:
                excel_data = excel_file.read()
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="synthetic_data.csv",
                    mime="text/csv",
                    key="download_csv_prompt"
                )
            with col2:
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name="synthetic_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_prompt"
                )
    
    # Existing File Upload Logic
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # PII Detection on Uploaded File
        pii_columns = [col for col in df.columns if col in PII_FIELDS]
        dpdp_columns = [col for col in df.columns if is_dpdp_pii(col)]
        
        if pii_columns:
            st.warning(f"⚠️ Uploaded dataset contains potential PII columns: {', '.join(pii_columns)}")
        
        # Display DPDP-specific warnings
        if dpdp_columns:
            for field in dpdp_columns:
                st.markdown(f"""
                <div class="dpdp-warning">
                🔐 <strong>DPDP Compliance Note</strong>: "{field}" contains PII under India's DPDP Act
                </div>
                """, unsafe_allow_html=True)

        st.subheader("📊 Preview of Original Data")
        st.dataframe(df.head())

        # Generate Synthetic Data
        st.subheader("⚙️ Generate Synthetic Data")
        if st.button("Generate Synthetic Data"):
            # More sophisticated synthetic data generation
            synthetic_df_from_file = df.copy() # Use a distinct variable name
            
            for col in synthetic_df_from_file.columns:
                if pd.api.types.is_numeric_dtype(synthetic_df_from_file[col]):
                    synthetic_df_from_file[col] = _synthesize_numeric_column_from_upload(synthetic_df_from_file[col], col)
                elif pd.api.types.is_object_dtype(synthetic_df_from_file[col]) or pd.api.types.is_categorical_dtype(synthetic_df_from_file[col]):
                    synthetic_df_from_file[col] = _synthesize_categorical_column_from_upload(synthetic_df_from_file[col], col)
                # Add handling for other types like datetime if needed

            st.success("Synthetic data generated!")
            st.dataframe(synthetic_df_from_file.head())
            
            # Dataset Summary
            st.markdown(f"**Rows:** {synthetic_df_from_file.shape[0]} | **Columns:** {synthetic_df_from_file.shape[1]}")
            
            # Detect PII in synthetic data
            pii_columns = [col for col in synthetic_df_from_file.columns if col in PII_FIELDS]
            dpdp_columns = [col for col in synthetic_df_from_file.columns if is_dpdp_pii(col)]
            
            if pii_columns:
                st.warning(f"⚠️ Generated synthetic data contains PII columns: {', '.join(pii_columns)}")
            
            # Display DPDP-specific warnings
            if dpdp_columns:
                for field in dpdp_columns:
                    st.markdown(f"""
                    <div class="dpdp-warning">
                    🔐 <strong>DPDP Compliance Note</strong>: "{field}" contains PII under India's DPDP Act
                    </div>
                    """, unsafe_allow_html=True)
            
            # Download options for synthetic data
            csv = synthetic_df_from_file.to_csv(index=False)
            
            # Use openpyxl to create Excel file
            writer = pd.ExcelWriter('synthetic_data.xlsx', engine='openpyxl')
            synthetic_df_from_file.to_excel(writer, index=False, sheet_name='Sheet1')
            writer.close()
            
            # Read the created Excel file
            with open('synthetic_data.xlsx', 'rb') as excel_file:
                excel_data = excel_file.read()
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="synthetic_data.csv",
                    mime="text/csv",
                    key="download_csv_file"
                )
            with col2:
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name="synthetic_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_file"
                )

        # Bias Checker
        st.subheader("📈 Bias Checker")
        selected_col = st.selectbox("Select a categorical column to check bias", df.columns)

        if selected_col:
            value_counts = df[selected_col].value_counts(normalize=True) * 100
            fig = px.bar(
                value_counts,
                x=value_counts.index,
                y=value_counts.values,
                labels={"x": selected_col, "y": "Percentage"},
                title=f"Distribution in '{selected_col}' Column"
            )
            st.plotly_chart(fig)

        # Ethical Scorecard
        st.subheader("✅ Ethical Scorecard (Demo Values)")
        col1, col2, col3 = st.columns(3)

        # For uploaded data, we calculate scores based on the *original* uploaded 'df'
        pii_cols_uploaded = [col for col in df.columns if col in PII_FIELDS or is_dpdp_pii(col)]
        dpdp_cols_uploaded_specific = [col for col in df.columns if is_dpdp_pii(col)]

        pii_risk_level_uploaded = "High" if pii_cols_uploaded else "Low"
        dpdp_risk_level_uploaded = "High" if dpdp_cols_uploaded_specific else "Low"
        bias_score_uploaded = calculate_bias_score(df) # Calculate bias on original uploaded df
        # Note: Compliance score for uploaded data might be less relevant unless we are assessing the original data's compliance.
        # For now, let's focus the dynamic compliance score on *generated* data.
        # We can show a static or simplified compliance note for uploaded data.
        
        col1.metric("Bias Score (Original Data)", f"{bias_score_uploaded:.0f} / 100")
        col2.metric("PII Risk (Original Data)", pii_risk_level_uploaded)
        col3.metric("DPDP Risk (Original Data)", dpdp_risk_level_uploaded)


        # Download PDF Report
       
        st.subheader("📄 Download Summary Report")
        if st.button("Download PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"{APP_NAME} Synthetic Data Report", ln=True, align="C")
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Dataset: {uploaded_file.name}", ln=True)
            pdf.cell(200, 10, txt="Bias Score: 82/100", ln=True)
            pdf.cell(200, 10, txt=f"PII Risk: {pii_risk_level_uploaded}", ln=True)
            pdf.cell(200, 10, txt=f"DPDP Risk: {dpdp_risk_level_uploaded}", ln=True)
            
            # List PII columns if present
            if pii_cols_uploaded:
                pdf.cell(200, 10, txt=f"PII Columns Detected: {', '.join(pii_cols_uploaded)}", ln=True)
            
            # List DPDP columns if present
            if dpdp_cols_uploaded_specific:
                pdf.cell(200, 10, txt=f"DPDP-Sensitive Columns: {', '.join(dpdp_cols_uploaded_specific)}", ln=True)
            
            pdf.ln(10)
            pdf.cell(200, 10, txt="Note: This is a demo summary report.", ln=True)

            # Download link
            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button(
                label="Download PDF",
                data=buffer.getvalue(),
                file_name="report.pdf",
                mime="application/pdf",
                key="download_pdf_report"
            )

with tab2:
    # Smart Schema Editor tab
    synth_df = None
    rows = 10
    if 'schema_df' in st.session_state:
        rows = max(1, len(st.session_state.schema_df))
    elif prompt and 'synthetic_df' in locals() and synthetic_df is not None:
        synth_df = synthetic_df
        rows = max(1, len(synthetic_df))
    elif uploaded_file and 'df' in locals():
        synth_df = df
        rows = max(1, len(df))
    
    show_smart_schema_editor(synth_df, rows)

# Sidebar with Instructions
st.sidebar.title(f"{APP_NAME} Guide")
st.sidebar.markdown(f"""
1. **Text Input Method**:
   - Describe the dataset you want
   - Example: "10 rows of employee data with name, age, salary, email"
   - Example keywords: 
     * Personal: name, email, phone, address
     * Professional: age, salary, job, company
     * Demographic: gender
     * Indian IDs: aadhaar, pan, passport, voterid

2. **Smart Schema Editor**:
   - Define exact field types: string, email, int, float, category, etc.
   - Add constraints like age ranges (18-60) or salary ranges (₹20K-₹5L)
   - Customize the structure of your synthetic data

3. **Privacy Controls**:
   - Auto-masking of sensitive fields
   - DPDP Act compliance warnings
   - PII risk assessment


4. **File Upload Method**:
   - Upload an existing CSV or XLSX file
   - Generate synthetic version of your data
   - Analyze bias and distribution

5. **PII Protection**:
   - Automatic detection of Personal Identifiable Information
   - Warnings for potential privacy risks
   - Synthetic data generation with fake personal data

6. **Features**:
   - Generate synthetic data
   - Download as CSV or Excel
   - Bias checking
   - Ethical scorecard
   - PII risk assessment

**Powered by {APP_NAME}**: Transforming data privacy, one synthetic dataset at a time.
""")

# Footer
st.markdown(f"""
---
*{APP_NAME} - Synthetic Data Generator* | Privacy-First Data Transformation
""")