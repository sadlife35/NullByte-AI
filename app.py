import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF
import io
from faker import Faker
import random
import openpyxl

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
            data[col] = [random.randint(22, 65) for _ in range(num_rows)]
        elif col == 'Salary':
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

# File Upload
uploaded_file = st.file_uploader("Upload your CSV or XLSX dataset", type=["csv", "xlsx"])

# Main Content
if prompt or uploaded_file:
    # Generate Synthetic Data from Text Input
    if prompt:
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
                    key="download_csv_prompt"  # Added unique key
                )
            with col2:
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name="synthetic_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_prompt"  # Added unique key
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
            
            # Numeric columns: add noise
            for col in synthetic_df.select_dtypes(include=np.number).columns:
                synthetic_df[col] = synthetic_df[col].apply(lambda x: x + np.random.normal(0, 1))
            
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
                    key="download_csv_upload"  # Added unique key
                )
            with col2:
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name="synthetic_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_upload"  # Added unique key
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
                key="download_pdf_report"  # Added unique key
            )

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

2. **Reproducibility**:
   - Check "Use fixed random seed" to generate consistent synthetic data
   - Same input will produce identical results

3. **File Upload Method**:
   - Upload an existing CSV or XLSX file
   - Generate synthetic version of your data
   - Analyze bias and distribution

4. **PII Protection**:
   - Automatic detection of Personal Identifiable Information
   - Warnings for potential privacy risks
   - Synthetic data generation with fake personal data

5. **Features**:
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