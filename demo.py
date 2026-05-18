from pathlib import Path
from PIL import Image
import streamlit as st
import polars as pl
from oneshot.llm_request import ImageInput, request_ollama
from oneshot.utils import b64enc, guess_image_mime, measure_time
from oneshot.llm_response import from_ollama_responses
import tomllib
import requests
import base64
import io
import json

st.set_page_config(page_title="Plate Reading with Gemma4", layout="wide")

DATA_AND_CONFIG = Path("data_and_config")
CONFIGFILE = DATA_AND_CONFIG / "config.toml"
IMAGE_DIR = DATA_AND_CONFIG / "images" # for query images
REF_IMAGE_DIR = DATA_AND_CONFIG / "references" # for reference images - although this is not needed (as gemma just gets confused)
VALID_EXTS = {".png", ".jpg", ".jpeg", ".gif"} # a filter for file endings
REF_RED = REF_IMAGE_DIR / "Red_A061.png"
REF_GREEN = REF_IMAGE_DIR / "Green_A049.png"
REF_NEGATIVE = REF_IMAGE_DIR / "Negative_A021.png"
LABELFILE = REF_IMAGE_DIR / "Labels.csv"

# helper function to retrueve paths
def discover_images(directory: Path):
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted([p for p in directory.iterdir() if p.suffix.lower() in VALID_EXTS])

# store image file paths
image_files = discover_images(IMAGE_DIR)

# name_to_path is a map (dictionary) mapping image name -> path
name_to_path = {p.name: p for p in image_files}

# import labels into dataframe
labels = pl.read_csv(LABELFILE, separator=";", encoding="utf-8")

# put labels into session_state
if "labels" not in st.session_state:
    st.session_state.labels = labels
    
# put config into sessions
if "config" not in st.session_state:
    st.session_state.config = tomllib.loads(CONFIGFILE.read_text(encoding="utf-8"))
    
# put ollama_host into sessions
if "ollama_host" not in st.session_state:
    st.session_state.ollama_host = st.session_state.config.get("ollama_host")
    
# put model into session_state
if "model" not in st.session_state:
    st.session_state.model = st.session_state.config.get("model")
    
# put prompt into sessions
if "prompt" not in st.session_state:
    st.session_state.prompt = st.session_state.config.get("prompt_simple")
    
# put reference images into sessions
if "reference_images" not in st.session_state:
    #red_ii = ImageInput(mimetype=guess_image_mime(REF_RED), b64=b64enc(REF_RED))
    #green_ii = ImageInput(mimetype=guess_image_mime(REF_GREEN), b64=b64enc(REF_GREEN))
    #negative_ii = ImageInput(mimetype=guess_image_mime(REF_NEGATIVE), b64=b64enc(REF_NEGATIVE))
    #st.session_state.reference_images = [negative_ii, red_ii, green_ii]
    #st.session_state.reference_images = [negative_ii, red_ii]
    st.session_state.reference_images = []
    
# create function to extract json block from response
def extract_json_block(s: str) -> str:
    lines = s.strip().splitlines()
    # drop any fence-like lines
    inner = [
        ln for ln in lines
        if not ln.strip().startswith("```")
    ]
    return "\n".join(inner)

# create function to convert to json from json block
def extract_json(s: str) -> str:
    result = "json could not be extracted"
    try:
        result = json.loads(extract_json_block(s))
    except:
        pass
    return result
    
# create lookup function for labels
def lookup_label(image_stem: str) -> dict[str]:
    label = {"label": "not found", "remark": "not found"}
    try:
        label = st.session_state.labels.filter(pl.col("Image") == image_stem).select("Label").item()
        remark = st.session_state.labels.filter(pl.col("Image") == image_stem).select("Remark").item()
    except:
        pass
    return {"label": label, "remark": remark}

# create lookup function for llm calls
def lookup_llm(image: Path):
    try:
        image_ii = ImageInput(mimetype=guess_image_mime(image), b64=b64enc(image))
        images = st.session_state.reference_images.copy() # copy is important!
        images.append(image_ii)
        
        # request
        rq = request_ollama(model_name = st.session_state.model,
                            question = st.session_state.prompt,
                            images = images,
                            url = f"{st.session_state.ollama_host}/api/generate")
        
        # relay request to llm
        raw_response, elapsed = measure_time(requests.post, url = rq.url, headers = rq.headers, json = rq.json)
        raw_response_json = raw_response.json()
        llm_response = {"response_text": raw_response_json.get("response"),
                        "response_json": extract_json(raw_response_json.get("response")),
                        "response_all": from_ollama_responses(raw_response_json),
                        "json_payload": rq.json,
                        "elapsed": format(elapsed, ".3f")}        
    except Exception as exc:
        llm_response = {"response_text": f"failed due to: {exc}",
                        "response_json": None,
                        "response_all": None,
                        "json_payload": None,
                        "elapsed": None}  
    return llm_response

# create function to revert base64 encoded images to images
def revert_base64_images(b64_list = list[str]) -> list[Image.Image]:
    images = []
    for b64_image in b64_list:
        image_bytes = base64.b64decode(b64_image)
        image = Image.open(io.BytesIO(image_bytes))
        images.append(image)
    return images

# session state stores data to be persisted across the session
if "model_status" not in st.session_state:
    st.session_state.model_status = "idle"
if "model_response" not in st.session_state:
    st.session_state.model_response = "No model response yet."
if "reference_answer" not in st.session_state:
    st.session_state.reference_answer = "No reference answer yet."
if "llm_response" not in st.session_state:
    st.session_state.llm_response = {}

# css 
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1120px;
        padding-top: 3.2rem;
        padding-bottom: 1.5rem;
    }
    h1, h2, h3, p { margin-top: 0; }
    .app-title {
        font-size: clamp(1.8rem, 2.7vw, 2.6rem);
        font-weight: 700;
        line-height: 1.15;
        margin: 0 0 0.65rem 0;
        padding-top: 1rem;
    }
    .intro-text, .small-text {
        color: #5f6368;
        font-size: 0.98rem;
        line-height: 1.6;
        margin-bottom: 0.55rem;
    }
    .field-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #1f1f1f;
        margin-bottom: 0.4rem;
    }
    .plain-box {
        min-height: 5.25rem;
        white-space: pre-wrap;
        line-height: 1.6;
        margin-top: 0.1rem;
    }
    .status-text {
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 0.55rem;
        margin-bottom: 0.2rem;
    }
    .status-idle { color: #5f6368; }
    .status-running { color: #8a5a00; }
    .status-finished { color: #1f6a38; }
    .subsection-gap {
        margin-top: 1rem;
    }
    div[data-testid="stImage"] img {
        object-fit: contain;
        height: auto;
    }
    .footer-wrap {
        margin-top: 1.2rem;
        padding-top: 0.35rem;
    }
    .debug {
          border: 0.2rem solid red;
          padding: 0.4rem;
          border-radius: 1rem;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.4rem;
            padding-left: 0.9rem;
            padding-right: 0.9rem;
        }
        .app-title {
            font-size: 1.9rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# the page proper
st.markdown('<div class="app-title">Plate Reading with Gemma4</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="intro-text">This demo shows image classification capabilities of the Gemma4 LLM. The demo will only be available until June 7th, 2026. <br />Select an image of a plate, view the label and optionally send it to Gemma4 for classification.</div>',
    unsafe_allow_html=True,
)
st.write("")

# create a left and right column
main_left, main_right = st.columns([1.25, 1], gap="large")

# initialize selected_path, which holds the path to the image (selected via dropdown below)
selected_path = None

# fill the left column
with main_left:
    # dropdown for image selection container html
    st.markdown('<div class="field-title">Dropdown selection of images</div>', unsafe_allow_html=True)
    if image_files:
        selected_name = st.selectbox(
            "Choose an image", # not visible with "hidden" and "collapsed" but anywho!
            options=list(name_to_path.keys()),
            label_visibility="collapsed", # this saves space - alternatives are "hidden" and "visible"
        )
        # path is derived from the map name_to_path (see above)
        selected_path = name_to_path[selected_name]
    else:
        st.warning("No images found in the images directory.")
    
    # image container html
    # title of image container html
    st.markdown('<div class="field-title">Preview of selected image</div>', unsafe_allow_html=True)
    # insert image
    if selected_path is not None:
        st.image(str(selected_path), width="stretch")
    else:
        st.info("Preview becomes available once images are present in the images directory.")
        
    # true lable, reference answer - this should be changed as soon as dropdown is changed
    if selected_path:
        selected_path_label = lookup_label(selected_path.stem)
        st.session_state.reference_answer = (
            f"Label: **{selected_path_label.get("label", "not available")}**\n"
            f"Remark: {selected_path_label.get("remark", "not available")}"
        )
        st.session_state.model_response = ""
    
# right column
with main_right:
    # move button and model output to here
    # Reference answer html container
    st.markdown('<div class="field-title">Reference:</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="plain-box">{st.session_state.reference_answer}</div>', unsafe_allow_html=True)
    
    # horizontal space divider
    st.markdown('<div class="subsection-gap"></div>', unsafe_allow_html=True)
    
    # button section html container
    st.markdown('<div class="field-title">Classify image (select response type):</div>', unsafe_allow_html=True)
    prompt_choice = st.radio("Response type", ["simple (class only)", "elaborate (with remark)"], index=0, horizontal=True, label_visibility="collapsed")
    if prompt_choice == "simple (class only)":
        st.session_state.prompt = st.session_state.config.get("prompt_simple")
    else:
        st.session_state.prompt = st.session_state.config.get("prompt_elaborate")
    submit = st.button("Submit image to Gemma4", width="stretch", disabled=selected_path is None)

    # initialize status contents
    # these are filled into Status display html section below
    status_class = "status-idle"
    status_label = "Idle" 

    # submit is filled by st.button, see above, selected_path is derived from dropdown content, see above
    if submit and selected_path is not None:
        st.session_state.model_status = "running"
        status_class = "status-running"
        status_label = "Relaying image to model ..."
        
        # here the task is relayed
        with st.spinner("Relaying image to model ..."):
            llm_response = lookup_llm(selected_path)
            st.session_state.llm_response = llm_response

        # model response
        st.session_state.model_status = "finished"
        if prompt_choice == "simple (class only)":
            response_class = llm_response.get('response_text')
            response_remark = "not available"
        else:
            response_class = llm_response.get('response_json').get("class", "not available")
            response_remark = llm_response.get('response_json').get("remark", "not available")
            
        st.session_state.model_response = (
            f"Class: **{response_class}**\n"
            f"Remark: {response_remark}\n"
            f"Model: {llm_response.get('response_all').model_name}\n"
            f"Elapsed: {llm_response.get('elapsed')} seconds."
        )
        
        status_class = "status-finished"
        status_label = "Finished"
    else:
        # not sure why this is necessary
        if st.session_state.model_status == "running":
            status_class = "status-running"
            status_label = "Relaying image to model ..."
        elif st.session_state.model_status == "finished":
            status_class = "status-finished"
            status_label = "Finished"
            
    # Status display html section container
    st.markdown(f'<div class="status-text {status_class}">{status_label}</div>', unsafe_allow_html=True)
    
    # Model response container
    st.write("") # to be changed to .markdown
    st.markdown('<div class="field-title">Model response</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="plain-box">{st.session_state.model_response}</div>', unsafe_allow_html=True)

# debug section
if st.session_state.config.get("debug"):
    debug_json_payload = st.session_state.llm_response.get("json_payload")
    debug_b64enc_images = "N/A"
    debug_images = None
    if debug_json_payload:
        debug_b64enc_images = debug_json_payload.get("images")
        debug_images = revert_base64_images(debug_b64enc_images)
        
    # st.markdown(f"""
    #             <div class="debug small-text">
    #             Debug section<br />
    #             {debug_b64enc_images}
    #             </div>
    #             """,
    #             unsafe_allow_html=True)
    
    if debug_images:
        st.image(debug_images, caption=[f"Image {i}" for i in range(len(debug_images))], width=200)

# footer container, below columns
st.markdown(
    """
    <div class="footer-wrap small-text">
        <div class="field-title">Information</div>
        This is a demo intended to promote scientific discussion. It is created and maintained for a limited time by <a href="https://johanneselias.net" target = "_blank">Johannes Elias</a>.
    </div>
    """,
    unsafe_allow_html=True,
)
