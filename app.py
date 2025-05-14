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
    "name": "Full Name"
}

# Define a function to validate constraints based on field type
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
                # We'll handle swapping in generate_value if needed, so just check they're not equal
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
                # We'll handle swapping in generate_value if needed
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
    elif field_type in ["email", "phone", "address", "name"]:
        # These types don't need constraints
        return True
    return False

# Function to generate value based on field type and constraint
def generate_value(field_type, constraint):
    """Generate a random value based on field type and constraint."""
    if field_type == "string":
        return fake.text(max_nb_chars=20).replace('\n', ' ')
    
    elif field_type == "int":
        if constraint and validate_constraint(field_type, constraint):
            min_val, max_val = map(float, re.findall(r"-?\d+(?:\.\d+)?", constraint))
            # Ensure max_val is greater than or equal to min_val
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            # Make sure both values are non-negative for age and salary
            if "age" in field_type.lower() or "salary" in field_type.lower():
                min_val = max(0, min_val)
            return random.randint(int(min_val), int(max_val))
        # Default range that ensures positive values
        return random.randint(1, 1000)
    
    elif field_type == "float":
        if constraint and validate_constraint(field_type, constraint):
            min_val, max_val = map(float, re.findall(r"-?\d+(?:\.\d+)?", constraint))
            # Ensure max_val is greater than or equal to min_val
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            # Make sure both values are non-negative for typical numeric fields
            if "age" in field_type.lower() or "salary" in field_type.lower() or "price" in field_type.lower():
                min_val = max(0, min_val)
            return round(random.uniform(min_val, max_val), 2)
        # Default range that ensures positive values
        return round(random.uniform(1, 1000), 2)
    
    elif field_type == "date":
        if constraint and validate_constraint(field_type, constraint):
            start_date, end_date = re.findall(r"\d{4}-\d{2}-\d{2}", constraint)
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            # Ensure end is after start
            if start > end:
                start, end = end, start
            days_between = (end - start).days
            random_days = random.randint(0, max(0, days_between))
            return (start + pd.Timedelta(days=random_days)).strftime("%Y-%m-%d")
        return fake.date_between(start_date="-1y", end_date="today").strftime("%Y-%m-%d")
    
    elif field_type == "category":
        if constraint:
            values = [v.strip() for v in constraint.split(",")]
            if values:  # Ensure there's at least one value
                return random.choice(values)
        return random.choice(["Option A", "Option B", "Option C"])
    
    elif field_type == "email":
        return fake.email()
    
    elif field_type == "phone":
        return fake.phone_number()
    
    elif field_type == "address":
        return fake.address().replace('\n', ', ')
    
    elif field_type == "name":
        return fake.name()
    
    return "N/A"

# Generate Synthetic Data Based on Input
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
    
    # Parse number of rows
    for word in description.split():
        if word.isdigit():
            num_rows = int(word)
            break
    
    # Detect column types
    column_mapping = {
        'name': 'Name',
        'age': 'Age',
        'salary': 'Salary',
        'email': 'Email',
        'phone': 'Phone',
        'address': 'Address',
        'gender': 'Gender',
        'job': 'Job Title',
        'company': 'Company'
    }
    
    # Find columns based on keywords
    for keyword, column in column_mapping.items():
        if keyword in description:
            columns.append(column)
            # Check for PII
            if column in PII_FIELDS:
                detected_pii.append(column)
    
    # Ensure we have at least some columns
    if not columns:
        st.error("No valid columns detected. Please use keywords like name, age, salary, email, etc.")
        return None
    
    # Generate data
    data = {}
    for col in columns:
        if col == 'Name':
            data[col] = [fake.name() for _ in range(num_rows)]
            if col not in detected_pii:
                detected_pii.append(col)
        elif col == 'Age':
            # Ensure age is within a reasonable positive range
            data[col] = [random.randint(18, 65) for _ in range(num_rows)]
        elif col == 'Salary':
            # Ensure salary is positive
            data[col] = [random.randint(30000, 150000) for _ in range(num_rows)]
        elif col == 'Email':
            data[col] = [fake.email() for _ in range(num_rows)]
            if col not in detected_pii:
                detected_pii.append(col)
        elif col == 'Phone':
            data[col] = [fake.phone_number() for _ in range(num_rows)]
            if col not in detected_pii:
                detected_pii.append(col)
        elif col == 'Address':
            data[col] = [fake.address().replace('\n', ', ') for _ in range(num_rows)]
            if col not in detected_pii:
                detected_pii.append(col)
        elif col == 'Gender':
            data[col] = [random.choice(['Male', 'Female', 'Other']) for _ in range(num_rows)]
        elif col == 'Job Title':
            data[col] = [fake.job() for _ in range(num_rows)]
        elif col == 'Company':
            data[col] = [fake.company() for _ in range(num_rows)]
    
    # Create DataFrame
    synthetic_df = pd.DataFrame(data)
    
    # Display PII warning if detected
    if detected_pii:
        st.warning(f"⚠️ Detected possible PII fields: {', '.join(detected_pii)}. Ensure compliance with privacy regulations.")
    
    return synthetic_df

# Smart Schema Editor Section
def show_smart_schema_editor(synthetic_df=None, num_rows=10):
    st.subheader("🧠 Smart Schema Editor")
    st.markdown("Define and customize your data schema with field types and constraints.")
    
    # Initialize schema state if not already present
    if 'schema' not in st.session_state:
        st.session_state.schema = []
        if synthetic_df is not None:
            # Pre-populate schema with columns from synthetic_df
            for col in synthetic_df.columns:
                field_type = "string"
                constraint = ""
                
                # Try to infer field type from column name and values
                if col == "Email" or "email" in col.lower():
                    field_type = "email"
                elif col == "Name" or "name" in col.lower():
                    field_type = "name"
                elif col == "Phone" or "phone" in col.lower():
                    field_type = "phone"
                elif col == "Address" or "address" in col.lower():
                    field_type = "address"
                elif col == "Age" or "age" in col.lower():
                    field_type = "int"
                    constraint = "18-60"  # Default age constraint
                elif col == "Salary" or "salary" in col.lower():
                    field_type = "int"
                    constraint = "20000-500000"  # Default salary constraint in rupees
                elif col == "Gender" or "gender" in col.lower():
                    field_type = "category"
                    constraint = "Male, Female, Other"
                
                st.session_state.schema.append({
                    "name": col,
                    "type": field_type,
                    "constraint": constraint
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
    
    # Number of rows input
    num_rows = st.number_input("Number of rows to generate", min_value=1, value=max(1, num_rows), step=1)
    
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
            data = {}
            schema_valid = True
            
            for field in st.session_state.schema:
                try:
                    data[field["name"]] = [
                        generate_value(field["type"], field["constraint"])
                        for _ in range(num_rows)
                    ]
                except Exception as e:
                    st.error(f"Error generating data for field '{field['name']}': {str(e)}")
                    schema_valid = False
                    break
            
            if schema_valid:
                schema_df = pd.DataFrame(data)
                st.session_state.schema_df = schema_df
                
                # Identify PII fields
                pii_detected = [
                    field["name"] for field in st.session_state.schema
                    if field["type"] in ["email", "phone", "address", "name"]
                ]
                
                if pii_detected:
                    st.warning(f"⚠️ Generated data contains PII fields: {', '.join(pii_detected)}. Ensure compliance with privacy regulations.")
                
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
            
            # PII Check on generated data
            pii_columns = [col for col in synthetic_df.columns if col in PII_FIELDS]
            if pii_columns:
                st.warning(f"⚠️ Generated data contains PII columns: {', '.join(pii_columns)}")
            
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
        if pii_columns:
            st.warning(f"⚠️ Uploaded dataset contains potential PII columns: {', '.join(pii_columns)}")

        st.subheader("📊 Preview of Original Data")
        st.dataframe(df.head())

        # Generate Synthetic Data
        st.subheader("⚙️ Generate Synthetic Data")
        if st.button("Generate Synthetic Data"):
            # More sophisticated synthetic data generation
            synthetic_df = df.copy()
            
            # Numeric columns: add noise but ensure values stay positive for relevant columns
            for col in synthetic_df.select_dtypes(include=np.number).columns:
                # Check if column might be age, salary, or other value that should be positive
                if any(keyword in col.lower() for keyword in ['age', 'salary', 'price', 'cost', 'amount']):
                    # Add noise but ensure values stay positive
                    synthetic_df[col] = synthetic_df[col].apply(
                        lambda x: max(1, x + np.random.normal(0, abs(x * 0.1)))
                    )
                else:
                    # For other numeric columns, apply regular noise
                    synthetic_df[col] = synthetic_df[col].apply(
                        lambda x: x + np.random.normal(0, abs(x * 0.1) if x != 0 else 1)
                    )
            
            # Categorical columns: reshuffle
            for col in synthetic_df.select_dtypes(include='object').columns:
                if col in PII_FIELDS:
                    # For PII columns, generate fake data
                    if 'name' in col.lower():
                        synthetic_df[col] = [fake.name() for _ in range(len(synthetic_df))]
                    elif 'email' in col.lower():
                        synthetic_df[col] = [fake.email() for _ in range(len(synthetic_df))]
                    elif 'phone' in col.lower():
                        synthetic_df[col] = [fake.phone_number() for _ in range(len(synthetic_df))]
                    elif 'address' in col.lower():
                        synthetic_df[col] = [fake.address().replace('\n', ', ') for _ in range(len(synthetic_df))]
                else:
                    # For non-PII categorical columns, shuffle
                    synthetic_df[col] = np.random.permutation(synthetic_df[col])

            st.success("Synthetic data generated!")
            st.dataframe(synthetic_df.head())
            
            # Dataset Summary
            st.markdown(f"**Rows:** {synthetic_df.shape[0]} | **Columns:** {synthetic_df.shape[1]}")
            
            # Detect PII in synthetic data
            pii_columns = [col for col in synthetic_df.columns if col in PII_FIELDS]
            if pii_columns:
                st.warning(f"⚠️ Generated synthetic data contains PII columns: {', '.join(pii_columns)}")
            
            # Download options for synthetic data
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
        
        # Dynamically adjust PII risk based on PII columns
        pii_columns = [col for col in df.columns if col in PII_FIELDS]
        pii_risk = "High" if pii_columns else "Low"
        
        col1.metric("Bias Score", "82 / 100")
        col2.metric("PII Risk", pii_risk)
        col3.metric("GDPR/DPDP", "✅ Compliant")

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
            pdf.cell(200, 10, txt=f"PII Risk: {pii_risk}", ln=True)
            pdf.cell(200, 10, txt="GDPR/DPDP Readiness: ✅", ln=True)
            
            # List PII columns if present
            if pii_columns:
                pdf.cell(200, 10, txt=f"PII Columns Detected: {', '.join(pii_columns)}", ln=True)
            
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
   - Supports keywords: 
     * Personal: name, email, phone, address
     * Professional: age, salary, job, company
     * Demographic: gender

2. **Smart Schema Editor**:
   - Define exact field types: string, email, int, float, category, etc.
   - Add constraints like age ranges (18-60) or salary ranges (₹20K-₹5L)
   - Customize the structure of your synthetic data

3. **Reproducibility**:
   - Check "Use fixed random seed" to generate consistent synthetic data
   - Same input will produce identical results

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