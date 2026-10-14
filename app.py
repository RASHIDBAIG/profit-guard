import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import plotly.express as px
import os
import uuid
import json
import requests
import pyotp
import qrcode
import io

# ==========================================
# CONFIG
# ==========================================
YOUR_NAME = "Rashid Baig"
YOUR_WHATSAPP = "+92 333 9228768"
YOUR_EMAIL = "rashidbaig123kid@gmail.com"
YOUR_KOFI = "https://ko-fi.com/profitguard"
YOUR_SADAPAY = "0333 9228768"
YOUR_UBL = "PK67UNIL0109000337172553"
GITHUB_RAW = "https://raw.githubusercontent.com/RASHIDBAIG/profit-guard/main"
YOUTUBE_VIDEO = "https://www.youtube.com/watch?v=vh3ZD-YLqPo"

st.set_page_config(page_title="Profit Guard", page_icon="rocket", layout="wide")

# Google Analytics - Measurement Protocol
try:
    GA_ID = st.secrets["ga"]["measurement_id"]
except Exception:
    GA_ID = ""

try:
    GA_API_SECRET = st.secrets["ga"]["api_secret"]
except Exception:
    GA_API_SECRET = ""

import random
if "ga_client_id" not in st.session_state:
    st.session_state.ga_client_id = str(random.randint(1000000000, 9999999999)) + "." + str(int(pd.Timestamp.now().timestamp()))

GA_CLIENT_ID = st.session_state.ga_client_id

def fetch_user_logs():
    """Fetch user logs from Google Sheet via Apps Script doGet"""
    try:
        webhook = st.secrets["tracking"]["webhook_url"]
        if "YOUR_SCRIPT_ID" in webhook:
            return None
        r = requests.get(webhook, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                return df
            else:
                return pd.DataFrame()
        return None
    except Exception:
        return None


def send_ga_event(event_name, params=None):
    if not GA_ID or not GA_API_SECRET:
        return
    try:
        url = "https://www.google-analytics.com/mp/collect"
        p = params or {}
        p["session_id"] = SESSION_ID
        p["engagement_time_msec"] = "100"
        payload = {
            "client_id": GA_CLIENT_ID,
            "events": [{"name": event_name, "params": p}]
        }
        requests.post(
            url,
            params={"measurement_id": GA_ID, "api_secret": GA_API_SECRET},
            json=payload,
            timeout=3
        )
    except Exception:
        pass

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    [data-testid="baseButton-header"] {display: none;}
    .main-header {
        background: linear-gradient(90deg, #1DB954 0%, #191414 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    section[data-testid="stSidebar"] {
        min-width: 340px !important;
        max-width: 340px !important;
        width: 340px !important;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        font-size: 15px !important;
        padding: 8px 4px !important;
        margin-bottom: 2px !important;
        border-radius: 6px !important;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background-color: #f0f2f6 !important;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .main-header { padding: 12px !important; }
        .main-header h1 { font-size: 22px !important; }
        .main-header p { font-size: 12px !important; }
        .stButton > button {
            width: 100% !important;
            min-height: 44px !important;
            font-size: 14px !important;
        }
        .stTextInput > div > input {
            min-height: 44px !important;
            font-size: 16px !important;
        }
        .stSelectbox > div > div { min-height: 44px !important; }
        .stFileUploader { padding: 10px !important; }
        [data-testid="stMetricValue"] { font-size: 20px !important; }
        [data-testid="stMetricLabel"] { font-size: 12px !important; }
        .stDataFrame { font-size: 12px !important; }
        .stTabs [data-baseweb="tab"] {
            font-size: 13px !important;
            padding: 8px 12px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# CURRENCIES
CURRENCY_OPTIONS = {
    "PKR (Pakistani Rupee)": {"code": "PKR", "rate_kg": 150, "shipping": 250, "rto": 850, "aov": 3000},
    "USD (US Dollar)":       {"code": "USD", "rate_kg": 0.54, "shipping": 0.90, "rto": 3.05, "aov": 10.80},
    "AED (UAE Dirham)":      {"code": "AED", "rate_kg": 1.98, "shipping": 3.30, "rto": 11.23, "aov": 39.63},
    "SAR (Saudi Riyal)":     {"code": "SAR", "rate_kg": 2.03, "shipping": 3.38, "rto": 11.49, "aov": 40.54},
    "GBP (British Pound)":   {"code": "GBP", "rate_kg": 0.43, "shipping": 0.71, "rto": 2.43, "aov": 8.57},
    "EUR (Euro)":            {"code": "EUR", "rate_kg": 0.50, "shipping": 0.83, "rto": 2.83, "aov": 10.00},
}

# ==========================================
# USER TRACKING
# ==========================================
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.session_state.first_seen = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

SESSION_ID = st.session_state.session_id

def get_user_info():
    try:
        headers = st.context.headers if hasattr(st, 'context') else {}
        ip = headers.get("X-Forwarded-For", headers.get("X-Real-Ip", "unknown"))
        ua = headers.get("User-Agent", "unknown")
        return ip, ua
    except Exception:
        return "unknown", "unknown"

def track_event(event_name, params=None):
    send_ga_event(event_name, params)

def log_to_sheet(action, details=""):
    try:
        webhook = st.secrets["tracking"]["webhook_url"]
        if "YOUR_SCRIPT_ID" in webhook:
            return
        ip, ua = get_user_info()
        payload = {
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": SESSION_ID,
            "action": action,
            "details": details,
            "ip": ip,
            "user_agent": ua[:200],
        }
        requests.post(webhook, json=payload, timeout=3)
    except Exception:
        pass

def track(action, details=""):
    track_event(action, {"details": details})
    log_to_sheet(action, details)

# ==========================================
# SIDEBAR: CURRENCY
# ==========================================
st.sidebar.markdown("### Currency")
currency_choice = st.sidebar.selectbox("Select currency:", list(CURRENCY_OPTIONS.keys()), index=0)
CUR = CURRENCY_OPTIONS[currency_choice]
CURRENCY = CUR["code"]
D_RATE = CUR["rate_kg"]
D_SHIP = CUR["shipping"]
D_RTO = CUR["rto"]
D_AOV = CUR["aov"]

if st.session_state.get('last_currency') != currency_choice:
    track("currency_change", currency_choice)
    st.session_state.last_currency = currency_choice

# PLATFORM
st.sidebar.markdown("---")
st.sidebar.markdown("### Platform")
st.sidebar.caption("This name appears on all reports.")
platform = st.sidebar.selectbox(
    "Select platform:",
    ["Shopify", "Shopify Plus", "WooCommerce", "WordPress", "Magento", "BigCommerce", "Wix", "Squarespace",
     "PrestaShop", "OpenCart", "Daraz", "Amazon", "eBay", "Etsy", "TikTok Shop", "Facebook Shop",
     "Instagram Shop", "WhatsApp Business", "Custom PHP / Laravel", "Custom Node.js", "Manual / Excel", "Other"],
    index=0
)
PLATFORM_NAME = platform

if st.session_state.get('last_platform') != platform:
    track("platform_change", platform)
    st.session_state.last_platform = platform

# HEADER
st.markdown(
    "<div class='main-header'>"
    "<h1>Profit Guard</h1>"
    "<p><b>Platform:</b> " + PLATFORM_NAME + " &nbsp;|&nbsp; <b>Currency:</b> " + CURRENCY +
    " &nbsp;|&nbsp; Courier Fraud, Warehouse Split and Bad Customer Detection</p>"
    "</div>",
    unsafe_allow_html=True
)

if 'app_opened_tracked' not in st.session_state:
    track("app_open", "Platform: " + PLATFORM_NAME)
    st.session_state.app_opened_tracked = True

# MENU
st.sidebar.markdown("---")
st.sidebar.title("Menu")

# ADMIN SECRET - apna secret rakho
try:
    ADMIN_SECRET = st.secrets["admin"]["url_secret"]
except Exception:
    ADMIN_SECRET = "rashid_admin_2026_x9k"

try:
    query_params = st.query_params
    admin_mode = query_params.get("mode", "") == ADMIN_SECRET
except Exception:
    admin_mode = False

if admin_mode:
    option = "Admin (Private)"
    st.sidebar.success("Admin Mode Active")
    st.sidebar.caption("Client view ke liye URL se ?mode= hatao")
else:
    option = st.sidebar.radio(
        "Choose a section:",
        ["Dashboard", "Problem 1: Courier Fraud", "Problem 2: Warehouse Split", "Problem 3: Bad Customers",
         "Email Template", "Help & Client Guide", "About"]
    )

if st.session_state.get('last_option') != option:
    track("section_view", option)
    st.session_state.last_option = option

st.sidebar.markdown("---")
st.sidebar.info("**How to use:**\n\n1. Export CSV from your store\n2. Upload in the matching section\n3. Get instant report\n4. Download PDF and claim refund")

# SIDEBAR SUPPORT
st.sidebar.markdown("---")
st.sidebar.markdown("### Support This Tool")
st.sidebar.markdown(
    "<a href='" + YOUR_KOFI + "' target='_blank' style='text-decoration:none;'>"
    "<div style='background:#FF5E5B; padding:10px; border-radius:8px; text-align:center; color:white; font-weight:bold; font-size:13px; margin-bottom:8px;'>"
    "Buy Me a Coffee"
    "</div>"
    "</a>"
    "<div style='background:#9FE870; padding:10px; border-radius:8px; text-align:center; font-size:11px; margin-bottom:8px; color:#163300; font-weight:bold;'>"
    "Wise: " + YOUR_EMAIL +
    "</div>"
    "<div style='background:#FF6B35; padding:10px; border-radius:8px; text-align:center; color:white; font-weight:bold; font-size:13px;'>"
    "SadaPay: " + YOUR_SADAPAY +
    "</div>",
    unsafe_allow_html=True
)

st.sidebar.markdown("---")
st.sidebar.caption("Profit Guard v1.0 | " + PLATFORM_NAME + " | " + CURRENCY)
st.sidebar.caption("Session: " + SESSION_ID)

# ==========================================
# HELPERS
# ==========================================
def read_file(uploaded):
    if uploaded.name.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded)
    for enc in ['utf-8', 'utf-8-sig', 'latin1']:
        try:
            return pd.read_csv(uploaded, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(uploaded)

def find_col(df, aliases, required=True, label='column'):
    for a in aliases:
        for c in df.columns:
            if str(c).strip().lower() == str(a).strip().lower():
                return c
    for a in aliases:
        for c in df.columns:
            if str(a).strip().lower() in str(c).strip().lower():
                return c
    if required:
        raise ValueError(label + " not found. Available: " + str(list(df.columns)))
    return None

def clean_id(series):
    return series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.replace('#', '', regex=False).str.upper()

def to_kg(series, unit):
    x = pd.to_numeric(series, errors='coerce')
    if str(unit).lower() == 'g':
        x = x / 1000.0
    return x

def fmt_money(amount):
    return CURRENCY + " " + (f"{amount:,.2f}" if amount < 100 else f"{int(amount):,}")

def csv_bytes(df):
    return df.to_csv(index=False).encode('utf-8')

def pdf_client_report(report_df, total_orders, total_kg, total_refund):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(29, 185, 84)
    pdf.cell(0, 12, PLATFORM_NAME + " Profit Guard", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 13)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, PLATFORM_NAME + " Courier Fraud Detection Report", ln=True, align="C")
    pdf.ln(2)
    pdf.set_draw_color(29, 185, 84)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(25, 20, 20)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, "Total Orders Analyzed:  " + str(total_orders), ln=True)
    pdf.cell(0, 8, "Overcharged Orders:  " + str(len(report_df)), ln=True)
    pdf.cell(0, 8, "Total Extra Weight Billed:  " + str(round(total_kg, 2)) + " kg", ln=True)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(200, 50, 50)
    pdf.cell(0, 10, "Total Refund Claim:  " + CURRENCY + " " + f"{total_refund:,.2f}", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(25, 20, 20)
    pdf.cell(0, 10, "Overcharged Orders Detail", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(29, 185, 84)
    pdf.set_text_color(255, 255, 255)
    headers = ["Order ID", "Actual (kg)", "Billed (kg)", "Overcharge (kg)", "Refund (" + CURRENCY + ")"]
    widths = [40, 35, 35, 40, 40]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)
    fill = False
    for idx, row in report_df.head(30).iterrows():
        if fill:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(widths[0], 7, str(row.get('Order ID', ''))[:20], border=1, fill=fill, align="C")
        pdf.cell(widths[1], 7, f"{row.get('actual_weight_kg', 0):.2f}", border=1, fill=fill, align="C")
        pdf.cell(widths[2], 7, f"{row.get('billed_weight_kg', 0):.2f}", border=1, fill=fill, align="C")
        pdf.cell(widths[3], 7, f"{row.get('overcharge_kg', 0):.2f}", border=1, fill=fill, align="C")
        pdf.cell(widths[4], 7, f"{row.get('refund_estimate_pkr', 0):,.2f}", border=1, fill=fill, align="C")
        pdf.ln()
        fill = not fill
    if len(report_df) > 30:
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 8, "(Showing top 30 of " + str(len(report_df)) + " overcharged orders. Full list in CSV report.)", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "Generated by Profit Guard for " + PLATFORM_NAME, ln=True, align="C")
    pdf.cell(0, 8, "WhatsApp: " + YOUR_WHATSAPP + "  |  Email: " + YOUR_EMAIL, ln=True, align="C")
    return bytes(pdf.output())

def show_video_hero():
    st.markdown(
        "<div style='background: linear-gradient(135deg, #1DB954 0%, #191414 100%); "
        "padding: 18px 22px; border-radius: 12px; margin-bottom: 15px; color: white; "
        "box-shadow: 0 4px 15px rgba(29,185,84,0.3);'>"
        "<h3 style='margin: 0; color: white;'>Watch How Profit Guard Works</h3>"
        "<p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;'>Complete video guide</p>"
        "</div>",
        unsafe_allow_html=True
    )
    st.video(YOUTUBE_VIDEO)

def show_support():
    st.markdown("---")
    st.markdown(
        "<div style='background: linear-gradient(135deg, #1DB954 0%, #191414 100%); "
        "padding: 25px; border-radius: 12px; margin-top: 20px; color: white; "
        "box-shadow: 0 6px 20px rgba(29,185,84,0.3);'>"
        "<div style='text-align: center;'>"
        "<div style='font-size: 20px; font-weight: bold; margin-bottom: 10px;'>Support This Free Tool</div>"
        "<div style='font-size: 15px; margin-bottom: 20px;'>This tool is 100% free. If it helped you save money, consider supporting!</div>"
        "</div>"
        "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 15px;'>"
        "<a href='" + YOUR_KOFI + "' target='_blank' style='text-decoration: none;'>"
        "<div style='background: #FF5E5B; padding: 12px 16px; border-radius: 8px; color: white; text-align: center; font-weight: bold; font-size: 13px;'>"
        "Buy Me a Coffee</div></a>"
        "<a href='mailto:" + YOUR_EMAIL + "' style='text-decoration: none;'>"
        "<div style='background: #9FE870; padding: 12px 16px; border-radius: 8px; color: #163300; text-align: center; font-weight: bold; font-size: 13px;'>"
        "Wise (International)</div></a>"
        "<div style='background: #FF6B35; padding: 12px 16px; border-radius: 8px; color: white; text-align: center; font-weight: bold; font-size: 13px;'>"
        "SadaPay: " + YOUR_SADAPAY + "</div>"
        "<div style='background: #1DB954; padding: 12px 16px; border-radius: 8px; color: white; text-align: center; font-weight: bold; font-size: 11px;'>"
        "UBL: " + YOUR_UBL + "</div>"
        "</div>"
        "<div style='text-align: center; margin-top: 15px; font-size: 12px; opacity: 0.85;'>"
        "WhatsApp: <b>" + YOUR_WHATSAPP + "</b> &nbsp;|&nbsp; Email: <b>" + YOUR_EMAIL + "</b>"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

# ==========================================
# DASHBOARD
# ==========================================
if option == "Dashboard":
    st.header("Profit Guard Dashboard")
    st.write("Welcome! This tool finds hidden money leaks in your e-commerce business.")

    with st.expander("Watch Help Video (First time here? Click here)", expanded=False):
        st.video(YOUTUBE_VIDEO)

    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            "### Courier Fraud\n"
            "Couriers overcharge by using **volumetric weight** instead of actual weight. "
            "Stores lose **" + CURRENCY + " 50,000 - 5,00,000** every month.\n\n"
            "**What you get:** Refund claim list"
        )
    with c2:
        st.markdown(
            "### Warehouse Split\n"
            "Orders split across warehouses = **double shipping fees**. "
            "Profits vanish on small orders.\n\n"
            "**What you get:** Product pairing insights"
        )
    with c3:
        st.markdown(
            "### Bad Customers\n"
            "High-return customers and fake addresses = **RTO losses**. "
            "Costing thousands monthly.\n\n"
            "**What you get:** Blacklist and warning list"
        )

    st.markdown("---")
    st.markdown(
        "### How to Start\n"
        "1. Go to the matching section from the left menu\n"
        "2. Download sample file to see the format\n"
        "3. Upload your CSV files\n"
        "4. Get instant report\n"
        "5. Download PDF and claim refund from your courier\n\n"
        "**Current Platform:** " + PLATFORM_NAME + " &nbsp;|&nbsp; **Currency:** " + CURRENCY + "\n\n"
        "**Need help?** Contact " + YOUR_NAME + " - WhatsApp: " + YOUR_WHATSAPP
    )
    show_support()

# ==========================================
# PROBLEM 1: COURIER FRAUD
# ==========================================
elif option == "Problem 1: Courier Fraud":
    st.header("Courier Volumetric Weight Fraud Detector")
    st.write("Upload your store orders CSV and courier billing CSV to detect overcharged orders.")

    st.info("New here? Download sample files to understand the format.")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("[Download Sample Store Orders CSV](" + GITHUB_RAW + "/sample_store_orders.csv)")
    with sc2:
        st.markdown("[Download Sample Courier Billing CSV](" + GITHUB_RAW + "/sample_courier_billing.csv)")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Step 1: Store Orders")
        shopify_file = st.file_uploader("Upload Store Orders CSV", type=['csv', 'xlsx', 'xls'], key='s1')
        if shopify_file:
            track("file_upload", "P1_store_orders: " + shopify_file.name)
    with col2:
        st.subheader("Step 2: Courier Billing")
        courier_file = st.file_uploader("Upload Courier Billing CSV", type=['csv', 'xlsx', 'xls'], key='c1')
        if courier_file:
            track("file_upload", "P1_courier_billing: " + courier_file.name)

    with st.expander("Settings (Optional - Defaults are recommended)"):
        s1, s2, s3 = st.columns(3)
        with s1:
            shopify_unit = st.selectbox("Store Weight Unit", ['g', 'kg'], index=0)
        with s2:
            courier_unit = st.selectbox("Courier Weight Unit", ['kg', 'g'], index=0)
        with s3:
            rate_per_kg = st.number_input("Rate per KG (" + CURRENCY + ")", value=float(D_RATE), min_value=0.01)
        tolerance_g = st.slider("Tolerance (grams)", 0, 200, 50)
        vol_divisor = st.number_input("Volumetric Divisor", value=5000, min_value=1000)

    if st.button("Run Fraud Detection", type='primary'):
        track("run_analysis", "P1_fraud_detection")
        if not shopify_file or not courier_file:
            st.error("Please upload both files first.")
        else:
            try:
                with st.spinner("Analyzing data..."):
                    shopify = read_file(shopify_file)
                    courier = read_file(courier_file)

                    shop_order = find_col(shopify, ['Order ID', 'OrderId', 'Name', 'Order Number'], True, 'Order ID')
                    shop_weight = find_col(shopify, ['Weight', 'weight', 'Weight (g)', 'Weight (kg)', 'grams'], True, 'Weight')
                    shop_len = find_col(shopify, ['Length', 'length', 'L'], False)
                    shop_wid = find_col(shopify, ['Width', 'width', 'W'], False)
                    shop_hei = find_col(shopify, ['Height', 'height', 'H'], False)

                    courier_order = find_col(courier, ['Order ID', 'OrderId', 'Tracking ID', 'CN', 'Consignment', 'Reference'], True, 'Courier Order ID')
                    courier_billed = find_col(courier, ['Billed Weight', 'Charged Weight', 'Chargeable Weight', 'Weight'], True, 'Billed Weight')
                    courier_amount = find_col(courier, ['Amount', 'Charge', 'Freight', 'Shipping Fee', 'Total'], False)
                    courier_name = find_col(courier, ['Courier', 'Courier Name', 'Company', 'Service'], False)

                    shopify['_order_id'] = clean_id(shopify[shop_order])
                    courier['_order_id'] = clean_id(courier[courier_order])
                    shopify['_weight_kg'] = to_kg(shopify[shop_weight], shopify_unit)
                    courier['_billed_kg'] = to_kg(courier[courier_billed], courier_unit)

                    for c in [shop_len, shop_wid, shop_hei]:
                        if c:
                            shopify[c + '_num'] = pd.to_numeric(shopify[c], errors='coerce')

                    agg_dict = {'_weight_kg': 'sum'}
                    if shop_len: agg_dict[shop_len + '_num'] = 'max'
                    if shop_wid: agg_dict[shop_wid + '_num'] = 'max'
                    if shop_hei: agg_dict[shop_hei + '_num'] = 'max'

                    shopify_order = shopify.groupby('_order_id').agg(agg_dict).reset_index()
                    order_id_map = shopify.groupby('_order_id')[shop_order].first().reset_index()
                    shopify_order = shopify_order.merge(order_id_map, on='_order_id')
                    shopify_order.rename(columns={shop_order: 'Order ID'}, inplace=True)

                    shopify_order['_length'] = shopify_order.get(shop_len + '_num', np.nan) if shop_len else np.nan
                    shopify_order['_width'] = shopify_order.get(shop_wid + '_num', np.nan) if shop_wid else np.nan
                    shopify_order['_height'] = shopify_order.get(shop_hei + '_num', np.nan) if shop_hei else np.nan

                    courier_agg_dict = {'_billed_kg': 'sum'}
                    if courier_amount: courier_agg_dict[courier_amount] = 'sum'
                    if courier_name: courier_agg_dict[courier_name] = 'first'

                    courier_agg = courier.groupby('_order_id').agg(courier_agg_dict).reset_index()
                    if courier_amount:
                        courier_agg.rename(columns={courier_amount: '_amount'}, inplace=True)
                    else:
                        courier_agg['_amount'] = courier_agg['_billed_kg'] * rate_per_kg
                    if courier_name:
                        courier_agg.rename(columns={courier_name: '_courier'}, inplace=True)
                    else:
                        courier_agg['_courier'] = 'Unknown'

                    df = shopify_order.merge(courier_agg, on='_order_id', how='inner')

                    df['actual_weight_kg'] = df['_weight_kg']
                    df['volumetric_weight_kg'] = (df['_length'] * df['_width'] * df['_height']) / vol_divisor
                    df['expected_billable_kg'] = np.where(df['volumetric_weight_kg'].notna(), np.maximum(df['actual_weight_kg'], df['volumetric_weight_kg']), df['actual_weight_kg'])
                    df['billed_weight_kg'] = df['_billed_kg']
                    df['overcharge_kg'] = df['billed_weight_kg'] - df['expected_billable_kg']
                    df['is_overcharged'] = df['overcharge_kg'] > (tolerance_g / 1000.0)
                    df['refund_estimate_pkr'] = df['overcharge_kg'].clip(lower=0) * rate_per_kg

                    report = df[df['is_overcharged']].copy()
                    report = report.sort_values('overcharge_kg', ascending=False)

                    track("analysis_complete", "P1: " + str(len(df)) + " orders, " + str(len(report)) + " fraud")

                    st.success("Analysis complete. " + str(len(df)) + " orders checked.")

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Orders", len(df))
                    c2.metric("Fraud Orders", len(report), delta=str(len(report)) + " found")
                    c3.metric("Extra Weight", str(round(report['overcharge_kg'].sum(), 2)) + " kg")
                    c4.metric("Refund Claim", fmt_money(report['refund_estimate_pkr'].sum()))

                    st.markdown("### Visual Analysis")
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        top10 = report.head(10).copy()
                        top10['Order ID'] = top10['Order ID'].astype(str)
                        fig = px.bar(top10, x='Order ID', y='refund_estimate_pkr',
                                     title='Top 10 Orders by Refund Amount (' + CURRENCY + ')',
                                     color='refund_estimate_pkr', color_continuous_scale='Reds')
                        fig.update_layout(showlegend=False, height=400)
                        st.plotly_chart(fig, use_container_width=True)

                    with chart_col2:
                        if '_courier' in report.columns and report['_courier'].nunique() > 0:
                            courier_summary = report.groupby('_courier').agg({
                                'refund_estimate_pkr': 'sum',
                                'Order ID': 'count'
                            }).reset_index()
                            courier_summary.columns = ['Courier', 'Refund', 'Orders']
                            fig2 = px.pie(courier_summary, values='Refund', names='Courier',
                                          title='Refund by Courier',
                                          color_discrete_sequence=px.colors.sequential.Greens_r)
                            fig2.update_layout(height=400)
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            fig2 = px.histogram(report, x='overcharge_kg', nbins=20,
                                                title='Distribution of Overcharge Amounts',
                                                color_discrete_sequence=['#1DB954'])
                            fig2.update_layout(height=400)
                            st.plotly_chart(fig2, use_container_width=True)

                    st.markdown("### Top Overcharged Orders")
                    display_df = report[['Order ID', 'actual_weight_kg', 'volumetric_weight_kg',
                                          'expected_billable_kg', 'billed_weight_kg',
                                          'overcharge_kg', 'refund_estimate_pkr']].head(50).copy()
                    display_df.columns = ['Order ID', 'Actual (kg)', 'Volumetric (kg)',
                                          'Expected (kg)', 'Billed (kg)',
                                          'Overcharge (kg)', 'Refund (' + CURRENCY + ')']
                    display_df = display_df.round(2)
                    st.dataframe(display_df, use_container_width=True)

                    d1, d2 = st.columns(2)
                    with d1:
                        if st.download_button(
                            label="Download Client Report (PDF)",
                            data=pdf_client_report(report, len(df), report['overcharge_kg'].sum(), report['refund_estimate_pkr'].sum()),
                            file_name=PLATFORM_NAME + "_Courier_Fraud_Report.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        ):
                            track("download", "P1_courier_fraud_PDF")
                    with d2:
                        if st.download_button(
                            label="Download Full Data (CSV)",
                            data=csv_bytes(report),
                            file_name=PLATFORM_NAME + "_courier_fraud_report.csv",
                            mime="text/csv",
                            use_container_width=True
                        ):
                            track("download", "P1_courier_fraud_CSV")
            except Exception as e:
                st.error("Error: " + str(e))
                st.exception(e)
                track("error", "P1: " + str(e)[:150])

# ==========================================
# PROBLEM 2: WAREHOUSE SPLIT
# ==========================================
elif option == "Problem 2: Warehouse Split":
    st.header("Warehouse Split Loss Analyzer")
    st.write("Find orders where items are split across multiple warehouses causing double shipping fees.")

    with st.expander("How does Warehouse Split Loss work? (Click to understand)"):
        st.markdown(
            "### The Problem\n"
            "Brands with multiple warehouses (e.g., Lahore + Karachi) face double shipping "
            "when one customer order has items in two warehouses.\n\n"
            "### The Loss\n"
            "- Customer order value: " + CURRENCY + " 3,000\n"
            "- Profit margin (15%): " + CURRENCY + " 450\n"
            "- Shipping cost per parcel: " + CURRENCY + " 250\n"
            "- Extra parcel cost: " + CURRENCY + " 250\n"
            "- Actual Profit: " + CURRENCY + " 450 - 500 = -50 (LOSS)\n\n"
            "### The Solution\n"
            "This tool shows:\n"
            "1. Which orders were split (warehouse-wise)\n"
            "2. Total extra shipping cost\n"
            "3. Product pairs often ordered together"
        )

    st.info("New here? Download sample file to see the format.")
    st.markdown("[Download Sample Warehouse Inventory CSV](" + GITHUB_RAW + "/sample_warehouse_inventory.csv)")
    st.markdown("---")

    inv_file = st.file_uploader("Upload Orders + Inventory CSV", type=['csv', 'xlsx', 'xls'], key='inv_m2')
    if inv_file:
        track("file_upload", "P2_inventory: " + inv_file.name)

    with st.expander("Settings"):
        c1, c2, c3 = st.columns(3)
        with c1:
            shipping_cost = st.number_input("Shipping Cost per Parcel (" + CURRENCY + ")", value=float(D_SHIP), min_value=0.01)
        with c2:
            avg_profit_margin = st.slider("Average Profit Margin (%)", 5, 50, 15)
        with c3:
            avg_order_value = st.number_input("Average Order Value (" + CURRENCY + ")", value=float(D_AOV), min_value=1.0)

    if st.button("Analyze Warehouse Splits", type='primary'):
        track("run_analysis", "P2_warehouse_split")
        if not inv_file:
            st.error("Please upload a file first.")
        else:
            try:
                with st.spinner("Analyzing warehouse splits..."):
                    df = read_file(inv_file)
                    order_col = find_col(df, ['Order ID', 'OrderId', 'order_id', 'Name'], True, 'Order ID')
                    sku_col = find_col(df, ['SKU', 'Sku', 'sku', 'Product', 'Product Name', 'Title'], True, 'SKU')
                    loc_col = find_col(df, ['Location', 'Warehouse', 'location', 'warehouse'], True, 'Location')

                    df[order_col] = df[order_col].astype(str).str.strip().str.upper()
                    df[loc_col] = df[loc_col].astype(str).str.strip()

                    grouped = df.groupby(order_col).agg({
                        loc_col: ['nunique', lambda x: list(set(x))],
                        sku_col: lambda x: list(x),
                    }).reset_index()
                    grouped.columns = ['Order ID', 'Unique Locations', 'Location List', 'Items']

                    split_orders = grouped[grouped['Unique Locations'] > 1].copy().sort_values('Unique Locations', ascending=False)

                    total_orders = len(grouped)
                    split_count = len(split_orders)
                    extra_parcels = split_orders['Unique Locations'].apply(lambda x: x - 1).sum() if split_count > 0 else 0
                    total_extra_shipping = extra_parcels * shipping_cost

                    split_orders['Extra Parcels'] = split_orders['Unique Locations'] - 1
                    split_orders['Extra Shipping'] = split_orders['Extra Parcels'] * shipping_cost
                    split_orders['Est. Profit'] = avg_order_value * (avg_profit_margin / 100)
                    split_orders['Net Profit'] = split_orders['Est. Profit'] - (split_orders['Extra Parcels'] + 1) * shipping_cost
                    split_orders['Status'] = split_orders['Net Profit'].apply(lambda x: 'LOSS' if x < 0 else 'Thin Margin')

                    track("analysis_complete", "P2: " + str(total_orders) + " orders, " + str(split_count) + " split")

                    st.success("Analysis complete. " + str(total_orders) + " orders checked.")

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Orders", total_orders)
                    m2.metric("Split Orders", split_count)
                    m3.metric("Extra Parcels", int(extra_parcels))
                    m4.metric("Total Extra Shipping", fmt_money(total_extra_shipping))

                    if split_count > 0:
                        st.markdown("### Visual Analysis")
                        chart_col1, chart_col2 = st.columns(2)

                        with chart_col1:
                            loc_combos = split_orders['Location List'].apply(lambda x: ' + '.join(sorted(x))).value_counts().head(10).reset_index()
                            loc_combos.columns = ['Warehouse Combination', 'Orders']
                            fig1 = px.bar(loc_combos, x='Orders', y='Warehouse Combination', orientation='h',
                                          title='Top Warehouse Combinations Causing Splits',
                                          color='Orders', color_continuous_scale='Reds')
                            fig1.update_layout(showlegend=False, height=400)
                            st.plotly_chart(fig1, use_container_width=True)

                        with chart_col2:
                            top_split = split_orders.head(10).copy()
                            top_split['Order ID'] = top_split['Order ID'].astype(str)
                            fig2 = px.bar(top_split, x='Order ID', y='Extra Shipping',
                                          title='Top 10 Orders by Extra Shipping (' + CURRENCY + ')',
                                          color='Extra Shipping', color_continuous_scale='Oranges')
                            fig2.update_layout(showlegend=False, height=400)
                            st.plotly_chart(fig2, use_container_width=True)

                    st.markdown("### Split Orders Detail")
                    display_cols = ['Order ID', 'Unique Locations', 'Location List', 'Extra Parcels', 'Extra Shipping', 'Status']
                    display_df = split_orders[display_cols].head(50).copy()
                    display_df['Location List'] = display_df['Location List'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
                    display_df.columns = ['Order ID', 'Unique Locations', 'Location List', 'Extra Parcels', 'Extra Shipping (' + CURRENCY + ')', 'Status']
                    st.dataframe(display_df, use_container_width=True)

                    st.markdown("### Smart Recommendation: Products Frequently Split Together")

                    multi_item = grouped[grouped['Items'].apply(lambda x: len(x) > 1 if isinstance(x, list) else False)].copy()

                    from collections import Counter
                    pair_counter = Counter()

                    for _, row in multi_item.iterrows():
                        items = row['Items']
                        locations = row['Location List']
                        if not isinstance(items, list) or len(items) < 2:
                            continue
                        if not isinstance(locations, list) or len(locations) < 2:
                            continue
                        unique_items = sorted(set(items))
                        for i in range(len(unique_items)):
                            for j in range(i + 1, len(unique_items)):
                                pair_counter[(unique_items[i], unique_items[j])] += 1

                    pairs_df = None
                    if pair_counter:
                        pair_data = []
                        for (a, b), count in pair_counter.most_common(15):
                            pair_data.append({
                                'Product A': a,
                                'Product B': b,
                                'Times Split Together': count,
                                'Est. Extra Cost (' + CURRENCY + ')': round(count * shipping_cost, 2),
                                'Recommendation': 'Move to same warehouse'
                            })
                        pairs_df = pd.DataFrame(pair_data)
                        st.dataframe(pairs_df, use_container_width=True)

                        st.success("Recommendation: Place top " + str(len(pairs_df)) + " product pairs in the same warehouse.")
                    else:
                        st.info("No frequently-split product pairs found. This is good news!")

                    st.markdown("### Warehouse Load Distribution")
                    warehouse_load = df.groupby(loc_col)[order_col].nunique().reset_index()
                    warehouse_load.columns = ['Warehouse', 'Orders']
                    warehouse_load = warehouse_load.sort_values('Orders', ascending=False)

                    fig3 = px.pie(warehouse_load, values='Orders', names='Warehouse',
                                  title='Order Distribution by Warehouse',
                                  color_discrete_sequence=px.colors.sequential.Viridis)
                    fig3.update_layout(height=400)
                    st.plotly_chart(fig3, use_container_width=True)

                    st.markdown("---")
                    d1, d2 = st.columns(2)
                    with d1:
                        if st.download_button(
                            label="Download Split Orders (CSV)",
                            data=csv_bytes(split_orders),
                            file_name=PLATFORM_NAME + "_split_orders_report.csv",
                            mime="text/csv",
                            use_container_width=True
                        ):
                            track("download", "P2_split_orders_CSV")
                    with d2:
                        if pairs_df is not None:
                            if st.download_button(
                                label="Download Product Pairing (CSV)",
                                data=csv_bytes(pairs_df),
                                file_name=PLATFORM_NAME + "_product_pairing.csv",
                                mime="text/csv",
                                use_container_width=True
                            ):
                                track("download", "P2_product_pairing_CSV")

                    st.markdown("### Business Impact Summary")
                    annual_extra = total_extra_shipping * 12

                    i1, i2 = st.columns(2)
                    with i1:
                        st.markdown("**Monthly Extra Shipping Cost:** " + fmt_money(total_extra_shipping))
                    with i2:
                        st.markdown("**Annual Extra Shipping Cost:** " + fmt_money(annual_extra))

                    st.warning("Action: You can save " + fmt_money(annual_extra) + " annually by moving top product pairs to the same warehouse.")

            except Exception as e:
                st.error("Error: " + str(e))
                st.exception(e)
                track("error", "P2: " + str(e)[:150])

# ==========================================
# PROBLEM 3: BAD CUSTOMERS
# ==========================================
elif option == "Problem 3: Bad Customers":
    st.header("Bad Customers / High-Return Buyer Detector")
    st.write("Identify customers with high RTO rates and suspicious addresses to prevent future losses.")

    with st.expander("How does Bad Customer Loss work? (Click to understand)"):
        st.markdown(
            "### The Problem\n"
            "Some customers (or competitors) place fake orders and reject parcels on delivery (RTO).\n"
            "This wastes ad budget, double shipping, packaging cost, and blocks inventory.\n\n"
            "### The Loss Calculation\n"
            "- Ad cost per order: " + CURRENCY + " 300\n"
            "- Forward shipping: " + CURRENCY + " 250\n"
            "- Return shipping: " + CURRENCY + " 250\n"
            "- Packaging: " + CURRENCY + " 50\n"
            "- Total loss per RTO: " + CURRENCY + " 850\n\n"
            "### The Solution\n"
            "This tool gives you:\n"
            "1. Blacklist - Customers with return rate above 50%\n"
            "2. Watchlist - Customers with return rate 30-50%\n"
            "3. Risk Score - 0-100 score per customer\n"
            "4. Suspicious Addresses - Fake or incomplete addresses\n"
            "5. Recommended Actions - Block COD, verify address"
        )

    st.info("New here? Download sample file to see the format.")
    st.markdown("[Download Sample Customer Orders CSV](" + GITHUB_RAW + "/sample_customer_orders.csv)")
    st.markdown("---")

    cust_file = st.file_uploader("Upload Customer Orders CSV", type=['csv', 'xlsx', 'xls'], key='cust_m3')
    if cust_file:
        track("file_upload", "P3_customers: " + cust_file.name)

    with st.expander("Settings"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            return_threshold = st.slider("Blacklist Threshold (%)", 20, 90, 50)
        with c2:
            watchlist_threshold = st.slider("Watchlist Threshold (%)", 10, 50, 30)
        with c3:
            min_orders = st.number_input("Min Orders to consider", value=2, min_value=1)
        with c4:
            rto_cost = st.number_input("Cost per RTO (" + CURRENCY + ")", value=float(D_RTO), min_value=1.0)
        short_addr_len = st.number_input("Short address length (chars)", value=15, min_value=5)

    if st.button("Detect Bad Customers", type='primary'):
        track("run_analysis", "P3_bad_customers")
        if not cust_file:
            st.error("Please upload a file first.")
        else:
            try:
                with st.spinner("Analyzing customers..."):
                    df = read_file(cust_file)

                    order_col = find_col(df, ['Order ID', 'OrderId', 'Name', 'Order Number'], True, 'Order ID')
                    phone_col = find_col(df, ['Phone', 'phone', 'Mobile', 'Contact'], False)
                    email_col = find_col(df, ['Email', 'email', 'Customer Email'], False)
                    addr_col = find_col(df, ['Address', 'address', 'Shipping Address'], False)
                    return_col = find_col(df, ['Return', 'Returned', 'RTO', 'Status', 'Refund', 'Order Status'], False)

                    identifier = phone_col if phone_col else email_col
                    if not identifier:
                        st.error("Phone or Email column not found.")
                        st.stop()

                    if return_col:
                        df['_is_return'] = df[return_col].astype(str).str.lower().str.strip().isin(
                            ['true', 'yes', '1', 'returned', 'rto', 'refunded', 'return', 'cancelled', 'canceled'])
                    else:
                        st.warning("No Return/RTO column found. Assuming all orders are successful.")
                        df['_is_return'] = False

                    customer_stats = df.groupby(identifier).agg({
                        order_col: 'count',
                        '_is_return': 'sum'
                    }).reset_index()
                    customer_stats.columns = ['Customer', 'Total Orders', 'Returns']
                    customer_stats['Successful Orders'] = customer_stats['Total Orders'] - customer_stats['Returns']
                    customer_stats['Return Rate %'] = (customer_stats['Returns'] / customer_stats['Total Orders'] * 100).round(1)
                    customer_stats['Loss'] = customer_stats['Returns'] * rto_cost

                    def calculate_risk(row):
                        rate = row['Return Rate %']
                        orders = row['Total Orders']
                        rate_score = min(rate, 100)
                        freq_score = min(orders * 10, 100)
                        return round(rate_score * 0.7 + freq_score * 0.3, 1)

                    customer_stats['Risk Score'] = customer_stats.apply(calculate_risk, axis=1)

                    def segment(row):
                        if row['Total Orders'] < min_orders:
                            return 'New/Low Volume'
                        if row['Return Rate %'] >= return_threshold:
                            return 'BLACKLIST'
                        elif row['Return Rate %'] >= watchlist_threshold:
                            return 'Watchlist'
                        elif row['Return Rate %'] < 20 and row['Total Orders'] >= 5:
                            return 'VIP'
                        else:
                            return 'Regular'

                    customer_stats['Segment'] = customer_stats.apply(segment, axis=1)
                    customer_stats = customer_stats.sort_values('Risk Score', ascending=False)

                    blacklist = customer_stats[customer_stats['Segment'] == 'BLACKLIST'].copy()
                    watchlist = customer_stats[customer_stats['Segment'] == 'Watchlist'].copy()
                    vip = customer_stats[customer_stats['Segment'] == 'VIP'].copy()

                    total_customers = len(customer_stats)
                    total_rto_loss = customer_stats['Loss'].sum()
                    potential_savings = total_rto_loss * 0.6

                    track("analysis_complete", "P3: " + str(total_customers) + " customers, " + str(len(blacklist)) + " blacklist")

                    st.success("Analysis complete. " + str(total_customers) + " unique customers analyzed.")

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Customers", total_customers)
                    m2.metric("Blacklisted", len(blacklist))
                    m3.metric("Watchlist", len(watchlist))
                    m4.metric("Total RTO Loss", fmt_money(total_rto_loss))

                    st.markdown("### Visual Analysis")
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        top_risk = customer_stats.head(10).copy()
                        top_risk['Customer Short'] = top_risk['Customer'].astype(str).str[-10:]
                        fig1 = px.bar(top_risk, x='Customer Short', y='Risk Score',
                                      title='Top 10 High-Risk Customers',
                                      color='Risk Score', color_continuous_scale='Reds')
                        fig1.update_layout(showlegend=False, height=400)
                        st.plotly_chart(fig1, use_container_width=True)

                    with chart_col2:
                        seg_dist = customer_stats['Segment'].value_counts().reset_index()
                        seg_dist.columns = ['Segment', 'Count']
                        fig2 = px.pie(seg_dist, values='Count', names='Segment',
                                      title='Customer Segmentation')
                        fig2.update_layout(height=400)
                        st.plotly_chart(fig2, use_container_width=True)

                    st.markdown("---")
                    st.markdown("### Blacklist - Block COD for These Customers")
                    if len(blacklist) > 0:
                        st.error(str(len(blacklist)) + " customers identified with high RTO rate. Total loss: " + fmt_money(blacklist['Loss'].sum()))
                        display_bl = blacklist[['Customer', 'Total Orders', 'Returns', 'Return Rate %', 'Risk Score', 'Loss']].head(50).copy()
                        display_bl.columns = ['Customer', 'Total Orders', 'Returns', 'Return Rate %', 'Risk Score', 'Loss (' + CURRENCY + ')']
                        st.dataframe(display_bl, use_container_width=True)

                        st.markdown("**Recommended Actions:**")
                        st.markdown(
                            "- Block COD (Cash on Delivery) for these customers\n"
                            "- Require advance payment before shipping\n"
                            "- Add to your store's fraud prevention list\n"
                            "- Tag them as BLACKLIST for future reference"
                        )
                    else:
                        st.success("No customers found in blacklist. Great!")

                    if len(watchlist) > 0:
                        st.markdown("---")
                        st.markdown("### Watchlist - Monitor These Customers")
                        st.warning(str(len(watchlist)) + " customers need monitoring. Total loss: " + fmt_money(watchlist['Loss'].sum()))
                        display_wl = watchlist[['Customer', 'Total Orders', 'Returns', 'Return Rate %', 'Risk Score', 'Loss']].head(50).copy()
                        display_wl.columns = ['Customer', 'Total Orders', 'Returns', 'Return Rate %', 'Risk Score', 'Loss (' + CURRENCY + ')']
                        st.dataframe(display_wl, use_container_width=True)

                    if len(vip) > 0:
                        st.markdown("---")
                        st.markdown("### VIP Customers - Offer Loyalty Rewards")
                        st.success(str(len(vip)) + " VIP customers identified. Keep them happy!")
                        display_vip = vip[['Customer', 'Total Orders', 'Returns', 'Return Rate %']].head(20).copy()
                        st.dataframe(display_vip, use_container_width=True)

                    if addr_col:
                        st.markdown("---")
                        st.markdown("### Suspicious Addresses - Verify Before Shipping")

                        df['_addr'] = df[addr_col].astype(str)
                        df['_addr_len'] = df['_addr'].str.len()
                        df['_has_digit'] = df['_addr'].str.contains(r'\d', na=False)
                        df['_generic'] = df['_addr'].str.lower().str.contains(
                            r'near|main market|chowk|gali|street|road|adjacent|opposite|beside',
                            na=False, regex=True
                        )

                        df['_flag_short'] = df['_addr_len'] < short_addr_len
                        df['_flag_no_digit'] = ~df['_has_digit']
                        df['_flag_generic'] = df['_generic']
                        df['_flag_count'] = df['_flag_short'].astype(int) + df['_flag_no_digit'].astype(int) + df['_flag_generic'].astype(int)
                        df['_is_suspicious'] = df['_flag_count'] >= 1

                        suspicious = df[df['_is_suspicious']].copy()

                        if len(suspicious) > 0:
                            st.warning(str(len(suspicious)) + " orders have suspicious addresses.")
                            display_suspicious = suspicious[[order_col, identifier, addr_col, '_flag_count']].drop_duplicates(subset=[order_col]).head(50)
                            display_suspicious.columns = ['Order ID', 'Customer', 'Address', 'Risk Flags']
                            st.dataframe(display_suspicious, use_container_width=True)

                            st.markdown("**Address Flags Explained:**")
                            st.markdown(
                                "- 1 flag = Low risk (verify via phone)\n"
                                "- 2 flags = Medium risk (call and confirm)\n"
                                "- 3 flags = High risk (do NOT ship COD)"
                            )
                        else:
                            st.success("No suspicious addresses found. All addresses look good!")

                    st.markdown("---")
                    st.markdown("### Business Impact Summary")

                    i1, i2, i3 = st.columns(3)
                    i1.metric("Monthly RTO Loss", fmt_money(total_rto_loss))
                    i2.metric("Annual RTO Loss", fmt_money(total_rto_loss * 12))
                    i3.metric("Savings if 60% Blocked", fmt_money(potential_savings * 12))

                    st.warning("Action Required: You can save " + fmt_money(potential_savings * 12) + " annually by blocking " + str(len(blacklist)) + " blacklisted customers from COD.")

                    st.markdown("---")
                    st.markdown("### Downloads")
                    d1, d2, d3 = st.columns(3)

                    with d1:
                        if st.download_button(
                            label="Download Blacklist (CSV)",
                            data=csv_bytes(blacklist),
                            file_name=PLATFORM_NAME + "_blacklist.csv",
                            mime="text/csv",
                            use_container_width=True
                        ):
                            track("download", "P3_blacklist_CSV")
                    with d2:
                        if st.download_button(
                            label="Download Watchlist (CSV)",
                            data=csv_bytes(watchlist),
                            file_name=PLATFORM_NAME + "_watchlist.csv",
                            mime="text/csv",
                            use_container_width=True
                        ):
                            track("download", "P3_watchlist_CSV")
                    with d3:
                        if st.download_button(
                            label="Download Full Report (CSV)",
                            data=csv_bytes(customer_stats),
                            file_name=PLATFORM_NAME + "_customer_analysis.csv",
                            mime="text/csv",
                            use_container_width=True
                        ):
                            track("download", "P3_customer_full_CSV")
            except Exception as e:
                st.error("Error: " + str(e))
                st.exception(e)
                track("error", "P3: " + str(e)[:150])

# ==========================================
# EMAIL TEMPLATE
# ==========================================
elif option == "Email Template":
    st.header("Refund Claim Email Generator")
    st.write("Generate a professional email to send to your courier company for refund claim.")

    st.markdown("### Fill in the details:")

    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("Your Company Name", value="Your Store Name")
        courier_name = st.text_input("Courier Company", value="Trax / Leopards / TCS")
        contact_person = st.text_input("Courier Contact Person", value="Accounts Manager")
    with col2:
        total_refund = st.number_input("Total Refund Amount (" + CURRENCY + ")", value=50000 if CURRENCY == "PKR" else 180, min_value=0)
        order_count = st.number_input("Number of Overcharged Orders", value=50, min_value=1)
        month = st.text_input("Billing Month", value="October 2024")

    if st.button("Generate Email", type='primary'):
        track("generate_email", "courier: " + courier_name)
        email_template = (
            "Subject: Refund Claim - Courier Overcharge on Volumetric Weight Billing - " + month + "\n\n"
            "Dear " + contact_person + ",\n\n"
            "I hope this message finds you well. I am writing on behalf of " + company_name + " regarding the courier billing for " + month + ".\n\n"
            "After a detailed audit of our courier bills against actual shipment weights, we have identified " + str(order_count) + " orders where we were overcharged due to volumetric weight billing discrepancies.\n\n"
            "The total overcharge amount is " + CURRENCY + " " + f"{total_refund:,}" + ". A detailed report with order-wise breakdown is attached for your review.\n\n"
            "We request you to:\n"
            "1. Review the attached report and verify the discrepancies.\n"
            "2. Process a refund of " + CURRENCY + " " + f"{total_refund:,}" + " to our account.\n"
            "3. Adjust future billing to reflect actual weights where applicable.\n\n"
            "We value our partnership with " + courier_name + " and trust that this matter will be resolved promptly.\n\n"
            "Kindly acknowledge this email and share a resolution timeline.\n\n"
            "Best regards,\n"
            + YOUR_NAME + "\n"
            + company_name + "\n"
            "WhatsApp: " + YOUR_WHATSAPP + "\n"
            "Email: " + YOUR_EMAIL + "\n"
        )
        st.markdown("### Your Email Template")
        st.text_area("Copy this email:", email_template, height=400)
        st.info("Tip: Attach the PDF report (from Problem 1) with this email.")

        if st.download_button(
            label="Download as Text File",
            data=email_template.encode('utf-8'),
            file_name="refund_claim_email_" + courier_name.replace(' ', '_') + ".txt",
            mime="text/plain"
        ):
            track("download", "email_template_TXT")

# ==========================================
# HELP & CLIENT GUIDE
# ==========================================
elif option == "Help & Client Guide":
    st.header("Help & Client Guide")

    show_video_hero()

    st.write("Download this guide as PDF and send it to your client via WhatsApp or Email.")

    if st.button("Download Help Guide (PDF)", type='primary'):
        track("download_help_guide", "pdf")
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(29, 185, 84)
            pdf.cell(0, 15, PLATFORM_NAME + " Profit Guard", ln=True, align="C")
            pdf.set_font("Helvetica", "I", 13)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 10, "Client Help Guide", ln=True, align="C")
            pdf.ln(3)
            pdf.set_draw_color(29, 185, 84)
            pdf.set_line_width(0.8)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(8)

            def title(text):
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(25, 20, 20)
                pdf.cell(0, 10, text, ln=True)
                pdf.ln(1)

            def body(text):
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 6, text)
                pdf.ln(3)

            title("1. What is Profit Guard?")
            body("Profit Guard is a professional tool built for " + PLATFORM_NAME + " stores. It solves 3 major problems:\n\n"
                 "   - Courier Volumetric Weight Fraud (extra charges)\n"
                 "   - Multi-Warehouse Order Splitting (double shipping)\n"
                 "   - High-Return Customers and Bad Addresses (RTO losses)")

            title("2. Video Guide")
            body("Watch the complete video tutorial here:\n" + YOUTUBE_VIDEO)

            title("3. How to Export Data")
            body("Export data from your " + PLATFORM_NAME + " store:\n\n"
                 "For Shopify: Admin > Orders > Export > CSV\n"
                 "For WooCommerce: Orders > Export > CSV\n"
                 "For Daraz: Seller Center > Orders > Export")

            title("4. How to Get Courier Billing Data")
            body("Login to your courier portal:\n\n"
                 "   - Trax: trax.pk\n"
                 "   - Leopards: leopardscourier.com\n"
                 "   - TCS: tcsexpress.com\n"
                 "   - PostEx: merchant.postex.pk")

            title("5. How to Use the Tool")
            body("Step 1: Open the tool in your browser.\n"
                 "Step 2: Select the problem from the left menu.\n"
                 "Step 3: Download the sample file to see the format.\n"
                 "Step 4: Upload your CSV files.\n"
                 "Step 5: Click Run.\n"
                 "Step 6: Download the PDF report.\n"
                 "Step 7: Send it to your courier for refund.")

            title("6. Data Privacy")
            body("Your data is never uploaded to any server. Everything is processed on your own computer.")

            title("7. Contact")
            body("Name: " + YOUR_NAME + "\nWhatsApp: " + YOUR_WHATSAPP + "\nEmail: " + YOUR_EMAIL + "\nVideo: " + YOUTUBE_VIDEO)

            pdf.ln(10)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 10, PLATFORM_NAME + " Profit Guard v1.0 | Currency: " + CURRENCY, ln=True, align="C")

            pdf_bytes = bytes(pdf.output())
            st.download_button(
                label="Save PDF",
                data=pdf_bytes,
                file_name=PLATFORM_NAME + "_Profit_Guard_Help_Guide.pdf",
                mime="application/pdf"
            )
            st.success("PDF is ready. Click above to download.")
        except Exception as e:
            st.error("PDF error: " + str(e))

# ==========================================
# ADMIN (PRIVATE) - With Google Authenticator 2FA
# ==========================================
elif option == "Admin (Private)":
    st.header("Admin Panel - 2FA Protected")

    try:
        correct_pass = st.secrets["admin"]["password"]
        totp_secret = st.secrets["admin"]["totp_secret"]
    except Exception:
        correct_pass = "changeme"
        totp_secret = None

    if totp_secret is None or totp_secret == "":
        st.warning("TOTP secret not configured in secrets.toml")
        st.info("PowerShell me chalao: python -c \"import pyotp; print(pyotp.random_base32())\"")
    else:
        tab1, tab2 = st.tabs(["Login", "Setup Google Authenticator"])

        with tab1:
            st.markdown("### Enter Credentials")

            if st.session_state.get("admin_logged_in"):
                st.success("You are logged in as Admin")

                if st.button("Logout"):
                    st.session_state.admin_logged_in = False
                    track("admin_logout", "")
                    st.rerun()

                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("Session ID", SESSION_ID)
                c2.metric("First Seen", st.session_state.first_seen)
                c3.metric("Platform", PLATFORM_NAME)

                st.markdown("### Live Tracking Info")
                st.info("Session: " + SESSION_ID + " | Platform: " + PLATFORM_NAME + " | Currency: " + CURRENCY)

                st.markdown("### GA4 Events Tracked")
                st.markdown(
                    "- app_open\n"
                    "- section_view\n"
                    "- currency_change\n"
                    "- platform_change\n"
                    "- file_upload\n"
                    "- run_analysis\n"
                    "- analysis_complete\n"
                    "- download\n"
                    "- generate_email\n"
                    "- download_help_guide\n"
                    "- error\n"
                    "- admin_login_success\n"
                    "- admin_login_fail\n"
                    "- admin_logout"
                )

                st.markdown("### Google Sheet Logging")
                st.write("Complete user activity is stored in your Google Sheet (via webhook_url in secrets).")
                st.write("Setup: Sheet banao, Apps Script me doPost function add karo, Deploy as Web App, URL secrets.toml me daalo.")

                st.markdown("---")
                st.markdown("### User Activity Logs (Live)")
                
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if st.button("Refresh Logs", use_container_width=True):
                        st.session_state.logs_loaded = True
                        st.rerun()
                with col_b:
                    st.caption("Google Sheet se latest data fetch karta hai")
                
                if st.session_state.get("logs_loaded"):
                    with st.spinner("Fetching logs from Google Sheet..."):
                        logs_df = fetch_user_logs()
                    
                    if logs_df is None or len(logs_df) == 0:
                        st.warning("No logs found. Webhook URL check karo.")
                    else:
                        st.success("Total " + str(len(logs_df)) + " events loaded")
                        
                        f1, f2, f3 = st.columns(3)
                        with f1:
                            actions = ["All"] + sorted(logs_df["action"].unique().tolist()) if "action" in logs_df.columns else ["All"]
                            filter_action = st.selectbox("Filter by Action", actions)
                        with f2:
                            sessions = ["All"] + sorted(logs_df["session_id"].unique().tolist()) if "session_id" in logs_df.columns else ["All"]
                            filter_session = st.selectbox("Filter by Session", sessions)
                        with f3:
                            limit = st.number_input("Show last N rows", value=100, min_value=10, max_value=5000, step=50)
                        
                        logs_df["_dt"] = pd.to_datetime(logs_df["timestamp"], errors="coerce")
                        logs_df["_date"] = logs_df["_dt"].dt.date
                        
                        st.markdown("#### Date Filter")
                        d1, d2, d3 = st.columns(3)
                        with d1:
                            date_preset = st.selectbox(
                                "Quick Range",
                                ["All Time", "Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Custom Range"]
                            )
                        with d2:
                            unique_dates = sorted([d for d in logs_df["_date"].dropna().unique()], reverse=True)
                            if len(unique_dates) > 0:
                                date_start = st.date_input("From", value=unique_dates[-1])
                            else:
                                date_start = st.date_input("From")
                        with d3:
                            if len(unique_dates) > 0:
                                date_end = st.date_input("To", value=unique_dates[0])
                            else:
                                date_end = st.date_input("To")
                        
                        today = pd.Timestamp.now().date()
                        if date_preset == "Today":
                            date_start = today
                            date_end = today
                        elif date_preset == "Yesterday":
                            date_start = today - pd.Timedelta(days=1)
                            date_end = today - pd.Timedelta(days=1)
                        elif date_preset == "Last 7 Days":
                            date_start = today - pd.Timedelta(days=7)
                            date_end = today
                        elif date_preset == "Last 30 Days":
                            date_start = today - pd.Timedelta(days=30)
                            date_end = today
                        filtered = logs_df.copy()
                        
                        if date_preset != "All Time":
                            filtered = filtered[
                                (filtered["_date"] >= date_start) & 
                                (filtered["_date"] <= date_end)
                            ]
                        if filter_action != "All" and "action" in filtered.columns:
                            filtered = filtered[filtered["action"] == filter_action]
                        if filter_session != "All" and "session_id" in filtered.columns:
                            filtered = filtered[filtered["session_id"] == filter_session]
                        
                        filtered = filtered.tail(int(limit))
                        
                        m1, m2, m3, m4 = st.columns(4)
                        if "session_id" in logs_df.columns:
                            m1.metric("Total Users", logs_df["session_id"].nunique())
                        if "action" in logs_df.columns:
                            m2.metric("Total Events", len(logs_df))
                            m3.metric("Unique Actions", logs_df["action"].nunique())
                        if "timestamp" in logs_df.columns:
                            m4.metric("Latest", str(logs_df["timestamp"].iloc[-1])[:16])
                        
                        st.markdown("---")
                        st.dataframe(filtered, use_container_width=True, height=400)
                        
                        st.markdown("### Per-User Summary")
                        if "session_id" in logs_df.columns and "action" in logs_df.columns:
                            session_summary = logs_df.groupby("session_id").agg({
                                "action": "count",
                                "timestamp": ["min", "max"]
                            }).reset_index()
                            session_summary.columns = ["Session ID", "Total Events", "First Seen", "Last Seen"]
                            session_summary = session_summary.sort_values("Last Seen", ascending=False)
                            st.dataframe(session_summary, use_container_width=True)
                        
                        if st.download_button(
                            "Download Full Logs (CSV)",
                            data=filtered.to_csv(index=False).encode('utf-8'),
                            file_name="profit_guard_user_logs.csv",
                            mime="text/csv"
                        ):
                            pass
                else:
                    st.info("Click Refresh Logs to load user activity from Google Sheet.")
                
                st.markdown("---")
                st.markdown("### Help Video")
                st.video(YOUTUBE_VIDEO)

            else:
                col1, col2 = st.columns(2)
                with col1:
                    admin_pass = st.text_input("Admin Password:", type="password", key="admin_pwd")
                with col2:
                    totp_code = st.text_input("6-Digit Code from Google Authenticator:", max_chars=6, key="totp_input")

                if st.button("Login", type="primary", use_container_width=True):
                    if admin_pass != correct_pass:
                        st.error("Wrong password")
                        track("admin_login_fail", "wrong_password")
                    elif len(totp_code) != 6 or not totp_code.isdigit():
                        st.error("Please enter 6-digit code")
                    else:
                        totp = pyotp.TOTP(totp_secret)
                        if totp.verify(totp_code, valid_window=1):
                            st.session_state.admin_logged_in = True
                            st.success("Login successful!")
                            track("admin_login_success", "with_2FA")
                            st.rerun()
                        else:
                            st.error("Invalid or expired code. Try again.")
                            track("admin_login_fail", "wrong_totp")

        with tab2:
            st.markdown("### Setup Google Authenticator")
            st.write("Phone pe Google Authenticator app kholo, + dabao, 'Scan QR code' select karo.")

            st.markdown(
                "**Step 1:** Play Store / App Store se Google Authenticator download karo\n\n"
                "**Step 2:** App kholo, + button dabao, 'Scan a QR code' select karo\n\n"
                "**Step 3:** Neeche wala QR code scan karo\n\n"
                "**Step 4:** App me 6-digit code aayega - wahi login me use karo"
            )

            try:
                totp = pyotp.TOTP(totp_secret)
                uri = totp.provisioning_uri(
                    name=YOUR_EMAIL,
                    issuer_name="Profit Guard Admin"
                )

                qr = qrcode.QRCode(version=1, box_size=10, border=2)
                qr.add_data(uri)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")

                buf = io.BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)

                col1, col2 = st.columns([1, 1])
                with col1:
                    st.image(buf, caption="Scan this QR with Google Authenticator", width=280)
                with col2:
                    st.markdown("### Manual Entry Code")
                    st.code(totp_secret, language=None)
                    st.caption("Agar QR scan nahi ho raha to ye code manually Google Authenticator me daalo.")

                st.markdown("---")
                st.markdown("### Test: Current Valid Code")
                st.info("Ye code right now valid hai (har 30 second me change hota hai):")
                current = totp.now()
                st.markdown(
                    "<div style='background:#1DB954; padding:20px; border-radius:10px; text-align:center;'>"
                    "<div style='color:white; font-size:12px; letter-spacing:2px;'>CURRENT CODE</div>"
                    "<div style='color:white; font-size:48px; font-weight:bold; letter-spacing:8px; font-family:monospace;'>" + current + "</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
                st.caption("Agar Google Authenticator me bhi yahi code aa raha hai to setup sahi hai")

            except Exception as e:
                st.error("QR generation error: " + str(e))

# ==========================================
# ABOUT
# ==========================================
else:
    st.header("About Profit Guard")
    st.markdown(
        "### What This Tool Does\n"
        "1. **Courier Fraud Detector** - Finds orders where courier overcharged you\n"
        "2. **Warehouse Split Analyzer** - Finds orders split across warehouses\n"
        "3. **Bad Customer Blacklist** - Finds high-return customers\n\n"
        "### Supported Platforms\n"
        "Shopify, WooCommerce, Daraz, Magento, BigCommerce, Amazon, and 20+ more\n\n"
        "### Supported Currencies\n"
        "PKR, USD, AED, SAR, GBP, EUR\n\n"
        "### Features\n"
        "- Platform selector (reports adapt to your platform)\n"
        "- Currency selector (reports adapt to your currency)\n"
        "- Sample files for easy setup\n"
        "- Visual charts with Plotly\n"
        "- Professional PDF reports\n"
        "- Email template generator\n"
        "- Help video tutorial\n"
        "- 100% privacy - data stays on your computer\n"
        "- 2FA protected admin panel\n\n"
        "### Contact\n"
        "**Name:** " + YOUR_NAME + "\n"
        "**WhatsApp:** " + YOUR_WHATSAPP + "\n"
        "**Email:** " + YOUR_EMAIL + "\n"
        "**Video Tutorial:** [Watch Here](" + YOUTUBE_VIDEO + ")"
    )

    st.markdown("### Watch Tutorial")
    st.video(YOUTUBE_VIDEO)

    show_support()