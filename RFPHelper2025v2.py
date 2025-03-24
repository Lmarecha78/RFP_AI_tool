import streamlit as st
import pandas as pd
import openai
import re
from io import BytesIO

###############################################################################
# 1) PAGE CONFIG MUST BE FIRST
###############################################################################
st.set_page_config(
    page_title="Skyhigh Security - RFI/RFP AI Tool",
    page_icon="🔒",
    layout="wide"
)

###############################################################################
# 2) OPTIONAL BACKGROUND
###############################################################################
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

# Set a custom background if desired
set_background("https://raw.githubusercontent.com/lmarecha78/RFP_AI_tool/main/skyhigh_bg.png")

###############################################################################
# 3) PASSWORD CHECK (two-click approach without st.experimental_rerun)
###############################################################################
if "password_authenticated" not in st.session_state:
    st.session_state.password_authenticated = False

if not st.session_state.password_authenticated:
    st.title("Enter Password to Access the App")
    pwd = st.text_input("Password", type="password")
    if st.button("Submit Password"):
        # Compare typed password to the one stored in Streamlit secrets
        if pwd == st.secrets["app_password"]:
            st.session_state.password_authenticated = True
            st.success("Password correct! Please refresh or click any button to proceed.")
            # We stop here so the main page won't show in this same run
            st.stop()
        else:
            st.error("Incorrect password. Please try again.")

    # If still not authenticated, stop to avoid showing the main page
    st.stop()

###############################################################################
# 4) MAIN APP (only runs if password_authenticated == True at script start)
###############################################################################
st.title("Skyhigh Security - RFI/RFP AI Tool")

# Simple dynamic UI approach
if "ui_version" not in st.session_state:
    st.session_state.ui_version = 0

def restart_ui():
    st.session_state.ui_version += 1

st.button("🔄 Restart", key=f"restart_button_{st.session_state.ui_version}", on_click=restart_ui)

# Retrieve session state for dynamic UI
customer_name_val = st.session_state.get(f"customer_name_{st.session_state.ui_version}", "").strip()
uploaded_file_val = st.session_state.get(f"uploaded_file_{st.session_state.ui_version}", None)
column_location_val = st.session_state.get(f"column_location_{st.session_state.ui_version}", "").strip()
unique_question_val = st.session_state.get(f"unique_question_{st.session_state.ui_version}", "").strip()

# Disable logic
disable_unique = bool(customer_name_val or uploaded_file_val or column_location_val)
disable_multi = bool(unique_question_val)

customer_name = st.text_input(
    "Customer Name",
    key=f"customer_name_{st.session_state.ui_version}",
    disabled=disable_multi
)

uploaded_file = st.file_uploader(
    "Upload a CSV or XLS file (single worksheet).",
    type=["csv", "xls", "xlsx"],
    key=f"uploaded_file_{st.session_state.ui_version}",
    disabled=disable_multi
)

column_location = st.text_input(
    "Specify the column with questions (e.g., B)",
    key=f"column_location_{st.session_state.ui_version}",
    disabled=disable_multi
)

unique_question = st.text_input(
    "Or ask a single unique question here",
    key=f"unique_question_{st.session_state.ui_version}",
    disabled=disable_unique
)

st.markdown("#### **Select Model for Answer Generation**")
model_choice = st.radio(
    "Choose a model:",
    options=["GPT-4.0", "Due Diligence (Fine-Tuned)"],
    captions=[
        "Recommended for technical RFPs/RFIs.",
        "Optimized for Due Diligence and security-related questionnaires."
    ]
)

model_mapping = {
    "GPT-4.0": "gpt-4-turbo",
    "Due Diligence (Fine-Tuned)": "ft:gpt-4o-2024-08-06:personal:skyhigh-due-diligence:BClhZf1W"
}
selected_model = model_mapping[model_choice]

def clean_answer(answer_text):
    return re.sub(r'\*\*(.*?)\*\*', r'\1', answer_text).strip()

if st.button("Submit", key=f"submit_button_{st.session_state.ui_version}"):
    responses = []

    if unique_question:
        questions = [unique_question]
    elif customer_name and uploaded_file and column_location:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file, engine="openpyxl")
            question_index = ord(column_location.strip().upper()) - ord('A')
            questions = df.iloc[:, question_index].dropna().tolist()
        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.stop()
    else:
        st.warning("Please provide either a unique question OR all multi-question fields (Customer Name, File, Column).")
        st.stop()

    st.success(f"Processing {len(questions)} question(s)...")

    import openai
    for idx, question in enumerate(questions, 1):
        prompt = (
            "You are an expert in Skyhigh Security products, providing highly detailed technical responses for an RFP. "
            "Your answer should be strictly technical, sourced exclusively from official Skyhigh Security documentation. "
            "Focus on architecture, specifications, security features, compliance, integrations, and standards. "
            "Do NOT include disclaimers or mention knowledge limitations. Only provide the direct answer.\n\n"
            f"Customer: {customer_name}\n"
            f"Product: {selected_model}\n"
            "### Question:\n"
            f"{question}\n\n"
            "### Direct Answer (from official Skyhigh docs):"
        )

        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )
        answer = clean_answer(response.choices[0].message.content.strip())
        responses.append(answer)

        st.markdown(f"""
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px;">
                <h4 style="color: #F5A623;">Q{idx}: {question}</h4>
                <pre style="color: #FFFFFF; white-space: pre-wrap;">{answer}</pre>
            </div><br>
        """, unsafe_allow_html=True)

    if uploaded_file and len(responses) == len(questions):
        df["Answers"] = pd.Series(responses)
        output = BytesIO()
        df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)
        st.download_button("📥 Download Responses", data=output, file_name="RFP_Responses.xlsx")
