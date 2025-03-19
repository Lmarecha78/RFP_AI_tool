import streamlit as st
import base64
import subprocess
import sys
import os

# Function to install packages
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Ensure required libraries are installed
required_packages = ["pandas", "openai", "streamlit"]
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        install_package(package)

import pandas as pd
import openai
import re
from io import BytesIO

# Set your OpenAI API key (Replace this in production with a secure method)
openai_api_key = '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'
openai.api_key = openai_api_key

# Streamlit page setup
st.set_page_config(
    page_title="Skyhigh Security",
    page_icon="🔒",
    layout="wide"
)

# Load background image
def set_background(image_file):
    with open(image_file, "rb") as image:
        encoded = base64.b64encode(image.read()).decode()
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');

    .stApp {{
        background-image: url('data:image/png;base64,{encoded}');
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Roboto', sans-serif;
    }}
    h1 {{
        font-size: 32px;
        margin-top: 0;
        padding-top: 10px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Set custom background
set_background("https://raw.githubusercontent.com/lmarecha78/RFP_AI_tool/main/skyhigh_bg.png")


# Branding and title
st.title("Skyhigh Security - RFI/RFP AI Tool (Not for Production)")

# Input fields
customer_name = st.text_input("Customer Name")

product_choice = st.selectbox(
    "What is the elected product?",
    [
        "Skyhigh Security SSE",
        "Skyhigh Security On-Premise Proxy",
        "Skyhigh Security GAM ICAP",
        "Skyhigh Security CASB",
        "Skyhigh Security Cloud Proxy"
    ]
)

language_choice = st.selectbox(
    "Select language",
    ["English", "French", "Spanish", "German", "Italian"]
)

uploaded_file = st.file_uploader("Upload a CSV or XLS file", type=["csv", "xls", "xlsx"])

# **Newly Added Model Selection**
st.markdown("#### **Select Model for Answer Generation**")
model_choice = st.radio(
    "Choose a model:",
    options=["GPT-4.0", "Due Diligence (Fine-Tuned)"],
    captions=[
        "Recommended option for most technical RFPs/RFIs.",
        "Optimized for Due Diligence and security-related questionnaires."
    ]
)

# Mapping model selection to actual model identifiers
model_mapping = {
    "GPT-4.0": "gpt-4-turbo",
    "Due Diligence (Fine-Tuned)": "ft:gpt-4o-2024-08-06:personal:skyhigh-due-diligence:BClhZf1W"
}
selected_model = model_mapping[model_choice]

column_location = st.text_input("Specify the location of the questions (e.g., B for column B)")
answer_column = st.text_input("Optional: Specify the column for answers (e.g., C for column C)")
optional_question = st.text_input("Extra/Optional: You can ask a unique question here")

# Function to clean answers
def clean_answer(answer):
    return re.sub(r'(Overall,.*|In conclusion.*|Conclusion:.*)', '', answer, flags=re.IGNORECASE | re.DOTALL).strip()

# Submit button logic
if st.button("Submit"):
    if optional_question:
        prompt = (
            f"I'm a highly technical Sales Engineer responding to an RFP for customer '{customer_name}'. "
            f"Provide a detailed, precise, and technical response sourced explicitly from official Skyhigh Security documentation. "
            f"Product: {product_choice}\n"
            f"Question: {optional_question}\n\nDetailed Technical Answer:"
        )

        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )

        answer = clean_answer(response.choices[0].message.content.strip())
        st.markdown(f"### Your Question: {optional_question}")
        st.write(answer)

    elif customer_name and uploaded_file and column_location:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            question_index = ord(column_location.strip().upper()) - ord('A')
            questions = df.iloc[:, question_index].dropna().tolist()

            answer_index = None
            if answer_column:
                answer_index = ord(answer_column.strip().upper()) - ord('A')
                if answer_index >= len(df.columns):
                    df.insert(answer_index, 'Answers', '')

            st.success(f"Extracted {len(questions)} questions for '{customer_name}'. Generating responses...")

            answers = []
            for idx, question in enumerate(questions, 1):
                prompt = (
                    f"I'm a highly technical Sales Engineer responding to an RFP for customer '{customer_name}'. "
                    f"Provide a detailed, precise, and technical response sourced explicitly from official Skyhigh Security documentation. "
                    f"Product: {product_choice}\n"
                    f"Question: {question}\n\nDetailed Technical Answer:"
                )

                response = openai.ChatCompletion.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.1
                )

                answer = clean_answer(response.choices[0].message.content.strip())
                answers.append(answer)

                st.markdown(f"### Q{idx}: {question}")
                st.write(answer)

            if answer_index is not None:
                df.iloc[:len(answers), answer_index] = answers

                output = BytesIO()
                df.to_excel(output, index=False)
                output.seek(0)

                st.download_button(
                    label="Download file with answers",
                    data=output,
                    file_name=f"{customer_name}_RFP_responses.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Error processing file: {e}")

    else:
        st.error("Please fill in all mandatory fields and upload a file or enter an optional question.")

