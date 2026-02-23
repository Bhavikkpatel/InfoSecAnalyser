import pandas as pd
import random
import uuid
from faker import Faker

fake = Faker()

# -------- CONFIG --------
NUM_VENDORS = 2000 
OUTPUT_FILE = "sample_tprm_assessments.xlsx"
# ------------------------

def random_yes_no():
    return random.choice(["Yes", "No"])

def random_compliance():
    frameworks = ["GDPR", "HIPAA", "PCI-DSS", "CCPA", "ISO 27001", "SOC 2", "NIST"]
    return ", ".join(random.sample(frameworks, random.randint(1, 4)))

def random_rto():
    return f"{random.choice([2,4,8,12,24,48])} hours"

def random_rpo():
    return f"{random.choice([15,30,60,120,240])} minutes"

def random_revenue():
    return random.choice([
        "< $1M",
        "$1M - $10M",
        "$10M - $50M",
        "$50M - $100M",
        "> $100M"
    ])

vendors = []

for _ in range(NUM_VENDORS):
    vendor = {
        # General Company Information
        "Legal Name": fake.company(),
        "Trade Name": fake.company_suffix(),
        "Business Registration Number": str(uuid.uuid4())[:12],
        "Country of Incorporation": fake.country(),
        "Headquarters Address": fake.address(),
        "Website": fake.url(),
        "Number of Employees": random.randint(20, 5000),
        "Years in Operation": random.randint(1, 30),
        "Primary Industry": random.choice(["IT Services", "FinTech", "Healthcare", "Manufacturing", "Retail"]),
        "Revenue Range": random_revenue(),

        # Information Security
        "Formal InfoSec Policy": random_yes_no(),
        "Certified Standards": random_compliance(),
        "Security Risk Assessment (12 months)": random_yes_no(),
        "Data Encryption": random.choice(["AES-256 at rest, TLS 1.2 in transit", "TLS only", "Encryption at rest only"]),
        "Penetration Testing": random.choice(["Annually", "Bi-annually", "Quarterly", "Not conducted"]),
        "DLP Strategy": random_yes_no(),
        "Security Breach Last 2 Years": random.choice(["None", "Minor incident resolved", "Major breach reported"]),

        # Compliance
        "Regulatory Compliance": random_compliance(),
        "External Audit Conducted": random_yes_no(),
        "Data Processing Agreement": random_yes_no(),
        "Internal Audit Frequency": random.choice(["Quarterly", "Annually", "Bi-annually"]),

        # Business Continuity
        "Business Continuity Plan": random_yes_no(),
        "DRP Testing Frequency": random.choice(["Quarterly", "Annually", "Bi-annually"]),
        "RTO": random_rto(),
        "RPO": random_rpo(),
        "Major Outage Last 2 Years": random.choice(["None", "1 outage", "Multiple outages"]),

        # Vendor Risk Management
        "Uses Subcontractors": random_yes_no(),
        "Subcontractor Monitoring": random.choice(["Annual audits", "Continuous monitoring", "Self-assessment only"]),
        "Subcontractor Access to Sensitive Data": random_yes_no(),

        # Incident Response
        "Incident Response Plan": random_yes_no(),
        "Incident Simulation Conducted": random_yes_no(),
        "Significant Breach Last 12 Months": random.choice(["None", "Yes - resolved", "Yes - ongoing investigation"]),

        # Financial
        "Financial Statements Provided": random_yes_no(),
        "Cyber Insurance": random_yes_no(),
        "Customer Compensation Policy": random.choice(["Defined in SLA", "Case-by-case basis", "Not defined"]),

        # Physical Security
        "24/7 Infrastructure Monitoring": random_yes_no(),
        "Access Control Mechanisms": random.choice(["Biometric + Badge", "Badge only", "Manual log entry"]),

        # HR & Training
        "Background Checks Conducted": random_yes_no(),
        "Cybersecurity Training Frequency": random.choice(["Quarterly", "Annually", "Upon hiring only"]),
        "Remote Work Security Guidelines": random_yes_no(),

        # Legal
        "Standard SLA Available": random_yes_no(),
        "Contract Termination & Data Destruction Policy": random_yes_no(),
        "Legal Dispute Resolution Mechanism": random.choice(["Arbitration", "Court litigation", "Mediation"])
    }

    vendors.append(vendor)

df = pd.DataFrame(vendors)
df.to_excel(OUTPUT_FILE, index=False)

print(f"Sample TPRM assessments generated successfully: {OUTPUT_FILE}")