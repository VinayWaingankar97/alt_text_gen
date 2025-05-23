import streamlit as st
import json
import os
import io
import tempfile
from PIL import Image
from app_helper import predict


st.set_page_config(layout="wide", page_title="Image Alt Text Generator")


def check_password():
    
    def password_entered():
        
        correct_username = "admin"
        correct_password = "qpalzm4567"  
        
        if st.session_state["username"].lower() == correct_username and \
           st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
            del st.session_state["username"]  
        else:
            st.session_state["password_correct"] = False
            st.error("😕 Invalid username or password")

    if st.session_state.get("password_correct", False):
        return True

    
    st.markdown("<h1 style='text-align: center;'>Login Required</h1>", unsafe_allow_html=True)
    
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
    
    return False

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

def main_app():
    
    st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
    try:
        st.image(r"C:\Users\vwaingankar\Desktop\alt_text_gen\logofinal.png", width=350)
    except:
        st.warning("Logo image not found. Update the path in the code or remove this section.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.title("Image Alt Text Generation")
    st.write("Upload one or multiple images to generate alt text with detailed metadata using Azure OpenAI.")

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

def main():
    
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if check_password():
        main_app()

if __name__ == "__main__":
    main()
