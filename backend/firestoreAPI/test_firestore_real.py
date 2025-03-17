import unittest
from datetime import datetime
from firestore_module import (
    initializeDoc, getUserDocument, update_user_field,
    addTask, modifyTask, deleteTask, updateGoals
)

class TestTimelyAIFirestoreRealDB(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Setup a test user in Firestore before running tests."""
        cls.test_user = f"test_user_{int(datetime.utcnow().timestamp())}"
        initializeDoc(cls.test_user)

    # @classmethod
    # def tearDownClass(cls):
    #     """Clean up Firestore by deleting the test user document."""
    #     from firebase_admin import firestore
    #     db = firestore.client()
    #     db.collection("users").document(cls.test_user).delete()

    def test_initializeDoc(self):
        """Check if user document is created in Firestore."""
        data = getUserDocument(self.test_user)
        self.assertIsNotNone(data)
        self.assertIn("userPref", data)
        self.assertIn("Tasks", data)

    def test_update_user_field(self):
        """Check if a specific user field can be updated."""
        result = update_user_field(self.test_user, "testField", "testValue")
        self.assertTrue(result)
        
        updated_data = getUserDocument(self.test_user)
        self.assertEqual(updated_data.get("testField"), "testValue")

    def test_addTask(self):
        """Check if a task can be added to Firestore."""
        task_id = addTask(self.test_user, {"name": "Real Task"})
        self.assertIsInstance(task_id, str)
        
        updated_data = getUserDocument(self.test_user)
        self.assertIn(task_id, updated_data.get("Tasks", {}))

    def test_modifyTask(self):
        """Check if a task can be modified."""
        task_id = addTask(self.test_user, {"name": "Temporary Task"})
        result = modifyTask(self.test_user, task_id, {"name": "Updated Task"})
        self.assertTrue(result)

        updated_data = getUserDocument(self.test_user)
        self.assertEqual(updated_data["Tasks"][task_id]["name"], "Updated Task")

    def test_deleteTask(self):
        """Check if a task can be deleted."""
        task_id = addTask(self.test_user, {"name": "To Be Deleted"})
        result = deleteTask(self.test_user, task_id)
        self.assertTrue(result)

        updated_data = getUserDocument(self.test_user)
        self.assertNotIn(task_id, updated_data.get("Tasks", {}))

    def test_updateGoals(self):
        """Check if user goals can be updated."""
        result = updateGoals(self.test_user, "Exercise", "Run", 40)
        self.assertTrue(result)

        updated_data = getUserDocument(self.test_user)
        self.assertEqual(updated_data["userPref"]["goals"]["Exercise"]["Run"], 40)

if __name__ == "__main__":
    unittest.main()
