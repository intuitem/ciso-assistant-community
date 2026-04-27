import pandas as pd

df = pd.read_excel("EUDI ARF HLRs.xlsx")

df["ref_ID"] = df["ref_ID"].astype(str).str.strip()

counts = df["ref_ID"].value_counts()
dupes = counts[counts >= 2].index

mask = df["ref_ID"].isin(dupes)
df.loc[mask, "ref_ID"] = (
    df.loc[mask, "ref_ID"]
    + "-"
    + df.loc[mask].groupby("ref_ID").cumcount().add(1).astype(str)
)

df.to_excel("EUDI_ARF_HLRs_unique.xlsx", index=False)