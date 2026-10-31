
import streamlit as st
import pandas as pd
import os
import json
from groq import Groq

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="E-Commerce Sales Analyzer",
    page_icon="📊",
    layout="wide"
)

# ==========================================
# GROQ CONFIGURATION
# ==========================================

MODEL = "openai/gpt-oss-120b"


def get_groq_api_key():
    """Read API key securely from Streamlit Secrets or environment."""

    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return os.getenv("GROQ_API_KEY", "")


# ==========================================
# HELPER FUNCTIONS
# ==========================================

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
            r"[^\d.\-]", "", regex=True
        ),
        errors="coerce"
    )


def money(value):
    return f"{value:,.2f}"


# ==========================================
# APPLICATION HEADER
# ==========================================

st.title("📊 E-Commerce Sales Analyzer")

st.markdown(
    "### Smart Sales Analysis Powered by Groq AI"
)

st.write(
    "Upload your Excel sales report and discover "
    "important business insights using artificial intelligence."
)

st.divider()

# ==========================================
# EXCEL FILE UPLOAD
# ==========================================

uploaded_file = st.file_uploader(
    "📁 Upload your Excel Sales File",
    type=["xlsx", "xls"]
)

if uploaded_file is None:

    st.info("Please upload an Excel file to begin.")

    st.stop()


# ==========================================
# READ EXCEL DATA
# ==========================================

try:

    df = pd.read_excel(uploaded_file)

except Exception as e:

    st.error(f"Unable to read Excel file: {e}")
    st.stop()


if df.empty:

    st.error("Your Excel file is empty.")
    st.stop()


st.success("Excel file uploaded successfully!")

st.subheader("📋 Preview of Your Sales Data")

st.dataframe(
    df.head(100),
    use_container_width=True
)

st.write(f"Total Records: {len(df)}")

# ==========================================
# AUTOMATIC COLUMN DETECTION
# ==========================================

columns = list(df.columns)

product_default = find_column(
    columns,
    ["product", "product name", "item", "item name"]
)

price_default = find_column(
    columns,
    ["price", "unit price", "selling price", "product price"]
)

quantity_default = find_column(
    columns,
    ["quantity", "qty", "units sold", "quantity sold"]
)

category_default = find_column(
    columns,
    ["category", "product category", "type"]
)

revenue_default = find_column(
    columns,
    ["revenue", "total sales", "sales amount", "total amount"]
)

st.divider()

st.subheader("⚙️ Select Your Excel Columns")

st.caption(
    "Check the detected columns and change them if necessary."
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


# ==========================================
# DATA CLEANING AND PROCESSING
# ==========================================

data = pd.DataFrame({

    "Product": df[product_col],
    "Price": clean_number(df[price_col]),
    "Quantity": clean_number(df[quantity_col]),
    "Category": df[category_col]

})

if revenue_col != "Calculate automatically":

    data["Revenue"] = clean_number(df[revenue_col])

else:

    data["Revenue"] = (
        data["Price"] * data["Quantity"]
    )


data = data.dropna(
    subset=[
        "Product",
        "Price",
        "Quantity",
        "Category",
        "Revenue"
    ]
)

if data.empty:

    st.error(
        "No valid sales records found. "
        "Please check your Excel columns."
    )

    st.stop()


if (
    (data["Price"] < 0).any()
    or (data["Quantity"] < 0).any()
    or (data["Revenue"] < 0).any()
):

    st.error(
        "Negative values were found in your sales data. "
        "Please correct your Excel file."
    )

    st.stop()


# ==========================================
# SALES CALCULATIONS
# ==========================================

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

best_product = product_sales.idxmax()

worst_product = product_sales.idxmin()

highest_price_product = product_prices["max"].idxmax()

lowest_price_product = product_prices["min"].idxmin()

highest_quantity_product = product_quantity.idxmax()

highest_category = category_sales.idxmax()


# ==========================================
# DISPLAY DASHBOARD
# ==========================================

st.divider()

st.header("📈 Sales Dashboard")

m1, m2, m3 = st.columns(3)

m1.metric(
    "Total Revenue",
    money(total_revenue)
)

m2.metric(
    "Unique Categories",
    unique_categories
)

m3.metric(
    "Total Products",
    data["Product"].nunique()
)


# ==========================================
# ANSWERS TO 8 QUESTIONS
# ==========================================

st.header("🏆 Answers to Your 8 Questions")

results = [

    (
        "1. Best Performing Product",
        f"{best_product} - {money(product_sales.max())}"
    ),

    (
        "2. Product with Highest Price",
        f"{highest_price_product} - "
        f"{money(product_prices['max'].max())}"
    ),

    (
        "3. Product with Lowest Price",
        f"{lowest_price_product} - "
        f"{money(product_prices['min'].min())}"
    ),

    (
        "4. Worst Performing Product",
        f"{worst_product} - {money(product_sales.min())}"
    ),

    (
        "5. Number of Unique Categories",
        str(unique_categories)
    ),

    (
        "6. Total Store Revenue",
        money(total_revenue)
    ),

    (
        "7. Highest Revenue Category",
        f"{highest_category} - {money(category_sales.max())}"
    ),

    (
        "8. Product with Highest Quantity Sold",
        f"{highest_quantity_product} - "
        f"{money(product_quantity.max())} units"
    )

]

for question, answer in results:

    st.markdown(f"**{question}**")

    st.success(answer)


# ==========================================
# SALES CHARTS
# ==========================================

st.divider()

st.header("📊 Sales Visualization")

chart1, chart2 = st.columns(2)

with chart1:

    st.subheader("Revenue by Product")

    st.bar_chart(product_sales)

with chart2:

    st.subheader("Revenue by Category")

    st.bar_chart(category_sales)


st.subheader("Quantity Sold by Product")

st.bar_chart(product_quantity)


# ==========================================
# GROQ AI BUSINESS ANALYSIS
# ==========================================

st.divider()

st.header("🤖 AI Business Insights")

if st.button("✨ Generate AI Insights", type="primary"):

    api_key = get_groq_api_key()

    if not api_key:

        st.error(
            "Groq API key not found. "
            "Please configure GROQ_API_KEY in Streamlit Cloud Secrets."
        )

    else:

        try:

            client = Groq(api_key=api_key)

            summary = {

                "total_revenue": float(total_revenue),

                "unique_categories": int(unique_categories),

                "best_product": str(best_product),

                "best_product_revenue": float(
                    product_sales.max()
                ),

                "worst_product": str(worst_product),

                "worst_product_revenue": float(
                    product_sales.min()
                ),

                "highest_price_product": str(
                    highest_price_product
                ),

                "highest_price": float(
                    product_prices["max"].max()
                ),

                "lowest_price_product": str(
                    lowest_price_product
                ),

                "lowest_price": float(
                    product_prices["min"].min()
                ),

                "highest_quantity_product": str(
                    highest_quantity_product
                ),

                "highest_quantity": float(
                    product_quantity.max()
                ),

                "highest_revenue_category": str(
                    highest_category
                ),

                "category_revenue": {
                    str(k): float(v)
                    for k, v in category_sales.items()
                },

                "product_revenue": {
                    str(k): float(v)
                    for k, v in product_sales.items()
                }

            }

            prompt = f"""
You are a professional E-Commerce Business Analyst.

Analyze the following sales data:

{json.dumps(summary, indent=2)}

Prepare a professional business report with:

1. Overall business performance.
2. Best-selling product analysis.
3. Worst-performing product analysis.
4. Category revenue analysis.
5. Pricing analysis.
6. Quantity sold analysis.
7. Three recommendations to increase sales.
8. Final business conclusion.

Use simple English.
Use clear headings and bullet points.
Only use the supplied statistics.
Do not invent information.
"""

            with st.spinner(
                "Groq AI is analyzing your sales data..."
            ):

                response = client.chat.completions.create(

                    model=MODEL,

                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],

                    temperature=0.4

                )

                ai_result = (
                    response.choices[0].message.content
                )

            st.success("AI Analysis Completed!")

            st.markdown(ai_result)

        except Exception as e:

            st.error(f"Groq API Error: {e}")


# ==========================================
# DOWNLOAD REPORT
# ==========================================

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

    label="Download Analysis Report",

    data=csv_data,

    file_name="ecommerce_sales_analysis.csv",

    mime="text/csv"

)


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "E-Commerce Sales Analyzer | "
    "Python + Streamlit + Pandas + Groq AI"
)
