# firebase_test.py - Run this to test Firebase connection
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

FIREBASE_CREDENTIALS_PATH = r"D:\web\webathon_timetable\firebase_credentials.json"

def test_firebase_connection():
    try:
        # Test 1: Check if file exists
        print("Test 1: Checking if credentials file exists...")
        if not os.path.exists(FIREBASE_CREDENTIALS_PATH):
            print(f"❌ FAILED: File not found at {FIREBASE_CREDENTIALS_PATH}")
            return False
        print("✅ PASSED: Credentials file exists")
        
        # Test 2: Check if file is valid JSON
        print("\nTest 2: Validating JSON format...")
        try:
            with open(FIREBASE_CREDENTIALS_PATH, 'r') as f:
                creds_data = json.load(f)
            print("✅ PASSED: Valid JSON format")
        except json.JSONDecodeError as e:
            print(f"❌ FAILED: Invalid JSON - {e}")
            return False
        
        # Test 3: Check required fields
        print("\nTest 3: Checking required fields...")
        required_fields = ['private_key', 'client_email', 'project_id', 'type']
        missing_fields = [field for field in required_fields if field not in creds_data]
        if missing_fields:
            print(f"❌ FAILED: Missing fields - {missing_fields}")
            return False
        print("✅ PASSED: All required fields present")
        
        # Test 4: Initialize Firebase
        print("\nTest 4: Initializing Firebase...")
        if firebase_admin._apps:
            firebase_admin.delete_app(firebase_admin.get_app())
        
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        print("✅ PASSED: Firebase initialized")
        
        # Test 5: Get Firestore client
        print("\nTest 5: Getting Firestore client...")
        db = firestore.client()
        print("✅ PASSED: Firestore client created")
        
        # Test 6: Test database operation
        print("\nTest 6: Testing database write/read...")
        test_ref = db.collection('test').document('connection_test')
        test_ref.set({
            'message': 'Connection test successful',
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        doc = test_ref.get()
        if doc.exists:
            print("✅ PASSED: Database write/read successful")
            print(f"Test document data: {doc.to_dict()}")
        else:
            print("❌ FAILED: Could not read test document")
            return False
        
        print("\n🎉 ALL TESTS PASSED! Firebase connection is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_firebase_connection()