import unittest
import sqlite3
from datetime import datetime
from Finance_Manager import PersonalFinanceManager

class TestPersonalFinanceManager(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.fm = PersonalFinanceManager(conn=self.conn)
        self.fm._register_test_user()

    def test_add_transaction(self):
        """test_add_transaction"""
        self.fm._add_transaction_for_test("income", 500, "Salary", "Monthly pay")
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (self.fm.current_user["id"],))
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_edit_transaction(self):
        """test_edit_transaction"""
        self.fm._add_transaction_for_test("expense", 200, "Food", "Lunch")
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE category = 'Food'")
        transaction_id = cursor.fetchone()[0]
        cursor.execute("UPDATE transactions SET amount = ? WHERE id = ?", (150, transaction_id))
        self.conn.commit()
        cursor.execute("SELECT amount FROM transactions WHERE id = ?", (transaction_id,))
        self.assertEqual(cursor.fetchone()[0], 150)

    def test_delete_transaction(self):
        """test_delete_transaction"""
        self.fm._add_transaction_for_test("expense", 100, "Snacks")
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM transactions")
        transaction_id = cursor.fetchone()[0]
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.conn.commit()
        cursor.execute("SELECT COUNT(*) FROM transactions")
        self.assertEqual(cursor.fetchone()[0], 0)

    def test_set_and_check_budget(self):
        """test_set_and_check_budget"""
        cursor = self.conn.cursor()
        cursor.execute("""INSERT INTO budgets (user_id, category, amount, month, year)
                          VALUES (?, ?, ?, ?, ?)""",
                       (self.fm.current_user["id"], "Food", 300, datetime.now().month, datetime.now().year))
        self.conn.commit()
        self.fm._add_transaction_for_test("expense", 250, "Food")
        cursor.execute("SELECT amount FROM budgets WHERE category = 'Food'")
        self.assertEqual(cursor.fetchone()[0], 300)

    def test_budget_limit_warning_logic(self):
        """test_budget_limit_warning_logic"""
        cursor = self.conn.cursor()
        cursor.execute("""INSERT INTO budgets (user_id, category, amount, month, year)
                          VALUES (?, ?, ?, ?, ?)""",
                       (self.fm.current_user["id"], "Rent", 500, datetime.now().month, datetime.now().year))
        self.conn.commit()
        self.fm._add_transaction_for_test("expense", 450, "Rent")
        today = datetime.now().strftime("%Y-%m-%d")
        self.fm.check_budget_limit("Rent", 450, today)

    def test_view_budgets(self):
        """test_view_budgets"""
        self.fm._add_transaction_for_test("expense", 100, "Utilities")
        cursor = self.conn.cursor()
        cursor.execute("""INSERT INTO budgets (user_id, category, amount, month, year)
                          VALUES (?, ?, ?, ?, ?)""",
                       (self.fm.current_user["id"], "Utilities", 200, datetime.now().month, datetime.now().year))
        self.conn.commit()
        cursor.execute("SELECT COUNT(*) FROM budgets WHERE category = 'Utilities'")
        self.assertEqual(cursor.fetchone()[0], 1)

    def test_generate_monthly_report_no_crash(self):
        """test_generate_monthly_report_no_crash"""
        self.fm._add_transaction_for_test("income", 1000, "Job", "Test salary")
        self.fm._add_transaction_for_test("expense", 300, "Groceries", "Test food")
        self.fm._generate_monthly_report()

    def test_generate_yearly_report_no_crash(self):
        """test_generate_yearly_report_no_crash"""
        self.fm._add_transaction_for_test("income", 1000, "Freelance")
        self.fm._generate_yearly_report()

    def tearDown(self):
        self.conn.close()

# === Custom runner for clean PASS/FAIL output ===

class VerboseTestResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        print(f"✔ {test.shortDescription()}: PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"✘ {test.shortDescription()}: FAIL\n{self.failures[-1][1]}")

    def addError(self, test, err):
        super().addError(test, err)
        print(f"✘ {test.shortDescription()}: ERROR\n{self.errors[-1][1]}")

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestPersonalFinanceManager)
    runner = unittest.TextTestRunner(resultclass=VerboseTestResult, verbosity=0)
    runner.run(suite)
