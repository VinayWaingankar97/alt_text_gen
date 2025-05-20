import streamlit as st
import json
import os
import io
import tempfile
import base64
import time
from PIL import Image
from openai import AzureOpenAI

# Page configuration
st.set_page_config(layout="wide", page_title="Image Alt Text Generator")

# Constants for token pricing
INPUT_TOKEN_PRICE_PER_1K = 0.02
OUTPUT_TOKEN_PRICE_PER_1K = 0.08

# Get Azure OpenAI credentials from environment variables
endpoint = os.getenv("ENDPOINT_URL", "https://alt-text-gen-openai-poc.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "B76JFNwYMyR4MgJt2kdMXJNugqVLbWACYpda8rTTbDJL5YrOu3o8JQQJ99BEACHYHv6XJ3w3AAABACOGe7sd")

# Function to predict alt text for a single image
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

# Function to predict alt text for multiple images
def predict(image_paths, user_context=None, project_id=None):
    if isinstance(image_paths, str):
        return predict_single(image_paths, user_context, project_id)
    
    combined_results = {}
    for image_path in image_paths:
        result = predict_single(image_path, user_context, project_id)
        combined_results.update(result)
    
    return combined_results

# Function to safely display images
def safe_display_image(file, caption, use_container_width=True):
    try:
        st.image(file, caption=caption, use_container_width=use_container_width)
    except Exception as e:
        try:
            image = Image.open(file)
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            buf.seek(0)
            
            st.image(buf, caption=f"{caption} (converted from original format)", use_container_width=use_container_width)
        except Exception as conversion_error:
            st.error(f"Could not display image: {str(e)}. Conversion also failed: {str(conversion_error)}")

# Main function
def main():
    # Display logo if it exists in the current directory
    try:
        st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
        st.image("logofinal.png", width=350)
        st.markdown("</div>", unsafe_allow_html=True)
    except:
        # If the logo file doesn't exist, just continue without it
        pass

    st.title("Image Alt Text Generation")
    st.write("Upload one or multiple images to generate alt text with detailed metadata using Azure OpenAI.")
    
    # Check if environment variables are set
    if not endpoint or not subscription_key:
        st.error("❌ Azure OpenAI credentials not found! Please set ENDPOINT_URL and AZURE_OPENAI_API_KEY as environment variables.")
        st.info("These can be set in the Streamlit Cloud dashboard under 'Advanced settings' > 'Secrets'")
        st.stop()

    # Add project ID field
    project_id = st.text_input(
        "Project ID",
        placeholder="Enter project identifier",
        help="Enter a unique identifier for this project"
    )
    
    user_context = st.text_area(
        "Provide context for alt text generation", 
        placeholder="",
        help="You can provide specific details or instructions for generating alt text. If left blank, a default generation prompt will be used."
    )

    uploaded_files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

    if uploaded_files:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_paths = []
            
            for uploaded_file in uploaded_files:
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_paths.append(temp_path)
            
            with st.spinner(f"Generating alt text for {len(image_paths)} image(s)..."):
                # Pass project_id to predict function
                all_results = predict(image_paths, user_context, project_id)
            
            for i, uploaded_file in enumerate(uploaded_files):
                st.markdown(f"### Image {i+1}: {uploaded_file.name}")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    uploaded_file.seek(0)
                    safe_display_image(
                        uploaded_file, 
                        caption=f"Image {i+1}: {uploaded_file.name}", 
                        use_container_width=True
                    )
                
                with col2:
                    filename = uploaded_file.name
                    
                    if filename in all_results:
                        result = all_results[filename]
                        
                        st.subheader("Generated Alt Text")
                        st.write(result["alt_text"])
                        
                        st.subheader("Metadata")
                        metadata = result["metadata"]
                        
                        # Display project ID in the UI
                        if "project_id" in metadata:
                            st.info(f"Project ID: {metadata['project_id']}")
                        
                        col_meta1, col_meta2 = st.columns(2)
                        
                        with col_meta1:
                            st.metric("Input Tokens", metadata.get("tokens_in", "N/A"))
                            st.metric("Output Tokens", metadata.get("tokens_out", "N/A"))
                            st.metric("Total Tokens", metadata.get("tokens_total", "N/A"))
                        
                        with col_meta2:
                            st.metric("Processing Time", metadata.get("duration", "N/A").replace(" seconds", "") if "duration" in metadata else "N/A")
                            st.metric("Estimated Cost", metadata.get("estimated_cost", "N/A"))
                    else:
                        st.error(f"No results found for {filename}")
                
                if i < len(uploaded_files) - 1:
                    st.markdown("---")
            
            with st.expander("View Raw JSON Response for All Images"):
                st.json(all_results)
                
            json_str = json.dumps(all_results, indent=2)
            st.download_button(
                label="Download JSON Results",
                data=json_str,
                file_name="alt_text_results.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()
