import pandas as pd

df = pd.read_csv(r"HDI vs Fertility Data/children-per-woman-vs-human-development-index.csv")

print(df.shape)
print(df.columns)
print(df.head(3))