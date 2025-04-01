# Optimization Problem:
# I have to make payments on different schedules for different accounts.
# Each payday I receive $675 that can be split across, at most, 3 accounts.
# Each account has a Need to Start Payments Date and a Deadline Date.
# Some accounts require a total amount to be paid off by the date (e.g. $1000 by 2025-12-31)
# Some accounts require a certain number of payments of a certain amount to be made by the date (e.g. 2 payments of $500 by 2025-12-31)
# Some accounts require atleast a certain number of payments be made, summing to a certain amount, by the date (e.g. atleast 2 payments summing to $1000 by 2025-12-31)
# All accounts have a start by date (prior to which the first payment needs to be made) and a days till deadline (which represents the days from the inital payment that the last payment needs to be made)

# ALL DATES ARE IN DAYS FROM TODAY
import calendar
from datetime import datetime, timedelta
import pulp
from pulp import PULP_CBC_CMD


# Function to find the weekday closest to a given day
def closest_weekday(year, month, day):
    date = datetime(year, month, day)
    weekday = date.weekday()
    if weekday == 5:  # Saturday
        date = date - timedelta(days=1)
    elif weekday == 6:  # Sunday
        date = date + timedelta(days=1)
    return date

# Function to generate paydays for closest to the 15th and end of the month for a year, from today
def get_paydays(year):
    pay_dates = []
    for month in range(1, 13):
        # Payday closest to the 15th
        first_payday = closest_weekday(year, month, 15).date()
        
        if first_payday > datetime.now().date():
            pay_dates.append(first_payday)
        
        # Payday closest to the end of the month
        last_day = calendar.monthrange(year, month)[1]
        last_payday = closest_weekday(year, month, last_day).date()
        if last_payday > datetime.now().date():
            pay_dates.append(last_payday)
    
    # Convert the list of paydays to a list of days from today
    today_date = datetime.now().date()
    pay_dates_days = [(payday - today_date).days for payday in pay_dates]
    return pay_dates_days
    

# Account Class to store account-specific information
class Account:
    def __init__(self, name, start_date, days_till_deadline, total_amount = None, num_payments = None, value_per_payment = None, min_payments = None, total_sum = None):
        self.name = name
        self.start_date = start_date
        self.days_till_deadline = days_till_deadline
        self.total_amount = total_amount
        self.num_payments = num_payments
        self.value_per_payment = value_per_payment
        self.min_payments = min_payments
        self.total_sum = total_sum
    def __repr__(self):
        if self.total_amount:
            return f"Account: {self.name}, Amount: {self.total_amount}"
        elif self.num_payments and self.value_per_payment:
            return f"Account: {self.name}, Num Payments: {self.num_payments}, Value per Payment: {self.value_per_payment}"
        elif self.min_payments and self.total_sum:
            return f"Account: {self.name}, Min Payments: {self.min_payments}, Total Sum: {self.total_sum}"
# List to store the accounts
today = datetime(datetime.now().year, datetime.now().month, datetime.now().day)

bonus_accounts = [
    Account("Wells Fargo", (datetime(2025, 4, 16) - today).days, 90, total_amount=1000),
    Account("Citizens Bank", (datetime(2025, 3, 31) - today).days, 60, num_payments=1, value_per_payment=500),
    Account("Capital One", (datetime(2025, 3, 31) - today).days, 75, num_payments=2, value_per_payment=500),
    Account("Fifth Third", (datetime(2025, 3, 31) - today).days, 90, total_amount=500),
    Account("Keybank", (datetime(2025, 6, 27) - today).days, 90, total_amount=1000),
    Account("Chime(SwagBucks)", (datetime(2025, 3, 31) - today).days, 30, num_payments=2, value_per_payment=200),
    Account("Truist", (datetime(2025, 4, 30) - today).days, 120, min_payments=2, total_sum=1000),
    Account("Bank of America", (datetime(2025, 5, 31) - today).days, 90, total_amount=2000)
]

# Subtract 10 days from the deadline for safety
safety_days = 10
for account in bonus_accounts:
    account.days_till_deadline -= safety_days

import pulp
# Create a LP Minimization problem
prob = pulp.LpProblem("Bonus", pulp.LpMinimize)

# Variables

# For each payday, for each account, create an integer variable representing the amount paid
amounts = pulp.LpVariable.dicts("Amount", ((payday, account) for payday in get_paydays(2025) for account in bonus_accounts), lowBound=0, cat='Integer')

# For each payday, for each account, create a binary variable representing if the account is paid
paid = pulp.LpVariable.dicts("Paid", ((payday, account) for payday in get_paydays(2025) for account in bonus_accounts), cat='Binary')

# For each account, create an integer variable representing the number of days from today the account is created
created = pulp.LpVariable.dicts("Created", (account for account in bonus_accounts), lowBound=0, cat='Integer')

# Constraints

# For each payday, the sum of the amounts paid across all accounts should be less than or equal to the pay amount
pay_amount = 675 # Amount received on payday
for payday in get_paydays(2025):
    prob += pulp.lpSum(amounts[(payday, account)] for account in bonus_accounts) <= pay_amount

# For each payday, only 3 accounts can be paid
for payday in get_paydays(2025):
    prob += pulp.lpSum(paid[(payday, account)] for account in bonus_accounts) <= 3

# For each payday, for each account link the integer variable amount to the binary variable paid such that if
# the amount is greater than 0, the binary variable is 1 and if binary variable is 1, the amount is greater than 0
# Eqn: paid binary variable = x, amount integer variable = y, M = 1000
# y <= Mx
M = 1000
for payday in get_paydays(2025):
    for account in bonus_accounts:
        prob += amounts[(payday, account)] <= M * paid[(payday, account)]
        
# For each payday, for each account, if the account is paid, the amount should be greater than some minimum value (50)
minimum_payment = 100
for payday in get_paydays(2025):
    for account in bonus_accounts:
        prob += amounts[(payday, account)] >= minimum_payment * paid[(payday, account)]

# For each account, the account should be created before the start date
for account in bonus_accounts:
    prob += created[account] <= account.start_date - 2

# For each account, the last payment should be made before created + days_till_deadline
# Need an auxiliary variable to represent the last payment date
last_payment = pulp.LpVariable.dicts("Last_Payment", (account for account in bonus_accounts), lowBound=0, cat='Integer')
for account in bonus_accounts:
    # For each payday, if the account is paid, the last payment should be greater than or equal to the payday
    for payday in get_paydays(2025):
        prob += last_payment[account] >= payday * paid[(payday, account)]
    
    # The last payment should be made before created + days_till_deadline
    prob += last_payment[account] <= (created[account] + account.days_till_deadline)

# For each last payment value, the last payment value should be equal to one of the paydays
# Done by creating a binary variable for each payday, then linking the last payment value to the x1*y1 + x2*y2 + ... + xn*yn = last_payment, and x1 + x2 + ... + xn = 1
paydays = get_paydays(2025)
last_payment_payday = pulp.LpVariable.dicts("Last_Payment_Binary",((payday, account) for payday in get_paydays(2025) for account in bonus_accounts), cat='Binary')
for account in bonus_accounts:
    prob += last_payment[account] == pulp.lpSum(payday * last_payment_payday[(payday, account)] for payday in get_paydays(2025))
    prob += pulp.lpSum(last_payment_payday[(payday, account)] for payday in get_paydays(2025)) == 1

# For each account, all the payments should be made after the account is created using Big M method
M = 1000
for account in bonus_accounts:
    for payday in get_paydays(2025):
        prob += created[account] <= payday + M * (1 - paid[(payday, account)])

# Account-specific constraints

# For accounts with a total amount, the total amount should be paid
for account in bonus_accounts:
    if account.total_amount:
        prob += pulp.lpSum(amounts[(payday, account)] for payday in get_paydays(2025)) == account.total_amount # Total amount
        prob += pulp.lpSum(paid[(payday, account)] for payday in get_paydays(2025)) >= 1 # Atleast one payment should be made

# For accounts with a number of payments and a value per payment, the number of payments should be made and each payment should be of the value
for account in bonus_accounts:
    if account.num_payments and account.value_per_payment:
        prob += pulp.lpSum(paid[(payday, account)] for payday in get_paydays(2025)) == account.num_payments # Number of payments
        # For each payday, if the account is paid, the amount should be equal to the value per payment
        for payday in get_paydays(2025):
            prob += amounts[(payday, account)] == account.value_per_payment * paid[(payday, account)]

# For accounts with a minimum number of payments and a total sum, atleast the minimum number of payments should be made summing to the total sum
for account in bonus_accounts:
    if account.min_payments and account.total_sum:
        prob += pulp.lpSum(paid[(payday, account)] for payday in get_paydays(2025)) >= account.min_payments # Minimum number of payments
        prob += pulp.lpSum(amounts[(payday, account)] for payday in get_paydays(2025)) >= account.total_sum # Total sum
        
# Create an auxiliary variable to represent the maximum last payment date across all accounts
all_account_max_last_payment = pulp.LpVariable("All_Account_Max_Last_Payment", cat='Integer')

# For each account, the maximum last payment date should be greater than or equal to the last payment date of the account
for account in bonus_accounts:
    prob += all_account_max_last_payment >= last_payment[account]

# Objective Function - Minimize the last payment date
prob += all_account_max_last_payment

# Solve the LP problem
prob.solve(PULP_CBC_CMD(msg=0))

# Print the status of the solution
print("Status:", pulp.LpStatus[prob.status])
print("Objective Function Value:", pulp.value(prob.objective))
print("\n")

# Print all the accounts, the created date, the last payment date, sorted by created date (converted to actual date)
bonus_accounts.sort(key=lambda x: created[x].varValue)
print(f"{'Account Name':<20}{'Created Date':<15}{'Last Payment Date':<20}")
print("-" * 55)
for account in bonus_accounts:
    created_date = (today + timedelta(days=created[account].varValue)).strftime('%Y-%m-%d')
    last_payment_date = (today + timedelta(days=last_payment[account].varValue)).strftime('%Y-%m-%d')
    print(f"{account.name:<20}{created_date:<15}{last_payment_date:<20}")

print("\n")
# Print each payday, the accounts paid and the amount paid, and the total amount paid
for payday in get_paydays(2025):
    print(f"Payday: {(today + timedelta(days=payday)).strftime('%Y-%m-%d')}, Total Amount Paid: {sum(amounts[(payday, account)].varValue for account in bonus_accounts if paid[(payday, account)].varValue)}")
    for account in bonus_accounts:
        if paid[(payday, account)].varValue:
            print(f"    {account.name}: {amounts[(payday, account)].varValue}")

# Make a csv sheet with the schedule, each payday is a row, each account is a column, the amount paid is the value
import csv
with open("bonus_schedule.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Payday"] + [account.name for account in bonus_accounts])
    for payday in get_paydays(2025):
        row = [f"{(today + timedelta(days=payday)).strftime('%Y-%m-%d')}"]
        for account in bonus_accounts:
            row.append(amounts[(payday, account)].varValue)
        writer.writerow(row)