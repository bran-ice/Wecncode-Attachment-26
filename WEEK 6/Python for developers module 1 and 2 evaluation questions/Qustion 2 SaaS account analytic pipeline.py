# Fixed constant
MRR_THRESHOLD = 1000
input_lines = [
    "Acme,Pro,1500,10,yes",
    "Globex,Free,0,3,yes",
    "Initech,Pro,800,5,no",
    "Umbrella,Enterprise,3000,50,yes",
    "Hooli,Free,200,2,yes"
]
accounts = []
for line in input_lines:
    parts = line.strip().split(",")
    record = {
        "name": parts[0].strip(),
        "plan": parts[1].strip(),
        "mrr": int(parts[2].strip()),
        "seats": int(parts[3].strip()),
        "active": parts[4].strip().lower() == "yes"
    }
    accounts.append(record)
unique_plans = sorted(list({account["plan"] for account in accounts}))
active_accounts_iter = filter(lambda acc: acc["active"], accounts)
active_accounts = list(active_accounts_iter)
active_count = len(active_accounts)
total_active_mrr = sum(acc["mrr"] for acc in active_accounts)
leaderboard_sorted = sorted(active_accounts, key=lambda acc: (acc["plan"], -acc["mrr"]))
leaderboard_lines = list(map(lambda acc: f"{acc['name']} ({acc['plan']}): ${acc['mrr']}", leaderboard_sorted))
def make_min_mrr(threshold):
    def predicate(acc):
        return acc["mrr"] >= threshold
    return predicate

qualified_predicate = make_min_mrr(MRR_THRESHOLD)
qualified_active = filter(qualified_predicate, active_accounts)
qualified_names = sorted([acc["name"] for acc in qualified_active])
tier_labels = [
    f"{acc['name']}: {'High' if acc['mrr'] >= MRR_THRESHOLD else 'Standard'}"
    for acc in active_accounts
]
print(f"Unique plans: {unique_plans}")
print(f"Active accounts: {active_count}")
print(f"Total active MRR: ${total_active_mrr}")
print("Accounts (by plan, then MRR desc):")
for line in leaderboard_lines:
    print(f"  {line}")
print(f"Qualified (active, MRR >= 1000): {qualified_names}")
print(f"Tier labels: {tier_labels}")