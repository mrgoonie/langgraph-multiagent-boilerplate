"""
Manual test script for OpenRouter API integration in conversation endpoints.
This script makes direct HTTP requests to test the integration.
"""
import asyncio
import aiohttp
import json
import uuid
from pprint import pprint


async def test_non_streaming_chat(conversation_id):
    """Test the non-streaming chat endpoint"""
    print("\n=== Testing Non-Streaming Chat ===")
    
    url = f"http://localhost:8000/api/conversations/{conversation_id}/chat"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "message": "Hello! Give me a short 2-sentence answer about AI agents."
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Status: {response.status}")
                    print(f"Response:")
                    pprint(result)
                    return True
                else:
                    print(f"Error: {response.status}")
                    print(await response.text())
                    return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


async def test_streaming_chat(conversation_id):
    """Test the streaming chat endpoint"""
    print("\n=== Testing Streaming Chat ===")
    
    url = f"http://localhost:8000/api/conversations/{conversation_id}/chat/stream"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "message": "Please explain in 3 bullet points why AI agents are useful."
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    print(f"Status: {response.status}")
                    print("Streaming response:")
                    print("-------------------")
                    
                    # Process the streaming response
                    content_so_far = ""
                    async for chunk in response.content.iter_chunks():
                        chunk_data = chunk[0].decode('utf-8')
                        if chunk_data.startswith('data:') and 'content' in chunk_data:
                            try:
                                # Parse the SSE data format
                                data_str = chunk_data.replace('data: ', '', 1).strip()
                                if data_str and data_str != '[DONE]':
                                    data = json.loads(data_str)
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
                    print(f"Error: {response.status}")
                    print(await response.text())
                    return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


async def create_test_conversation():
    """Create a test conversation to use for our tests"""
    print("\n=== Creating Test Conversation ===")
    
    url = "http://localhost:8000/api/conversations/"
    headers = {
        "Content-Type": "application/json"
    }
    
    # You'll need to replace this with an actual crew ID from your database
    # For testing, you can use the UUID of any existing crew
    payload = {
        "user_id": "test-user-123",
        "crew_id": "a7e6fdb6-5114-41fa-92f6-e66f7956fa89", # Replace with real crew ID
        "title": "OpenRouter API Test"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 201:
                    result = await response.json()
                    conversation_id = result["id"]
                    print(f"Created conversation with ID: {conversation_id}")
                    return conversation_id
                else:
                    print(f"Error: {response.status}")
                    print(await response.text())
                    # If we can't create a new conversation, use a fallback UUID for testing
                    # Replace this with a known conversation ID from your database
                    return "a23e4567-e89b-12d3-a456-426614174001"
    except Exception as e:
        print(f"Error: {str(e)}")
        # Return fallback UUID
        return "a23e4567-e89b-12d3-a456-426614174001"


async def main():
    """Run the tests"""
    # Create or get a conversation ID for testing
    conversation_id = await create_test_conversation()
    
    # Test the non-streaming chat endpoint
    await test_non_streaming_chat(conversation_id)
    
    # Test the streaming chat endpoint
    await test_streaming_chat(conversation_id)


if __name__ == "__main__":
    asyncio.run(main())
