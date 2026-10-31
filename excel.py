
import streamlit as st
import pandas as pd
import os
import json
import hashlib
from groq import Groq

# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="E-Commerce Sales Analyzer",
    page_icon="📊",
    layout="wide"
)

# =====================================================
# 2. GROQ API CONFIGURATION
# =====================================================

MODEL = "openai/gpt-oss-120b"


def get_api_key():
    """Load Groq API key securely."""

    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if key:
            return key
    except Exception:
        pass

    return os.getenv("GROQ_API_KEY", "")


def ask_groq(messages):
    """Send messages to Groq AI."""

    api_key = get_api_key()

    if not api_key:
        raise ValueError(
            "Groq API key is missing. "
            "Please configure GROQ_API_KEY."
        )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3
    )

    return response.choices[0].message.content


# =====================================================
# 3. HELPER FUNCTIONS
# =====================================================

def find_column(columns, possible_names):

    normalized = {
        str(col).strip().lower().replace("_", " ").replace("-", " "): col
        for col in columns
    }

    for name in possible_names:
        if name in normalized:
            return normalized[name]

    for name in possible_names:
        for normalized_name, original_name in normalized.items():
            if name in normalized_name:
                return original_name

    return None


def clean_number(series):

    return pd.to_numeric(
        series.astype(str).str.replace(
            r"[^\d.\-]", "",
            regex=True
        ),
        errors="coerce"
    )


def format_money(value):
    return f"{value:,.2f}"


def reset_chat(file_id):

    if st.session_state.get("file_id") != file_id:

        st.session_state.file_id = file_id
        st.session_state.chat_messages = []
        st.session_state.ai_report = None


# =====================================================
# 4. INITIALIZE SESSION STATE
# =====================================================

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "ai_report" not in st.session_state:
    st.session_state.ai_report = None


# =====================================================
# 5. APPLICATION HEADER
# =====================================================

st.title("📊 E-Commerce Sales Analyzer")

st.subheader(
    "AI-Powered Sales Dashboard & Excel Chatbot"
)

st.write(
    "Upload your Excel sales report and use artificial "
    "intelligence to understand your store's performance."
)

st.divider()


# =====================================================
# 6. EXCEL FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "📁 Upload Your Excel Sales File",
    type=["xlsx", "xls"]
)

if uploaded_file is None:

    st.info("Please upload an Excel file to begin.")

    st.stop()


# =====================================================
# 7. READ EXCEL DATA
# =====================================================

try:

    file_bytes = uploaded_file.getvalue()

    file_id = hashlib.md5(file_bytes).hexdigest()

    reset_chat(file_id)

    df = pd.read_excel(uploaded_file)

except Exception as error:

    st.error(f"Excel Processing Error: {error}")

    st.stop()


if df.empty:

    st.error("The uploaded Excel file is empty.")

    st.stop()


st.success("Excel file uploaded successfully!")

st.subheader("📋 Uploaded Excel Data")

st.dataframe(
    df.head(100),
    use_container_width=True
)

st.caption(f"Total records: {len(df)}")


# =====================================================
# 8. AUTOMATIC COLUMN DETECTION
# =====================================================

columns = list(df.columns)

if len(columns) < 4:

    st.error(
        "Your Excel file should contain product, price, "
        "quantity and category columns."
    )

    st.stop()


product_default = find_column(
    columns,
    ["product name", "product", "item name", "item"]
)

price_default = find_column(
    columns,
    ["unit price", "selling price", "product price", "price"]
)

quantity_default = find_column(
    columns,
    ["quantity sold", "units sold", "quantity", "qty"]
)

category_default = find_column(
    columns,
    ["product category", "category", "type"]
)

revenue_default = find_column(
    columns,
    ["total revenue", "revenue", "total sales",
     "sales amount", "total amount"]
)


# =====================================================
# 9. COLUMN SELECTION
# =====================================================

st.divider()

st.header("⚙️ Configure Your Excel Columns")

st.write(
    "Select the correct columns. The application "
    "automatically detects common column names."
)

col1, col2 = st.columns(2)

with col1:

    product_col = st.selectbox(
        "Product Name",
        columns,
        index=columns.index(product_default)
        if product_default in columns else 0
    )

    price_col = st.selectbox(
        "Product Price",
        columns,
        index=columns.index(price_default)
        if price_default in columns else 0
    )

    quantity_col = st.selectbox(
        "Quantity Sold",
        columns,
        index=columns.index(quantity_default)
        if quantity_default in columns else 0
    )


with col2:

    category_col = st.selectbox(
        "Product Category",
        columns,
        index=columns.index(category_default)
        if category_default in columns else 0
    )

    revenue_options = ["Calculate automatically"] + columns

    revenue_index = (
        revenue_options.index(revenue_default)
        if revenue_default in columns else 0
    )

    revenue_col = st.selectbox(
        "Revenue Column (Optional)",
        revenue_options,
        index=revenue_index
    )


# =====================================================
# 10. CLEAN AND PROCESS DATA
# =====================================================

data = pd.DataFrame({

    "Product": df[product_col].astype("string").str.strip(),

    "Price": clean_number(df[price_col]),

    "Quantity": clean_number(df[quantity_col]),

    "Category": df[category_col].astype("string").str.strip()

})


# Calculate revenue

if revenue_col == "Calculate automatically":

    data["Revenue"] = (
        data["Price"] * data["Quantity"]
    )

else:

    data["Revenue"] = clean_number(df[revenue_col])


# Remove invalid rows

data = data.dropna(
    subset=[
        "Product",
        "Price",
        "Quantity",
        "Category",
        "Revenue"
    ]
)

data = data[
    (data["Product"] != "") &
    (data["Category"] != "")
]


if data.empty:

    st.error("No valid sales records found.")

    st.stop()


if (
    (data["Price"] < 0).any()
    or (data["Quantity"] < 0).any()
    or (data["Revenue"] < 0).any()
):

    st.error(
        "Negative prices, quantities or revenue were found. "
        "Please correct your Excel file."
    )

    st.stop()


# =====================================================
# 11. SALES ANALYSIS
# =====================================================

product_sales = (
    data.groupby("Product")["Revenue"]
    .sum()
    .sort_values(ascending=False)
)

product_quantity = (
    data.groupby("Product")["Quantity"]
    .sum()
    .sort_values(ascending=False)
)

product_prices = data.groupby("Product")["Price"].agg(
    ["max", "min"]
)

category_sales = (
    data.groupby("Category")["Revenue"]
    .sum()
    .sort_values(ascending=False)
)

total_revenue = data["Revenue"].sum()

unique_categories = data["Category"].nunique()

total_products = data["Product"].nunique()

best_product = product_sales.idxmax()

worst_product = product_sales.idxmin()

highest_price_product = product_prices["max"].idxmax()

lowest_price_product = product_prices["min"].idxmin()

highest_quantity_product = product_quantity.idxmax()

highest_category = category_sales.idxmax()


# =====================================================
# 12. SALES DASHBOARD
# =====================================================

st.divider()

st.header("📈 Sales Dashboard")

m1, m2, m3 = st.columns(3)

m1.metric(
    "Total Revenue",
    format_money(total_revenue)
)

m2.metric(
    "Unique Categories",
    unique_categories
)

m3.metric(
    "Total Products",
    total_products
)


# =====================================================
# 13. ANSWERS TO 8 QUESTIONS
# =====================================================

st.divider()

st.header("🏆 Answers to 8 Sales Questions")

results = [

    (
        "1. Best Performing Product",
        f"{best_product} | Revenue: "
        f"{format_money(product_sales.max())}"
    ),

    (
        "2. Product with Highest Price",
        f"{highest_price_product} | Price: "
        f"{format_money(product_prices['max'].max())}"
    ),

    (
        "3. Product with Lowest Price",
        f"{lowest_price_product} | Price: "
        f"{format_money(product_prices['min'].min())}"
    ),

    (
        "4. Worst Performing Product",
        f"{worst_product} | Revenue: "
        f"{format_money(product_sales.min())}"
    ),

    (
        "5. Number of Unique Categories",
        str(unique_categories)
    ),

    (
        "6. Total Store Revenue",
        format_money(total_revenue)
    ),

    (
        "7. Highest Revenue Category",
        f"{highest_category} | Revenue: "
        f"{format_money(category_sales.max())}"
    ),

    (
        "8. Product with Highest Quantity Sold",
        f"{highest_quantity_product} | Quantity: "
        f"{format_money(product_quantity.max())}"
    )

]

for question, answer in results:

    st.markdown(f"**{question}**")

    st.success(answer)


# =====================================================
# 14. SALES CHARTS
# =====================================================

st.divider()

st.header("📊 Sales Visualizations")

chart1, chart2 = st.columns(2)

with chart1:

    st.subheader("Revenue by Product")

    st.bar_chart(product_sales)

with chart2:

    st.subheader("Revenue by Category")

    st.bar_chart(category_sales)

st.subheader("Quantity Sold by Product")

st.bar_chart(product_quantity)


# =====================================================
# 15. PREPARE DATA FOR GROQ AI
# =====================================================

sales_summary = {

    "total_revenue": float(total_revenue),

    "total_products": int(total_products),

    "unique_categories": int(unique_categories),

    "best_product": str(best_product),

    "best_product_revenue": float(product_sales.max()),

    "worst_product": str(worst_product),

    "worst_product_revenue": float(product_sales.min()),

    "highest_price_product": str(highest_price_product),

    "highest_price": float(product_prices["max"].max()),

    "lowest_price_product": str(lowest_price_product),

    "lowest_price": float(product_prices["min"].min()),

    "highest_quantity_product": str(highest_quantity_product),

    "highest_quantity": float(product_quantity.max()),

    "highest_revenue_category": str(highest_category),

    "product_revenue": {
        str(k): float(v)
        for k, v in product_sales.items()
    },

    "product_quantity": {
        str(k): float(v)
        for k, v in product_quantity.items()
    },

    "category_revenue": {
        str(k): float(v)
        for k, v in category_sales.items()
    },

    "product_prices": {
        str(k): {
            "highest_price": float(v["max"]),
            "lowest_price": float(v["min"])
        }
        for k, v in product_prices.iterrows()
    }

}


# =====================================================
# 16. GROQ AI BUSINESS REPORT
# =====================================================

st.divider()

st.header("🤖 AI Business Insights")

if st.button(
    "✨ Generate AI Business Report",
    type="primary"
):

    prompt = f"""
You are a professional E-Commerce Business Analyst.

Analyze the following Excel sales statistics:

{json.dumps(sales_summary, indent=2)}

Create a professional business report containing:

1. Overall business performance.
2. Best-performing product.
3. Worst-performing product.
4. Product category analysis.
5. Product pricing analysis.
6. Quantity sold analysis.
7. Three recommendations to increase revenue.
8. Final conclusion.

Use simple English.
Use headings and bullet points.
Only use the supplied data.
Do not invent statistics.
"""

    try:

        with st.spinner("Groq AI is analyzing your sales data..."):

            st.session_state.ai_report = ask_groq([
                {
                    "role": "user",
                    "content": prompt
                }
            ])

    except Exception as error:

        st.error(f"Groq API Error: {error}")


# Display report after button reruns

if st.session_state.ai_report:

    st.subheader("📑 Generated Business Report")

    st.markdown(st.session_state.ai_report)


# =====================================================
# 17. GROQ AI EXCEL CHATBOT
# =====================================================

st.divider()

st.header("💬 Chat with Your Excel Data")

st.write(
    "Ask questions about your uploaded Excel sheet. "
    "Your AI chatbot will analyze the sales information "
    "and provide answers."
)

st.info(
    "Example: Which product generated the most revenue? "
    "Which category has the lowest sales? Compare two products."
)


# Build chatbot data from the COMPLETE dataset summaries

chatbot_data = {

    "sales_summary": sales_summary,

    "total_valid_records": int(len(data)),

    # Detailed records are included for row-level questions.
    # For large files, only the first 300 rows are sent.
    "excel_records": data.head(300).to_dict(
        orient="records"
    )

}

records_note = (
    "All original records are included."
    if len(data) <= 300
    else (
        f"Only the first 300 of {len(data)} original records "
        "are included. Aggregated product and category "
        "statistics cover the complete dataset."
    )
)

system_prompt = f"""
You are an intelligent E-Commerce Sales Excel Chatbot.

Your purpose is to answer the user's questions about
their uploaded Excel sales data.

UPLOADED DATA:

{json.dumps(chatbot_data, default=str)}

RECORD COVERAGE:

{records_note}

INSTRUCTIONS:

1. Answer questions using the uploaded Excel data.
2. Use the complete aggregated summaries for overall
   revenue, product sales, quantities and category rankings.
3. Use the supplied original records for detailed
   row-level questions.
4. Never invent product names, prices, quantities or revenue.
5. If the requested information is unavailable, say so.
6. If only some original records are available, explain
   that limitation when answering row-level questions.
7. If asked to compare products, use the supplied
   product statistics.
8. If asked for business advice, provide practical
   recommendations based on the data.
9. If a question is unrelated to the uploaded Excel file,
   politely explain that you are an Excel Data Assistant.
10. Use clear English, headings and bullet points.
11. Do not claim to have checked records that were not supplied.
"""


# Display previous chat history

for message in st.session_state.chat_messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# Chat history controls

if st.button("🗑️ Clear Chat History"):

    st.session_state.chat_messages = []

    st.rerun()


# User chat input

user_question = st.chat_input(
    "Type your question about the Excel data..."
)


if user_question:

    try:

        # Prepare conversation history

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        messages.extend(
            st.session_state.chat_messages[-10:]
        )

        messages.append({

            "role": "user",

            "content": user_question

        })


        # Display user's message

        with st.chat_message("user"):

            st.markdown(user_question)


        # Generate AI answer

        with st.chat_message("assistant"):

            with st.spinner("Groq AI is analyzing your Excel data..."):

                bot_answer = ask_groq(messages)

                st.markdown(bot_answer)


        # Save conversation

        st.session_state.chat_messages.append({

            "role": "user",

            "content": user_question

        })

        st.session_state.chat_messages.append({

            "role": "assistant",

            "content": bot_answer

        })


    except Exception as error:

        st.error(f"Chatbot Error: {error}")


# =====================================================
# 18. DOWNLOAD SALES REPORT
# =====================================================

st.divider()

st.header("📥 Download Sales Report")

report = pd.DataFrame(
    results,
    columns=["Question", "Answer"]
)

csv_data = report.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="⬇️ Download Analysis Report",
    data=csv_data,
    file_name="ecommerce_sales_analysis.csv",
    mime="text/csv"
)


# =====================================================
# 19. FOOTER
# =====================================================

st.divider()

st.caption(
    "E-Commerce Sales Analyzer | "
    "Python | Streamlit | Pandas | Groq AI"
)
