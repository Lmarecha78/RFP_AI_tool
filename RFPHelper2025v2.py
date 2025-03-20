import streamlit as st
import pandas as pd
import openai
import re
from io import BytesIO
import os

# Streamlit page setup
st.set_page_config(
    page_title="Skyhigh Security",
    page_icon="🔒",
    layout="wide"
)

# ✅ Define authentication credentials
PASSWORD = "Skyhigh@2025!"  # 🔐 Change this to your secure password

# ✅ Function for authentication
def authenticate():
    """Check user authentication and store the result in session state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Skyhigh Security RFP Tool")
        st.subheader("Enter Password to Access")

        # Create a password input field
        password_input = st.text_input("Password", type="password")

        if st.button("Login"):
            if password_input == PASSWORD:
                st.session_state.authenticated = True
                st.success("✅ Authentication successful! Access granted.")
                st.rerun()  # ✅ Correct in Streamlit 1.18+
            else:
                st.error("❌ Incorrect password. Try again.")

        # Stop execution if authentication fails
        st.stop()

# ✅ Call authentication function
authenticate()

# 🎉 If authenticated, show the main app
st.title("Skyhigh Security - RFI/RFP AI Tool")

# Retrieve OpenAI API key securely from Streamlit Secrets
openai_api_key = st.secrets.get("OPENAI_API_KEY")

if not openai_api_key:
    st.error("❌ OpenAI API key is missing! Please set it in Streamlit Cloud 'Secrets'.")
    st.stop()

# ✅ OpenAI Client Initialization
try:
    from openai import OpenAI  # OpenAI v1.0+
    openai_client = OpenAI(api_key=openai_api_key)
    new_api = True
except ImportError:
    openai.api_key = openai_api_key
    openai_client = openai  # Assign module for older versions
    new_api = False

# Background image
def set_background(image_url):
    css = f"""
    <style>
    .stApp {{
        background-image: url("{image_url}");
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

set_background("https://raw.githubusercontent.com/lmarecha78/RFP_AI_tool/main/skyhigh_bg.png")

# User inputs
customer_name = st.text_input("Customer Name", key="customer_name")
product_choice = st.selectbox(
    "What is the elected product?",
    [
        "Skyhigh Security SSE",
        "Skyhigh Security On-Premise Proxy",
        "Skyhigh Security GAM ICAP",
        "Skyhigh Security CASB",
        "Skyhigh Security Cloud Proxy"
    ],
    key="product_choice"
)

language_choice = st.selectbox("Select language", ["English", "French", "Spanish", "German", "Italian"], key="language_choice")
uploaded_file = st.file_uploader("Upload a CSV or XLS file", type=["csv", "xls", "xlsx"], key="uploaded_file")

# Model selection
st.markdown("#### **Select Model for Answer Generation**")
model_choice = st.radio(
    "Choose a model:",
    options=["GPT-4.0", "Due Diligence (Fine-Tuned)"],
    captions=[
        "Recommended option for most technical RFPs/RFIs.",
        "Optimized for Due Diligence and security-related questionnaires."
    ],
    key="model_choice"
)

# Model mapping
model_mapping = {
    "GPT-4.0": "gpt-4-turbo",
    "Due Diligence (Fine-Tuned)": "ft:gpt-4o-2024-08-06:personal:skyhigh-due-diligence:BClhZf1W"
}
selected_model = model_mapping[model_choice]

column_location = st.text_input("Specify the location of the questions (e.g., B for column B)", key="column_location")
answer_column = st.text_input("Optional: Specify the column for answers (e.g., C for column C)", key="answer_column")
optional_question = st.text_input("Extra/Optional: You can ask a unique question here", key="optional_question")

# ✅ Check if a valid file is uploaded
if uploaded_file is None and not optional_question:
    st.error("❌ Please upload a file or enter an optional question.")
    st.stop()

# ✅ Try reading the file to ensure it is valid
try:
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        
        if file_extension == "csv":
            df = pd.read_csv(uploaded_file)
        elif file_extension in ["xls", "xlsx"]:
            df = pd.read_excel(uploaded_file)
        else:
            st.error("❌ Unsupported file type! Please upload a CSV or Excel file.")
            st.stop()
        
        st.success("✅ File uploaded and successfully read!")

except Exception as e:
    st.error(f"❌ Error reading the uploaded file: {e}")
    st.stop()

# Debugging: Show input values
st.write(f"**Debugging Info:**")
st.write(f"Uploaded file: {uploaded_file}")
st.write(f"Customer Name: {customer_name}")
st.write(f"Column Location: {column_location}")

# Function to clean responses
def clean_answer(answer):
    return re.sub(r'(Overall,.*|In conclusion.*|Conclusion:.*)', '', answer, flags=re.IGNORECASE | re.DOTALL).strip()

# Submit button
if st.button("Submit"):
    # ✅ Mandatory Field Checks
    if not customer_name:
        st.error("❌ Please enter a customer name.")
        st.stop()
    
    if not column_location:
        st.error("❌ Please specify the location of the questions (e.g., B for column B).")
        st.stop()

    if uploaded_file is None and not optional_question:
        st.error("❌ Please upload a file or enter an optional question.")
        st.stop()

    if optional_question:
        prompt = (
            f"You are an expert in Skyhigh Security products, providing highly detailed technical responses for an RFP. "
            f"Your answer should be **strictly technical**, focusing on architecture, specifications, security features, compliance, integrations, and standards. "
            f"**DO NOT** include disclaimers, introductions, or any mention of knowledge limitations. **Only provide the answer**.\n\n"
            f"Customer: {customer_name}\n"
            f"Product: {product_choice}\n"
            f"### Question:\n{optional_question}\n\n"
            f"### Direct Answer (no intro, purely technical):"
        )

        if new_api:
            response = openai_client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1
            )
        else:
            response = openai_client.ChatCompletion.create(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1
            )

        answer = clean_answer(response.choices[0].message.content.strip())
        st.markdown(f"### Your Question: {optional_question}")
        st.write(answer)

    else:
        st.error("Please fill in all mandatory fields and upload a file or enter an optional question.")


