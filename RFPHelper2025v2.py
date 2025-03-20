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

# ✅ Ensure OpenAI API key is set correctly
openai_api_key = st.secrets.get("OPENAI_API_KEY")

if not openai_api_key:
    st.error("❌ OpenAI API key is missing! Please set it in Streamlit Cloud 'Secrets'.")
else:
    openai.api_key = openai_api_key  # ✅ Correct way to set API key

# Set background image
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

# Branding and title
st.title("Skyhigh Security - RFI/RFP AI Tool")

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

# **Model Selection**
st.markdown("#### **Select Model for Answer Generation**")
model_choice = st.radio(
    "Choose a model:",
    options=["GPT-4.0", "Due Diligence (Fine-Tuned)"],
    captions=[
        "Recommended option for most technical RFPs/RFIs.",
        "Optimized for Due Diligence and security-related questionnaires."
    ]
)

# Model mapping
model_mapping = {
    "GPT-4.0": "gpt-4-turbo",
    "Due Diligence (Fine-Tuned)": "ft:gpt-4o-2024-08-06:personal:skyhigh-due-diligence:BClhZf1W"
}
selected_model = model_mapping[model_choice]

column_location = st.text_input("Specify the location of the questions (e.g., B for column B)")
answer_column = st.text_input("Optional: Specify the column for answers (e.g., C for column C)")
optional_question = st.text_input("Extra/Optional: You can ask a unique question here")

# ✅ Function to clean answers (Removes any conclusion, benefits, or summary-like statements)
def clean_answer(answer):
    """Removes conclusion-like statements, benefits, and outcome-driven phrases from the response."""
    # Patterns to detect and remove conclusions, benefit statements, and indirect summaries
    patterns = [
        r'\b(Overall,|In conclusion,|Conclusion:|To summarize,|Thus,|Therefore,|Finally,|This enables|This ensures|This allows|This provides|This results in|By leveraging|By implementing).*',  # Generic conclusions & enablers
        r'.*\b(enhancing|improving|achieving|helping to ensure|complying with|ensuring).*security posture.*',  # Compliance & security posture statements
        r'.*\b(this leads to|this results in|which results in|thereby improving|thus ensuring).*',  # Outcome-driven statements
        r'\b(By using|By adopting|By deploying|By integrating|By utilizing).*',  # "By doing X, you get Y" structures
        r'\b(This approach|This strategy|This technology).*',  # Indirect conclusions
    ]
    
    for pattern in patterns:
        answer = re.sub(pattern, '', answer, flags=re.IGNORECASE | re.DOTALL).strip()

    return answer

# **Submit Button Logic**
if st.button("Submit"):
    if optional_question:
        prompt = (
            f"You are an expert in Skyhigh Security products, providing highly detailed technical responses for an RFP. "
            f"Your answer should be **strictly technical**, focusing on architecture, specifications, security features, compliance, integrations, and standards. "
            f"Your response should be tailored to the specific needs of **{customer_name}** and their security requirements. "
            f"**DO NOT** include disclaimers, introductions, or any mention of knowledge limitations. "
            f"**DO NOT** include conclusions, summaries, benefits, security posture improvements, business impacts, or closing remarks. "
            f"**Only provide the answer in a direct, structured format without any inferred benefits or conclusions.**\n\n"
            f"Customer: {customer_name}\n"
            f"Product: {product_choice}\n"
            f"### Question:\n{optional_question}\n\n"
            f"### Direct Answer (no intro, no conclusions, no benefits, purely technical, customer-specific):"
        )

        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )

        answer = clean_answer(response.choices[0].message.content.strip())  # ✅ Strongest cleaning applied
        st.markdown(f"### Your Question: {optional_question}")
        st.write(answer)

    elif customer_name and uploaded_file and column_location:
        try:
            # Read file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file, engine="openpyxl")

            # Convert column letters to index
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
                    f"You are an expert in Skyhigh Security products, responding to an RFP for **{customer_name}**. "
                    f"Provide a detailed, precise, and technical response sourced explicitly from official Skyhigh Security documentation. "
                    f"Ensure the response aligns with the security priorities and infrastructure of **{customer_name}**. "
                    f"**Do NOT include introductions, disclaimers, conclusions, or benefits.**\n\n"
                    f"Product: {product_choice}\n"
                    f"### Question:\n{question}\n\n"
                    f"### Direct Technical Answer (tailored for {customer_name}):"
                )

                response = openai.ChatCompletion.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.1
                )

                answer = clean_answer(response.choices[0].message.content.strip())  # ✅ Cleans any remaining conclusions
                answers.append(answer)

                st.markdown(f"### Q{idx}: {question}")
                st.write(answer)

        except Exception as e:
            st.error(f"Error processing file: {e}")

    else:
        st.error("Please fill in all mandatory fields and upload a file or enter an optional question.")

