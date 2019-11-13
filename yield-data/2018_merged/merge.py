import pandas as pd
import os

dfs = []
for filename in os.listdir('/home/ian/spatial-crop-yield/yield-data/2018_merged'):
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(f'/home/ian/spatial-crop-yield/yield-data/2018_merged/{filename}', encoding = "ISO-8859-1")
            cols = [4, 5, 11]
            df = df[df.columns[cols]]
            dfs.append(df)

df_merged = dfs[0]
for df in dfs[1:]:
    df_merged = pd.concat([df_merged, df], join='outer')

df_merged.to_csv('merged.csv')
