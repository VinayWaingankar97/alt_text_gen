import os
import base64
import time
import json
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

endpoint = os.getenv("ENDPOINT_URL", "https://alt-text-gen-openai-poc.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "B76JFNwYMyR4MgJt2kdMXJNugqVLbWACYpda8rTTbDJL5YrOu3o8JQQJ99BEACHYHv6XJ3w3AAABACOGe7sd")

INPUT_TOKEN_PRICE_PER_1K = 0.02
OUTPUT_TOKEN_PRICE_PER_1K = 0.08

def predict_single(image_path, user_context=None, project_id=None):
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2025-01-01-preview",
    )
    
    start_time = time.time()
    
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("ascii")
    except FileNotFoundError:
        raise Exception(f"Image file not found at path: {image_path}")
    except Exception as e:
        raise Exception(f"Error reading image file: {str(e)}")
    
    default_user_text = "Generate Alt Text for the following Image:"
    
    user_content = [
        {"type": "text", "text": default_user_text}
    ]
    
    if user_context and user_context.strip():
        user_content.append({"type": "text", "text": user_context})
    
    user_content.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{encoded_image}"
        }
    })
    
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
    
    duration = time.time() - start_time
    
    tokens_in = completion.usage.prompt_tokens
    tokens_out = completion.usage.completion_tokens
    tokens_total = completion.usage.total_tokens
    
    estimated_cost = (tokens_in * INPUT_TOKEN_PRICE_PER_1K / 1000) + (tokens_out * OUTPUT_TOKEN_PRICE_PER_1K / 1000)
    
    alt_text = completion.choices[0].message.content
    
    filename = os.path.basename(image_path)
    
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
    
    # Add project_id to metadata if provided
    if project_id:
        result[filename]["metadata"]["project_id"] = project_id
    
    return result

def predict(image_paths, user_context=None, project_id=None):
    if isinstance(image_paths, str):
        return predict_single(image_paths, user_context, project_id)
    
    combined_results = {}
    for image_path in image_paths:
        result = predict_single(image_path, user_context, project_id)
        combined_results.update(result)
    
    return combined_results
