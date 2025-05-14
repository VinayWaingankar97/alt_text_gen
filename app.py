import streamlit as st
import json
import os
import io
import tempfile
from PIL import Image
from app_helper import predict

st.set_page_config(layout="wide", page_title="Image Alt Text Generator")

# Display organization logo at top center
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Use either raw string (r prefix) or double backslashes for Windows paths
    st.image(r"C:\Users\vwaingankar\Desktop\alt_text_gen\logo.png", use_column_width=True)

st.title("Image Alt Text Generation")
st.write("Upload one or multiple images to generate alt text with detailed metadata using Azure OpenAI.")

# Function to safely display images, converting AVIF if needed
def safe_display_image(file, caption, use_container_width=True):
    try:
        # Try to display the image directly
        st.image(file, caption=caption, use_container_width=use_container_width)
    except Exception as e:
        try:
            # If direct display fails, try to convert using PIL
            image = Image.open(file)
            
            # Convert to RGB if needed (handles AVIF and other formats)
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            # Save as PNG in memory
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            buf.seek(0)
            
            # Display the converted image
            st.image(buf, caption=f"{caption} (converted from original format)", use_container_width=use_container_width)
        except Exception as conversion_error:
            st.error(f"Could not display image: {str(e)}. Conversion also failed: {str(conversion_error)}")

# Main app
def main():
    # User-defined context text box
    user_context = st.text_area(
        "Optional: Provide additional context for alt text generation", 
        placeholder="Leave blank for default alt text generation...",
        help="You can provide specific details or instructions for generating alt text. If left blank, a default generation prompt will be used."
    )

    # Allow multiple file uploads
    uploaded_files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png", "avif"], accept_multiple_files=True)

    if uploaded_files:
        # Create a temporary directory to store uploaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            image_paths = []
            
            # Save all uploaded files to the temporary directory
            for uploaded_file in uploaded_files:
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_paths.append(temp_path)
            
            # Process all images and get combined results
            with st.spinner(f"Generating alt text for {len(image_paths)} image(s)..."):
                all_results = predict(image_paths, user_context)
            
            # Display each image with its results
            for i, uploaded_file in enumerate(uploaded_files):
                st.markdown(f"### Image {i+1}: {uploaded_file.name}")
                
                # Create columns for this image
                col1, col2 = st.columns([1, 2])
                
                # Display the image safely
                with col1:
                    # Reset file pointer to beginning
                    uploaded_file.seek(0)
                    safe_display_image(
                        uploaded_file, 
                        caption=f"Image {i+1}: {uploaded_file.name}", 
                        use_container_width=True
                    )
                
                # Display results for this image
                with col2:
                    filename = uploaded_file.name
                    
                    if filename in all_results:
                        result = all_results[filename]
                        
                        st.subheader("Generated Alt Text")
                        st.write(result["alt_text"])
                        
                        st.subheader("Metadata")
                        metadata = result["metadata"]
                        
                        # Display metadata in an organized way
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
                
                # Add a divider between images
                if i < len(uploaded_files) - 1:
                    st.markdown("---")
            
            # Show raw JSON if expanded
            with st.expander("View Raw JSON Response for All Images"):
                st.json(all_results)
                
            # Add option to download the JSON results
            json_str = json.dumps(all_results, indent=2)
            st.download_button(
                label="Download JSON Results",
                data=json_str,
                file_name="alt_text_results.json",
                mime="application/json"
            )

# Run the main app
if __name__ == "__main__":
    main()