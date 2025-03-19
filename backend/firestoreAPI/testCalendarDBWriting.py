import pandas as pd
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

def load_df_to_firestore(db, df, collection_name, user_id):
    """
    Load data from a pandas DataFrame and write it to Firestore
    mapping all events to a single user ID
    
    Args:
        df: pandas DataFrame containing calendar events
        collection_name: Name of the Firestore collection to write to
        user_id: ID of the user to associate with all events
    """
    # Print the first few rows of the DataFrame
    print("Preview of the DataFrame:")
    print(df.head())
    
    # Initialize Firebase Admin SDK
    # You need to replace the path with your own service account key
    if not firebase_admin._apps:
        cred = credentials.Certificate("firestore_credentials.json")
        firebase_admin.initialize_app(cred)
    
    # Get a reference to the Firestore database
    db = firestore.client()
    
    # Get a reference to the document that will store all events
    user_doc_ref = db.collection(collection_name).document(user_id)
    
    # Create a dictionary of all events with event_id as key
    events_dict = {}
    for _, row in df.iterrows():
        # Convert row to dictionary and handle NaN values
        row_dict = row.to_dict()
        for key, value in row_dict.items():
            if pd.isna(value):
                row_dict[key] = None
        
        # Use event_id as key in the events dictionary
        if 'event_id' in row:
            event_id = row['event_id']
        else:
            # Generate a unique ID if event_id is not present
            event_id = user_doc_ref.collection('temp').document().id
        
        events_dict[event_id] = row_dict
    
    # Write the entire events dictionary to Firestore
    print(f"Writing {len(events_dict)} events to Firestore document: {user_id}")
    
    # Check if the dictionary is too large for a single write (Firestore limit is 1MB)
    if len(str(events_dict)) > 900000:  # Using 900KB as a safe threshold
        print("Warning: Data exceeds recommended document size. Splitting into subcollection.")
        # Create a subcollection for events instead
        events_collection = user_doc_ref.collection("events")
        
        # Write each event as a separate document in the subcollection
        batch_size = 500
        batches = 0
        event_items = list(events_dict.items())
        
        for i in range(0, len(event_items), batch_size):
            batch = db.batch()
            items_slice = event_items[i:i+batch_size]
            
            for event_id, event_data in items_slice:
                doc_ref = events_collection.document(event_id)
                batch.set(doc_ref, event_data)
            
            # Commit the batch
            batch.commit()
            batches += 1
            print(f"Committed batch {batches}, records {i} to {min(i+batch_size, len(event_items))}")
    else:
        # Store all events in a field called "events" in the user document
        user_doc_ref.set({"events": events_dict})
        print("Successfully wrote events dictionary to Firestore")

if __name__ == "__main__":
    # Example usage:
    # Load the CSV file into a DataFrame
    csv_file_path = "example_calendar.csv"
    df = pd.read_csv(csv_file_path)
    
    # Set the name of the collection in Firestore
    collection_name = "UserCalendars"
    
    # Set the user ID to associate with these events
    user_id = "boss@cornell.edu"  # Use the ID from your screenshot
    
    # Load the DataFrame and write to Firestore
    load_df_to_firestore(df, collection_name, user_id)