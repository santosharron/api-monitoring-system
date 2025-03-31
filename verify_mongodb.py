"""
Verify MongoDB connection script.
"""
import os
import sys
import pymongo

def verify_mongodb_connection():
    """Verify the MongoDB connection using the URI from environment variable."""
    mongodb_uri = os.environ.get("MONGODB_URI")
    
    if not mongodb_uri:
        print("ERROR: MONGODB_URI environment variable is not set")
        return False
    
    print(f"Testing connection to MongoDB using URI: {mongodb_uri[:20]}...{mongodb_uri[-10:]}")
    
    try:
        # Connect with a 5 second timeout
        client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        
        # Force a connection by requesting server info
        server_info = client.server_info()
        
        print(f"SUCCESS: Connected to MongoDB {server_info.get('version', '')}")
        print(f"Database name: {client.get_database().name}")
        return True
    
    except pymongo.errors.ServerSelectionTimeoutError as e:
        print(f"ERROR: Could not connect to MongoDB - Connection timed out")
        print(f"Details: {str(e)}")
        return False
    
    except pymongo.errors.OperationFailure as e:
        print(f"ERROR: Authentication failed - {str(e)}")
        return False
    
    except Exception as e:
        print(f"ERROR: Failed to connect to MongoDB: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    if verify_mongodb_connection():
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure 