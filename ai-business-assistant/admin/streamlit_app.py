"""Optional Streamlit dashboard for local debugging."""
from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

DB_PATH = st.sidebar.text_input("Database path", "assistant.db")

st.title("AI Business Assistant Admin")

conn = sqlite3.connect(DB_PATH)

tab1, tab2, tab3 = st.tabs(["Tasks", "Notes", "History"])

with tab1:
    tasks = pd.read_sql_query("SELECT * FROM tasks ORDER BY id DESC", conn)
    st.dataframe(tasks, use_container_width=True)

with tab2:
    notes = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
    st.dataframe(notes, use_container_width=True)

with tab3:
    hist = pd.read_sql_query("SELECT * FROM conversation_history ORDER BY id DESC LIMIT 200", conn)
    st.dataframe(hist, use_container_width=True)

conn.close()
