import pandas as pd
import random

risks = []
departments = ["Finance", "IT", "HR", "Operations"]
statuses = ["Open", "Closed", "In Progress"]
levels = ["Low", "Medium", "High"]

for i in range(1, 51):
    risks.append({
        "Risk ID": f"RSK-{i:03d}",
        "Description": f"Potential risk issue related to process {i}.",
        "Department": random.choice(departments),
        "Status": random.choice(statuses),
        "Risk Level": random.choice(levels)
    })

df = pd.DataFrame(risks)
df.to_excel("sample_risks.xlsx", index=False)
print("sample_risks.xlsx created successfully.")
