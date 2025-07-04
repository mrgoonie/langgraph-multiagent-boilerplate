"""
Direct test script for testing the OpenRouter API integration in conversation endpoints.

This script performs simple HTTP requests to test both non-streaming and streaming chat endpoints.
For streaming requests, it handles Server-Sent Events (SSE) format properly.

To use:
1. Make sure the server is running (uvicorn app.main:app --reload)
2. Run this script: python test_openrouter_api.py
3. Check the output to verify the endpoints are working properly
"""
import requests
import json
import uuid
import time
import sseclient  # For handling Server-Sent Events
from pprint import pprint


def test_non_streaming_chat(conversation_id):
    """Test the non-streaming chat endpoint with OpenRouter integration"""
    print("\n=== Testing Non-Streaming Chat with OpenRouter API ===")
    
    url = f"http://localhost:8000/api/conversations/{conversation_id}/chat"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "message": "Hello! Give me a brief explanation of AI agents in 2 sentences."
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response:")
            pprint(result)
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


def test_streaming_chat(conversation_id):
    """Test the streaming chat endpoint with OpenRouter API integration"""
    print("\n=== Testing Streaming Chat with OpenRouter API ===")
    
    url = f"http://localhost:8000/api/conversations/{conversation_id}/chat/stream"
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    payload = {
        "message": "Please list 3 benefits of using AI agents in bullet points."
    }
    
    try:
        # Using stream=True to handle streaming responses
        response = requests.post(url, json=payload, headers=headers, stream=True)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Streaming response:")
            print("-------------------")
            
            # Create an SSE client from the response
            client = sseclient.SSEClient(response)
            
            # Process the streaming response
            content_so_far = ""
            for event in client.events():
                if event.data == "[DONE]":
                    break
                
                try:
                    data = json.loads(event.data)
                    if 'choices' in data and data['choices'][0].get('delta', {}).get('content'):
                        content = data['choices'][0]['delta']['content']
                        content_so_far += content
                        print(content, end='', flush=True)
                except json.JSONDecodeError:
                    pass
            
            print("\n-------------------")
            print(f"Complete response: {content_so_far}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


def create_test_conversation():
    """Create a test conversation to use for our tests"""
    print("\n=== Creating Test Conversation ===")
    
    url = "http://localhost:8000/api/conversations/"
    headers = {
        "Content-Type": "application/json"
    }
    
    # You'll need to update this with a valid crew ID from your database
    # For now, we're using a placeholder UUID
    payload = {
        "user_id": "test-user-" + str(uuid.uuid4())[:8],
        "crew_id": "a7e6fdb6-5114-41fa-92f6-e66f7956fa89",  # REPLACE WITH ACTUAL CREW ID
        "title": "OpenRouter API Test"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 201:
            result = response.json()
            conversation_id = result["id"]
            print(f"Created conversation with ID: {conversation_id}")
            return conversation_id
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
            # If we can't create a new conversation, use a hardcoded ID for testing
            # You should replace this with a known valid conversation ID
            fallback_id = input("Please enter a valid conversation ID to use: ")
            return fallback_id
    except Exception as e:
        print(f"Error: {str(e)}")
        fallback_id = input("Please enter a valid conversation ID to use: ")
        return fallback_id


def main():
    """Run the tests"""
    print("OpenRouter API Integration Test")
    print("==============================")
    print("This script will test both the non-streaming and streaming chat endpoints")
    print("to verify that the OpenRouter API integration is working correctly.")
    print("\nBefore running this test:")
    print("1. Make sure the server is running")
    print("2. Ensure you have a valid crew ID in the script")
    print("3. Verify that your .env file has a valid OPENROUTER_API_KEY")
    
    # Prompt for confirmation
    proceed = input("\nDo you want to proceed with the tests? (y/n): ")
    if proceed.lower() != 'y':
        print("Test aborted.")
        return
    
    # Create or get a conversation ID for testing
    conversation_id = create_test_conversation()
    
    # Test the non-streaming chat endpoint
    non_streaming_success = test_non_streaming_chat(conversation_id)
    
    # Test the streaming chat endpoint
    streaming_success = test_streaming_chat(conversation_id)
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Non-Streaming Chat: {'✅ PASSED' if non_streaming_success else '❌ FAILED'}")
    print(f"Streaming Chat: {'✅ PASSED' if streaming_success else '❌ FAILED'}")


if __name__ == "__main__":
    main()
