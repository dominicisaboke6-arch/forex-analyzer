import threading
import time
import streamlit as st
import pyautogui
import human_bot

st.set_page_config(page_title="Human Bot Controller", layout="centered")
st.title("Human Bot Controller")
st.caption("Move cursor to top-left corner (0, 0) at any time to abort pyautogui.")

if "config" not in st.session_state:
    st.session_state.config = human_bot.load_config()
if "running" not in st.session_state:
    st.session_state.running = False

cfg = st.session_state.config

col1, col2 = st.columns(2)
with col1:
    task = st.selectbox("Task", ["Active Session Loop", "Coding Snippet", "Spreadsheet Entry"])
with col2:
    minutes = st.number_input(
        "Active session (minutes)",
        min_value=1,
        max_value=240,
        value=int(cfg.get("default_session_minutes", 15)),
    )

save_key = st.selectbox("Save shortcut modifier", ["ctrl", "command"], index=0)

st.subheader("Target Screen Coordinates")
default_xy = cfg["editor_xy"] if task == "Coding Snippet" else cfg["spreadsheet_first_cell_xy"]
c_x, c_y = st.columns(2)
target_x = c_x.number_input("X", min_value=0, max_value=5000, value=int(default_xy[0]))
target_y = c_y.number_input("Y", min_value=0, max_value=5000, value=int(default_xy[1]))

b_col1, b_col2 = st.columns(2)
if b_col1.button("Capture Mouse in 3s"):
    time.sleep(3)
    pos = pyautogui.position()
    if task == "Coding Snippet":
        st.session_state.config["editor_xy"] = [pos.x, pos.y]
    else:
        st.session_state.config["spreadsheet_first_cell_xy"] = [pos.x, pos.y]
    st.info(f"Captured X={pos.x}, Y={pos.y}")
    st.rerun()

if b_col2.button("Save to config.json"):
    st.session_state.config["default_session_minutes"] = int(minutes)
    if task == "Coding Snippet":
        st.session_state.config["editor_xy"] = [int(target_x), int(target_y)]
    else:
        st.session_state.config["spreadsheet_first_cell_xy"] = [int(target_x), int(target_y)]
    human_bot.save_config(st.session_state.config)
    st.success("Saved settings to config.json")


def _run_task(selected_task: str, x: int, y: int, duration_min: int, mod_key: str):
    try:
        time.sleep(2)
        if selected_task == "Active Session Loop":
            human_bot.active_session_loop(minutes=int(duration_min))
        elif selected_task == "Coding Snippet":
            human_bot.run_coding_snippet((int(x), int(y)), save_key=mod_key)
        elif selected_task == "Spreadsheet Entry":
            sample_rows = [("Widget A", 120), ("Widget B", 340), ("Widget C", 85)]
            human_bot.run_spreadsheet_entry((int(x), int(y)), sample_rows)
    finally:
        st.session_state.running = False


if st.button("Run Bot", type="primary", disabled=st.session_state.running):
    st.session_state.running = True
    thread = threading.Thread(
        target=_run_task,
        args=(task, target_x, target_y, minutes, save_key),
        daemon=True,
    )
    thread.start()
    st.success(f"Started '{task}' in 2 seconds...")
