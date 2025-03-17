import unittest
from unittest.mock import patch, MagicMock
from firestore_module import (
    initializeDoc, getUserDocument, update_user_field,
    addTask, modifyTask, deleteTask, updateGoals
)

class TestTimelyAIFirestore(unittest.TestCase):
    
    @patch("firestore_module.db.collection")
    def test_initializeDoc(self, mock_collection):
        mock_doc_ref = mock_collection.return_value.document.return_value
        mock_doc_ref.get.return_value.exists = False
        
        data = initializeDoc("test_user")
        self.assertIn("userPref", data)
        self.assertIn("Tasks", data)
        self.assertIn("createdAt", data)

    @patch("firestore_module.db.collection")
    def test_getUserDocument(self, mock_collection):
        mock_doc_ref = mock_collection.return_value.document.return_value
        mock_doc_ref.get.return_value.exists = True
        mock_doc_ref.get.return_value.to_dict.return_value = {"test": "data"}
        
        data = getUserDocument("test_user")
        self.assertEqual(data, {"test": "data"})

    @patch("firestore_module.db.collection")
    def test_update_user_field(self, mock_collection):
        mock_doc_ref = mock_collection.return_value.document.return_value
        mock_doc_ref.update = MagicMock()
        
        result = update_user_field("test_user", "testField", "testValue")
        mock_doc_ref.update.assert_called()
        self.assertTrue(result)

    @patch("firestore_module.db.collection")
    def test_addTask(self, mock_collection):
        mock_doc_ref = mock_collection.return_value.document.return_value
        mock_doc_ref.get.return_value.exists = True
        mock_doc_ref.get.return_value.to_dict.return_value = {"Tasks": {}}
        
        task_id = addTask("test_user", {"name": "Task 1"})
        self.assertIsInstance(task_id, str)

    @patch("firestore_module.db.collection")
    def test_modifyTask(self, mock_collection):
        mock_doc_ref = mock_collection.return_value.document.return_value
        mock_doc_ref.get.return_value.exists = True
        mock_doc_ref.get.return_value.to_dict.return_value = {"Tasks": {"task_1": {}}}
        
        result = modifyTask("test_user", "task_1", {"name": "Updated Task"})
        self.assertTrue(result)

    @patch("firestore_module.db.collection")
    def test_deleteTask(self, mock_collection):
        mock_doc_ref = mock_collection.return_value.document.return_value
        mock_doc_ref.get.return_value.exists = True
        mock_doc_ref.get.return_value.to_dict.return_value = {"Tasks": {"task_1": {}}}
        
        result = deleteTask("test_user", "task_1")
        self.assertTrue(result)

    @patch("firestore_module.db.collection")
    def test_updateGoals(self, mock_collection):
        mock_doc_ref = mock_collection.return_value.document.return_value
        mock_doc_ref.get.return_value.exists = True
        mock_doc_ref.get.return_value.to_dict.return_value = {"userPref": {"goals": {"Exercise": {"Run": 0}}}}
        
        result = updateGoals("test_user", "Exercise", "Run", 30)
        self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()
