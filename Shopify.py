# ==========================================
# COURIER VOLUMETRIC WEIGHT FRAUD DETECTOR
# ==========================================
import pandas as pd
import numpy as np

# ---------------- CONFIG ----------------
SHOPIFY_FILE = 'shopify_orders.csv'
COURIER_FILE = 'courier_billing.csv'

SHOPIFY_IS_LINE_ITEM = True      # agar Shopify file mein har row product line hai to True
SHOPIFY_WEIGHT_UNIT = 'g'        # 'g' ya 'kg'
COURIER_WEIGHT_UNIT = 'kg'       # 'g' ya 'kg'

VOLUMETRIC_DIVISOR = 5000        # cm/kg ke liye 5000. Inches/lb ke liye 139
TOLERANCE_KG = 0.05              # 50 gram tolerance
PACKAGING_WEIGHT_KG = 0.0        # packing weight add karna ho to yahan likho
RATE_PER_KG = None               # e.g. 150. None rakho to courier Amount/Billed Weight se rate nikalega
OUTPUT_FILE = 'courier_overcharge_report.csv'

# ---------------- HELPERS ----------------
def read_any(path):
    if path.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(path)
    for enc in ['utf-8', 'utf-8-sig', 'latin1']:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path)

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
        raise ValueError(f"{label} nahi mila. Available columns: {list(df.columns)}")
    return None

def clean_order_id(series):
    return (series.astype(str)
            .str.strip()
            .str.replace(r'\.0$', '', regex=True)
            .str.replace('#', '', regex=False)
            .str.upper())

def to_kg(series, unit):
    x = pd.to_numeric(series, errors='coerce')
    if str(unit).lower() == 'g':
        x = x / 1000.0
    return x

# ---------------- LOAD DATA ----------------
shopify = read_any(SHOPIFY_FILE)
courier = read_any(COURIER_FILE)

# ---------------- COLUMN ALIASES ----------------
shop_order_aliases = ['Order ID', 'OrderId', 'order_id', 'Name', 'Order Number', 'order_number', 'id']
shop_weight_aliases = ['Weight', 'weight', 'Weight (g)', 'Weight (kg)', 'actual_weight', 'product_weight', 'grams', 'Total Weight']
shop_len_aliases = ['Length', 'length', 'Length (cm)', 'l', 'L']
shop_wid_aliases = ['Width', 'width', 'Width (cm)', 'w', 'W']
shop_hei_aliases = ['Height', 'height', 'Height (cm)', 'h', 'H']

courier_order_aliases = ['Order ID', 'OrderId', 'order_id', 'Order Number', 'Tracking ID', 'CN', 'Consignment', 'Reference', 'ref', 'order_number']
courier_billed_aliases = ['Billed Weight', 'billed_weight', 'Charged Weight', 'charged_weight', 'Chargeable Weight', 'weight', 'Weight', 'Weight (kg)', 'Billing Weight']
courier_amount_aliases = ['Amount', 'Charge', 'Courier Charges', 'Freight', 'Shipping Fee', 'Total', 'COD Amount', 'Billing Amount']

# ---------------- FIND COLUMNS ----------------
shop_order = find_col(shopify, shop_order_aliases, True, 'Shopify Order ID')
shop_weight = find_col(shopify, shop_weight_aliases, True, 'Shopify Weight')
shop_len = find_col(shopify, shop_len_aliases, False)
shop_wid = find_col(shopify, shop_wid_aliases, False)
shop_hei = find_col(shopify, shop_hei_aliases, False)

courier_order = find_col(courier, courier_order_aliases, True, 'Courier Order ID')
courier_billed = find_col(courier, courier_billed_aliases, True, 'Courier Billed Weight')
courier_amount = find_col(courier, courier_amount_aliases, False)

# ---------------- CLEAN IDS ----------------
shopify['_order_id'] = clean_order_id(shopify[shop_order])
courier['_order_id'] = clean_order_id(courier[courier_order])

# ---------------- WEIGHT ----------------
shopify['_weight_kg'] = to_kg(shopify[shop_weight], SHOPIFY_WEIGHT_UNIT)

# Dimensions numeric
for c in [shop_len, shop_wid, shop_hei]:
    if c:
        shopify[c + '_num'] = pd.to_numeric(shopify[c], errors='coerce')

# ---------------- AGGREGATE SHOPIFY ORDER LEVEL ----------------
if SHOPIFY_IS_LINE_ITEM:
    agg_dict = {'_weight_kg': 'sum'}
    if shop_len: agg_dict[shop_len + '_num'] = 'max'
    if shop_wid: agg_dict[shop_wid + '_num'] = 'max'
    if shop_hei: agg_dict[shop_hei + '_num'] = 'max'
    shopify_order = shopify.groupby('_order_id').agg(agg_dict).reset_index()
else:
    shopify_order = shopify.drop_duplicates('_order_id').copy()

if shop_len:
    shopify_order['_length'] = shopify_order[shop_len + '_num']
else:
    shopify_order['_length'] = np.nan

if shop_wid:
    shopify_order['_width'] = shopify_order[shop_wid + '_num']
else:
    shopify_order['_width'] = np.nan

if shop_hei:
    shopify_order['_height'] = shopify_order[shop_hei + '_num']
else:
    shopify_order['_height'] = np.nan

# ---------------- COURIER BILLED ----------------
courier['_billed_kg'] = to_kg(courier[courier_billed], COURIER_WEIGHT_UNIT)

if courier_amount:
    courier['_amount'] = pd.to_numeric(courier[courier_amount], errors='coerce')
else:
    courier['_amount'] = np.nan

courier_order_df = courier.groupby('_order_id').agg({
    '_billed_kg': 'sum',
    '_amount': 'sum'
}).reset_index()

# ---------------- MERGE ----------------
df = shopify_order.merge(courier_order_df, on='_order_id', how='inner')

# ---------------- CALCULATIONS ----------------
df['actual_weight_kg'] = df['_weight_kg'] + PACKAGING_WEIGHT_KG
df['volumetric_weight_kg'] = (df['_length'] * df['_width'] * df['_height']) / VOLUMETRIC_DIVISOR

df['expected_billable_kg'] = np.where(
    df['volumetric_weight_kg'].notna(),
    np.maximum(df['actual_weight_kg'], df['volumetric_weight_kg']),
    df['actual_weight_kg']
)

df['billed_weight_kg'] = df['_billed_kg']
df['overcharge_kg'] = df['billed_weight_kg'] - df['expected_billable_kg']
df['is_overcharged'] = df['overcharge_kg'] > TOLERANCE_KG

# Refund estimate
if RATE_PER_KG is not None:
    df['refund_estimate'] = df['overcharge_kg'].clip(lower=0) * RATE_PER_KG
else:
    df['_rate_used'] = np.where(
        df['billed_weight_kg'] > 0,
        df['_amount'] / df['billed_weight_kg'],
        np.nan
    )
    df['refund_estimate'] = df['overcharge_kg'].clip(lower=0) * df['_rate_used']

# ---------------- REPORT ----------------
report = df[df['is_overcharged']].copy()
report = report.sort_values('overcharge_kg', ascending=False)
report = report.rename(columns={'_order_id': 'Order ID'})
report.to_csv(OUTPUT_FILE, index=False)

print("Total matched orders:", len(df))
print("Overcharged orders:", len(report))
print("Total overcharge kg:", round(report['overcharge_kg'].sum(), 2))
print("Estimated refund:", round(report['refund_estimate'].sum(skipna=True), 2))
print("Report saved:", OUTPUT_FILE)