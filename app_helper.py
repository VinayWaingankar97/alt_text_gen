import os
import base64
import time
import json
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

# Load environment variables or use defaults
endpoint = os.getenv("ENDPOINT_URL")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

# Price per 1000 tokens (adjust these based on your pricing tier)
INPUT_TOKEN_PRICE_PER_1K = 0.02  # Example price for input tokens
OUTPUT_TOKEN_PRICE_PER_1K = 0.08  # Example price for output tokens

def predict_single(image_path, user_context=None):
    """
    Generate alt text and metadata for a single image
    Args:
        image_path: Path to the image file
        user_context: Optional user-provided context for alt text generation
    Returns:
        dict: JSON dictionary with alt text and metadata
    """
    # Initialize Azure OpenAI Service client with key-based authentication
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2025-01-01-preview",
    )
    
    # Track start time
    start_time = time.time()
    
    # Encode the image file
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("ascii")
    except FileNotFoundError:
        raise Exception(f"Image file not found at path: {image_path}")
    except Exception as e:
        raise Exception(f"Error reading image file: {str(e)}")
    
    # Prepare the chat prompt
    # Default user prompt if no context is provided
    default_user_text = "Generate Alt Text for the following Image:"
    
    # Construct user content dynamically
    user_content = [
        {"type": "text", "text": default_user_text}
    ]
    
    # Add user-provided context if available
    if user_context and user_context.strip():
        user_content.append({"type": "text", "text": user_context})
    
    # Add image URL
    user_content.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{encoded_image}"
        }
    })
    
    # Prepare the complete chat prompt
    chat_prompt = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an AI assistant that helps people find information. Generate a detailed description of the image for alt text purposes. Respond with only the alt text description."
                }
            ]
        },
        {
            "role": "user",
            "content": user_content
        }
    ]
    
    # Call Azure OpenAI to generate alt text
    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_tokens=800,
        temperature=1,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stream=False,
        response_format={"type": "text"}
    )
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Extract token usage
    tokens_in = completion.usage.prompt_tokens
    tokens_out = completion.usage.completion_tokens
    tokens_total = completion.usage.total_tokens
    
    # Calculate estimated cost in USD
    estimated_cost = (tokens_in * INPUT_TOKEN_PRICE_PER_1K / 1000) + (tokens_out * OUTPUT_TOKEN_PRICE_PER_1K / 1000)
    
    # Get alt text from response
    alt_text = completion.choices[0].message.content
    
    # Extract filename from path
    filename = os.path.basename(image_path)
    
    # Create result dictionary
    result = {
        filename: {
            "alt_text": alt_text,
            "metadata": {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "tokens_total": tokens_total,
                "duration": f"{duration:.2f} seconds",
                "estimated_cost": f"${estimated_cost:.6f}"
            }
        }
    }
    
    return result

def predict(image_paths, user_context=None):
    """
    Generate alt text and metadata for multiple images
    Args:
        image_paths: List of paths to image files or a single path
        user_context: Optional user-provided context for alt text generation
    Returns:
        dict: Combined JSON dictionary with alt text and metadata for all images
    """
    # Handle both single path and list of paths
    if isinstance(image_paths, str):
        return predict_single(image_paths, user_context)
    
    # Process multiple images and combine results
    combined_results = {}
    for image_path in image_paths:
        result = predict_single(image_path, user_context)
        combined_results.update(result)
    
    return combined_results