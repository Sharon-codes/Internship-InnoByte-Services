💸 Personal Finance Manager

A Python CLI app to track your money like a pro! 📊 Manage income, expenses, budgets, and reports with ease, powered by SQLite. 🚀

✨ Features
👤 User Accounts: Secure registration & login (SHA-256 hashed passwords).
💰 Transactions: Add, edit, delete income/expenses with categories.
📅 Budgets: Set monthly limits, get warnings if overspent (🟢🟠🔴).
📈 Reports: Monthly, yearly, category, and trend analysis.
💾 Backup/Restore: Save and recover your data safely.

🛠️ Requirements

To run this project, you’ll need:

- Python 3.6 or higher 🐍

Required Python packages:
- tabulate (for pretty-printed tables)
- getpass (included in Python standard library)
- sqlite3 (included in Python standard library)
- hashlib (included in Python standard library)
- os (included in Python standard library)
- datetime (included in Python standard library)

🎮 Usage
- Start: Run python Finance_Manager.py.
  
- Unauthenticated:
Register 📝
Login 🔑
Exit 🚪

- Authenticated:
Add/View/Edit/Delete transactions 💸
Set/View budgets 📋
Generate reports 📊
Backup/Restore data 💾
Logout 👋

Example: Register, add $1000 "Salary" income, set $300 "Food" budget, track spending, and view reports.

🔐 Security
Passwords hashed with SHA-256 🔒
Local SQLite storage 🗄️
Regular backups recommended 💾
