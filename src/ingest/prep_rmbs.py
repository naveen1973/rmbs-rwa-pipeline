#!/usr/bin/env python3
"""
RMBS Dashboard - Data Preparation Pipeline
==========================================
Ingests a monthly European DataWarehouse / BoE-format loan-level tape
(e.g. Avon Finance No.2) and produces import-ready, star-schema CSV tables
for the Power BI RMBS analytics dashboard.

The script is IDEMPOTENT and REPEATABLE: run it each month against the new
tape. It appends a new period row to the history tables (keyed by cut-off
date) so the prepayment / delinquency / default / loss time-series charts
build up automatically as tapes accumulate.

Usage:
    python prep_rmbs.py --tape "AF2_Monthly_Data_Tape_Oct_2020.xlsx" --out "./data" --seed-reference

Author: RMBS Dashboard build
"""
import argparse, os, sys, re
import numpy as np
import pandas as pd
from datetime import datetime

# ----------------------------------------------------------------------------
# Decode dictionaries (European DataWarehouse RMBS AR-field template)
# ----------------------------------------------------------------------------
PURPOSE = {1:"Purchase",2:"Re-mortgage",3:"Renovation",4:"Equity Release",
    5:"Construction",6:"Debt Consolidation",7:"Other",8:"Re-mortgage w/ Equity Release",
    9:"Re-mortgage Different Terms",10:"Combination",11:"Investment (BTL)",12:"Right to Buy",
    13:"Government Sponsored",18:"Other"}
REPAY = {1:"Interest Only",2:"Repayment",3:"Endowment",4:"Pension",5:"ISA/PEP",
    6:"Index-Linked",7:"Part & Part",8:"Savings",9:"Other"}
RATE_TYPE = {1:"Floating (for life)",2:"Floating reverting to SVR",3:"Fixed (for life)",
    4:"Fixed w/ resets",5:"Fixed then Floating",6:"Capped",7:"Discount",8:"Other"}
RATE_INDEX = {1:"1M LIBOR",2:"1M EURIBOR",3:"3M LIBOR",4:"3M EURIBOR",5:"6M LIBOR",
    6:"6M EURIBOR",7:"12M LIBOR",8:"12M EURIBOR",9:"BoE Base Rate",10:"ECB Base Rate",
    11:"Standard Variable Rate",12:"Other"}
OCCUPANCY = {1:"Owner-Occupied",2:"Partially Owner-Occupied",3:"Buy-to-Let / Non-OO",4:"Holiday / Second Home"}
PROP_TYPE = {1:"House (detached/semi)",2:"Flat / Apartment",3:"Bungalow",4:"Terraced House",
    5:"Multifamily (recourse)",6:"Multifamily (no recourse)",7:"Partially Commercial",
    8:"Commercial (recourse)",9:"Commercial (no recourse)",10:"Land Only",11:"Other"}
ACCT_STATUS = {1:"Performing",2:"Arrears",3:"Default / Foreclosure",4:"Redeemed",
    5:"Repurchased by Seller",6:"Other",7:"Repossessed"}
CHANNEL = {1:"Branch Network",2:"Central / Direct",3:"Broker",4:"Internet",5:"Packager"}
INCOME_VERIF = {1:"Self-cert, no checks",2:"Self-cert w/ affordability",3:"Verified",
    4:"Non-Verified",5:"Other"}
NUTS = {"UKC":"North East","UKD":"North West","UKE":"Yorkshire & Humber","UKF":"East Midlands",
    "UKG":"West Midlands","UKH":"East of England","UKI":"London","UKJ":"South East",
    "UKK":"South West","UKL":"Wales","UKM":"Scotland","UKN":"Northern Ireland"}

# IR-standard delinquency buckets (months in arrears). (low, high] in months.
DQ_BUCKETS = [
    ("<= 1 Month",        -0.01, 1.0),
    ("1 - 2 Months",       1.0,  2.0),
    ("2 - 3 Months",       2.0,  3.0),
    ("3 - 4 Months",       3.0,  4.0),
    ("4 - 5 Months",       4.0,  5.0),
    ("5 - 6 Months",       5.0,  6.0),
    ("> 6 Months",         6.0,  9999.0),
]

# ----------------------------------------------------------------------------
def find_col(df, code):
    """Locate a column whose header is the AR code or starts with 'AR.. '."""
    for c in df.columns:
        s = str(c)
        if s == code or s.startswith(code + " "):
            return c
    return None

def num(s):
    return pd.to_numeric(s, errors="coerce")

def parse_orig_date(v):
    """Parse origination date which may be 'Q2-1997' or a real date."""
    if pd.isna(v):
        return pd.NaT
    if isinstance(v, (datetime, pd.Timestamp)):
        return pd.Timestamp(v)
    s = str(v).strip()
    m = re.match(r"[Qq]([1-4])[-/ ](\d{4})", s)
    if m:
        q = int(m.group(1)); y = int(m.group(2))
        month = (q - 1) * 3 + 2  # mid-quarter
        return pd.Timestamp(year=y, month=month, day=1)
    try:
        return pd.Timestamp(pd.to_datetime(s))
    except Exception:
        return pd.NaT

def ltv_band(x):
    if pd.isna(x): return "Unknown"
    p = x * 100 if x <= 2 else x
    if p <= 50: return "0-50%"
    if p <= 60: return "50-60%"
    if p <= 70: return "60-70%"
    if p <= 80: return "70-80%"
    if p <= 90: return "80-90%"
    if p <= 100: return "90-100%"
    return ">100% (underwater)"

def seasoning_band(m):
    if pd.isna(m): return "Unknown"
    if m < 60: return "0-5y"
    if m < 120: return "5-10y"
    if m < 180: return "10-15y"
    if m < 240: return "15-20y"
    return "20y+"

def rate_band(r):
    if pd.isna(r): return "Unknown"
    if r < 2: return "<2%"
    if r < 3: return "2-3%"
    if r < 4: return "3-4%"
    if r < 5: return "4-5%"
    return ">5%"

def balance_band(b):
    if pd.isna(b): return "Unknown"
    if b < 50000: return "<50k"
    if b < 100000: return "50-100k"
    if b < 150000: return "100-150k"
    if b < 250000: return "150-250k"
    if b < 500000: return "250-500k"
    return ">500k"

def dq_bucket(mia):
    if pd.isna(mia): mia = 0.0
    if mia <= 1.0: return "<= 1 Month"
    if mia <= 2.0: return "1 - 2 Months"
    if mia <= 3.0: return "2 - 3 Months"
    if mia <= 4.0: return "3 - 4 Months"
    if mia <= 5.0: return "4 - 5 Months"
    if mia <= 6.0: return "5 - 6 Months"
    return "> 6 Months"

# ----------------------------------------------------------------------------
def build_loans(tape_path):
    df = pd.read_excel(tape_path, sheet_name="AF 2 Current", header=1)
    df = df[~df.iloc[:, 2].isna()].copy()   # drop blank rows (no loan id)

    g = lambda code: find_col(df, code)
    cutoff = pd.to_datetime(df[g("AR1")]).max()

    out = pd.DataFrame()
    out["LoanID"]            = df[g("AR3")].astype(str)
    out["Pool"]              = df[g("AR2")]
    out["CutoffDate"]        = cutoff
    out["Originator"]        = df[g("AR5")]
    out["Regulated"]         = df[g("AR4")].map({"Y":"Regulated","N":"Unregulated"}).fillna("Unknown")
    out["CreditQuality"]     = df[g("AR17")].fillna("No Data")
    out["FirstTimeBuyer"]    = df[g("AR22")]
    out["IncomeVerification"]= num(df[g("AR27")]).map(INCOME_VERIF).fillna("No Data")
    out["PrimaryIncome"]     = num(df[g("AR26")])
    out["OrigChannel"]       = num(df[g("AR58")]).map(CHANNEL).fillna("No Data")
    out["Purpose"]           = num(df[g("AR59")]).map(PURPOSE).fillna("No Data")
    out["OrigDate"]          = df[g("AR55")].map(parse_orig_date)
    out["MaturityDate"]      = pd.to_datetime(df[g("AR56")], errors="coerce")
    out["OrigTermMonths"]    = num(df[g("AR61")])
    out["OrigBalance"]       = num(df[g("AR66")])
    out["CurrentBalance"]    = num(df[g("AR67")]).clip(lower=0)
    out["RepaymentMethod"]   = num(df[g("AR69")]).map(REPAY).fillna("Other")
    out["PaymentDue"]        = num(df[g("AR71")])
    out["RateType"]          = num(df[g("AR107")]).map(RATE_TYPE).fillna("Other")
    out["RateIndex"]         = num(df[g("AR108")]).map(RATE_INDEX).fillna("Other")
    out["CurrentRate"]       = num(df[g("AR109")])
    out["Margin"]            = num(df[g("AR110")])
    out["Region"]            = df[g("AR128")].map(NUTS).fillna(df[g("AR128")]).fillna("Unknown")
    out["Occupancy"]         = num(df[g("AR130")]).map(OCCUPANCY).fillna("No Data")
    out["PropertyType"]      = num(df[g("AR131")]).map(PROP_TYPE).fillna("No Data")
    out["OrigLTV"]           = num(df[g("AR135")])
    out["OrigValuation"]     = num(df[g("AR136")])
    out["CurrentLTV"]        = num(df[g("AR141")])
    out["CurrentValuation"]  = num(df[g("AR143")])
    out["AccountStatus"]     = num(df[g("AR166")]).map(ACCT_STATUS).fillna("Performing")
    out["ArrearsBalance"]    = num(df[g("AR169")]).fillna(0)
    out["MonthsInArrears"]   = num(df[g("AR170")]).fillna(0)
    out["PrepayAmountMonth"] = num(df[g("AR97")]).fillna(0)
    out["CumulativePrepay"]  = num(df[g("AR100")]).fillna(0)
    out["Litigation"]        = df[g("AR174")]

    # ---- Derived metrics ----
    out["SeasoningMonths"] = ((cutoff.year - out["OrigDate"].dt.year) * 12 +
                              (cutoff.month - out["OrigDate"].dt.month))
    out["RemainingTermMonths"] = ((out["MaturityDate"].dt.year - cutoff.year) * 12 +
                                  (out["MaturityDate"].dt.month - cutoff.month))
    out["VintageYear"] = out["OrigDate"].dt.year
    out["IsInterestOnly"] = np.where(out["RepaymentMethod"].isin(["Interest Only","Part & Part"]), "Interest Only", "Repayment")
    out["IsBTL"] = np.where(out["Occupancy"].str.contains("Buy-to-Let"), "Buy-to-Let", "Owner-Occupied")
    out["Underwater"] = np.where(num(out["CurrentLTV"]) > 1.0, "Underwater (LTV>100%)", "In Equity")
    out["IsDelinquent"] = np.where(out["MonthsInArrears"] >= 1, 1, 0)
    out["IsSeriousArrears"] = np.where(out["MonthsInArrears"] > 3, 1, 0)

    # Bands
    out["LTVBand"]       = out["CurrentLTV"].map(ltv_band)
    out["OrigLTVBand"]   = out["OrigLTV"].map(ltv_band)
    out["SeasoningBand"] = out["SeasoningMonths"].map(seasoning_band)
    out["RateBand"]      = out["CurrentRate"].map(rate_band)
    out["BalanceBand"]   = out["CurrentBalance"].map(balance_band)
    out["DelinquencyBucket"] = out["MonthsInArrears"].map(dq_bucket)

    # display-friendly LTV as %
    out["CurrentLTV_pct"] = out["CurrentLTV"] * 100
    out["OrigLTV_pct"]    = out["OrigLTV"] * 100
    return out, cutoff

# ----------------------------------------------------------------------------
def build_exits(tape_path, cutoff):
    raw = pd.read_excel(tape_path, sheet_name="Sales, Redemptions, Repurchases", header=None)
    codes = raw.iloc[0].tolist()
    idx = {str(codes[i]): i for i in range(len(codes))}
    d = raw.iloc[2:].reset_index(drop=True)
    def c(code): return d.iloc[:, idx[code]] if code in idx else pd.Series([np.nan]*len(d))
    ex = pd.DataFrame()
    ex["Pool"]           = c("AR2")
    ex["PropertyID"]     = c("AR8").astype(str)
    ex["ExitStatus"]     = num(c("AR166")).map(ACCT_STATUS).fillna("Other")
    ex["RedemptionDate"] = pd.to_datetime(c("AR175"), errors="coerce")
    ex["DefaultBalance"] = num(c("AR177"))
    ex["DefaultDate"]    = pd.to_datetime(c("AR178"), errors="coerce")
    ex["SalePrice"]      = num(c("AR179"))
    ex["LossOnSale"]     = num(c("AR180"))
    ex = ex[~ex["PropertyID"].isin(["nan","None",""])].copy()
    ex["CutoffDate"]     = cutoff
    ex["LossSeverity"]   = np.where(ex["DefaultBalance"] > 0, ex["LossOnSale"] / ex["DefaultBalance"], np.nan)
    ex["RecoveryRate"]   = np.where(ex["DefaultBalance"] > 0, ex["SalePrice"] / ex["DefaultBalance"], np.nan)
    ex["IsDefault"]      = np.where(ex["DefaultBalance"] > 0, 1, 0)
    ex["IsRedemption"]   = np.where(ex["ExitStatus"] == "Redeemed", 1, 0)
    return ex

# ----------------------------------------------------------------------------
def wavg(values, weights):
    v = num(values); w = num(weights)
    m = v.notna() & w.notna() & (w > 0)
    if m.sum() == 0: return np.nan
    return float((v[m] * w[m]).sum() / w[m].sum())

def build_pool_summary(loans, exits, cutoff):
    bal = loans["CurrentBalance"]
    row = {
        "Period": cutoff.strftime("%Y-%m"),
        "CutoffDate": cutoff.strftime("%Y-%m-%d"),
        "Source": "Tape (loan-level)",
        "NumLoans": int(len(loans)),
        "CurrentBalance": float(bal.sum()),
        "OriginalBalance": float(loans["OrigBalance"].sum()),
        "AvgLoanSize": float(bal.mean()),
        "PoolFactor": float(bal.sum() / loans["OrigBalance"].sum()),
        "WA_Coupon": wavg(loans["CurrentRate"], bal),
        "WA_Margin": wavg(loans["Margin"], bal),
        "WA_CurrentLTV": wavg(loans["CurrentLTV"], bal) * 100,
        "WA_OrigLTV": wavg(loans["OrigLTV"], bal) * 100,
        "WA_Seasoning_Months": wavg(loans["SeasoningMonths"], bal),
        "WA_RemainingTerm_Months": wavg(loans["RemainingTermMonths"], bal),
        "ArrearsBalance": float(loans["ArrearsBalance"].sum()),
        "Pct_Delinquent_1m_plus": float(bal[loans["MonthsInArrears"] >= 1].sum() / bal.sum() * 100),
        "Pct_SeriousArrears_3m_plus": float(bal[loans["MonthsInArrears"] > 3].sum() / bal.sum() * 100),
        "Pct_Underwater": float(bal[num(loans["CurrentLTV"]) > 1].sum() / bal.sum() * 100),
        "Pct_InterestOnly": float(bal[loans["IsInterestOnly"] == "Interest Only"].sum() / bal.sum() * 100),
        "Pct_BTL": float(bal[loans["IsBTL"] == "Buy-to-Let"].sum() / bal.sum() * 100),
        # period activity from exits
        "Redemptions_Count": int(exits["IsRedemption"].sum()),
        "Defaults_Count": int(exits["IsDefault"].sum()),
        "Period_DefaultBalance": float(exits.loc[exits["IsDefault"]==1, "DefaultBalance"].sum()),
        "Period_LossOnSale": float(exits.loc[exits["IsDefault"]==1, "LossOnSale"].sum()),
        "Period_LossSeverity": (float(exits.loc[exits["IsDefault"]==1,"LossOnSale"].sum() /
                                       exits.loc[exits["IsDefault"]==1,"DefaultBalance"].sum())*100
                                if exits["IsDefault"].sum() > 0 else np.nan),
        # partial-prepay SMM proxy (full CPR requires consecutive tapes)
        "SMM_PartialPrepay_proxy": float(loans["PrepayAmountMonth"].sum() / bal.sum() * 100),
    }
    return pd.DataFrame([row])

def build_delinquency_long(loans, cutoff):
    bal = loans["CurrentBalance"]; tot = bal.sum()
    rows = []
    for i,(name, lo, hi) in enumerate(DQ_BUCKETS):
        m = loans["DelinquencyBucket"] == name
        rows.append({"Period": cutoff.strftime("%Y-%m"), "CutoffDate": cutoff.strftime("%Y-%m-%d"),
                     "Source": "Tape (loan-level)", "Bucket": name, "BucketOrder": i+1,
                     "Balance": float(bal[m].sum()), "Number": int(m.sum()),
                     "PctBalance": float(bal[m].sum() / tot * 100)})
    return pd.DataFrame(rows)

# ----------------------------------------------------------------------------
# Reference data taken from the Avon Finance No.2 Investor Report (28-Feb-2023)
# Used to seed the time-series so trend charts are populated and to provide the
# benchmark methodology. Tagged Source='Investor Report' for transparency.
# ----------------------------------------------------------------------------
def reference_history():
    return pd.DataFrame([
        {"Period":"2022-12","CutoffDate":"2022-12-31","Source":"Investor Report","NumLoans":6389,
         "CurrentBalance":633249943.04,"AvgLoanSize":99115.66,"WA_CurrentLTV":75.38,"WA_Coupon":4.80,
         "WA_Seasoning_Months":193.11,"CPR_1m":13.82,"CPR_3m":15.18,"CPR_12m":3.51,
         "PPR_1m":15.18,"PPR_3m":16.54,"PPR_12m":13.06,"CDR_1m":0.35,"CDR_3m":0.22,"CDR_Lifetime":0.16,
         "CumLossSeverity":16.57,"Pct_Delinquent_1m_plus":7.83},
        {"Period":"2023-02","CutoffDate":"2023-02-28","Source":"Investor Report","NumLoans":6187,
         "CurrentBalance":610011165.79,"AvgLoanSize":98595.63,"WA_CurrentLTV":75.48,"WA_Coupon":5.92,
         "WA_Seasoning_Months":196.12,"CPR_1m":9.62,"CPR_3m":12.70,"CPR_12m":9.04,
         "PPR_1m":11.24,"PPR_3m":14.15,"PPR_12m":15.82,"CDR_1m":0.51,"CDR_3m":0.29,"CDR_Lifetime":0.18,
         "CumLossSeverity":16.57,"Pct_Delinquent_1m_plus":9.54},
    ])

def reference_delinquency():
    data = [
        ("2023-02","<= 1 Month",551839344.10,5692,90.46),("2023-02","1 - 2 Months",19458288.25,176,3.19),
        ("2023-02","2 - 3 Months",12681433.87,96,2.08),("2023-02","3 - 4 Months",7115631.62,68,1.17),
        ("2023-02","4 - 5 Months",5408076.84,41,0.89),("2023-02","5 - 6 Months",2593440.82,23,0.43),
        ("2023-02","> 6 Months",10914950.29,91,1.79),
        ("2022-12","<= 1 Month",583682282.48,5953,92.17),("2022-12","1 - 2 Months",17858594.69,158,2.82),
        ("2022-12","2 - 3 Months",8249693.14,80,1.30),("2022-12","3 - 4 Months",5334040.57,43,0.84),
        ("2022-12","4 - 5 Months",4707824.52,36,0.74),("2022-12","5 - 6 Months",2772906.62,28,0.44),
        ("2022-12","> 6 Months",10644601.02,91,1.68),
    ]
    order = {n:i+1 for i,(n,_,_) in enumerate(DQ_BUCKETS)}
    rows = [{"Period":per,"CutoffDate":per+"-28","Source":"Investor Report","Bucket":bkt,
             "BucketOrder":order[bkt],"Balance":bal,"Number":num_,"PctBalance":pct}
            for per,bkt,bal,num_,pct in data]
    return pd.DataFrame(rows)

def capital_structure():
    # From Avon Finance No.2 IR 28-Feb-2023 (Principal & Interest distribution tables)
    return pd.DataFrame([
        {"Class":"Class A","Rating":"AAA","OrigBalance":666345000,"CurrentBalance":419265186.12,"Factor":0.629201,"Margin_pct":0.90,"Subordination":"Senior"},
        {"Class":"Class B","Rating":"AA","OrigBalance":32504000,"CurrentBalance":32504000.00,"Factor":1.0,"Margin_pct":1.50,"Subordination":"Mezzanine"},
        {"Class":"Class C","Rating":"A","OrigBalance":32505000,"CurrentBalance":32505000.00,"Factor":1.0,"Margin_pct":2.00,"Subordination":"Mezzanine"},
        {"Class":"Class D","Rating":"BBB","OrigBalance":24378000,"CurrentBalance":24378000.00,"Factor":1.0,"Margin_pct":2.50,"Subordination":"Mezzanine"},
        {"Class":"Class E","Rating":"BB","OrigBalance":20316000,"CurrentBalance":20316000.00,"Factor":1.0,"Margin_pct":3.00,"Subordination":"Junior"},
        {"Class":"Class F","Rating":"B","OrigBalance":8126000,"CurrentBalance":8126000.00,"Factor":1.0,"Margin_pct":3.25,"Subordination":"Junior"},
        {"Class":"Class Z","Rating":"NR","OrigBalance":28441000,"CurrentBalance":28441000.00,"Factor":1.0,"Margin_pct":np.nan,"Subordination":"Residual"},
        {"Class":"VRR Loan Note","Rating":"NR","OrigBalance":42770000,"CurrentBalance":29765799.28,"Factor":0.695950,"Margin_pct":np.nan,"Subordination":"Risk Retention"},
    ])

# ----------------------------------------------------------------------------
def scenario_tables(outdir):
    """Disconnected what-if parameter tables for stress testing."""
    pd.DataFrame({"HPI_Shock_pct":[-40,-35,-30,-25,-20,-15,-10,-5,0,5,10]}).to_csv(
        os.path.join(outdir,"Scenario_HPI.csv"), index=False)
    pd.DataFrame({"CDR_Multiplier":[0.5,0.75,1.0,1.5,2.0,2.5,3.0,4.0,5.0]}).to_csv(
        os.path.join(outdir,"Scenario_CDR.csv"), index=False)
    pd.DataFrame({"Severity_Multiplier":[0.5,0.75,1.0,1.25,1.5,1.75,2.0]}).to_csv(
        os.path.join(outdir,"Scenario_Severity.csv"), index=False)
    pd.DataFrame({"CPR_Assumption_pct":[0,2,4,6,8,10,12,15,20,25,30]}).to_csv(
        os.path.join(outdir,"Scenario_CPR.csv"), index=False)

def date_table(outdir, start="1997-01-01", end="2030-12-31"):
    rng = pd.date_range(start, end, freq="MS")
    dt = pd.DataFrame({"Date":rng})
    dt["Year"]=dt.Date.dt.year; dt["Quarter"]="Q"+dt.Date.dt.quarter.astype(str)
    dt["Month"]=dt.Date.dt.month; dt["MonthName"]=dt.Date.dt.strftime("%b")
    dt["YearMonth"]=dt.Date.dt.strftime("%Y-%m")
    dt.to_csv(os.path.join(outdir,"DateTable.csv"), index=False)

# ----------------------------------------------------------------------------
def append_history(path, new_df, keys=("Period","Source")):
    if os.path.exists(path):
        old = pd.read_csv(path)
        combined = pd.concat([old, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=list(keys), keep="last")
    else:
        combined = new_df
    sort_cols = [k for k in ("CutoffDate","Period","Source","BucketOrder") if k in combined.columns]
    combined = combined.sort_values(sort_cols)
    combined.to_csv(path, index=False)
    return combined

# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tape", required=True)
    ap.add_argument("--out", default="./data")
    ap.add_argument("--seed-reference", action="store_true",
                    help="Seed history with Investor-Report benchmark rows (first run only).")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    print(f"Reading tape: {args.tape}")
    loans, cutoff = build_loans(args.tape)
    exits = build_exits(args.tape, cutoff)
    print(f"  loans={len(loans):,}  exits={len(exits):,}  cutoff={cutoff.date()}")

    loans.to_csv(os.path.join(args.out, "Loans.csv"), index=False)
    exits.to_csv(os.path.join(args.out, "Exits.csv"), index=False)

    summ = build_pool_summary(loans, exits, cutoff)
    dq   = build_delinquency_long(loans, cutoff)

    if args.seed_reference:
        summ = pd.concat([reference_history(), summ], ignore_index=True)
        dq   = pd.concat([reference_delinquency(), dq], ignore_index=True)

    append_history(os.path.join(args.out, "PoolHistory.csv"), summ)
    append_history(os.path.join(args.out, "DelinquencyHistory.csv"), dq,
                   keys=("Period","Source","Bucket"))

    capital_structure().to_csv(os.path.join(args.out, "CapitalStructure.csv"), index=False)
    scenario_tables(args.out)
    date_table(args.out)

    print(f"Done. CSVs written to: {args.out}")
    for f in sorted(os.listdir(args.out)):
        p=os.path.join(args.out,f); print(f"  {f:28} {os.path.getsize(p):>9,} bytes")

if __name__ == "__main__":
    main()
