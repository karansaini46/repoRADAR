from autoscan.shared.db.database import SessionLocal
from autoscan.shared.db.models import Finding, Repository, Company

db = SessionLocal()
print("Findings summary:")
res = db.query(Finding.repository_id, Finding.is_false_positive).all()
print(f"Total findings: {len(res)}")
from collections import Counter
c = Counter((r[0], r[1]) for r in res)
for k, v in c.items():
    print(f"Repo {k}, is_false_positive={k[1]}: {v}")

repos = db.query(Repository.id, Repository.company_id, Repository.name).all()
for r in repos:
    print(f"Repo {r.id} belongs to company {r.company_id} ({r.name})")

companies = db.query(Company.id, Company.name).all()
print(companies[:5])
db.close()
