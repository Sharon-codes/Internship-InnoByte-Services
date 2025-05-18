import os
import sqlite3
import hashlib
import re
import datetime
from getpass import getpass
from tabulate import tabulate
from datetime import datetime, timedelta

class PersonalFinanceManager:
    def __init__(self, conn=None):
        self.db_file = "finance_manager.db"
        self.conn = conn  # Store provided connection, if any
        self.current_user = None
        self.setup_database()
        
    def setup_database(self):
        """Initialize the database and create necessary tables if they don't exist."""
        # Use provided connection or create a new one
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create transactions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Create budget table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, category, month, year)
        )
        ''')
        
        # Commit changes if we created the connection
        if not self.conn:
            conn.commit()
            conn.close()
        
    def hash_password(self, password):
        """Hash the password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self):
        """Register a new user."""
        print("\n=== User Registration ===")
        
        while True:
            username = input("Enter username (min 3 characters): ").strip()
            if len(username) < 3:
                print("Username must be at least 3 characters long.")
                continue
                
            # Check if username exists
            conn = self.conn if self.conn else sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                print("Username already exists. Please choose another one.")
                if not self.conn:
                    conn.close()
                continue
            
            # Password validation
            while True:
                password = getpass("Enter password (min 6 characters): ")
                if len(password) < 6:
                    print("Password must be at least 6 characters long.")
                    continue
                    
                confirm_password = getpass("Confirm password: ")
                if password != confirm_password:
                    print("Passwords do not match. Try again.")
                    continue
                break
            
            # Save user to database
            password_hash = self.hash_password(password)
            try:
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
                if not self.conn:
                    conn.commit()
                print("\n✓ Registration successful! You can now log in.")
                break
            except sqlite3.Error as e:
                print(f"Database error: {e}")
            finally:
                if not self.conn:
                    conn.close()
            
    def login(self):
        """Authenticate user and set current_user if successful."""
        print("\n=== User Login ===")
        
        username = input("Username: ").strip()
        password = getpass("Password: ")
        
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?", 
                (username,)
            )
            user = cursor.fetchone()
            
            if user and user[2] == self.hash_password(password):
                self.current_user = {"id": user[0], "username": user[1]}
                print(f"\n✓ Welcome back, {user[1]}!")
                if not self.conn:
                    conn.commit()
                return True
            else:
                print("Invalid username or password.")
                return False
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            if not self.conn:
                conn.close()
    
    def logout(self):
        """Log out the current user."""
        if self.current_user:
            print(f"\n✓ Goodbye, {self.current_user['username']}!")
            self.current_user = None
        else:
            print("No user is currently logged in.")
    
    def add_transaction(self):
        """Add a new income or expense transaction."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== Add Transaction ===")
        
        # Get transaction type (income or expense)
        while True:
            transaction_type = input("Transaction type (income/expense): ").strip().lower()
            if transaction_type in ["income", "expense"]:
                break
            print("Invalid type. Please enter 'income' or 'expense'.")
        
        # Get amount
        while True:
            try:
                amount = float(input("Amount: $").strip())
                if amount <= 0:
                    print("Amount must be greater than zero.")
                    continue
                break
            except ValueError:
                print("Invalid amount. Please enter a number.")
        
        # Get category
        categories = self.get_categories(transaction_type)
        print(f"\nAvailable {transaction_type} categories:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")
        print(f"{len(categories) + 1}. Other (create new)")
        
        while True:
            try:
                choice = int(input("\nSelect category number: "))
                if 1 <= choice <= len(categories):
                    category = categories[choice - 1]
                    break
                elif choice == len(categories) + 1:
                    category = input("Enter new category name: ").strip().title()
                    if not category:
                        print("Category cannot be empty.")
                        continue
                    break
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Please enter a number.")
        
        # Get description
        description = input("Description (optional): ").strip()
        
        # Get date (default is today)
        while True:
            date_input = input("Date (YYYY-MM-DD, leave empty for today): ").strip()
            if not date_input:
                date = datetime.now().strftime("%Y-%m-%d")
                break
            
            try:
                date = datetime.strptime(date_input, "%Y-%m-%d").strftime("%Y-%m-%d")
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD.")
        
        # Save transaction to database
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT INTO transactions 
                (user_id, type, amount, category, description, date) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (self.current_user["id"], transaction_type, amount, category, description, date)
            )
            if not self.conn:
                conn.commit()
            print(f"\n✓ {transaction_type.title()} transaction added successfully!")
            
            # Check if budget is exceeded for expense transactions
            if transaction_type == "expense":
                self.check_budget_limit(category, amount, date)
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def get_categories(self, transaction_type):
        """Get list of categories based on transaction type."""
        if transaction_type == "income":
            return ["Salary", "Freelance", "Investment", "Gift", "Refund"]
        else:  # expense
            return ["Food", "Housing", "Transportation", "Utilities", "Entertainment", 
                    "Healthcare", "Education", "Shopping", "Personal Care"]
    
    def view_transactions(self):
        """View all transactions for the current user."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== View Transactions ===")
        
        # Filter options
        print("\nFilter options:")
        print("1. View all transactions")
        print("2. Filter by date range")
        print("3. Filter by category")
        print("4. Filter by transaction type")
        
        choice = input("\nSelect an option (1-4): ").strip()
        
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """SELECT id, type, amount, category, description, date 
                   FROM transactions 
                   WHERE user_id = ?"""
        params = [self.current_user["id"]]
        
        # Apply filters based on user choice
        if choice == "2":
            start_date = input("Start date (YYYY-MM-DD): ").strip()
            end_date = input("End date (YYYY-MM-DD, leave empty for today): ").strip()
            
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
                
            query += " AND date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
            
        elif choice == "3":
            category = input("Enter category: ").strip()
            query += " AND category LIKE ?"
            params.append(f"%{category}%")
            
        elif choice == "4":
            while True:
                trans_type = input("Transaction type (income/expense): ").strip().lower()
                if trans_type in ["income", "expense"]:
                    break
                print("Invalid type. Please enter 'income' or 'expense'.")
                
            query += " AND type = ?"
            params.append(trans_type)
        
        query += " ORDER BY date DESC"
        
        try:
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            
            if not transactions:
                print("\nNo transactions found.")
                return
            
            # Display transactions
            headers = ["ID", "Type", "Amount", "Category", "Description", "Date"]
            table_data = []
            
            for t in transactions:
                # Format amount with currency symbol based on transaction type
                if t["type"] == "income":
                    amount = f"+${t['amount']:.2f}"
                else:
                    amount = f"-${t['amount']:.2f}"
                    
                table_data.append([
                    t["id"],
                    t["type"].title(),
                    amount,
                    t["category"],
                    t["description"] if t["description"] else "-",
                    t["date"]
                ])
            
            print("\n" + tabulate(table_data, headers=headers, tablefmt="pretty"))
            
            # Show summary
            total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
            total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
            balance = total_income - total_expense
            
            print(f"\nSummary:")
            print(f"Total Income: ${total_income:.2f}")
            print(f"Total Expenses: ${total_expense:.2f}")
            print(f"Balance: ${balance:.2f}")
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def edit_transaction(self):
        """Edit an existing transaction."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== Edit Transaction ===")
        
        # First, display recent transactions
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT id, type, amount, category, description, date 
                   FROM transactions 
                   WHERE user_id = ? 
                   ORDER BY date DESC LIMIT 10""",
                (self.current_user["id"],)
            )
            transactions = cursor.fetchall()
            
            if not transactions:
                print("No transactions found.")
                return
            
            # Display transactions
            headers = ["ID", "Type", "Amount", "Category", "Description", "Date"]
            table_data = []
            
            for t in transactions:
                # Format amount with currency symbol based on transaction type
                if t["type"] == "income":
                    amount = f"+${t['amount']:.2f}"
                else:
                    amount = f"-${t['amount']:.2f}"
                    
                table_data.append([
                    t["id"],
                    t["type"].title(),
                    amount,
                    t["category"],
                    t["description"] if t["description"] else "-",
                    t["date"]
                ])
            
            print("\nRecent Transactions:")
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            
            # Get transaction ID to edit
            while True:
                try:
                    transaction_id = int(input("\nEnter ID of transaction to edit (0 to cancel): "))
                    if transaction_id == 0:
                        return
                    
                    # Check if transaction exists and belongs to current user
                    cursor.execute(
                        """SELECT id, type, amount, category, description, date 
                           FROM transactions 
                           WHERE id = ? AND user_id = ?""",
                        (transaction_id, self.current_user["id"])
                    )
                    transaction = cursor.fetchone()
                    
                    if not transaction:
                        print("Transaction not found or you don't have permission to edit it.")
                        continue
                    break
                except ValueError:
                    print("Please enter a valid ID.")
            
            # Show current values
            print(f"\nEditing transaction #{transaction_id}:")
            print(f"Current type: {transaction['type']}")
            print(f"Current amount: ${transaction['amount']:.2f}")
            print(f"Current category: {transaction['category']}")
            print(f"Current description: {transaction['description'] or '-'}")
            print(f"Current date: {transaction['date']}")
            
            # Get new values
            print("\nEnter new values (leave empty to keep current value):")
            
            # Type
            while True:
                new_type = input(f"New type (income/expense): ").strip().lower()
                if not new_type:
                    new_type = transaction["type"]
                    break
                elif new_type in ["income", "expense"]:
                    break
                print("Invalid type. Please enter 'income' or 'expense'.")
            
            # Amount
            while True:
                new_amount_str = input(f"New amount: $").strip()
                if not new_amount_str:
                    new_amount = transaction["amount"]
                    break
                try:
                    new_amount = float(new_amount_str)
                    if new_amount <= 0:
                        print("Amount must be greater than zero.")
                        continue
                    break
                except ValueError:
                    print("Invalid amount. Please enter a number.")
            
            # Category
            if new_type != transaction["type"]:
                # If type changed, show categories for the new type
                categories = self.get_categories(new_type)
                print(f"\nAvailable {new_type} categories:")
                for i, category in enumerate(categories, 1):
                    print(f"{i}. {category}")
                print(f"{len(categories) + 1}. Other (create new)")
                print(f"{len(categories) + 2}. Keep current ({transaction['category']})")
                
                while True:
                    try:
                        choice = int(input("\nSelect category number: "))
                        if 1 <= choice <= len(categories):
                            new_category = categories[choice - 1]
                            break
                        elif choice == len(categories) + 1:
                            new_category = input("Enter new category name: ").strip().title()
                            if not new_category:
                                print("Category cannot be empty.")
                                continue
                            break
                        elif choice == len(categories) + 2:
                            new_category = transaction["category"]
                            break
                        else:
                            print("Invalid choice.")
                    except ValueError:
                        print("Please enter a number.")
            else:
                new_category_input = input(f"New category (current: {transaction['category']}): ").strip()
                new_category = new_category_input if new_category_input else transaction["category"]
            
            # Description
            new_description = input(f"New description (current: {transaction['description'] or '-'}): ").strip()
            if not new_description and transaction["description"]:
                new_description = transaction["description"]
            
            # Date
            while True:
                new_date_input = input(f"New date (YYYY-MM-DD, current: {transaction['date']}): ").strip()
                if not new_date_input:
                    new_date = transaction["date"]
                    break
                
                try:
                    new_date = datetime.strptime(new_date_input, "%Y-%m-%d").strftime("%Y-%m-%d")
                    break
                except ValueError:
                    print("Invalid date format. Please use YYYY-MM-DD.")
            
            # Update the transaction
            cursor.execute(
                """UPDATE transactions 
                   SET type = ?, amount = ?, category = ?, description = ?, date = ? 
                   WHERE id = ?""",
                (new_type, new_amount, new_category, new_description, new_date, transaction_id)
            )
            if not self.conn:
                conn.commit()
            print("\n✓ Transaction updated successfully!")
            
            # Check budget if the transaction is an expense
            if new_type == "expense":
                self.check_budget_limit(new_category, new_amount, new_date)
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def delete_transaction(self):
        """Delete an existing transaction."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== Delete Transaction ===")
        
        # First, display recent transactions
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT id, type, amount, category, description, date 
                   FROM transactions 
                   WHERE user_id = ? 
                   ORDER BY date DESC LIMIT 10""",
                (self.current_user["id"],)
            )
            transactions = cursor.fetchall()
            
            if not transactions:
                print("No transactions found.")
                return
            
            # Display transactions
            headers = ["ID", "Type", "Amount", "Category", "Description", "Date"]
            table_data = []
            
            for t in transactions:
                # Format amount with currency symbol based on transaction type
                if t["type"] == "income":
                    amount = f"+${t['amount']:.2f}"
                else:
                    amount = f"-${t['amount']:.2f}"
                    
                table_data.append([
                    t["id"],
                    t["type"].title(),
                    amount,
                    t["category"],
                    t["description"] if t["description"] else "-",
                    t["date"]
                ])
            
            print("\nRecent Transactions:")
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            
            # Get transaction ID to delete
            while True:
                try:
                    transaction_id = int(input("\nEnter ID of transaction to delete (0 to cancel): "))
                    if transaction_id == 0:
                        return
                    
                    # Check if transaction exists and belongs to current user
                    cursor.execute(
                        "SELECT id FROM transactions WHERE id = ? AND user_id = ?",
                        (transaction_id, self.current_user["id"])
                    )
                    if not cursor.fetchone():
                        print("Transaction not found or you don't have permission to delete it.")
                        continue
                    break
                except ValueError:
                    print("Please enter a valid ID.")
            
            # Confirm deletion
            confirm = input(f"Are you sure you want to delete transaction #{transaction_id}? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Deletion cancelled.")
                return
            
            # Delete the transaction
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            if not self.conn:
                conn.commit()
            print("\n✓ Transaction deleted successfully!")
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def set_budget(self):
        """Set or update budget for a category."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== Set Budget ===")
        
        # Get month and year
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        while True:
            try:
                month_input = input(f"Month (1-12, leave empty for current month {current_month}): ").strip()
                month = int(month_input) if month_input else current_month
                
                if not 1 <= month <= 12:
                    print("Month must be between 1 and 12.")
                    continue
                
                year_input = input(f"Year (leave empty for current year {current_year}): ").strip()
                year = int(year_input) if year_input else current_year
                
                if year < 2000 or year > 2100:
                    print("Please enter a valid year between 2000 and 2100.")
                    continue
                
                break
            except ValueError:
                print("Please enter a valid number.")
        
        # Show expense categories
        categories = self.get_categories("expense")
        print("\nExpense Categories:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")
        print(f"{len(categories) + 1}. Other (create new)")
        
        # Get category
        while True:
            try:
                choice = int(input("\nSelect category number: "))
                if 1 <= choice <= len(categories):
                    category = categories[choice - 1]
                    break
                elif choice == len(categories) + 1:
                    category = input("Enter new category name: ").strip().title()
                    if not category:
                        print("Category cannot be empty.")
                        continue
                    break
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Please enter a number.")
        
        # Get budget amount
        while True:
            try:
                amount = float(input(f"Budget amount for {category} (${month}/{year}): $").strip())
                if amount <= 0:
                    print("Budget amount must be greater than zero.")
                    continue
                break
            except ValueError:
                print("Invalid amount. Please enter a number.")
        
        # Set or update budget in database
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT OR REPLACE INTO budgets 
                   (user_id, category, amount, month, year) 
                   VALUES (?, ?, ?, ?, ?)""",
                (self.current_user["id"], category, amount, month, year)
            )
            if not self.conn:
                conn.commit()
            print(f"\n✓ Budget for {category} (${month}/{year}) set to ${amount:.2f}")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def check_budget_limit(self, category, amount, date_str):
        """Check if a transaction exceeds the budget limit."""
        if not self.current_user:
            return
            
        # Parse transaction date
        date = datetime.strptime(date_str, "%Y-%m-%d")
        month = date.month
        year = date.year
        
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # Get budget for the category and month/year
            cursor.execute(
                """SELECT amount FROM budgets 
                   WHERE user_id = ? AND category = ? AND month = ? AND year = ?""",
                (self.current_user["id"], category, month, year)
            )
            budget = cursor.fetchone()
            
            if not budget:
                return  # No budget set for this category
            
            budget_amount = budget[0]
            
            # Calculate total spent in this category for the month
            cursor.execute(
                """SELECT SUM(amount) FROM transactions 
                   WHERE user_id = ? AND type = 'expense' AND category = ? 
                   AND strftime('%m', date) = ? AND strftime('%Y', date) = ?""",
                (self.current_user["id"], category, f"{month:02d}", str(year))
            )
            
            total_spent = cursor.fetchone()[0] or 0
            
            # Check if budget is exceeded
            if total_spent > budget_amount:
                print(f"\n⚠️ Warning: You have exceeded your budget for {category} in {month}/{year}!")
                print(f"Budget: ${budget_amount:.2f}")
                print(f"Spent: ${total_spent:.2f}")
                print(f"Over budget by: ${(total_spent - budget_amount):.2f}")
            elif total_spent >= budget_amount * 0.8:
                remaining = budget_amount - total_spent
                print(f"\n⚠️ Warning: You are approaching your budget limit for {category} in {month}/{year}!")
                print(f"Budget: ${budget_amount:.2f}")
                print(f"Spent: ${total_spent:.2f}")
                print(f"Remaining: ${remaining:.2f} ({(remaining/budget_amount)*100:.1f}% left)")
        except sqlite3.Error as e:
            print(f"Database error when checking budget: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def view_budgets(self):
        """View all budgets for the current user."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== View Budgets ===")
        
        # Get month and year filter
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        while True:
            try:
                month_input = input(f"Month (1-12, leave empty for current month {current_month}): ").strip()
                month = int(month_input) if month_input else current_month
                
                if not 1 <= month <= 12:
                    print("Month must be between 1 and 12.")
                    continue
                
                year_input = input(f"Year (leave empty for current year {current_year}): ").strip()
                year = int(year_input) if year_input else current_year
                
                if year < 2000 or year > 2100:
                    print("Please enter a valid year between 2000 and 2100.")
                    continue
                
                break
            except ValueError:
                print("Please enter a valid number.")
        
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get all budgets for the month/year
            cursor.execute(
                """SELECT category, amount FROM budgets 
                   WHERE user_id = ? AND month = ? AND year = ?""",
                (self.current_user["id"], month, year)
            )
            budgets = cursor.fetchall()
            
            if not budgets:
                print(f"No budgets found for {month}/{year}.")
                return
            
            # Get actual spending for each budget category
            spending_data = {}
            for budget in budgets:
                category = budget["category"]
                
                cursor.execute(
                    """SELECT COALESCE(SUM(amount), 0) as total FROM transactions 
                       WHERE user_id = ? AND type = 'expense' AND category = ? 
                       AND strftime('%m', date) = ? AND strftime('%Y', date) = ?""",
                    (self.current_user["id"], category, f"{month:02d}", str(year))
                )
                
                total_spent = cursor.fetchone()[0] or 0
                spending_data[category] = total_spent
            
            # Display budget information
            headers = ["Category", "Budget", "Spent", "Remaining", "Progress"]
            table_data = []
            
            for budget in budgets:
                category = budget["category"]
                budget_amount = budget["amount"]
                spent = spending_data.get(category, 0)
                remaining = budget_amount - spent
                
                # Calculate percentage and create progress bar
                if budget_amount > 0:
                    percentage = (spent / budget_amount) * 100
                    if percentage > 100:
                        progress = "🔴 {:5.1f}% (OVER!)".format(percentage)
                    elif percentage >= 80:
                        progress = "🟠 {:5.1f}%".format(percentage)
                    else:
                        progress = "🟢 {:5.1f}%".format(percentage)
                else:
                    progress = "N/A"
                
                table_data.append([
                    category,
                    f"${budget_amount:.2f}",
                    f"${spent:.2f}",
                    f"${remaining:.2f}",
                    progress
                ])
            
            # Sort by percentage spent (descending)
            table_data.sort(key=lambda x: float(x[2].replace('$', '')), reverse=True)
            
            # Display budgets
            print(f"\nBudgets for {month}/{year}:")
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            
            # Show summary
            total_budget = sum(b["amount"] for b in budgets)
            total_spent = sum(spending_data.values())
            total_remaining = total_budget - total_spent
            
            print(f"\nSummary:")
            print(f"Total Budget: ${total_budget:.2f}")
            print(f"Total Spent: ${total_spent:.2f}")
            print(f"Total Remaining: ${total_remaining:.2f}")
            if total_budget > 0:
                print(f"Overall Progress: {(total_spent / total_budget) * 100:.1f}%")
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def generate_report(self):
        """Generate financial reports for the user."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== Generate Financial Report ===")
        print("1. Monthly Report")
        print("2. Yearly Report")
        print("3. Category Breakdown")
        print("4. Income vs Expense Trend")
        
        choice = input("\nSelect report type (1-4): ").strip()
        
        if choice == "1":
            self._generate_monthly_report()
        elif choice == "2":
            self._generate_yearly_report()
        elif choice == "3":
            self._generate_category_breakdown()
        elif choice == "4":
            self._generate_trend_report()
        else:
            print("Invalid choice.")
    
    def backup_data(self):
        """Create a backup of the database."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== Backup Data ===")
        
        # Create backup directory if it doesn't exist
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/finance_backup_{self.current_user['username']}_{timestamp}.db"
        
        try:
            # Connect to existing database
            conn = self.conn if self.conn else sqlite3.connect(self.db_file)
            
            # Back up the database
            with open(backup_file, 'wb') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n'.encode('utf-8'))
            
            if not self.conn:
                conn.close()
            print(f"\n✓ Backup created successfully: {backup_file}")
            
        except Exception as e:
            print(f"Error creating backup: {e}")
    
    def restore_data(self):
        """Restore data from a backup file."""
        if not self.current_user:
            print("Please log in first.")
            return
            
        print("\n=== Restore Data ===")
        
        # Check if backup directory exists
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            print("No backups found.")
            return
        
        # List available backups for the current user
        backups = [f for f in os.listdir(backup_dir) if f.startswith(f"finance_backup_{self.current_user['username']}_")]
        
        if not backups:
            print(f"No backups found for {self.current_user['username']}.")
            return
        
        # Display available backups
        print("\nAvailable backups:")
        for i, backup in enumerate(backups, 1):
            # Extract timestamp from filename
            timestamp = backup.split('_')[-1].split('.')[0]
            try:
                backup_time = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                backup_time = "Unknown date"
                
            print(f"{i}. {backup} ({backup_time})")
        
        # Get user selection
        while True:
            try:
                choice = int(input("\nSelect backup to restore (0 to cancel): "))
                if choice == 0:
                    return
                if 1 <= choice <= len(backups):
                    selected_backup = f"{backup_dir}/{backups[choice-1]}"
                    break
                print("Invalid choice.")
            except ValueError:
                print("Please enter a number.")
        
        # Confirm restoration
        confirm = input(f"\n⚠️ Warning: This will replace your current data with the backup.\nAre you sure? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Restoration cancelled.")
            return
        
        try:
            # Close current database connection
            if not self.conn:
                conn = sqlite3.connect(self.db_file)
                conn.close()
            
            # Create a temporary database file
            temp_db = f"temp_restore_{timestamp}.db"
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Read and execute SQL commands from backup file
            with open(selected_backup, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                cursor.executescript(sql_script)
            
            conn.commit()
            conn.close()
            
            # Replace the current database with the restored one
            os.remove(self.db_file)
            os.rename(temp_db, self.db_file)
            
            print(f"\n✓ Database restored successfully from {selected_backup}")
            
        except Exception as e:
            print(f"Error restoring backup: {e}")
            if os.path.exists(temp_db):
                os.remove(temp_db)
    
    def _generate_monthly_report(self):
        """Generate a monthly financial report."""
        # Get month and year
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        while True:
            try:
                month_input = input(f"Month (1-12, leave empty for current month {current_month}): ").strip()
                month = int(month_input) if month_input else current_month
                
                if not 1 <= month <= 12:
                    print("Month must be between 1 and 12.")
                    continue
                
                year_input = input(f"Year (leave empty for current year {current_year}): ").strip()
                year = int(year_input) if year_input else current_year
                
                if year < 2000 or year > 2100:
                    print("Please enter a valid year between 2000 and 2100.")
                    continue
                
                break
            except ValueError:
                print("Please enter a valid number.")
        
        month_name = datetime(year, month, 1).strftime("%B")
        print(f"\n=== Monthly Financial Report: {month_name} {year} ===")
        
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get all transactions for the month
            cursor.execute(
                """SELECT type, amount, category, date 
                   FROM transactions 
                   WHERE user_id = ? 
                   AND strftime('%m', date) = ? 
                   AND strftime('%Y', date) = ? 
                   ORDER BY date""",
                (self.current_user["id"], f"{month:02d}", str(year))
            )
            transactions = cursor.fetchall()
            
            if not transactions:
                print(f"No transactions found for {month_name} {year}.")
                return
            
            # Calculate summary statistics
            total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
            total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
            net_savings = total_income - total_expense
            
            # Group transactions by category
            income_by_category = {}
            expense_by_category = {}
            
            for t in transactions:
                if t["type"] == "income":
                    if t["category"] not in income_by_category:
                        income_by_category[t["category"]] = 0
                    income_by_category[t["category"]] += t["amount"]
                else:  # expense
                    if t["category"] not in expense_by_category:
                        expense_by_category[t["category"]] = 0
                    expense_by_category[t["category"]] += t["amount"]
            
            # Group transactions by day
            daily_income = {}
            daily_expense = {}
            
            for t in transactions:
                day = datetime.strptime(t["date"], "%Y-%m-%d").day
                if t["type"] == "income":
                    if day not in daily_income:
                        daily_income[day] = 0
                    daily_income[day] += t["amount"]
                else:  # expense
                    if day not in daily_expense:
                        daily_expense[day] = 0
                    daily_expense[day] += t["amount"]
            
            # Display summary
            print(f"\nSummary:")
            print(f"Total Income: ${total_income:.2f}")
            print(f"Total Expenses: ${total_expense:.2f}")
            print(f"Net Savings: ${net_savings:.2f}")
            
            if total_income > 0:
                savings_rate = (net_savings / total_income) * 100
                print(f"Savings Rate: {savings_rate:.1f}%")
            
            # Display income breakdown
            if income_by_category:
                print("\nIncome Breakdown:")
                income_table = []
                for category, amount in sorted(income_by_category.items(), key=lambda x: x[1], reverse=True):
                    percentage = (amount / total_income) * 100 if total_income > 0 else 0
                    income_table.append([category, f"${amount:.2f}", f"{percentage:.1f}%"])
                
                print(tabulate(income_table, headers=["Category", "Amount", "% of Income"], tablefmt="pretty"))
            
            # Display expense breakdown
            if expense_by_category:
                print("\nExpense Breakdown:")
                expense_table = []
                for category, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
                    percentage = (amount / total_expense) * 100 if total_expense > 0 else 0
                    expense_table.append([category, f"${amount:.2f}", f"{percentage:.1f}%"])
                
                print(tabulate(expense_table, headers=["Category", "Amount", "% of Expenses"], tablefmt="pretty"))
            
            # Check against budgets
            cursor.execute(
                """SELECT category, amount FROM budgets 
                   WHERE user_id = ? AND month = ? AND year = ?""",
                (self.current_user["id"], month, year)
            )
            budgets = cursor.fetchall()
            
            if budgets:
                print("\nBudget Performance:")
                budget_table = []
                
                for budget in budgets:
                    category = budget["category"]
                    budget_amount = budget["amount"]
                    spent = expense_by_category.get(category, 0)
                    remaining = budget_amount - spent
                    
                    if budget_amount > 0:
                        percentage = (spent / budget_amount) * 100
                        status = "🔴 OVER" if percentage > 100 else "🟠 CLOSE" if percentage >= 80 else "🟢 OK"
                    else:
                        percentage = 0
                        status = "N/A"
                    
                    budget_table.append([
                        category,
                        f"${budget_amount:.2f}",
                        f"${spent:.2f}",
                        f"${remaining:.2f}",
                        f"{percentage:.1f}%",
                        status
                    ])
                
                print(tabulate(
                    budget_table, 
                    headers=["Category", "Budget", "Spent", "Remaining", "Used", "Status"], 
                    tablefmt="pretty"
                ))
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def _generate_yearly_report(self):
        """Generate a yearly financial report."""
        # Get year
        current_year = datetime.now().year
        
        while True:
            try:
                year_input = input(f"Year (leave empty for current year {current_year}): ").strip()
                year = int(year_input) if year_input else current_year
                
                if year < 2000 or year > 2100:
                    print("Please enter a valid year between 2000 and 2100.")
                    continue
                
                break
            except ValueError:
                print("Please enter a valid number.")
        
        print(f"\n=== Yearly Financial Report: {year} ===")
        
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get all transactions for the year
            cursor.execute(
                """SELECT type, amount, category, strftime('%m', date) as month 
                   FROM transactions 
                   WHERE user_id = ? AND strftime('%Y', date) = ? 
                   ORDER BY date""",
                (self.current_user["id"], str(year))
            )
            transactions = cursor.fetchall()
            
            if not transactions:
                print(f"No transactions found for {year}.")
                return
            
            # Calculate summary statistics
            total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
            total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")
            net_savings = total_income - total_expense
            
            # Group transactions by month
            monthly_income = {str(i).zfill(2): 0 for i in range(1, 13)}
            monthly_expense = {str(i).zfill(2): 0 for i in range(1, 13)}
            
            for t in transactions:
                month = t["month"]
                if t["type"] == "income":
                    monthly_income[month] += t["amount"]
                else:  # expense
                    monthly_expense[month] += t["amount"]
            
            # Group transactions by category
            income_by_category = {}
            expense_by_category = {}
            
            for t in transactions:
                if t["type"] == "income":
                    if t["category"] not in income_by_category:
                        income_by_category[t["category"]] = 0
                    income_by_category[t["category"]] += t["amount"]
                else:  # expense
                    if t["category"] not in expense_by_category:
                        expense_by_category[t["category"]] = 0
                    expense_by_category[t["category"]] += t["amount"]
            
            # Display summary
            print(f"\nSummary for {year}:")
            print(f"Total Income: ${total_income:.2f}")
            print(f"Total Expenses: ${total_expense:.2f}")
            print(f"Net Savings: ${net_savings:.2f}")
            
            if total_income > 0:
                savings_rate = (net_savings / total_income) * 100
                print(f"Savings Rate: {savings_rate:.1f}%")
                
            # Monthly breakdown
            print("\nMonthly Breakdown:")
            month_names = [datetime(year, i, 1).strftime("%b") for i in range(1, 13)]
            monthly_table = []
            
            for i, month in enumerate(range(1, 13)):
                month_str = str(month).zfill(2)
                income = monthly_income[month_str]
                expense = monthly_expense[month_str]
                net = income - expense
                
                if income > 0 or expense > 0:
                    savings_rate = (net / income) * 100 if income > 0 else 0
                    monthly_table.append([
                        month_names[i],
                        f"${income:.2f}",
                        f"${expense:.2f}",
                        f"${net:.2f}",
                        f"{savings_rate:.1f}%" if income > 0 else "N/A"
                    ])
            
            print(tabulate(
                monthly_table, 
                headers=["Month", "Income", "Expenses", "Net Savings", "Savings Rate"], 
                tablefmt="pretty"
            ))
            
            # Top income sources
            if income_by_category:
                print("\nTop Income Sources:")
                income_table = []
                for category, amount in sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)[:5]:
                    percentage = (amount / total_income) * 100
                    income_table.append([category, f"${amount:.2f}", f"{percentage:.1f}%"])
                
                print(tabulate(income_table, headers=["Category", "Amount", "% of Income"], tablefmt="pretty"))
            
            # Top expense categories
            if expense_by_category:
                print("\nTop Expense Categories:")
                expense_table = []
                for category, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)[:5]:
                    percentage = (amount / total_expense) * 100
                    expense_table.append([category, f"${amount:.2f}", f"{percentage:.1f}%"])
                
                print(tabulate(expense_table, headers=["Category", "Amount", "% of Expenses"], tablefmt="pretty"))
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def _generate_category_breakdown(self):
        """Generate a report breaking down transactions by category."""
        print("\n=== Category Breakdown Report ===")
        
        # Get date range
        while True:
            try:
                start_date = input("Start date (YYYY-MM-DD): ").strip()
                if not start_date:
                    print("Start date is required.")
                    continue
                    
                datetime.strptime(start_date, "%Y-%m-%d")  # Validate format
                
                end_date = input("End date (YYYY-MM-DD, leave empty for today): ").strip()
                if not end_date:
                    end_date = datetime.now().strftime("%Y-%m-%d")
                else:
                    datetime.strptime(end_date, "%Y-%m-%d")  # Validate format
                
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD.")
        
        # Get transaction type
        while True:
            transaction_type = input("Transaction type (income/expense/both): ").strip().lower()
            if transaction_type in ["income", "expense", "both"]:
                break
            print("Invalid type. Please enter 'income', 'expense', or 'both'.")
        
        conn = self.conn if self.conn else sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Build query based on filters
            query = """SELECT type, category, SUM(amount) as total 
                       FROM transactions 
                       WHERE user_id = ? AND date BETWEEN ? AND ?"""
            params = [self.current_user["id"], start_date, end_date]
            
            if transaction_type != "both":
                query += " AND type = ?"
                params.append(transaction_type)
            
            query += " GROUP BY type, category ORDER BY type, total DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                print(f"No transactions found for the selected period and filters.")
                return
            
            # Display results
            income_categories = []
            expense_categories = []
            
            for result in results:
                if result["type"] == "income":
                    income_categories.append([result["category"], f"${result['total']:.2f}"])
                else:  # expense
                    expense_categories.append([result["category"], f"${result['total']:.2f}"])
            
            # Calculate totals
            income_total = sum(float(row[1].replace('$', '')) for row in income_categories)
            expense_total = sum(float(row[1].replace('$', '')) for row in expense_categories)
            
            # Display income categories
            if income_categories and (transaction_type == "income" or transaction_type == "both"):
                print(f"\nIncome Categories ({start_date} to {end_date}):")
                for i, (category, amount) in enumerate(income_categories):
                    # Add percentage to income categories
                    amount_value = float(amount.replace('$', ''))
                    percentage = (amount_value / income_total) * 100 if income_total > 0 else 0
                    income_categories[i].append(f"{percentage:.1f}%")
                
                print(tabulate(income_categories, headers=["Category", "Amount", "% of Total"], tablefmt="pretty"))
                print(f"Total Income: ${income_total:.2f}")
            
            # Display expense categories
            if expense_categories and (transaction_type == "expense" or transaction_type == "both"):
                print(f"\nExpense Categories ({start_date} to {end_date}):")
                for i, (category, amount) in enumerate(expense_categories):
                    # Add percentage to expense categories
                    amount_value = float(amount.replace('$', ''))
                    percentage = (amount_value / expense_total) * 100 if expense_total > 0 else 0
                    expense_categories[i].append(f"{percentage:.1f}%")
                
                print(tabulate(expense_categories, headers=["Category", "Amount", "% of Total"], tablefmt="pretty"))
                print(f"Total Expenses: ${expense_total:.2f}")
            
            # Show summary if both types are displayed
            if transaction_type == "both" and income_categories and expense_categories:
                net_savings = income_total - expense_total
                savings_rate = (net_savings / income_total) * 100 if income_total > 0 else 0
                
                print(f"\nSummary:")
                print(f"Total Income: ${income_total:.2f}")
                print(f"Total Expenses: ${expense_total:.2f}")
                print(f"Net Savings: ${net_savings:.2f}")
                print(f"Savings Rate: {savings_rate:.1f}%")
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if not self.conn:
                conn.close()
    
    def _generate_trend_report(self):
        """Generate a trend report for income vs expenses over time."""
        print("\n=== Income vs Expense Trend Report ===")
        
        # Get period type
        print("Select period:")
        print("1. Monthly trend (for a year)")
        print("2. Daily trend (for a month)")
        
        period_choice = input("Select option (1-2): ").strip()
        
        if period_choice == "1":
            # Monthly trend report
            current_year = datetime.now().year
            
            while True:
                try:
                    year_input = input(f"Year (leave empty for current year {current_year}): ").strip()
                    year = int(year_input) if year_input else current_year
                    
                    if year < 2000 or year > 2100:
                        print("Please enter a valid year between 2000 and 2100.")
                        continue
                    
                    break
                except ValueError:
                    print("Please enter a valid number.")
            
            conn = self.conn if self.conn else sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                # Get monthly income and expenses for the year
                cursor.execute(
                    """SELECT 
                        strftime('%m', date) as month,
                        type,
                        SUM(amount) as total
                       FROM transactions 
                       WHERE user_id = ? AND strftime('%Y', date) = ? 
                       GROUP BY month, type
                       ORDER BY month""",
                    (self.current_user["id"], str(year))
                )
                results = cursor.fetchall()
                
                if not results:
                    print(f"No transactions found for {year}.")
                    return
                
                # Process results
                monthly_data = {str(i).zfill(2): {"income": 0, "expense": 0} for i in range(1, 13)}
                
                for result in results:
                    month = result["month"]
                    transaction_type = result["type"]
                    total = result["total"]
                    
                    if month in monthly_data:
                        monthly_data[month][transaction_type] = total
                
                # Prepare table data
                month_names = [datetime(year, i, 1).strftime("%b") for i in range(1, 13)]
                trend_table = []
                
                for i, month in enumerate(range(1, 13)):
                    month_str = str(month).zfill(2)
                    data = monthly_data[month_str]
                    income = data["income"]
                    expense = data["expense"]
                    net = income - expense
                    
                    # Only include months with data
                    if income > 0 or expense > 0:
                        savings_rate = (net / income) * 100 if income > 0 else 0
                        trend = "↑" if net > 0 else "↓" if net < 0 else "→"
                        
                        trend_table.append([
                            month_names[i],
                            f"${income:.2f}",
                            f"${expense:.2f}",
                            f"${net:.2f}",
                            f"{savings_rate:.1f}%",
                            trend
                        ])
                
                print(f"\nMonthly Trend for {year}:")
                print(tabulate(
                    trend_table, 
                    headers=["Month", "Income", "Expenses", "Net", "Savings Rate", "Trend"], 
                    tablefmt="pretty"
                ))
                
                # Calculate averages
                months_with_data = len(trend_table)
                if months_with_data > 0:
                    avg_income = sum(float(row[1].replace('$', '')) for row in trend_table) / months_with_data
                    avg_expense = sum(float(row[2].replace('$', '')) for row in trend_table) / months_with_data
                    avg_net = sum(float(row[3].replace('$', '')) for row in trend_table) / months_with_data
                    
                    print(f"\nAverages:")
                    print(f"Average Monthly Income: ${avg_income:.2f}")
                    print(f"Average Monthly Expenses: ${avg_expense:.2f}")
                    print(f"Average Monthly Net: ${avg_net:.2f}")
            
            except sqlite3.Error as e:
                print(f"Database error: {e}")
            finally:
                if not self.conn:
                    conn.close()
                
        elif period_choice == "2":
            # Daily trend report for a month
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            while True:
                try:
                    month_input = input(f"Month (1-12, leave empty for current month {current_month}): ").strip()
                    month = int(month_input) if month_input else current_month
                    
                    if not 1 <= month <= 12:
                        print("Month must be between 1 and 12.")
                        continue
                    
                    year_input = input(f"Year (leave empty for current year {current_year}): ").strip()
                    year = int(year_input) if year_input else current_year
                    
                    if year < 2000 or year > 2100:
                        print("Please enter a valid year between 2000 and 2100.")
                        continue
                    
                    break
                except ValueError:
                    print("Please enter a valid number.")
            
            month_name = datetime(year, month, 1).strftime("%B")
            
            conn = self.conn if self.conn else sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                # Get daily income and expenses for the month
                cursor.execute(
                    """SELECT 
                        strftime('%d', date) as day,
                        type,
                        SUM(amount) as total
                       FROM transactions 
                       WHERE user_id = ? 
                       AND strftime('%m', date) = ? 
                       AND strftime('%Y', date) = ? 
                       GROUP BY day, type
                       ORDER BY day""",
                    (self.current_user["id"], f"{month:02d}", str(year))
                )
                results = cursor.fetchall()
                
                if not results:
                    print(f"No transactions found for {month_name} {year}.")
                    return
                
                # Get days in month
                days_in_month = (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day if month < 12 else 31
                
                # Process results
                daily_data = {str(i).zfill(2): {"income": 0, "expense": 0} for i in range(1, days_in_month + 1)}
                
                for result in results:
                    day = result["day"]
                    transaction_type = result["type"]
                    total = result["total"]
                    
                    if day in daily_data:
                        daily_data[day][transaction_type] = total
                
                # Prepare table data
                trend_table = []
                
                for day in range(1, days_in_month + 1):
                    day_str = str(day).zfill(2)
                    data = daily_data[day_str]
                    income = data["income"]
                    expense = data["expense"]
                    
                    # Only include days with data
                    if income > 0 or expense > 0:
                        net = income - expense
                        trend = "↑" if net > 0 else "↓" if net < 0 else "→"
                        
                        trend_table.append([
                            day,
                            f"${income:.2f}",
                            f"${expense:.2f}",
                            f"${net:.2f}",
                            trend
                        ])
                
                print(f"\nDaily Trend for {month_name} {year}:")
                print(tabulate(
                    trend_table, 
                    headers=["Day", "Income", "Expenses", "Net", "Trend"], 
                    tablefmt="pretty"
                ))
                
                # Calculate totals and averages
                days_with_data = len(trend_table)
                if days_with_data > 0:
                    total_income = sum(float(row[1].replace('$', '')) for row in trend_table)
                    total_expense = sum(float(row[2].replace('$', '')) for row in trend_table)
                    total_net = total_income - total_expense
                    
                    avg_income = total_income / days_with_data
                    avg_expense = total_expense / days_with_data
                    avg_net = total_net / days_with_data
                    
                    print(f"\nSummary:")
                    print(f"Total Income: ${total_income:.2f}")
                    print(f"Total Expenses: ${total_expense:.2f}")
                    print(f"Net: ${total_net:.2f}")
                    
                    print(f"\nDaily Averages (for days with transactions):")
                    print(f"Average Daily Income: ${avg_income:.2f}")
                    print(f"Average Daily Expenses: ${avg_expense:.2f}")
                    print(f"Average Daily Net: ${avg_net:.2f}")
            
            except sqlite3.Error as e:
                print(f"Database error: {e}")
            finally:
                if not self.conn:
                    conn.close()
        
        else:
            print("Invalid choice.")
    def add_transaction_direct(self, user_id, transaction_type, amount, category, description, date):
     """Directly insert a transaction into the database (used for unit testing)."""
     conn = self.conn if self.conn else sqlite3.connect(self.db_file)
     cursor = conn.cursor()
     cursor.execute(
        """INSERT INTO transactions 
        (user_id, type, amount, category, description, date) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, transaction_type, amount, category, description, date)
     )
     if not self.conn:
        conn.commit()
     if not self.conn:
        conn.close()
    def _register_test_user(self, username="testuser", password="testpass"):
     """Register a user directly for testing."""
     cursor = self.conn.cursor()
     password_hash = self.hash_password(password)
     cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
     self.conn.commit()
     self.current_user = {"id": cursor.lastrowid, "username": username}

    def _add_transaction_for_test(self, transaction_type, amount, category, description="", date=None):
     """Add a transaction directly to the DB."""
     if not date:
        date = datetime.now().strftime("%Y-%m-%d")
     cursor = self.conn.cursor()
     cursor.execute(
        """INSERT INTO transactions (user_id, type, amount, category, description, date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (self.current_user["id"], transaction_type, amount, category, description, date)
    )
     self.conn.commit()


def main():
    pfm = PersonalFinanceManager()
    while True:
        if not pfm.current_user:
            print("\nPersonal Finance Manager")
            print("1. Register")
            print("2. Login")
            print("3. Exit")
            choice = input("Choose an option: ").strip()
            
            if choice == "1":
                pfm.register_user()
            elif choice == "2":
                pfm.login()
            elif choice == "3":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
        else:
            print(f"\nWelcome, {pfm.current_user['username']}!")
            print("1. Add Transaction")
            print("2. View Transactions")
            print("3. Edit Transaction")
            print("4. Delete Transaction")
            print("5. Set Budget")
            print("6. View Budgets")
            print("7. Generate Report")
            print("8. Backup Data")
            print("9. Restore Data")
            print("10. Logout")
            choice = input("Choose an option: ").strip()
            
            if choice == "1":
                pfm.add_transaction()
            elif choice == "2":
                pfm.view_transactions()
            elif choice == "3":
                pfm.edit_transaction()
            elif choice == "4":
                pfm.delete_transaction()
            elif choice == "5":
                pfm.set_budget()
            elif choice == "6":
                pfm.view_budgets()
            elif choice == "7":
                pfm.generate_report()
            elif choice == "8":
                pfm.backup_data()
            elif choice == "9":
                pfm.restore_data()
            elif choice == "10":
                pfm.logout()
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()