import streamlit as st

st.set_page_config(
    page_title="ChronoVision Demo",
    page_icon="◈",
    layout="wide"
)

st.title("◈ ChronoVision — Video Input Demo")
st.caption("Upload a video and demonstrate multi-video temporal analysis.")

video = st.file_uploader(
    "Upload a video",
    type=["mp4", "mov", "avi", "mkv"]
)

if video:
    st.success(f"Loaded: {video.name}")
    st.video(video)

    st.info(
        "Video successfully ingested. "
        "ChronoVision can process this video through its detection, "
        "tracking and temporal reasoning pipeline."
    )
else:
    st.info("Upload an MP4 video to begin.")