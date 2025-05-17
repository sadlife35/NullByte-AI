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
AUTO_MASK_KEY = "auto_mask_pii"  # Key for session state - This key is being replaced by DEFAULT_PII_STRATEGY_KEY

# PII Handling Strategies
PII_HANDLING_STRATEGIES = {
    "realistic_fake": "Realistic Fake (Default)",
    "masked": "Masked (e.g., XXXXX1234)",
    "redacted": "Redacted (e.g., [REDACTED])",
    "scramble_column": "Scramble Column (Shuffle existing fakes)" # To be implemented later for schema generation
}
DEFAULT_PII_STRATEGY_KEY = "default_pii_strategy"

# --- Session State Initialization ---
if 'schema' not in st.session_state:
    st.session_state.schema = []
if 'schema_df' not in st.session_state:
    st.session_state.schema_df = None
if 'edge_cases' not in st.session_state:
    st.session_state.edge_cases = []
if DEFAULT_PII_STRATEGY_KEY not in st.session_state:
    st.session_state[DEFAULT_PII_STRATEGY_KEY] = "realistic_fake"
if 'initial_schema_populated' not in st.session_state: # For template loading logic
    st.session_state.initial_schema_populated = False
if 'prompt_generated_df' not in st.session_state:
    st.session_state.prompt_generated_df = None
if 'uploaded_df_for_schema' not in st.session_state:
    st.session_state.uploaded_df_for_schema = None
if 'num_rows_for_file_upload_tab3' not in st.session_state:
    st.session_state.num_rows_for_file_upload_tab3 = 10 # Default if no file uploaded yet
if 'uploaded_file_name_tab3' not in st.session_state:
    st.session_state.uploaded_file_name_tab3 = None
if 'file_action_tab3' not in st.session_state: # To store user choice in Tab 3
    st.session_state.file_action_tab3 = None


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
    "upi": "UPI ID",
    "animal_name": "Animal Name (Pet Name)" # New type for animal names
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
    if pd.isna(value) or not str(value).strip(): # Check for empty or NaN
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
                return True # Allow min == max for single value constraint
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
        values = [v.strip() for v in constraint.split(",") if v.strip()]
        return len(values) > 0
    elif field_type == "string":
        # For string type, constraint is optional
        return True
    elif field_type in ["email", "phone", "address", "name", "aadhaar", "pan", "passport", "voterid", "ifsc", "upi"]:
        # These types don't need constraints for generation, but validate if provided
        if constraint: # If a constraint is provided, check if it's a simple value for == edge case
             return True # We'll handle constraint validation for these types in the generator if needed
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
def _generate_string_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
        return str(edge_condition['value'])
    return fake.text(max_nb_chars=20).replace('\n', ' ')

def _generate_int_value(constraint, field_name, pii_strategy, edge_condition=None):
    min_default, max_default = 1, 1000
    if constraint and validate_constraint("int", constraint): # Original constraint
        min_val_str, max_val_str = map(str.strip, constraint.split('-'))
        min_default, max_default = int(float(min_val_str)), int(float(max_val_str))

    min_target, max_target = min_default, max_default

    if edge_condition:
        op = edge_condition['operator']
        try:
            val = int(edge_condition['value'])
            if op == '>': min_target = val + 1
            elif op == '<': max_target = val - 1
            elif op == '==': min_target, max_target = val, val
            elif op == '>=': min_target = val
            elif op == '<=': max_target = val
            # Note: != is complex for direct generation, would require generate-then-check-retry.
        except ValueError:
             st.warning(f"Edge case value '{edge_condition['value']}' for '{field_name}' is not a valid integer. Ignoring edge case for this field.")


    if "age" in field_name.lower() or "salary" in field_name.lower(): # Ensure non-negative for these
        min_target = max(0, min_target)

    if min_target > max_target: # If edge case created invalid range, try to make a small valid one
        if edge_condition and edge_condition.get('operator') == '==': return int(edge_condition['value']) # Exact value if possible
        st.warning(f"Edge case for '{field_name}' created an invalid range ({min_target}-{max_target}). Attempting to adjust or use original constraint.")
        # Attempt to create a small valid range around the edge value if possible, else revert
        if edge_condition and edge_condition.get('operator') in ['>', '>=']: max_target = min_target + abs(min_target // 20 or 10) + 10
        elif edge_condition and edge_condition.get('operator') in ['<', '<=']: min_target = max_target - abs(max_target // 20 or 10) - 10
        if min_target > max_target: # Still invalid, revert to original default or constraint
            min_target, max_target = min_default, max_default
            if "age" in field_name.lower() or "salary" in field_name.lower(): min_target = max(0, min_target)
            if min_target > max_target: return random.randint(0,100) # Absolute fallback

    return random.randint(min_target, max_target)

def _generate_float_value(constraint, field_name, pii_strategy, edge_condition=None):
    min_default, max_default = 1.0, 1000.0
    if constraint and validate_constraint("float", constraint):
        min_val_str, max_val_str = map(str.strip, constraint.split('-'))
        min_default, max_default = float(min_val_str), float(max_val_str)

    min_target, max_target = min_default, max_default

    if edge_condition:
        op = edge_condition['operator']
        try:
            val = float(edge_condition['value'])
            if op == '>': min_target = val + 0.01 # Small epsilon for float
            elif op == '<': max_target = val - 0.01
            elif op == '==': min_target, max_target = val, val
            elif op == '>=': min_target = val
            elif op == '<=': max_target = val
        except ValueError:
             st.warning(f"Edge case value '{edge_condition['value']}' for '{field_name}' is not a valid float. Ignoring edge case for this field.")


    if "age" in field_name.lower() or "salary" in field_name.lower() or "price" in field_name.lower():
        min_target = max(0.0, min_target)

    if min_target > max_target:
        if edge_condition and edge_condition.get('operator') == '==': return float(edge_condition['value']) # Exact value if possible
        st.warning(f"Edge case for '{field_name}' created an invalid float range ({min_target}-{max_target}). Attempting to adjust or use original constraint.")
        if edge_condition and edge_condition.get('operator') in ['>', '>=']: max_target = min_target + abs(min_target / 20.0 or 10.0) + 10.0
        elif edge_condition and edge_condition.get('operator') in ['<', '<=']: min_target = max_target - abs(max_target / 20.0 or 10.0) - 10.0
        if min_target > max_target:
            min_target, max_target = min_default, max_default
            if "age" in field_name.lower() or "salary" in field_name.lower() or "price" in field_name.lower(): min_target = max(0.0, min_target)
            if min_target > max_target: return round(random.uniform(0.0,100.0), 2)

    return round(random.uniform(min_target, max_target), 2)

def _generate_date_value(constraint, field_name, pii_strategy, edge_condition=None):
    start_default = datetime.now() - timedelta(days=365)
    end_default = datetime.now()

    if constraint and validate_constraint("date", constraint):
        start_date_str, end_date_str = map(str.strip, constraint.split('-'))
        try:
            start_default = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_default = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError:
            st.warning(f"Invalid date constraint format for '{field_name}'. Using default date range.")


    start_target, end_target = start_default, end_default

    if edge_condition:
        op = edge_condition['operator']
        try:
            val_date = datetime.strptime(str(edge_condition['value']), "%Y-%m-%d")
            if op == '>': start_target = val_date + timedelta(days=1)
            elif op == '<': end_target = val_date - timedelta(days=1)
            elif op == '==': start_target, end_target = val_date, val_date
            elif op == '>=': start_target = val_date
            elif op == '<=': end_target = val_date
        except ValueError:
             st.warning(f"Edge case value '{edge_condition['value']}' for '{field_name}' is not a valid date (YYYY-MM-DD). Ignoring edge case for this field.")


    if start_target > end_target:
        if edge_condition and edge_condition.get('operator') == '==': return val_date.strftime("%Y-%m-%d") # Exact value if possible
        st.warning(f"Edge case for '{field_name}' created an invalid date range. Using original constraint.")
        start_target, end_target = start_default, end_default
        if start_target > end_target: return fake.date_this_year().strftime("%Y-%m-%d") # Absolute fallback

    days_between = (end_target - start_target).days
    if days_between < 0: days_between = 0 # Should not happen if logic above is correct
    random_days = random.randint(0, days_between)
    return (start_target + timedelta(days=random_days)).strftime("%Y-%m-%d")

def _generate_category_value(constraint, field_name, pii_strategy, edge_condition=None):
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

def _apply_pii_strategy_to_value(value, field_type, pii_strategy):
    """Applies masking or redaction to a generated value based on the chosen strategy."""
    if pii_strategy == "masked":
        return mask_pii(value, field_type)
    elif pii_strategy == "redacted":
        return "[REDACTED]"
    # "realistic_fake" is the default if no other strategy applies or if value is already faked
    # "scramble_column" is handled *after* generation
    return value

def _generate_email_value(constraint, field_name, pii_strategy, edge_condition=None):
    # Edge cases for email (like '==') are less common for generation, but could be supported
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = fake.email()
    return _apply_pii_strategy_to_value(val, "email", pii_strategy)

def _generate_phone_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = f"+91 {random.randint(7000, 9999)}{random.randint(100000, 999999)}"
    return _apply_pii_strategy_to_value(val, "phone", pii_strategy)

def _generate_address_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = fake.address().replace('\n', ', ')
    # Address is typically faked, masking/redaction can be applied if needed via strategy
    return _apply_pii_strategy_to_value(val, "address", pii_strategy)

def _generate_name_value(constraint, field_name, pii_strategy, edge_condition=None):
    # This function now needs the full field_schema to access prefix/suffix
    # For simplicity in this diff, we'll assume field_schema is passed if called from generate_value
    # The call signature in VALUE_GENERATOR_FUNCTIONS might need adjustment if we pass full schema there.
    # For now, we'll assume field_name can be used to look up its schema if needed, or this logic moves.
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = fake.name()
    return _apply_pii_strategy_to_value(val, "name", pii_strategy)

def _generate_aadhaar_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = generate_aadhaar()
    return _apply_pii_strategy_to_value(val, "aadhaar", pii_strategy)

def _generate_pan_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = generate_pan()
    return _apply_pii_strategy_to_value(val, "pan", pii_strategy)

def _generate_passport_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = generate_passport()
    return _apply_pii_strategy_to_value(val, "passport", pii_strategy)

def _generate_voterid_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = generate_voter_id()
    return _apply_pii_strategy_to_value(val, "voterid", pii_strategy)

def _generate_ifsc_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = generate_ifsc()
    return _apply_pii_strategy_to_value(val, "ifsc", pii_strategy)

def _generate_upi_value(constraint, field_name, pii_strategy, edge_condition=None):
    if edge_condition and edge_condition.get('operator') == '==':
         val = str(edge_condition['value'])
    else:
        val = generate_upi()
    return _apply_pii_strategy_to_value(val, "upi", pii_strategy)

def _generate_animal_name_value(constraint, field_name, pii_strategy, edge_condition=None):
    """Generates a pet-like name."""
    if edge_condition and edge_condition.get('operator') == '==':
        return str(edge_condition['value'])
    # Using fake.first_name() as a proxy for pet names.
    # Could be expanded with a dedicated list of actual animal names.
    return fake.first_name()
    # Pet names are generally not PII, so no _apply_pii_strategy_to_value needed here.

# --- Constants for Domain-Specific Data Generation ---
DIAGNOSES_LIST = ["Hypertension", "Diabetes", "Asthma", "Arthritis", "Migraine",
                  "Bronchitis", "Anemia", "Pneumonia", "Sinusitis", "Depression", "Anxiety",
                  "Allergy", "Osteoporosis", "Glaucoma", "Eczema", "GERD", "COVID-19", "Influenza",
                  "Chronic Kidney Disease", "Hyperlipidemia", "Hypothyroidism", "Sleep Apnea", "Obesity"]
INSURANCE_PROVIDERS_LIST = ["United Health", "Aetna", "Blue Cross", "Cigna", "Humana",
                            "Kaiser Permanente", "Anthem", "Centene", "Molina Healthcare", "WellCare"]
BLOOD_TYPES_LIST = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
MEDICATIONS_LIST = ["Paracetamol", "Ibuprofen", "Amoxicillin", "Lisinopril", "Metformin",
                    "Atorvastatin", "Omeprazole", "Losartan", "Albuterol", "Gabapentin",
                    "Sertraline", "Amlodipine", "Simvastatin", "Hydrochlorothiazide", "Levothyroxine",
                    "Azithromycin", "Ciprofloxacin", "Prednisone", "Insulin Glargine", "Warfarin", "Clopidogrel"]
TRANSACTION_TYPES_LIST = ["Deposit", "Withdrawal", "Transfer", "Payment", "Refund", "Fee", "Interest"]
PRODUCT_NAMES_LIST = ["Laptop", "Smartphone", "Headphones", "Smartwatch", "Tablet",
                      "Camera", "Speaker", "Monitor", "Keyboard", "Mouse",
                      "Desk Chair", "Coffee Maker", "Blender", "Backpack", "Water Bottle",
                      "Running Shoes", "Yoga Mat", "Bluetooth Speaker", "External Hard Drive", "Webcam"]
PRODUCT_NAMES_LIST.extend(["Drone", "VR Headset", "Air Fryer", "Electric Scooter", "Fitness Tracker",
                           "Projector", "Robot Vacuum", "Security Camera System", "Portable SSD", "Gaming Console",
                           "Wireless Charger", "E-reader", "Digital Photo Frame", "Smart Thermostat", "Air Purifier",
                           "Electric Toothbrush", "Hair Dryer", "Instant Pot", "Microwave Oven", "Toaster", "Action Camera"])
PAYMENT_METHODS_LIST = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Cash on Delivery", "Wallet", "EMI"]
PRODUCT_CATEGORIES_LIST = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Beauty"]
SHIPPING_STATUSES_LIST = ["Pending", "Shipped", "Delivered", "Cancelled", "Returned"]
GRADES_LIST = ["A", "B", "C", "D", "F"]
SUBJECTS_LIST = ["Math", "Science", "English", "History", "Geography"]
DEPARTMENTS_LIST = ["IT", "HR", "Finance", "Marketing", "Operations"]
DEPARTMENTS_LIST.extend(["Legal", "Customer Support", "Research & Development", "Product Management", "Quality Assurance",
                         "Sales", "Supply Chain", "Administration", "Public Relations", "Design"])
POSITIONS_LIST = ["Manager", "Developer", "Analyst", "Designer", "Accountant",
                  "Consultant", "Specialist", "Coordinator", "Engineer", "Administrator",
                  "Director", "Vice President", "Executive", "Intern", "Team Lead", "Architect", "Scientist"]
DEGREES_LIST = ["B.Tech", "MBA", "B.Com", "B.A", "M.Sc"]
SKILLS_LIST = ["Python", "Java", "SQL", "Excel", "Communication"]
SKILLS_LIST.extend(["Project Management", "Data Analysis", "Machine Learning", "Cloud Computing", "Cybersecurity", "Agile Methodologies", "UI/UX Design",
                    "JavaScript", "React", "Node.js", "Angular", "Vue.js", "DevOps", "Kubernetes", "Docker", "Terraform",
                    "C++", "C#", ".NET", "PHP", "Ruby on Rails", "Go", "Swift", "Kotlin", "Mobile Development (iOS/Android)",
                    "Technical Writing", "Problem Solving", "Critical Thinking", "Leadership", "Teamwork", "Creativity",
                    "Digital Marketing", "SEO/SEM", "Content Creation", "Salesforce", "SAP", "Oracle", "Tableau", "Power BI"])
PROPERTY_TYPES_LIST = ["Apartment", "Villa", "Plot", "Office", "Shop"]
REALESTATE_STATUSES_LIST = ["Available", "Sold", "Rented", "Under Construction"]
AMENITIES_LIST = ["Swimming Pool", "Gym", "Park", "Security", "Play Area"]
FOOD_ITEMS_LIST = ["Pizza", "Burger", "Pasta", "Salad", "Fries", "Soda", "Sushi", "Tacos", "Biryani", "Noodles", "Sandwich", "Ice Cream",
                   "Salad Bowl", "Smoothie", "Coffee", "Tea", "Milkshake", "Wrap", "Steak", "Seafood Platter", "Dim Sum", "Ramen", "Curry",
                   "Dosa", "Idli", "Vada", "Samosa", "Spring Roll", "Momo", "Fried Chicken", "Hot Dog", "Pancakes", "Waffles",
                   "Omelette", "Cereal", "Yogurt", "Fruit Salad", "Juice", "Cake", "Pastry", "Cookie", "Donut", "Muffin"]
RESTAURANT_TYPES_LIST = ["Cafe", "Fine Dining", "Fast Food", "Pizzeria", "Bakery", "Cloud Kitchen"] # For restaurant name generation
DELIVERY_STATUSES_LIST = ["Order Placed", "Preparing", "Out for Delivery", "Delivered", "Cancelled by User", "Cancelled by Restaurant", "Delayed"]
ACADEMIC_JOURNALS_LIST = ["Nature", "Science", "Cell", "The Lancet", "JAMA", "IEEE Transactions", "Physical Review Letters",
                          "New England Journal of Medicine (NEJM)", "PNAS", "BMJ", "Nature Communications", "Journal of the American Chemical Society (JACS)",
                          "Angewandte Chemie", "Advanced Materials", "Nature Medicine", "Science Advances", "Cell Host & Microbe", "Immunity"]
COMMON_HASHTAGS_LIST = ["#instagood", "#photooftheday", "#love", "#travel", "#tech", "#science", "#innovation", "#news", "#health",
                        "#business", "#startup", "#motivation", "#art", "#foodie", "#fitness"]
SENSOR_TYPES_LIST = ["Temperature", "Humidity", "Pressure", "Light", "Motion", "GPS",
                     "Accelerometer", "Gyroscope", "Proximity", "Sound Level", "Air Quality", "CO2 Sensor",
                     "Water Flow", "Soil Moisture", "Radiation", "Magnetic Field", "Vibration", "Ultrasonic"]
SPECIES_LIST = ["Dog", "Cat", "Bird", "Fish", "Lion", "Tiger", "Elephant", "Bear", "Rabbit", "Horse", "Cow", "Sheep",
                "Deer", "Fox", "Wolf", "Monkey", "Snake", "Lizard", "Frog", "Turtle", "Shark", "Whale", "Dolphin",
                "Eagle", "Owl", "Penguin", "Crocodile", "Alligator", "Spider", "Ant", "Bee", "Butterfly"]
COMMON_DOG_BREEDS_LIST = ["Labrador Retriever", "German Shepherd", "Golden Retriever", "Bulldog", "Poodle", "Beagle"]
COMMON_CAT_BREEDS_LIST = ["Siamese", "Persian", "Maine Coon", "Ragdoll", "Bengal", "Sphynx"]
LOGISTICS_CARRIER_SUFFIXES_LIST = ["Logistics", "Shipping Lines", "Freight", "Express", "Carriers", "Transport", "Movers"]
LOGISTICS_SHIPMENT_STATUSES_LIST = ["Processing", "In Transit", "Out for Delivery", "Delivered",
                                    "Delayed", "Held at Customs", "Returned to Sender", "Exception",
                                    "Pending Pickup", "At Origin Facility", "At Destination Facility"]
HABITAT_LIST = ["Forest", "Desert", "Ocean", "Grassland", "Mountain", "Domestic", "Urban", "Arctic",
                "Jungle", "Savanna", "Wetland", "River", "Lake", "Cave", "Coral Reef", "Tundra", "Taiga", "Swamp"]
PUBLICATION_TYPES_LIST = ["Journal Article", "Conference Paper", "Book Chapter", "Preprint", "Thesis",
                          "Review Article", "Case Study", "Technical Report", "Poster Presentation", "Editorial",
                          "Letter to Editor", "Book Review", "Dataset Paper", "Software Paper", "Patent"]

# Travel & Tourism Domain Lists
TRAVEL_DESTINATIONS_LIST = ["Paris", "Rome", "London", "New York", "Tokyo", "Dubai", "Bali", "Barcelona", "Amsterdam", "Sydney", "Bangkok", "Singapore", "Venice", "Prague", "Vienna", "Berlin", "San Francisco", "Los Angeles", "Miami", "Chicago", "Toronto", "Vancouver", "Mexico City", "Rio de Janeiro", "Buenos Aires", "Cairo", "Cape Town", "Mumbai", "Delhi", "Beijing", "Shanghai", "Seoul", "Moscow", "Istanbul"]
AIRLINE_NAMES_LIST = ["Emirates", "Qatar Airways", "Singapore Airlines", "ANA All Nippon Airways", "Qantas Airways", "Lufthansa", "British Airways", "Delta Air Lines", "American Airlines", "United Airlines", "Air France", "KLM", "Turkish Airlines", "Cathay Pacific", "IndiGo", "Southwest Airlines"]
HOTEL_AMENITIES_LIST = ["WiFi", "Swimming Pool", "Gym", "Spa", "Restaurant", "Bar", "Room Service", "Parking", "Air Conditioning", "Breakfast Included", "Airport Shuttle", "Pet Friendly", "Business Center", "Concierge"]
ROOM_TYPES_LIST = ["Standard Room", "Deluxe Room", "Suite", "Family Room", "Single Room", "Double Room", "King Room", "Queen Room", "Studio", "Apartment", "Villa", "Bungalow"]
TRAVEL_BOOKING_STATUSES_LIST = ["Confirmed", "Pending", "Cancelled", "Modified", "Completed", "No-Show", "Waitlisted"]
TRAVEL_ACTIVITY_TYPES_LIST = ["Sightseeing Tour", "Museum Visit", "Adventure Sport", "Cooking Class", "Wine Tasting", "Cultural Show", "Shopping Trip", "Beach Relaxation", "Hiking", "Cruise"]



GENERAL_CATEGORIES_LIST = ["Category A", "Category B", "Category C", "Category D"]
GENERAL_STATUSES_LIST = ["Active", "Inactive", "Pending", "Completed"]

# --- Field Generator Dispatch Dictionary ---
# This will be replaced by CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP and generate_value
# FIELD_GENERATORS = { ... } # Removed for brevity, will be deprecated

# --- NEW: Map of Canonical Field Names to their Schema Details (Type, Constraint) ---
# This map will be used by the refactored generate_synthetic_data function
CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP = {
    # General & Common
    "id": {"type": "string", "constraint": "", "is_generic_numeric_id": True, "display_name": "ID"},
    "name": {"type": "name", "constraint": "", "display_name": "Name"},
    "age": {"type": "int", "constraint": "18-80", "display_name": "Age"},
    "gender": {"type": "category", "constraint": "Male,Female,Other", "display_name": "Gender"},
    "email": {"type": "email", "constraint": "", "display_name": "Email"},
    "phone": {"type": "phone", "constraint": "", "display_name": "Phone"},
    "address": {"type": "address", "constraint": "", "display_name": "Address"},
    "date": {"type": "date", "constraint": "", "display_name": "Date"}, # Generic date
    "value": {"type": "float", "constraint": "10-1000", "display_name": "Value"},
    "category": {"type": "category", "constraint": ",".join(GENERAL_CATEGORIES_LIST), "display_name": "Category"},
    "description": {"type": "string", "constraint": "", "display_name": "Description"}, # Uses fake.sentence()
    "status": {"type": "category", "constraint": ",".join(GENERAL_STATUSES_LIST), "display_name": "Status"},
    "score": {"type": "float", "constraint": "0-100", "display_name": "Score"},
    "city": {"type": "string", "constraint": "", "is_faker_city": True, "display_name": "City"},
    "state": {"type": "string", "constraint": "", "is_faker_state": True, "display_name": "State"},
    "country": {"type": "string", "constraint": "", "is_faker_country": True, "display_name": "Country"},
    "pincode": {"type": "string", "constraint": "", "is_faker_postcode": True, "display_name": "Pincode"}, # also zipcode
    "zipcode": {"type": "string", "constraint": "", "is_faker_postcode": True, "display_name": "Zipcode"},
    "currency": {"type": "string", "constraint": "", "is_faker_currency_code": True, "display_name": "Currency"},
    "job": {"type": "string", "constraint": "", "is_faker_job": True, "display_name": "Job Title"},
    "company": {"type": "string", "constraint": "", "is_faker_company": True, "display_name": "Company"},
    "aadhaar": {"type": "aadhaar", "constraint": "", "display_name": "Aadhaar"},
    "pan": {"type": "pan", "constraint": "", "display_name": "PAN"},
    "passport": {"type": "passport", "constraint": "", "display_name": "Passport"},
    "voterid": {"type": "voterid", "constraint": "", "display_name": "Voter ID"},
    "ifsc": {"type": "ifsc", "constraint": "", "display_name": "IFSC Code"}, # also ifsc_code
    "upi": {"type": "upi", "constraint": "", "display_name": "UPI ID"}, # also upi_id

    # Hospital Domain
    "patient_id": {"type": "string", "constraint": "", "is_generic_numeric_id": True, "display_name": "Patient ID"},
    "doctor_name": {"type": "name", "constraint": "", "prefix": "Dr.", "display_name": "Doctor Name"}, # Note: space after Dr. handled in generation
    "hospital_name": {"type": "string", "constraint": "", "suffix": " Hospital", "is_faker_company": True, "display_name": "Hospital Name"},
    "diagnosis": {"type": "category", "constraint": ",".join(DIAGNOSES_LIST), "display_name": "Diagnosis"},
    "admission_date": {"type": "date", "constraint": "", "display_name": "Admission Date"}, # Needs relative date logic if "discharge_date" is also present
    "discharge_date": {"type": "date", "constraint": "", "display_name": "Discharge Date"},
    "room_number": {"type": "string", "constraint": "", "is_room_number_pattern": True, "display_name": "Room Number"}, # e.g., "101A"
    "insurance_provider": {"type": "category", "constraint": ",".join(INSURANCE_PROVIDERS_LIST), "display_name": "Insurance Provider"},
    "blood_type": {"type": "category", "constraint": ",".join(BLOOD_TYPES_LIST), "display_name": "Blood Type"},
    "medication": {"type": "category", "constraint": ",".join(MEDICATIONS_LIST), "display_name": "Medication"},

    # Finance Domain (Example, expand as needed)
    "transaction_id": {"type": "string", "constraint": "", "is_generic_numeric_id": True, "display_name": "Transaction ID"},
    "account_number": {"type": "string", "constraint": "digits:10-12", "display_name": "Account Number"}, # Custom constraint type
    "bank_name": {"type": "string", "constraint": "", "is_faker_company": True, "suffix": " Bank", "display_name": "Bank Name"},
    "balance": {"type": "float", "constraint": "-5000-50000", "display_name": "Balance"},
    "reference_number": {"type": "string", "constraint": "", "is_reference_number_pattern": True, "display_name": "Reference Number"},
    "amount": {"type": "float", "constraint": "100-10000", "display_name": "Amount"},
    "salary": {"type": "int", "constraint": "20000-200000", "display_name": "Salary"},

    # Food Delivery Domain
    "restaurant_name": {"type": "string", "constraint": "", "is_faker_company": True, "suffix_from_list": RESTAURANT_TYPES_LIST, "display_name": "Restaurant Name"},
    "food_items": {"type": "category", "constraint": ",".join(FOOD_ITEMS_LIST), "display_name": "Food Items"}, # Could also be a multi-select or string for comma-separated items
    "order_total": {"type": "float", "constraint": "100-2000", "display_name": "Order Total (INR)"},
    "delivery_agent_name": {"type": "name", "constraint": "", "display_name": "Delivery Agent Name"},
    "delivery_time_minutes": {"type": "int", "constraint": "15-75", "display_name": "Delivery Time (Minutes)"},
    "delivery_rating": {"type": "int", "constraint": "1-5", "display_name": "Delivery Rating"},
    "delivery_address": {"type": "address", "constraint": "", "display_name": "Delivery Address"}, # Already covered by general address
    "payment_mode": {"type": "category", "constraint": ",".join(PAYMENT_METHODS_LIST), "display_name": "Payment Mode"}, # Re-use from e-commerce
    "delivery_status": {"type": "category", "constraint": ",".join(DELIVERY_STATUSES_LIST), "display_name": "Delivery Status"},

    # Education Domain
    "student_id": {"type": "string", "constraint": "", "is_generic_numeric_id": True, "display_name": "Student ID"},
    "school_name": {"type": "string", "constraint": "", "is_faker_company": True, "suffix": " School", "display_name": "School Name"},
    "teacher_name": {"type": "name", "constraint": "", "prefix_options": ["Mr.", "Ms.", "Dr."], "display_name": "Teacher Name"},
    "attendance": {"type": "string", "constraint": "70-100", "is_percentage_pattern": True, "display_name": "Attendance"},

    # Employee Domain
    "employee_id": {"type": "string", "constraint": "", "is_generic_numeric_id": True, "display_name": "Employee ID"},

    # Real Estate Domain
    "property_id": {"type": "string", "constraint": "", "is_generic_numeric_id": True, "display_name": "Property ID"},
    "area": {"type": "string", "constraint": "500-3000", "unit": "sq.ft.", "is_measurement_pattern": True, "display_name": "Area"},
    "year_built": {"type": "int", "constraint": "1990-2023", "display_name": "Year Built"},

    # E-commerce (some fields might be general or already covered)
    "order_id": {"type": "string", "constraint": "", "is_generic_numeric_id": True, "display_name": "Order ID"},
    "customer_name": {"type": "name", "constraint": "", "display_name": "Customer Name"},
    "product_name": {"type": "category", "constraint": ",".join(PRODUCT_NAMES_LIST), "display_name": "Product Name"},
    "price": {"type": "float", "constraint": "100-5000", "display_name": "Price"},
    "quantity": {"type": "int", "constraint": "1-10", "display_name": "Quantity"},
    "product_category": {"type": "category", "constraint": ",".join(PRODUCT_CATEGORIES_LIST), "display_name": "Product Category"},
    "discount": {"type": "float", "constraint": "0-0.5", "display_name": "Discount"}, # as a percentage
    "shipping_status": {"type": "category", "constraint": ",".join(SHIPPING_STATUSES_LIST), "display_name": "Shipping Status"},
    # ... Add ALL other canonical fields from FIELD_GENERATORS here, mapping them to a type and constraint

    # Academic/Research Domain
    "publication_title": {"type": "string", "constraint": "", "is_faker_sentence": True, "display_name": "Publication Title"}, # Use sentence for title
    "author_names": {"type": "name", "constraint": "", "is_multi_name": True, "display_name": "Author Names"}, # Special handling for multiple authors
    "journal_name": {"type": "category", "constraint": ",".join(ACADEMIC_JOURNALS_LIST), "display_name": "Journal Name"},
    "publication_year": {"type": "int", "constraint": "2000-2024", "display_name": "Publication Year"},
    "citation_count": {"type": "int", "constraint": "0-1000", "display_name": "Citation Count"},
    "doi": {"type": "string", "constraint": "", "is_doi_pattern": True, "display_name": "DOI"},
    "keywords": {"type": "string", "constraint": "", "is_keywords_list": True, "display_name": "Keywords"}, # Comma-separated list of words
    "publication_type": {"type": "category", "constraint": ",".join(PUBLICATION_TYPES_LIST), "display_name": "Publication Type"},

    # Social Media Domain
    "username": {"type": "string", "constraint": "", "is_faker_user_name": True, "display_name": "Username"},
    "post_text": {"type": "string", "constraint": "", "is_faker_paragraph": True, "display_name": "Post Text"},
    "like_count": {"type": "int", "constraint": "0-10000", "display_name": "Like Count"},
    "share_count": {"type": "int", "constraint": "0-5000", "display_name": "Share Count"},
    "comment_text": {"type": "string", "constraint": "", "is_faker_sentence": True, "display_name": "Comment Text"},
    "hashtags": {"type": "category", "constraint": ",".join(COMMON_HASHTAGS_LIST), "is_multi_category": True, "display_name": "Hashtags"},

    # IoT/Sensor Domain
    "sensor_id": {"type": "string", "constraint": "", "is_generic_alphanum_id": True, "prefix": "SENSOR-", "display_name": "Sensor ID"},
    "timestamp": {"type": "date", "constraint": "datetime", "display_name": "Timestamp"}, # Special constraint for datetime
    "temperature": {"type": "float", "constraint": "-20.0-50.0", "unit": "°C", "is_measurement_pattern": True, "display_name": "Temperature"},
    "humidity": {"type": "float", "constraint": "0.0-100.0", "unit": "%", "is_measurement_pattern": True, "display_name": "Humidity"},
    "latitude": {"type": "float", "constraint": "-90.0-90.0", "is_faker_latitude": True, "display_name": "Latitude"},
    "longitude": {"type": "float", "constraint": "-180.0-180.0", "is_faker_longitude": True, "display_name": "Longitude"},
    "sensor_type": {"type": "category", "constraint": ",".join(SENSOR_TYPES_LIST), "display_name": "Sensor Type"},

    # Animal Data Domain
    "animal_name": {"type": "animal_name", "constraint": "", "display_name": "Animal Name"}, # Changed type to "animal_name"
    "species": {"type": "category", "constraint": ",".join(SPECIES_LIST), "display_name": "Species"},
    "breed": {"type": "category", "constraint": ",".join(COMMON_DOG_BREEDS_LIST + COMMON_CAT_BREEDS_LIST), "display_name": "Breed"}, # Combine or make dynamic
    "animal_age": {"type": "int", "constraint": "0-25", "display_name": "Animal Age (Years)"},
    "habitat": {"type": "category", "constraint": ",".join(HABITAT_LIST), "display_name": "Habitat"},
    "animal_weight_kg": {"type": "float", "constraint": "0.1-1000", "display_name": "Weight (kg)"},
    "animal_color": {"type": "string", "constraint": "", "is_faker_color_name": True, "display_name": "Color"},

    # Logistics/Supply Chain Domain
    "shipment_id": {"type": "string", "constraint": "", "is_generic_alphanum_id": True, "prefix": "SHP-", "display_name": "Shipment ID"},
    "tracking_number": {"type": "string", "constraint": "", "is_tracking_number_pattern": True, "display_name": "Tracking Number"},
    "carrier_name": {"type": "string", "constraint": "", "is_faker_company": True, "suffix_from_list": LOGISTICS_CARRIER_SUFFIXES_LIST, "display_name": "Carrier Name"},
    "origin_location": {"type": "address", "constraint": "", "display_name": "Origin Location"}, # Reuses address type
    "destination_location": {"type": "address", "constraint": "", "display_name": "Destination Location"}, # Reuses address type
    "shipment_status_logistics": {"type": "category", "constraint": ",".join(LOGISTICS_SHIPMENT_STATUSES_LIST), "display_name": "Shipment Status"},
    "freight_cost": {"type": "float", "constraint": "50-5000", "display_name": "Freight Cost"},
    "estimated_delivery_date": {"type": "date", "constraint": "", "display_name": "Estimated Delivery Date"},
    "actual_delivery_date": {"type": "date", "constraint": "", "display_name": "Actual Delivery Date"},
    "package_weight_kg": {"type": "float", "constraint": "0.1-1000", "unit": "kg", "is_measurement_pattern": True, "display_name": "Package Weight (kg)"}, # Reused from animal, good generic
    "package_dimensions_cm": {"type": "string", "constraint": "", "is_dimension_pattern": True, "display_name": "Package Dimensions (cm)"},

    # Travel & Tourism Domain
    "booking_id": {"type": "string", "constraint": "", "is_generic_alphanum_id": True, "prefix": "BKG-", "display_name": "Booking ID"},
    "traveler_name": {"type": "name", "constraint": "", "display_name": "Traveler Name"},
    "destination_city_travel": {"type": "category", "constraint": ",".join(TRAVEL_DESTINATIONS_LIST), "is_faker_city_if_empty_constraint": True, "display_name": "Destination City"},
    "origin_city_travel": {"type": "category", "constraint": ",".join(TRAVEL_DESTINATIONS_LIST), "is_faker_city_if_empty_constraint": True, "display_name": "Origin City"},
    "travel_date": {"type": "date", "constraint": "", "display_name": "Travel Date"}, # Departure date
    "return_date": {"type": "date", "constraint": "", "display_name": "Return Date"}, # Needs to be after travel_date
    "flight_number": {"type": "string", "constraint": "", "is_flight_number_pattern": True, "display_name": "Flight Number"},
    "airline_name": {"type": "category", "constraint": ",".join(AIRLINE_NAMES_LIST), "is_faker_company_if_empty_constraint": True, "suffix": " Airlines", "display_name": "Airline Name"},
    "hotel_name": {"type": "string", "constraint": "", "is_faker_company": True, "suffix_options": [" Hotel", " Resort", " Inn", " Lodge", " Suites"], "display_name": "Hotel Name"},
    "room_type": {"type": "category", "constraint": ",".join(ROOM_TYPES_LIST), "display_name": "Room Type"},
    "booking_status_travel": {"type": "category", "constraint": ",".join(TRAVEL_BOOKING_STATUSES_LIST), "display_name": "Booking Status"},
    "total_travel_cost": {"type": "float", "constraint": "200-10000", "display_name": "Total Cost (USD)"}, # Assuming USD for now
    "travel_package_name": {"type": "string", "constraint": "", "is_faker_bs": True, "prefix": "Package: ", "display_name": "Travel Package Name"}, # Using bs for catchy names
    "hotel_amenities_included": {"type": "category", "constraint": ",".join(HOTEL_AMENITIES_LIST), "is_multi_category": True, "display_name": "Hotel Amenities"},
    "travel_activity": {"type": "category", "constraint": ",".join(TRAVEL_ACTIVITY_TYPES_LIST), "display_name": "Activity Booked"},

    # This is a crucial step for the refactor to work comprehensively.
}

FIELD_GENERATORS = {
    "patient_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "transaction_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "order_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)], # Will be caught by is_generic_numeric_id
    "student_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "employee_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "property_id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)],
    "id": lambda nr: [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(nr)], # Will be caught by is_generic_numeric_id
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

    # Food Delivery Synonyms
    "restaurant": "restaurant_name", "eatery name": "restaurant_name", "food place": "restaurant_name",
    "items ordered": "food_items", "dishes": "food_items", "menu items": "food_items",
    "bill amount": "order_total", "total cost": "order_total",
    "delivery boy name": "delivery_agent_name", "rider name": "delivery_agent_name", "delivery person": "delivery_agent_name",
    "restaurant name": "restaurant_name", # Added for exact phrase match
    "food items": "food_items",           # Added for exact phrase match
    "delivery agent": "delivery_agent_name", # Added for common phrase match
    "delivery agent name": "delivery_agent_name", # Added for exact phrase match
    "time to deliver": "delivery_time_minutes", "estimated delivery time": "delivery_time_minutes",
    "customer rating for delivery": "delivery_rating",
    "drop address": "delivery_address",
    "how paid": "payment_mode",
    "order current status": "delivery_status", "status of delivery": "delivery_status",
    **{key: key for key in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP.keys()}, # Canonical names are their own primary synonym

    # Academic/Research Synonyms
    "paper title": "publication_title", "article name": "publication_title",
    "authors": "author_names", "researchers": "author_names",
    "published in": "journal_name",
    "year of publication": "publication_year",
    "citations": "citation_count", "cited by": "citation_count",
    "digital object identifier": "doi",
    "research keywords": "keywords", "tags": "keywords", # 'tags' also used in social media
    "type of publication": "publication_type",

    # Social Media Synonyms
    "user name": "username", "handle": "username", "screen name": "username",
    "post content": "post_text", "tweet text": "post_text",
    "likes": "like_count", "number of likes": "like_count",
    "shares": "share_count", "retweets": "share_count",
    "comment": "comment_text", "reply": "comment_text",
    # "hashtags" is direct

    # IoT/Sensor Synonyms
    "device id": "sensor_id",
    "reading time": "timestamp", "event time": "timestamp",
    "temp": "temperature",
    # "humidity", "latitude", "longitude", "sensor_type" are fairly direct

    # Animal Data Synonyms
    "animal": "animal_name", # General term, might default to name
    "animal species": "species", "type of animal": "species",
    "animal breed": "breed",
    "age of animal": "animal_age",
    "natural environment": "habitat", "lives in": "habitat",
    "animal weight": "animal_weight_kg",
    "fur color": "animal_color", "coat color": "animal_color",
}
FIELD_SYNONYM_TO_CANONICAL_MAP.update({
    # Logistics Synonyms
    "shipment number": "shipment_id", "consignment id": "shipment_id",
    "tracking id": "tracking_number", "awb number": "tracking_number", "air waybill": "tracking_number",
    "shipping company": "carrier_name", "freight carrier": "carrier_name", "courier": "carrier_name",
    "pickup location": "origin_location", "despatch point": "origin_location", "from address": "origin_location", "origin": "origin_location",
    "delivery location": "destination_location", "drop-off point": "destination_location", "to address": "destination_location", "destination": "destination_location",
    "logistics status": "shipment_status_logistics", "delivery progress": "shipment_status_logistics",
    "shipping cost": "freight_cost", "transportation charges": "freight_cost",
    "edd": "estimated_delivery_date", "expected delivery": "estimated_delivery_date",
    "add": "actual_delivery_date", "delivered on": "actual_delivery_date",
    "parcel weight": "package_weight_kg", "shipment weight": "package_weight_kg",
    "box size": "package_dimensions_cm", "package size": "package_dimensions_cm", "dimensions": "package_dimensions_cm",
})
FIELD_SYNONYM_TO_CANONICAL_MAP.update({
    # Travel & Tourism Synonyms
    "booking reference": "booking_id", "reservation id": "booking_id", "confirmation number": "booking_id",
    "passenger name": "traveler_name", "guest name": "traveler_name",
    "travel destination": "destination_city_travel", "going to": "destination_city_travel", "arrival city": "destination_city_travel",
    "departure city": "origin_city_travel", "flying from": "origin_city_travel", "source city": "origin_city_travel",
    "departure date": "travel_date", "check-in date": "travel_date", "start date": "travel_date",
    "arrival date": "return_date", "check-out date": "return_date", "end date": "return_date", # Can be ambiguous, but common
    "flight code": "flight_number", "flight id": "flight_number",
    "airline company": "airline_name", "carrier": "airline_name", # 'carrier' also in logistics
    "accommodation name": "hotel_name", "place to stay": "hotel_name", "resort name": "hotel_name",
    "room category": "room_type", "type of room": "room_type",
    "reservation status": "booking_status_travel", "booking state": "booking_status_travel",
    "trip cost": "total_travel_cost", "package price": "total_travel_cost", "total fare": "total_travel_cost",
    "tour package": "travel_package_name", "vacation package": "travel_package_name",
    "hotel features": "hotel_amenities_included", "included services": "hotel_amenities_included",
    "booked activity": "travel_activity", "excursion": "travel_activity", "tour name": "travel_activity",
})

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
    parsed_schema_fields = [] # This will hold {"name": display_name, "type": type, "constraint": constraint, ...}
    detected_pii = []
    detected_dpdp = []

    # Parse number of rows
    match_rows = re.search(r"(\d+)\s*(rows|records|entries|row|record|entry)", description, re.IGNORECASE)
    if match_rows:
        num_rows = int(match_rows.group(1))
        description = description.replace(match_rows.group(0), "", 1).strip() # Remove row specifier from description

    # PROMPT_FIELD_CONFIG was here, but it's deprecated and removed.


    # --- New Parsing Logic using FIELD_SYNONYM_TO_CANONICAL_MAP and CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP ---
    remaining_description = description.lower()
    # Sort synonyms by length (descending) to match longer phrases first
    sorted_synonyms = sorted(FIELD_SYNONYM_TO_CANONICAL_MAP.keys(), key=len, reverse=True)
    
    # Split prompt by common delimiters like ",", "and", "with" to isolate potential field names
    # This is a simplification; more advanced NLP would be better.
    potential_field_phrases = re.split(r'\s*(?:,|and|with)\s*', remaining_description)
    
    processed_canonical_fields = set()

    for phrase in potential_field_phrases:
        phrase = phrase.strip()
        if not phrase:
            continue
        
        matched_canonical = None
        # Try to match the phrase (or parts of it) against synonyms
        for user_synonym in sorted_synonyms:
            if user_synonym in phrase: # Check if synonym is part of the current phrase
                canonical_field = FIELD_SYNONYM_TO_CANONICAL_MAP[user_synonym]
                if canonical_field in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP and canonical_field not in processed_canonical_fields:
                    matched_canonical = canonical_field
                    # Remove the matched synonym part from the phrase to avoid re-matching subsets
                    # This is tricky and might need refinement. For now, we assume one field per phrase segment.
                    # phrase = phrase.replace(user_synonym, "", 1).strip() 
                    break 
        
        if matched_canonical:
            schema_detail = CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP[matched_canonical]
            parsed_schema_fields.append({
                "name": schema_detail.get("display_name", matched_canonical.replace("_", " ").title()),
                "type": schema_detail["type"],
                "constraint": schema_detail["constraint"],
                "pii_handling": st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake"), # Default PII handling
                "_original_canonical": matched_canonical # Store for potential special handling
            })
            processed_canonical_fields.add(matched_canonical)
            # Add to detected PII/DPDP lists
            display_name = schema_detail.get("display_name", matched_canonical.replace("_", " ").title())
            if display_name in PII_FIELDS or matched_canonical in PII_FIELDS: # Check both
                if display_name not in detected_pii: detected_pii.append(display_name)
            if is_dpdp_pii(display_name) or is_dpdp_pii(matched_canonical):
                if display_name not in detected_dpdp: detected_dpdp.append(display_name)

    # Ensure we have at least some columns for simple generation
    if not parsed_schema_fields:
        # Check if the prompt was *only* for rows (e.g., "10 rows")
        # Remove digits and common row-specifying words to see if anything substantial is left
        prompt_content_check = re.sub(r'\d+', '', description).lower()
        prompt_content_check = prompt_content_check.replace("rows", "").replace("row", "").replace("records", "").replace("record", "").replace("entries", "").replace("entry", "").strip()
        
        if not prompt_content_check: # User likely just asked for a number of rows
            st.info(f"No specific fields requested. Generating a default dataset with {num_rows} rows (ID, Random Text, Random Number).")
            data = {
                "ID": [i + 1 for i in range(num_rows)],
                "Random Text": [fake.word() for _ in range(num_rows)],
                "Random Number": [random.randint(1, 100) for _ in range(num_rows)]
            }
            synthetic_df = pd.DataFrame(data)
            return synthetic_df
        else: # User provided other words, but they weren't recognized
            st.error(
                "No valid columns detected from your prompt for simple generation. "
                "Please use keywords like name, age, salary, email, state, country, etc., or try the Smart Schema Editor for more control."
            )
            return None

    # Generate data using the parsed schema
    data = {}
    for field_schema_item in parsed_schema_fields:
        col_display_name = field_schema_item["name"]
        # Special handling for Faker direct calls if specified in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP
        # This is a bridge for simple Faker calls that don't fit neatly into generate_value types
        # (e.g. city, state, country, job, company, currency)
        canonical_key = field_schema_item.get("_original_canonical")
        schema_details_for_canonical = CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP.get(canonical_key, {})

        if schema_details_for_canonical.get("is_faker_city"):
            data[col_display_name] = [fake.city() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_state"):
            data[col_display_name] = [fake.state() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_country"):
            data[col_display_name] = [fake.country() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("suffix_from_list") and schema_details_for_canonical.get("is_faker_company"): # More specific first
            # For fields like restaurant_name that combine a fake company with a suffix from a list
            suffix_list = schema_details_for_canonical["suffix_from_list"]
            data[col_display_name] = [f"{fake.company()} {random.choice(suffix_list)}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_company"): # General company name
            base_names = [fake.company() for _ in range(num_rows)]
            prefix = schema_details_for_canonical.get("prefix", "")
            suffix = schema_details_for_canonical.get("suffix", "")
            if prefix and not prefix.endswith(" "): prefix += " "
            if suffix and not suffix.startswith(" "): suffix = " " + suffix
            data[col_display_name] = [f"{prefix}{name}{suffix}".strip() for name in base_names]
        elif schema_details_for_canonical.get("is_faker_postcode"):
            data[col_display_name] = [fake.postcode() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_currency_code"):
            data[col_display_name] = [fake.currency_code() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_job"):
            data[col_display_name] = [fake.job() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_generic_numeric_id"):
            data[col_display_name] = [f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_room_number_pattern"):
            data[col_display_name] = [f"{random.randint(1, 20)}{random.choice(['A', 'B', 'C', 'D'])}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_percentage_pattern"):
            constraint = schema_details_for_canonical.get("constraint", "0-100")
            min_val, max_val = map(int, constraint.split('-'))
            data[col_display_name] = [f"{random.randint(min_val, max_val)}%" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_measurement_pattern"):
            constraint = schema_details_for_canonical.get("constraint", "1-100")
            unit = schema_details_for_canonical.get("unit", "")
            min_val, max_val = map(int, constraint.split('-'))
            data[col_display_name] = [f"{random.randint(min_val, max_val)} {unit}".strip() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_reference_number_pattern"):
            data[col_display_name] = [f"REF{random.randint(10000, 99999)}{random.randint(100, 999)}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_sentence"):
            data[col_display_name] = [fake.sentence() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_paragraph"):
            data[col_display_name] = [fake.paragraph(nb_sentences=3) for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_user_name"):
            data[col_display_name] = [fake.user_name() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_latitude"):
            data[col_display_name] = [fake.latitude() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_longitude"):
            data[col_display_name] = [fake.longitude() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_color_name"):
            data[col_display_name] = [fake.color_name() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_doi_pattern"):
            data[col_display_name] = [f"10.{random.randint(1000,9999)}/{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_generic_alphanum_id"):
            prefix = schema_details_for_canonical.get("prefix", "")
            data[col_display_name] = [f"{prefix}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_keywords_list"):
            data[col_display_name] = [", ".join(fake.words(nb=random.randint(2,5))) for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_tracking_number_pattern"):
            data[col_display_name] = [f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}{random.randint(100000000, 999999999)}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_dimension_pattern"):
            data[col_display_name] = [f"{random.randint(10,100)}x{random.randint(10,100)}x{random.randint(5,50)} cm" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_flight_number_pattern"):
            data[col_display_name] = [f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}{random.randint(100, 9999)}" for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_multi_name"): # For author lists
            data[col_display_name] = ["; ".join([fake.name() for _ in range(random.randint(1,4))]) for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_multi_category"): # For hashtags
            categories = schema_details_for_canonical.get("constraint", "").split(',')
            if categories and categories[0]: # Check if categories list is not empty or just an empty string
                data[col_display_name] = [", ".join(random.sample(categories, k=random.randint(1, min(3, len(categories))))) for _ in range(num_rows)]
            else: # Fallback if constraint is empty for multi_category
                data[col_display_name] = [fake.word() for _ in range(num_rows)]
        elif schema_details_for_canonical.get("is_faker_city_if_empty_constraint"):
            categories = schema_details_for_canonical.get("constraint", "").split(',')
            if categories and categories[0] and categories[0].strip():
                data[col_display_name] = [random.choice(categories) for _ in range(num_rows)]
            else:
                data[col_display_name] = [fake.word() for _ in range(num_rows)]

        else:
            # For types like "name" that might have prefix/suffix, pass the schema_details
            if field_schema_item["type"] == "name":
                 # Temporarily override field_schema_item for generate_value to include details from CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP
                 # This is a bit of a hack; ideally generate_value always gets the full effective schema for the field.
                 effective_schema_for_name = {**field_schema_item, **schema_details_for_canonical}
                 data[col_display_name] = [generate_value(effective_schema_for_name) for _ in range(num_rows)]
            else:
                 data[col_display_name] = [generate_value(field_schema_item) for _ in range(num_rows)]

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

# --- Value Generation Dispatcher ---
VALUE_GENERATOR_FUNCTIONS = {
    "string": _generate_string_value,
    "int": _generate_int_value,
    "float": _generate_float_value,
    "date": _generate_date_value,
    "category": _generate_category_value,
    "email": _generate_email_value,
    "phone": _generate_phone_value,
    "address": _generate_address_value,
    "name": _generate_name_value, # _generate_name_value will be enhanced
    "aadhaar": _generate_aadhaar_value,
    "pan": _generate_pan_value,
    "passport": _generate_passport_value,
    "voterid": _generate_voterid_value,
    "ifsc": _generate_ifsc_value,
    "upi": _generate_upi_value,
    "animal_name": _generate_animal_name_value, # Registering the new generator
}

def get_field_pii_strategy(field_schema, global_default_strategy):
    """Determines the PII handling strategy for a field."""
    # Field-specific strategy overrides global default
    return field_schema.get("pii_handling", global_default_strategy)

def generate_value(field_schema, edge_condition=None):
    """Generate a random value based on field type and constraint using a dispatch dictionary."""
    field_type = field_schema["type"]
    constraint = field_schema["constraint"]
    # field_name = field_schema["name"] # field_name is available in field_schema
    
    default_pii_strategy = st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake")
    current_pii_strategy = get_field_pii_strategy(field_schema, default_pii_strategy)

    # Special handling for name with prefix/suffix
    if field_type == "name":
        base_name = fake.name()
        # Handle multi_name for author lists - this logic might be better placed in the main generation loop
        # if field_schema.get("is_multi_name"): # This flag is now handled in the main loop
        #     return "; ".join([fake.name() for _ in range(random.randint(1,4))])

        prefix_options = field_schema.get("prefix_options")
        prefix = field_schema.get("prefix", "")
        if prefix_options and isinstance(prefix_options, list) and prefix_options:
            prefix = random.choice(prefix_options)
        
        if prefix and not prefix.endswith(" "):
            prefix += " "
            
        suffix = field_schema.get("suffix", "")
        if suffix and not suffix.startswith(" "):
            suffix = " " + suffix
        
        val = f"{prefix}{base_name}{suffix}".strip()
        return _apply_pii_strategy_to_value(val, "name", current_pii_strategy)
    elif field_type == "date" and constraint == "datetime": # Special handling for datetime
        # Generate a datetime object and format it
        dt_obj = fake.date_time_this_year()
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")


    generator_func = VALUE_GENERATOR_FUNCTIONS.get(field_type)
    if generator_func:
        # Pass field_name for context within generator functions
        return generator_func(constraint, field_schema["name"], current_pii_strategy, edge_condition=edge_condition)
    st.warning(f"Unknown field type '{field_type}' for field '{field_schema['name']}'. Defaulting to N/A.")
    return "N/A" # Fallback for unknown types

# The generate_domain_specific_data function is now effectively merged into generate_synthetic_data

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

# --- Schema Templates ---
SCHEMA_TEMPLATES = {
    "None (Custom Schema)": [], # Special value to indicate no template or custom editing
    "E-commerce Customer Orders": [
        {"name": "Order ID", "type": "string", "constraint": "", "_canonical_suggestion": "order_id"}, # Suggests using the canonical for specific ID gen
        {"name": "Customer Name", "type": "name", "constraint": ""},
        {"name": "Customer Email", "type": "email", "constraint": ""},
        {"name": "Product Name", "type": "category", "constraint": "Laptop, Smartphone, Headphones, Charger, Case"},
        {"name": "Quantity", "type": "int", "constraint": "1-5"},
        {"name": "Price Per Unit", "type": "float", "constraint": "10.99-1299.99"},
        {"name": "Order Date", "type": "date", "constraint": ""}, # Default date range will apply
        {"name": "Shipping Address", "type": "address", "constraint": ""},
        {"name": "Order Status", "type": "category", "constraint": "Pending, Shipped, Delivered, Cancelled, Returned"},
        {"name": "Payment Method", "type": "category", "constraint": "Credit Card, Debit Card, UPI, Net Banking"},
    ],
    "Basic Employee Records": [
        {"name": "Employee ID", "type": "string", "constraint": "", "_canonical_suggestion": "employee_id"},
        {"name": "Full Name", "type": "name", "constraint": ""},
        {"name": "Email", "type": "email", "constraint": ""},
        {"name": "Phone Number", "type": "phone", "constraint": ""},
        {"name": "Department", "type": "category", "constraint": "HR, Engineering, Marketing, Sales, Finance, Operations"},
        {"name": "Position", "type": "string", "constraint": ""}, # e.g., Software Engineer, Product Manager
        {"name": "Salary", "type": "int", "constraint": "30000-250000"},
        {"name": "Joining Date", "type": "date", "constraint": ""},
        {"name": "Age", "type": "int", "constraint": "22-60"},
    ],
    "Healthcare Patient Data (Demo)": [
        {"name": "Patient ID", "type": "string", "constraint": "", "_canonical_suggestion": "patient_id"},
        {"name": "Patient Name", "type": "name", "constraint": ""},
        {"name": "Age", "type": "int", "constraint": "0-90"}, # Broader age range for patients
        {"name": "Gender", "type": "category", "constraint": "Male, Female, Other"},
        {"name": "Admission Date", "type": "date", "constraint": ""},
        {"name": "Discharge Date", "type": "date", "constraint": ""},
        {"name": "Diagnosis", "type": "category", "constraint": "Flu, Common Cold, Hypertension, Diabetes, Injury"},
        {"name": "Attending Doctor", "type": "name", "constraint": "", "_canonical_suggestion": "doctor_name"}, # Suggests Dr. prefix
        {"name": "Contact Phone", "type": "phone", "constraint": ""},
    ],
    "Financial Transactions (Simplified)": [
        {"name": "Transaction ID", "type": "string", "constraint": "", "_canonical_suggestion": "transaction_id"},
        {"name": "Account Number", "type": "string", "constraint": ""}, # Could be more specific if needed
        {"name": "Transaction Date", "type": "date", "constraint": ""},
        {"name": "Amount", "type": "float", "constraint": "1.00-50000.00"},
        {"name": "Transaction Type", "type": "category", "constraint": "Credit, Debit, Transfer, Payment"},
        {"name": "Description", "type": "string", "constraint": ""},
    ]
    ,
    "Social Media Posts": [
        {"name": "Post ID", "type": "string", "constraint": "", "_canonical_suggestion": "id"},
        {"name": "Username", "type": "string", "constraint": "", "_canonical_suggestion": "username"},
        {"name": "Post Text", "type": "string", "constraint": "", "_canonical_suggestion": "post_text"},
        {"name": "Timestamp", "type": "date", "constraint": "datetime", "_canonical_suggestion": "timestamp"},
        {"name": "Likes", "type": "int", "constraint": "0-10000", "_canonical_suggestion": "like_count"},
        {"name": "Shares", "type": "int", "constraint": "0-5000", "_canonical_suggestion": "share_count"},
        {"name": "Hashtags", "type": "string", "constraint": "", "_canonical_suggestion": "hashtags"} # Suggests comma-separated
    ],
    "IoT Sensor Readings": [
        {"name": "Sensor ID", "type": "string", "constraint": "", "_canonical_suggestion": "sensor_id"},
        {"name": "Timestamp", "type": "date", "constraint": "datetime", "_canonical_suggestion": "timestamp"},
        {"name": "Temperature (°C)", "type": "float", "constraint": "-10.0-40.0", "_canonical_suggestion": "temperature"},
        {"name": "Humidity (%)", "type": "float", "constraint": "20.0-80.0", "_canonical_suggestion": "humidity"},
        {"name": "Latitude", "type": "float", "constraint": "-90.0-90.0", "_canonical_suggestion": "latitude"},
        {"name": "Longitude", "type": "float", "constraint": "-180.0-180.0", "_canonical_suggestion": "longitude"},
        {"name": "Sensor Type", "type": "category", "constraint": "Temperature,Humidity,Pressure,Light", "_canonical_suggestion": "sensor_type"}
    ],
    "Academic Publications": [
        {"name": "Publication ID", "type": "string", "constraint": "", "_canonical_suggestion": "id"},
        {"name": "Title", "type": "string", "constraint": "", "_canonical_suggestion": "publication_title"},
        {"name": "Authors", "type": "string", "constraint": "", "_canonical_suggestion": "author_names"}, # Suggests semi-colon separated
        {"name": "Journal", "type": "category", "constraint": "Nature, Science, Cell, The Lancet, PLOS One", "_canonical_suggestion": "journal_name"},
        {"name": "Publication Year", "type": "int", "constraint": "2000-2024", "_canonical_suggestion": "publication_year"},
        {"name": "DOI", "type": "string", "constraint": "", "_canonical_suggestion": "doi"},
        {"name": "Keywords", "type": "string", "constraint": "", "_canonical_suggestion": "keywords"}, # Suggests comma-separated
        {"name": "Citation Count", "type": "int", "constraint": "0-500", "_canonical_suggestion": "citation_count"}
    ],
    "Logistics Shipment Tracking": [
        {"name": "Shipment ID", "type": "string", "constraint": "", "_canonical_suggestion": "shipment_id"},
        {"name": "Tracking Number", "type": "string", "constraint": "", "_canonical_suggestion": "tracking_number"},
        {"name": "Carrier Name", "type": "string", "constraint": "", "_canonical_suggestion": "carrier_name"},
        {"name": "Origin", "type": "address", "constraint": "", "_canonical_suggestion": "origin_location"},
        {"name": "Destination", "type": "address", "constraint": "", "_canonical_suggestion": "destination_location"},
        {"name": "Status", "type": "category", "constraint": ",".join(LOGISTICS_SHIPMENT_STATUSES_LIST), "_canonical_suggestion": "shipment_status_logistics"},
        {"name": "Estimated Delivery", "type": "date", "constraint": "", "_canonical_suggestion": "estimated_delivery_date"},
        {"name": "Actual Delivery", "type": "date", "constraint": "", "_canonical_suggestion": "actual_delivery_date"},
        {"name": "Freight Cost (USD)", "type": "float", "constraint": "50-5000", "_canonical_suggestion": "freight_cost"},
        {"name": "Package Weight (kg)", "type": "float", "constraint": "0.1-1000", "_canonical_suggestion": "package_weight_kg"},
        {"name": "Package Dimensions (cm)", "type": "string", "constraint": "", "_canonical_suggestion": "package_dimensions_cm"},
    ],
    "Travel Booking Records": [
        {"name": "Booking ID", "type": "string", "constraint": "", "_canonical_suggestion": "booking_id"},
        {"name": "Traveler Name", "type": "name", "constraint": "", "_canonical_suggestion": "traveler_name"},
        {"name": "Destination", "type": "category", "constraint": ",".join(TRAVEL_DESTINATIONS_LIST[:10]), "_canonical_suggestion": "destination_city_travel"}, # Use a subset for template
        {"name": "Origin", "type": "category", "constraint": ",".join(TRAVEL_DESTINATIONS_LIST[10:20]), "_canonical_suggestion": "origin_city_travel"}, # Use a subset
        {"name": "Travel Date", "type": "date", "constraint": "", "_canonical_suggestion": "travel_date"},
        {"name": "Return Date", "type": "date", "constraint": "", "_canonical_suggestion": "return_date"},
        {"name": "Flight Number", "type": "string", "constraint": "", "_canonical_suggestion": "flight_number"},
        {"name": "Airline", "type": "category", "constraint": ",".join(AIRLINE_NAMES_LIST[:5]), "_canonical_suggestion": "airline_name"},
        {"name": "Hotel Name", "type": "string", "constraint": "", "_canonical_suggestion": "hotel_name"},
        {"name": "Room Type", "type": "category", "constraint": ",".join(ROOM_TYPES_LIST[:4]), "_canonical_suggestion": "room_type"},
        {"name": "Booking Status", "type": "category", "constraint": ",".join(TRAVEL_BOOKING_STATUSES_LIST), "_canonical_suggestion": "booking_status_travel"},
        {"name": "Total Cost (USD)", "type": "float", "constraint": "200-8000", "_canonical_suggestion": "total_travel_cost"},
        {"name": "Package Name", "type": "string", "constraint": "", "_canonical_suggestion": "travel_package_name"},
        {"name": "Booked Activity", "type": "category", "constraint": ",".join(TRAVEL_ACTIVITY_TYPES_LIST[:5]), "_canonical_suggestion": "travel_activity"},
    ],
}

# Smart Schema Editor Section
def show_smart_schema_editor(synthetic_df=None, num_rows=10):
    st.subheader("🧠 Smart Schema Editor")
    st.markdown("Define and customize your data schema with field types and constraints.")

    # Initialize schema state if not already present
    if 'schema' not in st.session_state:
        st.session_state.schema = []
    
    # Pre-populate from synthetic_df if schema is empty and df is available, and no template action pending
    if not st.session_state.initial_schema_populated and synthetic_df is not None and not st.session_state.schema:
            # Clear any previous schema if pre-populating from a new source
            # This check might be redundant now due to initial_schema_populated flag
            # if st.session_state.schema and synthetic_df.columns.tolist() != [f['name'] for f in st.session_state.schema]:
            #     st.session_state.schema = []

            # Pre-populate schema with columns from synthetic_df
            for col_name_from_df in synthetic_df.columns:
                inferred_type = "string" # Default
                inferred_constraint = ""
                # Attempt to find a canonical mapping for the column name
                # This helps in pre-filling schema with more specific types if the column name is recognized
                
                # Normalize col_name_from_df for matching (e.g., lower, replace space with underscore)
                normalized_col_name = col_name_from_df.lower().replace(" ", "_")
                canonical_match = None

                # Check direct match in canonical map
                if normalized_col_name in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP:
                    canonical_match = normalized_col_name
                else: # Check synonyms
                    for syn, can in FIELD_SYNONYM_TO_CANONICAL_MAP.items():
                        if syn == normalized_col_name: # Prioritize exact synonym match
                            if can in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP:
                                canonical_match = can
                                break
                        elif syn in normalized_col_name: # Broader match (less reliable)
                             if can in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP:
                                 canonical_match = can # Take first broader match
                                 # break # Don't break, allow more specific synonym match later
                
                field_details_for_schema = {"name": col_name_from_df}

                if canonical_match and canonical_match in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP:
                    details = CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP[canonical_match]
                    field_details_for_schema["type"] = details["type"]
                    field_details_for_schema["constraint"] = details["constraint"]
                    # Carry over relevant flags for generation if needed by schema editor (e.g. for display hints)
                    # For now, type and constraint are primary.
                else: # Fallback to regex-based inference if no canonical match
                    for pattern, f_type, f_constraint in SCHEMA_INFERENCE_RULES:
                        if re.search(pattern, col_name_from_df, re.IGNORECASE):
                            field_details_for_schema["type"] = f_type
                            field_details_for_schema["constraint"] = f_constraint
                            break 
                
                # Ensure default type and constraint if still not set
                field_details_for_schema.setdefault("type", "string")
                field_details_for_schema.setdefault("constraint", "")
                field_details_for_schema["pii_handling"] = st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake")

                st.session_state.schema.append(field_details_for_schema)
            st.session_state.initial_schema_populated = True # Mark as populated

    # --- Template Selector ---
    template_options = list(SCHEMA_TEMPLATES.keys())
    if 'selected_template_name' not in st.session_state:
        # Default to "None (Custom Schema)" or the first option
        st.session_state.selected_template_name = template_options[0] 

    st.markdown("---")
    newly_selected_template = st.selectbox(
        "Load Schema Template (optional, will replace current schema)",
        options=template_options,
        index=template_options.index(st.session_state.selected_template_name),
        key="template_selector_key"
    )

    if newly_selected_template != st.session_state.selected_template_name:
        st.session_state.selected_template_name = newly_selected_template
        if newly_selected_template != "None (Custom Schema)":
            template_content = SCHEMA_TEMPLATES[newly_selected_template]
            st.session_state.schema = [] # Clear current schema
            default_global_pii_strategy = st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake")
            for field_template in template_content:
                new_field = field_template.copy()
                # If template suggests a canonical type, try to get its full details
                canonical_suggestion = new_field.pop("_canonical_suggestion", None)
                if canonical_suggestion and canonical_suggestion in CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP:
                    canonical_details = CANONICAL_FIELD_TO_SCHEMA_DETAILS_MAP[canonical_suggestion]
                    new_field["type"] = canonical_details.get("type", new_field["type"])
                    new_field["constraint"] = canonical_details.get("constraint", new_field["constraint"])
                    # Potentially copy other relevant flags from canonical_details to new_field if needed by schema editor

                is_sensitive = new_field["type"] in ["email", "phone", "aadhaar", "pan", "passport", "voterid", "ifsc", "upi", "name", "address"]
                new_field["pii_handling"] = new_field.get("pii_handling", default_global_pii_strategy if is_sensitive else "realistic_fake")
                st.session_state.schema.append(new_field)
            st.session_state.schema_df = None # Clear previously generated data
            st.session_state.initial_schema_populated = True # Mark as populated (by template)
        else: # User selected "None (Custom Schema)"
            st.session_state.schema = [] # Clear schema
            st.session_state.schema_df = None
            st.session_state.initial_schema_populated = False # Allow re-inference if data is available
        st.rerun()
    st.markdown("---")
    # Display existing schema fields
    for i, field in enumerate(st.session_state.schema):
        is_sensitive_field = field["type"] in ["email", "phone", "aadhaar", "pan", "passport", "voterid", "ifsc", "upi", "name", "address"]
        cols = st.columns([3, 2, 2, 2, 1] if is_sensitive_field else [3, 2, 3, 1]) # Adjust columns based on sensitivity

        with cols[0]:
            st.session_state.schema[i]["name"] = cols[0].text_input(
                f"Field Name",
                value=field["name"],
                key=f"field_name_{i}"
            )

        with cols[1]:
            st.session_state.schema[i]["type"] = cols[1].selectbox(
                f"Field Type",
                options=list(FIELD_TYPES.keys()),
                format_func=lambda x: FIELD_TYPES[x],
                index=list(FIELD_TYPES.keys()).index(field["type"]) if field["type"] in FIELD_TYPES else 0,
                key=f"field_type_{i}"
            )

        with cols[2]:
            field_type = st.session_state.schema[i]["type"]
            placeholder = ""

            if field_type == "int" or field_type == "float":
                placeholder = "e.g., 1-100 or 20000-500000"
            elif field_type == "date":
                placeholder = "e.g., 2023-01-01 - 2023-12-31"
            elif field_type == "category":
                placeholder = "e.g., Option A, Option B, Option C"

            st.session_state.schema[i]["constraint"] = cols[2].text_input(
                f"Constraints",
                value=field["constraint"],
                placeholder=placeholder,
                key=f"field_constraint_{i}"
            )

        if is_sensitive_field:
            with cols[3]:
                # Ensure pii_handling key exists for old schema items
                if "pii_handling" not in st.session_state.schema[i]:
                     st.session_state.schema[i]["pii_handling"] = st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake")

                st.session_state.schema[i]["pii_handling"] = cols[3].selectbox(
                    "PII Handling",
                    options=list(PII_HANDLING_STRATEGIES.keys()),
                    format_func=lambda x: PII_HANDLING_STRATEGIES[x],
                    index=list(PII_HANDLING_STRATEGIES.keys()).index(st.session_state.schema[i]["pii_handling"]),
                    key=f"pii_handling_{i}",
                    help="Choose how to handle this sensitive field."
                )

        delete_button_col_index = 4 if is_sensitive_field else 3
        with cols[delete_button_col_index]:
            if cols[delete_button_col_index].button("Delete", key=f"delete_{i}"):
                st.session_state.schema.pop(i)
                st.rerun()

    # Add new field button
    if st.button("➕ Add Field"):
        st.session_state.schema.append({
            "name": f"Field{len(st.session_state.schema) + 1}",
            "type": "string",
            "constraint": "",
            "pii_handling": st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake") # Default for new fields
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

    # Default PII Handling Strategy
    st.session_state[DEFAULT_PII_STRATEGY_KEY] = st.selectbox(
        "Default PII Handling Strategy",
        options=list(PII_HANDLING_STRATEGIES.keys()),
        format_func=lambda x: PII_HANDLING_STRATEGIES[x],
        index=list(PII_HANDLING_STRATEGIES.keys()).index(st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake")),
        help="Default strategy for new sensitive fields or those not individually set."
    )

    # Generate button
    if st.button("🔄 Generate Data from Schema", use_container_width=True):
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
                    if rule.get('percentage', 0.0) > 0 and random.random() < (rule.get('percentage', 0.0) / 100.0):
                        potential_rules_for_row.append(rule)

                if potential_rules_for_row:
                    applied_edge_rule_for_row = random.choice(potential_rules_for_row) # Pick one if multiple qualify

                for field_schema in st.session_state.schema:
                    field_name = field_schema["name"]
                    field_specific_edge_condition = None

                    if applied_edge_rule_for_row and applied_edge_rule_for_row.get('conditions'):
                        for cond_in_rule in applied_edge_rule_for_row['conditions']:
                            if cond_in_rule['field'] == field_name:
                                field_specific_edge_condition = cond_in_rule # e.g. {'operator': '>', 'value': 100}
                                break
                    try:
                        # Pass the full field_schema dictionary to generate_value
                        row_data[field_name] = generate_value(field_schema, edge_condition=field_specific_edge_condition)
                        if is_dpdp_pii(field_name):
                            if field_name not in detected_dpdp: detected_dpdp.append(field_name)
                    except Exception as e:
                        st.error(f"Error generating data for field '{field_name}' (row {row_idx+1}): {str(e)}")
                        row_data[field_name] = None # Or some default error marker
                        schema_valid = False # Mark schema as invalid if any row fails

                all_rows_data.append(row_data)

            if schema_valid:
                schema_df = pd.DataFrame(all_rows_data)

                # Post-process for "Scramble Column" strategy
                for field_s in st.session_state.schema:
                    # Check if the field is sensitive and the strategy is scramble
                    is_sensitive = field_s["type"] in ["email", "phone", "aadhaar", "pan", "passport", "voterid", "ifsc", "upi", "name", "address"]
                    if is_sensitive and field_s.get("pii_handling") == "scramble_column" and field_s["name"] in schema_df.columns:
                        # Ensure the column exists before trying to scramble
                        # The values were already generated as "realistic_fake" by generate_value
                        # Now we shuffle them
                        col_to_scramble = schema_df[field_s["name"]].copy()
                        # Only shuffle if there's more than one unique value to avoid errors
                        if col_to_scramble.nunique() > 1:
                             np.random.shuffle(col_to_scramble.values) # Shuffle in place
                             schema_df[field_s["name"]] = col_to_scramble
                        else:
                             st.warning(f"Cannot scramble column '{field_s['name']}' as it has only one unique value.")


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
    if "schema_df" in st.session_state and st.session_state.schema_df is not None:
        st.subheader("📊 Generated Data from Schema")
        st.dataframe(st.session_state.schema_df)

        # Download options
        csv = st.session_state.schema_df.to_csv(index=False)

        # Use openpyxl to create Excel file
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer_excel:
            st.session_state.schema_df.to_excel(writer_excel, index=False, sheet_name='Sheet1')
        excel_data = excel_buffer.getvalue()


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
    # Attempt to find more categoricals if 'object' type is not sufficient
    if not categorical_cols:
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

        # Handle potential NaN values in counts before calculating probabilities
        probabilities = counts / len(df[col].dropna())
        # Ensure probabilities sum to 1 (or close to it) and handle potential floating point issues
        probabilities = probabilities[probabilities > 0] # Remove categories with 0 count after dropna
        probabilities = probabilities / probabilities.sum() # Re-normalize

        if len(probabilities) <= 1: # After cleaning, might have only one category left
             column_scores.append(100)
             continue

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
def _synthesize_numeric_column_from_upload(original_series, column_name, num_rows_to_generate):
    """Generates a new numeric series with num_rows_to_generate, based on original_series characteristics."""
    if not pd.api.types.is_numeric_dtype(original_series):
        st.warning(f"Attempted to synthesize non-numeric column '{column_name}' as numeric. Skipping.")
        return pd.Series([np.nan] * num_rows_to_generate, name=column_name)

    valid_series = original_series.dropna()
    if valid_series.empty:
        return pd.Series([np.nan] * num_rows_to_generate, name=column_name)

    min_val, max_val = valid_series.min(), valid_series.max()
    is_integer_type = pd.api.types.is_integer_dtype(original_series)

    generated_values = []
    for _ in range(num_rows_to_generate):
        if min_val == max_val: # Only one unique non-NaN value
            val = min_val
        elif is_integer_type:
            # Ensure min_val and max_val are integers for randint
            val = random.randint(int(round(min_val)), int(round(max_val)))
        else:
            val = random.uniform(min_val, max_val)
        
        if any(keyword in column_name.lower() for keyword in ['age', 'salary', 'price', 'cost', 'amount', 'quantity', 'marks', 'bedrooms', 'bathrooms']):
            val = max(1 if is_integer_type else 0.01, val) # Ensure positivity
        
        # If original was integer, round the result if it became float due to positivity adjustment
        if is_integer_type and isinstance(val, float):
            val = round(val)
            
        generated_values.append(val)
    
    # Attempt to cast back to original dtype if possible, esp. for integers
    new_series = pd.Series(generated_values, name=column_name)
    return new_series.astype(original_series.dtype, errors='ignore')


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

def _synthesize_categorical_column_from_upload(original_series, column_name, num_rows_to_generate):
    """Synthesizes a categorical/object column with num_rows_to_generate. Fakes PII, samples others."""
    # Check for PII first
    for keyword, (gen_type, gen_constraint) in PII_FIELD_SYNTHESIZERS_FOR_UPLOAD.items():
        if keyword in column_name.lower() and (column_name in PII_FIELDS or is_dpdp_pii(column_name)):
            default_pii_strategy = st.session_state.get(DEFAULT_PII_STRATEGY_KEY, "realistic_fake")
            field_schema_for_gen = {"type": gen_type, "constraint": gen_constraint, "name": column_name, "pii_handling": default_pii_strategy}
            return pd.Series([generate_value(field_schema_for_gen) for _ in range(num_rows_to_generate)], name=column_name)

    # Non-PII: sample from original distribution
    cleaned_series = original_series.dropna()
    if cleaned_series.empty:
        return pd.Series([np.nan] * num_rows_to_generate, name=column_name)

    value_counts = cleaned_series.value_counts(normalize=True)
    if value_counts.empty: # Should be caught by cleaned_series.empty, but safeguard
        return pd.Series([np.nan] * num_rows_to_generate, name=column_name)
        
    unique_values = value_counts.index
    probabilities = value_counts.values
    
    # Ensure probabilities sum to 1 (can be off due to floating point issues)
    probabilities = probabilities / np.sum(probabilities)

    generated_values = np.random.choice(unique_values, size=num_rows_to_generate, p=probabilities)
    
    new_series = pd.Series(generated_values, name=column_name)
    return new_series.astype(original_series.dtype, errors='ignore')


# Tabs for different workflows
tab1, tab2, tab3 = st.tabs(["Text-based Generation", "Smart Schema Editor", "File-based Generation"])

with tab1:
    # Main Content for Text-based Generation
    if prompt:
        synthetic_df = generate_synthetic_data(prompt)
        st.session_state.prompt_generated_df = synthetic_df # Store for tab2 access

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
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer_excel:
                synthetic_df.to_excel(writer_excel, index=False, sheet_name='Sheet1')
            excel_data = excel_buffer.getvalue()

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

with tab2:
    # Smart Schema Editor tab
    synth_df = None
    rows = 10
    # Check if there's data from prompt generation first
    if 'prompt_generated_df' in st.session_state and st.session_state.prompt_generated_df is not None:
         synth_df = st.session_state.prompt_generated_df
         rows = max(1, len(synth_df)) # Use synth_df which is now populated
    # If not, check if there's data from file upload
    elif 'uploaded_df_for_schema' in st.session_state and st.session_state.uploaded_df_for_schema is not None:
        synth_df = st.session_state.uploaded_df_for_schema
        rows = max(1, len(synth_df)) # Use synth_df which is now populated
    # If schema_df exists from a previous schema generation, use its row count
    elif 'schema_df' in st.session_state and st.session_state.schema_df is not None:
         rows = max(1, len(st.session_state.schema_df))


    show_smart_schema_editor(synth_df, rows)

with tab3:
    st.header("File-based Synthetic Data Generation")
    uploaded_file = st.file_uploader("Upload your CSV or XLSX dataset", type=["csv", "xlsx"], key="file_uploader_tab3")

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.session_state.uploaded_df_for_schema = df # Store for tab2 access

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

            # Reset choice if a new file is uploaded
            if st.session_state.get('uploaded_file_name_tab3') != uploaded_file.name:
                st.session_state.file_action_tab3 = None
                st.session_state.uploaded_file_name_tab3 = uploaded_file.name
                st.session_state.num_rows_for_file_upload_tab3 = len(df) # Reset num_rows default

            st.markdown("---")
            if st.session_state.file_action_tab3 is None:
                st.subheader("What would you like to do with the uploaded file?")
                choice_col1, choice_col2 = st.columns(2)
                with choice_col1:
                    if st.button("Generate Synthetic Data", key="choice_generate_data_tab3", use_container_width=True):
                        st.session_state.file_action_tab3 = "generate"
                        st.rerun()
                with choice_col2:
                    if st.button("Check Compliance of Original File", key="choice_check_compliance_tab3", use_container_width=True):
                        st.session_state.file_action_tab3 = "compliance"
                        st.rerun()
            
            if st.session_state.file_action_tab3 == "generate":
                st.subheader("⚙️ Configure Synthetic Data Generation")
                st.number_input( # The widget now directly manages st.session_state.num_rows_for_file_upload_tab3
                    "Number of *additional* synthetic rows to generate:",
                    min_value=1,
                    help="These rows will be generated based on the schema of your uploaded file and appended to it.",
                    step=max(1, len(df) // 10 if len(df) > 10 else 1),
                    key="num_rows_for_file_upload_tab3" # Use the session state variable itself as the key
                )

                if st.button("Generate Synthetic Data", key="generate_synthetic_from_file_tab3", use_container_width=True):
                    num_to_generate = st.session_state.num_rows_for_file_upload_tab3
                    new_synthetic_data = {}
                    for col_name in df.columns: # Use columns from the original uploaded df
                        original_column_series = df[col_name] # Base characteristics on original column
                        if pd.api.types.is_numeric_dtype(original_column_series):
                            new_synthetic_data[col_name] = _synthesize_numeric_column_from_upload(original_column_series, col_name, num_to_generate)
                        elif pd.api.types.is_object_dtype(original_column_series) or pd.api.types.is_categorical_dtype(original_column_series):
                            new_synthetic_data[col_name] = _synthesize_categorical_column_from_upload(original_column_series, col_name, num_to_generate)
                        else:
                            if not original_column_series.dropna().empty:
                                # For other types, sample with replacement from the original column to generate new rows
                                new_values = np.random.choice(original_column_series.dropna().values, size=num_to_generate, replace=True)
                                new_synthetic_data[col_name] = pd.Series(new_values, name=col_name).astype(original_column_series.dtype, errors='ignore')
                            else:
                                new_synthetic_data[col_name] = pd.Series([pd.NA] * num_to_generate, name=col_name).astype(original_column_series.dtype, errors='ignore')

                    newly_generated_df = pd.DataFrame(new_synthetic_data)
                    
                    # Concatenate original df with the newly generated_df
                    combined_df = pd.concat([df, newly_generated_df], ignore_index=True)
                    st.session_state.synthetic_df_from_file_tab3 = combined_df # Store the combined df

                if 'synthetic_df_from_file_tab3' in st.session_state and st.session_state.synthetic_df_from_file_tab3 is not None:
                    synthetic_df_from_file = st.session_state.synthetic_df_from_file_tab3
                    st.success(f"Successfully generated {len(synthetic_df_from_file) - len(df)} additional synthetic rows and appended to original data!")
                    st.dataframe(synthetic_df_from_file) # Show all generated data
                    st.markdown(f"**Rows:** {synthetic_df_from_file.shape[0]} | **Columns:** {synthetic_df_from_file.shape[1]}")

                    pii_cols_synthetic_file = [col for col in synthetic_df_from_file.columns if col in PII_FIELDS or is_dpdp_pii(col)]
                    dpdp_cols_synthetic_file = [col for col in synthetic_df_from_file.columns if is_dpdp_pii(col)]

                    if pii_cols_synthetic_file:
                        st.warning(f"⚠️ Generated synthetic data (from file) contains PII-like columns: {', '.join(pii_cols_synthetic_file)}")
                    if dpdp_cols_synthetic_file:
                        for field in dpdp_cols_synthetic_file:
                            st.markdown(f""" <div class="dpdp-warning"> 🔐 <strong>DPDP Compliance Note</strong>: "{field}" (in synthetic data) contains PII under India's DPDP Act </div> """, unsafe_allow_html=True)

                    csv_syn_file = synthetic_df_from_file.to_csv(index=False)
                    excel_buffer_syn_file = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer_syn_file, engine='openpyxl') as writer_excel_syn_file:
                        synthetic_df_from_file.to_excel(writer_excel_syn_file, index=False, sheet_name='Sheet1')
                    excel_data_syn_file = excel_buffer_syn_file.getvalue()

                    dl_col1, dl_col2 = st.columns(2)
                    with dl_col1:
                        st.download_button(label="Download CSV (Synthetic)", data=csv_syn_file, file_name="synthetic_data_from_file.csv", mime="text/csv", key="download_csv_synthetic_file")
                    with dl_col2:
                        st.download_button(label="Download Excel (Synthetic)", data=excel_data_syn_file, file_name="synthetic_data_from_file.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_excel_synthetic_file")

            elif st.session_state.file_action_tab3 == "compliance":
                st.markdown("---")
                st.subheader("Compliance Analysis of Original Uploaded File")
                # Bias Checker for original uploaded data
                st.subheader("📈 Bias Checker (Original Uploaded Data)")
                if not df.empty:
                    categorical_cols_upload = df.select_dtypes(include='object').columns.tolist()
                    if not categorical_cols_upload:
                        categorical_cols_upload = [col for col in df.columns if df[col].nunique() < 20 and df[col].nunique() > 1]
                    
                    if categorical_cols_upload:
                        selected_col_upload = st.selectbox("Select a categorical column to check bias", categorical_cols_upload, key="bias_checker_upload_tab3_compliance")
                        if selected_col_upload:
                            value_counts_upload = df[selected_col_upload].value_counts(normalize=True) * 100
                            fig_upload = px.bar(value_counts_upload, x=value_counts_upload.index, y=value_counts_upload.values, labels={"x": selected_col_upload, "y": "Percentage"}, title=f"Distribution in '{selected_col_upload}' (Original Data)")
                            st.plotly_chart(fig_upload)
                    else:
                        st.info("No suitable categorical columns found in the uploaded data for bias checking.")
                else:
                    st.info("Error: Original data seems to be empty for bias checking.")

                # Ethical Scorecard for original uploaded data
                st.subheader("✅ Ethical Scorecard (Original Uploaded Data Analysis)")
                score_col1, score_col2, score_col3 = st.columns(3)
                pii_cols_uploaded_orig = [col for col in df.columns if col in PII_FIELDS or is_dpdp_pii(col)]
                dpdp_cols_uploaded_specific_orig = [col for col in df.columns if is_dpdp_pii(col)]
                pii_risk_level_uploaded_orig = "High" if pii_cols_uploaded_orig else "Low"
                dpdp_risk_level_uploaded_orig = "High" if dpdp_cols_uploaded_specific_orig else "Low"
                bias_score_uploaded_orig = calculate_bias_score(df)

                score_col1.metric("Bias Score (Original)", f"{bias_score_uploaded_orig:.0f} / 100")
                score_col2.metric("PII Risk (Original)", pii_risk_level_uploaded_orig)
                score_col3.metric("DPDP Risk (Original)", dpdp_risk_level_uploaded_orig)

                # Download PDF Report for original uploaded data
                st.subheader("📄 Download Summary Report (Original Uploaded Data)")
                if st.button("Download PDF Report", key="pdf_report_upload_tab3_compliance", use_container_width=True):
                    pdf_upload = FPDF()
                    pdf_upload.add_page()
                    pdf_upload.set_font("Arial", size=12)
                    pdf_upload.cell(200, 10, txt=f"{APP_NAME} - Original Data Report", ln=True, align="C")
                    pdf_upload.ln(10)
                    pdf_upload.cell(200, 10, txt=f"Dataset: {uploaded_file.name}", ln=True)
                    pdf_upload.cell(200, 10, txt=f"Bias Score: {bias_score_uploaded_orig:.0f} / 100", ln=True)
                    pdf_upload.cell(200, 10, txt=f"PII Risk: {pii_risk_level_uploaded_orig}", ln=True)
                    if pii_cols_uploaded_orig: pdf_upload.cell(200, 10, txt=f"Detected PII Fields: {', '.join(pii_cols_uploaded_orig)}", ln=True)
                    pdf_upload.cell(200, 10, txt=f"DPDP Risk: {dpdp_risk_level_uploaded_orig}", ln=True)
                    if dpdp_cols_uploaded_specific_orig: pdf_upload.cell(200, 10, txt=f"Detected DPDP-Specific Fields: {', '.join(dpdp_cols_uploaded_specific_orig)}", ln=True)
                    pdf_upload.ln(10)
                    pdf_upload.cell(200, 10, txt="Note: This report reflects analysis of the original uploaded data.", ln=True)
                    buffer_upload_pdf = io.BytesIO()
                    pdf_upload.output(buffer_upload_pdf)
                    st.download_button(label="Download PDF Now", data=buffer_upload_pdf.getvalue(), file_name="original_data_report.pdf", mime="application/pdf", key="download_pdf_upload_final_tab3_compliance")

        except Exception as e:
            st.error(f"Error processing uploaded file: {e}")
            st.session_state.uploaded_df_for_schema = None # Clear on error

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
   - Define Edge Cases to inject specific scenarios.
   - Customize the structure of your synthetic data.

3. **Privacy Controls**:
   - **Granular PII Handling**: Choose how sensitive fields are generated (Realistic Fake, Masked, Redacted, Scramble Column).
   - DPDP Act compliance warnings.
   - PII risk assessment.

4. **File Upload Method**:
   - Upload an existing CSV or XLSX file.
   - Generate synthetic version of your data.
   - Analyze bias and distribution of the *original* data.

5. **PII Protection**:
   - Automatic detection of Personal Identifiable Information.
   - Warnings for potential privacy risks.
   - Synthetic data generation with fake personal data.

6. **Features**:
   - Generate synthetic data.
   - Download as CSV or Excel.
   - Bias checking.
   - Ethical scorecard.
   - PII risk assessment.
   - Edge Case Injection.

**Powered by {APP_NAME}**: Transforming data privacy, one synthetic dataset at a time.
""")

# Footer
st.markdown(f"""
---
*{APP_NAME} - Synthetic Data Generator* | Privacy-First Data Transformation
""")
